from tree cimport xmlNode, xmlDoc
cimport tree

cdef class SimpleNodeProxyBase
cdef class NodeProxyBase(SimpleNodeProxyBase)
cdef class NodeRegistry

cdef class SimpleDocumentProxyBase:
    cdef xmlDoc* _c_doc
    # XXX ugh, this has to be here to make the type checker pleased,
    # though will only be *used* by DocumentProxyBase subclasses, not
    # by SimpleDocumentProxyBase subclasses
    cdef NodeRegistry _registry
    
cdef class DocumentProxyBase(SimpleDocumentProxyBase):
    # cdef NodeRegistry _registry
    pass

    #cdef object getProxy(self, xmlNode* c_node)

cdef class SimpleNodeProxyBase:
    cdef SimpleDocumentProxyBase _doc
    cdef xmlNode* _c_node

cdef class NodeProxyBase(SimpleNodeProxyBase):
    pass

cdef class NodeRegistry:
    cdef object _proxies
    cdef object _proxy_types
    
    #cdef NodeProxyBase getProxy(self, xmlNode* c_node)
    cdef void registerProxy(self, SimpleNodeProxyBase proxy, int proxy_type)
    cdef void attemptDeallocation(self, xmlNode* c_node)
    cdef xmlNode* getDeallocationTop(self, xmlNode* c_node)
    cdef int canDeallocateChildNodes(self, xmlNode* c_node)
    cdef int canDeallocateAttributes(self, xmlNode* c_node)
    cdef int canDeallocateChildren(self, xmlNode* c_node)
