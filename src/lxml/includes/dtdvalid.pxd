from lxml.includes cimport tree
from lxml.includes.tree cimport xmlDoc, xmlDtd

cdef extern from "libxml/valid.h" nogil:
    ctypedef struct xmlValidCtxt

    cdef xmlValidCtxt* xmlNewValidCtxt()
    cdef void xmlFreeValidCtxt(xmlValidCtxt* cur)

    cdef int xmlValidateDtd(xmlValidCtxt* ctxt, xmlDoc* doc, xmlDtd* dtd)
    cdef tree.xmlElement* xmlGetDtdElementDesc(
        xmlDtd* dtd, tree.const_xmlChar* name)
