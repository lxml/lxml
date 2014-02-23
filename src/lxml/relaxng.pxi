# support for RelaxNG validation
from lxml.includes cimport relaxng

class RelaxNGError(LxmlError):
    u"""Base class for RelaxNG errors.
    """
    pass

class RelaxNGParseError(RelaxNGError):
    u"""Error while parsing an XML document as RelaxNG.
    """
    pass

class RelaxNGValidateError(RelaxNGError):
    u"""Error while validating an XML document with a RelaxNG schema.
    """
    pass

################################################################################
# RelaxNG

cdef class RelaxNG(_Validator):
    u"""RelaxNG(self, etree=None, file=None)
    Turn a document into a Relax NG validator.

    Either pass a schema as Element or ElementTree, or pass a file or
    filename through the ``file`` keyword argument.
    """
    cdef relaxng.xmlRelaxNG* _c_schema
    def __cinit__(self):
        self._c_schema = NULL

    def __init__(self, etree=None, *, file=None):
        cdef _Document doc
        cdef _Element root_node
        cdef xmlNode* c_node
        cdef xmlDoc* fake_c_doc
        cdef relaxng.xmlRelaxNGParserCtxt* parser_ctxt
        _Validator.__init__(self)
        fake_c_doc = NULL
        if etree is not None:
            doc = _documentOrRaise(etree)
            root_node = _rootNodeOrRaise(etree)
            c_node = root_node._c_node
            # work around for libxml2 crash bug if document is not RNG at all
            if _LIBXML_VERSION_INT < 20624:
                c_href = _getNs(c_node)
                if c_href is NULL or \
                       tree.xmlStrcmp(
                           c_href, <unsigned char*>'http://relaxng.org/ns/structure/1.0') != 0:
                    raise RelaxNGParseError, u"Document is not Relax NG"
            fake_c_doc = _fakeRootDoc(doc._c_doc, root_node._c_node)
            parser_ctxt = relaxng.xmlRelaxNGNewDocParserCtxt(fake_c_doc)
        elif file is not None:
            if _isString(file):
                doc = None
                filename = _encodeFilename(file)
                with self._error_log:
                    parser_ctxt = relaxng.xmlRelaxNGNewParserCtxt(_cstr(filename))
            else:
                doc = _parseDocument(file, None, None)
                parser_ctxt = relaxng.xmlRelaxNGNewDocParserCtxt(doc._c_doc)
        else:
            raise RelaxNGParseError, u"No tree or file given"

        if parser_ctxt is NULL:
            if fake_c_doc is not NULL:
                _destroyFakeDoc(doc._c_doc, fake_c_doc)
            raise RelaxNGParseError(
                self._error_log._buildExceptionMessage(
                    u"Document is not parsable as Relax NG"),
                self._error_log)

        relaxng.xmlRelaxNGSetParserStructuredErrors(
            parser_ctxt, _receiveError, <void*>self._error_log)
        self._c_schema = relaxng.xmlRelaxNGParse(parser_ctxt)

        if _LIBXML_VERSION_INT >= 20624:
            relaxng.xmlRelaxNGFreeParserCtxt(parser_ctxt)
        if self._c_schema is NULL:
            if fake_c_doc is not NULL:
                if _LIBXML_VERSION_INT < 20624:
                    relaxng.xmlRelaxNGFreeParserCtxt(parser_ctxt)
                _destroyFakeDoc(doc._c_doc, fake_c_doc)
            raise RelaxNGParseError(
                self._error_log._buildExceptionMessage(
                    u"Document is not valid Relax NG"),
                self._error_log)
        if fake_c_doc is not NULL:
            _destroyFakeDoc(doc._c_doc, fake_c_doc)

    def __dealloc__(self):
        relaxng.xmlRelaxNGFree(self._c_schema)

    def __call__(self, etree):
        u"""__call__(self, etree)

        Validate doc using Relax NG.

        Returns true if document is valid, false if not."""
        cdef _Document doc
        cdef _Element root_node
        cdef xmlDoc* c_doc
        cdef relaxng.xmlRelaxNGValidCtxt* valid_ctxt
        cdef int ret

        assert self._c_schema is not NULL, "RelaxNG instance not initialised"
        doc = _documentOrRaise(etree)
        root_node = _rootNodeOrRaise(etree)

        valid_ctxt = relaxng.xmlRelaxNGNewValidCtxt(self._c_schema)
        if valid_ctxt is NULL:
            raise MemoryError()

        try:
            self._error_log.clear()
            relaxng.xmlRelaxNGSetValidStructuredErrors(
                valid_ctxt, _receiveError, <void*>self._error_log)
            c_doc = _fakeRootDoc(doc._c_doc, root_node._c_node)
            with nogil:
                ret = relaxng.xmlRelaxNGValidateDoc(valid_ctxt, c_doc)
            _destroyFakeDoc(doc._c_doc, c_doc)
        finally:
            relaxng.xmlRelaxNGFreeValidCtxt(valid_ctxt)

        if ret == -1:
            raise RelaxNGValidateError(
                u"Internal error in Relax NG validation",
                self._error_log)
        if ret == 0:
            return True
        else:
            return False
