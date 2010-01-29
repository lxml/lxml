from cstd cimport FILE

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
    cdef xmlCharEncodingHandler* xmlFindCharEncodingHandler(char* name) nogil
    cdef xmlCharEncodingHandler* xmlGetCharEncodingHandler(
        xmlCharEncoding enc) nogil
    cdef int xmlCharEncCloseFunc(xmlCharEncodingHandler* handler) nogil
    cdef xmlCharEncoding xmlDetectCharEncoding(char* text, int len) nogil
    cdef char* xmlGetCharEncodingName(xmlCharEncoding enc) nogil
    cdef xmlCharEncoding xmlParseCharEncoding(char* name) nogil

cdef extern from "libxml/chvalid.h":
    cdef int xmlIsChar_ch(char c) nogil

cdef extern from "libxml/hash.h":
    ctypedef struct xmlHashTable
    ctypedef void xmlHashScanner(void* payload, void* data, char* name) # may require GIL!
    void xmlHashScan(xmlHashTable* table, xmlHashScanner f, void* data) nogil
    void* xmlHashLookup(xmlHashTable* table, char* name) nogil

cdef extern from *: # actually "libxml/dict.h"
    # libxml/dict.h appears to be broken to include in C
    ctypedef struct xmlDict
    cdef char* xmlDictLookup(xmlDict* dict, char* name, int len) nogil
    cdef char* xmlDictExists(xmlDict* dict, char* name, int len) nogil
    cdef int xmlDictOwns(xmlDict* dict, char* name) nogil

