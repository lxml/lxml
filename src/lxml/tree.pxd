from cstd cimport FILE, size_t

cdef extern from "lxml-version.h":
    cdef char* LXML_VERSION_STRING

cdef extern from "libxml/xmlversion.h":
    cdef char* xmlParserVersion
    cdef int LIBXML_VERSION

cdef extern from "libxml/encoding.h":
    ctypedef enum xmlCharEncoding:
        XML_CHAR_ENCODING_ERROR = -1 # No char encoding detected
        XML_CHAR_ENCODING_NONE = 0 # No char encoding detected
        XML_CHAR_ENCODING_UTF8 = 1 # UTF-8
        XML_CHAR_ENCODING_UTF16LE = 2 # UTF-16 little endian
        XML_CHAR_ENCODING_UTF16BE = 3 # UTF-16 big endian
        XML_CHAR_ENCODING_UCS4LE = 4 # UCS-4 little endian
        XML_CHAR_ENCODING_UCS4BE = 5 # UCS-4 big endian
        XML_CHAR_ENCODING_EBCDIC = 6 # EBCDIC uh!
        XML_CHAR_ENCODING_UCS4_2143 = 7 # UCS-4 unusual ordering
        XML_CHAR_ENCODING_UCS4_3412 = 8 # UCS-4 unusual ordering
        XML_CHAR_ENCODING_UCS2 = 9 # UCS-2
        XML_CHAR_ENCODING_8859_1 = 10 # ISO-8859-1 ISO Latin 1
        XML_CHAR_ENCODING_8859_2 = 11 # ISO-8859-2 ISO Latin 2
        XML_CHAR_ENCODING_8859_3 = 12 # ISO-8859-3
        XML_CHAR_ENCODING_8859_4 = 13 # ISO-8859-4
        XML_CHAR_ENCODING_8859_5 = 14 # ISO-8859-5
        XML_CHAR_ENCODING_8859_6 = 15 # ISO-8859-6
        XML_CHAR_ENCODING_8859_7 = 16 # ISO-8859-7
        XML_CHAR_ENCODING_8859_8 = 17 # ISO-8859-8
        XML_CHAR_ENCODING_8859_9 = 18 # ISO-8859-9
        XML_CHAR_ENCODING_2022_JP = 19 # ISO-2022-JP
        XML_CHAR_ENCODING_SHIFT_JIS = 20 # Shift_JIS
        XML_CHAR_ENCODING_EUC_JP = 21 # EUC-JP
        XML_CHAR_ENCODING_ASCII = 22 # pure ASCII

    ctypedef struct xmlCharEncodingHandler
    cdef xmlCharEncodingHandler* xmlFindCharEncodingHandler(char* name)
    cdef xmlCharEncodingHandler* xmlGetCharEncodingHandler(int enc)
    cdef int xmlCharEncCloseFunc(xmlCharEncodingHandler* handler)
    cdef int xmlDetectCharEncoding(char* text, int len)
    cdef char* xmlGetCharEncodingName(xmlCharEncoding enc)

cdef extern from "libxml/hash.h":
    ctypedef struct xmlHashTable
    ctypedef void xmlHashScanner(void* payload, void* data, char* name)
    void xmlHashScan(xmlHashTable* table, xmlHashScanner f, void* data)
    void* xmlHashLookup(xmlHashTable* table, char* name)

