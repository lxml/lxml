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


cdef class BaseParser:
    cdef _ErrorLog _error_log
    def __init__(self):
        self._error_log = _ErrorLog()

    property error_log:
        def __get__(self):
            return self._error_log.copy()

    cdef xmlDoc* _handleResult(self, xmlParserCtxt* ctxt,
                               xmlDoc* result) except NULL:
        if ctxt.wellFormed:
            __GLOBAL_PARSER_CONTEXT._initDocDict(result)
        elif result is not NULL:
            # free broken document
            tree.xmlFreeDoc(result)
            result = NULL
        self._error_log.disconnect()
        if result is NULL:
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
                 no_network=False, ns_clean=False):
        cdef int parse_options
        self._file_parser_ctxt = NULL
        BaseParser.__init__(self)

        parse_options = _XML_DEFAULT_PARSE_OPTIONS
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

    cdef xmlParserCtxt* _createContext(self) except NULL:
        cdef xmlParserCtxt* pctxt
        pctxt = xmlparser.xmlNewParserCtxt()
        if pctxt is NULL:
            self._error_log.disconnect()
            raise ParserError, "Failed to create parser context"
        return pctxt

    cdef xmlDoc* _parseDoc(self, text_utf) except NULL:
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

        __GLOBAL_PARSER_CONTEXT._initParserDict(pctxt)
        result = xmlparser.xmlCtxtReadDoc(
            pctxt, _cstr(text_utf), NULL, NULL, self._parse_options)
        return self._handleResult(pctxt, result)

    cdef xmlDoc* _parseDocFromFile(self, char* filename) except NULL:
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        self._error_log.connect()
        pctxt = self._file_parser_ctxt
        if pctxt is NULL:
            pctxt = self._createContext()
            self._file_parser_ctxt = pctxt

        __GLOBAL_PARSER_CONTEXT._initParserDict(pctxt)
        result = xmlparser.xmlCtxtReadFile(
            pctxt, filename, NULL, self._parse_options)
        if result is NULL:
            if pctxt.lastError.domain == xmlerror.XML_FROM_IO:
                self._error_log.disconnect()
                raise IOError, "Could not open file %s" % filename
        return self._handleResult(pctxt, result)


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

    cdef xmlDoc* _parseDoc(self, text_utf) except NULL:
        """Parse HTML document, share dictionary if possible.
        """
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef char* c_text
        cdef int c_len
        self._error_log.connect()
        c_text = _cstr(text_utf)
        pctxt = self._memory_parser_ctxt
        if pctxt is NULL:
            pctxt = htmlparser.htmlCreateMemoryParserCtxt('dummy', 5)
            if pctxt is NULL:
                self._error_log.disconnect()
                raise ParserError, "Failed to create parser context"
            self._memory_parser_ctxt = pctxt
        __GLOBAL_PARSER_CONTEXT._initParserDict(pctxt)
        result = htmlparser.htmlCtxtReadDoc(
            pctxt, c_text, NULL, NULL, self._parse_options)
        return self._handleResult(pctxt, result)

    cdef xmlDoc* _parseDocFromFile(self, char* filename) except NULL:
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef int parser_error
        self._error_log.connect()
        pctxt = self._file_parser_ctxt
        if pctxt is NULL:
            pctxt = htmlparser.htmlCreateFileParserCtxt(filename, NULL)
            if pctxt is NULL:
                self._error_log.disconnect()
                warnings = self._error_log.filter_from_warnings()
                if warnings and warnings[-1].domain == xmlerror.XML_FROM_IO:
                    raise IOError, "Could not open file %s" % filename
                raise ParserError, "Failed to create parser context"
            self._file_parser_ctxt = pctxt
        __GLOBAL_PARSER_CONTEXT._initParserDict(pctxt)
        result = htmlparser.htmlCtxtReadFile(
            pctxt, filename, NULL, self._parse_options)
        return self._handleResult(pctxt, result)

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
        return (<XMLParser>parser)._parseDoc(text_utf)
    elif isinstance(parser, HTMLParser):
        return (<HTMLParser>parser)._parseDoc(text_utf)
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
