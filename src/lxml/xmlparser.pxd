from tree cimport xmlDoc, xmlDict
from xmlerror cimport xmlError

cdef extern from "libxml/parser.h":
    
    cdef xmlDict xmlDictFree(xmlDict* sub)
    cdef int xmlDictReference(xmlDict* dict)
    
    ctypedef struct xmlParserCtxt:
        xmlDoc* myDoc
        xmlDict* dict
        int wellFormed
        xmlError lastError
        
    ctypedef enum xmlParserOption:
        XML_PARSE_RECOVER = 1 # recover on errors
        XML_PARSE_NOENT = 2 # substitute entities
        XML_PARSE_DTDLOAD = 4 # load the external subset
        XML_PARSE_DTDATTR = 8 # default DTD attributes
        XML_PARSE_DTDVALID = 16 # validate with the DTD
        XML_PARSE_NOERROR = 32 # suppress error reports
        XML_PARSE_NOWARNING = 64 # suppress warning reports
        XML_PARSE_PEDANTIC = 128 # pedantic error reporting
        XML_PARSE_NOBLANKS = 256 # remove blank nodes
        XML_PARSE_SAX1 = 512 # use the SAX1 interface internally
        XML_PARSE_XINCLUDE = 1024 # Implement XInclude substitition
        XML_PARSE_NONET = 2048 # Forbid network access
        XML_PARSE_NODICT = 4096 # Do not reuse the context dictionnary
        XML_PARSE_NSCLEAN = 8192 # remove redundant namespaces declarations
        XML_PARSE_NOCDATA = 16384 # merge CDATA as text nodes
        XML_PARSE_NOXINCNODE = 32768 # do not generate XINCLUDE START/END nodes
       
    cdef void xmlInitParser()
    cdef xmlParserCtxt* xmlCreateDocParserCtxt(char* cur)
    cdef xmlParserCtxt* xmlNewParserCtxt()
    cdef void xmlFreeParserCtxt(xmlParserCtxt* ctxt)
 
    cdef int xmlCtxtUseOptions(xmlParserCtxt* ctxt, int options)
    cdef int xmlParseDocument(xmlParserCtxt* ctxt)
    cdef xmlDoc* xmlParseDoc(char* cur)
    cdef xmlDoc* xmlCtxtReadFile(xmlParserCtxt* ctxt,
                                 char* filename, char* encoding, int options)
    
