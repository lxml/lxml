
cdef extern from "stdlib.h":
    cdef void* malloc(int size)
    void free(void* ptr)
    
