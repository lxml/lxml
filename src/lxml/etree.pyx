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

# the rules
# any libxml C argument/variable is prefixed with c_
# any non-public function/class is prefixed with an underscore
# instance creation is always through factories

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

cdef class _ElementTree(_DocumentBase):
    def getroot(self):
        cdef xmlNode* c_node
        c_node = xmlDocGetRootElement(self._c_doc)
        if c_node is NULL:
            return # return None
        return _elementFactory(self, c_node)
    
    def write(self, file, encoding='us-ascii'):
        # XXX dumping to memory first is definitely not the most efficient
        cdef char* mem
        cdef int size
        xmlDocDumpMemory(self._c_doc, &mem, &size)
        if encoding in ('UTF-8', 'utf8', 'UTF8', 'utf-8'):
            file.write(mem)
        else:
            file.write(unicode(mem, 'UTF-8').encode(encoding))
        xmlFree(mem)
        
cdef _ElementTree _elementTreeFactory(xmlDoc* c_doc):
    cdef _ElementTree result
    result = _ElementTree()
    result._c_doc = c_doc
    return result
    
cdef class _Element(_NodeBase):
    property tag:
        def __get__(self):
            return unicode(self._c_node.name, 'UTF-8')

    property attrib:
        def __get__(self):
            return _attribFactory(self._doc, self._c_node)
        
    property text:
        def __get__(self):
            cdef xmlNode* c_node
            c_node = self._c_node.children
            if c_node is NULL:
                return None
            if c_node.type != XML_TEXT_NODE:
                return None
            return unicode(c_node.content, 'UTF-8')

        def __set__(self, value):
            pass

    property tail:
        def __get__(self):
            cdef xmlNode* c_node
            c_node = self._c_node.next
            if c_node is NULL:
                return None
            if c_node.type != XML_TEXT_NODE:
                return None
            return unicode(c_node.content, 'UTF-8')

    def __getitem__(self, n):
        cdef xmlNode* c_node
        c_node = self._c_node.children
        c = 0
        while c_node is not NULL:
            if c_node.type == XML_ELEMENT_NODE:
                if c == n:
                    return _elementFactory(self._doc, c_node)
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
            if c_node.type == XML_ELEMENT_NODE:
                c = c + 1
            c_node = c_node.next
        return c
    
    def append(self, _Element element):
        xmlUnlinkNode(element._c_node)
        xmlAddChild(self._c_node, element._c_node)
        element._doc = self._doc

cdef _Element _elementFactory(_ElementTree tree, xmlNode* c_node):
    cdef _Element result
    if c_node is NULL:
        return None
    result = _Element()
    result._doc = tree
    result._c_node = c_node
    return result

cdef class _Attrib(_NodeBase):
    def __getitem__(self, key):
        cdef char* result
        key = key.encode('UTF-8')
        result = xmlGetNoNsProp(self._c_node, key)
        if result is NULL:
            raise KeyError, key
        return unicode(result, 'UTF-8')

cdef _Attrib _attribFactory(_ElementTree tree, xmlNode* c_node):
    cdef _Attrib result
    result = _Attrib()
    result._doc = tree
    result._c_node = c_node
    return result
    
def Element(tag, attrib=None, **extra):
    cdef xmlNode* c_node
    cdef _ElementTree tree

    tree = ElementTree()
    c_node = xmlNewDocNode(tree._c_doc, NULL, tag, NULL)
    xmlDocSetRootElement(tree._c_doc, c_node)
    return _elementFactory(tree, c_node)

def SubElement(_Element parent, tag, attrib=None, **extra):
    cdef xmlNode* c_node
    cdef _Element element
    
    c_node = xmlNewDocNode(parent._doc._c_doc, NULL, tag, NULL)
    element = _elementFactory(parent._doc, c_node)
    parent.append(element)
    return element

def ElementTree(_Element element=None, file=None):
    cdef xmlDoc* c_doc
    cdef xmlNode* c_node
    cdef _ElementTree tree
    
    if file is not None:
        # XXX read XML into memory not the fastest way to do this
        data = file.read()
        c_doc = xmlParseDoc(data)
    else:
        c_doc = xmlNewDoc("1.0")
    tree = _elementTreeFactory(c_doc)

    # XXX what if element and file are both not None?
    if element is not None:
        xmlDocSetRootElement(tree._c_doc, element._c_node)
        element._doc = tree

    return tree
