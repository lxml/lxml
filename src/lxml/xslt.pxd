from tree cimport xmlDoc

cdef extern from "libxslt/xsltInternals.h":
    ctypedef struct xsltStylesheet:
        pass

    cdef xsltStylesheet* xsltParseStylesheetDoc(xmlDoc* doc)
    cdef void xsltFreeStylesheet(xsltStylesheet* sheet)
    
#cdef extern from "libxslt/xslt.h":
#    pass

cdef extern from "libxslt/transform.h":
    cdef xmlDoc* xsltApplyStylesheet(xsltStylesheet* style, xmlDoc* doc,
                                     char** params)

cdef extern from "libxslt/xsltutils.h":
    cdef int xsltSaveResultToString(char** doc_txt_ptr,
                                    int* doc_txt_len,
                                    xmlDoc* result,
                                    xsltStylesheet* style)
    
