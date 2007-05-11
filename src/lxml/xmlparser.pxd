from tree cimport xmlDoc, xmlNode, xmlDict, xmlDtd
from tree cimport xmlInputReadCallback, xmlInputCloseCallback
from xmlerror cimport xmlError


cdef extern from "libxml/parser.h":
    ctypedef void (*startElementNsSAX2Func)(void* ctx,
                                            char* localname,
                                            char* prefix,
                                            char* URI,
                                            int nb_namespaces,
                                            char** namespaces,
                                            int nb_attributes,
                                            int nb_defaulted,
                                            char** attributes)

    ctypedef void (*endElementNsSAX2Func)(void* ctx,
                                          char* localname,
                                          char* prefix,
                                          char* URI)

    ctypedef void (*cdataBlockSAXFunc)(void* ctx,
                                       char* value,
                                       int len)

cdef extern from "libxml/tree.h":
    ctypedef struct xmlParserInput
    ctypedef struct xmlParserInputBuffer:
        void* context
        xmlInputReadCallback  readcallback
        xmlInputCloseCallback closecallback

    ctypedef struct xmlSAXHandler:
        startElementNsSAX2Func startElementNs
        endElementNsSAX2Func   endElementNs
        cdataBlockSAXFunc      cdataBlock

cdef extern from "libxml/xmlIO.h":
    cdef xmlParserInputBuffer* xmlAllocParserInputBuffer(int enc)

cdef extern from "libxml/parser.h":

    cdef xmlDict* xmlDictCreate()
    cdef xmlDict* xmlDictCreateSub(xmlDict* subdict)
    cdef void xmlDictFree(xmlDict* sub)
    cdef int xmlDictReference(xmlDict* dict)
    
    ctypedef struct xmlParserCtxt:
        xmlDoc* myDoc
        xmlDict* dict
        void* _private
        int wellFormed
        int recovery
        int options
        int disableSAX
        int errNo
        xmlError lastError
        xmlNode* node
        xmlSAXHandler* sax
        int* spaceTab
        
    ctypedef enum xmlParserOption:
        XML_PARSE_RECOVER = 1 # recover on errors
        XML_PARSE_NOENT = 2 # substitute entities
        XML_PARSE_DTDLOAD = 4 # load the external subset
        XML_PARSE_DTDATTR = 8 # default DTD attributes
        XML_PARSE_DTDVALID = 16 # validate with the DTD
        XML_PARSE_NOERROR = 32 # suppress error reports
        XML_PARSE_NOWARNING = 64 # suppress warning reports
        XML_PARSE_PEDANTIC = 128 # pedantic error reporting
        XML_PARSE_NOBLANKS = 256 # remove blank nodes
        XML_PARSE_SAX1 = 512 # use the SAX1 interface internally
        XML_PARSE_XINCLUDE = 1024 # Implement XInclude substitition
        XML_PARSE_NONET = 2048 # Forbid network access
        XML_PARSE_NODICT = 4096 # Do not reuse the context dictionnary
        XML_PARSE_NSCLEAN = 8192 # remove redundant namespaces declarations
        XML_PARSE_NOCDATA = 16384 # merge CDATA as text nodes
        XML_PARSE_NOXINCNODE = 32768 # do not generate XINCLUDE START/END nodes
        # libxml2 2.6.21+ only:
        XML_PARSE_COMPACT = 65536 # compact small text nodes

    cdef void xmlInitParser()
    cdef int xmlLineNumbersDefault(int onoff)
    cdef xmlParserCtxt* xmlNewParserCtxt()
    cdef xmlParserInput* xmlNewIOInputStream(xmlParserCtxt* ctxt,
                                             xmlParserInputBuffer* input,
                                             int enc)
    cdef int xmlCtxtUseOptions(xmlParserCtxt* ctxt, int options)
    cdef void xmlFreeParserCtxt(xmlParserCtxt* ctxt)
    cdef void xmlCtxtReset(xmlParserCtxt* ctxt)
    cdef void xmlClearParserCtxt(xmlParserCtxt* ctxt)
    cdef int xmlParseChunk(xmlParserCtxt* ctxt,
                           char* chunk, int size, int terminate)
    cdef xmlDoc* xmlCtxtReadDoc(xmlParserCtxt* ctxt,
                                char* cur, char* URL, char* encoding,
                                int options)
    cdef xmlDoc* xmlCtxtReadFile(xmlParserCtxt* ctxt,
                                 char* filename, char* encoding, int options)
    cdef xmlDoc* xmlCtxtReadIO(xmlParserCtxt* ctxt, 
                               xmlInputReadCallback ioread, 
                               xmlInputCloseCallback ioclose, 
                               void* ioctx,
                               char* URL, char* encoding, int options)
    cdef xmlDoc* xmlCtxtReadMemory(xmlParserCtxt* ctxt,
                                   char* buffer, int size,
                                   char* filename, char* encoding, int options)

# iterparse:

    cdef xmlParserCtxt* xmlCreatePushParserCtxt(xmlSAXHandler* sax,
                                                void* user_data,
                                                char* chunk,
                                                int size,
                                                char* filename)

    cdef int xmlCtxtResetPush(xmlParserCtxt* ctxt,
                              char* chunk,
                              int size,
                              char* filename,
                              char* encoding)

# entity loaders:

    ctypedef xmlParserInput* (*xmlExternalEntityLoader)(char * URL,
                                                        char * ID, 
                                                        xmlParserCtxt* context)
    cdef xmlExternalEntityLoader xmlGetExternalEntityLoader()
    cdef void xmlSetExternalEntityLoader(xmlExternalEntityLoader f)

# DTDs:

    cdef xmlDtd* xmlParseDTD(char* ExternalID, char* SystemID)
    cdef xmlDtd* xmlIOParseDTD(xmlSAXHandler* sax,
                               xmlParserInputBuffer* input,
                               int enc)

cdef extern from "libxml/parserInternals.h":
    cdef xmlParserInput* xmlNewStringInputStream(xmlParserCtxt* ctxt, 
                                                 char* buffer)
    cdef xmlParserInput* xmlNewInputFromFile(xmlParserCtxt* ctxt, 
                                             char* filename)
    cdef void xmlFreeInputStream(xmlParserInput* input)