cdef extern from "libxml/tree.h":

    # for some reason need to define this in this section;
    # libxml/dict.h appears to be broken to include in C
    ctypedef struct xmlDict
    
    ctypedef struct xmlDoc
    ctypedef struct xmlAttr
    
    ctypedef enum xmlElementType:
        XML_ELEMENT_NODE=           1
        XML_ATTRIBUTE_NODE=         2
        XML_TEXT_NODE=              3
        XML_CDATA_SECTION_NODE=     4
        XML_ENTITY_REF_NODE=        5
        XML_ENTITY_NODE=            6
        XML_PI_NODE=                7
        XML_COMMENT_NODE=           8
        XML_DOCUMENT_NODE=          9
        XML_DOCUMENT_TYPE_NODE=     10
        XML_DOCUMENT_FRAG_NODE=     11
        XML_NOTATION_NODE=          12
        XML_HTML_DOCUMENT_NODE=     13
        XML_DTD_NODE=               14
        XML_ELEMENT_DECL=           15
        XML_ATTRIBUTE_DECL=         16
        XML_ENTITY_DECL=            17
        XML_NAMESPACE_DECL=         18
        XML_XINCLUDE_START=         19
        XML_XINCLUDE_END=           20

    
    ctypedef struct xmlNs:
        char* href
        char* prefix
        xmlNs* next

    ctypedef struct xmlNode:
        void* _private
        xmlElementType   type
        char* name
        xmlNode* children
        xmlNode* last
        xmlNode* parent
        xmlNode* next
        xmlNode* prev
        xmlDoc* doc
        char* content
        xmlAttr* properties
        xmlNs* ns
        xmlNs* nsDef

    ctypedef struct xmlDtd:
        char* ExternalID
        char* SystemID

    ctypedef struct xmlDoc:
        xmlElementType type
        char* name
        xmlNode* children
        xmlNode* last
        xmlNode* parent
        xmlNode* next
        xmlNode* prev
        xmlDoc* doc
        xmlDict* dict
        xmlHashTable* ids
        char* version
        char* encoding
        char* URL
        void* _private
        xmlDtd* intSubset
        xmlDtd* extSubset
        
    ctypedef struct xmlAttr:
        void* _private
        xmlElementType type
        char* name
        xmlNode* children
        xmlNode* last
        xmlNode* parent
        xmlAttr* next
        xmlAttr* prev
        xmlDoc* doc
        xmlNs* ns
        
    ctypedef struct xmlElement:
        xmlElementType type
        char* name
        xmlNode* children
        xmlNode* last
        xmlNode* parent
        xmlNode* next
        xmlNode* prev
        xmlDoc* doc

    ctypedef struct xmlID:
        char* value
        xmlAttr* attr
        xmlDoc* doc
        
    ctypedef struct xmlBuffer
    
    ctypedef struct xmlOutputBuffer:
        xmlBuffer* buffer
        xmlBuffer* conv
        
    cdef void xmlFreeDoc(xmlDoc *cur)
    cdef void xmlFreeNode(xmlNode* cur)
    cdef void xmlFree(char* buf)
    
    cdef xmlNode* xmlNewNode(xmlNs* ns, char* name)
    cdef xmlNode* xmlNewDocText(xmlDoc* doc, char* content)
    cdef xmlNode* xmlNewDocComment(xmlDoc* doc, char* content)
    cdef xmlNode* xmlNewDocPI(xmlDoc* doc, char* name, char* content)
    cdef xmlNs* xmlNewNs(xmlNode* node, char* href, char* prefix)
    cdef xmlNode* xmlAddChild(xmlNode* parent, xmlNode* cur)
    cdef xmlNode* xmlReplaceNode(xmlNode* old, xmlNode* cur)
    cdef xmlNode* xmlAddPrevSibling(xmlNode* cur, xmlNode* elem)
    cdef xmlNode* xmlAddNextSibling(xmlNode* cur, xmlNode* elem)
    cdef xmlNode* xmlNewDocNode(xmlDoc* doc, xmlNs* ns,
                                char* name, char* content)
    cdef xmlDoc* xmlNewDoc(char* version)
    cdef xmlAttr* xmlNewProp(xmlNode* node, char* name, char* value)
    cdef xmlAttr* xmlNewNsProp(xmlNode* node, xmlNs* ns,
                               char* name, char* value)
    cdef char* xmlGetNoNsProp(xmlNode* node, char* name)
    cdef char* xmlGetNsProp(xmlNode* node, char* name, char* nameSpace)
    cdef void xmlSetNs(xmlNode* node, xmlNs* ns)
    cdef xmlAttr* xmlSetProp(xmlNode* node, char* name, char* value)
    cdef xmlAttr* xmlSetNsProp(xmlNode* node, xmlNs* ns,
                               char* name, char* value)
    cdef int xmlRemoveProp(xmlAttr* cur)
    cdef char* xmlGetNodePath(xmlNode* node)
    cdef void xmlDocDumpMemory(xmlDoc* cur, char** mem, int* size)
    cdef void xmlDocDumpMemoryEnc(xmlDoc* cur, char** mem, int* size,
                                  char* encoding)
    cdef int xmlSaveFileTo(xmlOutputBuffer* out, xmlDoc* cur, char* encoding)

    cdef void xmlUnlinkNode(xmlNode* cur)
    cdef xmlNode* xmlDocSetRootElement(xmlDoc* doc, xmlNode* root)
    cdef xmlNode* xmlDocGetRootElement(xmlDoc* doc)
    cdef void xmlSetTreeDoc(xmlNode* tree, xmlDoc* doc)
    cdef xmlAttr* xmlHasProp(xmlNode* node, char* name)
    cdef xmlAttr* xmlHasNsProp(xmlNode* node, char* name, char* nameSpace)
    cdef char* xmlNodeGetContent(xmlNode* cur)
    cdef xmlNs* xmlSearchNs(xmlDoc* doc, xmlNode* node, char* nameSpace)
    cdef xmlNs* xmlSearchNsByHref(xmlDoc* doc, xmlNode* node, char* href)
    cdef int xmlIsBlankNode(xmlNode* node)
    cdef void xmlElemDump(FILE* f, xmlDoc* doc, xmlNode* cur)
    cdef void xmlNodeDumpOutput(xmlOutputBuffer* buf,
                                xmlDoc* doc, xmlNode* cur, int level,
                                int format, char* encoding)
    cdef void xmlNodeSetName(xmlNode* cur, char* name)
    cdef void xmlNodeSetContent(xmlNode* cur, char* content)
    cdef xmlDoc* xmlCopyDoc(xmlDoc* doc, int recursive)
    cdef xmlNode* xmlCopyNode(xmlNode* node, int extended)
    cdef xmlNode* xmlDocCopyNode(xmlNode* node, xmlDoc* doc, int extended)
    cdef int xmlReconciliateNs(xmlDoc* doc, xmlNode* tree)
    cdef xmlBuffer* xmlBufferCreate()
    cdef char* xmlBufferContent(xmlBuffer* buf)
    cdef int xmlBufferLength(xmlBuffer* buf)
    cdef int xmlKeepBlanksDefault(int val)
    cdef char* xmlNodeGetBase(xmlDoc* doc, xmlNode* node)
    cdef char* xmlBuildURI(char* href, char* base)

