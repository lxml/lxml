from tree cimport xmlDoc, xmlDict
from tree cimport xmlInputReadCallback, xmlInputCloseCallback
from xmlparser cimport xmlParserCtxt, xmlSAXHandler
from xmlerror cimport xmlError

cdef extern from "libxml/HTMLparser.h":
    ctypedef enum htmlParserOption:
        HTML_PARSE_NOERROR    # suppress error reports
        HTML_PARSE_NOWARNING  # suppress warning reports
        HTML_PARSE_PEDANTIC   # pedantic error reporting
        HTML_PARSE_NOBLANKS   # remove blank nodes
        HTML_PARSE_NONET      # Forbid network access
        # libxml2 2.6.21+ only:
        HTML_PARSE_RECOVER    # Relaxed parsing
        HTML_PARSE_COMPACT    # compact small text nodes

    cdef xmlParserCtxt* htmlCreateMemoryParserCtxt(
        char* buffer, int size) nogil
    cdef xmlParserCtxt* htmlCreateFileParserCtxt(
        char* filename, char* encoding) nogil
    cdef xmlParserCtxt* htmlCreatePushParserCtxt(xmlSAXHandler* sax,
                                                 void* user_data,
                                                 char* chunk, int size,
                                                 char* filename, int enc) nogil
    cdef void htmlFreeParserCtxt(xmlParserCtxt* ctxt) nogil
    cdef void htmlCtxtReset(xmlParserCtxt* ctxt) nogil
    cdef int htmlCtxtUseOptions(xmlParserCtxt* ctxt, int options) nogil
    cdef int htmlParseDocument(xmlParserCtxt* ctxt) nogil
    cdef int htmlParseChunk(xmlParserCtxt* ctxt, 
                            char* chunk, int size, int terminate) nogil

    cdef xmlDoc* htmlCtxtReadFile(xmlParserCtxt* ctxt,
                                  char* filename, char* encoding,
                                  int options) nogil
    cdef xmlDoc* htmlCtxtReadDoc(xmlParserCtxt* ctxt,
                                 char* buffer, char* URL, char* encoding,
                                 int options) nogil
    cdef xmlDoc* htmlCtxtReadIO(xmlParserCtxt* ctxt, 
                                xmlInputReadCallback ioread, 
                                xmlInputCloseCallback ioclose, 
                                void* ioctx,
                                char* URL, char* encoding,
                                int options) nogil
    cdef xmlDoc* htmlCtxtReadMemory(xmlParserCtxt* ctxt,
                                    char* buffer, int size,
                                    char* filename, char* encoding,
                                    int options) nogil
