"""
DOM implementation on top of libxml.

Read-only for starters.
"""

from tree cimport xmlDoc, xmlNode, xmlAttr, xmlNs
cimport tree
from parser cimport xmlParseDoc
import nodereg
cimport nodereg

cdef class Node
cdef class Document(Node)

cdef class _RefBase:
    cdef xmlNode* _c_node
    cdef Document _doc
    
    def _getDoc(self):
        return self._doc

cdef class Node:
    cdef xmlNode* _c_node
    
    def _getDoc(self):
        return self._doc

    property ELEMENT_NODE:
        def __get__(self):
            return tree.XML_ELEMENT_NODE

    property ATTRIBUTE_NODE:
        def __get__(self):
            return tree.XML_ATTRIBUTE_NODE

    property COMMENT_NODE:
        def __get__(self):
            return tree.XML_COMMENT_NODE
        
    property TEXT_NODE:
        def __get__(self):
            return tree.XML_TEXT_NODE

    property DOCUMENT_NODE:
        def __get__(self):
            return tree.XML_DOCUMENT_NODE

    def __cmp__(Node self, Node other):
        # XXX this is fishy, should return negative, 0, larger
        if self._c_node is other._c_node:
            return 0
        else:
            return 1

    def isSameNode(Node self, Node other):
        return self.__cmp__(other) == 0

    property childNodes:
        def __get__(self):
            return _nodeListFactory(self._getDoc(), self._c_node)

    property parentNode:
        def __get__(self):
            return _nodeFactory(self._getDoc(), self._c_node.parent)

    property firstChild:
        def __get__(self):
            return _nodeFactory(self._getDoc(), self._c_node.children)
        
    property lastChild:
        def __get__(self):
            return _nodeFactory(self._getDoc(), self._c_node.last)

    property previousSibling:
        def __get__(self):
            return _nodeFactory(self._getDoc(), self._c_node.prev)

    property nextSibling:
        def __get__(self):
            return _nodeFactory(self._getDoc(), self._c_node.next)

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

    property textContent:
        def __get__(self):
            None

    def hasAttributes(self):
        return False

    def hasChildNodes(self):
        return self._c_node.children is not NULL

    def lookupNamespaceURI(self, prefix):
        cdef xmlNs* ns
        cdef char* p
        cdef Document doc
        if prefix is None:
            p = NULL
        else:
            p = prefix
        doc = self._getDoc()
        ns = tree.xmlSearchNs(<xmlDoc*>(doc._c_node), self._c_node, p)
        if ns is NULL:
            return None
        return unicode(ns.href, 'UTF-8')

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
        tree.xmlFreeDoc(<xmlDoc*>self._c_node)

    property nodeType:
        def __get__(self):
            return tree.XML_DOCUMENT_NODE
        
    property ownerDocument:
        def __get__(self):
            return None

    property nodeName:
        def __get__(self):
            return '#document'

    property documentElement:
        def __get__(self):
            cdef xmlNode* c_node
            c_node = self._c_node.children
            while c_node is not NULL:
                if c_node.type == tree.XML_ELEMENT_NODE:
                    return _elementFactory(self, c_node)
                c_node = c_node.next
            return None

    property textContent:
        def __get__(self):
            return None
        
    def lookupNamespaceURI(self, prefix):
        return self.documentElement.lookupNamespaceURI(prefix)
    
    # XXX tbd
    def createExpression(self, expression, resolver):
        pass

    def createNSResolver(self, Node nodeResolver):
        return _xpathNSResolverFactory(self, nodeResolver._c_node)

    def evaluate(self, expression, contextNode,
                 resolver, type, result):
        pass
    
cdef Document _documentFactory(xmlDoc* c_doc):
    cdef Document doc
    doc = Document()
    doc._c_node = <xmlNode*>c_doc
    return doc

cdef class XPathNSResolver(_RefBase):
    def lookupNamespaceURI(self, prefix):
        cdef xmlNs* ns
        cdef Document doc
        doc = self._getDoc()
        ns = tree.xmlSearchNs(<xmlDoc*>(doc._c_node), self._c_node, prefix)
        if ns is NULL:
            return None
        return unicode(ns.href, 'UTF-8')
        
cdef XPathNSResolver _xpathNSResolverFactory(Document doc, xmlNode* c_node):
    cdef XPathNSResolver result
    result = XPathNSResolver()
    result._doc = doc
    result._c_node = c_node
    return result
    
cdef class ElementAttrNode(NonDocNode):
    property nodeName:
        def __get__(self):
            if self.prefix is None:
                return self.localName
            else:
                return self.prefix + ':' + self.localName

    property localName:
        def __get__(self):
            return unicode(self._c_node.name, 'UTF-8')

    property prefix:
        def __get__(self):
            if self._c_node.ns is NULL or self._c_node.ns.prefix is NULL:
                return None
            return unicode(self._c_node.ns.prefix, 'UTF-8')

    property namespaceURI:
        def __get__(self):
            if self._c_node.ns is NULL or self._c_node.ns.href is NULL:
                return None
            return unicode(self._c_node.ns.href, 'UTF-8')

    property textContent:
        def __get__(self):
            result = []
            for node in self.childNodes:
                nt = node.nodeType
                if (nt == tree.XML_COMMENT_NODE or
                    nt == tree.XML_PI_NODE):
                    continue
                result.append(node.textContent)
            return ''.join(result)
            
