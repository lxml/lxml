################################################################################
# DEBUG setup

# list to collect error output messages from libxml2/libxslt
cdef object __ERROR_LOG
__ERROR_LOG = []

def __build_error_log_tuple(_):
    return python.PyList_AsTuple(__ERROR_LOG)

def clear_error_log():
    del __ERROR_LOG[:]

cdef void _logLines(char* s):
    cdef char* pos
    cdef int l
    while s is not NULL and s[0] != c'\0':
        pos = tree.xmlStrchr(s, c'\n')
        if pos is NULL:
            py_string = python.PyString_FromString(s)
            s = NULL
        else:
            l = pos - s
            py_string = python.PyString_FromStringAndSize(s, l)
            s = pos + 1
        python.PyList_Append(__ERROR_LOG, py_string)

    l = python.PyList_GET_SIZE(__ERROR_LOG) - __MAX_LOG_SIZE
    if l > 0:
        del __ERROR_LOG[:l]

cdef void logStructuredErrorFunc(void* userData,
                                  xmlerror.xmlError* error):
    _logLines(error.message)

cdef void logGenericErrorFunc(void* ctxt, char* msg, ...):
    _logLines(msg)

cdef void _logLibxmlErrors():
    xmlerror.xmlSetGenericErrorFunc(NULL, nullGenericErrorFunc)
    xmlerror.xmlSetStructuredErrorFunc(NULL, logStructuredErrorFunc)

cdef void _logLibxsltErrors():
    xslt.xsltSetGenericErrorFunc(NULL, logGenericErrorFunc)
    # xslt.xsltSetTransformErrorFunc

# ugly global shutting up of all errors, but seems to work..
cdef void nullGenericErrorFunc(void* ctxt, char* msg, ...):
    pass

cdef void nullStructuredErrorFunc(void* userData,
                                  xmlerror.xmlError* error):
    pass

cdef void _shutUpLibxmlErrors():
    xmlerror.xmlSetGenericErrorFunc(NULL, nullGenericErrorFunc)
    xmlerror.xmlSetStructuredErrorFunc(NULL, nullStructuredErrorFunc)

cdef void _shutUpLibxsltErrors():
    xslt.xsltSetGenericErrorFunc(NULL, nullGenericErrorFunc)
    # xslt.xsltSetTransformErrorFunc
