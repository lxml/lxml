"""
DOM implementation on top of libxml.

Read-only for starters.
"""
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
    ctypedef struct xmlAttr

    ctypedef struct xmlNs:
        char* href
        char* prefix

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
        xmlAttr* properties
        xmlNs* ns
        
    ctypedef struct xmlDoc:
        xmlElementType type
        char *name
        xmlNode *children
        xmlNode *last
        xmlNode *parent
        xmlNode *next
        xmlNode *prev
        xmlDoc *doc
                
    ctypedef struct xmlAttr:
        xmlElementType type
        char* name
        xmlNode* children
        xmlNode* last
        xmlNode* parent
        xmlNode* next
        xmlNode* prev
        xmlDoc* doc

    ctypedef struct xmlElement:
        xmlElementType type
        char* name
        xmlNode* children
        xmlNode* last
        xmlNode* parent
        xmlNode* next
        xmlNode* prev
        xmlDoc* doc
 
    cdef void xmlFreeDoc(xmlDoc *cur)
    cdef xmlNode* xmlNewNode(xmlNs* ns, char* name)
    cdef xmlNode* xmlAddChild(xmlNode* parent, xmlNode* cur)
    cdef xmlNode* xmlNewDocNode(xmlDoc* doc, xmlNs* ns,
                                char* name, char* content)
    cdef xmlDoc* xmlNewDoc(char* version)
    cdef xmlAttr* xmlNewProp(xmlNode* node, char* name, char* value)
    cdef char* xmlGetNoNsProp(xmlNode* node, char* name)
    cdef void xmlSetProp(xmlNode* node, char* name, char* value)
    cdef void xmlDocDumpMemory(xmlDoc* cur,
                               char** mem,
                               int* size)
    cdef void xmlFree(char* buf)
    cdef void xmlUnlinkNode(xmlNode* cur)
    cdef xmlNode* xmlDocSetRootElement(xmlDoc* doc, xmlNode* root)
    cdef xmlNode* xmlDocGetRootElement(xmlDoc* doc)
    cdef void xmlSetTreeDoc(xmlNode* tree, xmlDoc* doc)
    cdef xmlNode* xmlDocCopyNode(xmlNode* node, xmlDoc* doc, int extended)
    
cdef extern from "libxml/parser.h":
    cdef xmlDoc* xmlParseFile(char* filename)
    cdef xmlDoc* xmlParseDoc(char* cur)

cdef class Node
cdef class Document(Node)

cdef class _RefBase:
    cdef xmlNode* _o
    cdef Document _doc
    
    def _getDoc(self):
        return self._doc

cdef class Node:
    cdef xmlNode* _o
    
    def _getDoc(self):
        return self._doc

    property ELEMENT_NODE:
        def __get__(self):
            return 1

    property ATTRIBUTE_NODE:
        def __get__(self):
            return 2

    property TEXT_NODE:
        def __get__(self):
            return 3

    property DOCUMENT_NODE:
        def __get__(self):
            return 9

    def __cmp__(Node self, Node other):
        if self._o is other._o:
            return 0
        else:
            return 1

    def isSameNode(Node self, Node other):
        return self.__cmp__(self, other)

    property childNodes:
        def __get__(self):
            return _nodeListFactory(self._getDoc(), self._o)

    property parentNode:
        def __get__(self):
            return _nodeFactory(self._getDoc(), self._o.parent)

    property firstChild:
        def __get__(self):
            return _nodeFactory(self._getDoc(), self._o.children)
        
    property lastChild:
        def __get__(self):
            return _nodeFactory(self._getDoc(), self._o.last)

    property previousSibling:
        def __get__(self):
            return _nodeFactory(self._getDoc(), self._o.prev)

    property nextSibling:
        def __get__(self):
            return _nodeFactory(self._getDoc(), self._o.next)

cdef class NonDocNode(Node):
    cdef Document _doc
    
    def _getDoc(self):
        return self._doc

    property ownerDocument:
        def __get__(self):
            # XXX if this node has just be created this isn't valid
            # XXX but we're a read-only DOM for now
            return self._getDoc()

cdef class Document(Node):
    def _getDoc(self):
        return self
    
    def __dealloc__(self):
        xmlFreeDoc(<xmlDoc*>self._o)

    property nodeType:
        def __get__(self):
            return 9 # DOCUMENT_NODE
        
    property ownerDocument:
        def __get__(self):
            return None
        
cdef Document _documentFactory(xmlDoc* c_doc):
    cdef Document doc
    doc = Document()
    doc._o = <xmlNode*>c_doc
    return doc
        
cdef class Element(NonDocNode):
                
    property nodeName:
        def __get__(self):
            return self.tagName

    property nodeValue:
        def __get__(self):
            return None

    property nodeType:
        def __get__(self):
            return 1 # ELEMENT_NODE
        
    property localName:
        def __get__(self):
            return unicode(self._o.name, 'UTF-8')
        
    property tagName:
        def __get__(self):
            if self.prefix is None:
                return self.localName
            else:
                return self.prefix + ':' + self.localName

    property prefix:
        def __get__(self):
            if self._o.ns is NULL or self._o.ns.prefix is NULL:
                return None
            return unicode(self._o.ns.prefix, 'UTF-8')

    property namespaceURI:
        def __get__(self):
            if self._o.ns is NULL or self._o.ns.href is NULL:
                return None
            return unicode(self._o.ns.href, 'UTF-8')
        
    
cdef _elementFactory(Document doc, xmlNode* c_node):
    cdef Element result
    result = Element()
    result._doc = doc
    result._o = c_node
    return result
    
cdef class NodeList(_RefBase):
    def __getitem__(self, index):
        cdef xmlNode* c_node
        c_node = self._o.children
        c = 0
        while c_node is not NULL:
            if c == index:
                return _nodeFactory(self._getDoc(), c_node)
            c = c + 1
            c_node = c_node.next
        else:
            raise IndexError

cdef _nodeListFactory(Document doc, xmlNode* c_node):
    cdef NodeList result
    result = NodeList()
    result._doc = doc
    result._o = c_node
    return result

cdef _nodeFactory(Document doc, xmlNode* c_node):
    if c_node is NULL:
        return None
    if c_node.type == 1: # ELEMENT_NODE
        return _elementFactory(doc, c_node)
    if c_node.type == 9: # DOCUMENT_NODE
        return doc
    
def makeDocument(text):
    cdef xmlDoc* c_doc
    c_doc = xmlParseDoc(text)
    return _documentFactory(c_doc)
