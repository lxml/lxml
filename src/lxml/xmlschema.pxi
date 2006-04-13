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
    cdef _ErrorLog _error_log
    
    def __init__(self, etree):
        cdef _Document doc
        cdef _NodeBase root_node
        cdef xmlDoc* fake_c_doc
        cdef xmlNode* c_node
        cdef xmlschema.xmlSchemaParserCtxt* parser_ctxt

        doc = _documentOrRaise(etree)
        root_node = _rootNodeOf(etree)

        # work around for libxml2 bug if document is not XML schema at all
        c_node = root_node._c_node
        if c_node.ns is NULL or c_node.ns.href is NULL or \
               tree.strcmp(c_node.ns.href, 'http://www.w3.org/2001/XMLSchema') != 0:
            raise XMLSchemaParseError, "Document is not XML Schema"

        fake_c_doc = _fakeRootDoc(doc._c_doc, root_node._c_node)
        parser_ctxt = xmlschema.xmlSchemaNewDocParserCtxt(fake_c_doc)
        if parser_ctxt is NULL:
            _destroyFakeDoc(doc._c_doc, fake_c_doc)
            raise XMLSchemaParseError, "Document is not parsable as XML Schema"
        self._c_schema = xmlschema.xmlSchemaParse(parser_ctxt)

        xmlschema.xmlSchemaFreeParserCtxt(parser_ctxt)
        _destroyFakeDoc(doc._c_doc, fake_c_doc)

        if self._c_schema is NULL:
            raise XMLSchemaParseError, "Document is not valid XML Schema"
        self._error_log = _ErrorLog()

    def __dealloc__(self):
        xmlschema.xmlSchemaFree(self._c_schema)

    def validate(self, etree):
        """Validate doc using XML Schema.

        Returns true if document is valid, false if not.
        """
        cdef xmlschema.xmlSchemaValidCtxt* valid_ctxt
        cdef _Document doc
        cdef _NodeBase root_node
        cdef xmlDoc* c_doc
        cdef int ret

        doc = _documentOrRaise(etree)
        root_node = _rootNodeOf(etree)

        self._error_log.connect()
        valid_ctxt = xmlschema.xmlSchemaNewValidCtxt(self._c_schema)

        c_doc = _fakeRootDoc(doc._c_doc, root_node._c_node)
        ret = xmlschema.xmlSchemaValidateDoc(valid_ctxt, c_doc)
        _destroyFakeDoc(doc._c_doc, c_doc)

        xmlschema.xmlSchemaFreeValidCtxt(valid_ctxt)
        self._error_log.disconnect()
        if ret == -1:
            raise XMLSchemaValidateError, "Internal error in XML Schema validation."
        return ret == 0

    property error_log:
        def __get__(self):
            return self._error_log.copy()
