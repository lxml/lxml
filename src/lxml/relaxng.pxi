# support for RelaxNG validation
from lxml.includes cimport relaxng

cdef object _rnc2rng
try:
    import rnc2rng as _rnc2rng
except ImportError:
    _rnc2rng = None


cdef int _require_rnc2rng() except -1:
    if _rnc2rng is None:
        raise RelaxNGParseError(
            'compact syntax not supported (please install rnc2rng)')
    return 0


class RelaxNGError(LxmlError):
    """Base class for RelaxNG errors.
    """

class RelaxNGParseError(RelaxNGError):
    """Error while parsing an XML document as RelaxNG.
    """

class RelaxNGValidateError(RelaxNGError):
    """Error while validating an XML document with a RelaxNG schema.
    """


# Data types of the XML Schema datatype library whose validation adds the attributes
# that hold them to the ID and IDREF tables of the validated document (see _ID_TYPE_NAMES).
# Included or referenced schema documents are out of reach, so assume that they use them.
cdef XPath _check_for_relaxng_id_types = XPath(
    "boolean(descendant-or-self::rng:include | descendant-or-self::rng:externalRef | "
    "descendant-or-self::rng:data[contains(' ID IDREF IDREFS ENTITY ENTITIES ', "
    "                                      concat(' ', normalize-space(@type), ' '))])",
    namespaces={'rng': 'http://relaxng.org/ns/structure/1.0'})


################################################################################
# RelaxNG

