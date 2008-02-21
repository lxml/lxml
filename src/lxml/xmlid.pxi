cdef object _find_id_attributes

def XMLID(text):
    """XMLID(text)

    Parse the text and return a tuple (root node, ID dictionary).  The root
    node is the same as returned by the XML() function.  The dictionary
    contains string-element pairs.  The dictionary keys are the values of 'id'
    attributes.  The elements referenced by the ID are stored as dictionary
    values.
    """
    global _find_id_attributes
    if _find_id_attributes is None:
        _find_id_attributes = XPath('//*[string(@id)]')

    # ElementTree compatible implementation: parse and look for 'id' attributes
    root = XML(text)
    dic = {}
    for elem in _find_id_attributes(root):
        python.PyDict_SetItem(dic, elem.get('id'), elem)
    return (root, dic)

def XMLDTDID(text):
    """XMLDTDID(text)

    Parse the text and return a tuple (root node, ID dictionary).  The root
    node is the same as returned by the XML() function.  The dictionary
    contains string-element pairs.  The dictionary keys are the values of ID
    attributes as defined by the DTD.  The elements referenced by the ID are
    stored as dictionary values.

    Note that you must not modify the XML tree if you use the ID dictionary.
    The results are undefined.
    """
    cdef _Element root
    root = XML(text)
    # xml:id spec compatible implementation: use DTD ID attributes from libxml2
    if root._doc._c_doc.ids is NULL:
        return (root, {})
    else:
        return (root, _IDDict(root))

def parseid(source, parser=None, *, base_url=None):
    """parseid(source, parser=None)

    Parses the source into a tuple containing an ElementTree object and an
    ID dictionary.  If no parser is provided as second argument, the default
    parser is used.

    Note that you must not modify the XML tree if you use the ID dictionary.
    The results are undefined.
    """
    cdef _Document doc
    doc = _parseDocument(source, parser, base_url)
    return (_elementTreeFactory(doc, None), _IDDict(doc))

cdef class _IDDict:
    """IDDict(self, etree)
    A dictionary-like proxy class that mapps ID attributes to elements.

    The dictionary must be instantiated with the root element of a parsed XML
    document, otherwise the behaviour is undefined.  Elements and XML trees
    that were created or modified 'by hand' are not supported.
    """
    cdef _Document _doc
    cdef object _keys
    cdef object _items
    def __init__(self, etree):
        cdef _Document doc
        doc = _documentOrRaise(etree)
        if doc._c_doc.ids is NULL:
            raise ValueError("No ID dictionary available.")
        self._doc = doc
        self._keys  = None
        self._items = None

    def copy(self):
        return _IDDict(self._doc)

    def __getitem__(self, id_name):
        cdef tree.xmlHashTable* c_ids
        cdef tree.xmlID* c_id
        cdef xmlAttr* c_attr
        c_ids = self._doc._c_doc.ids
        id_utf = _utf8(id_name)
        c_id = <tree.xmlID*>tree.xmlHashLookup(c_ids, _cstr(id_utf))
        if c_id is NULL:
            raise KeyError("key not found.")
        c_attr = c_id.attr
        if c_attr is NULL or c_attr.parent is NULL:
            raise KeyError("ID attribute not found.")
        return _elementFactory(self._doc, c_attr.parent)

    def get(self, id_name):
        return self[id_name]

    def __contains__(self, id_name):
        cdef tree.xmlID* c_id
        id_utf = _utf8(id_name)
        c_id = <tree.xmlID*>tree.xmlHashLookup(
            self._doc._c_doc.ids, _cstr(id_utf))
        return c_id is not NULL

    def has_key(self, id_name):
        return id_name in self

    def __cmp__(self, other):
        if other is None:
            return 1
        else:
            return cmp(dict(self), other)

    def __richcmp__(self, other, int op):
        cdef int c_cmp
        if other is None:
            return op == 0 or op == 1 or op == 3
        c_cmp = cmp(dict(self), other)
        if c_cmp == 0: # equal
            return op == 1 or op == 2 or op == 5
        elif c_cmp < 0:
            return op == 0 or op == 1 or op == 3
        else:
            return op == 4 or op == 5 or op == 3

    def __repr__(self):
        return repr(dict(self))

    def keys(self):
        if self._keys is None:
            self._keys = self._build_keys()
        return self._keys[:]

    def __iter__(self):
        if self._keys is None:
            self._keys = self._build_keys()
        return iter(self._keys)

    def iterkeys(self):
        return self

    def __len__(self):
        if self._keys is None:
            self._keys = self._build_keys()
        return len(self._keys)

    def items(self):
        if self._items is None:
            self._items = self._build_items()
        return self._items[:]

    def iteritems(self):
        if self._items is None:
            self._items = self._build_items()
        return iter(self._items)

    def values(self):
        if self._items is None:
            self._items = self._build_items()
        values = []
        for item in self._items:
            value = python.PyTuple_GET_ITEM(item, 1)
            python.Py_INCREF(value)
            python.PyList_Append(values, value)
        return values

    def itervalues(self):
        return iter(self.values())

    cdef object _build_keys(self):
        keys = []
        tree.xmlHashScan(<tree.xmlHashTable*>self._doc._c_doc.ids,
                         _collectIdHashKeys, <python.PyObject*>keys)
        return keys

    cdef object _build_items(self):
        items = []
        context = (items, self._doc)
        tree.xmlHashScan(<tree.xmlHashTable*>self._doc._c_doc.ids,
                         _collectIdHashItemList, <python.PyObject*>context)
        return items

cdef void _collectIdHashItemDict(void* payload, void* context, char* name):
    # collect elements from ID attribute hash table
    cdef tree.xmlID* c_id
    c_id = <tree.xmlID*>payload
    if c_id is NULL or c_id.attr is NULL or c_id.attr.parent is NULL:
        return
    dic, doc = <object>context
    element = _elementFactory(doc, c_id.attr.parent)
    python.PyDict_SetItem(dic, funicode(name), element)

cdef void _collectIdHashItemList(void* payload, void* context, char* name):
    # collect elements from ID attribute hash table
    cdef tree.xmlID* c_id
    c_id = <tree.xmlID*>payload
    if c_id is NULL or c_id.attr is NULL or c_id.attr.parent is NULL:
        return
    lst, doc = <object>context
    element = _elementFactory(doc, c_id.attr.parent)
    python.PyList_Append(lst, (funicode(name), element))

cdef void _collectIdHashKeys(void* payload, void* collect_list, char* name):
    cdef tree.xmlID* c_id
    c_id = <tree.xmlID*>payload
    if c_id is NULL or c_id.attr is NULL or c_id.attr.parent is NULL:
        return
    python.PyList_Append(<object>collect_list, funicode(name))
