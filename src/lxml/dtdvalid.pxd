cimport tree
from tree cimport xmlDoc, xmlDtd

cdef extern from "libxml/valid.h":
    ctypedef struct xmlValidCtxt

    cdef xmlValidCtxt* xmlNewValidCtxt()
    cdef void xmlFreeValidCtxt(xmlValidCtxt* cur)

    cdef int xmlValidateDtd(xmlValidCtxt* ctxt, xmlDoc* doc, xmlDtd* dtd)
