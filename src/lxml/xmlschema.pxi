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
    """Turn a document into an XML Schema validator.
    """
    cdef xmlschema.xmlSchema* _c_schema
    def __init__(self, etree=None, file=None):
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
                raise XMLSchemaParseError, "Document is not XML Schema"

            fake_c_doc = _fakeRootDoc(doc._c_doc, root_node._c_node)
            self._error_log.connect()
            parser_ctxt = xmlschema.xmlSchemaNewDocParserCtxt(fake_c_doc)
        elif file is not None:
            filename = _getFilenameForFile(file)
            if filename is None:
                # XXX assume a string object
                filename = file
            filename = _encodeFilename(filename)
            self._error_log.connect()
            parser_ctxt = xmlschema.xmlSchemaNewParserCtxt(_cstr(filename))
        else:
            raise XMLSchemaParseError, "No tree or file given"

        if parser_ctxt is not NULL:
            self._c_schema = xmlschema.xmlSchemaParse(parser_ctxt)
            if _LIBXML_VERSION_INT >= 20624:
                xmlschema.xmlSchemaFreeParserCtxt(parser_ctxt)

        self._error_log.disconnect()

        if fake_c_doc is not NULL:
            _destroyFakeDoc(doc._c_doc, fake_c_doc)

        if self._c_schema is NULL:
            raise XMLSchemaParseError, self._error_log._buildExceptionMessage(
                "Document is not valid XML Schema")

    def __dealloc__(self):
        xmlschema.xmlSchemaFree(self._c_schema)

    def __call__(self, etree):
        """Validate doc using XML Schema.

        Returns true if document is valid, false if not.
        """
        cdef python.PyThreadState* state
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
            raise XMLSchemaError, "Failed to create validation context"

        c_doc = _fakeRootDoc(doc._c_doc, root_node._c_node)
        state = python.PyEval_SaveThread()
        ret = xmlschema.xmlSchemaValidateDoc(valid_ctxt, c_doc)
        python.PyEval_RestoreThread(state)
        _destroyFakeDoc(doc._c_doc, c_doc)

        xmlschema.xmlSchemaFreeValidCtxt(valid_ctxt)

        self._error_log.disconnect()
        if ret == -1:
            raise XMLSchemaValidateError, "Internal error in XML Schema validation."
        if ret == 0:
            return True
        else:
            return False
