# Public C API for lxml.etree

cdef public _Element deepcopyNodeToDocument(_Document doc, xmlNode* c_root):
    "Recursively copy the element into the document. doc is not modified."
    cdef xmlNode* c_node
    c_node = _copyNodeToDoc(c_root, doc._c_doc)
    return _elementFactory(doc, c_node)

cdef public _ElementTree elementTreeFactory(_NodeBase context_node):
    return newElementTree(context_node, _ElementTree)

cdef public _ElementTree newElementTree(_NodeBase context_node,
                                        object subclass):
    if <void*>context_node is NULL or context_node is None:
        raise TypeError

    return _newElementTree(context_node._doc, context_node, subclass)

cdef public _Element elementFactory(_Document doc, xmlNode* c_node):
    if c_node is NULL or doc is None:
        raise TypeError
    return _elementFactory(doc, c_node)

cdef public _Element makeElement(tag, _Document doc, parser,
                                 text, tail, attrib, nsmap):
    return _makeElement(tag, NULL, doc, parser, text, tail, attrib, nsmap, None)

cdef public void setElementClassLookupFunction(
    _element_class_lookup_function function, state):
    _setElementClassLookupFunction(function, state)

cdef public object lookupDefaultElementClass(state, doc, xmlNode* c_node):
    return _lookupDefaultElementClass(state, doc, c_node)

cdef public object lookupNamespaceElementClass(state, doc, xmlNode* c_node):
    return _find_nselement_class(state, doc, c_node)

cdef public object callLookupFallback(FallbackElementClassLookup lookup,
                                      _Document doc, xmlNode* c_node):
    return lookup._callFallback(doc, c_node)

cdef public int tagMatches(xmlNode* c_node, char* c_href, char* c_name):
    if c_node is NULL:
        return -1
    return _tagMatches(c_node, c_href, c_name)

cdef public _Document documentOrRaise(object input):
    return _documentOrRaise(input)

cdef public _NodeBase rootNodeOrRaise(object input):
    return _rootNodeOrRaise(input)

cdef public object textOf(xmlNode* c_node):
    if c_node is NULL:
        return None
    return _collectText(c_node.children)

cdef public object tailOf(xmlNode* c_node):
    if c_node is NULL:
        return None
    return _collectText(c_node.next)

cdef public int setNodeText(xmlNode* c_node, text) except -1:
    if c_node is NULL:
        raise ValueError
    return _setNodeText(c_node, text)

cdef public int setTailText(xmlNode* c_node, text) except -1:
    if c_node is NULL:
        raise ValueError
    return _setTailText(c_node, text)

cdef public object attributeValue(xmlNode* c_element, xmlAttr* c_attrib_node):
    return _attributeValue(c_element, c_attrib_node)

cdef public object attributeValueFromNsName(xmlNode* c_element,
                                            char* ns, char* name):
    return _attributeValueFromNsName(c_element, ns, name)

cdef public object getAttributeValue(_NodeBase element, key, default):
    return _getAttributeValue(element, key, default)

cdef public object iterattributes(_Element element, int keysvalues):
    return _attributeIteratorFactory(element, keysvalues)

cdef public int setAttributeValue(_NodeBase element, key, value) except -1:
    return _setAttributeValue(element, key, value)

cdef public int delAttribute(_NodeBase element, key) except -1:
    return _delAttribute(element, key)

cdef public int delAttributeFromNsName(tree.xmlNode* c_element,
                                       char* c_href, char* c_name):
    return _delAttributeFromNsName(c_element, c_href, c_name)

cdef public xmlNode* findChild(xmlNode* c_node, Py_ssize_t index):
    return _findChild(c_node, index)

cdef public xmlNode* findChildForwards(xmlNode* c_node, Py_ssize_t index):
    return _findChildForwards(c_node, index)

cdef public xmlNode* findChildBackwards(xmlNode* c_node, Py_ssize_t index):
    return _findChildBackwards(c_node, index)

cdef public xmlNode* nextElement(xmlNode* c_node):
    return _nextElement(c_node)

cdef public xmlNode* previousElement(xmlNode* c_node):
    return _previousElement(c_node)

cdef public void appendChild(_Element parent, _Element child):
    _appendChild(parent, child)

cdef public object pyunicode(char* s):
    if s is NULL:
        raise TypeError
    return funicode(s)

cdef public object utf8(object s):
    return _utf8(s)

cdef public object getNsTag(object tag):
    return _getNsTag(tag)

cdef public object namespacedName(xmlNode* c_node):
    return _namespacedName(c_node)

cdef public object namespacedNameFromNsName(char* href, char* name):
    return _namespacedNameFromNsName(href, name)

cdef public void iteratorStoreNext(_ElementIterator iterator, _NodeBase node):
    iterator._storeNext(node)

cdef public void initTagMatch(_ElementTagMatcher matcher, tag):
    matcher._initTagMatch(tag)

cdef public tree.xmlNs* findOrBuildNodeNs(_Document doc, xmlNode* c_node,
                                          char* href) except NULL:
    if doc is None:
        raise TypeError
    return doc._findOrBuildNodeNs(c_node, href)
