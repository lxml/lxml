# Proxy functions and low level node allocation stuff

# Proxies represent elements, their reference is stored in the C
# structure of the respective node to avoid multiple instantiation of
# the Python class.
#
# In PyPy, we store weak references instead of borrowed back-pointer
# references as borrowed references cannot be long-lived in its
# compatibility layer cpyext. Since we can't know when the object dies
# (and even the weak-ref callback won't tell us that), we double check
# on access that the object really is still alive and delete the
# weak-ref if it isn't.

cdef inline _Element getProxy(xmlNode* c_node):
    u"""Get a proxy for a given node.
    """
    #print "getProxy for:", <int>c_node
    if c_node is not NULL and c_node._private is not NULL:
        if python.IS_PYPY:
            return <_Element>python.PyWeakref_LockObject(<python.PyObject*>c_node._private)
        else:
            return <_Element>c_node._private
    else:
        return None

cdef inline bint hasProxy(xmlNode* c_node):
    if c_node._private is NULL:
        return False
    if python.IS_PYPY:
        return _isProxyAliveInPypy(c_node)
    return True

cdef bint _isProxyAliveInPypy(xmlNode* c_node):
    retval = True
    if python.PyWeakref_LockObject(<python.PyObject*>c_node._private) is None:
        # proxy has already died => remove weak reference
        weakref_ptr = <python.PyObject*>c_node._private
        c_node._private = NULL
        python.Py_XDECREF(weakref_ptr)
        retval = False
    return retval

cdef inline int _registerProxy(_Element proxy, _Document doc,
                               xmlNode* c_node) except -1:
    u"""Register a proxy and type for the node it's proxying for.
    """
    #print "registering for:", <int>proxy._c_node
    assert not hasProxy(c_node), u"double registering proxy!"
    proxy._doc = doc
    proxy._c_node = c_node
    if python.IS_PYPY:
        c_node._private = <void*>python.PyWeakref_NewRef(proxy, NULL)
    else:
        c_node._private = <void*>proxy
    return 0

cdef inline int _unregisterProxy(_Element proxy) except -1:
    u"""Unregister a proxy for the node it's proxying for.
    """
    cdef xmlNode* c_node = proxy._c_node
    if python.IS_PYPY:
        weakref_ptr = <python.PyObject*>c_node._private
        c_node._private = NULL
        python.Py_XDECREF(weakref_ptr)
    else:
        assert c_node._private is <void*>proxy, u"Tried to unregister unknown proxy"
        c_node._private = NULL
    return 0

################################################################################
# temporarily make a node the root node of its document

cdef xmlDoc* _fakeRootDoc(xmlDoc* c_base_doc, xmlNode* c_node) except NULL:
    return _plainFakeRootDoc(c_base_doc, c_node, 1)

cdef xmlDoc* _plainFakeRootDoc(xmlDoc* c_base_doc, xmlNode* c_node,
                               bint with_siblings) except NULL:
    # build a temporary document that has the given node as root node
    # note that copy and original must not be modified during its lifetime!!
    # always call _destroyFakeDoc() after use!
    cdef xmlNode* c_child
    cdef xmlNode* c_root
    cdef xmlNode* c_new_root
    cdef xmlDoc*  c_doc
    if with_siblings or (c_node.prev is NULL and c_node.next is NULL):
        c_root = tree.xmlDocGetRootElement(c_base_doc)
        if c_root is c_node:
            # already the root node, no siblings
            return c_base_doc

    c_doc  = _copyDoc(c_base_doc, 0)                   # non recursive!
    c_new_root = tree.xmlDocCopyNode(c_node, c_doc, 2) # non recursive!
    tree.xmlDocSetRootElement(c_doc, c_new_root)
    _copyParentNamespaces(c_node, c_new_root)

    c_new_root.children = c_node.children
    c_new_root.last = c_node.last
    c_new_root.next = c_new_root.prev = NULL

    # store original node
    c_doc._private = c_node

    # divert parent pointers of children
    c_child = c_new_root.children
    while c_child is not NULL:
        c_child.parent = c_new_root
        c_child = c_child.next

    c_doc.children = c_new_root
    return c_doc

