#  support for XMLSchema validation
cimport xmlschema

class XMLSchemaError(LxmlError):
    u"""Base class of all XML Schema errors
    """
    pass

class XMLSchemaParseError(XMLSchemaError):
    u"""Error while parsing an XML document as XML Schema.
    """
    pass

class XMLSchemaValidateError(XMLSchemaError):
    u"""Error while validating an XML document with an XML Schema.
    """
    pass

################################################################################
# XMLSchema

cdef XPath _check_for_default_attributes = XPath(
    u"boolean(//xs:attribute[@default or @fixed][1])",
    namespaces={u'xs': u'http://www.w3.org/2001/XMLSchema'})

cdef class XMLSchema(_Validator):
    u"""XMLSchema(self, etree=None, file=None)
    Turn a document into an XML Schema validator.

    Either pass a schema as Element or ElementTree, or pass a file or
    filename through the ``file`` keyword argument.

    Passing the ``attribute_defaults`` boolean option will make the
    schema insert default/fixed attributes into validated documents.
    """
    cdef xmlschema.xmlSchema* _c_schema
    cdef bint _has_default_attributes
    cdef bint _add_attribute_defaults
    def __cinit__(self):
        self._c_schema = NULL
        self._has_default_attributes = True # play safe
        self._add_attribute_defaults = False

    def __init__(self, etree=None, *, file=None, attribute_defaults=False):
        cdef _Document doc
        cdef _Element root_node
        cdef xmlDoc* fake_c_doc
        cdef xmlNode* c_node
        cdef char* c_href
        cdef xmlschema.xmlSchemaParserCtxt* parser_ctxt

        self._add_attribute_defaults = attribute_defaults
        _Validator.__init__(self)
        fake_c_doc = NULL
        if etree is not None:
            doc = _documentOrRaise(etree)
            root_node = _rootNodeOrRaise(etree)

            # work around for libxml2 bug if document is not XML schema at all
            if _LIBXML_VERSION_INT < 20624:
                c_node = root_node._c_node
                c_href = _getNs(c_node)
                if c_href is NULL or \
                       cstd.strcmp(c_href, 'http://www.w3.org/2001/XMLSchema') != 0:
                    raise XMLSchemaParseError, u"Document is not XML Schema"

            fake_c_doc = _fakeRootDoc(doc._c_doc, root_node._c_node)
            self._error_log.connect()
            parser_ctxt = xmlschema.xmlSchemaNewDocParserCtxt(fake_c_doc)
        elif file is not None:
            if _isString(file):
                doc = None
                filename = _encodeFilename(file)
                self._error_log.connect()
                parser_ctxt = xmlschema.xmlSchemaNewParserCtxt(_cstr(filename))
            else:
                doc = _parseDocument(file, None, None)
                self._error_log.connect()
                parser_ctxt = xmlschema.xmlSchemaNewDocParserCtxt(doc._c_doc)
        else:
            raise XMLSchemaParseError, u"No tree or file given"

        if parser_ctxt is not NULL:
            if doc is None:
                with nogil:
                    self._c_schema = xmlschema.xmlSchemaParse(parser_ctxt)
            else:
                # calling xmlSchemaParse on a schema with imports or
                # includes will cause libxml2 to create an internal
                # context for parsing, so push an implied context to route
                # resolve requests to the document's parser
                __GLOBAL_PARSER_CONTEXT.pushImpliedContextFromParser(doc._parser)
                self._c_schema = xmlschema.xmlSchemaParse(parser_ctxt)
                __GLOBAL_PARSER_CONTEXT.popImpliedContext()

            if _LIBXML_VERSION_INT >= 20624:
                xmlschema.xmlSchemaFreeParserCtxt(parser_ctxt)

        self._error_log.disconnect()

        if fake_c_doc is not NULL:
            _destroyFakeDoc(doc._c_doc, fake_c_doc)

        if self._c_schema is NULL:
            raise XMLSchemaParseError(
                self._error_log._buildExceptionMessage(
                    u"Document is not valid XML Schema"),
                self._error_log)

        if doc is not None:
            self._has_default_attributes = _check_for_default_attributes(doc)
        self._add_attribute_defaults = attribute_defaults and \
                                       self._has_default_attributes

    def __dealloc__(self):
        xmlschema.xmlSchemaFree(self._c_schema)

    def __call__(self, etree):
        u"""__call__(self, etree)

        Validate doc using XML Schema.

        Returns true if document is valid, false if not.
        """
        cdef xmlschema.xmlSchemaValidCtxt* valid_ctxt
        cdef _Document doc
        cdef _Element root_node
        cdef xmlDoc* c_doc
        cdef int ret

        assert self._c_schema is not NULL, "Schema instance not initialised"
        doc = _documentOrRaise(etree)
        root_node = _rootNodeOrRaise(etree)

        self._error_log.connect()
        valid_ctxt = xmlschema.xmlSchemaNewValidCtxt(self._c_schema)
        if valid_ctxt is NULL:
            self._error_log.disconnect()
            return python.PyErr_NoMemory()

        if self._add_attribute_defaults:
            xmlschema.xmlSchemaSetValidOptions(
                valid_ctxt, xmlschema.XML_SCHEMA_VAL_VC_I_CREATE)

        c_doc = _fakeRootDoc(doc._c_doc, root_node._c_node)
        with nogil:
            ret = xmlschema.xmlSchemaValidateDoc(valid_ctxt, c_doc)
        _destroyFakeDoc(doc._c_doc, c_doc)

        xmlschema.xmlSchemaFreeValidCtxt(valid_ctxt)

        self._error_log.disconnect()
        if ret == -1:
            raise XMLSchemaValidateError(
                u"Internal error in XML Schema validation.",
                self._error_log)
        if ret == 0:
            return True
        else:
            return False

    cdef _ParserSchemaValidationContext _newSaxValidator(
            self, bint add_default_attributes):
        cdef _ParserSchemaValidationContext context
        context = NEW_SCHEMA_CONTEXT(_ParserSchemaValidationContext)
        context._schema = self
        context._add_default_attributes = (self._has_default_attributes and (
            add_default_attributes or self._add_attribute_defaults))
        return context

