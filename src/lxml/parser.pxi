# XML parser that provides dictionary sharing

cimport xmlparser
cimport htmlparser
from xmlparser cimport xmlParserCtxt, xmlDict

class XMLSyntaxError(LxmlSyntaxError):
    pass

class ParserError(LxmlError):
    pass

cdef class _ParserContext:
    """Global parser context to share the string dictionary.
    """
    cdef xmlDict* _c_dict
    cdef int _initialized

    def __init__(self):
        self._c_dict = NULL
        self._initialized = 0

    def __dealloc__(self):
        if self._c_dict is not NULL:
            xmlparser.xmlDictFree(self._c_dict)

    cdef void _initParser(self):
        if not self._initialized:
            xmlparser.xmlInitParser()
            self._initialized = 1

    cdef void _initParserDict(self, xmlParserCtxt* pctxt):
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
            xmlparser.xmlDictReference(result.dict)
        elif result.dict != self._c_dict:
            if result.dict is not NULL:
                xmlparser.xmlDictFree(result.dict)
            result.dict = self._c_dict
            xmlparser.xmlDictReference(self._c_dict)

cdef _ParserContext __GLOBAL_PARSER_CONTEXT
__GLOBAL_PARSER_CONTEXT = _ParserContext()


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
        self._bytes_utf = ''
        self._bytes_read = 0

    cdef xmlparser.xmlParserInput* _createParserInput(self, xmlParserCtxt* ctxt):
        cdef xmlparser.xmlParserInputBuffer* c_buffer
        c_buffer = xmlparser.xmlAllocParserInputBuffer(0)
        c_buffer.context = <python.PyObject*>self
        c_buffer.readcallback = _copyFilelike
        return xmlparser.xmlNewIOInputStream(ctxt, c_buffer, 0)

    cdef xmlDoc* _readDoc(self, xmlParserCtxt* ctxt, int options):
        return xmlparser.xmlCtxtReadIO(
            ctxt, _copyFilelike, NULL, <python.PyObject*>self,
            self._c_url, NULL, options)

    cdef int write(self, char* c_buffer, int c_size):
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

cdef int _copyFilelike(void* ctxt, char* c_buffer, int c_size):
    return (<_FileParserContext>ctxt).write(c_buffer, c_size)
    

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
            c_context, _cstr(doc_ref._data_utf))
    elif doc_ref._type == PARSER_DATA_FILENAME:
        c_input = xmlparser.xmlNewInputFromFile(
            c_context, _cstr(doc_ref._data_utf))
    elif doc_ref._type == PARSER_DATA_FILE:
        file_context = _FileParserContext(doc_ref._file, context)
        c_input = file_context._createParserInput(c_context)

    if data is not None:
        context._storage.add(data)
    return c_input

cdef xmlparser.xmlExternalEntityLoader __DEFAULT_ENTITY_LOADER
__DEFAULT_ENTITY_LOADER = xmlparser.xmlGetExternalEntityLoader()

xmlparser.xmlSetExternalEntityLoader(_local_resolver)

############################################################
## Parsers
############################################################

cdef class BaseParser:
    cdef _ErrorLog _error_log
    cdef readonly object resolvers
    cdef _ResolverContext _context
    def __init__(self):
        cdef _ResolverContext context
        self._error_log = _ErrorLog()
        self.resolvers = _ResolverRegistry()
        self._context = _ResolverContext(self.resolvers)

    property error_log:
        def __get__(self):
            return self._error_log.copy()

    cdef _copy(self):
        cdef BaseParser parser
        parser = self.__class__()
        parser.resolvers = self.resolvers.copy()
        parser._context = _ResolverContext(parser.resolvers)
        return parser

    cdef _initContext(self, xmlParserCtxt* c_ctxt):
        __GLOBAL_PARSER_CONTEXT._initParserDict(c_ctxt)
        c_ctxt._private = <python.PyObject*>self._context

cdef _raiseParseError(xmlParserCtxt* ctxt, char* c_filename):
    if c_filename is not NULL and \
           ctxt.lastError.domain == xmlerror.XML_FROM_IO:
        if ctxt.lastError.message is not NULL:
            message = "Error reading file %s: %s" % (
                funicode(c_filename), funicode(ctxt.lastError.message))
        else:
            message = "Error reading file %s" % funicode(c_filename)
        raise IOError, message
    elif ctxt.lastError.message is not NULL:
        raise XMLSyntaxError, funicode(ctxt.lastError.message)
    else:
        raise XMLSyntaxError

cdef xmlDoc* _handleParseResult(xmlParserCtxt* ctxt, xmlDoc* result,
                                char* c_filename, int recover) except NULL:
    cdef _ResolverContext context
    if ctxt.myDoc is not NULL:
        if ctxt.myDoc != result:
            tree.xmlFreeDoc(ctxt.myDoc)
        ctxt.myDoc = NULL

    if ctxt.wellFormed or recover:
        __GLOBAL_PARSER_CONTEXT._initDocDict(result)
    elif result is not NULL:
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
    return result

############################################################
## XML parser
############################################################

