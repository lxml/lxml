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
    LXML_ITERPARSE_PARSER

cdef class _ParserContext:
    # Global parser context to share the string dictionary.
    #
    # This class is a singleton!
    #
    # It creates _ParserContext objects for each thread to keep thread state,
    # but those must never be used directly.  Always stick to using the static
    # __GLOBAL_PARSER_CONTEXT as defined below the class.
    #

    cdef xmlDict* _c_dict
    cdef _BaseParser _default_parser
    def __dealloc__(self):
        if self._c_dict is not NULL:
            xmlparser.xmlDictFree(self._c_dict)

    cdef void initMainParserContext(self):
        """Put the global context into the thread dictionary of the main
        thread.  To be called once and only in the main thread."""
        cdef python.PyObject* thread_dict
        cdef python.PyObject* result
        thread_dict = python.PyThreadState_GetDict()
        if thread_dict is not NULL:
            python.PyDict_SetItem(<object>thread_dict, "_ParserContext", self)

    cdef _ParserContext _findThreadParserContext(self):
        "Find (or create) the _ParserContext object for the current thread"
        cdef python.PyObject* thread_dict
        cdef python.PyObject* result
        cdef _ParserContext context
        thread_dict = python.PyThreadState_GetDict()
        if thread_dict is NULL:
            return self
        d = <object>thread_dict
        result = python.PyDict_GetItem(d, "_ParserContext")
        if result is not NULL:
            return <object>result
        context = _ParserContext()
        python.PyDict_SetItem(d, "_ParserContext", context)
        return context

    cdef void setDefaultParser(self, _BaseParser parser):
        "Set the default parser for the current thread"
        cdef _ParserContext context
        context = self._findThreadParserContext()
        context._default_parser = parser

    cdef _BaseParser getDefaultParser(self):
        "Return (or create) the default parser of the current thread"
        cdef _ParserContext context
        context = self._findThreadParserContext()
        if context._default_parser is None:
            if self._default_parser is None:
                self._default_parser = __DEFAULT_XML_PARSER._copy()
            if context is not self:
                context._default_parser = self._default_parser._copy()
        return context._default_parser

    cdef xmlDict* _getThreadDict(self, xmlDict* default):
        "Return the thread-local dict or create a new one if necessary."
        cdef _ParserContext context
        context = self._findThreadParserContext()
        if context._c_dict is NULL:
            # thread dict not yet set up => use default or create a new one
            if default is not NULL:
                context._c_dict = default
                xmlparser.xmlDictReference(default)
                return default
            if self._c_dict is NULL:
                self._c_dict = xmlparser.xmlDictCreate()
            if context is not self:
                context._c_dict = xmlparser.xmlDictCreateSub(self._c_dict)
        return context._c_dict

    cdef void initThreadDictRef(self, xmlDict** c_dict_ref):
        cdef xmlDict* c_dict
        cdef xmlDict* c_thread_dict
        c_dict = c_dict_ref[0]
        c_thread_dict = self._getThreadDict(c_dict)
        if c_dict is c_thread_dict:
            return
        if c_dict is not NULL:
            xmlparser.xmlDictFree(c_dict)
        c_dict_ref[0] = c_thread_dict
        xmlparser.xmlDictReference(c_thread_dict)

    cdef void initParserDict(self, xmlParserCtxt* pctxt):
        "Assure we always use the same string dictionary."
        self.initThreadDictRef(&pctxt.dict)

    cdef void initXPathParserDict(self, xpath.xmlXPathContext* pctxt):
        "Assure we always use the same string dictionary."
        self.initThreadDictRef(&pctxt.dict)

    cdef void initDocDict(self, xmlDoc* result):
        "Store dict of last object parsed if no shared dict yet"
        # XXX We also free the result dict here if there already was one.
        # This case should only occur for new documents with empty dicts,
        # otherwise we'd free data that's in use => segfault
        self.initThreadDictRef(&result.dict)

cdef _ParserContext __GLOBAL_PARSER_CONTEXT
__GLOBAL_PARSER_CONTEXT = _ParserContext()
__GLOBAL_PARSER_CONTEXT.initMainParserContext()

