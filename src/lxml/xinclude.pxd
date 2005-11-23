from tree cimport xmlDoc, xmlNode

cdef extern from "libxml/xinclude.h":
    
    cdef int xmlXIncludeProcess(xmlDoc* doc)
    cdef int xmlXIncludeProcessTree(xmlNode* doc)
    
