cimport tree
from tree cimport xmlDoc, xmlNode, xmlAttr, xmlNs
cimport xmlparser
cimport xpath
cimport xslt
cimport xmlerror
cimport cstd

from xmlparser cimport xmlParserCtxt, xmlDict
import _elementpath
from StringIO import StringIO
import sys

cdef int PROXY_ELEMENT
cdef int PROXY_ATTRIB
cdef int PROXY_ATTRIB_ITER
cdef int PROXY_ELEMENT_ITER

PROXY_ELEMENT = 0
PROXY_ATTRIB = 1
PROXY_ATTRIB_ITER = 2
PROXY_ELEMENT_ITER = 3

NS_COUNTER = 0

# the rules
# any libxml C argument/variable is prefixed with c_
# any non-public function/class is prefixed with an underscore
# instance creation is always through factories


class Error(Exception):
    pass

cdef class _DocumentBase:
    """Base class to reference a libxml document.

    When instances of this class are garbage collected, the libxml
    document is cleaned up.
    """
    cdef int ns_counter
    cdef xmlDoc* _c_doc
    
    def __dealloc__(self):
        # if there are no more references to the document, it is safe
        # to clean the whole thing up, as all nodes have a reference to
        # the document
        # print "freeing document:", <int>self._c_doc
        # displayNode(<xmlNode*>self._c_doc, 0)
        #print self._c_doc.dict is theParser._c_dict
        tree.xmlFreeDoc(self._c_doc)

# to help with debugging
cdef void displayNode(xmlNode* c_node, indent):
    cdef xmlNode* c_child
    print indent * ' ', <int>c_node
    c_child = c_node.children
    while c_child is not NULL:
        displayNode(c_child, indent + 1)
        c_child = c_child.next
        
cdef class _NodeBase:
    """Base class to reference a document object and a libxml node.

    By pointing to an ElementTree instance, a reference is kept to
    _ElementTree as long as there is some pointer to a node in it.
    """
    cdef _DocumentBase _doc
    cdef xmlNode* _c_node
    cdef int _proxy_type
    
    def __dealloc__(self):
        #print "trying to free node:", <int>self._c_node
        #displayNode(self._c_node, 0)
        if self._c_node is not NULL:
            unregisterProxy(self, self._proxy_type)
        attemptDeallocation(self._c_node)

    cdef xmlNs* _getNs(self, char* href):
        """Get or create namespace structure.
        """
        cdef xmlDoc* c_doc
        cdef xmlNode* c_node

        c_doc = self._doc._c_doc
        c_node = self._c_node
        cdef xmlNs* c_ns
        # look for existing ns
        c_ns = tree.xmlSearchNsByHref(c_doc, c_node, href)
        if c_ns is not NULL:
            return c_ns
        # create ns if existing ns cannot be found
        # try to simulate ElementTree's namespace prefix creation
        prefix = 'ns%s' % self._doc._ns_counter
        c_ns = tree.xmlNewNs(c_node, href, prefix)
        self._doc._ns_counter = self._doc._ns_counter + 1
        return c_ns

cdef class _ElementTreeBase(_DocumentBase):

##     def parse(self, source, parser=None):
##         # XXX ignore parser for now
##         cdef xmlDoc* c_doc
##         c_doc = theParser.parseDoc(source)
##         result._c_doc = c_doc
        
##         return self.getroot()
    
    def getroot(self):
        cdef xmlNode* c_node
        c_node = tree.xmlDocGetRootElement(self._c_doc)
        if c_node is NULL:
            return None
        return _elementFactory(self, c_node)
    
    def write(self, file, encoding='us-ascii'):
        # XXX dumping to memory first is definitely not the most efficient
        cdef char* mem
        cdef int size
        tree.xmlDocDumpMemory(self._c_doc, &mem, &size)
        if not encoding:
            encoding = 'us-ascii'
        # XXX complete hack to remove these, but for compatibility with
        # ElementTree selftest.py
        s = '<?xml version="1.0"?>\n'
        m = mem
        if m.startswith(s):
            m = m[len(s):]
        if m[-1] == '\n':
            m = m[:-1]
        if encoding in ('UTF-8', 'utf8', 'UTF8', 'utf-8'):
            file.write(m)
        else:
            file.write(funicode(m).encode(encoding))
        tree.xmlFree(mem)

    def getiterator(self, tag=None):
        root = self.getroot()
        if root is None:
            return []
        return root.getiterator(tag)

    def find(self, path):
        root = self.getroot()
        assert root is not None
        if path[:1] == "/":
            path = "." + path
        return root.find(path)

    def findtext(self, path, default=None):
        root = self.getroot()
        assert root is not None
        if path[:1] == "/":
            path = "." + path
        return root.findtext(path, default)

    def findall(self, path):
        root = self.getroot()
        assert root is not None
        if path[:1] == "/":
            path = "." + path
        return root.findall(path)

    # extension to ElementTree API
    def xpath(self, path):
        """XPath evaluate in context of document.

        Returns a list (nodeset), or bool, float or string.

        In case of a list result, return Element for element nodes,
        string for text and attribute values.
        """
        return _xpathEval(self, None, path)
    