cdef int _checkThreadDict(xmlDict* c_dict):
    """Check that c_dict is either the local thread dictionary or the global
    parent dictionary.
    """
    if __GLOBAL_PARSER_CONTEXT._c_dict is c_dict:
        return 1 # main thread
    if __GLOBAL_PARSER_CONTEXT._getThreadDict(NULL) is c_dict:
        return 1 # local thread dict
    return 0

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
    cdef object _bytes
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
        self._bytes  = ''
        self._bytes_read = 0

    cdef xmlparser.xmlParserInput* _createParserInput(self, xmlParserCtxt* ctxt):
        cdef xmlparser.xmlParserInputBuffer* c_buffer
        c_buffer = xmlparser.xmlAllocParserInputBuffer(0)
        c_buffer.context = <python.PyObject*>self
        c_buffer.readcallback = _readFilelikeParser
        return xmlparser.xmlNewIOInputStream(ctxt, c_buffer, 0)

    cdef xmlDoc* _readDoc(self, xmlParserCtxt* ctxt, int options,
                          LxmlParserType parser_type):
        cdef python.PyThreadState* state
        cdef xmlDoc* result
        state = python.PyEval_SaveThread()
        if parser_type == LXML_XML_PARSER:
            result = xmlparser.xmlCtxtReadIO(
                ctxt, _readFilelikeParser, NULL, <python.PyObject*>self,
                self._c_url, NULL, options)
        else:
            result = htmlparser.htmlCtxtReadIO(
                ctxt, _readFilelikeParser, NULL, <python.PyObject*>self,
                self._c_url, NULL, options)
        python.PyEval_RestoreThread(state)
        return result

    cdef int copyToBuffer(self, char* c_buffer, int c_size):
        cdef char* c_start
        cdef Py_ssize_t byte_count, remaining
        cdef python.PyGILState_STATE gil_state
        if self._bytes_read < 0:
            return 0
        gil_state = python.PyGILState_Ensure()
        try:
            byte_count = python.PyString_GET_SIZE(self._bytes)
            remaining = byte_count - self._bytes_read
            if remaining <= 0:
                self._bytes = self._filelike.read(c_size)
                if not python.PyString_Check(self._bytes):
                    raise TypeError, "reading file objects must return plain strings"
                remaining = python.PyString_GET_SIZE(self._bytes)
                self._bytes_read = 0
                if remaining == 0:
                    self._bytes_read = -1
                    python.PyGILState_Release(gil_state)
                    return 0
            if c_size > remaining:
                c_size = remaining
            c_start = _cstr(self._bytes) + self._bytes_read
            python.PyGILState_Release(gil_state)
            self._bytes_read = self._bytes_read + c_size
            cstd.memcpy(c_buffer, c_start, c_size)
            return c_size
        except:
            self._exc_context._store_raised()
            python.PyGILState_Release(gil_state)
            return -1

cdef int _readFilelikeParser(void* ctxt, char* c_buffer, int c_size):
    return (<_FileParserContext>ctxt).copyToBuffer(c_buffer, c_size)

############################################################
## support for custom document loaders
############################################################

cdef  xmlparser.xmlParserInput* _parser_resolve_from_python(
    char* c_url, char* c_pubid, xmlParserCtxt* c_context, int* error):
    # call the Python document loaders
    cdef xmlparser.xmlParserInput* c_input
    cdef _ResolverContext context
    cdef _InputDocument   doc_ref
    cdef _FileParserContext file_context
    error[0] = 0
    context = <_ResolverContext>c_context._private
    try:
        if c_url is NULL:
            url = None
        elif c_context.myDoc is NULL or c_context.myDoc.URL is NULL:
            # parsing a main document, so URL was passed verbatimly by user
            url = c_url
        else:
            # parsing a related document (DTD etc.) => UTF-8 encoded URL
            url = funicode(c_url)
        if c_pubid is NULL:
            pubid = None
        else:
            pubid = funicode(c_pubid) # always UTF-8

        doc_ref = context._resolvers.resolve(url, pubid, context)
        if doc_ref is None:
            return NULL
    except:
        context._store_raised()
        error[0] = 1
        return NULL

    c_input = NULL
    data = None
    if doc_ref._type == PARSER_DATA_STRING:
        data = doc_ref._data_bytes
        c_input = xmlparser.xmlNewStringInputStream(
            c_context, _cstr(data))
    elif doc_ref._type == PARSER_DATA_FILENAME:
        c_input = xmlparser.xmlNewInputFromFile(
            c_context, _cstr(doc_ref._data_bytes))
    elif doc_ref._type == PARSER_DATA_FILE:
        file_context = _FileParserContext(doc_ref._file, context, url)
        c_input = file_context._createParserInput(c_context)
        data = file_context

    if data is not None:
        context._storage.add(data)
    return c_input

