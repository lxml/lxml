# XML parser that provides dictionary sharing

cimport xmlparser
cimport htmlparser
from xmlparser cimport xmlParserCtxt, xmlDict

class XMLSyntaxError(LxmlSyntaxError):
    pass

class ParserError(LxmlError):
    pass

ctypedef enum LxmlParserType:
    LXML_XML_PARSER
    LXML_HTML_PARSER

cdef class _ParserContext:
    """Global parser context to share the string dictionary.
    """
    cdef xmlDict* _c_dict
    def __init__(self):
        self._c_dict = NULL

    def __dealloc__(self):
        if self._c_dict is not NULL:
            xmlparser.xmlDictFree(self._c_dict)

    cdef void _initParserDict(self, xmlParserCtxt* pctxt):
        "Assure we always use the same string dictionary."
        if self._c_dict is NULL or self._c_dict is pctxt.dict:
            return
        if pctxt.dict is not NULL:
            xmlparser.xmlDictFree(pctxt.dict)
        pctxt.dict = self._c_dict
        xmlparser.xmlDictReference(pctxt.dict)

    cdef void _initXPathParserDict(self, xpath.xmlXPathContext* pctxt):
        "Assure we always use the same string dictionary."
        if self._c_dict is NULL or self._c_dict is pctxt.dict:
            return
        if pctxt.dict is not NULL:
            xmlparser.xmlDictFree(pctxt.dict)
        pctxt.dict = self._c_dict
        xmlparser.xmlDictReference(pctxt.dict)

    cdef void _initDocDict(self, xmlDoc* result):
        "Store dict of last object parsed if no shared dict yet"
        if result is NULL:
            return
        if self._c_dict is NULL:
            #print "storing shared dict"
            if result.dict is NULL:
                result.dict = xmlparser.xmlDictCreate()
            self._c_dict = result.dict
            xmlparser.xmlDictReference(self._c_dict)
        elif result.dict != self._c_dict:
            if result.dict is not NULL:
                xmlparser.xmlDictFree(result.dict)
            result.dict = self._c_dict
            xmlparser.xmlDictReference(result.dict)

cdef _ParserContext __GLOBAL_PARSER_CONTEXT
__GLOBAL_PARSER_CONTEXT = _ParserContext()

############################################################
## support for Python unicode I/O
############################################################

# name of Python unicode encoding as known to libxml2
cdef char* _UNICODE_ENCODING
_UNICODE_ENCODING = NULL

cdef void _setupPythonUnicode():
    """Sets _UNICODE_ENCODING to the internal encoding name of Python unicode
    strings if libxmls supports reading native Python unicode.  This depends
    on iconv and the local Python installation, so we simply check if we find
    a matching encoding handler.
    """
    cdef tree.xmlCharEncodingHandler* enchandler
    cdef Py_ssize_t l
    cdef char* buffer
    cdef char* enc
    utext = python.PyUnicode_DecodeUTF8("<test/>", 7, 'strict')
    l = python.PyUnicode_GET_DATA_SIZE(utext)
    buffer = python.PyUnicode_AS_DATA(utext)
    enc = _findEncodingName(buffer, l)
    enchandler = tree.xmlFindCharEncodingHandler(enc)
    if enchandler is not NULL:
        global _UNICODE_ENCODING
        tree.xmlCharEncCloseFunc(enchandler)
        _UNICODE_ENCODING = enc

cdef char* _findEncodingName(char* buffer, int size):
    "Work around bug in libxml2: find iconv name of encoding on our own."
    cdef int enc
    enc = tree.xmlDetectCharEncoding(buffer, size)
    if enc == tree.XML_CHAR_ENCODING_UTF16LE:
        return "UTF16LE"
    elif enc == tree.XML_CHAR_ENCODING_UTF16BE:
        return "UTF16BE"
    elif enc == tree.XML_CHAR_ENCODING_UCS4LE:
        return "UCS-4LE"
    elif enc == tree.XML_CHAR_ENCODING_UCS4BE:
        return "UCS-4BE"
    else:
        return tree.xmlGetCharEncodingName(enc)

_setupPythonUnicode()

############################################################
## support for file-like objects
############################################################

