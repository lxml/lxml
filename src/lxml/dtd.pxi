# support for DTD validation
from lxml.includes cimport dtdvalid

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

cdef inline int _assertValidDTDNode(node, void *c_node) except -1:
    assert c_node is not NULL, u"invalid DTD proxy at %s" % id(node)

@cython.internal
cdef class _DTDElementContentDecl:
    cdef DTD _dtd
    cdef tree.xmlElementContent* _c_node

    def __cinit__(self):
        self._c_node = NULL

    def __repr__(self):
        return "<%s.%s object name=%r type=%r occur=%r at 0x%x>" % (self.__class__.__module__, self.__class__.__name__, self.name, self.type, self.occur, id(self))

    property name:
       def __get__(self):
           _assertValidDTDNode(self, self._c_node)
           return funicode(self._c_node.name) if self._c_node.name is not NULL else None

    property type:
       def __get__(self):
           _assertValidDTDNode(self, self._c_node)
           type = self._c_node.type
           if type == tree.XML_ELEMENT_CONTENT_PCDATA:
               return "pcdata"
           elif type == tree.XML_ELEMENT_CONTENT_ELEMENT:
               return "element"
           elif type == tree.XML_ELEMENT_CONTENT_SEQ:
               return "seq"
           elif type == tree.XML_ELEMENT_CONTENT_OR:
               return "or"
           else:
               return None

    property occur:
       def __get__(self):
           _assertValidDTDNode(self, self._c_node)
           occur = self._c_node.ocur
           if occur == tree.XML_ELEMENT_CONTENT_ONCE:
               return "once"
           elif occur == tree.XML_ELEMENT_CONTENT_OPT:
               return "opt"
           elif occur == tree.XML_ELEMENT_CONTENT_MULT:
               return "mult"
           elif occur == tree.XML_ELEMENT_CONTENT_PLUS:
               return "plus"
           else:
               return None

    property left:
       def __get__(self):
           _assertValidDTDNode(self, self._c_node)
           c1 = self._c_node.c1
           if c1 is not NULL:
               node = _DTDElementContentDecl()
               node._dtd = self._dtd
               node._c_node = <tree.xmlElementContent*>c1
               return node
           else:
               return None

    property right:
       def __get__(self):
           _assertValidDTDNode(self, self._c_node)
           c2 = self._c_node.c2
           if c2 is not NULL:
               node = _DTDElementContentDecl()
               node._dtd = self._dtd
               node._c_node = <tree.xmlElementContent*>c2
               return node
           else:
               return None