cdef xmlparser.xmlParserInput* _local_resolver(char* c_url, char* c_pubid,
                                               xmlParserCtxt* c_context):
    # no Python objects here, may be called without thread context !
    # when we declare a Python object, Pyrex will INCREF(None) !
    cdef xmlparser.xmlParserInput* c_input
    cdef python.PyGILState_STATE gil_state
    cdef int error
    if c_context._private is NULL:
        if __DEFAULT_ENTITY_LOADER is NULL:
            return NULL
        return __DEFAULT_ENTITY_LOADER(c_url, c_pubid, c_context)

    gil_state = python.PyGILState_Ensure()
    c_input = _parser_resolve_from_python(c_url, c_pubid, c_context, &error)
    python.PyGILState_Release(gil_state)

    if c_input is not NULL:
        return c_input
    if error:
        return NULL
    if __DEFAULT_ENTITY_LOADER is NULL:
        return NULL
    return __DEFAULT_ENTITY_LOADER(c_url, c_pubid, c_context)

cdef xmlparser.xmlExternalEntityLoader __DEFAULT_ENTITY_LOADER
__DEFAULT_ENTITY_LOADER = xmlparser.xmlGetExternalEntityLoader()

xmlparser.xmlSetExternalEntityLoader(_local_resolver)

############################################################
## Parsers
############################################################

