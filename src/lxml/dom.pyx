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
 
    cdef void xmlFreeDoc(xmlDoc *cur)
    cdef xmlNode* xmlNewNode(xmlNs* ns, char* name)
    cdef xmlNode* xmlAddChild(xmlNode* parent, xmlNode* cur)
    cdef xmlNode* xmlNewDocNode(xmlDoc* doc, xmlNs* ns,
                                char* name, char* content)
    cdef xmlDoc* xmlNewDoc(char* version)
    cdef xmlAttr* xmlNewProp(xmlNode* node, char* name, char* value)
    cdef char* xmlGetNoNsProp(xmlNode* node, char* name)
    cdef char* xmlGetNsProp(xmlNode* node, char* name, char* nameSpace)
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
    cdef xmlAttr* xmlHasProp(xmlNode* node, char* name)
    cdef xmlAttr* xmlHasNsProp(xmlNode* node, char* name, char* nameSpace)
    cdef char* xmlNodeGetContent(xmlNode* cur)
    
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
            return XML_ELEMENT_NODE

    property ATTRIBUTE_NODE:
        def __get__(self):
            return XML_ATTRIBUTE_NODE

    property COMMENT_NODE:
        def __get__(self):
            return XML_COMMENT_NODE
        
    property TEXT_NODE:
        def __get__(self):
            return XML_TEXT_NODE

    property DOCUMENT_NODE:
        def __get__(self):
            return XML_DOCUMENT_NODE

    def __cmp__(Node self, Node other):
        # XXX this is fishy, should return negative, 0, larger
        if self._o is other._o:
            return 0
        else:
            return 1

    def isSameNode(Node self, Node other):
        return self.__cmp__(other) == 0

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

    property attributes:
        def __get__(self):
            return None

    property nodeValue:
        def __get__(self):
            return None

    property localName:
        def __get__(self):
            return None

    property namespaceURI:
        def __get__(self):
            return None

    property prefix:
        def __get__(self):
            return None

    def hasAttributes(self):
        return False

    def hasChildNodes(self):
        return self._o.children is not NULL
    
cdef class NonDocNode(Node):
    cdef Document _doc
    
    def _getDoc(self):
        return self._doc

    property ownerDocument:
        def __get__(self):
            # XXX if this node has just been created this isn't valid
            # XXX but we're a read-only DOM for now
            return self._getDoc()

cdef class Document(Node):
    def _getDoc(self):
        return self
    
    def __dealloc__(self):
        xmlFreeDoc(<xmlDoc*>self._o)

    property nodeType:
        def __get__(self):
            return XML_DOCUMENT_NODE
        
    property ownerDocument:
        def __get__(self):
            return None

    property nodeName:
        def __get__(self):
            return '#document'

    property documentElement:
        def __get__(self):
            cdef xmlNode* c_node
            c_node = self._o.children
            while c_node is not NULL:
                if c_node.type == XML_ELEMENT_NODE:
                    return _elementFactory(self, c_node)
                c_node = c_node.next
            return None
        
cdef Document _documentFactory(xmlDoc* c_doc):
    cdef Document doc
    doc = Document()
    doc._o = <xmlNode*>c_doc
    return doc


cdef class ElementAttrNode(NonDocNode):
    property nodeName:
        def __get__(self):
            if self.prefix is None:
                return self.localName
            else:
                return self.prefix + ':' + self.localName

    property localName:
        def __get__(self):
            return unicode(self._o.name, 'UTF-8')

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

cdef class Element(ElementAttrNode):

    property nodeType:
        def __get__(self):
            return XML_ELEMENT_NODE
                
    property tagName:
        def __get__(self):
            return self.nodeName

    property attributes:
        def __get__(self):
            return _namedNodeMapFactory(self._getDoc(), self._o)

    def hasAttributes(self):
        return self._o.properties is not NULL

    def getAttributeNS(self, namespaceURI, localName):
        cdef char* value
        cdef char* nsuri
        if namespaceURI is None:
            nsuri = NULL
        else:
            nsuri = namespaceURI
        # this doesn't have the ns bug, unlike xmlHasNsProp
        value = xmlGetNsProp(self._o, localName, nsuri)
        if value is NULL:
            return ''
        result = unicode(value, 'UTF-8')
        xmlFree(value)
        return result
        
    def getAttributeNodeNS(self, namespaceURI, localName):

        if not self.hasAttributeNS(namespaceURI, localName):
            return None
        return self.attributes.getNamedItemNS(namespaceURI, localName)

    def hasAttributeNS(self, namespaceURI, localName):
        cdef char* value
        cdef char* nsuri
        if namespaceURI is None:
            nsuri = NULL
        else:
            nsuri = namespaceURI
        # XXX cannot use xmlHasNsProp due to bug
        value = xmlGetNsProp(self._o, localName, nsuri)
        result = value is not NULL
        if result:
            xmlFree(value)
        return result
    
cdef _elementFactory(Document doc, xmlNode* c_node):
    cdef Element result
    result = Element()
    result._doc = doc
    result._o = c_node
    return result

cdef class Attr(ElementAttrNode):
    property parentNode:
        def __get__(self):
            return None
    property previousSibling:
        def __get__(self):
            return None
    property nextSibling:
        def __get__(self):
            return None

    property nodeType:
        def __get__(self):
            return XML_ATTRIBUTE_NODE
        
    property name:
        def __get__(self):
            return self.nodeName
        
    property ownerElement:
        def __get__(self):
            return _nodeFactory(self._getDoc(), self._o.parent)

    property value:
        def __get__(self):
            cdef char* content
            content = xmlNodeGetContent(self._o)
            if content is NULL:
                return ''
            result = unicode(content, 'UTF-8')
            xmlFree(content)
            return result

    property nodeValue:
        def __get__(self):
            return self.value

    def hasChildNodes(self):
        return self.value != ''
        
