
cdef extern from "libxml/xpath.h":
    cdef enum xmlXPathObjectType:
        XPATH_UNDEFINED
        XPATH_NODESET
        XPATH_BOOLEAN
        XPATH_NUMBER
        XPATH_STRING
        XPATH_POINT
        XPATH_RANGE
        XPATH_LOCATIONSET
        XPATH_USERS
        XPATH_XSLT_TREE

    cdef struct xmlXPathContext:
        xmlDocPtr doc       # The current document 
        xmlNodePtr node     # The current node 
    ctypedef xmlXPathContext *xmlXPathContextPtr

    cdef struct xmlNodeSet:
        int nodeNr                  # number of nodes in the set 
        int nodeMax                 # size of the array as allocated 
        xmlNodePtr *nodeTab         #  array of nodes in no particular order 

    ctypedef xmlNodeSet *xmlNodeSetPtr

    cdef struct _xmlXPathObject:
        xmlXPathObjectType type
        xmlNodeSetPtr nodesetval
        int boolval
        double floatval
        xmlChar *stringval
        void *user
        int index
        void *user2
        int index2
    ctypedef _xmlXPathObject xmlXPathObject
    ctypedef xmlXPathObject *xmlXPathObjectPtr

    xmlBufferPtr xmlBufferCreate()
    void xmlBufferFree(xmlBufferPtr buf)
    xmlXPathContextPtr xmlXPathNewContext (xmlDocPtr doc)
    void xmlXPathFreeContext(xmlXPathContextPtr ctxt)
    xmlXPathObjectPtr  xmlXPathEvalExpression(xmlChar *expr, xmlXPathContextPtr ctxt)
    void xmlXPathFreeObject(xmlXPathObjectPtr obj)


