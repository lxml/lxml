cimport tree

cdef extern from "libxml/xpath.h":
    ctypedef enum xmlXPathObjectType:
        XPATH_UNDEFINED = 0
        XPATH_NODESET = 1
        XPATH_BOOLEAN = 2
        XPATH_NUMBER = 3
        XPATH_STRING = 4
        XPATH_POINT = 5
        XPATH_RANGE = 6
        XPATH_LOCATIONSET = 7
        XPATH_USERS = 8
        XPATH_XSLT_TREE = 9

    ctypedef struct xmlNodeSet:
        int nodeNr
        int nodeMax
        tree.xmlNode** nodeTab
        
    ctypedef struct xmlXPathObject:
        xmlXPathObjectType type
        xmlNodeSet* nodesetval
        int boolval
        double floatval
        char* stringval

    ctypedef struct xmlXPathContext:
        tree.xmlDoc* doc
        tree.xmlNode* node
        
    cdef xmlXPathContext* xmlXPathNewContext(tree.xmlDoc* doc)
    cdef xmlXPathObject* xmlXPathEvalExpression(char* str,
                                                xmlXPathContext* ctxt)
    cdef void xmlXPathFreeContext(xmlXPathContext* ctxt)
    cdef void xmlXPathFreeObject(xmlXPathObject* obj)
    cdef int xmlXPathRegisterNs(xmlXPathContext* ctxt,
                                char* prefix, char* ns_uri)
    
