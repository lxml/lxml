# XML parser that provides dictionary sharing

cimport xmlparser
from xmlparser cimport xmlParserCtxt, xmlDict

class XMLSyntaxError(LxmlSyntaxError):
    pass

cdef int _getParseOptions():
    return (xmlparser.XML_PARSE_NOENT | xmlparser.XML_PARSE_NOCDATA |
            xmlparser.XML_PARSE_NOWARNING | xmlparser.XML_PARSE_NOERROR)

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
        
    cdef xmlDoc* parseDoc(self, text) except NULL:
        """Parse document, share dictionary if possible.
        """
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef int parse_error
        self._initParse()
        pctxt = xmlparser.xmlCreateDocParserCtxt(text)
        if pctxt is NULL:
            raise XMLSyntaxError

        self._prepareParse(pctxt)
        xmlparser.xmlCtxtUseOptions(
            pctxt,
            _getParseOptions())
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

    cdef xmlDoc* parseDocFromFile(self, char* filename) except NULL:
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt

        self._initParse()
        pctxt = xmlparser.xmlNewParserCtxt()
        self._prepareParse(pctxt)
        # XXX set options twice? needed to shut up libxml2
        xmlparser.xmlCtxtUseOptions(pctxt, _getParseOptions())
        result = xmlparser.xmlCtxtReadFile(pctxt, filename,
                                           NULL, _getParseOptions())
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