cdef void _destroyFakeDoc(xmlDoc* c_base_doc, xmlDoc* c_doc):
    # delete a temporary document
    cdef xmlNode* c_child
    cdef xmlNode* c_parent
    cdef xmlNode* c_root
    if c_doc is c_base_doc:
        return
    c_root = tree.xmlDocGetRootElement(c_doc)

    # restore parent pointers of children
    c_parent = <xmlNode*>c_doc._private
    c_child = c_root.children
    while c_child is not NULL:
        c_child.parent = c_parent
        c_child = c_child.next

    # prevent recursive removal of children
    c_root.children = c_root.last = NULL
    tree.xmlFreeDoc(c_doc)

cdef _Element _fakeDocElementFactory(_Document doc, xmlNode* c_element):
    u"""Special element factory for cases where we need to create a fake
    root document, but still need to instantiate arbitrary nodes from
    it.  If we instantiate the fake root node, things will turn bad
    when it's destroyed.

    Instead, if we are asked to instantiate the fake root node, we
    instantiate the original node instead.
    """
    if c_element.doc is not doc._c_doc:
        if c_element.doc._private is not NULL:
            if c_element is c_element.doc.children:
                c_element = <xmlNode*>c_element.doc._private
                #assert c_element.type == tree.XML_ELEMENT_NODE
    return _elementFactory(doc, c_element)

################################################################################
# support for freeing tree elements when proxy objects are destroyed

cdef int attemptDeallocation(xmlNode* c_node):
    u"""Attempt deallocation of c_node (or higher up in tree).
    """
    cdef xmlNode* c_top
    # could be we actually aren't referring to the tree at all
    if c_node is NULL:
        #print "not freeing, node is NULL"
        return 0
    c_top = getDeallocationTop(c_node)
    if c_top is not NULL:
        #print "freeing:", c_top.name
        _removeText(c_top.next) # tail
        tree.xmlFreeNode(c_top)
        return 1
    return 0

cdef xmlNode* getDeallocationTop(xmlNode* c_node):
    u"""Return the top of the tree that can be deallocated, or NULL.
    """
    cdef xmlNode* c_next
    #print "trying to do deallocating:", c_node.type
    if hasProxy(c_node):
        #print "Not freeing: proxies still exist"
        return NULL
    while c_node.parent is not NULL:
        c_node = c_node.parent
        #print "checking:", c_current.type
        if c_node.type == tree.XML_DOCUMENT_NODE or \
               c_node.type == tree.XML_HTML_DOCUMENT_NODE:
            #print "not freeing: still in doc"
            return NULL
        # if we're still attached to the document, don't deallocate
        if hasProxy(c_node):
            #print "Not freeing: proxies still exist"
            return NULL
    # see whether we have children to deallocate
    if not canDeallocateChildNodes(c_node):
        return NULL
    # see whether we have siblings to deallocate
    c_next = c_node.prev
    while c_next:
        if _isElement(c_next):
            if hasProxy(c_next) or not canDeallocateChildNodes(c_next):
                return NULL
        c_next = c_next.prev
    c_next = c_node.next
    while c_next:
        if _isElement(c_next):
            if hasProxy(c_next) or not canDeallocateChildNodes(c_next):
                return NULL
        c_next = c_next.next
    return c_node

cdef int canDeallocateChildNodes(xmlNode* c_parent):
    cdef xmlNode* c_node
    c_node = c_parent.children
    tree.BEGIN_FOR_EACH_ELEMENT_FROM(c_parent, c_node, 1)
    if hasProxy(c_node):
        return 0
    tree.END_FOR_EACH_ELEMENT_FROM(c_node)
    return 1

################################################################################
# fix _Document references and namespaces when a node changes documents

cdef void _copyParentNamespaces(xmlNode* c_from_node, xmlNode* c_to_node) nogil:
    u"""Copy the namespaces of all ancestors of c_from_node to c_to_node.
    """
    cdef xmlNode* c_parent
    cdef xmlNs* c_ns
    cdef xmlNs* c_new_ns
    cdef int prefix_known
    c_parent = c_from_node.parent
    while c_parent and (tree._isElementOrXInclude(c_parent) or
                        c_parent.type == tree.XML_DOCUMENT_NODE):
        c_new_ns = c_parent.nsDef
        while c_new_ns:
            # libxml2 will check if the prefix is already defined
            tree.xmlNewNs(c_to_node, c_new_ns.href, c_new_ns.prefix)
            c_new_ns = c_new_ns.next
        c_parent = c_parent.parent

