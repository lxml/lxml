cimport tree
cimport xmlerror

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
        char* function
        char* functionURI
        # actually signature is void (*error)(void*, xmlError*)
        void* error
        xmlerror.xmlError lastError
        void* userData

    ctypedef struct xmlXPathParserContext:
        xmlXPathContext* context
        xmlXPathObject* value
        tree.xmlNode* ancestor
        int error

    ctypedef void (*xmlXPathFunction)(xmlXPathParserContext* ctxt, int nargs)
    ctypedef xmlXPathFunction (*xmlXPathFuncLookupFunc)(void* ctxt,
                                                        char* name,
                                                        char* ns_uri)
    
    cdef xmlXPathContext* xmlXPathNewContext(tree.xmlDoc* doc)
    cdef xmlXPathObject* xmlXPathEvalExpression(char* str,
                                                xmlXPathContext* ctxt)
    cdef void xmlXPathFreeContext(xmlXPathContext* ctxt)
    cdef void xmlXPathFreeObject(xmlXPathObject* obj)
    cdef int xmlXPathRegisterNs(xmlXPathContext* ctxt,
                                char* prefix, char* ns_uri)
    
    cdef xmlNodeSet* xmlXPathNodeSetCreate(tree.xmlNode* val)


cdef extern from "libxml/xpathInternals.h":
    cdef int xmlXPathRegisterFunc(xmlXPathContext* ctxt,
                                  char* name,
                                  xmlXPathFunction f)
    cdef int xmlXPathRegisterFuncNS(xmlXPathContext* ctxt,
                                    char* name,
                                    char* ns_uri,
                                    xmlXPathFunction f)
    cdef void xmlXPathRegisterFuncLookup(xmlXPathContext *ctxt,
					 xmlXPathFuncLookupFunc f,
					 void *funcCtxt)
    cdef xmlXPathObject* valuePop (xmlXPathParserContext *ctxt)
    cdef int valuePush(xmlXPathParserContext* ctxt, xmlXPathObject *value)
    
    cdef xmlXPathObject* xmlXPathNewCString(char *val)
    cdef xmlXPathObject* xmlXPathWrapCString(char * val)
    cdef xmlXPathObject* xmlXPathNewString(char *val)
    cdef xmlXPathObject* xmlXPathWrapString(char * val)
    cdef xmlXPathObject* xmlXPathNewFloat(double val)
    cdef xmlXPathObject* xmlXPathNewBoolean(int val)
    cdef xmlXPathObject* xmlXPathNewNodeSet(tree.xmlNode* val)
    cdef xmlXPathObject* xmlXPathNewValueTree(tree.xmlNode* val)
    cdef void xmlXPathNodeSetAdd(xmlNodeSet* cur,
                                  tree.xmlNode* val)
    cdef void xmlXPathNodeSetAddUnique(xmlNodeSet* cur,
                                        tree.xmlNode* val)
    cdef xmlXPathObject* xmlXPathWrapNodeSet(xmlNodeSet* val)
    cdef void xmlXPathErr(xmlXPathParserContext* ctxt, int error)
