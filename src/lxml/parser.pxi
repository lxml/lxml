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
## support for custom document loaders
############################################################

cdef xmlparser.xmlParserInput* _local_resolver(char* c_url, char* c_pubid,
                                               xmlParserCtxt* c_context):
    cdef _ResolverContext context
    cdef _InputDocument   doc_ref
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
        data = doc_ref._file.read()
        c_input = xmlparser.xmlNewStringInputStream(
            c_context, _cstr(data))

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

cdef xmlDoc* _handleParseResult(xmlParserCtxt* ctxt, xmlDoc* result,
                                char* c_filename) except NULL:
    cdef _ResolverContext context
    if ctxt.wellFormed or (ctxt.options & xmlparser.XML_PARSE_RECOVER):
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
    return result

############################################################
## XML parser
############################################################

cdef int _XML_DEFAULT_PARSE_OPTIONS
_XML_DEFAULT_PARSE_OPTIONS = (
    xmlparser.XML_PARSE_NOENT |
    xmlparser.XML_PARSE_NOCDATA |
    xmlparser.XML_PARSE_NOWARNING |
    xmlparser.XML_PARSE_NOERROR
    )

cdef class XMLParser(BaseParser):
    """The XML parser.  Parsers can be supplied as additional argument to
    various parse functions of the lxml API.  A default parser is always
    available and can be replaced by a call to the global function
    'set_default_parser'.  New parsers can be created at any time without a
    major run-time overhead.

    The keyword arguments in the constructor are mainly based on the libxml2
    parser configuration.  A DTD will only be loaded if validation or
    attribute default values are requested.

    Note that you must not share parsers between threads.
    """
    cdef int _parse_options
    cdef xmlParserCtxt* _file_parser_ctxt
    cdef xmlParserCtxt* _memory_parser_ctxt
    def __init__(self, attribute_defaults=False, dtd_validation=False,
                 load_dtd=False, no_network=False, ns_clean=False):
        cdef int parse_options
        self._file_parser_ctxt = NULL
        BaseParser.__init__(self)

        parse_options = _XML_DEFAULT_PARSE_OPTIONS
        if load_dtd:
            parse_options = parse_options | xmlparser.XML_PARSE_DTDLOAD
        if dtd_validation:
            parse_options = parse_options | xmlparser.XML_PARSE_DTDLOAD | \
                            xmlparser.XML_PARSE_DTDVALID
        if attribute_defaults:
            parse_options = parse_options | xmlparser.XML_PARSE_DTDLOAD | \
                            xmlparser.XML_PARSE_DTDATTR
        if no_network:
            parse_options = parse_options | xmlparser.XML_PARSE_NONET
        if ns_clean:
            parse_options = parse_options | xmlparser.XML_PARSE_NSCLEAN

        self._parse_options = parse_options

    def __dealloc__(self):
        if self._file_parser_ctxt != NULL:
            xmlparser.xmlFreeParserCtxt(self._file_parser_ctxt)
        if self._memory_parser_ctxt != NULL:
            xmlparser.xmlFreeParserCtxt(self._memory_parser_ctxt)

    def copy(self):
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

    cdef xmlDoc* _parseDoc(self, char* c_text) except NULL:
        """Parse document, share dictionary if possible.
        """
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef int parse_error
        self._error_log.connect()
        pctxt = self._memory_parser_ctxt
        if pctxt is NULL:
            pctxt = self._createContext()
            self._memory_parser_ctxt = pctxt
        self._initContext(pctxt)
        result = xmlparser.xmlCtxtReadDoc(
            pctxt, c_text, NULL, NULL, self._parse_options)
        self._error_log.disconnect()
        return _handleParseResult(pctxt, result, NULL)

    cdef xmlDoc* _parseDocFromFile(self, char* c_filename) except NULL:
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        self._error_log.connect()
        pctxt = self._file_parser_ctxt
        if pctxt is NULL:
            pctxt = self._createContext()
            self._file_parser_ctxt = pctxt
        self._initContext(pctxt)
        result = xmlparser.xmlCtxtReadFile(
            pctxt, c_filename, NULL, self._parse_options)
        self._error_log.disconnect()
        return _handleParseResult(pctxt, result, c_filename)

