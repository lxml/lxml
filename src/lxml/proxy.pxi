# Proxy functions and low level node allocation stuff

# Proxies represent elements, their reference is stored in the C
# structure of the respective node to avoid multiple instantiation of
# the Python class

cdef inline _Element getProxy(xmlNode* c_node):
    """Get a proxy for a given node.
    """
    #print "getProxy for:", <int>c_node
    if c_node is not NULL and c_node._private is not NULL:
        return <_Element>c_node._private
    else:
        return None

cdef inline int hasProxy(xmlNode* c_node):
    return c_node._private is not NULL
    
cdef inline int _registerProxy(_Element proxy) except -1:
    """Register a proxy and type for the node it's proxying for.
    """
    cdef xmlNode* c_node
    # cannot register for NULL
    c_node = proxy._c_node
    if c_node is NULL:
        return 0
    #print "registering for:", <int>proxy._c_node
    assert c_node._private is NULL, "double registering proxy!"
    c_node._private = <void*>proxy
    # additional INCREF to make sure _Document is GC-ed LAST!
    proxy._gc_doc = <python.PyObject*>proxy._doc
    python.Py_INCREF(proxy._doc)

cdef inline int _unregisterProxy(_Element proxy) except -1:
    """Unregister a proxy for the node it's proxying for.
    """
    cdef xmlNode* c_node
    c_node = proxy._c_node
    assert c_node._private is <void*>proxy, "Tried to unregister unknown proxy"
    c_node._private = NULL
    return 0

cdef inline void _releaseProxy(_Element proxy):
    """An additional DECREF for the document.
    """
    python.Py_XDECREF(proxy._gc_doc)
    proxy._gc_doc = NULL

cdef inline void _updateProxyDocument(xmlNode* c_node, _Document doc):
    """Replace the document reference of a proxy.

    This may deallocate the original document of the proxy!
    """
    cdef _Element element = <_Element>c_node._private
    if element._doc is not doc:
        python.Py_INCREF(doc)
        python.Py_DECREF(element._doc)
        element._doc = doc
        element._gc_doc = <python.PyObject*>doc

################################################################################
# temporarily make a node the root node of its document

cdef xmlDoc* _fakeRootDoc(xmlDoc* c_base_doc, xmlNode* c_node) except NULL:
    # build a temporary document that has the given node as root node
    # note that copy and original must not be modified during its lifetime!!
    # always call _destroyFakeDoc() after use!
    cdef xmlNode* c_child
    cdef xmlNode* c_root
    cdef xmlNode* c_new_root
    cdef xmlDoc*  c_doc
    c_root = tree.xmlDocGetRootElement(c_base_doc)
    if c_root is c_node:
        # already the root node
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
    """Special element factory for cases where we need to create a fake
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
    """Attempt deallocation of c_node (or higher up in tree).
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
    """Return the top of the tree that can be deallocated, or NULL.
    """
    cdef xmlNode* c_current
    cdef xmlNode* c_top
    #print "trying to do deallocating:", c_node.type
    if c_node._private is not NULL:
        #print "Not freeing: proxies still exist"
        return NULL
    c_current = c_node.parent
    c_top = c_node
    while c_current is not NULL:
        #print "checking:", c_current.type
        if c_current.type == tree.XML_DOCUMENT_NODE or \
               c_current.type == tree.XML_HTML_DOCUMENT_NODE:
            #print "not freeing: still in doc"
            return NULL
        # if we're still attached to the document, don't deallocate
        if c_current._private is not NULL:
            #print "Not freeing: proxies still exist"
            return NULL
        c_top = c_current
        c_current = c_current.parent
    # see whether we have children to deallocate
    if canDeallocateChildNodes(c_top):
        return c_top
    else:
        return NULL

cdef int canDeallocateChildNodes(xmlNode* c_parent):
    cdef xmlNode* c_node
    c_node = c_parent.children
    tree.BEGIN_FOR_EACH_ELEMENT_FROM(c_parent, c_node, 1)
    if c_node._private is not NULL:
        return 0
    tree.END_FOR_EACH_ELEMENT_FROM(c_node)
    return 1

################################################################################
# fix _Document references and namespaces when a node changes documents

cdef void _copyParentNamespaces(xmlNode* c_from_node, xmlNode* c_to_node):
    """Copy the namespaces of all ancestors of c_from_node to c_to_node.
    """
    cdef xmlNode* c_parent
    cdef xmlNs* c_ns
    cdef xmlNs* c_new_ns
    cdef int prefix_known
    c_parent = c_from_node.parent
    while c_parent is not NULL and (tree._isElementOrXInclude(c_parent) or
                                    c_parent.type == tree.XML_DOCUMENT_NODE):
        c_new_ns = c_parent.nsDef
        while c_new_ns is not NULL:
            # libxml2 will check if the prefix is already defined
            tree.xmlNewNs(c_to_node, c_new_ns.href, c_new_ns.prefix)
            c_new_ns = c_new_ns.next
        c_parent = c_parent.parent

ctypedef struct _nscache:
    xmlNs** new
    xmlNs** old
    cstd.size_t size
    cstd.size_t last