cdef class RelaxNG(_Validator):
    """RelaxNG(self, etree=None, file=None)
    Turn a document into a Relax NG validator.

    Either pass a schema as Element or ElementTree, or pass a file or
    filename through the ``file`` keyword argument.
    """
    cdef relaxng.xmlRelaxNG* _c_schema
    cdef bint _uses_id_types

    def __cinit__(self):
        self._uses_id_types = True # play it safe

    def __init__(self, etree=None, *, file=None):
        if self._c_schema is not NULL:
            raise RuntimeError("Repeated call to RelaxNG.__init__()")

        cdef _Document doc
        cdef _Element root_node
        cdef xmlDoc* fake_c_doc = NULL
        cdef relaxng.xmlRelaxNGParserCtxt* parser_ctxt = NULL
        cdef bint write_locked = False
        _Validator.__init__(self)
        if etree is not None:
            doc = _documentOrRaise(etree)
            root_node = _rootNodeOrRaise(etree)
            self._uses_id_types = _check_for_relaxng_id_types(root_node)
            write_locked = doc.lock_fakedoc(root_node._c_node)
            try:
                fake_c_doc = _fakeRootDoc(doc._c_doc, root_node._c_node)
            except:
                doc.unlock_fakedoc(write_locked)
                raise
            parser_ctxt = relaxng.xmlRelaxNGNewDocParserCtxt(fake_c_doc)
        elif file is not None:
            if isinstance(file, str):
                if file[-4:].lower() == '.rnc':
                    _require_rnc2rng()
                    rng_data_utf8 = _utf8(_rnc2rng.dumps(_rnc2rng.load(file)))
                    doc = _parseMemoryDocument(rng_data_utf8, parser=None, url=file)
                    self._uses_id_types = _check_for_relaxng_id_types(doc)
                    parser_ctxt = relaxng.xmlRelaxNGNewDocParserCtxt(doc._c_doc)
                else:
                    doc = None
                    filename = _encodeFilename(file)
                    with self._error_log, lxml_document_loader:
                        parser_ctxt = relaxng.xmlRelaxNGNewParserCtxt(_cstr(filename))
            elif (_getFilenameForFile(file) or '')[-4:].lower() == '.rnc':
                _require_rnc2rng()
                rng_data_utf8 = _utf8(_rnc2rng.dumps(_rnc2rng.load(file)))
                doc = _parseMemoryDocument(
                    rng_data_utf8, parser=None, url=_getFilenameForFile(file))
                self._uses_id_types = _check_for_relaxng_id_types(doc)
                parser_ctxt = relaxng.xmlRelaxNGNewDocParserCtxt(doc._c_doc)
            else:
                doc = _parseDocument(file, parser=None, base_url=None)
                self._uses_id_types = _check_for_relaxng_id_types(doc)
                parser_ctxt = relaxng.xmlRelaxNGNewDocParserCtxt(doc._c_doc)
        else:
            raise RelaxNGParseError, "No tree or file given"

        if parser_ctxt is NULL:
            if fake_c_doc is not NULL:
                _destroyFakeDoc(doc._c_doc, fake_c_doc)
                doc.unlock_fakedoc(write_locked)
            raise RelaxNGParseError(
                self._error_log._buildExceptionMessage(
                    "Document is not parsable as Relax NG"),
                self._error_log)

        # Need a cast here because older libxml2 releases do not use 'const' in the functype.
        relaxng.xmlRelaxNGSetParserStructuredErrors(
            parser_ctxt, <xmlerror.xmlStructuredErrorFunc> _receiveError, <void*>self._error_log)
        _connectGenericErrorLog(self._error_log, xmlerror.XML_FROM_RELAXNGP)
        old_resource_loader = _register_relaxng_resource_loader(parser_ctxt)
        self._c_schema = relaxng.xmlRelaxNGParse(parser_ctxt)
        _reset_resource_loader(old_resource_loader)
        _connectGenericErrorLog(None)

        relaxng.xmlRelaxNGFreeParserCtxt(parser_ctxt)
        if fake_c_doc is not NULL:
            _destroyFakeDoc(doc._c_doc, fake_c_doc)
            doc.unlock_fakedoc(write_locked)

        if self._c_schema is NULL:
            raise RelaxNGParseError(
                self._error_log._buildExceptionMessage(
                    "Document is not valid Relax NG"),
                self._error_log)

    def __dealloc__(self):
        relaxng.xmlRelaxNGFree(self._c_schema)

    def __call__(self, etree):
        """__call__(self, etree)

        Validate doc using Relax NG.

        Returns true if document is valid, false if not."""
        cdef _Document doc
        cdef _Element root_node
        cdef relaxng.xmlRelaxNGValidCtxt* valid_ctxt
        cdef tree.xmlHashTable* c_refs = NULL
        cdef int ret

        assert self._c_schema is not NULL, "RelaxNG instance not initialised"
        doc = _documentOrRaise(etree)
        root_node = _rootNodeOrRaise(etree)

        valid_ctxt = relaxng.xmlRelaxNGNewValidCtxt(self._c_schema)
        if valid_ctxt is NULL:
            raise MemoryError()

        cdef bint uses_id_types = self._uses_id_types
        cdef bint write_locked = uses_id_types
        if uses_id_types:
            # Validation adds attributes to the ID and IDREF tables of the document.
            doc.lock_write()
        else:
            write_locked = doc.lock_fakedoc(root_node._c_node)
        try:
            self._error_log.clear()
            # Need a cast here because older libxml2 releases do not use 'const' in the functype.
            relaxng.xmlRelaxNGSetValidStructuredErrors(
                valid_ctxt, <xmlerror.xmlStructuredErrorFunc> _receiveError, <void*>self._error_log)
            _connectGenericErrorLog(self._error_log, xmlerror.XML_FROM_RELAXNGV)
            if uses_id_types:
                c_refs = _replaceIdRefTable(doc._c_doc, NULL)
            try:
                ret = _validateRelaxNGKeepingPsvi(valid_ctxt, doc, root_node._c_node)
            finally:
                if uses_id_types:
                    _freeIdRefTable(_replaceIdRefTable(doc._c_doc, c_refs))
        finally:
            doc.unlock_fakedoc(write_locked)
            _connectGenericErrorLog(None)
            relaxng.xmlRelaxNGFreeValidCtxt(valid_ctxt)

        if ret == -1:
            raise RelaxNGValidateError(
                "Internal error in Relax NG validation",
                self._error_log)
        if ret == 0:
            return True
        else:
            return False

    @classmethod
    def from_rnc_string(cls, src, base_url=None):
        """Parse a RelaxNG schema in compact syntax from a text string

        Requires the rnc2rng package to be installed.

        Passing the source URL or file path of the source as 'base_url'
        will enable resolving resource references relative to the source.
        """
        _require_rnc2rng()
        rng_str = utf8(_rnc2rng.dumps(_rnc2rng.loads(src)))
        return cls(_parseMemoryDocument(rng_str, parser=None, url=base_url))