class _ElementTree(_ElementTreeBase):
    __slots__ = ['__weakref__']
    
cdef _ElementTreeBase _elementTreeFactory(xmlDoc* c_doc):
    cdef _ElementTreeBase result
    result = _ElementTree()
    result._ns_counter = 0
    result._c_doc = c_doc
    return result

cdef class _ElementBase(_NodeBase):
    # MANIPULATORS

    def __setitem__(self, index, _NodeBase element):
        cdef xmlNode* c_node
        cdef xmlNode* c_next
        c_node = _findChild(self._c_node, index)
        if c_node is NULL:
            raise IndexError
        c_next = element._c_node.next
        _removeText(c_node.next)
        tree.xmlReplaceNode(c_node, element._c_node)
        _moveTail(c_next, element._c_node)
        changeDocumentBelow(element._c_node, self._doc)
        
    def __delitem__(self, index):
        cdef xmlNode* c_node
        c_node = _findChild(self._c_node, index)
        if c_node is NULL:
            raise IndexError
        _removeText(c_node.next)
        _removeNode(c_node)

    def __delslice__(self, start, stop):
        cdef xmlNode* c_node
        c_node = _findChild(self._c_node, start)
        _deleteSlice(c_node, start, stop)
        
    def __setslice__(self, start, stop, value):
        cdef xmlNode* c_node
        cdef xmlNode* c_next
        cdef _ElementBase mynode
        # first, find start of slice
        c_node = _findChild(self._c_node, start)
        # now delete the slice
        _deleteSlice(c_node, start, stop)
        # now find start of slice again, for insertion (just before it)
        c_node = _findChild(self._c_node, start)
        # if the insertion point is at the end, append there
        if c_node is NULL:
            for node in value:
                self.append(node)
            return
        # if the next element is in the list, insert before it
        for node in value:
            mynode = node
            # store possible text tail
            c_next = mynode._c_node.next
            # now move node previous to insertion point
            tree.xmlUnlinkNode(mynode._c_node)
            tree.xmlAddPrevSibling(c_node, mynode._c_node)
            # and move tail just behind his node
            _moveTail(c_next, mynode._c_node)
            # move it into a new document
            changeDocumentBelow(mynode._c_node, self._doc)
            
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
        _moveTail(c_next, element._c_node)
        # uh oh, elements may be pointing to different doc when
        # parent element has moved; change them too..
        changeDocumentBelow(element._c_node, self._doc)

    def clear(self):
        cdef xmlAttr* c_attr
        cdef xmlAttr* c_attr_next
        cdef xmlNode* c_node
        cdef xmlNode* c_node_next
        self.text = None
        self.tail = None
        # remove all attributes
        c_attr = self._c_node.properties
        while c_attr is not NULL:
            c_attr_next = c_attr.next
            tree.xmlRemoveProp(c_attr)
            c_attr = c_attr_next
        # remove all subelements
        c_node = self._c_node.children
        while c_node is not NULL:
            c_node_next = c_node.next
            if _isElement(c_node):
                _removeText(c_node_next)
                c_node_next = c_node.next
                _removeNode(c_node)
            c_node = c_node_next

    def insert(self, index, _ElementBase element):
        cdef xmlNode* c_node
        cdef xmlNode* c_next
        c_node = _findChild(self._c_node, index)
        if c_node is NULL:
            self.append(element)
            return
        c_next = element._c_node.next
        tree.xmlAddPrevSibling(c_node, element._c_node)
        _moveTail(c_next, element._c_node)
        changeDocumentBelow(element._c_node, self._doc)

    def remove(self, _ElementBase element):
        cdef xmlNode* c_node
        c_node = self._c_node.children
        while c_node is not NULL:
            if c_node is element._c_node:
                _removeText(element._c_node.next)
                tree.xmlUnlinkNode(element._c_node)
                return
            c_node = c_node.next
        else:
            raise ValueError, "Matching element could not be found"
        
    # PROPERTIES
    property tag:
        def __get__(self):
            if self._c_node.ns is NULL or self._c_node.ns.href is NULL:
                return funicode(self._c_node.name)
            else:
                # XXX optimize
                s = "{%s}%s" % (self._c_node.ns.href, self._c_node.name)
                return funicode(s)

        def __set__(self, value):
            cdef xmlNs* c_ns
            ns, text = _getNsTag(value)
            tree.xmlNodeSetName(self._c_node, text)
            if ns is None:
                return
            c_ns = self._getNs(ns)
            tree.xmlSetNs(self._c_node, c_ns)
            
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
            _removeText(self._c_node.children)
            if value is None:
                return
            # now add new text node with value at start
            text = value.encode('UTF-8')
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
            cdef xmlNode* c_text_node
            # remove all text nodes at the start first
            _removeText(self._c_node.next)
            if value is None:
                return
            text = value.encode('UTF-8')
            c_text_node = tree.xmlNewDocText(self._doc._c_doc, text)
            # XXX what if we're the top element?
            tree.xmlAddNextSibling(self._c_node, c_text_node)

    # ACCESSORS
    def __repr__(self):
        return "<Element %s at %x>" % (self.tag, id(self))
    
    def __getitem__(self, index):
        cdef xmlNode* c_node
        c_node = _findChild(self._c_node, index)
        if c_node is NULL:
            raise IndexError, "list index out of range"
        return _elementFactory(self._doc, c_node)

    def __getslice__(self, start, stop):
        cdef xmlNode* c_node
        cdef int c
        # this does not work for negative start, stop, however,
        # python seems to convert these to positive start, stop before
        # calling, so this all works perfectly (at the cost of a len() call)
        c_node = _findChild(self._c_node, start)
        if c_node is NULL:
            return []
        c = start
        result = []
        while c_node is not NULL and c < stop:
            if _isElement(c_node):
                result.append(_elementFactory(self._doc, c_node))
                c = c + 1
            c_node = c_node.next
        return result        
            
    def __len__(self):
        cdef int c
        cdef xmlNode* c_node
        c = 0
        c_node = self._c_node.children
        while c_node is not NULL:
            if _isElement(c_node):
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

    def getchildren(self):
        cdef xmlNode* c_node
        result = []
        c_node = self._c_node.children
        while c_node is not NULL:
            if _isElement(c_node):
                result.append(_elementFactory(self._doc, c_node))
            c_node = c_node.next
        return result

    def getiterator(self, tag=None):
        result = []
        if tag == "*":
            tag = None
        if tag is None or self.tag == tag:
            result.append(self)
        for node in self:
            result.extend(node.getiterator(tag))
        return result

        # XXX this doesn't work yet
        # return _docOrderIteratorFactory(self._doc, self._c_node, tag)

    def makeelement(self, tag, attrib):
        return Element(tag, attrib)

    def find(self, path):
        return _elementpath.find(self, path)

    def findtext(self, path, default=None):
        return _elementpath.findtext(self, path, default)

    def findall(self, path):
        return _elementpath.findall(self, path)

    def xpath(self, path):
        return _xpathEval(self._doc, self, path)
        
