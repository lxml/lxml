from libc.string cimport const_char

cdef extern from "libxml/tree.h":
    ctypedef struct xmlDoc

cdef extern from "gumbo_libxml.h":
    cdef xmlDoc *gumbo_libxml_parse(const_char *buffer) nogil