@cython.internal
cdef class _DTDAttributeDecl:
    cdef DTD _dtd
    cdef tree.xmlAttribute* _c_node

    def __cinit__(self):
        self._c_node = NULL

    def __repr__(self):
        return "<%s.%s object name=%r elemname=%r prefix=%r type=%r default=%r default_value=%r at 0x%x>" % (self.__class__.__module__, self.__class__.__name__, self.name, self.elemname, self.prefix, self.type, self.default, self.default_value, id(self))

    property name:
       def __get__(self):
           _assertValidDTDNode(self, self._c_node)
           return funicode(self._c_node.name) if self._c_node.name is not NULL else None

    property elemname:
       def __get__(self):
           _assertValidDTDNode(self, self._c_node)
           return funicode(self._c_node.elem) if self._c_node.elem is not NULL else None

    property prefix:
       def __get__(self):
           _assertValidDTDNode(self, self._c_node)
           return funicode(self._c_node.prefix) if self._c_node.prefix is not NULL else None

    property type:
       def __get__(self):
           _assertValidDTDNode(self, self._c_node)
           type = self._c_node.atype
           if type == tree.XML_ATTRIBUTE_CDATA:
               return "cdata"
           elif type == tree.XML_ATTRIBUTE_ID:
               return "id"
           elif type == tree.XML_ATTRIBUTE_IDREF:
               return "idref"
           elif type == tree.XML_ATTRIBUTE_IDREFS:
               return "idrefs"
           elif type == tree.XML_ATTRIBUTE_ENTITY:
               return "entity"
           elif type == tree.XML_ATTRIBUTE_ENTITIES:
               return "entities"
           elif type == tree.XML_ATTRIBUTE_NMTOKEN:
               return "nmtoken"
           elif type == tree.XML_ATTRIBUTE_NMTOKENS:
               return "nmtokens"
           elif type == tree.XML_ATTRIBUTE_ENUMERATION:
               return "enumeration"
           elif type == tree.XML_ATTRIBUTE_NOTATION:
               return "notation"
           else:
               return None

    property default:
       def __get__(self):
           _assertValidDTDNode(self, self._c_node)
           default = self._c_node.def_
           if default == tree.XML_ATTRIBUTE_NONE:
               return "none"
           elif default == tree.XML_ATTRIBUTE_REQUIRED:
               return "required"
           elif default == tree.XML_ATTRIBUTE_IMPLIED:
               return "implied"
           elif default == tree.XML_ATTRIBUTE_FIXED:
               return "fixed"
           else:
               return None

    property default_value:
       def __get__(self):
           _assertValidDTDNode(self, self._c_node)
           return funicode(self._c_node.defaultValue) if self._c_node.defaultValue is not NULL else None

    def itervalues(self):
        _assertValidDTDNode(self, self._c_node)
        cdef tree.xmlEnumeration *c_node = self._c_node.tree
        while c_node is not NULL:
            yield funicode(c_node.name)
            c_node = c_node.next

    def values(self):
        return list(self.itervalues())

@cython.internal
cdef class _DTDElementDecl:
    cdef DTD _dtd
    cdef tree.xmlElement* _c_node

    def __cinit__(self):
        self._c_node = NULL

    def __repr__(self):
        return "<%s.%s object name=%r prefix=%r type=%r at 0x%x>" % (self.__class__.__module__, self.__class__.__name__, self.name, self.prefix, self.type, id(self))

    property name:
        def __get__(self):
            _assertValidDTDNode(self, self._c_node)
            return funicode(self._c_node.name) if self._c_node.name is not NULL else None

    property prefix:
       def __get__(self):
           _assertValidDTDNode(self, self._c_node)
           return funicode(self._c_node.prefix) if self._c_node.prefix is not NULL else None

    property type:
        def __get__(self):
           _assertValidDTDNode(self, self._c_node)
           cdef int type = self._c_node.etype
           if type == tree.XML_ELEMENT_TYPE_UNDEFINED:
               return "undefined"
           elif type == tree.XML_ELEMENT_TYPE_EMPTY:
               return "empty"
           elif type == tree.XML_ELEMENT_TYPE_ANY:
               return "any"
           elif type == tree.XML_ELEMENT_TYPE_MIXED:
               return "mixed"
           elif type == tree.XML_ELEMENT_TYPE_ELEMENT:
               return "element"
           else:
               return None

    property content:
       def __get__(self):
           _assertValidDTDNode(self, self._c_node)
           cdef tree.xmlElementContent *content = self._c_node.content
           if content is not NULL:
               node = _DTDElementContentDecl()
               node._dtd = self._dtd
               node._c_node = content
               return node
           else:
               return None

    def iterattributes(self):
        _assertValidDTDNode(self, self._c_node)
        cdef tree.xmlAttribute *c_node = self._c_node.attributes
        while c_node is not NULL:
            node = _DTDAttributeDecl()
            node._dtd = self._dtd
            node._c_node = c_node
            yield node
            c_node = c_node.nexth

    def attributes(self):
        return list(self.iterattributes())

