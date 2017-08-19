cdef class ElementMaker:
    cdef readonly dict _nsmap
    cdef readonly dict _typemap
    cdef readonly object _namespace
    cdef readonly object _makeelement