class _Element(_ElementBase):
    __slots__ = ['__weakref__']
    
cdef _ElementBase _elementFactory(_ElementTreeBase etree, xmlNode* c_node):
    cdef _ElementBase result
    result = getProxy(c_node, PROXY_ELEMENT)
    if result is not None:
        return result
    if c_node is NULL:
        return None
    if c_node.type == tree.XML_ELEMENT_NODE:
        result = _Element()
    elif c_node.type == tree.XML_COMMENT_NODE:
        result = _Comment()
    else:
        assert 0, "Unknown node type"
    result._doc = etree
    result._c_node = c_node
    result._proxy_type = PROXY_ELEMENT
    registerProxy(result, PROXY_ELEMENT)
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
            return funicode(self._c_node.content)

        def __set__(self, value):
            pass
                        
    # ACCESSORS
    def __repr__(self):
        return "<Comment at %x>" % id(self)
    
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
    result = getProxy(c_node, PROXY_ELEMENT)
    if result is not None:
        return result
    if c_node is NULL:
        return None
    result = _Comment()
    result._doc = etree
    result._c_node = c_node
    result._proxy_type = PROXY_ELEMENT
    registerProxy(result, PROXY_ELEMENT)
    return result

cdef class _AttribBase(_NodeBase):
    # MANIPULATORS
    def __setitem__(self, key, value):
        cdef xmlNs* c_ns
        ns, tag = _getNsTag(key)
        value = value.encode('UTF-8')
        if ns is None:
            tree.xmlSetProp(self._c_node, tag, value)
        else:
            c_ns = self._getNs(ns)
            tree.xmlSetNsProp(self._c_node, c_ns, tag, value)

    def __delitem__(self, key):
        cdef xmlNs* c_ns
        cdef xmlAttr* c_attr
        ns, tag = _getNsTag(key)
        if ns is None:
            c_attr = tree.xmlHasProp(self._c_node, tag)
        else:
            c_attr = tree.xmlHasNsProp(self._c_node, tag, ns)
        if c_attr is NULL:
            # XXX free namespace that is not in use..?
            raise KeyError, key
        tree.xmlRemoveProp(c_attr)
        
    # ACCESSORS
    def __repr__(self):
        result = {}
        for key, value in self.items():
            result[key] = value
        return repr(result)
    
    def __getitem__(self, key):
        cdef xmlNs* c_ns
        cdef char* result
        ns, tag = _getNsTag(key)
        if ns is None:
            result = tree.xmlGetNoNsProp(self._c_node, tag)
        else:
            result = tree.xmlGetNsProp(self._c_node, tag, ns)
        if result is NULL:
            # XXX free namespace that is not in use..?
            raise KeyError, key
        return funicode(result)

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
                # XXX namespaces {}
                result.append(funicode(c_node.name))
            c_node = c_node.next
        return result

    def values(self):
        result = []
        cdef xmlNode* c_node
        c_node = <xmlNode*>(self._c_node.properties)
        while c_node is not NULL:
            if c_node.type == tree.XML_ATTRIBUTE_NODE:
                result.append(
                    funicode(tree.xmlGetNoNsProp(self._c_node, c_node.name))
                    )
            c_node = c_node.next
        return result
        
    def items(self):
        result = []
        cdef xmlNode* c_node
        c_node = <xmlNode*>(self._c_node.properties)
        while c_node is not NULL:
            if c_node.type == tree.XML_ATTRIBUTE_NODE:
                # XXX namespaces {}
                result.append((
                    funicode(c_node.name),
                    funicode(tree.xmlGetNoNsProp(self._c_node, c_node.name))
                    ))
            c_node = c_node.next
        return result
    
