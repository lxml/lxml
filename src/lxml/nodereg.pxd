from tree cimport xmlNode, xmlDoc
cimport tree

cdef class NodeRegistry
cdef class NodeProxyBase

cdef class DocumentProxyBase:
    cdef xmlDoc* _c_doc
    cdef NodeRegistry _registry

    cdef object getProxy(self, xmlNode* c_node)

cdef class NodeProxyBase:
    cdef DocumentProxyBase _doc
    cdef xmlNode* _c_node
            
cdef class NodeRegistry:
    cdef object _proxies

    cdef NodeProxyBase getProxy(self, xmlNode* c_node)
    cdef void registerProxy(self, NodeProxyBase proxy)
    cdef attemptDeallocation(self, xmlNode* c_node)
    cdef xmlNode* getDeallocationTop(self, xmlNode* c_node)
    cdef int canDeallocateChildren(self, xmlNode* c_node)