cdef int _XML_DEFAULT_PARSE_OPTIONS
_XML_DEFAULT_PARSE_OPTIONS = (
    xmlparser.XML_PARSE_NOENT |
    xmlparser.XML_PARSE_NOCDATA
    )

cdef class XMLParser(BaseParser):
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

    Note that you must not share parsers between threads.  This applies also
    to the default parser.
    """
    cdef int _parse_options
    cdef xmlParserCtxt* _file_parser_ctxt
    cdef xmlParserCtxt* _memory_parser_ctxt
    cdef xmlParserCtxt* _filelike_parser_ctxt
    def __init__(self, attribute_defaults=False, dtd_validation=False,
                 load_dtd=False, no_network=False, ns_clean=False,
                 recover=False):
        cdef int parse_options
        self._memory_parser_ctxt   = NULL
        self._file_parser_ctxt     = NULL
        self._filelike_parser_ctxt = NULL

        BaseParser.__init__(self)

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

        self._parse_options = parse_options

    def __dealloc__(self):
        if self._file_parser_ctxt != NULL:
            xmlparser.xmlFreeParserCtxt(self._file_parser_ctxt)
        if self._memory_parser_ctxt != NULL:
            xmlparser.xmlFreeParserCtxt(self._memory_parser_ctxt)
        if self._filelike_parser_ctxt != NULL:
            xmlparser.xmlFreeParserCtxt(self._filelike_parser_ctxt)

    def copy(self):
        "Create a new parser with the same configuration."
        cdef XMLParser parser
        parser = self._copy()
        parser._parse_options = self._parse_options
        return parser

    cdef xmlParserCtxt* _createContext(self) except NULL:
        cdef xmlParserCtxt* pctxt
        pctxt = xmlparser.xmlNewParserCtxt()
        if pctxt is NULL:
            self._error_log.disconnect()
            raise ParserError, "Failed to create parser context"
        return pctxt

    cdef xmlDoc* _parseDoc(self, char* c_text, char* c_filename) except NULL:
        """Parse document, share dictionary if possible.
        """
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef int recover
        self._error_log.connect()
        pctxt = self._memory_parser_ctxt
        if pctxt is NULL:
            pctxt = self._createContext()
            self._memory_parser_ctxt = pctxt
        self._initContext(pctxt)
        result = xmlparser.xmlCtxtReadDoc(
            pctxt, c_text, c_filename, NULL, self._parse_options)
        self._error_log.disconnect()
        recover = self._parse_options & xmlparser.XML_PARSE_RECOVER
        return _handleParseResult(pctxt, result, NULL, recover)

    cdef xmlDoc* _parseDocFromFile(self, char* c_filename) except NULL:
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef int recover
        self._error_log.connect()
        pctxt = self._file_parser_ctxt
        if pctxt is NULL:
            pctxt = self._createContext()
            self._file_parser_ctxt = pctxt
        self._initContext(pctxt)
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
        pctxt = self._filelike_parser_ctxt
        if pctxt is NULL:
            pctxt = self._createContext()
            self._filelike_parser_ctxt = pctxt
        self._initContext(pctxt)
        file_context = _FileParserContext(filelike, self._context)
        result = file_context._readDoc(pctxt, self._parse_options)
        self._error_log.disconnect()
        recover = self._parse_options & xmlparser.XML_PARSE_RECOVER
        result = _handleParseResult(pctxt, result, c_filename, recover)
        return result

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

cdef BaseParser __DEFAULT_PARSER
__DEFAULT_PARSER = __DEFAULT_XML_PARSER

def set_default_parser(parser=None):
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
    elif isinstance(parser, (HTMLParser, XMLParser)):
        __DEFAULT_PARSER = parser
    else:
        raise TypeError, "Invalid parser"

def get_default_parser():
    return __DEFAULT_PARSER

############################################################
## HTML parser
############################################################

cdef int _HTML_DEFAULT_PARSE_OPTIONS
_HTML_DEFAULT_PARSE_OPTIONS = 0

cdef class HTMLParser(BaseParser):
    """The HTML parser.  This parser allows reading HTML into a normal XML
    tree.  By default, it can read broken (non well-formed) HTML, depending on
    the capabilities of libxml2.  Use the 'recover' option to switch this off.

    Available keyword arguments:
    * recover            - try hard to parse through broken HTML (default: True)
    * no_network         - prevent network access
    * remove_blank_text  - clean up empty text nodes

    Note that you must not share parsers between threads.
    """
    cdef int _parse_options
    cdef xmlParserCtxt* _memory_parser_ctxt
    cdef xmlParserCtxt* _file_parser_ctxt
    def __init__(self, recover=True, no_network=False, remove_blank_text=False):
        cdef int parse_options
        self._memory_parser_ctxt = NULL
        self._file_parser_ctxt   = NULL
        BaseParser.__init__(self)

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

    def __dealloc__(self):
        if self._file_parser_ctxt != NULL:
            htmlparser.htmlFreeParserCtxt(self._file_parser_ctxt)
        if self._memory_parser_ctxt != NULL:
            htmlparser.htmlFreeParserCtxt(self._memory_parser_ctxt)

    def copy(self):
        "Create a new parser with the same configuration."
        cdef HTMLParser parser
        parser = self._copy()
        parser._parse_options = self._parse_options
        return parser

    cdef xmlDoc* _parseDoc(self, char* c_text, char* c_filename) except NULL:
        """Parse HTML document, share dictionary if possible.
        """
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef int recover
        self._error_log.connect()
        pctxt = self._memory_parser_ctxt
        if pctxt is NULL:
            pctxt = htmlparser.htmlCreateMemoryParserCtxt('dummy', 5)
            if pctxt is NULL:
                self._error_log.disconnect()
                raise ParserError, "Failed to create parser context"
            self._memory_parser_ctxt = pctxt
        self._initContext(pctxt)
        result = htmlparser.htmlCtxtReadDoc(
            pctxt, c_text, c_filename, NULL, self._parse_options)
        self._error_log.disconnect()
        recover = self._parse_options & xmlparser.XML_PARSE_RECOVER
        return _handleParseResult(pctxt, result, NULL, recover)

    cdef xmlDoc* _parseDocFromFile(self, char* c_filename) except NULL:
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef int recover
        self._error_log.connect()
        pctxt = self._file_parser_ctxt
        if pctxt is NULL:
            pctxt = htmlparser.htmlCreateFileParserCtxt(c_filename, NULL)
            if pctxt is NULL:
                self._error_log.disconnect()
                warnings = self._error_log.filter_from_warnings()
                if warnings and warnings[-1].domain == xmlerror.XML_FROM_IO:
                    raise IOError, "Could not open file %s" % c_filename
                raise ParserError, "Failed to create parser context"
            self._file_parser_ctxt = pctxt
        self._initContext(pctxt)
        result = htmlparser.htmlCtxtReadFile(
            pctxt, c_filename, NULL, self._parse_options)
        self._error_log.disconnect()
        recover = self._parse_options & xmlparser.XML_PARSE_RECOVER
        return _handleParseResult(pctxt, result, c_filename, recover)

cdef HTMLParser __DEFAULT_HTML_PARSER
__DEFAULT_HTML_PARSER = HTMLParser()

############################################################
## helper functions for document creation
############################################################

cdef xmlDoc* _parseDoc(text_utf, filename, parser) except NULL:
    cdef char* c_filename
    if parser is None:
        parser = __DEFAULT_PARSER
    __GLOBAL_PARSER_CONTEXT._initParser()
    if not filename:
        c_filename = NULL
    else:
        c_filename = _cstr(filename)
    if isinstance(parser, XMLParser):
        return (<XMLParser>parser)._parseDoc(_cstr(text_utf), c_filename)
    elif isinstance(parser, HTMLParser):
        return (<HTMLParser>parser)._parseDoc(_cstr(text_utf), c_filename)
    else:
        raise TypeError, "invalid parser"

cdef xmlDoc* _parseDocFromFile(filename, parser) except NULL:
    if parser is None:
        parser = __DEFAULT_PARSER
    __GLOBAL_PARSER_CONTEXT._initParser()
    if isinstance(parser, XMLParser):
        return (<XMLParser>parser)._parseDocFromFile(_cstr(filename))
    elif isinstance(parser, HTMLParser):
        return (<HTMLParser>parser)._parseDocFromFile(_cstr(filename))
    else:
        raise TypeError, "invalid parser"

cdef xmlDoc* _parseDocFromFilelike(source, filename, parser) except NULL:
    cdef char* c_filename
    if parser is None:
        parser = __DEFAULT_PARSER
    __GLOBAL_PARSER_CONTEXT._initParser()
    if not filename:
        c_filename = NULL
    else:
        c_filename = _cstr(filename)
    if isinstance(parser, XMLParser):
        return (<XMLParser>parser)._parseDocFromFilelike(source, c_filename)
    elif isinstance(parser, HTMLParser):
        data_utf = _utf8(source.read())
        return (<HTMLParser>parser)._parseDoc(_cstr(data_utf), c_filename)
    else:
        raise TypeError, "invalid parser"

cdef xmlDoc* _newDoc():
    cdef xmlDoc* result
    result = tree.xmlNewDoc("1.0")
    __GLOBAL_PARSER_CONTEXT._initDocDict(result)
    return result

############################################################
## API level helper functions for _Document creation
## (here we convert to UTF-8)
############################################################

cdef _Document _parseDocument(source, parser):
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

cdef _Document _parseMemoryDocument(text, url, parser):
    cdef xmlDoc* c_doc
    text_utf = _utf8(text)
    if python.PyUnicode_Check(text):
        text_utf = _stripDeclaration(text_utf)
    if url is not None:
        url = _utf8(url)
    c_doc = _parseDoc(text_utf, url, parser)
    return _documentFactory(c_doc, parser)

cdef _Document _parseFilelikeDocument(source, url, parser):
    cdef xmlDoc* c_doc
    if url is not None:
        url = _utf8(url)
    c_doc = _parseDocFromFilelike(source, url, parser)
    return _documentFactory(c_doc, parser)
