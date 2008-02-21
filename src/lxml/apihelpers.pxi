# Private/public helper functions for API functions

cdef void displayNode(xmlNode* c_node, indent):
    # to help with debugging
    cdef xmlNode* c_child
    print indent * ' ', <long>c_node
    c_child = c_node.children
    while c_child is not NULL:
        displayNode(c_child, indent + 1)
        c_child = c_child.next

cdef _Document _documentOrRaise(object input):
    """Call this to get the document of a _Document, _ElementTree or _Element
    object, or to raise an exception if it can't be determined.

    Should be used in all API functions for consistency.
    """
    cdef _Document doc
    cdef _Element element
    if isinstance(input, _ElementTree):
        element = (<_ElementTree>input)._context_node
        if element is not None:
            doc = element._doc
    elif isinstance(input, _Element):
        doc = (<_Element>input)._doc
    elif isinstance(input, _Document):
        doc = <_Document>input
    else:
        raise TypeError("Invalid input object: %s" % type(input))
    if doc is None:
        raise ValueError("Input object has no document: %s" % type(input))
    else:
        return doc

cdef _Element _rootNodeOrRaise(object input):
    """Call this to get the root node of a _Document, _ElementTree or
     _Element object, or to raise an exception if it can't be determined.

    Should be used in all API functions for consistency.
     """
    cdef _Element node
    if isinstance(input, _ElementTree):
        node = (<_ElementTree>input)._context_node
    elif isinstance(input, _Element):
        node = <_Element>input
    elif isinstance(input, _Document):
        node = (<_Document>input).getroot()
    else:
        raise TypeError("Invalid input object: %s" % type(input))
    if node is None:
        raise ValueError("Input object has no element: %s" % type(input))
    else:
        return node

cdef _Document _documentOf(object input):
    # call this to get the document of a
    # _Document, _ElementTree or _Element object
    # may return None!
    cdef _Element element
    if isinstance(input, _ElementTree):
        element = (<_ElementTree>input)._context_node
        if element is not None:
            return element._doc
    elif isinstance(input, _Element):
        return (<_Element>input)._doc
    elif isinstance(input, _Document):
        return <_Document>input
    return None

cdef _Element _rootNodeOf(object input):
    # call this to get the root node of a
    # _Document, _ElementTree or _Element object
    # may return None!
    if isinstance(input, _ElementTree):
        return (<_ElementTree>input)._context_node
    elif isinstance(input, _Element):
        return <_Element>input
    elif isinstance(input, _Document):
        return (<_Document>input).getroot()
    else:
        return None

cdef _Element _makeElement(tag, xmlDoc* c_doc, _Document doc,
                           _BaseParser parser, text, tail, attrib, nsmap,
                           extra_attrs):
    """Create a new element and initialize text content, namespaces and
    attributes.

    This helper function will reuse as much of the existing document as
    possible:

    If 'parser' is None, the parser will be inherited from 'doc' or the
    default parser will be used.

    If 'doc' is None, 'c_doc' is used to create a new _Document and the new
    element is made its root node.

    If 'c_doc' is also NULL, a new xmlDoc will be created.
    """
    cdef xmlNode* c_node
    ns_utf, name_utf = _getNsTag(tag)
    if parser is not None and parser._for_html:
        _htmlTagValidOrRaise(name_utf)
    else:
        _tagValidOrRaise(name_utf)
    if doc is not None:
        c_doc = doc._c_doc
    elif c_doc is NULL:
        c_doc = _newDoc()
    c_node = _createElement(c_doc, name_utf)
    if c_node is NULL:
        return python.PyErr_NoMemory()
    try:
        if text is not None:
            _setNodeText(c_node, text)
        if tail is not None:
            _setTailText(c_node, tail)
        if doc is None:
            tree.xmlDocSetRootElement(c_doc, c_node)
            doc = _documentFactory(c_doc, parser)
        # add namespaces to node if necessary
        doc._setNodeNamespaces(c_node, ns_utf, nsmap)
        _initNodeAttributes(c_node, doc, attrib, extra_attrs)
        return _elementFactory(doc, c_node)
    except:
        # free allocated c_node/c_doc unless Python does it for us
        if c_node.doc is not c_doc:
            # node not yet in document => will not be freed by document
            if tail is not None:
                _removeText(c_node.next) # tail
            tree.xmlFreeNode(c_node)
        if doc is None:
            # c_doc will not be freed by doc
            tree.xmlFreeDoc(c_doc)
        raise

