from tree cimport xmlDoc, xmlDict
from xmlparser cimport xmlParserCtxt
from xmlerror cimport xmlError

cdef extern from "libxml/HTMLparser.h":
    ctypedef enum htmlParserOption:
        HTML_PARSE_NOERROR    # suppress error reports
        HTML_PARSE_NOWARNING  # suppress warning reports
        HTML_PARSE_PEDANTIC   # pedantic error reporting
        HTML_PARSE_NOBLANKS   # remove blank nodes
        HTML_PARSE_NONET      # Forbid network access
# libxml2 2.6.21+ only:
#        HTML_PARSE_RECOVER    # Relaxed parsing
#        HTML_PARSE_COMPACT    # compact small text nodes

    cdef xmlParserCtxt* htmlCreateMemoryParserCtxt(char* buffer, int size)
    cdef xmlParserCtxt* htmlCreateFileParserCtxt(char* filename, char* encoding)
    cdef void htmlFreeParserCtxt(xmlParserCtxt* ctxt)
    cdef int htmlParseDocument(xmlParserCtxt* ctxt)

    cdef xmlDoc* htmlCtxtReadFile(xmlParserCtxt* ctxt,
                                  char* filename, char* encoding,
                                  int options)
    cdef xmlDoc* htmlCtxtReadDoc(xmlParserCtxt* ctxt,
                                 char* buffer, char* URL, char* encoding,
                                 int options)