cdef class Element(ElementAttrNode):

    property nodeType:
        def __get__(self):
            return tree.XML_ELEMENT_NODE
                
    property tagName:
        def __get__(self):
            return self.nodeName

    property attributes:
        def __get__(self):
            return _namedNodeMapFactory(self._getDoc(), self._c_node)

    def hasAttributes(self):
        return self._c_node.properties is not NULL

    def getAttributeNS(self, namespaceURI, localName):
        cdef char* value
        cdef char* nsuri
        if namespaceURI is None:
            nsuri = NULL
        else:
            nsuri = namespaceURI
        # this doesn't have the ns bug, unlike xmlHasNsProp
        value = tree.xmlGetNsProp(self._c_node, localName, nsuri)
        if value is NULL:
            return ''
        result = unicode(value, 'UTF-8')
        tree.xmlFree(value)
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
        value = tree.xmlGetNsProp(self._c_node, localName, nsuri)
        result = value is not NULL
        if result:
            tree.xmlFree(value)
        return result
    
cdef _elementFactory(Document doc, xmlNode* c_node):
    cdef Element result
    result = Element()
    result._doc = doc
    result._c_node = c_node
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
            return tree.XML_ATTRIBUTE_NODE
        
    property name:
        def __get__(self):
            return self.nodeName
        
    property ownerElement:
        def __get__(self):
            return _nodeFactory(self._getDoc(), self._c_node.parent)

    property value:
        def __get__(self):
            cdef char* content
            content = tree.xmlNodeGetContent(self._c_node)
            if content is NULL:
                return ''
            result = unicode(content, 'UTF-8')
            tree.xmlFree(content)
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
    result._c_node = c_node
    return result

cdef class CharacterData(NonDocNode):
    property nodeType:
        def __get__(self):
            return tree.XML_TEXT_NODE 

    property data:
        def __get__(self):
            return unicode(self._c_node.content, "UTF-8")

    property length:
        def __get__(self):
            return len(self.data)

    property nodeValue:
        def __get__(self):
            return self.data

    property textContent:
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
    result._c_node = c_node
    return result

cdef class Comment(CharacterData):
    property nodeName:
        def __get__(self):
            return '#comment'

    property nodeType:
        def __get__(self):
            return tree.XML_COMMENT_NODE
        
cdef _commentFactory(Document doc, xmlNode* c_node):
    cdef Comment result
    result = Comment()
    result._doc = doc
    result._c_node = c_node
    return result

cdef class NodeList(_RefBase):
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

    def __iter__(self):
        return _nodeListIteratorFactory(self._doc, self._c_node.children)
    
    def item(self, index):
        try:
            return self.__getitem__(index)
        except IndexError:
            return None

    property length:
        def __get__(self):
            cdef xmlNode* c_node
            c_node = self._c_node.children
            c = 0
            while c_node is not NULL:
                c = c + 1
                c_node = c_node.next
            return c
        
cdef _nodeListFactory(Document doc, xmlNode* c_node):
    cdef NodeList result
    result = NodeList()
    result._doc = doc
    result._c_node = c_node
    return result

cdef class _NodeListIterator(_RefBase):
    def __next__(self):
        cdef xmlNode* c_node
        c_node = self._c_node
        if c_node is not NULL:
            self._c_node = c_node.next
            return _nodeFactory(self._doc, c_node)
        else:
            raise StopIteration
    
cdef _NodeListIterator _nodeListIteratorFactory(Document doc, xmlNode* c_node):
    cdef _NodeListIterator result
    result = _NodeListIterator()
    result._doc = doc
    result._c_node = c_node
    return result

cdef class NamedNodeMap(_RefBase):
    def __iter__(self):
        return _namedNodeMapIteratorFactory(
            self._doc, <xmlNode*>self._c_node.properties)
    
##     def getNamedItem(self, name):
##         cdef xmlAttr* c_node
##         c_node = xmlHasProp(self._c_node, name)
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
        value = tree.xmlGetNsProp(self._c_node, localName, nsuri)
        if value is NULL:
            return None
        tree.xmlFree(value)
        
        c_node = tree.xmlHasNsProp(self._c_node, localName, nsuri)
        if c_node is NULL:
            return None
        return _attrFactory(self._doc, <xmlNode*>c_node)
    
    def item(self, index):
        cdef xmlNode* c_node
        c_node = <xmlNode*>self._c_node.properties
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
    result._c_node = c_node
    return result

cdef class _NamedNodeMapIterator(_RefBase):
    def __next__(self):
        cdef xmlNode* c_node
        c_node = self._c_node
        if c_node is not NULL:
            self._c_node = c_node.next
            return _nodeFactory(self._doc, c_node)
        else:
            raise StopIteration
    
cdef _NamedNodeMapIterator _namedNodeMapIteratorFactory(Document doc,
                                                        xmlNode* c_node):
    cdef _NamedNodeMapIterator result
    result = _NamedNodeMapIterator()
    result._doc = doc
    result._c_node = c_node
    return result

cdef _nodeFactory(Document doc, xmlNode* c_node):
    if c_node is NULL:
        return None
    elif c_node.type == tree.XML_ELEMENT_NODE:
        return _elementFactory(doc, c_node)
    elif c_node.type == tree.XML_TEXT_NODE:
        return _textFactory(doc, c_node)
    elif c_node.type == tree.XML_ATTRIBUTE_NODE:
        return _attrFactory(doc, c_node)
    elif c_node.type == tree.XML_COMMENT_NODE:
        return _commentFactory(doc, c_node)
    elif c_node.type == tree.XML_DOCUMENT_NODE:
        return doc
    
def makeDocument(text):
    cdef xmlDoc* c_doc
    c_doc = xmlParseDoc(text)
    return _documentFactory(c_doc)
   
