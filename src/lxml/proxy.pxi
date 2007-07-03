# Proxy functions and low level node allocation stuff

# Proxies represent elements, their reference is stored in the C
# structure of the respective node to avoid multiple instantiation of
# the Python class

cdef _Element getProxy(xmlNode* c_node):
    """Get a proxy for a given node.
    """
    #print "getProxy for:", <int>c_node
    if c_node is not NULL and c_node._private is not NULL:
        return <_Element>c_node._private
    else:
        return None

cdef int hasProxy(xmlNode* c_node):
    return c_node._private is not NULL
    
cdef registerProxy(_Element proxy):
    """Register a proxy and type for the node it's proxying for.
    """
    cdef xmlNode* c_node
    # cannot register for NULL
    c_node = proxy._c_node
    if c_node is NULL:
        return
    #print "registering for:", <int>proxy._c_node
    assert c_node._private is NULL, "double registering proxy!"
    c_node._private = <void*>proxy
    # additional INCREF to make sure _Document is GC-ed LAST!
    proxy._gc_doc = <python.PyObject*>proxy._doc
    python.Py_INCREF(proxy._doc)

cdef unregisterProxy(_Element proxy):
    """Unregister a proxy for the node it's proxying for.
    """
    cdef xmlNode* c_node
    c_node = proxy._c_node
    assert c_node._private is <void*>proxy, "Tried to unregister unknown proxy"
    c_node._private = NULL
    python.Py_DECREF(<object>proxy._gc_doc)

################################################################################
# temporarily make a node the root node of its document

cdef xmlDoc* _fakeRootDoc(xmlDoc* c_base_doc, xmlNode* c_node):
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
    _copyParentNamespaces(c_node, c_root)

    c_new_root.children = c_node.children
    c_new_root.last = c_node.last
    c_new_root.next = c_new_root.prev = c_new_root.parent = NULL

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
    if c_doc != c_base_doc:
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

cdef void _copyParentNamespaces(xmlNode* c_from_node, xmlNode* c_to_node):
    """Copy the namespaces of all ancestors of c_from_node to c_to_node.

    This is used in _fakeRootDoc() to avoid loosing namespace declarations.
    """
    cdef xmlNode* c_parent
    cdef xmlNs* c_ns
    cdef xmlNs* c_new_ns
    cdef int prefix_known
    c_parent = c_from_node.parent
    while c_parent is not NULL and tree._isElementOrXInclude(c_parent):
        c_new_ns = c_parent.nsDef
        while c_new_ns is not NULL:
            # check if prefix is already defined
            c_ns = tree.xmlSearchNs(c_to_node.doc, c_to_node, c_new_ns.prefix)
            if c_ns is NULL:
                tree.xmlNewNs(c_to_node, c_new_ns.href, c_new_ns.prefix)
            c_new_ns = c_new_ns.next
        c_parent = c_parent.parent

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

