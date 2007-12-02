cimport tree
from tree cimport xmlDoc, xmlDtd

cdef extern from "libxml/valid.h":
    ctypedef struct xmlValidCtxt

    cdef xmlValidCtxt* xmlNewValidCtxt() nogil
    cdef void xmlFreeValidCtxt(xmlValidCtxt* cur) nogil

    cdef int xmlValidateDtd(xmlValidCtxt* ctxt, xmlDoc* doc, xmlDtd* dtd) nogil