class _Attrib(_AttribBase):
    __slots__ = ['__weakref__']
    
cdef _AttribBase _attribFactory(_ElementTreeBase etree, xmlNode* c_node):
    cdef _AttribBase result
    result = getProxy(c_node, PROXY_ATTRIB)
    if result is not None:
        return result
    result = _Attrib()
    result._doc = etree
    result._c_node = c_node
    result._proxy_type = PROXY_ATTRIB
    registerProxy(result, PROXY_ATTRIB)
    return result

cdef class _AttribIteratorBase(_NodeBase):
    def __next__(self):
        cdef xmlNode* c_node
        c_node = self._c_node
        while c_node is not NULL:
            if c_node.type == tree.XML_ATTRIBUTE_NODE:
                break
            c_node = c_node.next
        else:
            raise StopIteration
        unregisterProxy(self, PROXY_ATTRIB_ITER)
        self._c_node = c_node.next
        registerProxy(self, PROXY_ATTRIB_ITER)
        return funicode(c_node.name)

class _AttribIterator(_AttribIteratorBase):
    __slots__ = ['__weakref__']
    
cdef _AttribIteratorBase _attribIteratorFactory(_ElementTreeBase etree,
                                                xmlNode* c_node):
    cdef _AttribIteratorBase result
    result = getProxy(c_node, PROXY_ATTRIB_ITER)
    if result is not None:
        return result
    result = _AttribIterator()
    result._doc = etree
    result._c_node = c_node
    result._proxy_type = PROXY_ATTRIB_ITER
    registerProxy(result, PROXY_ATTRIB_ITER)
    return result

cdef class _ElementIteratorBase(_NodeBase):
    def __next__(self):
        cdef xmlNode* c_node
        c_node = self._c_node
        while c_node is not NULL:
            if _isElement(c_node):
                break
            c_node = c_node.next
        else:
            raise StopIteration
        unregisterProxy(self, PROXY_ELEMENT_ITER)
        self._c_node = c_node.next
        registerProxy(self, PROXY_ELEMENT_ITER)
        return _elementFactory(self._doc, c_node)

class _ElementIterator(_ElementIteratorBase):
    __slots__ = ['__weakref__']
    
cdef _ElementIteratorBase _elementIteratorFactory(_ElementTreeBase etree,
                                                  xmlNode* c_node):
    cdef _ElementIteratorBase result
    result = getProxy(c_node, PROXY_ELEMENT_ITER)
    if result is not None:
        return result
    result = _ElementIterator()
    result._doc = etree
    result._c_node = c_node
    result._proxy_type = PROXY_ELEMENT_ITER
    registerProxy(result, PROXY_ELEMENT_ITER)
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

# module-level API for ElementTree

def Element(tag, attrib=None, **extra):
    cdef xmlNode* c_node
    cdef _ElementTreeBase etree

    etree = ElementTree()
    c_node = _createElement(etree._c_doc, tag, attrib, extra)
    tree.xmlDocSetRootElement(etree._c_doc, c_node)
    # XXX hack for namespaces
    result = _elementFactory(etree, c_node)
    result.tag = tag
    return result

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
    # XXX hack for namespaces
    element.tag = tag
    return element

def ElementTree(_ElementBase element=None, file=None):
    cdef xmlDoc* c_doc
    cdef xmlNode* c_next
    cdef xmlNode* c_node
    cdef xmlNode* c_node_copy
    cdef _ElementTreeBase etree
    
    if file is not None:
        if isinstance(file, str) or isinstance(file, unicode):
            f = open(file, 'r')
            data = f.read()
            f.close()
        else:
            # XXX read XML into memory not the fastest way to do this
            data = file.read()
        c_doc = theParser.parseDoc(data)
    else:
        c_doc = theParser.newDoc()

    etree = _elementTreeFactory(c_doc)

    # XXX what if element and file are both not None?
    if element is not None:
        c_next = element._c_node.next
        tree.xmlDocSetRootElement(etree._c_doc, element._c_node)
        _moveTail(c_next, element._c_node)
        changeDocumentBelow(element._c_node, etree)

    return etree

def XML(text):
    cdef xmlDoc* c_doc
    c_doc = theParser.parseDoc(text)
    return _elementTreeFactory(c_doc).getroot()

fromstring = XML

def iselement(element):
    return isinstance(element, _ElementBase)

def dump(_NodeBase elem):
    _dumpToFile(sys.stdout, elem._doc._c_doc, elem._c_node)

