#  support for XMLSchema validation
cimport xmlschema

class XMLSchemaError(LxmlError):
    """Base class of all XML Schema errors
    """
    pass

class XMLSchemaParseError(XMLSchemaError):
    """Error while parsing an XML document as XML Schema.
    """
    pass

class XMLSchemaValidateError(XMLSchemaError):
    """Error while validating an XML document with an XML Schema.
    """
    pass

################################################################################
# XMLSchema

cdef class XMLSchema(_Validator):
    """XMLSchema(self, etree=None, file=None)
    Turn a document into an XML Schema validator.

    Either pass a schema as Element or ElementTree, or pass a file or
    filename through the ``file`` keyword argument.
    """
    cdef xmlschema.xmlSchema* _c_schema
    def __init__(self, etree=None, *, file=None):
        cdef _Document doc
        cdef _Element root_node
        cdef xmlDoc* fake_c_doc
        cdef xmlNode* c_node
        cdef char* c_href
        cdef xmlschema.xmlSchemaParserCtxt* parser_ctxt
        _Validator.__init__(self)
        self._c_schema = NULL
        fake_c_doc = NULL
        if etree is not None:
            doc = _documentOrRaise(etree)
            root_node = _rootNodeOrRaise(etree)

            # work around for libxml2 bug if document is not XML schema at all
            #if _LIBXML_VERSION_INT < 20624:
            c_node = root_node._c_node
            c_href = _getNs(c_node)
            if c_href is NULL or \
                   cstd.strcmp(c_href, 'http://www.w3.org/2001/XMLSchema') != 0:
                raise XMLSchemaParseError("Document is not XML Schema")

            fake_c_doc = _fakeRootDoc(doc._c_doc, root_node._c_node)
            self._error_log.connect()
            parser_ctxt = xmlschema.xmlSchemaNewDocParserCtxt(fake_c_doc)
        elif file is not None:
            if _isString(file):
                filename = _encodeFilename(file)
                self._error_log.connect()
                parser_ctxt = xmlschema.xmlSchemaNewParserCtxt(_cstr(filename))
            else:
                doc = _parseDocument(file, None, None)
                self._error_log.connect()
                parser_ctxt = xmlschema.xmlSchemaNewDocParserCtxt(doc._c_doc)
        else:
            raise XMLSchemaParseError("No tree or file given")

        if parser_ctxt is not NULL:
            self._c_schema = xmlschema.xmlSchemaParse(parser_ctxt)
            if _LIBXML_VERSION_INT >= 20624:
                xmlschema.xmlSchemaFreeParserCtxt(parser_ctxt)

        self._error_log.disconnect()

        if fake_c_doc is not NULL:
            _destroyFakeDoc(doc._c_doc, fake_c_doc)

        if self._c_schema is NULL:
            raise XMLSchemaParseError(
                self._error_log._buildExceptionMessage(
                    "Document is not valid XML Schema"),
                self._error_log)

    def __dealloc__(self):
        xmlschema.xmlSchemaFree(self._c_schema)

    def __call__(self, etree):
        """__call__(self, etree)

        Validate doc using XML Schema.

        Returns true if document is valid, false if not.
        """
        cdef xmlschema.xmlSchemaValidCtxt* valid_ctxt
        cdef _Document doc
        cdef _Element root_node
        cdef xmlDoc* c_doc
        cdef int ret

        doc = _documentOrRaise(etree)
        root_node = _rootNodeOrRaise(etree)

        self._error_log.connect()
        valid_ctxt = xmlschema.xmlSchemaNewValidCtxt(self._c_schema)
        if valid_ctxt is NULL:
            self._error_log.disconnect()
            return python.PyErr_NoMemory()

        c_doc = _fakeRootDoc(doc._c_doc, root_node._c_node)
        with nogil:
            ret = xmlschema.xmlSchemaValidateDoc(valid_ctxt, c_doc)
        _destroyFakeDoc(doc._c_doc, c_doc)

        xmlschema.xmlSchemaFreeValidCtxt(valid_ctxt)

        self._error_log.disconnect()
        if ret == -1:
            raise XMLSchemaValidateError(
                "Internal error in XML Schema validation.",
                self._error_log)
        if ret == 0:
            return True
        else:
            return False

    cdef _ParserSchemaValidationContext _newSaxValidator(self):
        cdef _ParserSchemaValidationContext context
        context = NEW_SCHEMA_CONTEXT(_ParserSchemaValidationContext)
        context._schema = self
        context._valid_ctxt = NULL
        context._sax_plug = NULL
        return context

cdef class _ParserSchemaValidationContext:
    cdef XMLSchema _schema
    cdef xmlschema.xmlSchemaValidCtxt* _valid_ctxt
    cdef xmlschema.xmlSchemaSAXPlugStruct* _sax_plug

    def __dealloc__(self):
        self.disconnect()
        if self._valid_ctxt:
            xmlschema.xmlSchemaFreeValidCtxt(self._valid_ctxt)

    cdef _ParserSchemaValidationContext copy(self):
        return self._schema._newSaxValidator()

    cdef int connect(self, xmlparser.xmlParserCtxt* c_ctxt) except -1:
        if self._valid_ctxt is NULL:
            self._valid_ctxt = xmlschema.xmlSchemaNewValidCtxt(
                self._schema._c_schema)
            if self._valid_ctxt is NULL:
                return python.PyErr_NoMemory()
        self._sax_plug = xmlschema.xmlSchemaSAXPlug(
            self._valid_ctxt, &c_ctxt.sax, &c_ctxt.userData)

    cdef void disconnect(self):
        if self._sax_plug is not NULL:
            xmlschema.xmlSchemaSAXUnplug(self._sax_plug)
            self._sax_plug = NULL

    cdef bint isvalid(self):
        if self._valid_ctxt is NULL:
            return 1 # valid
        return xmlschema.xmlSchemaIsValid(self._valid_ctxt)

cdef extern from "etree_defs.h":
    # macro call to 't->tp_new()' for fast instantiation
    cdef _ParserSchemaValidationContext NEW_SCHEMA_CONTEXT "PY_NEW" (object t)