cdef class _ParserSchemaValidationContext:
    cdef XMLSchema _schema
    cdef xmlschema.xmlSchemaValidCtxt* _valid_ctxt
    cdef xmlschema.xmlSchemaSAXPlugStruct* _sax_plug
    cdef bint _add_default_attributes
    def __cinit__(self):
        self._valid_ctxt = NULL
        self._sax_plug = NULL
        self._add_default_attributes = False

    def __dealloc__(self):
        self.disconnect()
        if self._valid_ctxt:
            xmlschema.xmlSchemaFreeValidCtxt(self._valid_ctxt)

    cdef _ParserSchemaValidationContext copy(self):
        assert self._schema is not None, "_ParserSchemaValidationContext not initialised"
        return self._schema._newSaxValidator(
            self._add_default_attributes)

    cdef void inject_default_attributes(self, xmlDoc* c_doc):
        # we currently need to insert default attributes manually
        # after parsing, as libxml2 does not support this at parse
        # time
        if self._add_default_attributes:
            with nogil:
                xmlschema.xmlSchemaValidateDoc(self._valid_ctxt, c_doc)

    cdef int connect(self, xmlparser.xmlParserCtxt* c_ctxt) except -1:
        if self._valid_ctxt is NULL:
            self._valid_ctxt = xmlschema.xmlSchemaNewValidCtxt(
                self._schema._c_schema)
            if self._valid_ctxt is NULL:
                return python.PyErr_NoMemory()
            if self._add_default_attributes:
                xmlschema.xmlSchemaSetValidOptions(
                    self._valid_ctxt,
                    xmlschema.XML_SCHEMA_VAL_VC_I_CREATE)
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