cdef class _BaseParser:
    cdef int _parse_options
    cdef _ErrorLog _error_log
    cdef readonly _ResolverRegistry resolvers
    cdef _ResolverContext _context
    cdef LxmlParserType _parser_type
    cdef xmlParserCtxt* _parser_ctxt
    cdef ElementClassLookup _class_lookup
    cdef object _lockParser
    cdef object _unlockParser

    def __init__(self, context_class=_ResolverContext):
        cdef xmlParserCtxt* pctxt
        if isinstance(self, HTMLParser):
            self._parser_type = LXML_HTML_PARSER
            pctxt = htmlparser.htmlCreateMemoryParserCtxt('dummy', 5)
        elif isinstance(self, XMLParser):
            self._parser_type = LXML_XML_PARSER
            pctxt = xmlparser.xmlNewParserCtxt()
        elif isinstance(self, iterparse):
            self._parser_type = LXML_ITERPARSE_PARSER
            pctxt = xmlparser.xmlNewParserCtxt()
        else:
            raise TypeError, "This class cannot be instantiated"
        self._parser_ctxt = pctxt
        if pctxt is NULL:
            raise ParserError, "Failed to create parser context"
        if pctxt.sax != NULL:
            # hard switch-off for CDATA nodes => makes them plain text
            pctxt.sax.cdataBlock = NULL
        if thread is None or self._parser_type == LXML_ITERPARSE_PARSER:
            # no threading
            self._lockParser   = self.__dummy
            self._unlockParser = self.__dummy
        else:
            lock = thread.allocate_lock()
            self._lockParser   = lock.acquire
            self._unlockParser = lock.release
        self._error_log = _ErrorLog()
        self.resolvers  = _ResolverRegistry()
        self._context = context_class(self.resolvers)
        pctxt._private = <python.PyObject*>self._context

    def __dealloc__(self):
        if self._parser_ctxt is not NULL:
            xmlparser.xmlFreeParserCtxt(self._parser_ctxt)

    property error_log:
        def __get__(self):
            return self._error_log.copy()

    def __dummy(self):
        pass

    def setElementClassLookup(self, ElementClassLookup lookup = None):
        """Set a lookup scheme for element classes generated from this parser.

        Reset it by passing None or nothing.
        """
        self._class_lookup = lookup

    cdef _BaseParser _copy(self):
        "Create a new parser with the same configuration."
        cdef _BaseParser parser
        parser = self.__class__()
        parser._parse_options = self._parse_options
        parser._class_lookup  = self._class_lookup
        parser.resolvers = self.resolvers._copy()
        parser._context = _ResolverContext(parser.resolvers)
        parser._parser_ctxt._private = <python.PyObject*>parser._context
        return parser

    def copy(self):
        "Create a new parser with the same configuration."
        return self._copy()

    def makeelement(self, _tag, attrib=None, nsmap=None, **_extra):
        """Creates a new element associated with this parser.
        """
        return _makeElement(_tag, NULL, None, self, attrib, nsmap, _extra)

    cdef xmlDoc* _parseUnicodeDoc(self, utext, char* c_filename) except NULL:
        """Parse unicode document, share dictionary if possible.
        """
        cdef python.PyThreadState* state
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

        self._lockParser()
        self._error_log.connect()
        try:
            pctxt = self._parser_ctxt
            __GLOBAL_PARSER_CONTEXT.initParserDict(pctxt)

            c_text = python.PyUnicode_AS_DATA(utext)
            state = python.PyEval_SaveThread()
            if self._parser_type == LXML_HTML_PARSER:
                result = htmlparser.htmlCtxtReadMemory(
                    pctxt, c_text, buffer_len, c_filename, _UNICODE_ENCODING,
                    self._parse_options)
            else:
                result = xmlparser.xmlCtxtReadMemory(
                    pctxt, c_text, buffer_len, c_filename, _UNICODE_ENCODING,
                    self._parse_options)
            python.PyEval_RestoreThread(state)

            recover = self._parse_options & xmlparser.XML_PARSE_RECOVER
            return _handleParseResult(pctxt, result, None, recover)
        finally:
            self._error_log.disconnect()
            self._unlockParser()

    cdef xmlDoc* _parseDoc(self, char* c_text, Py_ssize_t c_len,
                           char* c_filename) except NULL:
        """Parse document, share dictionary if possible.
        """
        cdef python.PyThreadState* state
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef int recover
        if c_len > python.INT_MAX:
            raise ParserError, "string is too long to parse it with libxml2"
        self._lockParser()
        self._error_log.connect()
        try:
            pctxt = self._parser_ctxt
            __GLOBAL_PARSER_CONTEXT.initParserDict(pctxt)

            state = python.PyEval_SaveThread()
            if self._parser_type == LXML_HTML_PARSER:
                result = htmlparser.htmlCtxtReadMemory(
                    pctxt, c_text, c_len, c_filename, NULL, self._parse_options)
            else:
                result = xmlparser.xmlCtxtReadMemory(
                    pctxt, c_text, c_len, c_filename, NULL, self._parse_options)
            python.PyEval_RestoreThread(state)

            recover = self._parse_options & xmlparser.XML_PARSE_RECOVER
            return _handleParseResult(pctxt, result, None, recover)
        finally:
            self._error_log.disconnect()
            self._unlockParser()

    cdef xmlDoc* _parseDocFromFile(self, char* c_filename) except NULL:
        cdef python.PyThreadState* state
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef int recover
        result = NULL
        self._lockParser()
        self._error_log.connect()
        try:
            pctxt = self._parser_ctxt
            __GLOBAL_PARSER_CONTEXT.initParserDict(pctxt)

            state = python.PyEval_SaveThread()
            if self._parser_type == LXML_HTML_PARSER:
                result = htmlparser.htmlCtxtReadFile(
                    pctxt, c_filename, NULL, self._parse_options)
            else:
                result = xmlparser.xmlCtxtReadFile(
                    pctxt, c_filename, NULL, self._parse_options)
            python.PyEval_RestoreThread(state)

            recover = self._parse_options & xmlparser.XML_PARSE_RECOVER
            return _handleParseResult(pctxt, result, c_filename, recover)
        finally:
            self._error_log.disconnect()
            self._unlockParser()

    cdef xmlDoc* _parseDocFromFilelike(self, filelike, filename) except NULL:
        cdef _FileParserContext file_context
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef char* c_filename
        cdef int recover
        if not filename:
            filename = None
        self._lockParser()
        self._error_log.connect()
        try:
            pctxt = self._parser_ctxt
            __GLOBAL_PARSER_CONTEXT.initParserDict(pctxt)
            file_context = _FileParserContext(filelike, self._context, filename)
            result = file_context._readDoc(
                pctxt, self._parse_options, self._parser_type)

            recover = self._parse_options & xmlparser.XML_PARSE_RECOVER
            return _handleParseResult(pctxt, result, filename, recover)
        finally:
            self._error_log.disconnect()
            self._unlockParser()

