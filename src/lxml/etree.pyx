cimport tree
from tree cimport xmlDoc, xmlNode
cimport xmlparser
from xmlparser cimport xmlParserCtxt, xmlDict

import sys

import nodereg
cimport nodereg

PROXY_ATTRIB = 1
PROXY_ATTRIB_ITER = 2
PROXY_ELEMENT_ITER = 3

# the rules
# any libxml C argument/variable is prefixed with c_
# any non-public function/class is prefixed with an underscore
# instance creation is always through factories

cdef nodereg.NodeRegistry node_registry
node_registry = nodereg.NodeRegistry()

cdef class _DocumentBase(nodereg.SimpleDocumentProxyBase):
    """Base class to reference a libxml document.

    When instances of this class are garbage collected, the libxml
    document is cleaned up.
    """
    def getProxy(self, id, proxy_type=0):
        return node_registry.getProxy(id, proxy_type)

    def registerProxy(self, nodereg.SimpleNodeProxyBase proxy, proxy_type=0):
        node_registry.registerProxy(proxy, proxy_type)

    def unregisterProxy(self, nodereg.SimpleNodeProxyBase proxy, proxy_type=0):
        node_registry.unregisterProxy(proxy, proxy_type)

    def getProxies(self):
        return node_registry._proxies
        
    def __dealloc__(self):
        # if there are no more references to the document, it is safe
        # to clean the whole thing up, as all nodes have a reference to
        # the document
        #print "freeing document:", <int>self._c_doc
        #displayNode(<xmlNode*>self._c_doc, 0)
        #print self._c_doc.dict is theParser._c_dict
        tree.xmlFreeDoc(self._c_doc)
        #print "dune"

# to help with debugging
cdef void displayNode(xmlNode* c_node, indent):
    cdef xmlNode* c_child
    print indent * ' ', <int>c_node
    c_child = c_node.children
    while c_child is not NULL:
        displayNode(c_child, indent + 1)
        c_child = c_child.next
        
cdef class _NodeBase(nodereg.SimpleNodeProxyBase):
    """Base class to reference a document object and a libxml node.

    By pointing to an ElementTree instance, a reference is kept to
    _ElementTree as long as there is some pointer to a node in it.
    """
    def __dealloc__(self):
        #print "trying to free node:", <int>self._c_node
        # displayNode(self._c_node, 0)
        node_registry.attemptDeallocation(self._c_node)
        
cdef class _ElementTreeBase(_DocumentBase):
    def getroot(self):
        cdef xmlNode* c_node
        c_node = tree.xmlDocGetRootElement(self._c_doc)
        if c_node is NULL:
            return # return None
        return _elementFactory(self, c_node)
    
    def write(self, file, encoding='us-ascii'):
        # XXX dumping to memory first is definitely not the most efficient
        cdef char* mem
        cdef int size
        tree.xmlDocDumpMemory(self._c_doc, &mem, &size)
        if encoding in ('UTF-8', 'utf8', 'UTF8', 'utf-8'):
            file.write(mem)
        else:
            file.write(unicode(mem, 'UTF-8').encode(encoding))
        tree.xmlFree(mem)

class _ElementTree(_ElementTreeBase):
    __slots__ = ['__weakref__']
    
cdef _ElementTreeBase _elementTreeFactory(xmlDoc* c_doc):
    cdef _ElementTreeBase result
    result = _ElementTree()
    result._c_doc = c_doc
    return result

