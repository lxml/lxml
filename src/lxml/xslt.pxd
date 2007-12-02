from tree cimport xmlDoc, xmlDict
from xpath cimport xmlXPathContext, xmlXPathFunction

cdef extern from "libxslt/xslt.h":
    cdef int xsltLibxsltVersion

cdef extern from "libxslt/xsltconfig.h":
    cdef int LIBXSLT_VERSION

cdef extern from "libxslt/xsltInternals.h":
    ctypedef struct xsltDocument:
        xmlDoc* doc

    ctypedef struct xsltStylesheet:
        char* encoding
        xmlDoc* doc

    ctypedef struct xsltTransformContext:
        xsltStylesheet* style
        xmlXPathContext* xpathCtxt
        xsltDocument* document
        void* _private
        xmlDict* dict
        int profile

    cdef xsltStylesheet* xsltParseStylesheetDoc(xmlDoc* doc) nogil
    cdef void xsltFreeStylesheet(xsltStylesheet* sheet) nogil

cdef extern from "libxslt/extensions.h":
    cdef int xsltRegisterExtFunction(xsltTransformContext* ctxt,
                                     char* name,
                                     char* URI,
                                     xmlXPathFunction function) nogil
    cdef int xsltRegisterExtModuleFunction(char* name, char* URI,
                                           xmlXPathFunction function) nogil
    cdef int xsltUnregisterExtModuleFunction(char* name, char* URI)
    cdef xmlXPathFunction xsltExtModuleFunctionLookup(
        char* name, char* URI) nogil
    cdef int xsltRegisterExtPrefix(xsltStylesheet* style, 
                                   char* prefix, char* URI) nogil

cdef extern from "libxslt/documents.h":
    ctypedef enum xsltLoadType:
        XSLT_LOAD_START
        XSLT_LOAD_STYLESHEET
        XSLT_LOAD_DOCUMENT

    ctypedef xmlDoc* (*xsltDocLoaderFunc)(char* URI, xmlDict* dict,
                                          int options,
                                          void* ctxt,
                                          xsltLoadType type)
    cdef xsltDocLoaderFunc xsltDocDefaultLoader
    cdef void xsltSetLoaderFunc(xsltDocLoaderFunc f) nogil

cdef extern from "libxslt/transform.h":
    cdef xmlDoc* xsltApplyStylesheet(xsltStylesheet* style, xmlDoc* doc,
                                     char** params) nogil
    cdef xmlDoc* xsltApplyStylesheetUser(xsltStylesheet* style, xmlDoc* doc,
                                         char** params, char* output,
                                         void* profile,
                                         xsltTransformContext* context) nogil
    cdef xsltTransformContext* xsltNewTransformContext(xsltStylesheet* style,
                                                       xmlDoc* doc) nogil
    cdef void xsltFreeTransformContext(xsltTransformContext* context) nogil

cdef extern from "libxslt/xsltutils.h":
    cdef int xsltSaveResultToString(char** doc_txt_ptr,
                                    int* doc_txt_len,
                                    xmlDoc* result,
                                    xsltStylesheet* style) nogil
    
    cdef void xsltSetGenericErrorFunc(
        void* ctxt, void (*handler)(void* ctxt, char* msg, ...)) nogil
    cdef void xsltSetTransformErrorFunc(
        xsltTransformContext*, void* ctxt,
        void (*handler)(void* ctxt, char* msg, ...)) nogil

cdef extern from "libxslt/security.h":
    ctypedef struct xsltSecurityPrefs
    ctypedef enum xsltSecurityOption:
        XSLT_SECPREF_READ_FILE = 1
        XSLT_SECPREF_WRITE_FILE = 2
        XSLT_SECPREF_CREATE_DIRECTORY = 3
        XSLT_SECPREF_READ_NETWORK = 4
        XSLT_SECPREF_WRITE_NETWORK = 5

    ctypedef int (*xsltSecurityCheck)(xsltSecurityPrefs* sec,
                                      xsltTransformContext* ctxt,
                                      char* value)

    cdef xsltSecurityPrefs* xsltNewSecurityPrefs() nogil
    cdef void xsltFreeSecurityPrefs(xsltSecurityPrefs* sec) nogil
    cdef int xsltSecurityForbid(xsltSecurityPrefs* sec,
                                xsltTransformContext* ctxt,
                                char* value) nogil
    cdef int xsltSecurityAllow(xsltSecurityPrefs* sec,
                                xsltTransformContext* ctxt,
                                char* value) nogil
    cdef int xsltSetSecurityPrefs(xsltSecurityPrefs* sec,
                                  xsltSecurityOption option,
                                  xsltSecurityCheck func) nogil
    cdef int xsltSetCtxtSecurityPrefs(xsltSecurityPrefs* sec,
                                      xsltTransformContext* ctxt) nogil
    cdef xmlDoc* xsltGetProfileInformation(xsltTransformContext* ctxt) nogil

cdef extern from "libxslt/extra.h":
    cdef char* XSLT_LIBXSLT_NAMESPACE
    cdef char* XSLT_XALAN_NAMESPACE
    cdef char* XSLT_SAXON_NAMESPACE
    cdef char* XSLT_XT_NAMESPACE

    cdef xmlXPathFunction xsltFunctionNodeSet
    cdef void xsltRegisterAllExtras() nogil

cdef extern from "libexslt/exslt.h":
    cdef void exsltRegisterAll() nogil