cdef class _FileParserContext:
    cdef object _filelike
    cdef object _url
    cdef object _bytes_utf
    cdef _ExceptionContext _exc_context
    cdef cstd.size_t _bytes_read
    cdef char* _c_url
    def __init__(self, filelike, exc_context, url=None):
        self._exc_context = exc_context
        self._filelike = filelike
        self._url = url
        if url is None:
            self._c_url = NULL
        else:
            self._c_url = _cstr(url)
        self._bytes_utf  = ''
        self._bytes_read = 0

    cdef xmlparser.xmlParserInput* _createParserInput(self, xmlParserCtxt* ctxt):
        cdef xmlparser.xmlParserInputBuffer* c_buffer
        c_buffer = xmlparser.xmlAllocParserInputBuffer(0)
        c_buffer.context = <python.PyObject*>self
        c_buffer.readcallback = _readFilelikeParser
        return xmlparser.xmlNewIOInputStream(ctxt, c_buffer, 0)

    cdef xmlDoc* _readDoc(self, xmlParserCtxt* ctxt, int options,
                          LxmlParserType parser_type):
        if parser_type == LXML_XML_PARSER:
            return xmlparser.xmlCtxtReadIO(
                ctxt, _readFilelikeParser, NULL, <python.PyObject*>self,
                self._c_url, NULL, options)
        else:
            return htmlparser.htmlCtxtReadIO(
                ctxt, _readFilelikeParser, NULL, <python.PyObject*>self,
                self._c_url, NULL, options)

    cdef int copyToBuffer(self, char* c_buffer, int c_size):
        cdef char* c_start
        cdef Py_ssize_t byte_count, remaining
        if self._bytes_read < 0:
            return 0
        try:
            byte_count = python.PyString_GET_SIZE(self._bytes_utf)
            remaining = byte_count - self._bytes_read
            if remaining <= 0:
                self._bytes_utf = _utf8( self._filelike.read(c_size) )
                self._bytes_read = 0
                remaining = python.PyString_GET_SIZE(self._bytes_utf)
                if remaining == 0:
                    self._bytes_read = -1
                    return 0
            if c_size > remaining:
                c_size = remaining
            c_start = _cstr(self._bytes_utf) + self._bytes_read
            self._bytes_read = self._bytes_read + c_size
            cstd.memcpy(c_buffer, c_start, c_size)
            return c_size
        except Exception:
            self._exc_context._store_raised()
            return -1

cdef int _readFilelikeParser(void* ctxt, char* c_buffer, int c_size):
    return (<_FileParserContext>ctxt).copyToBuffer(c_buffer, c_size)

############################################################
## support for custom document loaders
############################################################

cdef xmlparser.xmlParserInput* _local_resolver(char* c_url, char* c_pubid,
                                               xmlParserCtxt* c_context):
    cdef _ResolverContext context
    cdef _InputDocument   doc_ref
    cdef _FileParserContext file_context
    cdef xmlparser.xmlParserInput* c_input
    if c_context._private is NULL or \
       not isinstance(<object>c_context._private, _ResolverContext):
        if __DEFAULT_ENTITY_LOADER is NULL:
            return NULL
        return __DEFAULT_ENTITY_LOADER(c_url, c_pubid, c_context)

    try:
        if c_url is NULL:
            url = None
        else:
            url = funicode(c_url)
        if c_pubid is NULL:
            pubid = None
        else:
            pubid = funicode(c_pubid)

        context = <_ResolverContext>c_context._private
        doc_ref = context._resolvers.resolve(url, pubid, context)
    except Exception:
        context._store_raised()
        return NULL

    if doc_ref is None:
        if __DEFAULT_ENTITY_LOADER is NULL:
            return NULL
        return __DEFAULT_ENTITY_LOADER(c_url, c_pubid, c_context)

    c_input = NULL
    data = None
    if doc_ref._type == PARSER_DATA_STRING:
        data = doc_ref._data_utf
        c_input = xmlparser.xmlNewStringInputStream(
            c_context, _cstr(data))
    elif doc_ref._type == PARSER_DATA_FILENAME:
        c_input = xmlparser.xmlNewInputFromFile(
            c_context, _cstr(doc_ref._data_utf))
    elif doc_ref._type == PARSER_DATA_FILE:
        file_context = _FileParserContext(doc_ref._file, context)
        c_input = file_context._createParserInput(c_context)
        data = file_context

    if data is not None:
        context._storage.add(data)
    return c_input

cdef xmlparser.xmlExternalEntityLoader __DEFAULT_ENTITY_LOADER
__DEFAULT_ENTITY_LOADER = xmlparser.xmlGetExternalEntityLoader()

xmlparser.xmlSetExternalEntityLoader(_local_resolver)

############################################################
## Parsers
############################################################