cdef struct _ElementPsvi:
    xmlNode* c_node
    void* psvi


cdef Py_ssize_t _collectElementPsvi(xmlNode* c_node, _ElementPsvi* c_saved,
                                    Py_ssize_t max_count) noexcept nogil:
    """Count the elements below 'c_node' (inclusive) whose 'psvi' field is set, and store
    the first 'max_count' of them with that value in 'c_saved'.
    """
    cdef Py_ssize_t count = 0
    cdef xmlNode* c_element = c_node
    tree.BEGIN_FOR_EACH_ELEMENT_FROM(c_node, c_element, 1)
    if c_element.type == tree.XML_ELEMENT_NODE and c_element.psvi is not NULL:
        if count < max_count:
            c_saved[count].c_node = c_element
            c_saved[count].psvi = c_element.psvi
        count += 1
    tree.END_FOR_EACH_ELEMENT_FROM(c_element)
    return count


cdef int _validateRelaxNGKeepingPsvi(relaxng.xmlRelaxNGValidCtxt* valid_ctxt, _Document doc,
                                     xmlNode* c_node) except? -1:
    """Validate an element of the document and its descendants without changing the 'psvi'
    fields of the elements.

    xmlRelaxNGValidateDoc() marks the elements that it validated in their 'psvi' fields and
    resets these to NULL when it is done, but libxslt keeps the ids of generate-id() there
    while it transforms the document, during which Python extensions may validate it (or wait
    for other threads that do).  Restore them afterwards, and keep out the other RelaxNG
    validations of the document meanwhile, which also change these fields.

    Transformations hold the update lock of their input document from before libxslt runs
    until it is done, so the fields need saving only while a thread holds it.
    """
    cdef _ElementPsvi* c_saved = NULL
    cdef Py_ssize_t count = 0, i
    cdef xmlDoc* c_doc
    cdef int ret
    cdef bint locked = doc.lock_psvi()
    try:
        if doc._lock.is_update_locked():
            with nogil:
                count = _collectElementPsvi(c_node, NULL, 0)
        if count:
            c_saved = <_ElementPsvi*> python.lxml_malloc(count, sizeof(_ElementPsvi))
            if c_saved is NULL:
                raise MemoryError()
            count = min(count, _collectElementPsvi(c_node, c_saved, count))

        c_doc = _fakeRootDoc(doc._c_doc, c_node)
        with nogil:
            ret = relaxng.xmlRelaxNGValidateDoc(valid_ctxt, c_doc)
        _destroyFakeDoc(doc._c_doc, c_doc)

        for i in range(count):
            c_saved[i].c_node.psvi = c_saved[i].psvi
    finally:
        python.lxml_free(c_saved)
        doc.unlock_psvi(locked)
    return ret


cdef xmlparser.xmlExternalEntityLoader _register_relaxng_resource_loader(relaxng.xmlRelaxNGParserCtxt *rng_ctxt) noexcept nogil:
    if tree.LIBXML_VERSION < 21400:
        return _register_resource_loader()
    # libxml2 2.14 has per-context document loaders.
    relaxng.xmlRelaxNGSetResourceLoader(rng_ctxt, <xmlparser.xmlResourceLoader> _local_resource_loader, NULL)
    return NULL
