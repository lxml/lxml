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
    ctypedef struct xmlAttr
    
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
        
    ctypedef struct xmlAttr:
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
    
cdef extern from "libxml/parser.h":
    cdef xmlDoc* xmlParseFile(char* filename)
    cdef xmlDoc* xmlParseDoc(char* cur)
    
cdef class _Node
cdef class _ElementTree

cdef class _Node:
    cdef _ElementTree _tree
    cdef xmlNode* _o
    
    def _getTree(self):
        return self._tree
    
cdef class _AttribIterator(_Node):
    def __next__(self):
        cdef xmlNode* node
        node = self._o
        while node is not NULL:
            if node.type == XML_ATTRIBUTE_NODE:
                break
            node = node.next
        else:
            raise StopIteration
        self._o = node.next
        result = unicode(node.name, 'UTF-8')
        return result
    
cdef class _Attrib(_Node):
    def __getitem__(self, key):
        cdef char* result
        key = key.encode('UTF-8')
        result = xmlGetNoNsProp(self._o, key)
        if result is NULL:
            raise KeyError, key
        return unicode(result, 'UTF-8')

    def __setitem__(self, key, value):
        key = key.encode('UTF-8')
        value = value.encode('UTF-8')
        xmlSetProp(self._o, key, value)
        
    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def __len__(self):
        cdef int c
        cdef xmlNode* node
        c = 0
        node = <xmlNode*>(self._o.properties)
        while node is not NULL:
            if node.type == XML_ATTRIBUTE_NODE:
                c = c + 1
            node = node.next
        return c

    def __iter__(self):
        cdef _AttribIterator iterator
        iterator = _AttribIterator()
        iterator._tree = self._getTree()
        iterator._o = <xmlNode*>self._o.properties
        return iterator

    def keys(self):
        result = []
        cdef xmlNode* node
        node = <xmlNode*>(self._o.properties)
        while node is not NULL:
            if node.type == XML_ATTRIBUTE_NODE:
                result.append(unicode(node.name, 'UTF-8'))
            node = node.next
        return result

    def values(self):
        result = []
        cdef xmlNode* node
        node = <xmlNode*>(self._o.properties)
        while node is not NULL:
            if node.type == XML_ATTRIBUTE_NODE:
                result.append(
                    unicode(xmlGetNoNsProp(self._o, node.name), 'UTF-8')
                    )
            node = node.next
        return result
        
    def items(self):
        result = []
        cdef xmlNode* node
        node = <xmlNode*>(self._o.properties)
        while node is not NULL:
            if node.type == XML_ATTRIBUTE_NODE:
                result.append((
                    unicode(node.name, 'UTF-8'),
                    unicode(xmlGetNoNsProp(self._o, node.name), 'UTF-8')
                    ))
            node = node.next
        return result

cdef class _ElementIterator(_Node):
    def __next__(self):
        cdef xmlNode* node
        node = self._o
        while node is not NULL:
            if node.type == XML_ELEMENT_NODE:
                break
            node = node.next
        else:
            raise StopIteration
        self._o = node.next
        return ElementFactory(self._getTree(), node)

cdef class _Element(_Node):    
    property tag:
        def __get__(self):
            return unicode(self._o.name, 'UTF-8')

    property attrib:
        def __get__(self):
            cdef _Attrib attrib
            attrib = _Attrib()
            attrib._tree = self._tree
            attrib._o = self._o
            return attrib

    property text:
        def __get__(self):
            cdef xmlNode* node
            node = self._o.children
            if node is NULL:
                return None
            if node.type != XML_TEXT_NODE:
                return None
            return unicode(node.content, 'UTF-8')

        def __set__(self, value):
            pass
        
    property tail:
        def __get__(self):
            cdef xmlNode* node
            node = self._o.next
            if node is NULL:
                return None
            if node.type != XML_TEXT_NODE:
                return None
            return unicode(node.content, 'UTF-8')
        
    def get(self, key, default=None):
        return self.attrib.get(key, default)

    def set(self, key, value):
        self.attrib[key] = value

    def keys(self):
        return self.attrib.keys()

    def items(self):
        return self.attrib.items()
    
    def __iter__(self):
        cdef _ElementIterator iterator
        iterator = _ElementIterator()
        iterator._tree = self._getTree()
        iterator._o = self._o.children
        return iterator
    
    def __getitem__(self, n):
        cdef xmlNode* node
        node = self._o.children
        c = 0
        while node is not NULL:
            if node.type == XML_ELEMENT_NODE:
                if c == n:
                    return ElementFactory(self._getTree(), node)
                c = c + 1
            node = node.next
        else:
            raise IndexError
  
    def __len__(self):
        cdef int c
        cdef xmlNode* node
        c = 0
        node = self._o.children
        while node is not NULL:
            if node.type == XML_ELEMENT_NODE:
                c = c + 1
            node = node.next
        return c

    def append(self, _Element element):
        xmlUnlinkNode(element._o)
        xmlAddChild(self._o, element._o)
        # move element into tree
        # (may be no-op but could cause garbage collection)
        element._tree = self._tree