cdef class _BaseParser:
    cdef int _parse_options
    cdef _ErrorLog _error_log
    cdef readonly object resolvers
    cdef _ResolverContext _context
    cdef LxmlParserType _parser_type
    cdef xmlParserCtxt* _parser_ctxt

    def __init__(self):
        cdef xmlParserCtxt* pctxt
        if isinstance(self, HTMLParser):
            self._parser_type = LXML_HTML_PARSER
            pctxt = htmlparser.htmlCreateMemoryParserCtxt('dummy', 5)
        elif isinstance(self, XMLParser):
            self._parser_type = LXML_XML_PARSER
            pctxt = xmlparser.xmlNewParserCtxt()
        else:
            raise TypeError, "This class cannot be instantiated"
        self._parser_ctxt = pctxt
        if pctxt is NULL:
            raise ParserError, "Failed to create parser context"
        self._error_log = _ErrorLog()
        self.resolvers  = _ResolverRegistry()
        self._context   = _ResolverContext(self.resolvers)
        pctxt._private = <python.PyObject*>self._context

    def __dealloc__(self):
        if self._parser_ctxt != NULL:
            xmlparser.xmlFreeParserCtxt(self._parser_ctxt)

    property error_log:
        def __get__(self):
            return self._error_log.copy()

    def copy(self):
        "Create a new parser with the same configuration."
        cdef _BaseParser parser
        parser = self.__class__()
        parser._parse_options = self._parse_options
        parser.resolvers = self.resolvers.copy()
        parser._context = _ResolverContext(parser.resolvers)
        return parser

    cdef xmlDoc* _parseUnicodeDoc(self, utext, char* c_filename) except NULL:
        """Parse unicode document, share dictionary if possible.
        """
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef int recover
        cdef Py_ssize_t py_buffer_len
        cdef int buffer_len
        cdef char* c_text
        py_buffer_len = python.PyUnicode_GET_DATA_SIZE(utext)
        if py_buffer_len > python.INT_MAX:
            text_utf = _utf8(utext)
            py_buffer_len = python.PyString_GET_SIZE(text_utf)
            return self._parseDoc(_cstr(text_utf), py_buffer_len, c_filename)
        buffer_len = py_buffer_len

        self._error_log.connect()
        pctxt = self._parser_ctxt
        __GLOBAL_PARSER_CONTEXT._initParserDict(pctxt)

        c_text = python.PyUnicode_AS_DATA(utext)
        if self._parser_type == LXML_HTML_PARSER:
            result = htmlparser.htmlCtxtReadMemory(
                pctxt, c_text, buffer_len, c_filename, _UNICODE_ENCODING,
                self._parse_options)
        else:
            result = xmlparser.xmlCtxtReadMemory(
                pctxt, c_text, buffer_len, c_filename, _UNICODE_ENCODING,
                self._parse_options)

        self._error_log.disconnect()
        recover = self._parse_options & xmlparser.XML_PARSE_RECOVER
        return _handleParseResult(pctxt, result, NULL, recover)

    cdef xmlDoc* _parseDoc(self, char* c_text, Py_ssize_t c_len,
                           char* c_filename) except NULL:
        """Parse document, share dictionary if possible.
        """
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef int recover
        if c_len > python.INT_MAX:
            raise ParserError, "string is too long to parse it with libxml2"

        self._error_log.connect()
        pctxt = self._parser_ctxt
        __GLOBAL_PARSER_CONTEXT._initParserDict(pctxt)

        if self._parser_type == LXML_HTML_PARSER:
            result = htmlparser.htmlCtxtReadMemory(
                pctxt, c_text, c_len, c_filename, NULL, self._parse_options)
        else:
            result = xmlparser.xmlCtxtReadMemory(
                pctxt, c_text, c_len, c_filename, NULL, self._parse_options)

        self._error_log.disconnect()
        recover = self._parse_options & xmlparser.XML_PARSE_RECOVER
        return _handleParseResult(pctxt, result, NULL, recover)

    cdef xmlDoc* _parseDocFromFile(self, char* c_filename) except NULL:
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef int recover
        self._error_log.connect()
        pctxt = self._parser_ctxt
        __GLOBAL_PARSER_CONTEXT._initParserDict(pctxt)

        if self._parser_type == LXML_HTML_PARSER:
            result = htmlparser.htmlCtxtReadFile(
                pctxt, c_filename, NULL, self._parse_options)
        else:
            result = xmlparser.xmlCtxtReadFile(
                pctxt, c_filename, NULL, self._parse_options)

        self._error_log.disconnect()
        recover = self._parse_options & xmlparser.XML_PARSE_RECOVER
        return _handleParseResult(pctxt, result, c_filename, recover)

    cdef xmlDoc* _parseDocFromFilelike(self, filelike,
                                       char* c_filename) except NULL:
        # we read Python string, so we must convert to UTF-8
        cdef _FileParserContext file_context
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef int recover
        self._error_log.connect()
        pctxt = self._parser_ctxt
        __GLOBAL_PARSER_CONTEXT._initParserDict(pctxt)

        file_context = _FileParserContext(filelike, self._context)
        result = file_context._readDoc(
            pctxt, self._parse_options, self._parser_type)

        self._error_log.disconnect()
        recover = self._parse_options & xmlparser.XML_PARSE_RECOVER
        return _handleParseResult(pctxt, result, c_filename, recover)

