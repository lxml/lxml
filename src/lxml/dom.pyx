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
    
cdef class _DocumentBase:
    """Base class to reference a libxml document.

    When instances of this class are garbage collected, the libxml
    document is cleaned up.
    """
    
    cdef xmlDoc* _c_doc

    def __dealloc__(self):
        xmlFreeDoc(self._c_doc)
    
cdef class _NodeBase:
    """Base class to reference a document object and a libxml node.

    By pointing to an ElementTree instance, a reference is kept to
    _ElementTree as long as there is some pointer to a node in it.
    """
    cdef _DocumentBase _doc
    cdef xmlNode* _c_node

cdef class Document(_DocumentBase):
    property childNodes:
        def __get__(self):
            return _nodeListFactory(self, <xmlNode*>self._c_doc)

    property firstChild:
        def __get__(self):
            return _nodeFactory(self, self._c_doc.children)

    property lastChild:
        def __get__(self):
            return _nodeFactory(self, self._c_doc.last)

    property previousSibling:
        def __get__(self):
            return _nodeFactory(self, self._c_doc.prev)

    property nextSibling:
        def __get__(self):
            return _nodeFactory(self, self._c_doc.next)

    property ownerDocument:
        def __get__(self):
            return None
        
cdef Document _documentFactory(xmlDoc* c_doc):
    cdef Document doc
    doc = Document()
    doc._c_doc = c_doc
    return doc
    
cdef class Node(_NodeBase):
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
        if self._c_node is other._c_node:
            return 0
        else:
            return 1
    
cdef class Element(Node):

    property childNodes:
        def __get__(self):
            return _nodeListFactory(self._doc, self._c_node)
                
    property nodeName:
        def __get__(self):
            return self.tagName

    property nodeValue:
        def __get__(self):
            return None
        
    property localName:
        def __get__(self):
            return unicode(self._c_node.name, 'UTF-8')
        
    property tagName:
        def __get__(self):
            if self.prefix is None:
                return self.localName
            else:
                return self.prefix + ':' + self.localName

    property prefix:
        def __get__(self):
            if self._c_node.ns is NULL or self._c_node.ns.prefix is NULL:
                return None
            return unicode(self._c_node.ns.prefix, 'UTF-8')

    property parentNode:
        def __get__(self):
            return _nodeFactory(self._doc, self._c_node.parent)

    property firstChild:
        def __get__(self):
            return _nodeFactory(self._doc, self._c_node.children)
        
    property lastChild:
        def __get__(self):
            return _nodeFactory(self._doc, self._c_node.last)

    property previousSibling:
        def __get__(self):
            return _nodeFactory(self._doc, self._c_node.prev)

    property nextSibling:
        def __get__(self):
            return _nodeFactory(self._doc, self._c_node.next)

    property ownerDocument:
        def __get__(self):
            # XXX if this node has just be created this isn't valid
            # XXX but we're a read-only DOM for now
            return self._doc
    
cdef _elementFactory(Document doc, xmlNode* c_node):
    cdef Element result
    result = Element()
    result._doc = doc
    result._c_node = c_node
    return result
    
cdef class NodeList(_NodeBase):
    def __getitem__(self, index):
        cdef xmlNode* c_node
        c_node = self._c_node.children
        c = 0
        while c_node is not NULL:
            if c == index:
                return _nodeFactory(self._doc, c_node)
            c = c + 1
            c_node = c_node.next
        else:
            raise IndexError

cdef _nodeListFactory(Document doc, xmlNode* c_node):
    cdef NodeList result
    result = NodeList()
    result._doc = doc
    result._c_node = c_node
    return result

cdef _nodeFactory(Document doc, xmlNode* c_node):
    if c_node is NULL:
        return None
    if c_node.type == 1: # ELEMENT_NODE
        return _elementFactory(doc, c_node)
    
def makeDocument(text):
    cdef xmlDoc* c_doc
    c_doc = xmlParseDoc(text)
    return _documentFactory(c_doc)
