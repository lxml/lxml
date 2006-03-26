# XML parser that provides dictionary sharing

cimport xmlparser
from xmlparser cimport xmlParserCtxt, xmlDict

class XMLSyntaxError(LxmlSyntaxError):
    pass

cdef int _DEFAULT_PARSE_OPTIONS
_DEFAULT_PARSE_OPTIONS = (
    xmlparser.XML_PARSE_NOENT |
    xmlparser.XML_PARSE_NOCDATA |
    xmlparser.XML_PARSE_NOWARNING |
    xmlparser.XML_PARSE_NOERROR
    )

cdef int _ORIG_DEFAULT_PARSE_OPTIONS
_ORIG_DEFAULT_PARSE_OPTIONS = _DEFAULT_PARSE_OPTIONS


cdef class XMLParser:
    """The XML parser.  Parsers can be supplied as additional argument to
    various parse functions of the lxml API.  A default parser is always
    available and can be replaced by a call to the global function
    'set_default_parser'.  New parsers can be created at any time without a
    major run-time overhead.

    The keyword arguments in the constructor are mainly based on the libxml2
    parser configuration.  A DTD will only be loaded if validation or
    attribute default values are requested.
    """
    cdef int _parse_options
    def __init__(self, attribute_defaults=False, dtd_validation=False,
                 no_network=False, ns_clean=False):
        cdef int parse_options
        parse_options = _ORIG_DEFAULT_PARSE_OPTIONS

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

    property error_log:
        def __get__(self):
            return __build_error_log_tuple(self)

##     def copy(self, attribute_defaults=None, dtd_validation=None,
##              no_network=None, ns_clean=None):
##         cdef int parse_options
##         parse_options = self._parse_options
##         if attribute_defaults is None:
##             attribute_defaults = parse_options & xmlparser.XML_PARSE_DTDATTR
##         if dtd_validation is None:
##             dtd_validation = parse_options & xmlparser.XML_PARSE_DTDVALID
##         if no_network is None:
##             no_network = parse_options & xmlparser.XML_PARSE_NONET
##         if ns_clean is None:
##             ns_clean = parse_options & xmlparser.XML_PARSE_NSCLEAN

##         return self.__class__(attribute_defaults=attribute_defaults,
##                               dtd_validation=dtd_validation,
##                               no_network=no_network, ns_clean=ns_clean)


def set_default_parser(parser=None):
    """Set a default XMLParser.  This parser is used globally whenever no
    parser is supplied to the various parse functions of the lxml API.  If
    this function is called without a parser (or if it is None), the default
    parser is reset to the original configuration.
    """
    if parser is not None:
        _DEFAULT_PARSE_OPTIONS = (<XMLParser>parser)._parse_options
    else:
        _DEFAULT_PARSE_OPTIONS = _ORIG_DEFAULT_PARSE_OPTIONS


cdef class Parser:

    cdef xmlDict* _c_dict
    cdef int _parser_initialized
    
    def __init__(self):
        self._c_dict = NULL
        self._parser_initialized = 0
        
    def __dealloc__(self):
        #print "cleanup parser"
        if self._c_dict is not NULL:
            #print "freeing dictionary (cleanup parser)"
            xmlparser.xmlDictFree(self._c_dict)
        
    cdef xmlDoc* parseDoc(self, text, parser) except NULL:
        """Parse document, share dictionary if possible.
        """
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef int parse_error

        if parser is not None:
            parse_options = (<XMLParser>parser)._parse_options
        else:
            parse_options = _DEFAULT_PARSE_OPTIONS

        self._initParse()
        pctxt = xmlparser.xmlCreateDocParserCtxt(_cstr(text))
        if pctxt is NULL:
            raise XMLSyntaxError

        self._prepareParse(pctxt)
        xmlparser.xmlCtxtUseOptions(
            pctxt,
            parse_options)
        parse_error = xmlparser.xmlParseDocument(pctxt)
        # in case of errors, clean up context plus any document
        if parse_error != 0 or not pctxt.wellFormed:
            if pctxt.myDoc is not NULL:
                tree.xmlFreeDoc(pctxt.myDoc)
                pctxt.myDoc = NULL
            xmlparser.xmlFreeParserCtxt(pctxt)
            raise XMLSyntaxError
        result = pctxt.myDoc
        self._finalizeParse(result)
        xmlparser.xmlFreeParserCtxt(pctxt)
        return result

    cdef xmlDoc* parseDocFromFile(self, char* filename, parser) except NULL:
        cdef int parse_options
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt

        if parser is not None:
            parse_options = (<XMLParser>parser)._parse_options
        else:
            parse_options = _DEFAULT_PARSE_OPTIONS

        self._initParse()
        pctxt = xmlparser.xmlNewParserCtxt()
        self._prepareParse(pctxt)
        # XXX set options twice? needed to shut up libxml2
        xmlparser.xmlCtxtUseOptions(pctxt, parse_options)
        result = xmlparser.xmlCtxtReadFile(pctxt, filename,
                                           NULL, parse_options)
        if result is NULL:
            if pctxt.lastError.domain == xmlerror.XML_FROM_IO:
                raise IOError, "Could not open file %s" % filename
        # in case of errors, clean up context plus any document
        # XXX other errors?
        if not pctxt.wellFormed:
            if pctxt.myDoc is not NULL:
                tree.xmlFreeDoc(pctxt.myDoc)
                pctxt.myDoc = NULL
            xmlparser.xmlFreeParserCtxt(pctxt)
            raise XMLSyntaxError
        self._finalizeParse(result)
        xmlparser.xmlFreeParserCtxt(pctxt)
        return result
    
    cdef void _initParse(self):
        if not self._parser_initialized:
            xmlparser.xmlInitParser()
            self._parser_initialized = 1
            
    cdef void _prepareParse(self, xmlParserCtxt* pctxt):
        if self._c_dict is not NULL and pctxt.dict is not NULL:
            #print "sharing dictionary (parseDoc)"
            xmlparser.xmlDictFree(pctxt.dict)
            pctxt.dict = self._c_dict
            xmlparser.xmlDictReference(pctxt.dict)

    cdef void _finalizeParse(self, xmlDoc* result):
        # store dict of last object parsed if no shared dict yet
        if self._c_dict is NULL:
            #print "storing shared dict"
            self._c_dict = result.dict
        xmlparser.xmlDictReference(self._c_dict)
    
    cdef xmlDoc* newDoc(self):
        cdef xmlDoc* result
        cdef xmlDict* d

        result = tree.xmlNewDoc("1.0")

        if self._c_dict is NULL:
            # we need to get dict from the new document if it's there,
            # otherwise make one
            if result.dict is not NULL:
                d = result.dict
            else:
                d = xmlparser.xmlDictCreate()
                result.dict = d
            self._c_dict = d
            xmlparser.xmlDictReference(self._c_dict)
        else:
            # we need to reuse the central dict and get rid of the new one
            if result.dict is not NULL:
                xmlparser.xmlDictFree(result.dict)
            result.dict = self._c_dict
            xmlparser.xmlDictReference(result.dict)
        return result
