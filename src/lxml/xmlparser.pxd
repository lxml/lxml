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

    ctypedef void (*startElementSAXFunc)(void* ctx, char* name, char** atts)

    ctypedef void (*endElementSAXFunc)(void* ctx, char* name)

    ctypedef void (*charactersSAXFunc)(void* ctx, char* ch, int len)

    ctypedef void (*cdataBlockSAXFunc)(void* ctx, char* value, int len)

    ctypedef void (*commentSAXFunc)(void* ctx, char* value)

    ctypedef void (*processingInstructionSAXFunc)(void* ctx, 
                                                  char* target, 
                                                  char* data)

    ctypedef void (*internalSubsetSAXFunc)(void* ctx, 
                                            char* name, 
                                            char* externalID, 
                                            char* systemID)

    ctypedef void (*endDocumentSAXFunc)(void* ctx)

    ctypedef void (*referenceSAXFunc)(void * ctx, char* name)

    cdef int XML_SAX2_MAGIC

cdef extern from "libxml/tree.h":
    ctypedef struct xmlParserInput:
        int line
        int length
        char* base
        char* cur
        char* end

    ctypedef struct xmlParserInputBuffer:
        void* context
        xmlInputReadCallback  readcallback
        xmlInputCloseCallback closecallback

    ctypedef struct xmlSAXHandler:
        internalSubsetSAXFunc           internalSubset
        startElementNsSAX2Func          startElementNs
        endElementNsSAX2Func            endElementNs
        startElementSAXFunc             startElement
        endElementSAXFunc               endElement
        charactersSAXFunc               characters
        cdataBlockSAXFunc               cdataBlock
        referenceSAXFunc                reference
        commentSAXFunc                  comment
        processingInstructionSAXFunc	processingInstruction
        endDocumentSAXFunc              endDocument
        int                             initialized

cdef extern from "libxml/xmlIO.h":
    cdef xmlParserInputBuffer* xmlAllocParserInputBuffer(int enc) nogil

cdef extern from "libxml/parser.h":

    cdef xmlDict* xmlDictCreate() nogil
    cdef xmlDict* xmlDictCreateSub(xmlDict* subdict) nogil
    cdef void xmlDictFree(xmlDict* sub) nogil
    cdef int xmlDictReference(xmlDict* dict) nogil
    
    cdef int XML_COMPLETE_ATTRS # SAX option for adding DTD default attributes

    ctypedef struct xmlParserCtxt:
        xmlDoc* myDoc
        xmlDict* dict
        void* _private
        bint wellFormed
        bint recovery
        int options
        bint disableSAX
        int errNo
        bint replaceEntities
        bint loadsubset
        bint validate
        xmlError lastError
        xmlNode* node
        xmlSAXHandler* sax
        void* userData
        int* spaceTab
        int spaceMax
        bint html
        bint progressive
        int inSubset
        int charset
        xmlParserInput* input

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
        # libxml2 2.7.0+ only:
        XML_PARSE_OLD10 = 131072 # parse using XML-1.0 before update 5
        XML_PARSE_NOBASEFIX = 262144 # do not fixup XINCLUDE xml:base uris
        XML_PARSE_HUGE = 524288 # relax any hardcoded limit from the parser

    cdef void xmlInitParser() nogil
    cdef void xmlCleanupParser() nogil

    cdef int xmlLineNumbersDefault(int onoff) nogil
    cdef xmlParserCtxt* xmlNewParserCtxt() nogil
    cdef xmlParserInput* xmlNewIOInputStream(xmlParserCtxt* ctxt,
                                             xmlParserInputBuffer* input,
                                             int enc) nogil
    cdef int xmlCtxtUseOptions(xmlParserCtxt* ctxt, int options) nogil
    cdef void xmlFreeParserCtxt(xmlParserCtxt* ctxt) nogil
    cdef void xmlCtxtReset(xmlParserCtxt* ctxt) nogil
    cdef void xmlClearParserCtxt(xmlParserCtxt* ctxt) nogil
    cdef int xmlParseChunk(xmlParserCtxt* ctxt,
                           char* chunk, int size, int terminate) nogil
    cdef xmlDoc* xmlCtxtReadDoc(xmlParserCtxt* ctxt,
                                char* cur, char* URL, char* encoding,
                                int options) nogil
    cdef xmlDoc* xmlCtxtReadFile(xmlParserCtxt* ctxt,
                                 char* filename, char* encoding,
                                 int options) nogil
    cdef xmlDoc* xmlCtxtReadIO(xmlParserCtxt* ctxt, 
                               xmlInputReadCallback ioread, 
                               xmlInputCloseCallback ioclose, 
                               void* ioctx,
                               char* URL, char* encoding,
                               int options) nogil
    cdef xmlDoc* xmlCtxtReadMemory(xmlParserCtxt* ctxt,
                                   char* buffer, int size,
                                   char* filename, char* encoding,
                                   int options) nogil

# iterparse:

    cdef xmlParserCtxt* xmlCreatePushParserCtxt(xmlSAXHandler* sax,
                                                void* user_data,
                                                char* chunk,
                                                int size,
                                                char* filename) nogil

    cdef int xmlCtxtResetPush(xmlParserCtxt* ctxt,
                              char* chunk,
                              int size,
                              char* filename,
                              char* encoding) nogil

# entity loaders:

    ctypedef xmlParserInput* (*xmlExternalEntityLoader)(
        char * URL, char * ID, xmlParserCtxt* context) nogil
    cdef xmlExternalEntityLoader xmlGetExternalEntityLoader() nogil
    cdef void xmlSetExternalEntityLoader(xmlExternalEntityLoader f) nogil

# DTDs:

    cdef xmlDtd* xmlParseDTD(char* ExternalID, char* SystemID) nogil
    cdef xmlDtd* xmlIOParseDTD(xmlSAXHandler* sax,
                               xmlParserInputBuffer* input,
                               int enc) nogil

cdef extern from "libxml/parserInternals.h":
    cdef xmlParserInput* xmlNewInputStream(xmlParserCtxt* ctxt)
    cdef xmlParserInput* xmlNewStringInputStream(xmlParserCtxt* ctxt, 
                                                 char* buffer) nogil
    cdef xmlParserInput* xmlNewInputFromFile(xmlParserCtxt* ctxt, 
                                             char* filename) nogil
    cdef void xmlFreeInputStream(xmlParserInput* input) nogil
    cdef int xmlSwitchEncoding(xmlParserCtxt* ctxt, int enc) nogil
