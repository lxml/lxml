# support for DTD validation
cimport dtdvalid

class DTDError(LxmlError):
    u"""Base class for DTD errors.
    """
    pass

class DTDParseError(DTDError):
    u"""Error while parsing a DTD.
    """
    pass

class DTDValidateError(DTDError):
    u"""Error while validating an XML document with a DTD.
    """
    pass

################################################################################
# DTD

cdef class DTD(_Validator):
    u"""DTD(self, file=None, external_id=None)
    A DTD validator.

    Can load from filesystem directly given a filename or file-like object.
    Alternatively, pass the keyword parameter ``external_id`` to load from a
    catalog.
    """
    cdef tree.xmlDtd* _c_dtd
    def __cinit__(self):
        self._c_dtd = NULL

    def __init__(self, file=None, *, external_id=None):
        _Validator.__init__(self)
        if file is not None:
            if _isString(file):
                file = _encodeFilename(file)
                self._error_log.connect()
                self._c_dtd = xmlparser.xmlParseDTD(NULL, _cstr(file))
                self._error_log.disconnect()
            elif hasattr(file, u'read'):
                self._c_dtd = _parseDtdFromFilelike(file)
            else:
                raise DTDParseError, u"file must be a filename or file-like object"
        elif external_id is not None:
            self._error_log.connect()
            self._c_dtd = xmlparser.xmlParseDTD(external_id, NULL)
            self._error_log.disconnect()
        else:
            raise DTDParseError, u"either filename or external ID required"

        if self._c_dtd is NULL:
            raise DTDParseError(
                self._error_log._buildExceptionMessage(u"error parsing DTD"),
                self._error_log)

    def __dealloc__(self):
        tree.xmlFreeDtd(self._c_dtd)

    def __call__(self, etree):
        u"""__call__(self, etree)

        Validate doc using the DTD.

        Returns true if the document is valid, false if not.
        """
        cdef _Document doc
        cdef _Element root_node
        cdef xmlDoc* c_doc
        cdef dtdvalid.xmlValidCtxt* valid_ctxt
        cdef int ret

        assert self._c_dtd is not NULL, "DTD not initialised"
        doc = _documentOrRaise(etree)
        root_node = _rootNodeOrRaise(etree)

        self._error_log.connect()
        valid_ctxt = dtdvalid.xmlNewValidCtxt()
        if valid_ctxt is NULL:
            self._error_log.disconnect()
            raise DTDError(u"Failed to create validation context",
                           self._error_log)

        c_doc = _fakeRootDoc(doc._c_doc, root_node._c_node)
        with nogil:
            ret = dtdvalid.xmlValidateDtd(valid_ctxt, c_doc, self._c_dtd)
        _destroyFakeDoc(doc._c_doc, c_doc)

        dtdvalid.xmlFreeValidCtxt(valid_ctxt)

        self._error_log.disconnect()
        if ret == -1:
            raise DTDValidateError(u"Internal error in DTD validation",
                                   self._error_log)
        if ret == 1:
            return True
        else:
            return False


cdef tree.xmlDtd* _parseDtdFromFilelike(file) except NULL:
    cdef _ExceptionContext exc_context
    cdef _FileReaderContext dtd_parser
    cdef _ErrorLog error_log
    cdef tree.xmlDtd* c_dtd
    exc_context = _ExceptionContext()
    dtd_parser = _FileReaderContext(file, exc_context, None, None)
    error_log = _ErrorLog()

    error_log.connect()
    c_dtd = dtd_parser._readDtd()
    error_log.disconnect()

    exc_context._raise_if_stored()
    if c_dtd is NULL:
        raise DTDParseError(u"error parsing DTD", error_log)
    return c_dtd

cdef extern from "etree_defs.h":
    # macro call to 't->tp_new()' for fast instantiation
    cdef DTD NEW_DTD "PY_NEW" (object t)

cdef DTD _dtdFactory(tree.xmlDtd* c_dtd):
    # do not run through DTD.__init__()!
    cdef DTD dtd
    if c_dtd is NULL:
        return None
    dtd = NEW_DTD(DTD)
    dtd._c_dtd = tree.xmlCopyDtd(c_dtd)
    if dtd._c_dtd is NULL:
        python.PyErr_NoMemory()
    _Validator.__init__(dtd)
    return dtd