ctypedef struct _nscache:
    xmlNs** new
    xmlNs** old
    size_t size
    size_t last

cdef int _growNsCache(_nscache* c_ns_cache) except -1:
    cdef xmlNs** c_ns_ptr
    if c_ns_cache.size == 0:
        c_ns_cache.size = 20
    else:
        c_ns_cache.size *= 2
    c_ns_ptr = <xmlNs**> stdlib.realloc(
        c_ns_cache.new, c_ns_cache.size * sizeof(xmlNs*))
    if c_ns_ptr is not NULL:
        c_ns_cache.new = c_ns_ptr
        c_ns_ptr = <xmlNs**> stdlib.realloc(
            c_ns_cache.old, c_ns_cache.size * sizeof(xmlNs*))
    if c_ns_ptr is not NULL:
        c_ns_cache.old = c_ns_ptr
    else:
        stdlib.free(c_ns_cache.new)
        stdlib.free(c_ns_cache.old)
        raise MemoryError()
    return 0

cdef inline int _appendToNsCache(_nscache* c_ns_cache,
                                 xmlNs* c_old_ns, xmlNs* c_new_ns) except -1:
    if c_ns_cache.last >= c_ns_cache.size:
        _growNsCache(c_ns_cache)
    c_ns_cache.old[c_ns_cache.last] = c_old_ns
    c_ns_cache.new[c_ns_cache.last] = c_new_ns
    c_ns_cache.last += 1

cdef int _stripRedundantNamespaceDeclarations(
    xmlNode* c_element, _nscache* c_ns_cache, xmlNs** c_del_ns_list) except -1:
    u"""Removes namespace declarations from an element that are already
    defined in its parents.  Does not free the xmlNs's, just prepends
    them to the c_del_ns_list.
    """
    cdef xmlNs* c_ns
    cdef xmlNs* c_ns_next
    cdef xmlNs** c_nsdef
    # use a xmlNs** to handle assignments to "c_element.nsDef" correctly
    c_nsdef = &c_element.nsDef
    while c_nsdef[0] is not NULL:
        c_ns = tree.xmlSearchNsByHref(
            c_element.doc, c_element.parent, c_nsdef[0].href)
        if c_ns is NULL:
            # new namespace href => keep and cache the ns declaration
            _appendToNsCache(c_ns_cache, c_nsdef[0], c_nsdef[0])
            c_nsdef = &c_nsdef[0].next
        else:
            # known namespace href => cache mapping and strip old ns
            _appendToNsCache(c_ns_cache, c_nsdef[0], c_ns)
            # cut out c_nsdef.next and prepend it to garbage chain
            c_ns_next = c_nsdef[0].next
            c_nsdef[0].next = c_del_ns_list[0]
            c_del_ns_list[0] = c_nsdef[0]
            c_nsdef[0] = c_ns_next
    return 0

