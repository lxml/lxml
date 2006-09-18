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

    cdef xsltStylesheet* xsltParseStylesheetDoc(xmlDoc* doc)
    cdef void xsltFreeStylesheet(xsltStylesheet* sheet)

cdef extern from "libxslt/extensions.h":
    cdef int xsltRegisterExtFunction(xsltTransformContext* ctxt,
                                     char* name,
                                     char* URI,
                                     xmlXPathFunction function)
    cdef int xsltRegisterExtModuleFunction(char* name, char* URI,
                                           xmlXPathFunction function)
    cdef int xsltUnregisterExtModuleFunction(char* name, char* URI)
    cdef xmlXPathFunction xsltExtModuleFunctionLookup(char* name, char* URI)

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
    cdef void xsltSetLoaderFunc(xsltDocLoaderFunc f)

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

    cdef xsltSecurityPrefs* xsltNewSecurityPrefs()
    cdef void xsltFreeSecurityPrefs(xsltSecurityPrefs* sec)
    cdef int xsltSecurityForbid(xsltSecurityPrefs* sec,
                                xsltTransformContext* ctxt,
                                char* value)
    cdef int xsltSecurityAllow(xsltSecurityPrefs* sec,
                                xsltTransformContext* ctxt,
                                char* value)
    cdef int xsltSetSecurityPrefs(xsltSecurityPrefs* sec,
                                  xsltSecurityOption option,
                                  xsltSecurityCheck func)
    cdef int xsltSetCtxtSecurityPrefs(xsltSecurityPrefs* sec,
                                      xsltTransformContext* ctxt)
    cdef xmlDoc* xsltGetProfileInformation(xsltTransformContext* ctxt)

cdef extern from "libxslt/extra.h":
    cdef char* XSLT_LIBXSLT_NAMESPACE
    cdef char* XSLT_XALAN_NAMESPACE
    cdef char* XSLT_SAXON_NAMESPACE
    cdef char* XSLT_XT_NAMESPACE

    cdef xmlXPathFunction xsltFunctionNodeSet
    cdef void xsltRegisterAllExtras()

cdef extern from "libexslt/exslt.h":
    cdef void exsltRegisterAll()
