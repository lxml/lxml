
cdef extern from "stdlib.h":
    cdef void* malloc(int size)
    void free(void* ptr)
    
cdef extern from "stdarg.h":
    ctypedef void *va_list
    void va_start(va_list ap, void *last)
    void va_end(va_list ap)

cdef extern from "etree.h":
    cdef int va_int(va_list ap)
    cdef char *va_charptr(va_list ap)
    
