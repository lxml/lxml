from tree cimport xmlNode, xmlDoc, xmlAttr
import weakref

cdef class SimpleDocumentProxyBase:
    pass

cdef class DocumentProxyBase(SimpleDocumentProxyBase):
    def __init__(self):
        self._registry = NodeRegistry()
        
    def getProxy(self, id, proxy_type=0):
        # XXX This cannot be a cdef, as this apparently strips off the
        # weakref functionality from the returned object, possibly
        # by the cast to NodeProxyBase, which is not yet weakreffable
        return self._registry.getProxy(id, proxy_type)

    def registerProxy(self, SimpleNodeProxyBase proxy, proxy_type=0):
        self._registry.registerProxy(proxy, proxy_type)

    def unregisterProxy(self, SimpleNodeProxyBase proxy, proxy_type=0):
        """Unregister a proxy again for a particular node.
        """
        self._registry.unregisterProxy(proxy, proxy_type)
        
    def getProxies(self):
        return self._registry._proxies
        
    def __dealloc__(self):
        # if there are no more references to the document, it is safe
        # to clean the whole thing up, as all nodes have a reference to
        # the document
        # print "free doc"
        tree.xmlFreeDoc(self._c_doc)

cdef class SimpleNodeProxyBase:
    """Policy-less base class, which can be used by extensions.

    For instance if a global node registry is needed instead of a
    document-local one.
    """

cdef class NodeProxyBase(SimpleNodeProxyBase):
    def __dealloc__(self):
        # print "Trying to wipe out:", self, self._c_node.name
        cdef NodeRegistry reg
        reg = self._doc._registry
        reg.attemptDeallocation(self._c_node)
        
cdef class NodeRegistry:
    """A registry of Python-level proxies for libxml2 nodes.

    All libxml2 nodes that have a Python proxy for them are managed here.

    The idea is that there can only be a single Python proxy for each
    libxml2 node. This class tracks these proxies. Whenever a proxy
    has no more references to it, Pyrex will call the __dealloc__ method
    on it.

    This method will then check whether the underlying libxml2 node
    (and its subtree) can be safely garbage collected.
    
    Garbage collection of the underlying C-level structure is only
    safe if:

    * the top of the C-level tree is not connected to anything, such
      as being part of a larger tree.

    * there is no node proxy pointing to any part of the tree.

    The proxies themselves need to be weak-referenceable, as the
    mapping in the registry will have to consist of weak references.
    This way, a node being registered in the registry does not count
    as something that stops the node from being deallocated.
    """
    
    def __init__(self):
        self._proxies = weakref.WeakValueDictionary()
        self._proxy_types = []
        
    def getProxy(self, id, proxy_type):
        """Given an xmlNode, return node proxy, or None if no proxy yet.
        """
        # XXX This cannot be a cdef, as this apparently strips off the
        # weakref functionality from the returned object, possibly
        # by the cast to NodeProxyBase, which is not yet weakreffable
        return self._proxies.get((id, proxy_type), None)
 
    cdef void registerProxy(self, SimpleNodeProxyBase proxy, int proxy_type):
        """Register a proxy with the registry.
        """
        cdef xmlNode* c_node
        c_node = proxy._c_node
        assert not self._proxies.has_key((<int>c_node, proxy_type))
        if proxy_type not in self._proxy_types:
            self._proxy_types.append(proxy_type)
        self._proxies[(<int>c_node, proxy_type)] = proxy

    def unregisterProxy(self, SimpleNodeProxyBase proxy, proxy_type):
        del self._proxies[(<int>proxy._c_node, proxy_type)]
        
    cdef void attemptDeallocation(self, xmlNode* c_node):
        """Attempt deallocation of c_node (or higher up in tree).
        """
        cdef xmlNode* c_top
        # could be we actually aren't referring to the tree at all
        if c_node is NULL:
            return
        c_top = self.getDeallocationTop(c_node)
        if c_top is not NULL:
            # print "freeing:", c_top.name
            tree.xmlFreeNode(c_top)
        
    cdef xmlNode* getDeallocationTop(self, xmlNode* c_node):
        """Return the top of the tree that can be deallocated, or NULL.
        """
        cdef xmlNode* c_current
        cdef xmlNode* c_top
        # print "deallocating:", c_node.type
        c_current = c_node.parent
        c_top = c_node
        while c_current is not NULL:
            # print "checking:", c_current.type
            # if we're still attached to the document, don't deallocate
            if c_current.type == tree.XML_DOCUMENT_NODE:
                # print "still in doc"
                return NULL
            c_top = c_current
            c_current = c_current.parent
        # if the top is not c_node, check whether it has node;
        # if the top is the node we're checking, then we *can*
        # still deallocate safely
        if c_top is not c_node:
            id = <int>c_top
            proxies = self._proxies
            for proxy_type in self._proxy_types:
                if proxies.has_key((id, proxy_type)):
                    return NULL
        # otherwise, see whether we have children to deallocate
        if self.canDeallocateChildren(c_top):
            return c_top
        else:
            return NULL

    cdef int canDeallocateChildNodes(self, xmlNode* c_node):
        cdef xmlNode* c_current
        proxies = self._proxies
        proxy_types = self._proxy_types
        # print "checking childNodes"
        c_current = c_node.children
        while c_current is not NULL:
            id = <int>c_current
            for proxy_type in proxy_types:
                if proxies.has_key((id, proxy_type)):
                    return 0
            if not self.canDeallocateChildren(c_current):
                return 0 
            c_current = c_current.next
        return 1

    cdef int canDeallocateAttributes(self, xmlNode* c_node):
        cdef xmlAttr* c_current
        proxies = self._proxies
        proxy_types = self._proxy_types
        # print "checking attributes"
        c_current = c_node.properties
        while c_current is not NULL:
            id = <int>c_current
            for proxy_type in proxy_types:
                if proxies.has_key((id, proxy_type)):
                    return 0
            # only check child nodes, don't try checking properties as
            # attribute has none
            if not self.canDeallocateChildNodes(<xmlNode*>c_current):
                return 0
            c_current = c_current.next
        # apparently we can deallocate all subnodes
        return 1
    
    cdef int canDeallocateChildren(self, xmlNode* c_node):
        # the current implementation is inefficient as it does a
        # tree traversal to find out whether there are any node proxies
        # we could improve this by a smarter datastructure
        # print "checking children"
        # check children
        if not self.canDeallocateChildNodes(c_node):
            return 0        
        # check any attributes
        if (c_node.type == tree.XML_ELEMENT_NODE and
            not self.canDeallocateAttributes(c_node)):
            return 0
        # apparently we can deallocate all subnodes
        return 1