def tostring(element, encoding=None):
    f = StringIO()
    ElementTree(element).write(f, encoding)
    return f.getvalue()

def parse(source, parser=None):
    # XXX ignore parser for now
    cdef xmlDoc* c_doc

    # XXX simplistic StringIO support
    if isinstance(source, StringIO):
        c_doc = theParser.parseDoc(source.getvalue())
        return _elementTreeFactory(c_doc)
    
    if tree.PyFile_Check(source):
        # this is a file object, so retrieve file name
        filename = tree.PyFile_Name(source)
        # XXX this is a hack that makes to seem a crash go away;
        # filename is a borrowed reference which may be what's tripping
        # things up
        tree.Py_INCREF(filename)
    else:
        filename = source
        
    # open filename
    c_doc = theParser.parseDocFromFile(filename)
    result = _elementTreeFactory(c_doc)
    return result

# Globally shared XML parser to enable dictionary sharing
cdef class Parser:

    cdef xmlDict* _c_dict
    cdef int _parser_initialized
    
    def __init__(self):
        self._c_dict = NULL
        self._parser_initialized = 0
        
    def __del__(self):
        #print "cleanup parser"
        if self._c_dict is not NULL:
            #print "freeing dictionary (cleanup parser)"
            xmlparser.xmlDictFree(self._c_dict)
        
    cdef xmlDoc* parseDoc(self, text) except NULL:
        """Parse document, share dictionary if possible.
        """
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt
        cdef int parse_error
        self._initParse()
        pctxt = xmlparser.xmlCreateDocParserCtxt(text)
        self._prepareParse(pctxt)
        xmlparser.xmlCtxtUseOptions(
            pctxt,
            _getParseOptions())
        parse_error = xmlparser.xmlParseDocument(pctxt)
        # in case of errors, clean up context plus any document
        if parse_error != 0 or not pctxt.wellFormed:
            if pctxt.myDoc is not NULL:
                tree.xmlFreeDoc(pctxt.myDoc)
                pctxt.myDoc = NULL
            xmlparser.xmlFreeParserCtxt(pctxt)
            raise SyntaxError
        result = pctxt.myDoc
        self._finalizeParse(result)
        xmlparser.xmlFreeParserCtxt(pctxt)
        return result

    cdef xmlDoc* parseDocFromFile(self, char* filename) except NULL:
        cdef xmlDoc* result
        cdef xmlParserCtxt* pctxt

        self._initParse()
        pctxt = xmlparser.xmlNewParserCtxt()
        self._prepareParse(pctxt)
        # XXX set options twice? needed to shut up libxml2
        xmlparser.xmlCtxtUseOptions(pctxt, _getParseOptions())
        result = xmlparser.xmlCtxtReadFile(pctxt, filename,
                                           NULL, _getParseOptions())
        if result is NULL:
            if pctxt.lastError.domain == xmlerror.XML_FROM_IO:
                raise IOError, "Could not open file %s" % filename
        # in case of errors, clean up context plus any document
        # XXX other errors?
        if not pctxt.wellFormed:
            if pctxt.myDoc is not NULL:
                tree.xmlFreeDoc(pctxt.myDoc)
                pctxt.myDoc = NULL
            xmlparser.xmlFreeParserCtxt(pctxt)
            raise SyntaxError
        self._finalizeParse(result)
        xmlparser.xmlFreeParserCtxt(pctxt)
        return result
    
    cdef void _initParse(self):
        if not self._parser_initialized:
            xmlparser.xmlInitParser()
            self._parser_initialized = 1
            
    cdef void _prepareParse(self, xmlParserCtxt* pctxt):
        if self._c_dict is not NULL and pctxt.dict is not NULL:
            #print "sharing dictionary (parseDoc)"
            xmlparser.xmlDictFree(pctxt.dict)
            pctxt.dict = self._c_dict
            xmlparser.xmlDictReference(pctxt.dict)

    cdef void _finalizeParse(self, xmlDoc* result):
        # store dict of last object parsed if no shared dict yet
        if self._c_dict is NULL:
            #print "storing shared dict"
            self._c_dict = result.dict
            xmlparser.xmlDictReference(self._c_dict)
    
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

cdef Parser theParser
theParser = Parser()

cdef class XSLT:
    """Turn a document into an XSLT object.
    """
    cdef xslt.xsltStylesheet* _c_style
    
    def __init__(self, _ElementTreeBase doc):
        # make a copy of the document as stylesheet needs to assume it
        # doesn't change
        cdef xslt.xsltStylesheet* c_style
        cdef xmlDoc* c_doc
        c_doc = tree.xmlCopyDoc(doc._c_doc, 1)
        
        c_style = xslt.xsltParseStylesheetDoc(c_doc)
        if c_style is NULL:
            raise Error, "Cannot parse style sheet"
        self._c_style = c_style
        # XXX is it worthwile to use xsltPrecomputeStylesheet here?
        
    def __dealloc__(self):
        # this cleans up copy of doc as well
        xslt.xsltFreeStylesheet(self._c_style)
        
    def apply(self, _ElementTreeBase doc):
        cdef xmlDoc* c_result 
        c_result = xslt.xsltApplyStylesheet(self._c_style, doc._c_doc, NULL)
        if c_result is NULL:
            raise Error, "Error applying stylesheet"
        # XXX should set special flag to indicate this is XSLT result
        # so that xsltSaveResultTo* functional can be used during
        # serialize?
        return _elementTreeFactory(c_result)

    def tostring(self, _ElementTreeBase doc):
        """Save result doc to string using stylesheet as guidance.
        """
        cdef char* s
        cdef int l
        cdef int r
        r = xslt.xsltSaveResultToString(&s, &l, doc._c_doc, self._c_style)
        if r == -1:
            raise Error, "Error saving stylesheet result to string"
        result = funicode(s)
        tree.xmlFree(s)
        return result

