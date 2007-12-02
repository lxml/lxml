
cdef extern from "stdio.h":
    ctypedef struct FILE
    cdef int sprintf(char* str, char* format, ...)
    cdef int printf(char* str)

cdef extern from "string.h":
    ctypedef int size_t
    cdef int strlen(char* s)
    cdef char* strstr(char* haystack, char* needle)
    cdef char* strchr(char* haystack, int needle)
    cdef char* strrchr(char* haystack, int needle)
    cdef int strcmp(char* s1, char* s2)
    cdef int strncmp(char* s1, char* s2, size_t len)
    cdef void* memcpy(void* dest, void* src, size_t len)
    cdef void* memset(void* s, int c, size_t len)

cdef extern from "stdlib.h":
    cdef void* malloc(size_t size)
    cdef void  free(void* ptr)

cdef extern from "stdarg.h":
    ctypedef void *va_list
    void va_start(va_list ap, void *last)
    void va_end(va_list ap)

cdef extern from "etree_defs.h":
    cdef int va_int(va_list ap)
    cdef char *va_charptr(va_list ap)
