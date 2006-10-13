# Proxy functions

# Proxies represent elements, their reference is stored in the C
# structure of the respective node to avoid multiple instantiation of
# the Python class

cdef _NodeBase getProxy(xmlNode* c_node):
    """Get a proxy for a given node.
    """
    #print "getProxy for:", <int>c_node
    if c_node is not NULL and c_node._private is not NULL:
        return <_NodeBase>c_node._private
    else:
        return None

cdef int hasProxy(xmlNode* c_node):
    return c_node._private is not NULL
    
cdef registerProxy(_NodeBase proxy):
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

cdef unregisterProxy(_NodeBase proxy):
    """Unregister a proxy for the node it's proxying for.
    """
    cdef xmlNode* c_node
    c_node = proxy._c_node
    assert c_node._private is <void*>proxy, "Tried to unregister unknown proxy"
    c_node._private = NULL

################################################################################
# temporarily make a node the root node of its document

cdef xmlDoc* _fakeRootDoc(xmlDoc* c_base_doc, xmlNode* c_node):
    # build a temporary document that has the given node as root node
    # note that copy and original must not be modified during its lifetime!!
    # always call _destroyFakeDoc() after use!
    cdef xmlNode* c_child
    cdef xmlNode* c_root
    cdef xmlDoc*  c_doc
    c_root = tree.xmlDocGetRootElement(c_base_doc)
    if c_root is c_node:
        # already the root node
        return c_base_doc

    c_doc  = _copyDoc(c_base_doc, 0)               # non recursive!
    c_root = tree.xmlDocCopyNode(c_node, c_doc, 2) # non recursive!
    tree.xmlDocSetRootElement(c_doc, c_root)

    c_root.children = c_node.children
    c_root.last = c_node.last
    c_root.next = c_root.prev = c_root.parent = NULL

    # store original node
    c_doc._private = c_node

    # divert parent pointers of children
    c_child = c_root.children
    while c_child is not NULL:
        c_child.parent = c_root
        c_child = c_child.next

    c_doc.children = c_root
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

################################################################################
# support for freeing tree elements when proxy objects are destroyed

cdef void attemptDeallocation(xmlNode* c_node):
    """Attempt deallocation of c_node (or higher up in tree).
    """
    cdef xmlNode* c_top
    # could be we actually aren't referring to the tree at all
    if c_node is NULL:
        #print "not freeing, node is NULL"
        return
    c_top = getDeallocationTop(c_node)
    if c_top is not NULL:
        #print "freeing:", c_top.name
        _removeText(c_top.next) # tail
        tree.xmlFreeNode(c_top)

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

cdef void _deallocDocument(xmlDoc* c_doc):
    """We cannot rely on Python's GC to *always* dealloc the _Document *after*
    all proxies it contains => traverse the document and mark all its proxies
    as dead by deleting their xmlNode* reference.
    """
    cdef xmlNode* c_node
    c_node = c_doc.children
    tree.BEGIN_FOR_EACH_ELEMENT_FROM(<xmlNode*>c_doc, c_node, 1)
    if c_node._private is not NULL:
        (<_NodeBase>c_node._private)._c_node = NULL
    tree.END_FOR_EACH_ELEMENT_FROM(c_node)
    tree.xmlFreeDoc(c_doc)

################################################################################
# change _Document references when a node changes documents

cdef void moveNodeToDocument(_NodeBase node, _Document doc):
    """For a node and all nodes below, change document.

    A node can change document in certain operations as an XML
    subtree can move. This updates all possible proxies in the
    tree below (including the current node). It also reconciliates
    namespaces so they're correct inside the new environment.
    """
    tree.xmlReconciliateNs(doc._c_doc, node._c_node)
    if node._doc is not doc:
        node._doc = doc
        changeDocumentBelow(node._c_node, doc)

cdef void changeDocumentBelow(xmlNode* c_parent, _Document doc):
    """Update the Python references in the tree below the node.
    Does not update the node itself.

    Note that we expect C pointers to the document to be updated already by
    libxml2.
    """
    cdef xmlNode* c_node
    c_node = c_parent.children
    tree.BEGIN_FOR_EACH_ELEMENT_FROM(c_parent, c_node, 1)
    if c_node._private is not NULL:
        (<_NodeBase>c_node._private)._doc = doc
    tree.END_FOR_EACH_ELEMENT_FROM(c_node)