cdef int _raiseParseError(xmlParserCtxt* ctxt, filename) except 0:
    if filename is not None and \
           ctxt.lastError.domain == xmlerror.XML_FROM_IO:
        if ctxt.lastError.message is not NULL:
            message = "Error reading file '%s': %s" % (
                filename, (ctxt.lastError.message).strip())
        else:
            message = "Error reading file '%s'" % filename
        raise IOError, message
    elif ctxt.lastError.message is not NULL:
        message = (ctxt.lastError.message).strip()
        if ctxt.lastError.line >= 0:
            message = "line %d: %s" % (ctxt.lastError.line, message)
        raise XMLSyntaxError, message
    else:
        raise XMLSyntaxError

cdef xmlDoc* _handleParseResult(xmlParserCtxt* ctxt, xmlDoc* result,
                                filename, int recover) except NULL:
    cdef _ResolverContext context
    if ctxt.myDoc is not NULL:
        if ctxt.myDoc != result:
            tree.xmlFreeDoc(ctxt.myDoc)
        ctxt.myDoc = NULL

    if result is not NULL:
        if ctxt.wellFormed or recover:
            __GLOBAL_PARSER_CONTEXT.initDocDict(result)
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
        _raiseParseError(ctxt, filename)
    elif result.URL is NULL and filename is not None:
        result.URL = tree.xmlStrdup(_cstr(filename))
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

    Available boolean keyword arguments:
    * attribute_defaults - read default attributes from DTD
    * dtd_validation     - validate (if DTD is available)
    * load_dtd           - use DTD for parsing
    * no_network         - prevent network access
    * ns_clean           - clean up redundant namespace declarations
    * recover            - try hard to parse through broken XML
    * remove_blank_text  - discard blank text nodes

    For read-only documents that will not be altered after parsing, you can
    also pass the following keyword arguments:
    * compact            - compactly store short element text content

    Note that you should avoid sharing parsers between threads.  This does not
    apply to the default parser.

    You must not modify documents that were parsed with the 'compact' option.
    """
    def __init__(self, attribute_defaults=False, dtd_validation=False,
                 load_dtd=False, no_network=False, ns_clean=False,
                 recover=False, remove_blank_text=False, compact=False):
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
        if compact:
            parse_options = parse_options | xmlparser.XML_PARSE_COMPACT

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
    __GLOBAL_PARSER_CONTEXT.initParserDict(pctxt)
    pctxt._private = <python.PyObject*>context
    c_doc = xmlparser.xmlCtxtReadDoc(
        pctxt, c_text, NULL, NULL, options)
    try:
        recover = options & xmlparser.XML_PARSE_RECOVER
        c_doc = _handleParseResult(pctxt, c_doc, None, recover)
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
    __GLOBAL_PARSER_CONTEXT.initParserDict(pctxt)
    pctxt._private = <python.PyObject*>context
    c_doc = xmlparser.xmlCtxtReadFile(
        pctxt, c_filename, NULL, options)
    try:
        recover = options & xmlparser.XML_PARSE_RECOVER
        if c_filename is NULL:
            filename = None
        else:
            filename = c_filename
        c_doc = _handleParseResult(pctxt, c_doc, filename, recover)
    finally:
        xmlparser.xmlFreeParserCtxt(pctxt)
    return c_doc


cdef XMLParser __DEFAULT_XML_PARSER
__DEFAULT_XML_PARSER = XMLParser()

__GLOBAL_PARSER_CONTEXT.setDefaultParser(__DEFAULT_XML_PARSER)

def setDefaultParser(_BaseParser parser=None):
    """Set a default parser for the current thread.  This parser is used
    globally whenever no parser is supplied to the various parse functions of
    the lxml API.  If this function is called without a parser (or if it is
    None), the default parser is reset to the original configuration.

    Note that the pre-installed default parser is not thread-safe.  Avoid the
    default parser in multi-threaded environments.  You can create a separate
    parser for each thread explicitly or use a parser pool.
    """
    if parser is None:
        parser = __DEFAULT_XML_PARSER
    __GLOBAL_PARSER_CONTEXT.setDefaultParser(parser)

def getDefaultParser():
    return __GLOBAL_PARSER_CONTEXT.getDefaultParser()

def set_default_parser(parser):
    "Deprecated, please use setDefaultParser instead."
    setDefaultParser(parser)

def get_default_parser():
    "Deprecated, please use getDefaultParser instead."
    return getDefaultParser()

############################################################
## HTML parser
############################################################

cdef int _HTML_DEFAULT_PARSE_OPTIONS
_HTML_DEFAULT_PARSE_OPTIONS = 0

cdef class HTMLParser(_BaseParser):
    """The HTML parser.  This parser allows reading HTML into a normal XML
    tree.  By default, it can read broken (non well-formed) HTML, depending on
    the capabilities of libxml2.  Use the 'recover' option to switch this off.

    Available boolean keyword arguments:
    * recover            - try hard to parse through broken HTML (default: True)
    * no_network         - prevent network access
    * remove_blank_text  - discard empty text nodes

    For read-only documents that will not be altered after parsing, you can
    also pass the following keyword arguments:
    * compact            - compactly store short element text content

    Note that you should avoid sharing parsers between threads.  You must not
    modify documents that were parsed with the 'compact' option.
    """
    def __init__(self, recover=True, no_network=False, remove_blank_text=False,
                 compact=False):
        cdef int parse_options
        _BaseParser.__init__(self)

        parse_options = _HTML_DEFAULT_PARSE_OPTIONS
        if recover:
            parse_options = parse_options | htmlparser.HTML_PARSE_RECOVER
        if no_network:
            parse_options = parse_options | htmlparser.HTML_PARSE_NONET
        if remove_blank_text:
            parse_options = parse_options | htmlparser.HTML_PARSE_NOBLANKS
        if compact:
            parse_options = parse_options | htmlparser.HTML_PARSE_COMPACT

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
        parser = __GLOBAL_PARSER_CONTEXT.getDefaultParser()
    if not filename:
        c_filename = NULL
    else:
        filename_utf = _encodeFilenameUTF8(filename)
        c_filename = _cstr(filename_utf)
    if python.PyUnicode_Check(text):
        return (<_BaseParser>parser)._parseUnicodeDoc(text, c_filename)
    else:
        c_text = _cstr(text)
        c_len  = python.PyString_GET_SIZE(text)
        return (<_BaseParser>parser)._parseDoc(c_text, c_len, c_filename)

cdef xmlDoc* _parseDocFromFile(filename8, _BaseParser parser) except NULL:
    if parser is None:
        parser = __GLOBAL_PARSER_CONTEXT.getDefaultParser()
    return (<_BaseParser>parser)._parseDocFromFile(_cstr(filename8))

cdef xmlDoc* _parseDocFromFilelike(source, filename,
                                   _BaseParser parser) except NULL:
    if parser is None:
        parser = __GLOBAL_PARSER_CONTEXT.getDefaultParser()
    return (<_BaseParser>parser)._parseDocFromFilelike(source, filename)

cdef xmlDoc* _newDoc():
    cdef xmlDoc* result
    result = tree.xmlNewDoc("1.0")
    __GLOBAL_PARSER_CONTEXT.initDocDict(result)
    return result

cdef xmlDoc* _copyDoc(xmlDoc* c_doc, int recursive):
    cdef python.PyThreadState* state
    cdef xmlDoc* result
    if recursive:
        state = python.PyEval_SaveThread()
    result = tree.xmlCopyDoc(c_doc, recursive)
    _bugFixURL(c_doc, result)
    if recursive:
        python.PyEval_RestoreThread(state)
    __GLOBAL_PARSER_CONTEXT.initDocDict(result)
    return result

cdef xmlDoc* _copyDocRoot(xmlDoc* c_doc, xmlNode* c_new_root):
    "Recursively copy the document and make c_new_root the new root node."
    cdef python.PyThreadState* state
    cdef xmlDoc* result
    cdef xmlNode* c_node
    result = tree.xmlCopyDoc(c_doc, 0) # non recursive
    _bugFixURL(c_doc, result)
    __GLOBAL_PARSER_CONTEXT.initDocDict(result)
    state = python.PyEval_SaveThread()
    c_node = tree.xmlDocCopyNode(c_new_root, result, 1) # recursive
    tree.xmlDocSetRootElement(result, c_node)
    _copyTail(c_new_root.next, c_node)
    python.PyEval_RestoreThread(state)
    return result

cdef xmlNode* _copyNodeToDoc(xmlNode* c_node, xmlDoc* c_doc):
    "Recursively copy the element into the document. c_doc is not modified."
    cdef xmlNode* c_root
    c_root = tree.xmlDocCopyNode(c_node, c_doc, 1) # recursive
    _copyTail(c_node.next, c_root)
    return c_root

cdef void _bugFixURL(xmlDoc* c_source_doc, xmlDoc* c_target_doc):
    """libxml2 <= 2.6.17 had a bug that prevented it from copying the document
    URL in xmlDocCopy()"""
    if c_source_doc.URL is not NULL and _LIBXML_VERSION_INT < 20618:
        if c_target_doc.URL is not NULL:
            tree.xmlFree(c_target_doc.URL)
        c_target_doc.URL = tree.xmlStrdup(c_source_doc.URL)


############################################################
## API level helper functions for _Document creation
## (here we convert to UTF-8)
############################################################

cdef _Document _parseDocument(source, _BaseParser parser):
    filename = _getFilenameForFile(source)
    if hasattr(source, 'getvalue') and hasattr(source, 'tell'):
        # StringIO - reading from start?
        if source.tell() == 0:
            return _parseMemoryDocument(
                source.getvalue(), _encodeFilenameUTF8(filename), parser)

    # Support for file-like objects (urlgrabber.urlopen, ...)
    if hasattr(source, 'read'):
        return _parseFilelikeDocument(
            source, _encodeFilenameUTF8(filename), parser)

    # Otherwise parse the file directly from the filesystem
    if filename is None:
        filename = _encodeFilename(source)
    # open filename
    return _parseDocumentFromURL(filename, parser)

cdef _Document _parseDocumentFromURL(url, _BaseParser parser):
    cdef xmlDoc* c_doc
    c_doc = _parseDocFromFile(url, parser)
    return _documentFactory(c_doc, parser)

cdef _Document _parseMemoryDocument(text, url, _BaseParser parser):
    cdef xmlDoc* c_doc
    if python.PyUnicode_Check(text):
        if _hasEncodingDeclaration(text):
            raise ValueError, \
                  "Unicode strings with encoding declaration are not supported."
        # pass native unicode only if libxml2 can handle it
        if _UNICODE_ENCODING is NULL:
            text = python.PyUnicode_AsUTF8String(text)
    elif not python.PyString_Check(text):
        raise ValueError, "can only parse strings"
    if python.PyUnicode_Check(url):
        url = python.PyUnicode_AsUTF8String(url)
    c_doc = _parseDoc(text, url, parser)
    return _documentFactory(c_doc, parser)

cdef _Document _parseFilelikeDocument(source, url, _BaseParser parser):
    cdef xmlDoc* c_doc
    if python.PyUnicode_Check(url):
        url = python.PyUnicode_AsUTF8String(url)
    c_doc = _parseDocFromFilelike(source, url, parser)
    return _documentFactory(c_doc, parser)
