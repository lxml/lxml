from tree cimport xmlDoc, xmlNode

cdef extern from "libxml/xinclude.h":
    
    cdef int xmlXIncludeProcess(xmlDoc* doc)
    cdef int xmlXIncludeProcessFlags(xmlDoc* doc, int parser_opts)
    cdef int xmlXIncludeProcessTree(xmlNode* doc)
    cdef int xmlXIncludeProcessTreeFlags(xmlNode* doc, int parser_opts)
    