cdef class _ElementBase(_NodeBase):
    # MANIPULATORS
    def set(self, key, value):
        self.attrib[key] = value
        
    def append(self, _ElementBase element):
        cdef xmlNode* c_next
        cdef xmlNode* c_next2
        # store possible text node
        c_next = element._c_node.next
        # XXX what if element is coming from a different document?
        tree.xmlUnlinkNode(element._c_node)
        # move node itself
        tree.xmlAddChild(self._c_node, element._c_node)
        # tail support: look for any text nodes trailing this node and
        # move them too
        while c_next is not NULL and c_next.type == tree.XML_TEXT_NODE:
            c_next2 = c_next.next
            tree.xmlUnlinkNode(c_next)
            tree.xmlAddChild(self._c_node, c_next)
            c_next = c_next2
        # uh oh, elements may be pointing to different doc when
        # parent element has moved; change them too..
        node_registry.changeDocumentBelow(element, self._doc)

    # PROPERTIES
    property tag:
        def __get__(self):
            return unicode(self._c_node.name, 'UTF-8')

    property attrib:
        def __get__(self):
            return _attribFactory(self._doc, self._c_node)
        
    property text:
        def __get__(self):
            cdef xmlNode* c_node
            return _collectText(self._c_node.children)
        
        def __set__(self, value):
            cdef xmlNode* c_text_node
            # remove all text nodes at the start first
            while 1:
                c_text_node = self._c_node.children
                if (c_text_node is NULL or
                    c_text_node.type != tree.XML_TEXT_NODE):
                    break
                tree.xmlUnlinkNode(c_text_node)
                tree.xmlFreeNode(c_text_node)
            text = value.encode('UTF-8')
            # now add new text node with value at start
            c_text_node = tree.xmlNewDocText(self._doc._c_doc,
                                             text)
            if self._c_node.children is NULL:
                tree.xmlAddChild(self._c_node, c_text_node)
            else:
                tree.xmlAddPrevSibling(self._c_node.children,
                                       c_text_node)
        
    property tail:
        def __get__(self):
            cdef xmlNode* c_node
            return _collectText(self._c_node.next)
           
        def __set__(self, value):
            cdef xmlNode* c_node
            cdef xmlNode* c_text_node
            text = value.encode('UTF-8')
            c_text_node = tree.xmlNewDocText(self._doc._c_doc, text)
            # XXX what if we're the top element?
            tree.xmlAddNextSibling(self._c_node, c_text_node)
                
    # ACCESSORS
    def __getitem__(self, n):
        cdef xmlNode* c_node
        c_node = self._c_node.children
        c = 0
        while c_node is not NULL:
            if c_node.type == tree.XML_ELEMENT_NODE:
                if c == n:
                    return _elementFactory(self._doc, c_node)
                c = c + 1
            c_node = c_node.next
        else:
            raise IndexError

    def __setitem__(self, index, nodereg.SimpleNodeProxyBase element):
        cdef xmlNode* c_node
        assert iselement(element)
        c_node = self._c_node.children
        c = 0
        while c_node is not NULL:
            if c_node.type == tree.XML_ELEMENT_NODE:
                if c == index:
                    tree.xmlReplaceNode(c_node, element._c_node)
                    node_registry.changeDocumentBelow(element, self._doc)
                c = c + 1
            c_node = c_node.next
        else:
            raise IndexError
    
    def __len__(self):
        cdef int c
        cdef xmlNode* c_node
        c = 0
        c_node = self._c_node.children
        while c_node is not NULL:
            if c_node.type == tree.XML_ELEMENT_NODE:
                c = c + 1
            c_node = c_node.next
        return c

    def __iter__(self):
        return _elementIteratorFactory(self._doc, self._c_node.children)
    
    def get(self, key, default=None):
        return self.attrib.get(key, default)

    def keys(self):
        return self.attrib.keys()

    def items(self):
        return self.attrib.items()

class _Element(_ElementBase):
    __slots__ = ['__weakref__']
    
cdef _ElementBase _elementFactory(_ElementTreeBase etree, xmlNode* c_node):
    cdef _ElementBase result
    result = etree.getProxy(<int>c_node)
    if result is not None:
        return result
    if c_node is NULL:
        return None
    result = _Element()
    result._doc = etree
    result._c_node = c_node
    etree.registerProxy(result)
    return result

cdef class _CommentBase(_ElementBase):
    def set(self, key, value):
        pass
    
    def append(self, _ElementBase element):
        pass

    property tag:
        def __get__(self):
            return None
        
    property attrib:
        def __get__(self):
            return {}
        
    property text:
        def __get__(self):
            return unicode(self._c_node.content, 'UTF-8')

        def __set__(self, value):
            pass
                        
    # ACCESSORS
    def __getitem__(self, n):
        raise IndexError

    def __len__(self):
        return 0

    def get(self, key, default=None):
        return None

    def keys(self):
        return []
    
    def items(self):
        return []
    