cdef _raiseParseError(xmlParserCtxt* ctxt, char* c_filename):
    if c_filename is not NULL and \
           ctxt.lastError.domain == xmlerror.XML_FROM_IO:
        if ctxt.lastError.message is not NULL:
            message = "Error reading file %s: %s" % (
                funicode(c_filename),
                funicode(ctxt.lastError.message).strip())
        else:
            message = "Error reading file %s" % funicode(c_filename)
        raise IOError, message
    elif ctxt.lastError.message is not NULL:
        raise XMLSyntaxError, funicode(ctxt.lastError.message).strip()
    else:
        raise XMLSyntaxError

cdef xmlDoc* _handleParseResult(xmlParserCtxt* ctxt, xmlDoc* result,
                                char* c_filename, int recover) except NULL:
    cdef _ResolverContext context
    if ctxt.myDoc is not NULL:
        if ctxt.myDoc != result:
            tree.xmlFreeDoc(ctxt.myDoc)
        ctxt.myDoc = NULL

    if result is not NULL:
        if ctxt.wellFormed or recover:
            __GLOBAL_PARSER_CONTEXT._initDocDict(result)
        else:
            # free broken document
            tree.xmlFreeDoc(result)
            result = NULL

    if ctxt._private is not NULL:
        context = <_ResolverContext>ctxt._private
        if context._has_raised():
            if result is not NULL:
                tree.xmlFreeDoc(result)
                result = NULL
            context._raise_if_stored()

    if result is NULL:
        _raiseParseError(ctxt, c_filename)
    elif result.URL is NULL and c_filename is not NULL:
        result.URL = tree.xmlStrdup(c_filename)
    return result

############################################################
## XML parser
############################################################

cdef int _XML_DEFAULT_PARSE_OPTIONS
_XML_DEFAULT_PARSE_OPTIONS = (
    xmlparser.XML_PARSE_NOENT |
    xmlparser.XML_PARSE_NOCDATA
    )

cdef class XMLParser(_BaseParser):
    """The XML parser.  Parsers can be supplied as additional argument to
    various parse functions of the lxml API.  A default parser is always
    available and can be replaced by a call to the global function
    'set_default_parser'.  New parsers can be created at any time without a
    major run-time overhead.

    The keyword arguments in the constructor are mainly based on the libxml2
    parser configuration.  A DTD will also be loaded if validation or
    attribute default values are requested.

    Available keyword arguments:
    * attribute_defaults - read default attributes from DTD
    * dtd_validation     - validate (if DTD is available)
    * load_dtd           - use DTD for parsing
    * no_network         - prevent network access
    * ns_clean           - clean up redundant namespace declarations
    * recover            - try hard to parse through broken XML
    * remove_blank_text  - discard blank text nodes

    Note that you must not share parsers between threads.  This applies also
    to the default parser.
    """
    def __init__(self, attribute_defaults=False, dtd_validation=False,
                 load_dtd=False, no_network=False, ns_clean=False,
                 recover=False, remove_blank_text=False):
        cdef int parse_options
        _BaseParser.__init__(self)

        parse_options = _XML_DEFAULT_PARSE_OPTIONS
        if load_dtd:
            parse_options = parse_options | xmlparser.XML_PARSE_DTDLOAD
        if dtd_validation:
            parse_options = parse_options | xmlparser.XML_PARSE_DTDVALID | \
                            xmlparser.XML_PARSE_DTDLOAD
        if attribute_defaults:
            parse_options = parse_options | xmlparser.XML_PARSE_DTDATTR | \
                            xmlparser.XML_PARSE_DTDLOAD
        if no_network:
            parse_options = parse_options | xmlparser.XML_PARSE_NONET
        if ns_clean:
            parse_options = parse_options | xmlparser.XML_PARSE_NSCLEAN
        if recover:
            parse_options = parse_options | xmlparser.XML_PARSE_RECOVER
        if remove_blank_text:
            parse_options = parse_options | xmlparser.XML_PARSE_NOBLANKS

        self._parse_options = parse_options

