from tree cimport xmlNode, xmlDoc
cimport tree

cdef class ProxyBase
cdef class NodeRegistry
cdef class NodeProxyBase(ProxyBase)

cdef class DocumentProxyBase:
    cdef xmlDoc* _c_doc
    cdef NodeRegistry _registry

    #cdef object getProxy(self, xmlNode* c_node)

cdef class ProxyBase:
    cdef DocumentProxyBase _doc
    cdef xmlNode* _c_node

cdef class NodeProxyBase(ProxyBase):
    pass

cdef class NodeRegistry:
    cdef object _proxies
    cdef object _proxy_types
    
    #cdef NodeProxyBase getProxy(self, xmlNode* c_node)
    cdef void registerProxy(self, ProxyBase proxy, int proxy_type)
    cdef attemptDeallocation(self, xmlNode* c_node)
    cdef xmlNode* getDeallocationTop(self, xmlNode* c_node)
    cdef int canDeallocateChildNodes(self, xmlNode* c_node)
    cdef int canDeallocateAttributes(self, xmlNode* c_node)
    cdef int canDeallocateChildren(self, xmlNode* c_node)