class _Comment(_CommentBase):
    __slots__ = ['__weakref__']

cdef _CommentBase _commentFactory(_ElementTreeBase etree, xmlNode* c_node):
    cdef _CommentBase result
    result = etree.getProxy(<int>c_node)
    if result is not None:
        return result
    if c_node is NULL:
        return None
    result = _Comment()
    result._doc = etree
    result._c_node = c_node
    etree.registerProxy(result)
    return result

cdef class _AttribBase(_NodeBase):
    # MANIPULATORS
    def __setitem__(self, key, value):
        key = key.encode('UTF-8')
        value = value.encode('UTF-8')
        tree.xmlSetProp(self._c_node, key, value)

    # ACCESSORS
    def __getitem__(self, key):
        cdef char* result
        key = key.encode('UTF-8')
        result = tree.xmlGetNoNsProp(self._c_node, key)
        if result is NULL:
            raise KeyError, key
        return unicode(result, 'UTF-8')

    def __len__(self):
        cdef int c
        cdef xmlNode* c_node
        c = 0
        c_node = <xmlNode*>(self._c_node.properties)
        while c_node is not NULL:
            if c_node.type == tree.XML_ATTRIBUTE_NODE:
                c = c + 1
            c_node = c_node.next
        return c
    
    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def __iter__(self):
        return _attribIteratorFactory(self._doc,
                                      <xmlNode*>self._c_node.properties)
    
    def keys(self):
        result = []
        cdef xmlNode* c_node
        c_node = <xmlNode*>(self._c_node.properties)
        while c_node is not NULL:
            if c_node.type == tree.XML_ATTRIBUTE_NODE:
                result.append(unicode(c_node.name, 'UTF-8'))
            c_node = c_node.next
        return result

    def values(self):
        result = []
        cdef xmlNode* c_node
        c_node = <xmlNode*>(self._c_node.properties)
        while c_node is not NULL:
            if c_node.type == tree.XML_ATTRIBUTE_NODE:
                result.append(
                    unicode(tree.xmlGetNoNsProp(self._c_node, c_node.name), 'UTF-8')
                    )
            c_node = c_node.next
        return result
        
    def items(self):
        result = []
        cdef xmlNode* c_node
        c_node = <xmlNode*>(self._c_node.properties)
        while c_node is not NULL:
            if c_node.type == tree.XML_ATTRIBUTE_NODE:
                result.append((
                    unicode(c_node.name, 'UTF-8'),
                    unicode(tree.xmlGetNoNsProp(self._c_node, c_node.name), 'UTF-8')
                    ))
            c_node = c_node.next
        return result

class _Attrib(_AttribBase):
    __slots__ = ['__weakref__']
    
cdef _AttribBase _attribFactory(_ElementTreeBase etree, xmlNode* c_node):
    cdef _AttribBase result
    result = etree.getProxy(<int>c_node, PROXY_ATTRIB)
    if result is not None:
        return result
    result = _Attrib()
    result._doc = etree
    result._c_node = c_node
    etree.registerProxy(result, PROXY_ATTRIB)
    return result

cdef class _AttribIteratorBase(_NodeBase):
    def __next__(self):
        cdef xmlNode* c_node
        c_node = self._c_node
        while c_node is not NULL:
            if c_node.type ==tree.XML_ATTRIBUTE_NODE:
                break
            c_node = c_node.next
        else:
            raise StopIteration
        self._doc.unregisterProxy(self, PROXY_ATTRIB_ITER)
        self._c_node = c_node.next
        self._doc.registerProxy(self, PROXY_ATTRIB_ITER)
        return unicode(c_node.name, 'UTF-8')

class _AttribIterator(_AttribIteratorBase):
    __slots__ = ['__weakref__']
    