cdef xmlDoc* _internalParseDoc(char* c_text, int options,
                               _ResolverContext context) except NULL:
    # internal parser function for XSLT
    cdef xmlParserCtxt* pctxt
    cdef xmlDoc* c_doc
    cdef int recover
    pctxt = xmlparser.xmlNewParserCtxt()
    if pctxt is NULL:
        return NULL
    __GLOBAL_PARSER_CONTEXT._initParserDict(pctxt)
    pctxt._private = <python.PyObject*>context
    c_doc = xmlparser.xmlCtxtReadDoc(
        pctxt, c_text, NULL, NULL, options)
    try:
        recover = options & xmlparser.XML_PARSE_RECOVER
        c_doc = _handleParseResult(pctxt, c_doc, NULL, recover)
    finally:
        xmlparser.xmlFreeParserCtxt(pctxt)
    return c_doc

cdef xmlDoc* _internalParseDocFromFile(char* c_filename, int options,
                                       _ResolverContext context) except NULL:
    # internal parser function for XSLT
    cdef xmlParserCtxt* pctxt
    cdef xmlDoc* c_doc
    cdef int recover
    pctxt = xmlparser.xmlNewParserCtxt()
    if pctxt is NULL:
        return NULL
    __GLOBAL_PARSER_CONTEXT._initParserDict(pctxt)
    pctxt._private = <python.PyObject*>context
    c_doc = xmlparser.xmlCtxtReadFile(
        pctxt, c_filename, NULL, options)
    try:
        recover = options & xmlparser.XML_PARSE_RECOVER
        c_doc = _handleParseResult(pctxt, c_doc, c_filename, recover)
    finally:
        xmlparser.xmlFreeParserCtxt(pctxt)
    return c_doc


cdef XMLParser __DEFAULT_XML_PARSER
__DEFAULT_XML_PARSER = XMLParser()

cdef _BaseParser __DEFAULT_PARSER
__DEFAULT_PARSER = __DEFAULT_XML_PARSER

def set_default_parser(_BaseParser parser=None):
    """Set a default parser.  This parser is used globally whenever no parser
    is supplied to the various parse functions of the lxml API.  If this
    function is called without a parser (or if it is None), the default parser
    is reset to the original configuration.

    Note that the default parser is not thread-safe.  Avoid the default parser
    in multi-threaded environments.  You can create a separate parser for each
    thread explicitly or use a parser pool.
    """
    global __DEFAULT_PARSER
    if parser is None:
        __DEFAULT_PARSER = __DEFAULT_XML_PARSER
    else:
        __DEFAULT_PARSER = parser

def get_default_parser():
    return __DEFAULT_PARSER

############################################################
## HTML parser
############################################################

cdef int _HTML_DEFAULT_PARSE_OPTIONS
_HTML_DEFAULT_PARSE_OPTIONS = 0

cdef class HTMLParser(_BaseParser):
    """The HTML parser.  This parser allows reading HTML into a normal XML
    tree.  By default, it can read broken (non well-formed) HTML, depending on
    the capabilities of libxml2.  Use the 'recover' option to switch this off.

    Available keyword arguments:
    * recover            - try hard to parse through broken HTML (default: True)
    * no_network         - prevent network access
    * remove_blank_text  - discard empty text nodes

    Note that you must not share parsers between threads.
    """
    def __init__(self, recover=True, no_network=False, remove_blank_text=False):
        cdef int parse_options
        _BaseParser.__init__(self)

        parse_options = _HTML_DEFAULT_PARSE_OPTIONS
        if recover:
            # XXX: make it compile on libxml2 < 2.6.21
            #parse_options = parse_options | htmlparser.HTML_PARSE_RECOVER
            parse_options = parse_options | xmlparser.XML_PARSE_RECOVER
        if no_network:
            parse_options = parse_options | htmlparser.HTML_PARSE_NONET
        if remove_blank_text:
            parse_options = parse_options | htmlparser.HTML_PARSE_NOBLANKS

        self._parse_options = parse_options

cdef HTMLParser __DEFAULT_HTML_PARSER
__DEFAULT_HTML_PARSER = HTMLParser()