cdef int _growNsCache(_nscache* c_ns_cache) except -1:
    cdef xmlNs** c_ns_ptr
    if c_ns_cache.size == 0:
        c_ns_cache.size = 20
    else:
        c_ns_cache.size *= 2
    c_ns_ptr = <xmlNs**> cstd.realloc(
        c_ns_cache.new, c_ns_cache.size * sizeof(xmlNs*))
    if c_ns_ptr is not NULL:
        c_ns_cache.new = c_ns_ptr
        c_ns_ptr = <xmlNs**> cstd.realloc(
            c_ns_cache.old, c_ns_cache.size * sizeof(xmlNs*))
    if c_ns_ptr is not NULL:
        c_ns_cache.old = c_ns_ptr
    else:
        cstd.free(c_ns_cache.new)
        cstd.free(c_ns_cache.old)
        python.PyErr_NoMemory()
        return -1
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
    """Removes namespace declarations from an element that are already
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
            # known namespace href => strip the ns
            if c_ns is tree.xmlSearchNs(c_element.doc, c_element.parent,
                                        c_ns.prefix):
                # prefix is not shadowed by parents => ns is reusable
                _appendToNsCache(c_ns_cache, c_nsdef[0], c_ns)
            # cut out c_nsdef.next and prepend it to garbage chain
            c_ns_next = c_nsdef[0].next
            c_nsdef[0].next = c_del_ns_list[0]
            c_del_ns_list[0] = c_nsdef[0]
            c_nsdef[0] = c_ns_next
    return 0

cdef int moveNodeToDocument(_Document doc, xmlDoc* c_source_doc,
                            xmlNode* c_element) except -1:
    """Fix the xmlNs pointers of a node and its subtree that were moved.

    Mainly copied from libxml2's xmlReconciliateNs().  Expects libxml2 doc
    pointers of node to be correct already, but fixes _Document references.

    For each node in the subtree, we do three things here:

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
    cdef cstd.size_t i
    cdef tree.xmlDict* c_dict

    if not tree._isElementOrXInclude(c_element):
        return 0

    # we need to copy the names of tags and attributes iff the element
    # is based on a different libxml2 tag name dictionary
    if doc._c_doc.dict is not c_source_doc.dict:
        c_dict = doc._c_doc.dict
    else:
        c_dict = NULL

    c_start_node = c_element
    c_del_ns_list = NULL

    c_ns_cache.new = NULL
    c_ns_cache.old = NULL
    c_ns_cache.size = 0
    c_ns_cache.last = 0

    while c_element is not NULL:
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
                for i from 0 <= i < c_ns_cache.last:
                    if c_node.ns is c_ns_cache.old[i]:
                        c_node.ns = c_ns_cache.new[i]
                        break
                else:
                    # not in cache => find a replacement from this document
                    c_ns = doc._findOrBuildNodeNs(
                        c_element, c_node.ns.href, c_node.ns.prefix)
                    _appendToNsCache(&c_ns_cache, c_node.ns, c_ns)
                    c_node.ns = c_ns

            # 3) re-assign names from the target dict
            if c_dict is not NULL:
                c_name = tree.xmlDictLookup(c_dict, c_node.name, -1)
                # c_name can be NULL on memory error, but we don't
                # handle that here
                if c_name is not NULL:
                    c_node.name = c_name

            if c_node is c_element:
                # after the element, continue with its attributes
                c_node = <xmlNode*>c_element.properties
            else:
                c_node = c_node.next

        # traverse to next element, start with children
        c_node = c_element.children
        while c_node is not NULL and \
              not tree._isElementOrXInclude(c_node):
            c_node = c_node.next

        if c_node is NULL:
            # no children => back off and continue with siblings and parents

            # 4) fix _Document reference (may dealloc the original document!)
            if c_element._private is not NULL:
                _updateProxyDocument(c_element, doc)

            if c_element is c_start_node:
                break # all done

            # continue with siblings
            c_node = c_element.next
            while (c_node is not NULL and
                   not tree._isElementOrXInclude(c_node)):
                c_node = c_node.next
            # if that didn't help, back off through parents' siblings
            while c_node is NULL:
                c_element = c_element.parent
                if c_element is NULL or not tree._isElementOrXInclude(c_element):
                    break

                # 4) fix _Document reference (may dealloc the original document!)
                if c_element._private is not NULL:
                    _updateProxyDocument(c_element, doc)

                if c_element is c_start_node:
                    break
                # parents already done -> look for their siblings
                c_node = c_element.next
                while (c_node is not NULL and
                       not tree._isElementOrXInclude(c_node)):
                    c_node = c_node.next
        if c_node is c_start_node:
            break # all done
        c_element = c_node

    # free now unused namespace declarations
    if c_del_ns_list is not NULL:
        tree.xmlFreeNsList(c_del_ns_list)

    # cleanup
    if c_ns_cache.new is not NULL:
        cstd.free(c_ns_cache.new)
    if c_ns_cache.old is not NULL:
        cstd.free(c_ns_cache.old)

    return 0