cdef _Element _makeSubElement(_Element parent, tag, text, tail,
                              attrib, nsmap, extra_attrs):
    """Create a new child element and initialize text content, namespaces and
    attributes.
    """
    cdef xmlNode* c_node
    cdef xmlDoc* c_doc
    if parent is None or parent._doc is None:
        return None
    ns_utf, name_utf = _getNsTag(tag)
    c_doc = parent._doc._c_doc

    if parent._doc._parser is not None and parent._doc._parser._for_html:
        _htmlTagValidOrRaise(name_utf)
    else:
        _tagValidOrRaise(name_utf)

    c_node = _createElement(c_doc, name_utf)
    if c_node is NULL:
        return python.PyErr_NoMemory()
    tree.xmlAddChild(parent._c_node, c_node)

    if text is not None:
        _setNodeText(c_node, text)
    if tail is not None:
        _setTailText(c_node, tail)

    # add namespaces to node if necessary
    parent._doc._setNodeNamespaces(c_node, ns_utf, nsmap)
    _initNodeAttributes(c_node, parent._doc, attrib, extra_attrs)
    return _elementFactory(parent._doc, c_node)

cdef _initNodeAttributes(xmlNode* c_node, _Document doc, attrib, extra):
    """Initialise the attributes of an element node.
    """
    cdef bint is_html
    cdef xmlNs* c_ns
    # 'extra' is not checked here (expected to be a keyword dict)
    if attrib is not None and not hasattr(attrib, 'items'):
        raise TypeError("Invalid attribute dictionary: %s" % type(attrib))
    if extra is not None and extra:
        if attrib is None:
            attrib = extra
        else:
            attrib.update(extra)
    if attrib:
        is_html = doc._parser._for_html
        for name, value in attrib.items():
            attr_ns_utf, attr_name_utf = _getNsTag(name)
            if not is_html:
                _attributeValidOrRaise(attr_name_utf)
            value_utf = _utf8(value)
            if attr_ns_utf is None:
                tree.xmlNewProp(c_node, _cstr(attr_name_utf), _cstr(value_utf))
            else:
                c_ns = doc._findOrBuildNodeNs(c_node, _cstr(attr_ns_utf), NULL)
                tree.xmlNewNsProp(c_node, c_ns,
                                  _cstr(attr_name_utf), _cstr(value_utf))

cdef object _attributeValue(xmlNode* c_element, xmlAttr* c_attrib_node):
    cdef char* value
    cdef char* href
    href = _getNs(<xmlNode*>c_attrib_node)
    if href is NULL:
        value = tree.xmlGetNoNsProp(c_element, c_attrib_node.name)
    else:
        value = tree.xmlGetNsProp(c_element, c_attrib_node.name, href)
    result = funicode(value)
    tree.xmlFree(value)
    return result

cdef object _attributeValueFromNsName(xmlNode* c_element,
                                      char* c_href, char* c_name):
    cdef char* c_result
    if c_href is NULL:
        c_result = tree.xmlGetNoNsProp(c_element, c_name)
    else:
        c_result = tree.xmlGetNsProp(c_element, c_name, c_href)
    if c_result is NULL:
        return None
    result = funicode(c_result)
    tree.xmlFree(c_result)
    return result

cdef object _getAttributeValue(_Element element, key, default):
    cdef char* c_result
    cdef char* c_tag
    ns, tag = _getNsTag(key)
    c_tag = _cstr(tag)
    if ns is None:
        c_result = tree.xmlGetNoNsProp(element._c_node, c_tag)
    else:
        c_result = tree.xmlGetNsProp(element._c_node, c_tag, _cstr(ns))
    if c_result is NULL:
        # XXX free namespace that is not in use..?
        return default
    result = funicode(c_result)
    tree.xmlFree(c_result)
    return result

cdef int _setAttributeValue(_Element element, key, value) except -1:
    cdef xmlNs* c_ns
    cdef char* c_value
    cdef char* c_tag
    ns, tag = _getNsTag(key)
    if not element._doc._parser._for_html:
        _attributeValidOrRaise(tag)
    c_tag = _cstr(tag)
    if isinstance(value, QName):
        value = _resolveQNameText(element, value)
    else:
        value = _utf8(value)
    c_value = _cstr(value)
    if ns is None:
        tree.xmlSetProp(element._c_node, c_tag, c_value)
    else:
        c_ns = element._doc._findOrBuildNodeNs(element._c_node,
                                               _cstr(ns), NULL)
        tree.xmlSetNsProp(element._c_node, c_ns, c_tag, c_value)
    return 0

cdef int _delAttribute(_Element element, key) except -1:
    cdef xmlAttr* c_attr
    cdef char* c_href
    ns, tag = _getNsTag(key)
    if ns is None:
        c_href = NULL
    else:
        c_href = _cstr(ns)
    if _delAttributeFromNsName(element._c_node, c_href, _cstr(tag)):
        raise KeyError(key)
    return 0