cdef _AttribIteratorBase _attribIteratorFactory(_ElementTreeBase etree,
                                                xmlNode* c_node):
    cdef _AttribIteratorBase result
    result = etree.getProxy(<int>c_node, PROXY_ATTRIB_ITER)
    if result is not None:
        return result
    result = _AttribIterator()
    result._doc = etree
    result._c_node = c_node
    etree.registerProxy(result, PROXY_ATTRIB_ITER)
    return result

cdef class _ElementIteratorBase(_NodeBase):
    def __next__(self):
        cdef xmlNode* c_node
        c_node = self._c_node
        while c_node is not NULL:
            if c_node.type == tree.XML_ELEMENT_NODE:
                break
            c_node = c_node.next
        else:
            raise StopIteration
        self._doc.unregisterProxy(self, PROXY_ELEMENT_ITER)
        self._c_node = c_node.next
        self._doc.registerProxy(self, PROXY_ELEMENT_ITER)
        return _elementFactory(self._doc, c_node)

class _ElementIterator(_ElementIteratorBase):
    __slots__ = ['__weakref__']
    
cdef _ElementIteratorBase _elementIteratorFactory(_ElementTreeBase etree,
                                                  xmlNode* c_node):
    cdef _ElementIteratorBase result
    result = etree.getProxy(<int>c_node, PROXY_ELEMENT_ITER)
    if result is not None:
        return result
    result = _ElementIterator()
    result._doc = etree
    result._c_node = c_node
    etree.registerProxy(result, PROXY_ELEMENT_ITER)
    return result

cdef xmlNode* _createElement(xmlDoc* c_doc, char* tag,
                             object attrib, object extra):
    cdef xmlNode* c_node
    if attrib is None:
        attrib = {}
    attrib.update(extra)
    c_node = tree.xmlNewDocNode(c_doc, NULL, tag, NULL)
    for name, value in attrib.items():
        tree.xmlNewProp(c_node, name, value)
    return c_node

cdef xmlNode* _createComment(xmlDoc* c_doc, char* text):
    cdef xmlNode* c_node
    c_node = tree.xmlNewDocComment(c_doc, text)
    return c_node

def Element(tag, attrib=None, **extra):
    cdef xmlNode* c_node
    cdef _ElementTreeBase etree

    etree = ElementTree()
    c_node = _createElement(etree._c_doc, tag, attrib, extra)
    tree.xmlDocSetRootElement(etree._c_doc, c_node)
    return _elementFactory(etree, c_node)

def Comment(text=None):
    cdef xmlNode* c_node
    cdef _ElementTreeBase etree
    if text is None:
        text = ''
    text = ' %s ' % text
    etree = ElementTree()
    c_node = _createComment(etree._c_doc, text)
    tree.xmlAddChild(<xmlNode*>etree._c_doc, c_node)
    return _commentFactory(etree, c_node)

def SubElement(_ElementBase parent, tag, attrib=None, **extra):
    cdef xmlNode* c_node
    cdef _ElementBase element
    c_node = _createElement(parent._doc._c_doc, tag, attrib, extra)
    element = _elementFactory(parent._doc, c_node)
    parent.append(element)
    return element

def ElementTree(_ElementBase element=None, file=None):
    cdef xmlDoc* c_doc
    cdef xmlNode* c_node
    cdef xmlNode* c_node_copy
    cdef _ElementTreeBase etree
    
    if file is not None:
        # XXX read XML into memory not the fastest way to do this
        data = file.read()
        c_doc = theParser.parseDoc(data)
    else:
        c_doc = theParser.newDoc()

    etree = _elementTreeFactory(c_doc)

    # XXX what if element and file are both not None?
    if element is not None:
        tree.xmlDocSetRootElement(etree._c_doc, element._c_node)
        element._doc = etree
    
    return etree

