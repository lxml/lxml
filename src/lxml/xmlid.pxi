# Created at import time: threads that called XMLID() first could replace each other's.
cdef object _find_id_attributes = XPath('//*[string(@id)]')

def XMLID(text, parser=None, *, base_url=None):
    """XMLID(text, parser=None, base_url=None)

    Parse the text and return a tuple (root node, ID dictionary).  The root
    node is the same as returned by the XML() function.  The dictionary
    contains string-element pairs.  The dictionary keys are the values of 'id'
    attributes.  The elements referenced by the ID are stored as dictionary
    values.
    """
    cdef dict dic

    # ElementTree compatible implementation: parse and look for 'id' attributes
    root = XML(text, parser, base_url=base_url)
    dic = {}
    for elem in _find_id_attributes(root):
        dic[elem.get('id')] = elem
    return root, dic

def XMLDTDID(text, parser=None, *, base_url=None):
    """XMLDTDID(text, parser=None, base_url=None)

    Parse the text and return a tuple (root node, ID dictionary).  The root
    node is the same as returned by the XML() function.  The dictionary
    contains string-element pairs.  The dictionary keys are the values of ID
    attributes as defined by the DTD.  The elements referenced by the ID are
    stored as dictionary values.

    Note that you must not modify the XML tree if you use the ID dictionary.
    The results are undefined.
    """
    cdef _Element root
    root = <_Element?> XML(text, parser, base_url=base_url)
    # xml:id spec compatible implementation: use DTD ID attributes from libxml2
    if root._doc._c_doc.ids is NULL:
        return root, {}
    else:
        return root, _IDDict(root)

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
    return _elementTreeFactory(doc, None), _IDDict(doc)


cdef class _IDDict:
    """IDDict(self, etree)
    A dictionary-like proxy class that mapps ID attributes to elements.

    The dictionary must be instantiated with the root element of a parsed XML
    document, otherwise the behaviour is undefined.  Elements and XML trees
    that were created or modified 'by hand' are not supported.
    """
    cdef _Document _doc
    # Snapshots of the keys and items, built on first use and then never changed.
    # The flags tell that they are set, so that readers need no lock.
    cdef list _keys
    cdef list _items
    cdef atomic_int _keys_set
    cdef atomic_int _items_set

    def __cinit__(self, etree):
        cdef _Document doc
        cdef bint has_ids
        doc = _documentOrRaise(etree)
        # The ID table is changed by tree modifications (under the write lock) => read lock.
        doc.lock_read()
        has_ids = doc._c_doc.ids is not NULL
        doc.unlock_read()
        if not has_ids:
            raise ValueError, "No ID dictionary available."
        self._doc = doc
        self._keys  = None
        self._items = None

    def copy(self):
        return _IDDict(self._doc)

    def __getitem__(self, id_name):
        cdef tree.xmlID* c_id
        cdef xmlAttr* c_attr
        id_utf = _utf8(id_name)
        doc = self._doc
        doc.lock_read()
        try:
            c_id = <tree.xmlID*>tree.xmlHashLookup(doc._c_doc.ids, _xcstr(id_utf))
            if c_id is NULL:
                raise KeyError, "key not found."
            c_attr = c_id.attr
            if c_attr is NULL or c_attr.parent is NULL:
                raise KeyError, "ID attribute not found."
            return _elementFactory(doc, c_attr.parent)
        finally:
            doc.unlock_read()

    def get(self, id_name):
        return self[id_name]

    def __contains__(self, id_name):
        cdef tree.xmlID* c_id
        id_utf = _utf8(id_name)
        doc = self._doc
        doc.lock_read()
        c_id = <tree.xmlID*>tree.xmlHashLookup(doc._c_doc.ids, _xcstr(id_utf))
        doc.unlock_read()
        return c_id is not NULL

    def has_key(self, id_name):
        return id_name in self

    def __repr__(self):
        return repr(dict(self))

    def keys(self):
        return self._key_list()[:]

    def __iter__(self):
        return iter(self._key_list())

    def iterkeys(self):
        return self

    def __len__(self):
        return len(self._key_list())

    def items(self):
        return self._item_list()[:]

    def iteritems(self):
        return iter(self._item_list())

    def values(self):
        return [(<tuple> item)[1] for item in self._item_list()]

    def itervalues(self):
        return iter(self.values())

    @cython.final
    cdef list _key_list(self):
        if not atomic_load(&self._keys_set):
            keys = self._build_keys()
            with cython.critical_section(self):
                # The first thread that built the list sets it.
                if self._keys is None:
                    self._keys = keys
                    atomic_add(&self._keys_set, 1)
        return self._keys

    @cython.final
    cdef list _item_list(self):
        if not atomic_load(&self._items_set):
            items = self._build_items()
            with cython.critical_section(self):
                # The first thread that built the list sets it.
                if self._items is None:
                    self._items = items
                    atomic_add(&self._items_set, 1)
        return self._items

    @cython.final
    cdef list _build_keys(self):
        keys = []
        doc = self._doc
        doc.lock_read()
        try:
            tree.xmlHashScan(<tree.xmlHashTable*>doc._c_doc.ids,
                             <tree.xmlHashScanner>_collectIdHashKeys, <python.PyObject*>keys)
        finally:
            doc.unlock_read()
        return keys

    @cython.final
    cdef list _build_items(self):
        items = []
        doc = self._doc
        context = (items, doc)
        doc.lock_read()
        try:
            tree.xmlHashScan(<tree.xmlHashTable*>doc._c_doc.ids,
                             <tree.xmlHashScanner>_collectIdHashItemList, <python.PyObject*>context)
        finally:
            doc.unlock_read()
        return items


cdef void _collectIdHashItemList(void* payload, void* context, xmlChar* name) noexcept:
    # collect elements from ID attribute hash table
    cdef list lst
    c_id = <tree.xmlID*>payload
    if c_id is NULL or c_id.attr is NULL or c_id.attr.parent is NULL:
        return
    lst, doc = <tuple>context
    element = _elementFactory(doc, c_id.attr.parent)
    lst.append( (funicode(name), element) )


cdef void _collectIdHashKeys(void* payload, void* collect_list, xmlChar* name) noexcept:
    c_id = <tree.xmlID*>payload
    if c_id is NULL or c_id.attr is NULL or c_id.attr.parent is NULL:
        return
    (<list>collect_list).append(funicode(name))
