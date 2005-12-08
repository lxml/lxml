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
    """Turn a document into an Relax NG validator.
    Can also load from filesystem directly given file object or filename.
    """
    cdef relaxng.xmlRelaxNG* _c_schema
    
    def __init__(self, _ElementTree etree=None, file=None):
        cdef relaxng.xmlRelaxNGParserCtxt* parser_ctxt

        if etree is not None:
            parser_ctxt = relaxng.xmlRelaxNGNewDocParserCtxt(etree._doc._c_doc)
        elif file is not None:
            filename = _getFilenameForFile(file)
            if filename is None:
                # XXX assume a string object
                filename = file
            parser_ctxt = relaxng.xmlRelaxNGNewParserCtxt(filename)
        else:
            raise RelaxNGParseError, "No tree or file given"
        if parser_ctxt is NULL:
            raise RelaxNGParseError, "Document is not parsable as Relax NG"
        self._c_schema = relaxng.xmlRelaxNGParse(parser_ctxt)
        if self._c_schema is NULL:
            raise RelaxNGParseError, "Document is not valid Relax NG"
        relaxng.xmlRelaxNGFreeParserCtxt(parser_ctxt)
        
    def __dealloc__(self):
        relaxng.xmlRelaxNGFree(self._c_schema)
        
    def validate(self, _ElementTree etree):
        """Validate doc using Relax NG.

        Returns true if document is valid, false if not."""
        cdef xmlDoc* c_doc
        cdef relaxng.xmlRelaxNGValidCtxt* valid_ctxt
        cdef int ret
        valid_ctxt = relaxng.xmlRelaxNGNewValidCtxt(self._c_schema)

        c_doc = _fakeRootDoc(etree._doc._c_doc, etree._context_node._c_node)
        ret = relaxng.xmlRelaxNGValidateDoc(valid_ctxt, c_doc)
        _destroyFakeDoc(etree._doc._c_doc, c_doc)

        relaxng.xmlRelaxNGFreeValidCtxt(valid_ctxt)
        if ret == -1:
            raise RelaxNGValidateError, "Internal error in Relax NG validation"
        return ret == 0