cdef int _delAttributeFromNsName(xmlNode* c_node, char* c_href, char* c_name):
    cdef xmlAttr* c_attr
    if c_href is NULL:
        c_attr = tree.xmlHasProp(c_node, c_name)
    else:
        c_attr = tree.xmlHasNsProp(c_node, c_name, c_href)
    if c_attr is NULL:
        # XXX free namespace that is not in use..?
        return -1
    tree.xmlRemoveProp(c_attr)
    return 0

cdef object _collectAttributes(xmlNode* c_node, int collecttype):
    """Collect all attributes of a node in a list.  Depending on collecttype,
    it collects either the name (1), the value (2) or the name-value tuples.
    """
    cdef Py_ssize_t count
    cdef xmlAttr* c_attr
    c_attr = c_node.properties
    count = 0
    while c_attr is not NULL:
        if c_attr.type == tree.XML_ATTRIBUTE_NODE:
            count = count + 1
        c_attr = c_attr.next

    if count == 0:
        return []

    attributes = python.PyList_New(count)
    c_attr = c_node.properties
    count = 0
    while c_attr is not NULL:
        if c_attr.type == tree.XML_ATTRIBUTE_NODE:
            if collecttype == 1:
                item = _namespacedName(<xmlNode*>c_attr)
            elif collecttype == 2:
                item = _attributeValue(c_node, c_attr)
            else:
                item = (_namespacedName(<xmlNode*>c_attr),
                        _attributeValue(c_node, c_attr))

            python.Py_INCREF(item)
            python.PyList_SET_ITEM(attributes, count, item)
            count = count + 1
        c_attr = c_attr.next
    return attributes

cdef object __RE_XML_ENCODING
__RE_XML_ENCODING = re.compile(
    r'^(\s*<\?\s*xml[^>]+)\s+encoding\s*=\s*"[^"]*"\s*', re.U)

cdef object __REPLACE_XML_ENCODING
__REPLACE_XML_ENCODING = __RE_XML_ENCODING.sub

cdef object __HAS_XML_ENCODING
__HAS_XML_ENCODING = __RE_XML_ENCODING.match

cdef object _stripEncodingDeclaration(object xml_string):
    # this is a hack to remove the XML encoding declaration from unicode
    return __REPLACE_XML_ENCODING(r'\g<1>', xml_string)

cdef int _hasEncodingDeclaration(object xml_string):
    # check if a (unicode) string has an XML encoding declaration
    return __HAS_XML_ENCODING(xml_string) is not None

cdef object _stripDeclaration(object xml_string):
    # this is a hack to remove the XML declaration when we encode to UTF-8
    xml_string = xml_string.strip()
    if xml_string[:5] == '<?xml':
        i = xml_string.find('?>')
        if i != -1:
            i = i + 2
            while xml_string[i:i+1] in '\n\r ':
                i = i+1
            xml_string = xml_string[i:]
    return xml_string

cdef int _hasText(xmlNode* c_node):
    return c_node is not NULL and _textNodeOrSkip(c_node.children) is not NULL

cdef int _hasTail(xmlNode* c_node):
    return c_node is not NULL and _textNodeOrSkip(c_node.next) is not NULL

cdef _collectText(xmlNode* c_node):
    """Collect all text nodes and return them as a unicode string.

    Start collecting at c_node.
    
    If there was no text to collect, return None
    """
    cdef Py_ssize_t scount
    cdef char* text
    cdef xmlNode* c_node_cur
    # check for multiple text nodes
    scount = 0
    text = NULL
    c_node_cur = c_node = _textNodeOrSkip(c_node)
    while c_node_cur is not NULL:
        if c_node_cur.content[0] != c'\0':
            text = c_node_cur.content
        scount = scount + 1
        c_node_cur = _textNodeOrSkip(c_node_cur.next)

    # handle two most common cases first
    if text is NULL:
        if scount > 0:
            return ''
        else:
            return None
    if scount == 1:
        return funicode(text)

    # the rest is not performance critical anymore
    result = ''
    while c_node is not NULL:
        result = result + c_node.content
        c_node = _textNodeOrSkip(c_node.next)
    return funicode(result)

cdef void _removeText(xmlNode* c_node):
    """Remove all text nodes.

    Start removing at c_node.
    """
    cdef xmlNode* c_next
    c_node = _textNodeOrSkip(c_node)
    while c_node is not NULL:
        c_next = _textNodeOrSkip(c_node.next)
        tree.xmlUnlinkNode(c_node)
        tree.xmlFreeNode(c_node)
        c_node = c_next