cdef extern from "libxml/tree.h":
    ctypedef struct xmlDoc
    ctypedef struct xmlAttr
    ctypedef struct xmlNotationTable

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
        unsigned short line

    ctypedef struct xmlDtd:
        char* name
        char* ExternalID
        char* SystemID
        void* notations
        void* entities
        void* pentities
        void* attributes
        void* elements
        xmlNode* children
        xmlNode* last
        xmlDoc* doc

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
        int standalone
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
        int error

    char* XML_XML_NAMESPACE
        
    cdef void xmlFreeDoc(xmlDoc* cur) nogil
    cdef void xmlFreeDtd(xmlDtd* cur) nogil
    cdef void xmlFreeNode(xmlNode* cur) nogil
    cdef void xmlFreeNsList(xmlNs* ns) nogil
    cdef void xmlFreeNs(xmlNs* ns) nogil
    cdef void xmlFree(char* buf) nogil
    
    cdef xmlNode* xmlNewNode(xmlNs* ns, char* name) nogil
    cdef xmlNode* xmlNewDocText(xmlDoc* doc, char* content) nogil
    cdef xmlNode* xmlNewDocComment(xmlDoc* doc, char* content) nogil
    cdef xmlNode* xmlNewDocPI(xmlDoc* doc, char* name, char* content) nogil
    cdef xmlNode* xmlNewReference(xmlDoc* doc, char* name) nogil
    cdef xmlNode* xmlNewCDataBlock(xmlDoc* doc, char* text, int len) nogil
    cdef xmlNs* xmlNewNs(xmlNode* node, char* href, char* prefix) nogil
    cdef xmlNode* xmlAddChild(xmlNode* parent, xmlNode* cur) nogil
    cdef xmlNode* xmlReplaceNode(xmlNode* old, xmlNode* cur) nogil
    cdef xmlNode* xmlAddPrevSibling(xmlNode* cur, xmlNode* elem) nogil
    cdef xmlNode* xmlAddNextSibling(xmlNode* cur, xmlNode* elem) nogil
    cdef xmlNode* xmlNewDocNode(xmlDoc* doc, xmlNs* ns,
                                char* name, char* content) nogil
    cdef xmlDoc* xmlNewDoc(char* version) nogil
    cdef xmlAttr* xmlNewProp(xmlNode* node, char* name, char* value) nogil
    cdef xmlAttr* xmlNewNsProp(xmlNode* node, xmlNs* ns,
                               char* name, char* value) nogil
    cdef char* xmlGetNoNsProp(xmlNode* node, char* name) nogil
    cdef char* xmlGetNsProp(xmlNode* node, char* name, char* nameSpace) nogil
    cdef void xmlSetNs(xmlNode* node, xmlNs* ns) nogil
    cdef xmlAttr* xmlSetProp(xmlNode* node, char* name, char* value) nogil
    cdef xmlAttr* xmlSetNsProp(xmlNode* node, xmlNs* ns,
                               char* name, char* value) nogil
    cdef int xmlRemoveProp(xmlAttr* cur) nogil
    cdef char* xmlGetNodePath(xmlNode* node) nogil
    cdef void xmlDocDumpMemory(xmlDoc* cur, char** mem, int* size) nogil
    cdef void xmlDocDumpMemoryEnc(xmlDoc* cur, char** mem, int* size,
                                  char* encoding) nogil
    cdef int xmlSaveFileTo(xmlOutputBuffer* out, xmlDoc* cur,
                           char* encoding) nogil

    cdef void xmlUnlinkNode(xmlNode* cur) nogil
    cdef xmlNode* xmlDocSetRootElement(xmlDoc* doc, xmlNode* root) nogil
    cdef xmlNode* xmlDocGetRootElement(xmlDoc* doc) nogil
    cdef void xmlSetTreeDoc(xmlNode* tree, xmlDoc* doc) nogil
    cdef xmlAttr* xmlHasProp(xmlNode* node, char* name) nogil
    cdef xmlAttr* xmlHasNsProp(xmlNode* node, char* name, char* nameSpace) nogil
    cdef char* xmlNodeGetContent(xmlNode* cur) nogil
    cdef int xmlNodeBufGetContent(xmlBuffer* buffer, xmlNode* cur) nogil
    cdef xmlNs* xmlSearchNs(xmlDoc* doc, xmlNode* node, char* prefix) nogil
    cdef xmlNs* xmlSearchNsByHref(xmlDoc* doc, xmlNode* node, char* href) nogil
    cdef int xmlIsBlankNode(xmlNode* node) nogil
    cdef long xmlGetLineNo(xmlNode* node) nogil
    cdef void xmlElemDump(FILE* f, xmlDoc* doc, xmlNode* cur) nogil
    cdef void xmlNodeDumpOutput(xmlOutputBuffer* buf,
                                xmlDoc* doc, xmlNode* cur, int level,
                                int format, char* encoding) nogil
    cdef void xmlNodeSetName(xmlNode* cur, char* name) nogil
    cdef void xmlNodeSetContent(xmlNode* cur, char* content) nogil
    cdef xmlDtd* xmlCopyDtd(xmlDtd* dtd) nogil
    cdef xmlDoc* xmlCopyDoc(xmlDoc* doc, int recursive) nogil
    cdef xmlNode* xmlCopyNode(xmlNode* node, int extended) nogil
    cdef xmlNode* xmlDocCopyNode(xmlNode* node, xmlDoc* doc, int extended) nogil
    cdef int xmlReconciliateNs(xmlDoc* doc, xmlNode* tree) nogil
    cdef xmlNs* xmlNewReconciliedNs(xmlDoc* doc, xmlNode* tree, xmlNs* ns) nogil
    cdef xmlBuffer* xmlBufferCreate() nogil
    cdef void xmlBufferWriteChar(xmlBuffer* buf, char* string) nogil
    cdef void xmlBufferFree(xmlBuffer* buf) nogil
    cdef char* xmlBufferContent(xmlBuffer* buf) nogil
    cdef int xmlBufferLength(xmlBuffer* buf) nogil
    cdef int xmlKeepBlanksDefault(int val) nogil
    cdef char* xmlNodeGetBase(xmlDoc* doc, xmlNode* node) nogil
    cdef void xmlNodeSetBase(xmlNode* node, char* uri) nogil
    cdef int xmlValidateNCName(char* value, int space) nogil

cdef extern from "libxml/uri.h":
    cdef char* xmlBuildURI(char* href, char* base) nogil

cdef extern from "libxml/HTMLtree.h":
    cdef void htmlNodeDumpFormatOutput(xmlOutputBuffer* buf,
                                       xmlDoc* doc, xmlNode* cur,
                                       char* encoding, int format) nogil
    cdef xmlDoc* htmlNewDoc(char* uri, char* externalID) nogil

cdef extern from "libxml/valid.h":
    cdef xmlAttr* xmlGetID(xmlDoc* doc, char* ID) nogil
    cdef void xmlDumpNotationTable(xmlBuffer* buffer,
                                   xmlNotationTable* table) nogil

