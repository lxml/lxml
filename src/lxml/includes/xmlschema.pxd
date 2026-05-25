from lxml.includes.tree cimport xmlDoc
from lxml.includes.xmlparser cimport xmlSAXHandler, xmlResourceLoader
from lxml.includes.xmlerror cimport xmlStructuredErrorFunc

cdef extern from "libxml/xmlschemas.h" nogil:
    """
    #if LIBXML_VERSION < 21400
        #define xmlSchemaSetResourceLoader(ctxt, loader, data)  ((void) ((void) ctxt, (void) loader, (void) data))
    #endif
    """
    ctypedef struct xmlSchema
    ctypedef struct xmlSchemaParserCtxt

    ctypedef struct xmlSchemaSAXPlugStruct
    ctypedef struct xmlSchemaValidCtxt

    ctypedef enum xmlSchemaValidOption:
        XML_SCHEMA_VAL_VC_I_CREATE = 1

    cdef void xmlSchemaSetResourceLoader(xmlSchemaParserCtxt* ctxt,
        xmlResourceLoader loader, void *ctx)
    cdef void xmlSchemaSetParserStructuredErrors(xmlSchemaParserCtxt* ctxt,
        xmlStructuredErrorFunc serror, void *ctx)

    cdef xmlSchemaValidCtxt* xmlSchemaNewValidCtxt(xmlSchema* schema) nogil
    cdef void xmlSchemaSetValidStructuredErrors(xmlSchemaValidCtxt* ctxt,
        xmlStructuredErrorFunc serror, void *ctx)

    cdef int xmlSchemaValidateDoc(xmlSchemaValidCtxt* ctxt, xmlDoc* doc) nogil
    cdef xmlSchema* xmlSchemaParse(xmlSchemaParserCtxt* ctxt) nogil
    cdef xmlSchemaParserCtxt* xmlSchemaNewParserCtxt(char* URL) nogil
    cdef xmlSchemaParserCtxt* xmlSchemaNewDocParserCtxt(xmlDoc* doc) nogil
    cdef void xmlSchemaFree(xmlSchema* schema) nogil
    cdef void xmlSchemaFreeParserCtxt(xmlSchemaParserCtxt* ctxt) nogil
    cdef void xmlSchemaFreeValidCtxt(xmlSchemaValidCtxt* ctxt) nogil
    cdef int xmlSchemaSetValidOptions(xmlSchemaValidCtxt* ctxt,
                                      int options) nogil

    cdef xmlSchemaSAXPlugStruct* xmlSchemaSAXPlug(xmlSchemaValidCtxt* ctxt,
                                                  xmlSAXHandler** sax,
                                                  void** data) nogil
    cdef int xmlSchemaSAXUnplug(xmlSchemaSAXPlugStruct* sax_plug)
    cdef int xmlSchemaIsValid(xmlSchemaValidCtxt* ctxt)
