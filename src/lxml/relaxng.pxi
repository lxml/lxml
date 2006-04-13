# support for RelaxNG validation
cimport relaxng

class RelaxNGError(LxmlError):
    pass

class RelaxNGParseError(RelaxNGError):
    pass

class RelaxNGValidateError(RelaxNGError):
    pass

################################################################################
# RelaxNG

cdef class RelaxNG:
    """Turn a document into a Relax NG validator.
    Can also load from filesystem directly given file object or filename.
    """
    cdef relaxng.xmlRelaxNG* _c_schema
    cdef _ErrorLog _error_log
    
    def __init__(self, etree=None, file=None):
        cdef _Document doc
        cdef _NodeBase root_node
        cdef xmlNode* c_node
        cdef xmlDoc* fake_c_doc
        cdef relaxng.xmlRelaxNGParserCtxt* parser_ctxt

        fake_c_doc = NULL
        if etree is not None:
            doc = _documentOrRaise(etree)
            root_node = _rootNodeOf(etree)
            c_node = root_node._c_node
            # work around for libxml2 bug if document is not RNG at all
            if c_node.ns is NULL or c_node.ns.href is NULL or \
                   tree.strcmp(c_node.ns.href,
                               'http://relaxng.org/ns/structure/1.0') != 0:
                raise RelaxNGParseError, "Document is not Relax NG"
            fake_c_doc = _fakeRootDoc(doc._c_doc, root_node._c_node)
            parser_ctxt = relaxng.xmlRelaxNGNewDocParserCtxt(fake_c_doc)
        elif file is not None:
            filename = _getFilenameForFile(file)
            if filename is None:
                # XXX assume a string object
                filename = file
            parser_ctxt = relaxng.xmlRelaxNGNewParserCtxt(filename)
        else:
            raise RelaxNGParseError, "No tree or file given"

        if parser_ctxt is NULL:
            if fake_c_doc is not NULL:
                _destroyFakeDoc(doc._c_doc, fake_c_doc)
            raise RelaxNGParseError, "Document is not parsable as Relax NG"
        self._c_schema = relaxng.xmlRelaxNGParse(parser_ctxt)

        # XXX: freeing parser context will crash if document was not RNG!!
        #relaxng.xmlRelaxNGFreeParserCtxt(parser_ctxt)
        if self._c_schema is NULL:
            if fake_c_doc is not NULL:
                relaxng.xmlRelaxNGFreeParserCtxt(parser_ctxt)
                _destroyFakeDoc(doc._c_doc, fake_c_doc)
            raise RelaxNGParseError, "Document is not valid Relax NG"
        relaxng.xmlRelaxNGFreeParserCtxt(parser_ctxt)
        if fake_c_doc is not NULL:
            _destroyFakeDoc(doc._c_doc, fake_c_doc)
        self._error_log = _ErrorLog()
        
    def __dealloc__(self):
        relaxng.xmlRelaxNGFree(self._c_schema)
        
    def validate(self, etree):
        """Validate doc using Relax NG.

        Returns true if document is valid, false if not."""
        cdef _Document doc
        cdef _NodeBase root_node
        cdef xmlDoc* c_doc
        cdef relaxng.xmlRelaxNGValidCtxt* valid_ctxt
        cdef int ret

        doc = _documentOrRaise(etree)
        root_node = _rootNodeOf(etree)

        self._error_log.connect()
        valid_ctxt = relaxng.xmlRelaxNGNewValidCtxt(self._c_schema)

        c_doc = _fakeRootDoc(doc._c_doc, root_node._c_node)
        ret = relaxng.xmlRelaxNGValidateDoc(valid_ctxt, c_doc)
        _destroyFakeDoc(doc._c_doc, c_doc)

        relaxng.xmlRelaxNGFreeValidCtxt(valid_ctxt)
        self._error_log.disconnect()
        if ret == -1:
            raise RelaxNGValidateError, "Internal error in Relax NG validation"
        return ret == 0

    property error_log:
        def __get__(self):
            return self._error_log.copy()