cdef xmlDoc* _internalParseDoc(char* c_text, int options,
                               _ResolverContext context) except NULL:
    # internal parser function for XSLT
    cdef xmlParserCtxt* pctxt
    cdef xmlDoc* c_doc
    pctxt = xmlparser.xmlNewParserCtxt()
    if pctxt is NULL:
        return NULL
    __GLOBAL_PARSER_CONTEXT._initParserDict(pctxt)
    pctxt._private = <python.PyObject*>context
    c_doc = xmlparser.xmlCtxtReadDoc(
        pctxt, c_text, NULL, NULL, options)
    try:
        c_doc = _handleParseResult(pctxt, c_doc, NULL)
    finally:
        xmlparser.xmlFreeParserCtxt(pctxt)
    return c_doc

cdef xmlDoc* _internalParseDocFromFile(char* c_filename, int options,
                                       _ResolverContext context) except NULL:
    # internal parser function for XSLT
    cdef xmlParserCtxt* pctxt
    cdef xmlDoc* c_doc
    pctxt = xmlparser.xmlNewParserCtxt()
    if pctxt is NULL:
        return NULL
    __GLOBAL_PARSER_CONTEXT._initParserDict(pctxt)
    pctxt._private = <python.PyObject*>context
    c_doc = xmlparser.xmlCtxtReadFile(
        pctxt, c_filename, NULL, options)
    try:
        c_doc = _handleParseResult(pctxt, c_doc, c_filename)
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
_HTML_DEFAULT_PARSE_OPTIONS = (
    htmlparser.HTML_PARSE_NOWARNING |
    htmlparser.HTML_PARSE_NOERROR
    )

cdef class HTMLParser(BaseParser):
    """The HTML parser.  This parser allows reading HTML into a normal XML
    tree.  By default, it can read broken (non well-formed) HTML, depending on
    the capabilities of libxml2.  Use the 'recover' option to switch this off.

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
        cdef HTMLParser parser
        parser = self._copy()
        parser._parse_options = self._parse_options
        return parser

    cdef xmlDoc* _parseDoc(self, char* c_text) except NULL:
        """Parse HTML document, share dictionary if possible.
        """
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef int c_len
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
            pctxt, c_text, NULL, NULL, self._parse_options)
        self._error_log.disconnect()
        return _handleParseResult(pctxt, result, NULL)

    cdef xmlDoc* _parseDocFromFile(self, char* c_filename) except NULL:
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef int parser_error
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
        return _handleParseResult(pctxt, result, c_filename)

cdef HTMLParser __DEFAULT_HTML_PARSER
__DEFAULT_HTML_PARSER = HTMLParser()

############################################################
## helper functions for document creation
############################################################

cdef xmlDoc* _parseDoc(text_utf, parser) except NULL:
    if parser is None:
        parser = __DEFAULT_PARSER
    __GLOBAL_PARSER_CONTEXT._initParser()
    if isinstance(parser, XMLParser):
        return (<XMLParser>parser)._parseDoc(_cstr(text_utf))
    elif isinstance(parser, HTMLParser):
        return (<HTMLParser>parser)._parseDoc(_cstr(text_utf))
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

cdef xmlDoc* _newDoc():
    cdef xmlDoc* result
    result = tree.xmlNewDoc("1.0")
    __GLOBAL_PARSER_CONTEXT._initDocDict(result)
    return result

############################################################
## API level helper functions for _Document creation
############################################################

cdef _Document _parseDocument(source, parser):
    cdef xmlDoc* c_doc
    filename = _getFilenameForFile(source)
    # Support for unamed file-like object (StringIO, urlgrabber.urlopen, ...)
    if not filename and hasattr(source, 'read'):
        return _parseMemoryDocument(source.read(), parser)

    # Otherwise parse the file directly from the filesystem
    if filename is None:
        filename = source
    # open filename
    c_doc = _parseDocFromFile(_utf8(filename), parser)
    return _documentFactory(c_doc, parser)

cdef _Document _parseMemoryDocument(text, parser):
    cdef xmlDoc* c_doc
    if python.PyUnicode_Check(text):
        text = _stripDeclaration(_utf8(text))
    c_doc = _parseDoc(text, parser)
    return _documentFactory(c_doc, parser)

