
cdef extern from "libxml/parser.h":
    void xmlInitParser()
    void xmlCleanupParser()

    xmlDocPtr xmlParseFile(char *filename)
    xmlDocPtr xmlParseDoc(xmlChar *cur)
