from tree cimport xmlDoc
from xpath cimport xmlXPathContext, xmlXPathFunction

cdef extern from "libxslt/xsltInternals.h":
    ctypedef struct xsltStylesheet:
        pass

    ctypedef struct xsltTransformContext:
        xmlXPathContext* xpathCtxt
    
    cdef xsltStylesheet* xsltParseStylesheetDoc(xmlDoc* doc)
    cdef void xsltFreeStylesheet(xsltStylesheet* sheet)
    
#cdef extern from "libxslt/xslt.h":
#    pass

cdef extern from "libxslt/extensions.h":
    cdef int xsltRegisterExtFunction(xsltTransformContext* ctxt,
                                     char* name,
                                     char * URI,
                                     xmlXPathFunction function)

cdef extern from "libxslt/transform.h":
    cdef xmlDoc* xsltApplyStylesheet(xsltStylesheet* style, xmlDoc* doc,
                                     char** params)
    cdef xmlDoc* xsltApplyStylesheetUser(xsltStylesheet* style, xmlDoc* doc,
                                         char** params, char* output,
                                         void* profile,
                                         xsltTransformContext* context)
    cdef xsltTransformContext* xsltNewTransformContext(xsltStylesheet* style,
                                                       xmlDoc* doc)
    cdef void xsltFreeTransformContext(xsltTransformContext* context)

cdef extern from "libxslt/xsltutils.h":
    cdef int xsltSaveResultToString(char** doc_txt_ptr,
                                    int* doc_txt_len,
                                    xmlDoc* result,
                                    xsltStylesheet* style)
    
    cdef void xsltSetGenericErrorFunc(void* ctxt,
                                      void (*handler)(void* ctxt, char* msg, ...))
    cdef void xsltSetTransformErrorFunc(xsltTransformContext*,
                                        void* ctxt,
                                        void (*handler)(void* ctxt, char* msg, ...))
    
