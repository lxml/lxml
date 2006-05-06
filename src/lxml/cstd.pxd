
cdef extern from "stdio.h":
    ctypedef struct FILE
    cdef int strlen(char* s)
    cdef char* strstr(char* haystack, char* needle)
    cdef int strcmp(char* s1, char* s2)
    cdef int strncmp(char* s1, char* s2, int len)

cdef extern from "stdarg.h":
    ctypedef void *va_list
    void va_start(va_list ap, void *last)
    void va_end(va_list ap)

cdef extern from "etree.h":
    cdef int va_int(va_list ap)
    cdef char *va_charptr(va_list ap)