cdef void moveNodeToDocument(_Document doc, xmlNode* c_element):
    """Fix the xmlNs pointers of a node and its subtree that were moved.

    Mainly copied from libxml2's xmlReconciliateNs().  Expects libxml2 doc
    pointers of node to be correct already, but fixes _Document references.
    """
    cdef _Element element
    cdef xmlDoc* c_doc
    cdef xmlNode* c_start_node
    cdef xmlNode* c_node
    cdef xmlNs** c_ns_new_cache
    cdef xmlNs** c_ns_old_cache
    cdef xmlNs* c_ns
    cdef xmlNs* c_new_ns
    cdef xmlNs* c_del_ns
    cdef xmlNs* c_last_del_ns
    cdef cstd.size_t i, c_cache_size, c_cache_last

    if not tree._isElementOrXInclude(c_element):
        return

    c_doc = c_element.doc
    c_start_node = c_element
    c_ns_new_cache = NULL
    c_ns_old_cache = NULL
    c_cache_size = 0
    c_cache_last = 0
    c_del_ns = c_last_del_ns = NULL

    while c_element is not NULL:
        # remove namespaces defined here that are known in the new ancestors
        if c_element.nsDef is not NULL:
            while c_element.nsDef is not NULL:
                c_ns = tree.xmlSearchNsByHref(
                    c_element.doc, c_element.parent, c_element.nsDef.href)
                if c_ns is NULL:
                    break
                if c_del_ns is NULL:
                    c_del_ns = c_last_del_ns = c_element.nsDef
                else:
                    c_last_del_ns.next = c_element.nsDef
                    c_last_del_ns = c_element.nsDef
                c_element.nsDef = c_element.nsDef.next
            if c_element.nsDef is not NULL:
                c_new_ns = c_element.nsDef
                while c_new_ns.next is not NULL:
                    if c_new_ns.next is not c_element.ns:
                        c_ns = tree.xmlSearchNsByHref(
                            c_element.doc, c_element.parent, c_new_ns.next.href)
                        if c_ns is not NULL:
                            # already known or equal to a known definition
                            if c_del_ns is NULL:
                                c_del_ns = c_last_del_ns = c_new_ns.next
                            else:
                                c_last_del_ns.next = c_new_ns.next
                                c_last_del_ns = c_new_ns.next
                            c_new_ns.next = c_new_ns.next.next
                        else:
                            c_new_ns = c_new_ns.next
                    else:
                        c_new_ns = c_new_ns.next

        # make sure the namespace of an element and its attributes is declared
        # in this document
        c_node = c_element
        while c_node is not NULL:
            if c_node.ns is not NULL:
                c_ns = c_node.ns
                for i from 0 <= i < c_cache_last:
                    if c_ns is c_ns_old_cache[i]:
                        c_node.ns = c_ns_new_cache[i]
                        c_ns = NULL
                        break

                if c_ns is not NULL:
                    # not in cache, must find a replacement from this document
                    c_new_ns = doc._findOrBuildNodeNs(c_node,
                                                      c_ns.href, c_ns.prefix)
                    if c_cache_last >= c_cache_size:
                        # must resize cache
                        if c_cache_size == 0:
                            c_cache_size = 20
                        else:
                            c_cache_size = c_cache_size * 2
                        c_ns_new_cache = <xmlNs**> python.PyMem_Realloc(
                            c_ns_new_cache, c_cache_size * sizeof(xmlNs*))
                        if c_ns_new_cache is NULL:
                            python.PyMem_Free(c_ns_old_cache)
                            python.PyErr_NoMemory()
                        c_ns_old_cache = <xmlNs**> python.PyMem_Realloc(
                            c_ns_old_cache, c_cache_size * sizeof(xmlNs*))
                        if c_ns_old_cache is NULL:
                            python.PyMem_Free(c_ns_new_cache)
                            python.PyErr_NoMemory()
                    c_ns_new_cache[c_cache_last] = c_new_ns
                    c_ns_old_cache[c_cache_last] = c_node.ns
                    c_cache_last = c_cache_last + 1
                    c_node.ns = c_new_ns
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

            # fix _Document reference (may dealloc the original document!)
            if c_element._private is not NULL:
                element = <_Element>c_element._private
                if element._doc is not doc:
                    python.Py_INCREF(doc)
                    python.Py_DECREF(element._doc)
                    element._doc = doc
                    element._gc_doc = <python.PyObject*>doc

            if c_element is c_start_node:
                break

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

                # fix _Document reference (may dealloc the original document!)
                if c_element._private is not NULL:
                    element = <_Element>c_element._private
                    if element._doc is not doc:
                        python.Py_INCREF(doc)
                        python.Py_DECREF(element._doc)
                        element._doc = doc
                        element._gc_doc = <python.PyObject*>doc

                if c_element is c_start_node:
                    break
                # parents already done -> look for their siblings
                c_node = c_element.next
                while (c_node is not NULL and
                       not tree._isElementOrXInclude(c_node)):
                    c_node = c_node.next
        if c_node is c_start_node:
            break
        c_element = c_node

    # free now unused namespace declarations
    if c_del_ns is not NULL:
        c_last_del_ns.next = NULL
        tree.xmlFreeNsList(c_del_ns)

    # cleanup
    if c_ns_new_cache is not NULL:
        python.PyMem_Free(c_ns_new_cache)
    if c_ns_old_cache is not NULL:
        python.PyMem_Free(c_ns_old_cache)