cdef int moveNodeToDocument(_Document doc, xmlDoc* c_source_doc,
                            xmlNode* c_element) except -1:
    u"""Fix the xmlNs pointers of a node and its subtree that were moved.

    Originally copied from libxml2's xmlReconciliateNs().  Expects
    libxml2 doc pointers of node to be correct already, but fixes
    _Document references.

    For each node in the subtree, we do this:

    1) Remove redundant declarations of namespace that are already
       defined in its parents.

    2) Replace namespaces that are *not* defined on the node or its
       parents by the equivalent namespace declarations that *are*
       defined on the node or its parents (possibly using a different
       prefix).  If a namespace is unknown, declare a new one on the
       node.

    3) Reassign the names of tags and attribute from the dict of the
       target document *iff* it is different from the dict used in the
       source subtree.

    4) Set the Document reference to the new Document (if different).
       This is done on backtracking to keep the original Document
       alive as long as possible, until all its elements are updated.

    Note that the namespace declarations are removed from the tree in
    step 1), but freed only after the complete subtree was traversed
    and all occurrences were replaced by tree-internal pointers.
    """
    cdef xmlNode* c_start_node
    cdef xmlNode* c_node
    cdef char* c_name
    cdef _nscache c_ns_cache
    cdef xmlNs* c_ns
    cdef xmlNs* c_ns_next
    cdef xmlNs* c_nsdef
    cdef xmlNs* c_del_ns_list
    cdef size_t i, proxy_count = 0

    if not tree._isElementOrXInclude(c_element):
        return 0

    c_start_node = c_element
    c_del_ns_list = NULL

    c_ns_cache.new = NULL
    c_ns_cache.old = NULL
    c_ns_cache.size = 0
    c_ns_cache.last = 0

    tree.BEGIN_FOR_EACH_FROM(c_element, c_element, 1)
    if tree._isElementOrXInclude(c_element):
        if hasProxy(c_element):
            proxy_count += 1

        # 1) cut out namespaces defined here that are already known by
        #    the ancestors
        if c_element.nsDef is not NULL:
            _stripRedundantNamespaceDeclarations(
                c_element, &c_ns_cache, &c_del_ns_list)

        # 2) make sure the namespaces of an element and its attributes
        #    are declared in this document (i.e. on the node or its parents)
        c_node = c_element
        while c_node is not NULL:
            if c_node.ns is not NULL:
                c_ns = NULL
                for i in range(c_ns_cache.last):
                    if c_node.ns is c_ns_cache.old[i]:
                        if (c_node.type == tree.XML_ATTRIBUTE_NODE
                                and c_node.ns.prefix
                                and not c_ns_cache.new[i].prefix):
                            # avoid dropping prefix from attributes
                            continue
                        c_ns = c_ns_cache.new[i]
                        break

                if not c_ns:
                    # not in cache or not acceptable
                    # => find a replacement from this document
                    c_ns = doc._findOrBuildNodeNs(
                        c_start_node, c_node.ns.href, c_node.ns.prefix,
                        c_node.type == tree.XML_ATTRIBUTE_NODE)
                    _appendToNsCache(&c_ns_cache, c_node.ns, c_ns)
                c_node.ns = c_ns

            if c_node is c_element:
                # after the element, continue with its attributes
                c_node = <xmlNode*>c_element.properties
            else:
                c_node = c_node.next
    tree.END_FOR_EACH_FROM(c_element)

    # free now unused namespace declarations
    if c_del_ns_list is not NULL:
        tree.xmlFreeNsList(c_del_ns_list)

    # cleanup
    if c_ns_cache.new is not NULL:
        stdlib.free(c_ns_cache.new)
    if c_ns_cache.old is not NULL:
        stdlib.free(c_ns_cache.old)

    # 3) fix the names in the tree if we moved it from a different thread
    if doc._c_doc.dict is not c_source_doc.dict:
        fixThreadDictNames(c_start_node, c_source_doc.dict, doc._c_doc.dict)

    # 4) fix _Document references
    #    (and potentially deallocate the source document)
    if proxy_count > 0:
        if proxy_count == 1 and c_start_node._private is not NULL:
            proxy = getProxy(c_start_node)
            if proxy is not None:
                if proxy._doc is not doc:
                    proxy._doc = doc
            else:
                fixElementDocument(c_start_node, doc, proxy_count)
        else:
            fixElementDocument(c_start_node, doc, proxy_count)

    return 0


cdef void fixElementDocument(xmlNode* c_element, _Document doc,
                             size_t proxy_count):
    cdef xmlNode* c_node = c_element
    cdef _Element proxy = None # init-to-None required due to fake-loop below
    tree.BEGIN_FOR_EACH_FROM(c_element, c_node, 1)
    if c_node._private is not NULL:
        proxy = getProxy(c_node)
        if proxy is not None:
            if proxy._doc is not doc:
                proxy._doc = doc
            proxy_count -= 1
            if proxy_count == 0:
                return
    tree.END_FOR_EACH_FROM(c_node)