cdef class Parser:

    cdef xmlDict* _c_dict

    def __init__(self):
        self._c_dict = NULL

    def __del__(self):
        #print "cleanup parser"
        if self._c_dict is not NULL:
            #print "freeing dictionary (cleanup parser)"
            xmlparser.xmlDictFree(self._c_dict)
        
    cdef xmlDoc* parseDoc(self, text):
        """Parse document, share dictionary if possible.
        """
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        #print "parseDoc"
        
        xmlparser.xmlInitParser()
        pctxt = xmlparser.xmlCreateDocParserCtxt(text)

        if self._c_dict is not NULL and pctxt.dict is not NULL:
            #print "sharing dictionary (parseDoc)"
            xmlparser.xmlDictFree(pctxt.dict)
            pctxt.dict = self._c_dict
            xmlparser.xmlDictReference(pctxt.dict)

        # parse with the following options
        # * substitute entities
        # * no network access
        # * no cdata nodes
        xmlparser.xmlCtxtUseOptions(
            pctxt,
            xmlparser.XML_PARSE_NOENT |
            xmlparser.XML_PARSE_NOCDATA)

        xmlparser.xmlParseDocument(pctxt)

        if pctxt.wellFormed:
            result = pctxt.myDoc

            # store dict of last object parsed if no shared dict yet
            if self._c_dict is NULL:
                #print "storing shared dict"
                self._c_dict = result.dict
                xmlparser.xmlDictReference(self._c_dict)
        else:
            result = NULL
            if pctxt.myDoc is not NULL:
                tree.xmlFreeDoc(pctxt.myDoc)
            pctxt.myDoc = NULL
        xmlparser.xmlFreeParserCtxt(pctxt)

        return result

    cdef xmlDoc* newDoc(self):
        cdef xmlDoc* result
        #print "newDoc"
        #if result.dict is NULL:
        #    print "result.dict is NULL (!)"

        result = tree.xmlNewDoc("1.0")
        if result.dict is not NULL:
            #print "freeing dictionary (newDoc)"
            xmlparser.xmlDictFree(result.dict)
            
        if self._c_dict is not NULL:
            #print "sharing dictionary (newDoc)"
            result.dict = self._c_dict
            xmlparser.xmlDictReference(self._c_dict)
            
        if self._c_dict is NULL:
            #print "add dictionary reference (newDoc)"
            self._c_dict = result.dict
            xmlparser.xmlDictReference(self._c_dict)
        return result
    
# globally shared parser
cdef Parser theParser
theParser = Parser()
    
def XML(text):
    cdef xmlDoc* c_doc
    c_doc = theParser.parseDoc(text)
    return _elementTreeFactory(c_doc).getroot()

fromstring = XML

def iselement(element):
    return isinstance(element, _ElementBase)

def dump(nodereg.SimpleNodeProxyBase elem):
    _dumpToFile(sys.stdout, elem._doc._c_doc, elem._c_node)

cdef _dumpToFile(f, xmlDoc* c_doc, xmlNode* c_node):
    cdef tree.PyFileObject* o
    cdef tree.xmlOutputBuffer* c_buffer
    cdef xmlNode* c_next
    
    if not tree.PyFile_Check(f):
        raise ValueError, "Not a file"
    o = <tree.PyFileObject*>f
    c_buffer = tree.xmlOutputBufferCreateFile(tree.PyFile_AsFile(o), NULL)
    tree.xmlNodeDumpOutput(c_buffer, c_doc, c_node, 0, 0, NULL)
    # dump next node if it's a text node
    c_next = c_node.next
    if not (c_next is not NULL and c_next.type == tree.XML_TEXT_NODE):
        c_next = NULL
    if c_next is not NULL:
        tree.xmlNodeDumpOutput(c_buffer, c_doc, c_next, 0, 0, NULL)
    tree.xmlOutputBufferWriteString(c_buffer, '\n')
    tree.xmlOutputBufferFlush(c_buffer)
    
cdef _collectText(xmlNode* c_node):
    """Collect all text nodes and return them as a unicode string.
    If there was no text to collect, return None
    """
    result = ''
    while c_node is not NULL and c_node.type == tree.XML_TEXT_NODE:
        result = result + c_node.content
        c_node = c_node.next
    if result:
        return unicode(result, 'UTF-8')
    else:
        return None
            
