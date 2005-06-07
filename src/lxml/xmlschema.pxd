cimport tree
from tree cimport xmlDoc

cdef extern from "libxml/xmlschemas.h":
    ctypedef struct xmlSchema
    ctypedef struct xmlSchemaParserCtxt
    
    ctypedef struct xmlSchemaValidCtxt
        
    cdef xmlSchemaValidCtxt* xmlSchemaNewValidCtxt(xmlSchema* schema)
    cdef int xmlSchemaValidateDoc(xmlSchemaValidCtxt* ctxt, xmlDoc* doc)
    cdef xmlSchema* xmlSchemaParse(xmlSchemaParserCtxt* ctxt)
    cdef xmlSchemaParserCtxt* xmlSchemaNewParserCtxt(char* URL)
    cdef xmlSchemaParserCtxt* xmlSchemaNewDocParserCtxt(xmlDoc* doc)
    cdef void xmlSchemaFree(xmlSchema* schema)
    cdef void xmlSchemaFreeParserCtxt(xmlSchemaParserCtxt* ctxt)
    cdef void xmlSchemaFreeValidCtxt(xmlSchemaValidCtxt* ctxt)