cdef int _setNodeText(xmlNode* c_node, value) except -1:
    cdef xmlNode* c_text_node
    # remove all text nodes at the start first
    _removeText(c_node.children)
    if value is None:
        return 0
    # now add new text node with value at start
    text = _utf8(value)
    c_text_node = tree.xmlNewDocText(c_node.doc, _cstr(text))
    if c_node.children is NULL:
        tree.xmlAddChild(c_node, c_text_node)
    else:
        tree.xmlAddPrevSibling(c_node.children, c_text_node)
    return 0

cdef int _setTailText(xmlNode* c_node, value) except -1:
    cdef xmlNode* c_text_node
    # remove all text nodes at the start first
    _removeText(c_node.next)
    if value is None:
        return 0
    text = _utf8(value)
    c_text_node = tree.xmlNewDocText(c_node.doc, _cstr(text))
    # XXX what if we're the top element?
    tree.xmlAddNextSibling(c_node, c_text_node)
    return 0

cdef _resolveQNameText(_Element element, value):
    cdef xmlNs* c_ns
    ns, tag = _getNsTag(value)
    if ns is None:
        return tag
    else:
        c_ns = element._doc._findOrBuildNodeNs(
            element._c_node, _cstr(ns), NULL)
        return '%s:%s' % (c_ns.prefix, tag)

cdef bint _hasChild(xmlNode* c_node):
    return c_node is not NULL and _findChildForwards(c_node, 0) is not NULL

cdef Py_ssize_t _countElements(xmlNode* c_node):
    "Counts the elements within the following siblings and the node itself."
    cdef Py_ssize_t count
    count = 0
    while c_node is not NULL:
        if _isElement(c_node):
            count = count + 1
        c_node = c_node.next
    return count

cdef int _findChildSlice(
    python.slice sliceobject, xmlNode* c_parent,
    xmlNode** c_start_node, Py_ssize_t* c_step, Py_ssize_t* c_length) except -1:
    """Resolve a children slice.

    Returns the start node, step size and the slice length in the
    pointer arguments.
    """
    cdef Py_ssize_t start, stop, childcount
    childcount = _countElements(c_parent.children)
    if childcount == 0:
        c_start_node[0] = NULL
        c_length[0] = 0
        if sliceobject.step is None:
            c_step[0] = 1
        else:
            python._PyEval_SliceIndex(sliceobject.step, c_step)
        return 0
    python.PySlice_GetIndicesEx(
        sliceobject, childcount, &start, &stop, c_step, c_length)
    if start > childcount / 2:
        c_start_node[0] = _findChildBackwards(c_parent, childcount - start - 1)
    else:
        c_start_node[0] = _findChild(c_parent, start)
    return 0

cdef bint _isFullSlice(python.slice sliceobject):
    """Conservative guess if this slice is a full slice as in ``s[:]``.
    """
    cdef Py_ssize_t step
    if sliceobject is None:
        return 0
    if sliceobject.start is None and \
            sliceobject.stop is None:
        if sliceobject.step is None:
            return 1
        python._PyEval_SliceIndex(sliceobject.step, &step)
        if step == 1:
            return 1
        return 0
    return 0

cdef _collectChildren(_Element element):
    cdef xmlNode* c_node
    result = []
    c_node = element._c_node.children
    if c_node is not NULL:
        if not _isElement(c_node):
            c_node = _nextElement(c_node)
        while c_node is not NULL:
            python.PyList_Append(result, _elementFactory(element._doc, c_node))
            c_node = _nextElement(c_node)
    return result

cdef xmlNode* _findChild(xmlNode* c_node, Py_ssize_t index):
    if index < 0:
        return _findChildBackwards(c_node, -index - 1)
    else:
        return _findChildForwards(c_node, index)
    
cdef xmlNode* _findChildForwards(xmlNode* c_node, Py_ssize_t index):
    """Return child element of c_node with index, or return NULL if not found.
    """
    cdef xmlNode* c_child
    cdef Py_ssize_t c
    c_child = c_node.children
    c = 0
    while c_child is not NULL:
        if _isElement(c_child):
            if c == index:
                return c_child
            c = c + 1
        c_child = c_child.next
    return NULL

cdef xmlNode* _findChildBackwards(xmlNode* c_node, Py_ssize_t index):
    """Return child element of c_node with index, or return NULL if not found.
    Search from the end.
    """
    cdef xmlNode* c_child
    cdef Py_ssize_t c
    c_child = c_node.last
    c = 0
    while c_child is not NULL:
        if _isElement(c_child):
            if c == index:
                return c_child
            c = c + 1
        c_child = c_child.prev
    return NULL
    
