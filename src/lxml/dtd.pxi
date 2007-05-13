# support for DTD validation
cimport dtdvalid

class DTDError(LxmlError):
    """Base class for DTD errors.
    """
    pass

class DTDParseError(DTDError):
    """Error while parsing a DTD.
    """
    pass

class DTDValidateError(DTDError):
    """Error while validating an XML document with a DTD.
    """
    pass

################################################################################
# DTD

cdef class DTD(_Validator):
    """A DTD validator.

    Can load from filesystem directly given a filename or file-like object.
    Alternatively, pass the keyword parameter ``external_id`` to load from a
    catalog.
    """
    cdef tree.xmlDtd* _c_dtd
    def __init__(self, file=None, external_id=None):
        self._c_dtd = NULL
        if file is not None:
            if python._isString(file):
                self._c_dtd = xmlparser.xmlParseDTD(NULL, _cstr(file))
            elif hasattr(file, 'read'):
                self._c_dtd = _parseDtdFromFilelike(file)
            else:
                raise DTDParseError, "parsing from file objects is not supported"
        elif external_id is not None:
            self._c_dtd = xmlparser.xmlParseDTD(external_id, NULL)
        else:
            raise DTDParseError, "either filename or external ID required"

        if self._c_dtd is NULL:
            raise DTDParseError, "error parsing DTD"
        _Validator.__init__(self)

    def __dealloc__(self):
        tree.xmlFreeDtd(self._c_dtd)

    def __call__(self, etree):
        """Validate doc using the DTD.

        Returns true if the document is valid, false if not.
        """
        cdef python.PyThreadState* state
        cdef _Document doc
        cdef _Element root_node
        cdef xmlDoc* c_doc
        cdef dtdvalid.xmlValidCtxt* valid_ctxt
        cdef int ret

        doc = _documentOrRaise(etree)
        root_node = _rootNodeOrRaise(etree)

        self._error_log.connect()
        valid_ctxt = dtdvalid.xmlNewValidCtxt()
        if valid_ctxt is NULL:
            self._error_log.disconnect()
            raise DTDError, "Failed to create validation context"

        c_doc = _fakeRootDoc(doc._c_doc, root_node._c_node)
        state = python.PyEval_SaveThread()
        ret = dtdvalid.xmlValidateDtd(valid_ctxt, c_doc, self._c_dtd)
        python.PyEval_RestoreThread(state)
        _destroyFakeDoc(doc._c_doc, c_doc)

        dtdvalid.xmlFreeValidCtxt(valid_ctxt)

        self._error_log.disconnect()
        if ret == -1:
            raise DTDValidateError, "Internal error in DTD validation"
        return ret == 1


cdef tree.xmlDtd* _parseDtdFromFilelike(file) except NULL:
    cdef _ExceptionContext exc_context
    cdef _FileParserContext dtd_parser
    cdef tree.xmlDtd* c_dtd
    exc_context = _ExceptionContext()
    dtd_parser = _FileParserContext(file, exc_context)

    c_dtd = dtd_parser._readDtd()

    exc_context._raise_if_stored()
    if c_dtd is NULL:
        raise DTDParseError, "error parsing DTD"
    return c_dtd
