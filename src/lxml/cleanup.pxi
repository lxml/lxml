# functions for tree cleanup and removing elements from subtrees

def cleanup_namespaces(tree_or_element):
    u"""cleanup_namespaces(tree_or_element)

    Remove all namespace declarations from a subtree that are not used
    by any of the elements or attributes in that tree.
    """
    cdef _Element element
    element = _rootNodeOrRaise(tree_or_element)
    _removeUnusedNamespaceDeclarations(element._c_node)

def strip_attributes(tree_or_element, *attribute_names):
    u"""strip_attributes(tree_or_element, *attribute_names)

    Delete all attributes with the provided attribute names from an
    Element (or ElementTree) and its descendants.

    Example usage::

        strip_attributes(root_element,
                         'simpleattr',
                         '{http://some/ns}attrname')
    """
    cdef _Element element
    cdef list ns_tags
    cdef char** c_ns_tags
    cdef Py_ssize_t c_tag_count

    element = _rootNodeOrRaise(tree_or_element)
    if not attribute_names: return

    ns_tags = _sortedTagList([ _getNsTag(attr)
                               for attr in <tuple>attribute_names ])
    ns_tags = [ (ns, tag if tag != b'*' else None)
                for ns, tag in ns_tags ]

    # tag names are passes as C pointers as this allows us to take
    # them from the doc dict and do pointer comparisons
    c_ns_tags = <char**> cstd.malloc(sizeof(char*) * len(ns_tags) * 2 + 2)
    if c_ns_tags is NULL:
        python.PyErr_NoMemory()

    try:
        c_tag_count = _mapTagsToCharArray(element._doc._c_doc, ns_tags, c_ns_tags)
        if c_tag_count > 0:
            _strip_attributes(element._c_node, c_ns_tags, c_tag_count)
    finally:
        cstd.free(c_ns_tags)

cdef _strip_attributes(xmlNode* c_node, char** c_ns_tags, Py_ssize_t c_tag_count):
    cdef xmlAttr* c_attr
    cdef Py_ssize_t i
    cdef char* c_href
    cdef char* c_name

    tree.BEGIN_FOR_EACH_ELEMENT_FROM(c_node, c_node, 1)
    if c_node.type == tree.XML_ELEMENT_NODE:
        if c_node.properties is not NULL:
            for i in range(c_tag_count):
                c_href = c_ns_tags[2*i]
                c_name = c_ns_tags[2*i+1]
                # must compare attributes manually to make sure we
                # only match on wildcard tag names if the attribute
                # has no namespace
                c_attr = c_node.properties
                while c_attr is not NULL:
                    if c_name is NULL or c_attr.name == c_name:
                        if c_href is NULL:
                            if c_attr.ns is NULL or c_attr.ns.href is NULL:
                                tree.xmlRemoveProp(c_attr)
                                break
                        elif c_attr.ns is not NULL and c_attr.ns.href is not NULL:
                            if cstd.strcmp(c_attr.ns.href, c_href) == 0:
                                tree.xmlRemoveProp(c_attr)
                                break
                    c_attr = c_attr.next
    tree.END_FOR_EACH_ELEMENT_FROM(c_node)

