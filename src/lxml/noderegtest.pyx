# this is a test module which sets up some concrete classes and
# factories so it is possible to test the use of the nodereg module

from tree cimport xmlNode, xmlDoc
cimport tree

cdef extern from "libxml/parser.h":
    cdef xmlDoc* xmlParseFile(char* filename)
    cdef xmlDoc* xmlParseDoc(char* cur)

import nodereg
cimport nodereg

class DOMError(Exception):
    pass

cdef class DocumentBase(nodereg.DocumentProxyBase):

    property documentElement:
        def __get__(self):
            cdef xmlNode* c_node
            c_node = self._c_doc.children
            while c_node is not NULL:
                if c_node.type == tree.XML_ELEMENT_NODE:
                    return _elementFactory(self, c_node)
                c_node = c_node.next
            return None

    def createElementNS(self, namespaceURI, qualifiedName):
        cdef xmlNode* c_node
        c_node = tree.xmlNewDocNode(self._c_doc, NULL, qualifiedName, NULL)
        return _elementFactory(self, c_node)
        
class Document(DocumentBase):
    __slots__ = ['__weakref__']

cdef _documentFactory(xmlDoc* c_doc):
    cdef DocumentBase result
    result = Document()
    result._c_doc = c_doc
    return result
    
cdef object _nodeFactory(DocumentBase doc, xmlNode* c_node):
    if c_node is NULL:
        return None
    elif c_node.type == tree.XML_ELEMENT_NODE:
        return _elementFactory(doc, c_node)
    elif c_node.type == tree.XML_DOCUMENT_NODE:
        return doc
    
cdef class Node(nodereg.NodeProxyBase):

    def getFirstChild(self):
        return _nodeFactory(self._doc, self._c_node.children)
    
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
        
cdef class ElementBase(Node):
        
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

    def appendChild(self, Node newChild):
        if newChild._c_node.parent is not NULL:
            self.removeChild(newChild)
        if self is newChild:
            raise DOMError # HIERARCHY_REQUEST_ERR
        tree.xmlAddChild(self._c_node, newChild._c_node)
        return newChild

    def removeChild(self, Node oldChild):
        if oldChild._c_node.parent is not self._c_node:
            raise DOMError # NOT_FOUND_ERR
        tree.xmlUnlinkNode(oldChild._c_node)
        return oldChild
    
class Element(ElementBase):
    __slots__ = ['__weakref__']
    
cdef _elementFactory(DocumentBase doc, xmlNode* c_node):
    cdef ElementBase result
    result = doc.getProxy(<int>c_node)
    if result is not None:
        # print "returning proxy:", result.nodeName
        return result
    result = Element()
    result._doc = doc
    result._c_node = c_node
    # print "regi proxy:", result.nodeName
    doc.registerProxy(result)
    return result   

def makeDocument(text):
    """Construct a document from some xml.
    """
    cdef xmlDoc* c_doc
    c_doc = xmlParseDoc(text)
    return _documentFactory(c_doc)