cdef xmlNode* _textNodeOrSkip(xmlNode* c_node):
    """Return the node if it's a text node.  Skip over ignorable nodes in a
    series of text nodes.  Return NULL if a non-ignorable node is found.

    This is used to skip over XInclude nodes when collecting adjacent text
    nodes.
    """
    while c_node is not NULL:
        if c_node.type == tree.XML_TEXT_NODE:
            return c_node
        elif c_node.type == tree.XML_XINCLUDE_START or \
                 c_node.type == tree.XML_XINCLUDE_END:
            c_node = c_node.next
        else:
            return NULL
    return NULL

cdef xmlNode* _nextElement(xmlNode* c_node):
    """Given a node, find the next sibling that is an element.
    """
    if c_node is NULL:
        return NULL
    c_node = c_node.next
    while c_node is not NULL:
        if _isElement(c_node):
            return c_node
        c_node = c_node.next
    return NULL

cdef xmlNode* _previousElement(xmlNode* c_node):
    """Given a node, find the next sibling that is an element.
    """
    if c_node is NULL:
        return NULL
    c_node = c_node.prev
    while c_node is not NULL:
        if _isElement(c_node):
            return c_node
        c_node = c_node.prev
    return NULL

cdef xmlNode* _parentElement(xmlNode* c_node):
    "Given a node, find the parent element."
    if c_node is NULL or not _isElement(c_node):
        return NULL
    c_node = c_node.parent
    if c_node is NULL or not _isElement(c_node):
        return NULL
    return c_node

cdef bint _tagMatches(xmlNode* c_node, char* c_href, char* c_name):
    """Tests if the node matches namespace URI and tag name.

    A node matches if it matches both c_href and c_name.

    A node matches c_href if any of the following is true:
    * c_href is NULL
    * its namespace is NULL and c_href is the empty string
    * its namespace string equals the c_href string

    A node matches c_name if any of the following is true:
    * c_name is NULL
    * its name string equals the c_name string
    """
    cdef char* c_node_href
    if c_node is NULL:
        return 0
    if c_node.type != tree.XML_ELEMENT_NODE:
        # not an element, only succeed if we match everything
        return c_name is NULL and c_href is NULL
    if c_name is NULL:
        if c_href is NULL:
            # always match
            return 1
        else:
            c_node_href = _getNs(c_node)
            if c_node_href is NULL:
                return c_href[0] == c'\0'
            else:
                return cstd.strcmp(c_node_href, c_href) == 0
    elif c_href is NULL:
        if _getNs(c_node) is not NULL:
            return 0
        return cstd.strcmp(c_node.name, c_name) == 0
    elif cstd.strcmp(c_node.name, c_name) == 0:
        c_node_href = _getNs(c_node)
        if c_node_href is NULL:
            return c_href[0] == c'\0'
        else:
            return cstd.strcmp(c_node_href, c_href) == 0
    else:
        return 0

cdef int _removeNode(_Document doc, xmlNode* c_node) except -1:
    """Unlink and free a node and subnodes if possible.  Otherwise, make sure
    it's self-contained.
    """
    cdef xmlNode* c_next
    c_next = c_node.next
    tree.xmlUnlinkNode(c_node)
    _moveTail(c_next, c_node)
    if not attemptDeallocation(c_node):
        # make namespaces absolute
        moveNodeToDocument(doc, c_node)
    return 0

cdef void _moveTail(xmlNode* c_tail, xmlNode* c_target):
    cdef xmlNode* c_next
    # tail support: look for any text nodes trailing this node and 
    # move them too
    c_tail = _textNodeOrSkip(c_tail)
    while c_tail is not NULL:
        c_next = _textNodeOrSkip(c_tail.next)
        tree.xmlUnlinkNode(c_tail)
        tree.xmlAddNextSibling(c_target, c_tail)
        c_target = c_tail
        c_tail = c_next

cdef void _copyTail(xmlNode* c_tail, xmlNode* c_target):
    cdef xmlNode* c_new_tail
    # tail copying support: look for any text nodes trailing this node and
    # copy it to the target node
    c_tail = _textNodeOrSkip(c_tail)
    while c_tail is not NULL:
        if c_target.doc is not c_tail.doc:
            c_new_tail = tree.xmlDocCopyNode(c_tail, c_target.doc, 0)
        else:
            c_new_tail = tree.xmlCopyNode(c_tail, 0)
        tree.xmlAddNextSibling(c_target, c_new_tail)
        c_target = c_new_tail
        c_tail = _textNodeOrSkip(c_tail.next)

cdef int _deleteSlice(_Document doc, xmlNode* c_node,
                      Py_ssize_t count, Py_ssize_t step) except -1:
    """Delete slice, ``count`` items starting with ``c_node`` with a step
    width of ``step``.
    """
    cdef xmlNode* c_next
    cdef Py_ssize_t c, i
    cdef _node_to_node_function next_element
    if c_node is NULL:
        return 0
    if step > 0:
        next_element = _nextElement
    else:
        step = -step
        next_element = _previousElement
    # now start deleting nodes
    c = 0
    c_next = c_node
    while c_node is not NULL and c < count:
        for i from 0 <= i < step:
            c_next = next_element(c_next)
        _removeNode(doc, c_node)
        c = c + 1
        c_node = c_next
    return 0

