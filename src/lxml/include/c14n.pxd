from tree cimport xmlDoc, xmlOutputBuffer
from xpath cimport xmlNodeSet
    
cdef extern from "libxml/c14n.h":
    cdef int xmlC14NDocDumpMemory(xmlDoc* doc,
                                  xmlNodeSet* nodes,
                                  int exclusive,
                                  char** inclusive_ns_prefixes,
                                  int with_comments,
                                  char** doc_txt_ptr) nogil

    cdef int xmlC14NDocSave(xmlDoc* doc,
                            xmlNodeSet* nodes,
                            int exclusive,
                            char** inclusive_ns_prefixes,
                            int with_comments,
                            char* filename,
                            int compression) nogil

    cdef int xmlC14NDocSaveTo(xmlDoc* doc,
                              xmlNodeSet* nodes,
                              int exclusive,
                              char** inclusive_ns_prefixes,
                              int with_comments,
                              xmlOutputBuffer* buffer) nogil

