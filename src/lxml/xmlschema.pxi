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
    
    def __init__(self, _ElementTree etree):
        cdef _Document doc
        cdef xmlschema.xmlSchemaParserCtxt* parser_ctxt
        doc = etree._doc
        parser_ctxt = xmlschema.xmlSchemaNewDocParserCtxt(doc._c_doc)
        if parser_ctxt is NULL:
            raise XMLSchemaParseError, "Document is not parsable as XML Schema"
        self._c_schema = xmlschema.xmlSchemaParse(parser_ctxt)
        if self._c_schema is NULL:
            xmlschema.xmlSchemaFreeParserCtxt(parser_ctxt)
            raise XMLSchemaParseError, "Document is not valid XML Schema"
        xmlschema.xmlSchemaFreeParserCtxt(parser_ctxt)
        
    def __dealloc__(self):
        xmlschema.xmlSchemaFree(self._c_schema)

    def validate(self, _ElementTree etree):
        """Validate doc using XML Schema.

        Returns true if document is valid, false if not.
        """
        cdef xmlschema.xmlSchemaValidCtxt* valid_ctxt
        cdef xmlDoc* c_doc
        cdef int ret
        valid_ctxt = xmlschema.xmlSchemaNewValidCtxt(self._c_schema)

        c_doc = _fakeRootDoc(etree._doc._c_doc, etree._context_node._c_node)
        ret = xmlschema.xmlSchemaValidateDoc(valid_ctxt, c_doc)
        _destroyFakeDoc(etree._doc._c_doc, c_doc)

        xmlschema.xmlSchemaFreeValidCtxt(valid_ctxt)
        if ret == -1:
            raise XMLSchemaValidateError, "Internal error in XML Schema validation."
        return ret == 0

    property error_log:
        def __get__(self):
            return __build_error_log_tuple(self)