cdef int _replaceSlice(_Element parent, xmlNode* c_node,
                       Py_ssize_t slicelength, Py_ssize_t step,
                       bint left_to_right, elements) except -1:
    """Replace the slice of ``count`` elements starting at ``c_node`` with
    positive step width ``step`` by the Elements in ``elements``.  The
    direction is given by the boolean argument ``left_to_right``.

    ``c_node`` may be NULL to indicate the end of the children list.
    """
    cdef xmlNode* c_orig_neighbour
    cdef xmlNode* c_next
    cdef _Element element
    cdef Py_ssize_t seqlength, i, c
    cdef _node_to_node_function next_element
    assert step > 0
    if left_to_right:
        next_element = _nextElement
    else:
        next_element = _previousElement

    if not python.PyList_Check(elements) and \
            not python.PyTuple_Check(elements):
        elements = list(elements)

    if step > 1:
        # *replacing* children stepwise with list => check size!
        seqlength = len(elements)
        if seqlength != slicelength:
            raise ValueError(
                "attempt to assign sequence of size %d "
                "to extended slice of size %d" % (seqlength, slicelength))

    if c_node is NULL:
        # no children yet => add all elements straight away
        if left_to_right:
            for element in elements:
                assert element is not None, "Node must not be None"
                _appendChild(parent, element)
        else:
            for element in elements:
                assert element is not None, "Node must not be None"
                _prependChild(parent, element)
        return 0

    # remove the elements first as some might be re-added
    if left_to_right:
        # L->R, remember left neighbour
        c_orig_neighbour = _previousElement(c_node)
    else:
        # R->L, remember right neighbour
        c_orig_neighbour = _nextElement(c_node)

    c = 0
    c_next = c_node
    while c_node is not NULL and c < slicelength:
        for i from 0 <= i < step:
            c_next = next_element(c_next)
        _removeNode(parent._doc, c_node)
        c = c + 1
        c_node = c_next

    # make sure each element is inserted only once
    elements = iter(elements)

    # find the first node right of the new insertion point
    if left_to_right:
        if c_orig_neighbour is not NULL:
            c_node = next_element(c_orig_neighbour)
        else:
            # before the first element
            c_node = _findChildForwards(parent._c_node, 0)
    elif c_orig_neighbour is NULL:
        # at the end, but reversed stepping
        # append one element and go to the next insertion point
        for element in elements:
            assert element is not None, "Node must not be None"
            _appendChild(parent, element)
            c_node = element._c_node
            if slicelength > 0:
                slicelength = slicelength - 1
                for i from 1 <= i < step:
                    c_node = next_element(c_node)
            break

    if left_to_right:
        # adjust step size after removing slice as we are not stepping
        # over the newly inserted elements
        step = step - 1

    # now insert elements where we removed them
    if c_node is not NULL:
        for element in elements:
            assert element is not None, "Node must not be None"
            # move element and tail over
            c_next = element._c_node.next
            tree.xmlAddPrevSibling(c_node, element._c_node)
            _moveTail(c_next, element._c_node)

            # integrate element into new document
            moveNodeToDocument(parent._doc, element._c_node)

            # stop at the end of the slice
            if slicelength > 0:
                slicelength = slicelength - 1
                for i from 0 <= i < step:
                    c_node = next_element(c_node)
                if c_node is NULL:
                    break
        else:
            # everything inserted
            return 0

    # append the remaining elements at the respective end
    if left_to_right:
        for element in elements:
            assert element is not None, "Node must not be None"
            _appendChild(parent, element)
    else:
        for element in elements:
            assert element is not None, "Node must not be None"
            _prependChild(parent, element)

    return 0

cdef int _appendChild(_Element parent, _Element child) except -1:
    """Append a new child to a parent element.
    """
    cdef xmlNode* c_next
    cdef xmlNode* c_node
    c_node = child._c_node
    # store possible text node
    c_next = c_node.next
    # move node itself
    tree.xmlUnlinkNode(c_node)
    tree.xmlAddChild(parent._c_node, c_node)
    _moveTail(c_next, c_node)
    # uh oh, elements may be pointing to different doc when
    # parent element has moved; change them too..
    moveNodeToDocument(parent._doc, c_node)

