# read-only tree implementation

cdef class _ReadOnlyElementProxy:
    "The main read-only Element proxy class (for internal use only!)."
    cdef xmlNode* _c_node
    cdef object _source_proxy
    cdef object _dependent_proxies

    cdef int _assertNode(self) except -1:
        """This is our way of saying: this proxy is invalid!
        """
        assert self._c_node is not NULL, "Proxy invalidated!"
        return 0

    property tag:
        """Element tag
        """
        def __get__(self):
            self._assertNode()
            return _namespacedName(self._c_node)

    property text:
        """Text before the first subelement. This is either a string or 
        the value None, if there was no text.
        """
        def __get__(self):
            self._assertNode()
            return _collectText(self._c_node.children)
        
    property tail:
        """Text after this element's end tag, but before the next sibling
        element's start tag. This is either a string or the value None, if
        there was no text.
        """
        def __get__(self):
            self._assertNode()
            return _collectText(self._c_node.next)

    property attrib:
        def __get__(self):
            self._assertNode()
            return dict(_collectAttributes(self._c_node, 3))

    property prefix:
        """Namespace prefix or None.
        """
        def __get__(self):
            self._assertNode()
            if self._c_node.ns is not NULL:
                if self._c_node.ns.prefix is not NULL:
                    return funicode(self._c_node.ns.prefix)
            return None

    property sourceline:
        """Original line number as found by the parser or None if unknown.
        """
        def __get__(self):
            cdef long line
            self._assertNode()
            line = tree.xmlGetLineNo(self._c_node)
            if line > 0:
                return line
            else:
                return None

    def __repr__(self):
        return "<Element %s at %x>" % (self.tag, id(self))
    
    def __getitem__(self, Py_ssize_t index):
        """Returns the subelement at the given position.
        """
        cdef xmlNode* c_node
        c_node = _findChild(self._c_node, index)
        if c_node is NULL:
            raise IndexError("list index out of range")
        return _newReadOnlyProxy(self._source_proxy, c_node)

    def __getslice__(self, Py_ssize_t start, Py_ssize_t stop):
        """Returns a list containing subelements in the given range.
        """
        cdef xmlNode* c_node
        cdef Py_ssize_t c
        c_node = _findChild(self._c_node, start)
        if c_node is NULL:
            return []
        c = start
        result = []
        while c_node is not NULL and c < stop:
            if tree._isElement(c_node):
                python.PyList_Append(
                    result, _newReadOnlyProxy(self._source_proxy, c_node))
                c = c + 1
            c_node = c_node.next
        return result

    def __len__(self):
        """Returns the number of subelements.
        """
        cdef Py_ssize_t c
        cdef xmlNode* c_node
        self._assertNode()
        c = 0
        c_node = self._c_node.children
        while c_node is not NULL:
            if tree._isElement(c_node):
                c = c + 1
            c_node = c_node.next
        return c

    def __nonzero__(self):
        cdef xmlNode* c_node
        self._assertNode()
        c_node = _findChildBackwards(self._c_node, 0)
        return c_node != NULL

    def __iter__(self):
        return iter(self.getchildren())

    def iterchildren(self, tag=None, *, reversed=False):
        """iterchildren(self, tag=None, reversed=False)

        Iterate over the children of this element.
        """
        children = self.getchildren()
        if tag is not None:
            children = [ el for el in children if el.tag == tag ]
        if reversed:
            children = children[::-1]
        return iter(children)

    def get(self, key, default=None):
        """Gets an element attribute.
        """
        self._assertNode()
        return _getNodeAttributeValue(self._c_node, key, default)

    def keys(self):
        """Gets a list of attribute names. The names are returned in an
        arbitrary order (just like for an ordinary Python dictionary).
        """
        self._assertNode()
        return _collectAttributes(self._c_node, 1)

    def values(self):
        """Gets element attributes, as a sequence. The attributes are returned
        in an arbitrary order.
        """
        self._assertNode()
        return _collectAttributes(self._c_node, 2)

    def items(self):
        """Gets element attributes, as a sequence. The attributes are returned
        in an arbitrary order.
        """
        self._assertNode()
        return _collectAttributes(self._c_node, 3)

    cpdef getchildren(self):
        """Returns all subelements. The elements are returned in document
        order.
        """
        cdef xmlNode* c_node
        self._assertNode()
        result = []
        c_node = self._c_node.children
        while c_node is not NULL:
            if tree._isElement(c_node):
                python.PyList_Append(
                    result, _newReadOnlyProxy(self._source_proxy, c_node))
            c_node = c_node.next
        return result

    def getparent(self):
        """Returns the parent of this element or None for the root element.
        """
        cdef xmlNode* c_parent
        self._assertNode()
        c_parent = self._c_node.parent
        if c_parent is NULL or not tree._isElement(c_parent):
            return None
        else:
            return _newReadOnlyProxy(self._source_proxy, c_parent)

    def getnext(self):
        """Returns the following sibling of this element or None.
        """
        cdef xmlNode* c_node
        self._assertNode()
        c_node = _nextElement(self._c_node)
        if c_node is not NULL:
            return _newReadOnlyProxy(self._source_proxy, c_node)
        return None

    def getprevious(self):
        """Returns the preceding sibling of this element or None.
        """
        cdef xmlNode* c_node
        self._assertNode()
        c_node = _previousElement(self._c_node)
        if c_node is not NULL:
            return _newReadOnlyProxy(self._source_proxy, c_node)
        return None


cdef extern from "etree_defs.h":
    # macro call to 't->tp_new()' for fast instantiation
    cdef _ReadOnlyElementProxy NEW_RO_PROXY "PY_NEW" (object t)

cdef _ReadOnlyElementProxy _newReadOnlyProxy(
    _ReadOnlyElementProxy sourceProxy, xmlNode* c_node):
    cdef _ReadOnlyElementProxy el
    el = NEW_RO_PROXY(_ReadOnlyElementProxy)
    el._c_node = c_node
    if sourceProxy is None:
        el._source_proxy = el
        el._dependent_proxies = [el]
    else:
        el._source_proxy = sourceProxy
        python.PyList_Append(sourceProxy._dependent_proxies, el)
    return el

cdef _freeReadOnlyProxies(_ReadOnlyElementProxy sourceProxy):
    cdef _ReadOnlyElementProxy el
    if sourceProxy is None:
        return
    if sourceProxy._dependent_proxies is None:
        return
    for el in sourceProxy._dependent_proxies:
        el._c_node = NULL
    del sourceProxy._dependent_proxies[:]