cdef class _ElementTree:
    cdef xmlDoc* _doc
    
    def __dealloc__(self):
        #cdef xmlNode* node
        #node = xmlDocGetRootElement(self._doc)
        #if node is not NULL:
        #    print "dealloc:", node.name
        #else:
        #    print "dealloc: no doc element"
        xmlFreeDoc(self._doc)
        #print "done dealloc"

    def _getTree(self):
        return self

    def getroot(self):
        cdef xmlNode* node
        node = xmlDocGetRootElement(self._doc)
        if node is NULL:
            return None
        return ElementFactory(self, node)

    def write(self, file, encoding="us-ascii"):
        # XXX dumping to memory first is definitely not the most
        # efficient way possible
        cdef char* mem
        cdef int size
        xmlDocDumpMemory(self._doc, &mem, &size)
        file.write(unicode(mem, 'UTF-8').encode(encoding))
        # XXX is this safe?
        xmlFree(mem)
        
cdef _Element ElementFactory(_ElementTree tree, xmlNode* o):
    cdef _Element result
    if o is NULL:
        return None
    result = _Element()
    result._tree = tree
    result._o = o
    return result

cdef xmlNode* makeNode(xmlDoc* doc, char* tag, object attrib, object extra):
    cdef xmlNode* node
    if attrib is None:
        attrib = {}
    # XXX pyrex doesn't like this, doesn't seem able to deduce the type
    # attrib = attrib or {}
    attrib.update(extra)
    node = xmlNewDocNode(doc, NULL, tag, NULL)
    for name, value in attrib.items():
        xmlNewProp(node, name, value)
    return node
    
def Element(tag, attrib=None, **extra):
    cdef xmlDoc* doc
    cdef xmlNode* node
    cdef _ElementTree tree
    # make up document for element; in many cases this is going to
    # be refcounted again (and thus deallocated) soon after, but
    # this element may end up playing document by itself
    doc = xmlNewDoc("1.0")
    node = makeNode(doc, tag, attrib, extra)
    xmlDocSetRootElement(doc, node)
    # XXX for some reason *have* to create explicit name for
    # tree, otherwise it is immediately deallocated!
    tree = _ElementTree()
    tree._doc = doc
    return ElementFactory(tree, node)

def SubElement(_Element parent, tag, attrib=None, **extra):
    cdef xmlDoc* doc
    cdef xmlNode* node
    doc = (parent._tree._doc)
    node = makeNode(doc, tag, attrib, extra)
    result = ElementFactory(parent._tree, node)
    parent.append(result)
    return result

def ElementTree(_Element element=None, file=None):
    cdef xmlDoc* doc
    cdef _ElementTree result

    if file is not None:
        # XXX not very robust
        # if isinstance(file, str):
        #    file = open(str, 'rb')
        # XXX read XML into memory definitely not the fastest way to do this
        data = file.read()
        doc = xmlParseDoc(data)    
        result = _ElementTree()
        result._doc = doc
        return result

    if element is not None:
        doc = xmlNewDoc("1.0")
        # unlink element from previous document
        xmlDocSetRootElement(doc, element._o)
        result = _ElementTree()
        result._doc = doc
        # move element into tree
        # (can cause garbage collection of previous document)
        element._tree = result
        return result
        
    doc = xmlNewDoc("1.0")
    result = _ElementTree()
    result._doc = doc
    return result

def XML(text):
    cdef xmlDoc* doc
    cdef _ElementTree tree
    doc = xmlParseDoc(text)
    tree = _ElementTree()
    tree._doc = doc
    return tree.getroot()