cdef int _prependChild(_Element parent, _Element child) except -1:
    """Prepend a new child to a parent element.
    """
    cdef xmlNode* c_next
    cdef xmlNode* c_child
    cdef xmlNode* c_node
    c_node = child._c_node
    # store possible text node
    c_next = c_node.next
    # move node itself
    c_child = _findChildForwards(parent._c_node, 0)
    if c_child is NULL:
        tree.xmlUnlinkNode(c_node)
        tree.xmlAddChild(parent._c_node, c_node)
    else:
        tree.xmlAddPrevSibling(c_child, c_node)
    _moveTail(c_next, c_node)
    # uh oh, elements may be pointing to different doc when
    # parent element has moved; change them too..
    moveNodeToDocument(parent._doc, c_node)

cdef int _appendSibling(_Element element, _Element sibling) except -1:
    """Append a new child to a parent element.
    """
    cdef xmlNode* c_next
    cdef xmlNode* c_node
    c_node = sibling._c_node
    # store possible text node
    c_next = c_node.next
    # move node itself
    tree.xmlAddNextSibling(element._c_node, c_node)
    _moveTail(c_next, c_node)
    # uh oh, elements may be pointing to different doc when
    # parent element has moved; change them too..
    moveNodeToDocument(element._doc, c_node)

cdef int _prependSibling(_Element element, _Element sibling) except -1:
    """Append a new child to a parent element.
    """
    cdef xmlNode* c_next
    cdef xmlNode* c_node
    c_node = sibling._c_node
    # store possible text node
    c_next = c_node.next
    # move node itself
    tree.xmlAddPrevSibling(element._c_node, c_node)
    _moveTail(c_next, c_node)
    # uh oh, elements may be pointing to different doc when
    # parent element has moved; change them too..
    moveNodeToDocument(element._doc, c_node)

cdef int isutf8(char* s):
    cdef char c
    c = s[0]
    while c != c'\0':
        if c & 0x80:
            return 1
        s = s + 1
        c = s[0]
    return 0

cdef int isutf8py(pystring):
    cdef char* s
    cdef char* c_end
    cdef char c
    cdef bint is_non_ascii
    s = _cstr(pystring)
    c_end = s + python.PyString_GET_SIZE(pystring)
    is_non_ascii = 0
    while s < c_end:
        c = s[0]
        if c & 0x80:
            is_non_ascii = 1
        elif c == c'\0':
            return -1 # invalid!
        elif is_non_ascii == 0 and not tree.xmlIsChar_ch(c):
            return -1 # invalid!
        s += 1
    return is_non_ascii

cdef object funicode(char* s):
    cdef Py_ssize_t slen
    cdef char* spos
    cdef bint is_non_ascii
    spos = s
    is_non_ascii = 0
    while spos[0] != c'\0':
        if spos[0] & 0x80:
            is_non_ascii = 1
            break
        spos += 1
    while spos[0] != c'\0':
        spos += 1
    slen = spos - s
    if is_non_ascii:
        return python.PyUnicode_DecodeUTF8(s, slen, NULL)
    return python.PyString_FromStringAndSize(s, slen)

cdef object _utf8(object s):
    if python.PyString_Check(s):
        assert not isutf8py(s), \
               "All strings must be XML compatible, either Unicode or ASCII"
    elif python.PyUnicode_Check(s):
        # FIXME: we should test these strings, too ...
        s = python.PyUnicode_AsUTF8String(s)
        assert isutf8py(s) != -1, \
               "All strings must be XML compatible, either Unicode or ASCII"
    else:
        raise TypeError("Argument must be string or unicode.")
    return s

cdef object _encodeFilename(object filename):
    """Make sure a filename is 8-bit encoded (or None).
    """
    if filename is None:
        return None
    elif python.PyString_Check(filename):
        return filename
    elif python.PyUnicode_Check(filename):
        return python.PyUnicode_AsEncodedString(
            filename, _C_FILENAME_ENCODING, NULL)
    else:
        raise TypeError("Argument must be string or unicode.")

cdef object _encodeFilenameUTF8(object filename):
    """Recode filename as UTF-8. Tries ASCII, local filesystem encoding and
    UTF-8 as source encoding.
    """
    cdef char* c_filename
    if filename is None:
        return None
    elif python.PyString_Check(filename):
        if not isutf8py(filename):
            # plain ASCII!
            return filename
        c_filename = _cstr(filename)
        try:
            # try to decode with default encoding
            filename = python.PyUnicode_Decode(
                c_filename, python.PyString_GET_SIZE(filename),
                _C_FILENAME_ENCODING, NULL)
        except UnicodeDecodeError, decode_exc:
            try:
                # try if it's UTF-8
                filename = python.PyUnicode_DecodeUTF8(
                    c_filename, python.PyString_GET_SIZE(filename), NULL)
            except UnicodeDecodeError:
                raise decode_exc # otherwise re-raise original exception
    if python.PyUnicode_Check(filename):
        return python.PyUnicode_AsUTF8String(filename)
    else:
        raise TypeError("Argument must be string or unicode.")

