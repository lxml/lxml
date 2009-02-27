
cdef extern from "string.h":
    cdef int strlen(char* s) nogil
    cdef char* strstr(char* haystack, char* needle) nogil
    cdef char* strchr(char* haystack, int needle) nogil
    cdef char* strrchr(char* haystack, int needle) nogil
    cdef int strcmp(char* s1, char* s2) nogil
    cdef int strncmp(char* s1, char* s2, size_t len) nogil
    cdef void* memcpy(void* dest, void* src, size_t len) nogil
    cdef void* memset(void* s, int c, size_t len) nogil

cdef extern from "stdio.h":
    ctypedef struct FILE
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
