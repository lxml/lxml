# functions for tree cleanup and removing elements from subtrees

def cleanup_namespaces(tree_or_element):
    u"""cleanup_namespaces(tree_or_element)

    Remove all namespace declarations from a subtree that are not used
    by any of the elements in that tree.
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
    cdef xmlNode* c_node
    cdef xmlAttr* c_attr
    cdef _Element element
    cdef list ns_tags
    cdef char* c_name

    element = _rootNodeOrRaise(tree_or_element)
    if not attribute_names: return

    ns_tags = _sortedTagList([ _getNsTag(attr)
                               for attr in <tuple>attribute_names ])
    ns_tags = [ (ns, tag if tag != '*' else None)
                for ns, tag in ns_tags ]

    c_node = element._c_node
    tree.BEGIN_FOR_EACH_ELEMENT_FROM(c_node, c_node, 1)
    if c_node.type == tree.XML_ELEMENT_NODE:
        if c_node.properties is not NULL:
            for ns, tag in ns_tags:
                # must search attributes manually to make sure we only
                # match on blank tag names if there is no namespace
                c_name = NULL if tag is None else _cstr(tag)
                c_attr = c_node.properties
                while c_attr is not NULL:
                    if ns is None:
                        if c_attr.ns is NULL or c_attr.ns.href is NULL:
                            if c_name is NULL or \
                                   cstd.strcmp(c_attr.name, c_name) == 0:
                                tree.xmlRemoveProp(c_attr)
                                break
                    elif c_attr.ns is not NULL and c_attr.ns.href is not NULL:
                        if cstd.strcmp(c_attr.ns.href, _cstr(ns)) == 0:
                            if c_name is NULL or \
                                   cstd.strcmp(c_attr.name, c_name) == 0:
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
    cdef xmlNode* c_node
    cdef xmlNode* c_child
    cdef xmlNode* c_next
    cdef char* c_href
    cdef char* c_name
    cdef _Element element
    cdef _Document doc
    cdef list ns_tags
    cdef bint strip_comments, strip_pis, strip_entities

    doc = _documentOrRaise(tree_or_element)
    element = _rootNodeOrRaise(tree_or_element)
    if not tag_names: return

    ns_tags = _filterSpecialTagNames(
        tag_names, &strip_comments, &strip_pis, &strip_entities)

    c_node = element._c_node
    tree.BEGIN_FOR_EACH_ELEMENT_FROM(c_node, c_node, 1)
    if c_node.type == tree.XML_ELEMENT_NODE:
        # we run through the children here to prevent any problems
        # with the tree iteration which would occur if we unlinked the
        # c_node itself
        c_child = _findChildForwards(c_node, 0)
        while c_child is not NULL:
            if c_child.type == tree.XML_ELEMENT_NODE:
                for ns, tag in ns_tags:
                    if ns is None:
                        # _tagMatches() considers NULL a wildcard
                        # match but we don't
                        if c_child.ns is not NULL and c_child.ns.href is not NULL:
                            continue
                        c_href = NULL
                    else:
                        c_href = _cstr(ns)
                    c_name = NULL if tag is None else _cstr(tag)
                    if _tagMatches(c_child, c_href, c_name):
                        c_next = _nextElement(c_child)
                        if not with_tail:
                            tree.xmlUnlinkNode(c_child)
                        _removeNode(doc, c_child)
                        c_child = c_next
                        break
                else:
                    c_child = _nextElement(c_child)
            elif strip_comments and c_child.type == tree.XML_COMMENT_NODE or \
                     strip_pis and c_child.type == tree.XML_PI_NODE or \
                     strip_entities and c_child.type == tree.XML_ENTITY_REF_NODE:
                c_next = _nextElement(c_child)
                if with_tail:
                    _removeText(c_next)
                tree.xmlUnlinkNode(c_child)
                attemptDeallocation(c_child)
                c_child = c_next
            else:
                c_child = _nextElement(c_child)
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
    cdef xmlNode* c_node
    cdef xmlNode* c_child
    cdef xmlNode* c_next
    cdef char* c_href
    cdef char* c_name
    cdef _Element element
    cdef _Document doc
    cdef list ns_tags
    cdef bint strip_comments, strip_pis, strip_entities

    doc = _documentOrRaise(tree_or_element)
    element = _rootNodeOrRaise(tree_or_element)
    if not tag_names: return

    ns_tags = _filterSpecialTagNames(
        tag_names, &strip_comments, &strip_pis, &strip_entities)

    c_node = element._c_node
    tree.BEGIN_FOR_EACH_ELEMENT_FROM(c_node, c_node, 1)
    if c_node.type == tree.XML_ELEMENT_NODE:
        # we run through the children here to prevent any problems
        # with the tree iteration which would occur if we unlinked the
        # c_node itself
        c_child = _findChildForwards(c_node, 0)
        while c_child is not NULL:
            if c_child.type == tree.XML_ELEMENT_NODE:
                for ns, tag in ns_tags:
                    if ns is None:
                        # _tagMatches() considers NULL a wildcard
                        # match but we don't
                        if c_child.ns is not NULL and c_child.ns.href is not NULL:
                            continue
                        c_href = NULL
                    else:
                        c_href = _cstr(ns)
                    c_name = NULL if tag is None else _cstr(tag)
                    if _tagMatches(c_child, c_href, c_name):
                        if c_child.children is not NULL:
                            c_next = _findChildForwards(c_child, 0)
                        else:
                            c_next = _nextElement(c_child)
                        _replaceNodeByChildren(doc, c_child)
                        if not attemptDeallocation(c_child):
                            if c_child.ns is not NULL:
                                # make namespaces absolute
                                moveNodeToDocument(doc, doc._c_doc, c_child)
                        c_child = c_next
                        break
                else:
                    c_child = c_child.next
            elif strip_comments and c_child.type == tree.XML_COMMENT_NODE or \
                     strip_pis and c_child.type == tree.XML_PI_NODE or \
                     strip_entities and c_child.type == tree.XML_ENTITY_REF_NODE:
                c_next = _nextElement(c_child)
                tree.xmlUnlinkNode(c_child)
                attemptDeallocation(c_child)
                c_child = c_next
            else:
                c_child = _nextElement(c_child)
    tree.END_FOR_EACH_ELEMENT_FROM(c_node)


# helper functions

cdef list _sortedTagList(list l):
    # This is required since the namespace may be None (which Py3
    # can't compare to strings).  A bit of overhead, but at least
    # portable ...
    cdef list decorated_list
    cdef tuple ns_tag
    cdef Py_ssize_t i
    decorated_list = [ (ns_tag[0] or '', ns_tag[1], i, ns_tag)
                       for i, ns_tag in enumerate(l) ]
    decorated_list.sort()
    return [ item[-1] for item in decorated_list ]

cdef list _filterSpecialTagNames(tag_names, bint* comments, bint* pis, bint* entities):
    cdef list ns_tags
    comments[0] = 0
    pis[0] = 0
    entities[0] = 0

    if Comment in tag_names:
        comments[0] = 1
        tag_names = [ tag for tag in tag_names
                      if tag is not Comment ]
    if ProcessingInstruction in tag_names:
        pis[0] = 1
        tag_names = [ tag for tag in tag_names
                      if tag is not ProcessingInstruction ]
    if Entity in tag_names:
        entities[0] = 1
        tag_names = [ tag for tag in tag_names
                      if tag is not Entity ]
    ns_tags = _sortedTagList([ _getNsTag(tag) for tag in tag_names ])
    return [ (ns, tag if tag != '*' else None)
             for ns, tag in ns_tags ]
