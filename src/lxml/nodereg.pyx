from tree cimport xmlNode, xmlDoc
#cimport tree

import weakref

#cdef class NodeRegistry
#cdef class NodeProxyBase

cdef class DocumentProxyBase:
    def __init__(self):
        self._registry = NodeRegistry()
        
    def getProxy(self, xmlNode* c_node):
        return self._registry.getProxy(c_node)

    def registerProxy(self, NodeProxyBase proxy):
        self._registry.registerProxy(proxy)
        
    def __dealloc__(self):
        # if there are no more references to the document, it is safe
        # to clean the whole thing up, as all nodes have a reference to
        # the document
        tree.xmlFreeDoc(self._c_doc)
        
cdef class NodeProxyBase:           
    def __dealloc__(self):
        self._doc._registry.attemptDeallocation(self._c_node)

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
        
    cdef NodeProxyBase getProxy(self, xmlNode* c_node):
        """Given an xmlNode, return node proxy, or None if no proxy yet.
        """
        return self._proxies.get(<int>c_node, None)
 
    cdef void registerProxy(self, NodeProxyBase proxy):
        """Register a proxy with the registry.
        """
        cdef xmlNode* c_node
        c_node = proxy._c_node
        assert not self._proxies.has_key[<int>c_node]
        self._proxies[<int>c_node] = proxy

    cdef attemptDeallocation(self, xmlNode* c_node):
        """Attempt deallocation of c_node (or higher up in tree).
        """
        cdef xmlNode* c_top
        c_top = self.getDeallocationTop(c_node)
        if c_top is not NULL:
            tree.xmlFreeNode(c_top)
        
    cdef xmlNode* getDeallocationTop(self, xmlNode* c_node):
        """Return the top of the tree that can be deallocated, or NULL.
        """
        cdef xmlNode* c_current
        c_current = c_node.parent
        while c_current is not NULL:
            c_current = c_current.parent
        # if we're still attached to the document, don't deallocate
        if c_current.type == tree.XML_DOCUMENT_NODE:
            return NULL
        # otherwise, see whether we have children to deallocate
        if self.canDeallocateChildren(c_current):
            return c_current
        else:
            return NULL
        
    cdef int canDeallocateChildren(self, xmlNode* c_node):
        # the current implementation is inefficient as it does a
        # tree traversal to find out whether there are any node proxies
        # we could improve this by a smarter datastructure
        # XXX should handle attribute nodes and other things we don't reach
        cdef xmlNode* c_current
        c_current = c_node.children
        proxies = self._proxies
        while c_current is not NULL:
            id = <int>c_node
            if proxies.has_key(id):
                return 0
            if not self.canDeallocateChildren(c_current):
                return 0 
            c_current = c_current.next
        # apparently we can deallocate all subnodes
        return 1

