
# Helper to wrap pointer into python objects
cdef extern from "Python.h": 
    object PyString_Decode(char* s, int size, char* encoding, char* errors)
        
cdef extern from "libxml/tree.h":
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

    ctypedef struct xmlDoc
    
    ctypedef struct xmlNode:
        xmlElementType   type
        char   *name
        xmlNode *children
        xmlNode *last
        xmlNode *parent
        xmlNode *next
        xmlNode *prev
        xmlDoc *doc
        char *content
        
    ctypedef struct xmlDoc:
        xmlElementType type
        char *name
        xmlNode *children
        xmlNode *last
        xmlNode *parent
        xmlNode *next
        xmlNode *prev
        xmlDoc *doc

    ctypedef struct xmlNs:
        char* href
        char* prefix
        
    cdef void xmlFreeDoc(xmlDoc *cur)
    cdef xmlNode* xmlNewNode(xmlNs* ns, char* name)
    cdef xmlNode* xmlAddChild(xmlNode* parent, xmlNode* cur)
    cdef xmlNode* xmlNewDocNode(xmlDoc* doc, xmlNs* ns,
                                char* name, char* content)
    cdef xmlDoc* xmlNewDoc(char* version)
    
cdef extern from "libxml/parser.h":
    cdef xmlDoc *xmlParseFile(char* filename)

cdef class _BaseNode
cdef class _Node(_BaseNode)
cdef class _Document(_BaseNode)

cdef class _BaseNode:
    cdef xmlNode *_o

    def name(self):
        return unicode(self._o.name, 'UTF-8')

    def type(self):
        return self._o.type

    def firstChild(self):
        return Node(self._getDoc(), self._o.children)

    def parent(self):
        cdef xmlNode *parent
        parent = self._o.parent
        if parent.type == XML_DOCUMENT_NODE:
            return self._getDoc()
        return Node(self._getDoc(), self._o.parent)
    
    def nextSibling(self):
        return Node(self._getDoc(), self._o.next)

    def previousSibling(self):
        return Node(self._getDoc(), self._o.prev)
 
cdef class _Document(_BaseNode):

    def __dealloc__(self):
        xmlFreeDoc(<xmlDoc*>self._o)

    def parent(self):
        return None
    
    def _getDoc(self):
        return self
    
cdef _Document Document(xmlDoc* o):
    cdef _Document result
    result = _Document()
    result._o = <xmlNode*>o
    return result

cdef class _Node(_BaseNode):
    cdef _Document _doc

    def _getDoc(self):
        return self._doc

cdef class _TextNode(_Node):
    def content(self):
        return unicode(self._o.content, 'UTF-8')
    
cdef _Node Node(_Document doc, xmlNode* o):
    cdef _Node result
    if o is NULL:
        return None
    if o.type == XML_TEXT_NODE:
        result = _TextNode()
    else:
        result = _Node()
    result._doc = doc
    result._o = o
    return result

def parseFile(filename):
    cdef xmlDoc *doc
    doc = xmlParseFile(filename)
    return Document(doc)

