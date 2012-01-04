from libc.stdio cimport FILE

cdef extern from "stdio.h":
    cdef size_t fread(void *ptr, size_t size, size_t nmemb,
                      FILE *stream) nogil
    cdef int feof(FILE *stream) nogil
    cdef int ferror(FILE *stream) nogil
    cdef int sprintf(char* str, char* format, ...) nogil
    cdef int printf(char* str, ...) nogil

cdef extern from "stdlib.h":
    cdef void* malloc(size_t size) nogil
    cdef void* realloc(void* ptr, size_t size) nogil
    cdef void  free(void* ptr) nogil

cdef extern from "stdarg.h":
    ctypedef void *va_list
    void va_start(va_list ap, void *last) nogil
    void va_end(va_list ap) nogil

cdef extern from "etree_defs.h":
    cdef int va_int(va_list ap) nogil
    cdef char *va_charptr(va_list ap) nogil
