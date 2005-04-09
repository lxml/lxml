#from xmlparser cimport xmlDict

cdef extern from "stdio.h":
    ctypedef struct FILE
    cdef int strlen(char* s)
    
cdef extern from "Python.h":
    ctypedef struct PyObject
    
    cdef FILE* PyFile_AsFile(PyObject* p)
    cdef int PyFile_Check(object p)
    cdef object PyFile_Name(object p)
    cdef void Py_INCREF(object o)
    cdef object PyUnicode_DecodeUTF8(char* s, int size, char* errors)
    cdef object PyString_FromStringAndSize(char* s, int size)
    
cdef extern from "libxml/encoding.h":
    ctypedef struct xmlCharEncodingHandler
    
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
        char* URL
        
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

    ctypedef struct xmlOutputBuffer
    
    cdef void xmlFreeDoc(xmlDoc *cur)
    cdef void xmlFreeNode(xmlNode* cur)
    cdef void xmlFree(char* buf)
    
    cdef xmlNode* xmlNewNode(xmlNs* ns, char* name)
    cdef xmlNode* xmlNewDocText(xmlDoc* doc, char* content)
    cdef xmlNode* xmlNewDocComment(xmlDoc* doc, char* content)
    cdef xmlNs* xmlNewNs(xmlNode* node, char* href, char* prefix)
    cdef xmlNode* xmlAddChild(xmlNode* parent, xmlNode* cur)
    cdef xmlNode* xmlReplaceNode(xmlNode* old, xmlNode* cur)
    cdef xmlNode* xmlAddPrevSibling(xmlNode* cur, xmlNode* elem)
    cdef xmlNode* xmlAddNextSibling(xmlNode* cur, xmlNode* elem)
    cdef xmlNode* xmlNewDocNode(xmlDoc* doc, xmlNs* ns,
                                char* name, char* content)
    cdef xmlDoc* xmlNewDoc(char* version)
    cdef xmlAttr* xmlNewProp(xmlNode* node, char* name, char* value)
    cdef char* xmlGetNoNsProp(xmlNode* node, char* name)
    cdef char* xmlGetNsProp(xmlNode* node, char* name, char* nameSpace)
    cdef void xmlSetNs(xmlNode* node, xmlNs* ns)
    cdef void xmlSetProp(xmlNode* node, char* name, char* value)
    cdef void xmlSetNsProp(xmlNode* node, xmlNs* ns, char* name, char* value)
    cdef void xmlRemoveProp(xmlAttr* cur)
    cdef void xmlDocDumpMemory(xmlDoc* cur,
                               char** mem,
                               int* size)
    cdef void xmlUnlinkNode(xmlNode* cur)
    cdef xmlNode* xmlDocSetRootElement(xmlDoc* doc, xmlNode* root)
    cdef xmlNode* xmlDocGetRootElement(xmlDoc* doc)
    cdef void xmlSetTreeDoc(xmlNode* tree, xmlDoc* doc)
    cdef xmlNode* xmlDocCopyNode(xmlNode* node, xmlDoc* doc, int extended)
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
    cdef xmlDoc* xmlCopyDoc(xmlDoc* doc, int recursive)
    
cdef extern from "libxml/xmlIO.h":
    cdef xmlOutputBuffer* xmlOutputBufferCreateFile(
        FILE* file,
        xmlCharEncodingHandler* encoder)
    cdef int xmlOutputBufferWriteString(xmlOutputBuffer* out, char* str)
    cdef int xmlOutputBufferFlush(xmlOutputBuffer* out)
    
cdef extern from "libxml/xmlstring.h":
    cdef char* xmlStrdup(char* cur)
    