def strip_elements(tree_or_element, *tag_names, bint with_tail=True):
    u"""strip_elements(tree_or_element, *tag_names, with_tail=True)

    Delete all elements with the provided tag names from a tree or
    subtree.  This will remove the elements and their entire subtree,
    including all their attributes, text content and descendants.  It
    will also remove the tail text of the element unless you
    explicitly set the ``with_tail`` option to False.

    Note that this will not delete the element (or ElementTree root
    element) that you passed even if it matches.  It will only treat
    its descendants.  If you want to include the root element, check
    its tag name directly before even calling this function.

    Example usage::

        strip_elements(some_element,
            'simpletagname',             # non-namespaced tag
            '{http://some/ns}tagname',   # namespaced tag
            '{http://some/other/ns}*'    # any tag from a namespace
            Comment                      # comments
            )
    """
    cdef _Element element
    cdef _Document doc
    cdef list ns_tags
    cdef char** c_ns_tags
    cdef Py_ssize_t c_tag_count
    cdef bint strip_comments, strip_pis, strip_entities

    doc = _documentOrRaise(tree_or_element)
    element = _rootNodeOrRaise(tree_or_element)
    if not tag_names: return

    ns_tags = _filterSpecialTagNames(
        tag_names, &strip_comments, &strip_pis, &strip_entities)

    if (strip_comments or strip_pis) and isinstance(tree_or_element, _ElementTree):
        # include PIs and comments next to the root node
        if strip_comments:
            _removeSiblings(element._c_node, tree.XML_COMMENT_NODE, with_tail)
        if strip_pis:
            _removeSiblings(element._c_node, tree.XML_PI_NODE, with_tail)

    # tag names are passed as C pointers as this allows us to take
    # them from the doc dict and do pointer comparisons
    c_ns_tags = <char**> cstd.malloc(sizeof(char*) * len(ns_tags) * 2 + 2)
    if c_ns_tags is NULL:
        python.PyErr_NoMemory()

    try:
        c_tag_count = _mapTagsToCharArray(doc._c_doc, ns_tags, c_ns_tags)
        if c_tag_count > 0 or strip_comments or strip_pis or strip_entities:
            _strip_elements(doc, element._c_node, c_ns_tags, c_tag_count,
                            strip_comments, strip_pis, strip_entities, with_tail)
    finally:
        cstd.free(c_ns_tags)

cdef _strip_elements(_Document doc, xmlNode* c_node,
                     char** c_ns_tags, Py_ssize_t c_tag_count,
                     bint strip_comments, bint strip_pis, bint strip_entities,
                     bint with_tail):
    cdef xmlNode* c_child
    cdef xmlNode* c_next
    cdef Py_ssize_t i

    tree.BEGIN_FOR_EACH_ELEMENT_FROM(c_node, c_node, 1)
    if c_node.type == tree.XML_ELEMENT_NODE:
        # we run through the children here to prevent any problems
        # with the tree iteration which would occur if we unlinked the
        # c_node itself
        c_child = _findChildForwards(c_node, 0)
        while c_child is not NULL:
            c_next = _nextElement(c_child)
            if c_child.type == tree.XML_ELEMENT_NODE:
                for i in range(0, c_tag_count*2, 2):
                    if _tagMatchesExactly(c_child, c_ns_tags[i], c_ns_tags[i+1]):
                        if not with_tail:
                            tree.xmlUnlinkNode(c_child)
                        _removeNode(doc, c_child)
                        break
            elif c_child.type == tree.XML_COMMENT_NODE and strip_comments \
                     or c_child.type == tree.XML_PI_NODE and strip_pis \
                     or c_child.type == tree.XML_ENTITY_REF_NODE and strip_entities:
                if with_tail:
                    _removeText(c_child.next)
                tree.xmlUnlinkNode(c_child)
                attemptDeallocation(c_child)
            c_child = c_next
    tree.END_FOR_EACH_ELEMENT_FROM(c_node)


def strip_tags(tree_or_element, *tag_names):
    u"""strip_tags(tree_or_element, *tag_names)

    Delete all elements with the provided tag names from a tree or
    subtree.  This will remove the elements and their attributes, but
    *not* their text/tail content or descendants.  Instead, it will
    merge the text content and children of the element into its
    parent.

    Note that this will not delete the element (or ElementTree root
    element) that you passed even if it matches.  It will only treat
    its descendants.

    Example usage::

        strip_tags(some_element,
            'simpletagname',             # non-namespaced tag
            '{http://some/ns}tagname',   # namespaced tag
            '{http://some/other/ns}*'    # any tag from a namespace
            Comment                      # comments (including their text!)
            )
    """
    cdef _Element element
    cdef _Document doc
    cdef list ns_tags
    cdef bint strip_comments, strip_pis, strip_entities
    cdef char** c_ns_tags
    cdef Py_ssize_t c_tag_count

    doc = _documentOrRaise(tree_or_element)
    element = _rootNodeOrRaise(tree_or_element)
    if not tag_names: return

    ns_tags = _filterSpecialTagNames(
        tag_names, &strip_comments, &strip_pis, &strip_entities)

    if (strip_comments or strip_pis) and isinstance(tree_or_element, _ElementTree):
        # include PIs and comments next to the root node
        if strip_comments:
            _removeSiblings(element._c_node, tree.XML_COMMENT_NODE, 0)
        if strip_pis:
            _removeSiblings(element._c_node, tree.XML_PI_NODE, 0)

    # tag names are passes as C pointers as this allows us to take
    # them from the doc dict and do pointer comparisons
    c_ns_tags = <char**> cstd.malloc(sizeof(char*) * len(ns_tags) * 2 + 2)
    if c_ns_tags is NULL:
        python.PyErr_NoMemory()

    try:
        c_tag_count = _mapTagsToCharArray(doc._c_doc, ns_tags, c_ns_tags)
        if c_tag_count > 0 or strip_comments or strip_pis or strip_entities:
            _strip_tags(doc, element._c_node, c_ns_tags, c_tag_count,
                        strip_comments, strip_pis, strip_entities)
    finally:
        cstd.free(c_ns_tags)