cdef extern from "libxml/xmlIO.h":
    cdef int xmlOutputBufferWriteString(xmlOutputBuffer* out, char* str) nogil
    cdef int xmlOutputBufferWrite(xmlOutputBuffer* out,
                                  int len, char* str) nogil
    cdef int xmlOutputBufferFlush(xmlOutputBuffer* out) nogil
    cdef int xmlOutputBufferClose(xmlOutputBuffer* out) nogil

    ctypedef int (*xmlInputReadCallback)(void* context,
                                         char* buffer, int len)
    ctypedef int (*xmlInputCloseCallback)(void* context)

    ctypedef int (*xmlOutputWriteCallback)(void* context,
                                           char* buffer, int len)
    ctypedef int (*xmlOutputCloseCallback)(void* context)

    cdef xmlOutputBuffer* xmlAllocOutputBuffer(
        xmlCharEncodingHandler* encoder) nogil
    cdef xmlOutputBuffer* xmlOutputBufferCreateIO(
        xmlOutputWriteCallback iowrite,
        xmlOutputCloseCallback ioclose,
        void * ioctx, 
        xmlCharEncodingHandler* encoder) nogil
    cdef xmlOutputBuffer* xmlOutputBufferCreateFile(
        FILE* file, xmlCharEncodingHandler* encoder) nogil
    cdef xmlOutputBuffer* xmlOutputBufferCreateFilename(
        char* URI, xmlCharEncodingHandler* encoder, int compression) nogil

cdef extern from "libxml/xmlsave.h":
    ctypedef struct xmlSaveCtxt

    ctypedef enum xmlSaveOption:
        XML_SAVE_FORMAT   = 1   # format save output            (2.6.17)
        XML_SAVE_NO_DECL  = 2   # drop the xml declaration      (2.6.21)
        XML_SAVE_NO_EMPTY = 4   # no empty tags                 (2.6.22)
        XML_SAVE_NO_XHTML = 8   # disable XHTML1 specific rules (2.6.22)
        XML_SAVE_XHTML = 16     # force XHTML1 specific rules         (2.7.2)
        XML_SAVE_AS_XML = 32    # force XML serialization on HTML doc (2.7.2)
        XML_SAVE_AS_HTML = 64   # force HTML serialization on XML doc (2.7.2)

    cdef xmlSaveCtxt* xmlSaveToFilename(char* filename, char* encoding,
                                        int options) nogil
    cdef xmlSaveCtxt* xmlSaveToBuffer(xmlBuffer* buffer, char* encoding,
                                      int options) nogil # libxml2 2.6.23
    cdef long xmlSaveDoc(xmlSaveCtxt* ctxt, xmlDoc* doc) nogil
    cdef long xmlSaveTree(xmlSaveCtxt* ctxt, xmlNode* node) nogil
    cdef int xmlSaveClose(xmlSaveCtxt* ctxt) nogil
    cdef int xmlSaveFlush(xmlSaveCtxt* ctxt) nogil
    cdef int xmlSaveSetAttrEscape(xmlSaveCtxt* ctxt, void* escape_func) nogil
    cdef int xmlSaveSetEscape(xmlSaveCtxt* ctxt, void* escape_func) nogil

cdef extern from "libxml/globals.h":
    cdef int xmlThrDefKeepBlanksDefaultValue(int onoff) nogil
    cdef int xmlThrDefLineNumbersDefaultValue(int onoff) nogil
    cdef int xmlThrDefIndentTreeOutput(int onoff) nogil
    
cdef extern from "libxml/xmlstring.h":
    cdef char* xmlStrdup(char* cur) nogil

cdef extern from "libxml/xmlmemory.h":
    cdef void* xmlMalloc(size_t size) nogil
    cdef int xmlMemBlocks() nogil

cdef extern from "etree_defs.h":
    cdef bint _isElement(xmlNode* node) nogil
    cdef bint _isElementOrXInclude(xmlNode* node) nogil
    cdef char* _getNs(xmlNode* node) nogil
    cdef void BEGIN_FOR_EACH_ELEMENT_FROM(xmlNode* tree_top,
                                          xmlNode* start_node,
                                          bint inclusive) nogil
    cdef void END_FOR_EACH_ELEMENT_FROM(xmlNode* start_node) nogil
    cdef void BEGIN_FOR_EACH_FROM(xmlNode* tree_top,
                                  xmlNode* start_node,
                                  bint inclusive) nogil
    cdef void END_FOR_EACH_FROM(xmlNode* start_node) nogil
