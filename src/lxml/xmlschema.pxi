#  support for XMLSchema validation
cimport xmlschema

class XMLSchemaError(LxmlError):
    pass

class XMLSchemaParseError(XMLSchemaError):
    pass

class XMLSchemaValidateError(XMLSchemaError):
    pass

################################################################################
# XMLSchema

cdef class XMLSchema:
    """Turn a document into an XML Schema validator.
    """
    cdef xmlschema.xmlSchema* _c_schema
    
    def __init__(self, _ElementTree tree):
        cdef xmlschema.xmlSchemaParserCtxt* parser_ctxt
        parser_ctxt = xmlschema.xmlSchemaNewDocParserCtxt(tree._c_doc)
        if parser_ctxt is NULL:
            raise XMLSchemaParseError, "Document is not valid XML Schema"
        self._c_schema = xmlschema.xmlSchemaParse(parser_ctxt)
        if self._c_schema is NULL:
            xmlschema.xmlSchemaFreeParserCtxt(parser_ctxt)
            raise XMLSchemaParseError, "Document is not valid XML Schema"
        xmlschema.xmlSchemaFreeParserCtxt(parser_ctxt)
        
    def __dealloc__(self):
        xmlschema.xmlSchemaFree(self._c_schema)

    def validate(self, _ElementTree doc):
        """Validate doc using XML Schema.

        Returns true if document is valid, false if not.
        """
        cdef xmlschema.xmlSchemaValidCtxt* valid_ctxt
        cdef int ret
        valid_ctxt = xmlschema.xmlSchemaNewValidCtxt(self._c_schema)
        ret = xmlschema.xmlSchemaValidateDoc(valid_ctxt, doc._c_doc)
        xmlschema.xmlSchemaFreeValidCtxt(valid_ctxt)
        if ret == -1:
            raise XMLSchemaValidateError, "Internal error in XML Schema validation."
        return ret == 0
        
