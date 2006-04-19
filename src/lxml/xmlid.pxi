from UserDict import DictMixin

def XMLID(text):
    """Parse the text and return a tuple (root node, ID dictionary).  The root
    node is the same as returned by the XML() function.  The dictionary
    contains string-element pairs.  The dictionary keys are the values of 'id'
    attributes.  The elements referenced by the ID are stored as dictionary
    values.
    """
    root = XML(text)
    # ElementTree compatible implementation: look for 'id' attributes
    dic = {}
    for elem in root.xpath('//*[string(@id)]'):
        python.PyDict_SetItem(dic, elem.get('id'), elem)
    return (root, dic)

def XMLDTDID(text):
    """Parse the text and return a tuple (root node, ID dictionary).  The root
    node is the same as returned by the XML() function.  The dictionary
    contains string-element pairs.  The dictionary keys are the values of ID
    attributes as defined by the DTD.  The elements referenced by the ID are
    stored as dictionary values.
    """
    cdef _NodeBase root
    root = XML(text)
    # xml:id spec compatible implementation: use DTD ID attributes from libxml2
    if root._doc._c_doc.ids is NULL:
        return (root, {})
    else:
        return (root, _IDDict(root))

class _IDDict(DictMixin):
    """A dictionary class that mapps ID attributes to elements.

    The dictionary must be instantiated with the root element of a parsed XML
    document, otherwise the behaviour is undefined.  Elements and XML trees
    that were created or modified through the API are not supported.
    """
    def __init__(self, etree):
        cdef _Document doc
        doc = _documentOrRaise(etree)
        if doc._c_doc.ids is NULL:
            raise ValueError, "No ID dictionary available."
        self.__doc = doc
        self.__keys  = None
        self.__items = None

    def copy(self):
        return IDDict(self._doc)

    def __getitem__(self, id_name):
        cdef tree.xmlHashTable* c_ids
        cdef tree.xmlID* c_id
        cdef xmlAttr* c_attr
        cdef _Document doc
        doc = self.__doc
        c_ids = doc._c_doc.ids
        id_utf = _utf8(id_name)
        c_id = <tree.xmlID*>tree.xmlHashLookup(c_ids, _cstr(id_utf))
        if c_id is NULL:
            raise KeyError, "Key not found."
        c_attr = c_id.attr
        if c_attr is NULL or c_attr.parent is NULL:
            raise KeyError, "ID attribute not found."
        return _elementFactory(doc, c_attr.parent)

    def __contains__(self, id_name):
        cdef tree.xmlID* c_id
        cdef _Document doc
        doc = self.__doc
        id_utf = _utf8(id_name)
        c_id = <tree.xmlID*>tree.xmlHashLookup(doc._c_doc.ids, _cstr(id_utf))
        return c_id is not NULL

    def keys(self):
        keys = self.__keys
        if keys is not None:
            return python.PySequence_List(keys)
        keys = self.__build_keys()
        self.__keys = python.PySequence_Tuple(keys)
        return keys

    def __build_keys(self):
        cdef _Document doc
        keys = []
        doc = self.__doc
        tree.xmlHashScan(<tree.xmlHashTable*>doc._c_doc.ids,
                         _collectIdHashKeys, <python.PyObject*>keys)
        return keys

    def items(self):
        items = self.__items
        if items is not None:
            return python.PySequence_List(items)
        items = self.__build_items()
        self.__items = python.PySequence_Tuple(items)
        return items

    def iteritems(self):
        items = self.__items
        if items is None:
            items = self.items()
        return iter(items)

    def __build_items(self):
        cdef _Document doc
        items = []
        doc = self.__doc
        context = (items, doc)
        tree.xmlHashScan(<tree.xmlHashTable*>doc._c_doc.ids,
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