cdef _attrFactory(Document doc, xmlNode* c_node):
    cdef Attr result
    result = Attr()
    result._doc = doc
    result._o = c_node
    return result

cdef class CharacterData(NonDocNode):
    property nodeType:
        def __get__(self):
            return XML_TEXT_NODE 

    property data:
        def __get__(self):
            return unicode(self._o.content, "UTF-8")

    property length:
        def __get__(self):
            return len(self.data)

    property nodeValue:
        def __get__(self):
            return self.data
        
cdef class Text(CharacterData):
    property nodeName:
        def __get__(self):
            return '#text'

cdef _textFactory(Document doc, xmlNode* c_node):
    cdef Text result
    result = Text()
    result._doc = doc
    result._o = c_node
    return result

cdef class Comment(CharacterData):
    property nodeName:
        def __get__(self):
            return '#comment'

    property nodeType:
        def __get__(self):
            return XML_COMMENT_NODE
        
cdef _commentFactory(Document doc, xmlNode* c_node):
    cdef Comment result
    result = Comment()
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
                return _nodeFactory(self._doc, c_node)
            c = c + 1
            c_node = c_node.next
        else:
            raise IndexError

    def __iter__(self):
        return _nodeListIteratorFactory(self._doc, self._o.children)
    
    def item(self, index):
        try:
            return self.__getitem__(index)
        except IndexError:
            return None

    property length:
        def __get__(self):
            cdef xmlNode* c_node
            c_node = self._o.children
            c = 0
            while c_node is not NULL:
                c = c + 1
                c_node = c_node.next
            return c
        
cdef _nodeListFactory(Document doc, xmlNode* c_node):
    cdef NodeList result
    result = NodeList()
    result._doc = doc
    result._o = c_node
    return result

cdef class _NodeListIterator(_RefBase):
    def __next__(self):
        cdef xmlNode* c_node
        c_node = self._o
        if c_node is not NULL:
            self._o = c_node.next
            return _nodeFactory(self._doc, c_node)
        else:
            raise StopIteration
    
cdef _NodeListIterator _nodeListIteratorFactory(Document doc, xmlNode* c_node):
    cdef _NodeListIterator result
    result = _NodeListIterator()
    result._doc = doc
    result._o = c_node
    return result

cdef class NamedNodeMap(_RefBase):
    def __iter__(self):
        return _namedNodeMapIteratorFactory(
            self._doc, <xmlNode*>self._o.properties)
    
##     def getNamedItem(self, name):
##         cdef xmlAttr* c_node
##         c_node = xmlHasProp(self._o, name)
##         if c_node is NULL:
##             return None
##         return _attrFactory(self._doc, <xmlNode*>c_node)
        
    def getNamedItemNS(self, namespaceURI, localName):
        cdef xmlAttr* c_node
        cdef char* nsuri
        cdef char* value
        if namespaceURI is None:
            nsuri = NULL
        else:
            nsuri = namespaceURI
        # XXX big hack relying on xmlGetNsProp to check whether we
        # can get attribute safely, avoiding bug in xmlHasNsProp
        value = xmlGetNsProp(self._o, localName, nsuri)
        if value is NULL:
            return None
        xmlFree(value)
        
        c_node = xmlHasNsProp(self._o, localName, nsuri)
        if c_node is NULL:
            return None
        return _attrFactory(self._doc, <xmlNode*>c_node)
    
    def item(self, index):
        cdef xmlNode* c_node
        c_node = <xmlNode*>self._o.properties
        c = 0
        while c_node is not NULL:
            if c == index:
                return _nodeFactory(self._doc, c_node)
            c = c + 1
            c_node = c_node.next
        else:
            return None

    property length:
        def __get__(self):
            return 0 # XXX fix

cdef _namedNodeMapFactory(Document doc, xmlNode* c_node):
    cdef NamedNodeMap result
    result = NamedNodeMap()
    result._doc = doc
    result._o = c_node
    return result

cdef class _NamedNodeMapIterator(_RefBase):
    def __next__(self):
        cdef xmlNode* c_node
        c_node = self._o
        if c_node is not NULL:
            self._o = c_node.next
            return _nodeFactory(self._doc, c_node)
        else:
            raise StopIteration
    
cdef _NamedNodeMapIterator _namedNodeMapIteratorFactory(Document doc,
                                                        xmlNode* c_node):
    cdef _NamedNodeMapIterator result
    result = _NamedNodeMapIterator()
    result._doc = doc
    result._o = c_node
    return result

cdef _nodeFactory(Document doc, xmlNode* c_node):
    if c_node is NULL:
        return None
    elif c_node.type == XML_ELEMENT_NODE:
        return _elementFactory(doc, c_node)
    elif c_node.type == XML_TEXT_NODE:
        return _textFactory(doc, c_node)
    elif c_node.type == XML_ATTRIBUTE_NODE:
        return _attrFactory(doc, c_node)
    elif c_node.type == XML_COMMENT_NODE:
        return _commentFactory(doc, c_node)
    elif c_node.type == XML_DOCUMENT_NODE:
        return doc
    
def makeDocument(text):
    cdef xmlDoc* c_doc
    c_doc = xmlParseDoc(text)
    return _documentFactory(c_doc)
