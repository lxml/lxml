from tree cimport xmlDoc

cdef extern from "libxml/xinclude.h":
    
    cdef int xmlXIncludeProcess(xmlDoc* doc)
    
