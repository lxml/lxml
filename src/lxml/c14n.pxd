from tree cimport xmlDoc

cdef extern from "libxml/xpath.h":
    ctypedef struct xmlNodeSet
    
cdef extern from "libxml/c14n.h":
    cdef int xmlC14NDocDumpMemory(xmlDoc* doc,
                                  xmlNodeSet* nodes,
                                  int exclusive,
                                  char** inclusive_ns_prefixes,
                                  int with_comments,
                                  char** doc_txt_ptr)
    