cdef extern from "libxml/valid.h":
    cdef xmlAttr* xmlGetID(xmlDoc* doc, char* ID)

cdef extern from "libxml/xmlIO.h":
    cdef int xmlOutputBufferWriteString(xmlOutputBuffer* out, char* str)
    cdef int xmlOutputBufferFlush(xmlOutputBuffer* out)
    cdef int xmlOutputBufferClose(xmlOutputBuffer* out)

    ctypedef int (*xmlInputReadCallback)(void* context, char* buffer, int len)
    ctypedef int (*xmlInputCloseCallback)(void* context)

    ctypedef int (*xmlOutputWriteCallback)(void* context, char* buffer, int len)
    ctypedef int (*xmlOutputCloseCallback)(void* context)

    cdef xmlOutputBuffer* xmlAllocOutputBuffer(xmlCharEncodingHandler* encoder)
    cdef xmlOutputBuffer* xmlOutputBufferCreateIO(
        xmlOutputWriteCallback iowrite,
        xmlOutputCloseCallback ioclose,
        void * ioctx, 
        xmlCharEncodingHandler* encoder)
    cdef xmlOutputBuffer* xmlOutputBufferCreateFile(
        FILE* file, xmlCharEncodingHandler* encoder)
    cdef xmlOutputBuffer* xmlOutputBufferCreateFilename(
        char* URI, xmlCharEncodingHandler* encoder, int compression)

cdef extern from "libxml/xmlsave.h":
    ctypedef struct xmlSaveCtxt:
        pass
    
    cdef xmlSaveCtxt* xmlSaveToFilename(char* filename, char* encoding,
                                        int options)
    cdef long xmlSaveDoc(xmlSaveCtxt* ctxt, xmlDoc* doc)
    cdef int xmlSaveClose(xmlSaveCtxt* ctxt)

cdef extern from "libxml/globals.h":
    cdef int xmlThrDefKeepBlanksDefaultValue(int onoff)
    cdef int xmlThrDefLineNumbersDefaultValue(int onoff)
    cdef int xmlThrDefIndentTreeOutput(int onoff)
    
cdef extern from "libxml/xmlstring.h":
    cdef char* xmlStrdup(char* cur)

cdef extern from "libxml/xmlmemory.h":
    cdef void* xmlMalloc(size_t size)

cdef extern from "etree_defs.h":
    cdef int _isElement(xmlNode* node)
    cdef char* _getNs(xmlNode* node)
    cdef void BEGIN_FOR_EACH_ELEMENT_FROM(xmlNode* tree_top,
                                          xmlNode* start_node, int inclusive)
    cdef void END_FOR_EACH_ELEMENT_FROM(xmlNode* start_node)