cdef _strip_tags(_Document doc, xmlNode* c_node,
                 char** c_ns_tags, Py_ssize_t c_tag_count,
                 bint strip_comments, bint strip_pis, bint strip_entities):
    cdef xmlNode* c_child
    cdef xmlNode* c_next
    cdef Py_ssize_t i

    tree.BEGIN_FOR_EACH_ELEMENT_FROM(c_node, c_node, 1)
    if c_node.type == tree.XML_ELEMENT_NODE:
        # we run through the children here to prevent any problems
        # with the tree iteration which would occur if we unlinked the
        # c_node itself
        c_child = _findChildForwards(c_node, 0)
        while c_child is not NULL:
            if c_child.type == tree.XML_ELEMENT_NODE:
                for i in range(c_tag_count):
                    if _tagMatchesExactly(c_child, c_ns_tags[2*i], c_ns_tags[2*i+1]):
                        c_next = _findChildForwards(c_child, 0) or _nextElement(c_child)
                        _replaceNodeByChildren(doc, c_child)
                        if not attemptDeallocation(c_child):
                            if c_child.nsDef is not NULL:
                                # make namespaces absolute
                                moveNodeToDocument(doc, doc._c_doc, c_child)
                        c_child = c_next
                        break
                else:
                    c_child = _nextElement(c_child)
            else:
                c_next = _nextElement(c_child)
                if c_child.type == tree.XML_COMMENT_NODE and strip_comments \
                       or c_child.type == tree.XML_PI_NODE and strip_pis \
                       or c_child.type == tree.XML_ENTITY_REF_NODE and strip_entities:
                    tree.xmlUnlinkNode(c_child)
                    attemptDeallocation(c_child)
                c_child = c_next
    tree.END_FOR_EACH_ELEMENT_FROM(c_node)


# helper functions

cdef list _sortedTagList(list l):
    # This is required since the namespace may be None (which Py3
    # can't compare to strings).  A bit of overhead, but at least
    # portable ...
    cdef list decorated_list
    cdef tuple ns_tag
    cdef Py_ssize_t i
    decorated_list = [ (ns_tag[0] or b'', ns_tag[1], i, ns_tag)
                       for i, ns_tag in enumerate(l) ]
    decorated_list.sort()
    return [ item[-1] for item in decorated_list ]

cdef list _filterSpecialTagNames(tag_names, bint* comments, bint* pis, bint* entities):
    cdef list ns_tags
    comments[0] = 0
    pis[0] = 0
    entities[0] = 0

    ns_tags = []
    for tag in tag_names:
        if tag is Comment:
            comments[0] = 1
        elif tag is ProcessingInstruction:
            pis[0] = 1
        elif tag is Entity:
            entities[0] = 1
        else:
            ns_tags.append(_getNsTag(tag))

    return [ (ns, tag if tag != b'*' else None)
             for ns, tag in _sortedTagList(ns_tags) ]

cdef Py_ssize_t _mapTagsToCharArray(xmlDoc* c_doc, list ns_tags,
                                    char** c_ns_tags) except -1:
    cdef Py_ssize_t count = 0
    cdef char* c_tag
    for ns, tag in ns_tags:
        if ns is None:
            c_ns_tags[0] = NULL
        else:
            c_ns_tags[0] = _cstr(ns)
        if tag is None:
            c_ns_tags[1] = NULL
        else:
            c_tag = _cstr(tag)
            c_ns_tags[1] = tree.xmlDictExists(
                c_doc.dict, c_tag, cstd.strlen(c_tag))
            if c_ns_tags[1] == NULL:
                # not in the dict => not in the document
                continue
        c_ns_tags += 2
        count += 1
    return count