# Private helper functions
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

    Start collecting at c_node.
    
    If there was no text to collect, return None
    """
    result = ''
    while c_node is not NULL and c_node.type == tree.XML_TEXT_NODE:
        result = result + c_node.content
        c_node = c_node.next
    if result:
        return funicode(result)
    else:
        return None

cdef _removeText(xmlNode* c_node):
    """Remove all text nodes.

    Start removing at c_node.
    """
    cdef xmlNode* c_next
    while c_node is not NULL and c_node.type == tree.XML_TEXT_NODE:
        c_next = c_node.next
        tree.xmlUnlinkNode(c_node)
        # XXX cannot safely free in case of direct text node proxies..
        tree.xmlFreeNode(c_node)
        c_node = c_next

cdef xmlNode* _findChild(xmlNode* c_node, int index):
    if index < 0:
        return _findChildBackwards(c_node, -index - 1)
    else:
        return _findChildForwards(c_node, index)
    
cdef xmlNode* _findChildForwards(xmlNode* c_node, int index):
    """Return child element of c_node with index, or return NULL if not found.
    """
    cdef xmlNode* c_child
    cdef int c
    c_child = c_node.children
    c = 0
    while c_child is not NULL:
        if _isElement(c_child):
            if c == index:
                return c_child
            c = c + 1
        c_child = c_child.next
    else:
        return NULL

cdef xmlNode* _findChildBackwards(xmlNode* c_node, int index):
    """Return child element of c_node with index, or return NULL if not found.
    Search from the end.
    """
    cdef xmlNode* c_child
    cdef int c
    c_child = c_node.last
    c = 0
    while c_child is not NULL:
        if _isElement(c_child):
            if c == index:
                return c_child
            c = c + 1
        c_child = c_child.prev
    else:
        return NULL
    
cdef xmlNode* _nextElement(xmlNode* c_node):
    """Given a node, find the next sibling that is an element.
    """
    c_node = c_node.next
    while c_node is not NULL:
        if _isElement(c_node):
            return c_node
        c_node = c_node.next
    return NULL

cdef void _removeNode(xmlNode* c_node):
    """Unlink and free a node if possible (nothing else refers to it).
    """
    tree.xmlUnlinkNode(c_node)
    if not hasProxy(c_node):
        tree.xmlFreeNode(c_node)

cdef void _moveTail(xmlNode* c_tail, xmlNode* c_target):
    cdef xmlNode* c_next
    # tail support: look for any text nodes trailing this node and
    # move them too
    while c_tail is not NULL and c_tail.type == tree.XML_TEXT_NODE:
        c_next = c_tail.next
        tree.xmlUnlinkNode(c_tail)
        tree.xmlAddNextSibling(c_target, c_tail)
        c_target = c_tail
        c_tail = c_next

cdef int _isElement(xmlNode* c_node):
    return (c_node.type == tree.XML_ELEMENT_NODE or
            c_node.type == tree.XML_COMMENT_NODE)

cdef void _deleteSlice(xmlNode* c_node, int start, int stop):
    """Delete slice, starting with c_node, start counting at start, end at stop.
    """
    cdef xmlNode* c_next
    cdef int c
    if c_node is NULL:
        return
    # now start deleting nodes
    c = start
    while c_node is not NULL and c < stop:
        c_next = c_node.next
        if _isElement(c_node):
            _removeText(c_node.next)
            c_next = c_node.next
            _removeNode(c_node)
            c = c + 1
        c_node = c_next

cdef int _getParseOptions():
    return (xmlparser.XML_PARSE_NOENT | xmlparser.XML_PARSE_NOCDATA |
            xmlparser.XML_PARSE_NOWARNING | xmlparser.XML_PARSE_NOERROR)

def _getNsTag(tag):
    """Given a tag, find namespace URI and tag name.
    Return None for NS uri if no namespace URI available.
    """
    tag = tag.encode('UTF-8')
    if tag[0] == '{':
        i = tag.find('}')
        assert i != -1
        return tag[1:i], tag[i + 1:]
    return None, tag

cdef object _createNodeSetResult(_ElementTreeBase doc,
                                 xpath.xmlXPathObject* xpathObj):
    cdef xmlNode* c_node
    cdef char* s
    result = []
    if xpathObj.nodesetval is NULL:
        return result
    for i from 0 <= i < xpathObj.nodesetval.nodeNr:
        c_node = xpathObj.nodesetval.nodeTab[i]
        if c_node.type == tree.XML_ELEMENT_NODE:
            result.append(_elementFactory(doc, c_node))
        elif c_node.type == tree.XML_TEXT_NODE:
            result.append(funicode(c_node.content))
        elif c_node.type == tree.XML_ATTRIBUTE_NODE:
            s = tree.xmlNodeGetContent(c_node)
            attr_value = funicode(s)
            tree.xmlFree(s)
            result.append(attr_value)
        elif c_node.type == tree.XML_COMMENT_NODE:
            s = tree.xmlNodeGetContent(c_node)
            s2 = '<!--%s-->' % s
            comment_value = funicode(s2)
            tree.xmlFree(s)
            result.append(comment_value)
        else:
            print "Not yet implemented result node type:", c_node.type
            raise NotImplementedError
    return result

cdef object _xpathEval(_ElementTreeBase doc, _ElementBase element,
                       object path):    
    cdef xpath.xmlXPathContext* xpathCtxt
    cdef xpath.xmlXPathObject* xpathObj
    cdef xmlNode* c_node

    path = path.encode('UTF-8')

    xpathCtxt = xpath.xmlXPathNewContext(doc._c_doc)
    if xpathCtxt is NULL:
        raise Error, "Unable to create new XPath context"

    # element context is requested
    if element is not None:
        xpathCtxt.node = element._c_node

    # XXX register namespaces?

    xpathObj = xpath.xmlXPathEvalExpression(path, xpathCtxt)
    if xpathObj is NULL:
        xpath.xmlXPathFreeContext(xpathCtxt)
        raise SyntaxError, "Error in xpath expression."

    if xpathObj.type == xpath.XPATH_UNDEFINED:
        xpath.xmlXPathFreeObject(xpathObj)
        xpath.xmlXPathFreeContext(xpathCtxt)
        raise Error, "Undefined xpath result"
    elif xpathObj.type == xpath.XPATH_NODESET:
        result = _createNodeSetResult(doc, xpathObj)
    elif xpathObj.type == xpath.XPATH_BOOLEAN:
        result = xpathObj.boolval
    elif xpathObj.type == xpath.XPATH_NUMBER:
        result = xpathObj.floatval
    elif xpathObj.type == xpath.XPATH_STRING:
        result = funicode(xpathObj.stringval)
    elif xpathObj.type == xpath.XPATH_POINT:
        raise NotImplementedError
    elif xpathObj.type == xpath.XPATH_RANGE:
        raise NotImplementedError
    elif xpathObj.type == xpath.XPATH_LOCATIONSET:
        raise NotImplementedError
    elif xpathObj.type == xpath.XPATH_USERS:
        raise NotImplementedError
    elif xpathObj.type == xpath.XPATH_XSLT_TREE:
        raise NotImplementedError
    else:
        raise Error, "Unknown xpath result %s" % str(xpathObj.type)

    xpath.xmlXPathFreeObject(xpathObj)
    xpath.xmlXPathFreeContext(xpathCtxt)

    return result

cdef int isutf8(char* string):
    cdef int i
    i = 0
    while 1:
        if string[i] == c'\0':
            return 0
        if string[i] & 0x80:
            return 1
        i = i + 1

cdef object funicode(char* s):
    if isutf8(s):
        return tree.PyUnicode_DecodeUTF8(s, tree.strlen(s), "strict")
    return tree.PyString_FromStringAndSize(s, tree.strlen(s))

# backpointer functionality

cdef struct _ProxyRef

cdef struct _ProxyRef:
    tree.PyObject* proxy
    int type
    _ProxyRef* next
        
ctypedef _ProxyRef ProxyRef
    
# XXX not portable
cdef int PROXYREF_SIZEOF
PROXYREF_SIZEOF = 12

cdef _NodeBase getProxy(xmlNode* c_node, int proxy_type):
    """Get a proxy for a given node and node type.
    """
    cdef ProxyRef* ref
    #print "getProxy for:", <int>c_node
    if c_node is NULL:
        return None
    ref = <ProxyRef*>c_node._private
    while ref is not NULL:
        if ref.type == proxy_type:
            return <_NodeBase>ref.proxy
        ref = ref.next
    return None

cdef int hasProxy(xmlNode* c_node):
    return c_node._private is not NULL
    
cdef ProxyRef* createProxyRef(_NodeBase proxy, int proxy_type):
    """Create a backpointer proxy refeference for a proxy and type.
    """
    cdef ProxyRef* result
    result = <ProxyRef*>cstd.malloc(PROXYREF_SIZEOF)
    result.proxy = <tree.PyObject*>proxy
    result.type = proxy_type
    result.next = NULL
    return result

cdef void registerProxy(_NodeBase proxy, int proxy_type):
    """Register a proxy and type for the node it's proxying for.
    """
    cdef ProxyRef* ref
    cdef ProxyRef* prev_ref
    # cannot register for NULL
    if proxy._c_node is NULL:
        return
    # XXX should we check whether we ran into proxy_type before?
    #print "registering for:", <int>proxy._c_node
    ref = <ProxyRef*>proxy._c_node._private
    if ref is NULL:
        proxy._c_node._private = <void*>createProxyRef(proxy, proxy_type)
        return
    while ref is not NULL:
        prev_ref = ref
        ref = ref.next
    prev_ref.next = createProxyRef(proxy, proxy_type)

cdef void unregisterProxy(_NodeBase proxy, int proxy_type):
    """Unregister a proxy for the node it's proxying for.
    """
    cdef ProxyRef* ref
    cdef ProxyRef* prev_ref
    cdef xmlNode* c_node
    c_node = proxy._c_node
    ref = <ProxyRef*>c_node._private
    if ref.type == proxy_type:
        c_node._private = <void*>ref.next
        cstd.free(ref)
        return
    prev_ref = ref
    #print "First registered is:", ref.type
    ref = ref.next
    while ref is not NULL:
        #print "Registered is:", ref.type
        if ref.type == proxy_type:
            prev_ref.next = ref.next
            cstd.free(ref)
            return
        prev_ref = ref
        ref = ref.next
    #print "Proxy:", proxy, "Proxy type:", proxy_type
    assert 0, "Tried to unregister unknown proxy"


cdef void changeDocumentBelow(xmlNode* c_node,
                              _DocumentBase doc):
    """For a node and all nodes below, change document.

    A node can change document in certain operations as an XML
    subtree can move. This updates all possible proxies in the
    tree below (including the current node).
    """
    cdef ProxyRef* ref
    cdef xmlNode* c_current
    cdef xmlAttr* c_attr_current
    cdef _NodeBase proxy

    if c_node is NULL:
        return
    
    if c_node._private is not NULL:
        ref = <ProxyRef*>c_node._private
        while ref is not NULL:
            proxy = <_NodeBase>ref.proxy
            proxy._doc = doc
            ref = ref.next

    # adjust all children
    c_current = c_node.children
    while c_current is not NULL:
        changeDocumentBelow(c_current, doc)
        c_current = c_current.next
        
    # adjust all attributes
    c_attr_current = c_node.properties
    while c_attr_current is not NULL:
        changeDocumentBelow(c_current, doc)
        c_attr_current = c_attr_current.next
        
cdef void attemptDeallocation(xmlNode* c_node):
    """Attempt deallocation of c_node (or higher up in tree).
    """
    cdef xmlNode* c_top
    # could be we actually aren't referring to the tree at all
    if c_node is NULL:
        #print "not freeing, node is NULL"
        return
    c_top = getDeallocationTop(c_node)
    if c_top is not NULL:
        #print "freeing:", c_top.name
        tree.xmlFreeNode(c_top)

cdef xmlNode* getDeallocationTop(xmlNode* c_node):
    """Return the top of the tree that can be deallocated, or NULL.
    """
    cdef xmlNode* c_current
    cdef xmlNode* c_top
    #print "deallocating:", c_node.type
    c_current = c_node.parent
    c_top = c_node
    while c_current is not NULL:
        #print "checking:", c_current.type
        # if we're still attached to the document, don't deallocate
        if c_current.type == tree.XML_DOCUMENT_NODE:
            #print "not freeing: still in doc"
            return NULL
        c_top = c_current
        c_current = c_current.parent
    # if the top is not c_node, check whether it has node;
    # if the top is the node we're checking, then we *can*
    # still deallocate safely
    if c_top is not c_node:
        if c_top._private is not NULL:
            # print "Not freeing: proxies still exist"
            return NULL
    # XXX what if top has *other* proxies pointing to it?

    # otherwise, see whether we have children to deallocate
    if canDeallocateChildren(c_top):
        return c_top
    else:
        return NULL

cdef int canDeallocateChildNodes(xmlNode* c_node):
    cdef xmlNode* c_current
    #print "checking childNodes"
    c_current = c_node.children
    while c_current is not NULL:
        if c_current._private is not NULL:
            return 0
        if not canDeallocateChildren(c_current):
            return 0 
        c_current = c_current.next
    return 1

cdef int canDeallocateAttributes(xmlNode* c_node):
    cdef xmlAttr* c_current
    #print "checking attributes"
    c_current = c_node.properties
    while c_current is not NULL:
        if c_current._private is not NULL:
            return 0
        # only check child nodes, don't try checking properties as
        # attribute has none
        if not canDeallocateChildNodes(<xmlNode*>c_current):
            return 0
        c_current = c_current.next
    # apparently we can deallocate all subnodes
    return 1

cdef int canDeallocateChildren(xmlNode* c_node):
    # the current implementation is inefficient as it does a
    # tree traversal to find out whether there are any node proxies
    # we could improve this by a smarter datastructure
    #print "checking children"
    # check children
    if not canDeallocateChildNodes(c_node):
        return 0        
    # check any attributes
    if (c_node.type == tree.XML_ELEMENT_NODE and
        not canDeallocateAttributes(c_node)):
        return 0
    # apparently we can deallocate all subnodes
    return 1