@cython.internal
cdef class _DTDEntityDecl:
    cdef DTD _dtd
    cdef tree.xmlEntity* _c_node

    def __cinit__(self):
        self._c_node = NULL

    def __repr__(self):
        return "<%s.%s object name=%r at 0x%x>" % (self.__class__.__module__, self.__class__.__name__, self.name, id(self))

    property name:
        def __get__(self):
            _assertValidDTDNode(self, self._c_node)
            return funicode(self._c_node.name) if self._c_node.name is not NULL else None

    property orig:
        def __get__(self):
            _assertValidDTDNode(self, self._c_node)
            return funicode(self._c_node.orig) if self._c_node.orig is not NULL else None

    property content:
        def __get__(self):
            _assertValidDTDNode(self, self._c_node)
            return funicode(self._c_node.content) if self._c_node.content is not NULL else None

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
                with self._error_log:
                    self._c_dtd = xmlparser.xmlParseDTD(NULL, _xcstr(file))
            elif hasattr(file, 'read'):
                self._c_dtd = _parseDtdFromFilelike(file)
            else:
                raise DTDParseError, u"file must be a filename or file-like object"
        elif external_id is not None:
            with self._error_log:
                self._c_dtd = xmlparser.xmlParseDTD(<const_xmlChar*>external_id, NULL)
        else:
            raise DTDParseError, u"either filename or external ID required"

        if self._c_dtd is NULL:
            raise DTDParseError(
                self._error_log._buildExceptionMessage(u"error parsing DTD"),
                self._error_log)

    property name:
       def __get__(self):
          return funicode(self._c_dtd.name) if (self._c_dtd is not NULL and self._c_dtd.name is not NULL) else None

    property external_id:
       def __get__(self):
          return funicode(self._c_dtd.ExternalID) if (self._c_dtd is not NULL and self._c_dtd.ExternalID is not NULL) else None

    property system_url:
       def __get__(self):
          return funicode(self._c_dtd.SystemID) if (self._c_dtd is not NULL and self._c_dtd.SystemID is not NULL) else None

    def iterelements(self):
        cdef tree.xmlNode *c_node = self._c_dtd.children if self._c_dtd is not NULL else NULL
        while c_node is not NULL:
            if c_node.type == tree.XML_ELEMENT_DECL:
                node = _DTDElementDecl()
                node._dtd = self
                node._c_node = <tree.xmlElement*>c_node
                yield node
            c_node = c_node.next

    def elements(self):
        return list(self.iterelements())

    def iterentities(self):
        cdef tree.xmlNode *c_node = self._c_dtd.children if self._c_dtd is not NULL else NULL
        while c_node is not NULL:
            if c_node.type == tree.XML_ENTITY_DECL:
                node = _DTDEntityDecl()
                node._dtd = self
                node._c_node = <tree.xmlEntity*>c_node
                yield node
            c_node = c_node.next

    def entities(self):
        return list(self.iterentities())

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
        cdef int ret = -1

        assert self._c_dtd is not NULL, "DTD not initialised"
        doc = _documentOrRaise(etree)
        root_node = _rootNodeOrRaise(etree)

        valid_ctxt = dtdvalid.xmlNewValidCtxt()
        if valid_ctxt is NULL:
            raise DTDError(u"Failed to create validation context")

        try:
            with self._error_log:
                c_doc = _fakeRootDoc(doc._c_doc, root_node._c_node)
                ret = dtdvalid.xmlValidateDtd(valid_ctxt, c_doc, self._c_dtd)
                _destroyFakeDoc(doc._c_doc, c_doc)
        finally:
            dtdvalid.xmlFreeValidCtxt(valid_ctxt)

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
    dtd_parser = _FileReaderContext(file, exc_context, None)
    error_log = _ErrorLog()

    with error_log:
        c_dtd = dtd_parser._readDtd()

    exc_context._raise_if_stored()
    if c_dtd is NULL:
        raise DTDParseError(u"error parsing DTD", error_log)
    return c_dtd

cdef DTD _dtdFactory(tree.xmlDtd* c_dtd):
    # do not run through DTD.__init__()!
    cdef DTD dtd
    if c_dtd is NULL:
        return None
    dtd = DTD.__new__(DTD)
    dtd._c_dtd = tree.xmlCopyDtd(c_dtd)
    if dtd._c_dtd is NULL:
        raise MemoryError()
    _Validator.__init__(dtd)
    return dtd