############################################################
## helper functions for document creation
############################################################

cdef xmlDoc* _parseDoc(text, filename, _BaseParser parser) except NULL:
    cdef char* c_filename
    cdef char* c_text
    cdef Py_ssize_t c_len
    if parser is None:
        parser = __DEFAULT_PARSER
    if not filename:
        c_filename = NULL
    else:
        c_filename = _cstr(filename)
    if python.PyUnicode_Check(text):
        return (<_BaseParser>parser)._parseUnicodeDoc(text, c_filename)
    else:
        c_text = _cstr(text)
        c_len  = python.PyString_GET_SIZE(text)
        return (<_BaseParser>parser)._parseDoc(c_text, c_len, c_filename)

cdef xmlDoc* _parseDocFromFile(filename, _BaseParser parser) except NULL:
    if parser is None:
        parser = __DEFAULT_PARSER
    return (<_BaseParser>parser)._parseDocFromFile(_cstr(filename))

cdef xmlDoc* _parseDocFromFilelike(source, filename,
                                   _BaseParser parser) except NULL:
    cdef char* c_filename
    if parser is None:
        parser = __DEFAULT_PARSER
    if not filename:
        c_filename = NULL
    else:
        c_filename = _cstr(filename)
    return (<_BaseParser>parser)._parseDocFromFilelike(source, c_filename)

cdef xmlDoc* _newDoc():
    cdef xmlDoc* result
    result = tree.xmlNewDoc("1.0")
    __GLOBAL_PARSER_CONTEXT._initDocDict(result)
    return result

cdef xmlDoc* _copyDoc(xmlDoc* c_doc, int recursive):
    cdef xmlDoc* result
    result = tree.xmlCopyDoc(c_doc, recursive)
    if c_doc.URL is not NULL:
        # handle a bug in older libxml2 versions
        if result.URL is not NULL:
            tree.xmlFree(result.URL)
        result.URL = tree.xmlStrdup(c_doc.URL)
    __GLOBAL_PARSER_CONTEXT._initDocDict(result)
    return result

cdef xmlDoc* _copyDocRoot(xmlDoc* c_doc, xmlNode* c_new_root):
    "Recursively copy the document and make c_new_root the new root node."
    cdef xmlDoc* result
    cdef xmlDoc* fake_c_doc
    fake_c_doc = _fakeRootDoc(c_doc, c_new_root)
    result = tree.xmlCopyDoc(fake_c_doc, 1)
    _destroyFakeDoc(c_doc, fake_c_doc)
    if c_doc.URL is not NULL:
        # handle a bug in older libxml2 versions
        if result.URL is not NULL:
            tree.xmlFree(result.URL)
        result.URL = tree.xmlStrdup(c_doc.URL)
    __GLOBAL_PARSER_CONTEXT._initDocDict(result)
    return result

############################################################
## API level helper functions for _Document creation
## (here we convert to UTF-8)
############################################################

cdef _Document _parseDocument(source, _BaseParser parser):
    cdef xmlDoc* c_doc
    filename = _getFilenameForFile(source)
    if hasattr(source, 'getvalue') and hasattr(source, 'tell'):
        # StringIO - reading from start?
        if source.tell() == 0:
            return _parseMemoryDocument(source.getvalue(), filename, parser)

    # Support for file-like objects (urlgrabber.urlopen, ...)
    if hasattr(source, 'read'):
        return _parseFilelikeDocument(source, filename, parser)

    # Otherwise parse the file directly from the filesystem
    if filename is None:
        filename = source
    # open filename
    c_doc = _parseDocFromFile(_utf8(filename), parser)
    return _documentFactory(c_doc, parser)

cdef _Document _parseMemoryDocument(text, url, _BaseParser parser):
    cdef xmlDoc* c_doc
    if python.PyUnicode_Check(text):
        # pass native unicode only if libxml2 can handle it
        if _UNICODE_ENCODING is NULL:
            text = _stripEncodingDeclaration(_utf8(text))
    else:
        text = _utf8(text)
    if url is not None:
        url = _utf8(url)
    c_doc = _parseDoc(text, url, parser)
    return _documentFactory(c_doc, parser)

cdef _Document _parseFilelikeDocument(source, url, _BaseParser parser):
    cdef xmlDoc* c_doc
    if url is not None:
        url = _utf8(url)
    c_doc = _parseDocFromFilelike(source, url, parser)
    return _documentFactory(c_doc, parser)
