'''
We keep all of the xmlmemory.h declarations in here
'''


cdef extern from "libxml/xmlmemory.h":
    ctypedef void (*xmlFreeFunc)(void *mem)
    ctypedef void *(*xmlMallocFunc)(size_t size)
    ctypedef void *(*xmlReallocFunc)(void *mem, size_t size)
    ctypedef char *(*xmlStrdupFunc)(char *str)
    int xmlMemSetup (xmlFreeFunc freeFunc,
                     xmlMallocFunc mallocFunc,
                     xmlReallocFunc reallocFunc,
                     xmlStrdupFunc strdupFunc)
    int xmlMemGet ( xmlFreeFunc *freeFunc,
                    xmlMallocFunc *mallocFunc,
                    xmlReallocFunc *reallocFunc,
                    xmlStrdupFunc *strdupFunc)
    int xmlMemUsed()
    void * xmlMemMalloc(size_t size)
    void * xmlMemRealloc(void *ptr,size_t size)
    void xmlMemFree (void *ptr)
    void xmlFree(void *ptr)
    char *xmlMemoryStrdup (char *str)




