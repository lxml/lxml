from tree cimport xmlDoc

cdef extern from "libxml/parser.h":
    cdef xmlDoc* xmlParseFile(char* filename)
    cdef xmlDoc* xmlParseDoc(char* cur)