cdef void fixThreadDictNames(xmlNode* c_element,
                             tree.xmlDict* c_src_dict,
                             tree.xmlDict* c_dict) nogil:
    # re-assign the names of tags and attributes
    #
    # this should only be called when the element is based on a
    # different libxml2 tag name dictionary
    if c_element.type == tree.XML_DOCUMENT_NODE or \
            c_element.type == tree.XML_HTML_DOCUMENT_NODE:
        # may define "xml" namespace
        fixThreadDictNsForNode(c_element, c_src_dict, c_dict)
        c_element = c_element.children
        while c_element is not NULL:
            fixThreadDictNamesForNode(c_element, c_src_dict, c_dict)
            c_element = c_element.next
    elif tree._isElementOrXInclude(c_element):
        fixThreadDictNamesForNode(c_element, c_src_dict, c_dict)

cdef void fixThreadDictNamesForNode(xmlNode* c_element,
                                    tree.xmlDict* c_src_dict,
                                    tree.xmlDict* c_dict) nogil:
    cdef xmlNode* c_node = c_element
    tree.BEGIN_FOR_EACH_FROM(c_element, c_node, 1)
    if c_node.name is not NULL:
        fixThreadDictNameForNode(c_node, c_src_dict, c_dict)
    if c_node.type in (tree.XML_ELEMENT_NODE, tree.XML_XINCLUDE_START):
        fixThreadDictNamesForAttributes(
            c_node.properties, c_src_dict, c_dict)
        fixThreadDictNsForNode(c_node, c_src_dict, c_dict)
    elif c_node.type == tree.XML_TEXT_NODE:
        # libxml2's SAX2 parser interns some indentation space
        fixThreadDictContentForNode(c_node, c_src_dict, c_dict)
    tree.END_FOR_EACH_FROM(c_node)

cdef inline void fixThreadDictNamesForAttributes(tree.xmlAttr* c_attr,
                                                 tree.xmlDict* c_src_dict,
                                                 tree.xmlDict* c_dict) nogil:
    cdef xmlNode* c_child
    cdef xmlNode* c_node = <xmlNode*>c_attr
    while c_node is not NULL:
        fixThreadDictNameForNode(c_node, c_src_dict, c_dict)
        # libxml2 keeps some (!) attribute values in the dict
        c_child = c_node.children
        while c_child is not NULL:
            fixThreadDictContentForNode(c_child, c_src_dict, c_dict)
            c_child = c_child.next
        c_node = c_node.next

cdef inline void fixThreadDictNameForNode(xmlNode* c_node,
                                          tree.xmlDict* c_src_dict,
                                          tree.xmlDict* c_dict) nogil:
    cdef const_xmlChar* c_name = c_node.name
    if c_name is not NULL and \
           c_node.type != tree.XML_TEXT_NODE and \
           c_node.type != tree.XML_COMMENT_NODE:
        if tree.xmlDictOwns(c_src_dict, c_node.name):
            # c_name can be NULL on memory error, but we don't handle that here
            c_name = tree.xmlDictLookup(c_dict, c_name, -1)
            if c_name is not NULL:
                c_node.name = c_name

cdef inline void fixThreadDictContentForNode(xmlNode* c_node,
                                             tree.xmlDict* c_src_dict,
                                             tree.xmlDict* c_dict) nogil:
    if c_node.content is not NULL and \
           c_node.content is not <xmlChar*>&c_node.properties:
        if tree.xmlDictOwns(c_src_dict, c_node.content):
            # result can be NULL on memory error, but we don't handle that here
            c_node.content = <xmlChar*>tree.xmlDictLookup(c_dict, c_node.content, -1)

cdef inline void fixThreadDictNsForNode(xmlNode* c_node,
                                        tree.xmlDict* c_src_dict,
                                        tree.xmlDict* c_dict) nogil:
    cdef xmlNs* c_ns = c_node.nsDef
    while c_ns is not NULL:
        if c_ns.href is not NULL:
            if tree.xmlDictOwns(c_src_dict, c_ns.href):
                c_ns.href = tree.xmlDictLookup(c_dict, c_ns.href, -1)
        if c_ns.prefix is not NULL:
            if tree.xmlDictOwns(c_src_dict, c_ns.prefix):
                c_ns.prefix = tree.xmlDictLookup(c_dict, c_ns.prefix, -1)
        c_ns = c_ns.next