cdef _getNsTag(tag):
    """Given a tag, find namespace URI and tag name.
    Return None for NS uri if no namespace URI available.
    """
    cdef char* c_tag
    cdef char* c_ns_end
    cdef Py_ssize_t taglen
    cdef Py_ssize_t nslen
    if isinstance(tag, QName):
        tag = (<QName>tag).text
    tag = _utf8(tag)
    c_tag = _cstr(tag)
    if c_tag[0] == c'{':
        c_tag = c_tag + 1
        c_ns_end = cstd.strchr(c_tag, c'}')
        if c_ns_end is NULL:
            raise ValueError("Invalid tag name")
        nslen  = c_ns_end - c_tag
        taglen = python.PyString_GET_SIZE(tag) - nslen - 2
        if taglen == 0:
            raise ValueError("Empty tag name")
        if nslen > 0:
            ns = python.PyString_FromStringAndSize(c_tag,   nslen)
        tag = python.PyString_FromStringAndSize(c_ns_end+1, taglen)
    elif python.PyString_GET_SIZE(tag) == 0:
        raise ValueError("Empty tag name")
    return ns, tag

cdef int _pyXmlNameIsValid(name_utf8):
    return _xmlNameIsValid(_cstr(name_utf8))

cdef int _pyHtmlNameIsValid(name_utf8):
    return _htmlNameIsValid(_cstr(name_utf8))

cdef int _xmlNameIsValid(char* c_name):
    return tree.xmlValidateNCName(c_name, 0) == 0

cdef int _htmlNameIsValid(char* c_name):
    if c_name is NULL or c_name[0] == c'\0':
        return 0
    while c_name[0] != c'\0':
        if c_name[0] == c'&' or \
                c_name[0] == c'<' or \
                c_name[0] == c'>' or \
                c_name[0] == c'/' or \
                c_name[0] == c'"' or \
                c_name[0] == c"'" or \
                c_name[0] == c'\x09' or \
                c_name[0] == c'\x0A' or \
                c_name[0] == c'\x0B' or \
                c_name[0] == c'\x0C' or \
                c_name[0] == c'\x20':
            return 0
        c_name = c_name + 1
    return 1

cdef bint _characterReferenceIsValid(char* c_name):
    cdef bint is_hex
    if c_name[0] == c'x':
        c_name += 1
        is_hex = 1
    else:
        is_hex = 0
    if c_name[0] == c'\0':
        return 0
    while c_name[0] != c'\0':
        if c_name[0] < c'0' or c_name[0] > c'9':
            if not is_hex:
                return 0
            if not (c_name[0] >= c'a' and c_name[0] <= c'f'):
                if not (c_name[0] >= c'A' and c_name[0] <= c'F'):
                    return 0
        c_name += 1
    return 1

cdef int _tagValidOrRaise(tag_utf) except -1:
    if not _pyXmlNameIsValid(tag_utf):
        raise ValueError("Invalid tag name %r" % \
              python.PyUnicode_FromEncodedObject(tag_utf, 'UTF-8', 'strict'))
    return 0

cdef int _htmlTagValidOrRaise(tag_utf) except -1:
    if not _pyHtmlNameIsValid(tag_utf):
        raise ValueError("Invalid HTML tag name %r" % \
              python.PyUnicode_FromEncodedObject(tag_utf, 'UTF-8', 'strict'))
    return 0

cdef int _attributeValidOrRaise(name_utf) except -1:
    if not _pyXmlNameIsValid(name_utf):
        raise ValueError("Invalid attribute name %r" % \
              python.PyUnicode_FromEncodedObject(name_utf, 'UTF-8', 'strict'))
    return 0

cdef object _namespacedName(xmlNode* c_node):
    return _namespacedNameFromNsName(_getNs(c_node), c_node.name)

cdef object _namespacedNameFromNsName(char* href, char* name):
    if href is NULL:
        return funicode(name)
    else:
        s = python.PyString_FromFormat("{%s}%s", href, name)
        if isutf8(href) or isutf8(name):
            return python.PyUnicode_FromEncodedObject(s, 'UTF-8', NULL)
        else:
            return s

cdef _getFilenameForFile(source):
    """Given a Python File or Gzip object, give filename back.

    Returns None if not a file object.
    """
    # file instances have a name attribute
    try:
        return source.name
    except AttributeError:
        pass
    # gzip file instances have a filename attribute
    try:
        return source.filename
    except AttributeError:
        pass
    # urllib2 provides a geturl() method
    try:
        geturl = source.geturl
    except AttributeError:
        # can't determine filename
        return None
    else:
        return geturl()
