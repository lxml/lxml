cimport tree
from tree cimport xmlDoc, xmlNode, xmlAttr, xmlNs
cimport xmlparser
cimport xpath
cimport xslt
cimport relaxng
cimport xmlschema
cimport xmlerror
cimport xinclude
cimport c14n
cimport cstd
import types

from xmlparser cimport xmlParserCtxt, xmlDict
import _elementpath
from StringIO import StringIO
import sys

DEBUG = False

cdef int PROXY_ELEMENT
cdef int PROXY_ATTRIB
cdef int PROXY_ATTRIB_ITER
cdef int PROXY_ELEMENT_ITER

PROXY_ELEMENT = 0
PROXY_ATTRIB = 1
PROXY_ATTRIB_ITER = 2
PROXY_ELEMENT_ITER = 3

# the rules
# any libxml C argument/variable is prefixed with c_
# any non-public function/class is prefixed with an underscore
# instance creation is always through factories

class Error(Exception):
    pass

class XPathError(Error):
    pass

class XPathContextError(XPathError):
    pass

class XPathNamespaceError(XPathError):
    pass

class XPathResultError(XPathError):
    pass

class XSLTError(Error):
    pass

class XSLTParseError(XSLTError):
    pass

class XSLTApplyError(XSLTError):
    pass

class XSLTSaveError(XSLTError):
    pass

class RelaxNGError(Error):
    pass

class RelaxNGParseError(RelaxNGError):
    pass

class RelaxNGValidateError(RelaxNGError):
    pass

class XMLSchemaError(Error):
    pass

class XMLSchemaParseError(XMLSchemaError):
    pass

class XMLSchemaValidateError(XMLSchemaError):
    pass

class XIncludeError(Error):
    pass

class C14NError(Error):
    pass

cdef class _DocumentBase:
    """Base class to reference a libxml document.

    When instances of this class are garbage collected, the libxml
    document is cleaned up.
    """
    cdef int _ns_counter
    cdef xmlDoc* _c_doc
    
    def __dealloc__(self):
        # if there are no more references to the document, it is safe
        # to clean the whole thing up, as all nodes have a reference to
        # the document
        #print "freeing document:", <int>self._c_doc
        #displayNode(<xmlNode*>self._c_doc, 0)
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
        self._doc._ns_counter = self._doc._ns_counter + 1
        c_ns = tree.xmlNewNs(c_node, href, prefix)
        return c_ns

cdef class _ElementTree(_DocumentBase):

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
        cdef tree.xmlSaveCtxt* save_ctxt
        cdef char* mem
        cdef int size
        
        # recognize a diversity of ways to spell this in Python
        if encoding in ('UTF-8', 'utf8', 'UTF8', 'utf-8'):
            encoding = 'UTF-8'

        filename = _getFilenameForFile(file)
        if filename is not None:
            # it's a file object, so write to file
            # XXX options? error handling?
            save_ctxt = tree.xmlSaveToFilename(filename, encoding, 0)
            tree.xmlSaveDoc(save_ctxt, self._c_doc)
            tree.xmlSaveClose(save_ctxt)
        else:
            # it's a string object
            tree.xmlDocDumpMemoryEnc(self._c_doc, &mem, &size, encoding)
            m = mem
            # XXX this is purely for ElementTree compatibility..
            if encoding == 'UTF-8' or encoding == 'us-ascii':
                # strip off XML prologue..
                i = m.find('\n')
                if i != -1:
                    m = m[i + 1:]
                # strip off ending \n..
                m = m[:-1]
            if encoding == 'UTF-8':
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

    # extensions to ElementTree API
    def xpath(self, path, namespaces=None):
        """XPath evaluate in context of document.

        namespaces is an optional dictionary with prefix to namespace URI
        mappings, used by XPath.
        
        Returns a list (nodeset), or bool, float or string.

        In case of a list result, return Element for element nodes,
        string for text and attribute values.

        Note: if you are going to apply multiple XPath expressions
        against the same document, it is more efficient to use
        XPathEvaluator directly.
        """
        return XPathDocumentEvaluator(self, namespaces).evaluate(path)

    def xslt(self, xslt, **kw):
        """Transform this document using other document.

        xslt is a tree that should be XSLT
        keyword parameters are XSLT transformation parameters.

        Returns the transformed tree.

        Note: if you are going to apply the same XSLT stylesheet against
        multiple documents, it is more efficient to use the XSLT
        class directly.
        """
        style = XSLT(xslt)
        return style.apply(self, **kw)

    def relaxng(self, relaxng):
        """Validate this document using other document.

        relaxng is a tree that should contain Relax NG XML

        Returns True or False, depending on whether validation
        succeeded.

        Note: if you are going to apply the same Relax NG schema against
        multiple documents, it is more efficient to use the RelaxNG
        class directly.
        """
        schema = RelaxNG(relaxng)
        return schema.validate(self)

    def xmlschema(self, xmlschema):
        """Validate this document using other doucment.

        xmlschema is a tree that should contain XML Schema XML.

        Returns True or False, depending on whether validation
        succeeded.

        Note: If you are going to applyt he same XML Schema against
        multiple documents, it is more efficient to use the XMLSchema
        class directly.
        """
        schema = XMLSchema(xmlschema)
        return schema.validate(self)
        
    def xinclude(self):
        """Process this document, including using XInclude.
        """
        cdef int result
        # XXX what happens memory-wise with the original XInclude nodes?
        # they seem to be still accessible if a reference to them has
        # been made previously, but I have no idea whether they get freed
        # at all. The XInclude nodes appear to be still being in the same
        # parent and same document, but they must not be connected to the
        # tree..
        result = xinclude.xmlXIncludeProcess(self._c_doc)
        if result == -1:
            raise XIncludeError, "XInclude processing failed"
        
    def write_c14n(self, file):
        """C14N write of document. Always writes UTF-8.
        """
        cdef char* data
        cdef int bytes
        bytes = c14n.xmlC14NDocDumpMemory(self._c_doc,
                                          NULL, 0, NULL, 1, &data)
        if bytes < 0:
            raise C14NError, "C18N failed"
        file.write(data)
        tree.xmlFree(data)
    
cdef _ElementTree _elementTreeFactory(xmlDoc* c_doc):
    cdef _ElementTree result
    result = _ElementTree()
    result._ns_counter = 0
    result._c_doc = c_doc
    return result

cdef class _Element(_NodeBase):
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
        changeDocumentBelow(element, self._doc)
        
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
        cdef _Element mynode
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
            changeDocumentBelow(mynode, self._doc)
            
    def set(self, key, value):
        self.attrib[key] = value
        
    def append(self, _Element element):
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
        changeDocumentBelow(element, self._doc)

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

    def insert(self, index, _Element element):
        cdef xmlNode* c_node
        cdef xmlNode* c_next
        c_node = _findChild(self._c_node, index)
        if c_node is NULL:
            self.append(element)
            return
        c_next = element._c_node.next
        tree.xmlAddPrevSibling(c_node, element._c_node)
        _moveTail(c_next, element._c_node)
        changeDocumentBelow(element, self._doc)

    def remove(self, _Element element):
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
            return _namespacedName(self._c_node)
    
        def __set__(self, value):
            cdef xmlNs* c_ns
            ns, text = _getNsTag(value)
            tree.xmlNodeSetName(self._c_node, text)
            if ns is None:
                return
            c_ns = self._getNs(ns)
            tree.xmlSetNs(self._c_node, c_ns)

    # not in ElementTree, read-only
    property prefix:
        def __get__(self):
            if self._c_node.ns is not NULL:
                if self._c_node.ns.prefix is not NULL:
                    return funicode(self._c_node.ns.prefix)
            return None
        
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

    def xpath(self, path, namespaces=None):
        return XPathElementEvaluator(self, namespaces).evaluate(path)

cdef _Element _elementFactory(_ElementTree etree, xmlNode* c_node):
    cdef _Element result
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

cdef class _Comment(_Element):
    def set(self, key, value):
        pass
    
    def append(self, _Element element):
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
    
cdef _Comment _commentFactory(_ElementTree etree, xmlNode* c_node):
    cdef _Comment result
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

cdef class _Attrib(_NodeBase):
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
                result.append(_namespacedName(c_node))
            c_node = c_node.next
        return result

    def values(self):
        result = []
        cdef xmlNode* c_node
        c_node = <xmlNode*>(self._c_node.properties)
        while c_node is not NULL:
            if c_node.type == tree.XML_ATTRIBUTE_NODE:
                result.append(self._getValue(c_node))
            c_node = c_node.next
        return result

    cdef object _getValue(self, xmlNode* c_node):
        if c_node.ns is NULL or c_node.ns.href is NULL:
            value = tree.xmlGetNoNsProp(self._c_node, c_node.name)
        else:
            value = tree.xmlGetNsProp(
                self._c_node, c_node.name, c_node.ns.href)
        return funicode(value)
    
    def items(self):
        result = []
        cdef xmlNode* c_node
        c_node = <xmlNode*>(self._c_node.properties)
        while c_node is not NULL:
            if c_node.type == tree.XML_ATTRIBUTE_NODE:
                result.append((
                    _namespacedName(c_node),
                    self._getValue(c_node)
                    ))
            c_node = c_node.next
        return result
    
cdef _Attrib _attribFactory(_ElementTree etree, xmlNode* c_node):
    cdef _Attrib result
    result = getProxy(c_node, PROXY_ATTRIB)
    if result is not None:
        return result
    result = _Attrib()
    result._doc = etree
    result._c_node = c_node
    result._proxy_type = PROXY_ATTRIB
    registerProxy(result, PROXY_ATTRIB)
    return result

cdef class _AttribIterator(_NodeBase):
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
    
cdef _AttribIterator _attribIteratorFactory(_ElementTree etree,
                                            xmlNode* c_node):
    cdef _AttribIterator result
    result = getProxy(c_node, PROXY_ATTRIB_ITER)
    if result is not None:
        return result
    result = _AttribIterator()
    result._doc = etree
    result._c_node = c_node
    result._proxy_type = PROXY_ATTRIB_ITER
    registerProxy(result, PROXY_ATTRIB_ITER)
    return result

cdef class _ElementIterator(_NodeBase):
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

cdef _ElementIterator _elementIteratorFactory(_ElementTree etree,
                                              xmlNode* c_node):
    cdef _ElementIterator result
    result = getProxy(c_node, PROXY_ELEMENT_ITER)
    if result is not None:
        return result
    result = _ElementIterator()
    result._doc = etree
    result._c_node = c_node
    result._proxy_type = PROXY_ELEMENT_ITER
    registerProxy(result, PROXY_ELEMENT_ITER)
    return result

cdef xmlNode* _createElement(xmlDoc* c_doc, object tag,
                             object attrib, object extra):
    cdef xmlNode* c_node
    tag_utf = tag.encode('UTF-8')
    if attrib is None:
        attrib = {}
    attrib.update(extra)
    c_node = tree.xmlNewDocNode(c_doc, NULL, tag_utf, NULL)
    for name, value in attrib.items():
        name_utf = name.encode('UTF-8')
        value_utf = value.encode('UTF-8')
        tree.xmlNewProp(c_node, name_utf, value_utf)
    return c_node

cdef xmlNode* _createComment(xmlDoc* c_doc, char* text):
    cdef xmlNode* c_node
    c_node = tree.xmlNewDocComment(c_doc, text)
    return c_node

# module-level API for ElementTree

def Element(tag, attrib=None, nsmap=None, **extra):
    cdef xmlNode* c_node
    cdef _ElementTree etree
    etree = ElementTree()
    c_node = _createElement(etree._c_doc, tag, attrib, extra)
    tree.xmlDocSetRootElement(etree._c_doc, c_node)
    # add namespaces to node if necessary
    _addNamespaces(etree._c_doc, c_node, nsmap)
    # XXX hack for namespaces
    result = _elementFactory(etree, c_node)
    result.tag = tag
    return result

def Comment(text=None):
    cdef xmlNode* c_node
    cdef _ElementTree etree
    if text is None:
        text = ''
    text = ' %s ' % text.encode('UTF-8')
    etree = ElementTree()
    c_node = _createComment(etree._c_doc, text)
    tree.xmlAddChild(<xmlNode*>etree._c_doc, c_node)
    return _commentFactory(etree, c_node)

def SubElement(_Element parent, tag, attrib=None, nsmap=None, **extra):
    cdef xmlNode* c_node
    cdef _Element element
    c_node = _createElement(parent._doc._c_doc, tag, attrib, extra)
    element = _elementFactory(parent._doc, c_node)
    parent.append(element)
    # add namespaces to node if necessary
    _addNamespaces(parent._doc._c_doc, c_node, nsmap)
    # XXX hack for namespaces
    element.tag = tag
    return element

def ElementTree(_Element element=None, file=None):
    cdef xmlDoc* c_doc
    cdef xmlNode* c_next
    cdef xmlNode* c_node
    cdef xmlNode* c_node_copy
    cdef _ElementTree etree
    
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
        changeDocumentBelow(element, etree)
    
    return etree

def XML(text):
    cdef xmlDoc* c_doc
    c_doc = theParser.parseDoc(text.encode('UTF-8'))
    return _elementTreeFactory(c_doc).getroot()

fromstring = XML

def iselement(element):
    return isinstance(element, _Element)

def dump(_NodeBase elem):
    assert elem is not None, "Must supply element."
    _dumpToFile(sys.stdout, elem._doc._c_doc, elem._c_node)

def tostring(_NodeBase element, encoding='us-ascii'):
    cdef _DocumentBase doc
    cdef tree.xmlOutputBuffer* c_buffer
    cdef tree.xmlCharEncodingHandler* enchandler
    cdef char* enc

    assert element is not None
    
    #if encoding is None:
    #    encoding = 'UTF-8'
    if encoding in ('utf8', 'UTF8', 'utf-8'):
        encoding = 'UTF-8'
    doc = element._doc
    if element is element._doc.getroot():
        f = StringIO()
        doc.write(f, encoding)
        return f.getvalue()
    enc = encoding
    # it is necessary to *and* find the encoding handler *and* use
    # encoding during output
    enchandler = tree.xmlFindCharEncodingHandler(enc)
    c_buffer = tree.xmlAllocOutputBuffer(enchandler)
    tree.xmlNodeDumpOutput(c_buffer, doc._c_doc, element._c_node, 0, 0,
                           enc)
    _dumpNextNode(c_buffer, doc._c_doc, element._c_node, enc)
    tree.xmlOutputBufferFlush(c_buffer)
    if c_buffer.conv is not NULL: 
        result = tree.xmlBufferContent(c_buffer.conv)
    else:
        result = tree.xmlBufferContent(c_buffer.buffer)
    tree.xmlOutputBufferClose(c_buffer)
    return result

def parse(source, parser=None):
    # XXX ignore parser for now
    cdef xmlDoc* c_doc

    # XXX simplistic StringIO support
    if isinstance(source, StringIO):
        c_doc = theParser.parseDoc(source.getvalue())
        return _elementTreeFactory(c_doc)

    filename = _getFilenameForFile(source)
    if filename is None:
        filename = source
        
    # open filename
    c_doc = theParser.parseDocFromFile(filename)
    result = _elementTreeFactory(c_doc)
    return result

cdef _addNamespaces(xmlDoc* c_doc, xmlNode* c_node, object nsmap):
    cdef xmlNs* c_ns
    if nsmap is None:
        return
    for prefix, href in nsmap.items():
        # add namespace with prefix if ns is not already known
        c_ns = tree.xmlSearchNsByHref(c_doc, c_node, href)
        if c_ns is NULL:
            if prefix is not None:
                tree.xmlNewNs(c_node, href, prefix)
            else:
                tree.xmlNewNs(c_node, href, NULL)
        
cdef class XPathDocumentEvaluator:
    """Create an XPath evaluator for a document.
    """
    cdef xpath.xmlXPathContext* _c_ctxt
    cdef _ElementTree _doc
    cdef object _extension_functions
    cdef object _exc_info
    cdef object _namespaces
    cdef object _extensions
    cdef object _temp_elements
    cdef object _temp_docs
    
    def __init__(self, _ElementTree doc,
                 namespaces=None, extensions=None):
        cdef xpath.xmlXPathContext* xpathCtxt
        cdef int ns_register_status
        
        xpathCtxt = xpath.xmlXPathNewContext(doc._c_doc)
        if xpathCtxt is NULL:
            # XXX what triggers this exception?
            raise XPathContextError, "Unable to create new XPath context"

        self._doc = doc
        self._c_ctxt = xpathCtxt
        self._c_ctxt.userData = <void*>self
        self._namespaces = namespaces
        self._extensions = extensions
        
        if namespaces is not None:
            self.registerNamespaces(namespaces)
        self._extension_functions = {}
        if extensions is not None:
            for extension in extensions:
                self._extension_functions.update(extension)
                for (ns_uri, name), function in extension.items():
                    if ns_uri is not None:
                        xpath.xmlXPathRegisterFuncNS(
                            xpathCtxt, name, ns_uri, _xpathCallback)
                    else:
                        xpath.xmlXPathRegisterFunc(
                            xpathCtxt, name, _xpathCallback)
                        
    def __dealloc__(self):
        xpath.xmlXPathFreeContext(self._c_ctxt)
    
    def registerNamespace(self, prefix, uri):
        """Register a namespace with the XPath context.
        """
        s_prefix = prefix.encode('UTF8')
        s_uri = uri.encode('UTF8')
        # XXX should check be done to verify namespace doesn't already exist?
        ns_register_status = xpath.xmlXPathRegisterNs(
            self._c_ctxt, s_prefix, s_uri)
        if ns_register_status != 0:
            # XXX doesn't seem to be possible to trigger this
            # from Python
            raise XPathNamespaceError, (
                "Unable to register namespaces with prefix "
                "%s and uri %s" % (prefix, uri))

    def registerNamespaces(self, namespaces):
        """Register a prefix -> uri dict.
        """
        for prefix, uri in namespaces.items():
            self.registerNamespace(prefix, uri)
    
    def evaluate(self, path):
        return self._evaluate(path, NULL)

    cdef object _evaluate(self, path, xmlNode* c_ctxt_node):
        cdef xpath.xmlXPathObject* xpathObj
        cdef xmlNode* c_node
        
        # if element context is requested; unfortunately need to modify ctxt
        self._c_ctxt.node = c_ctxt_node

        path = path.encode('UTF-8')
        self._exc_info = None
        self._release()
        xpathObj = xpath.xmlXPathEvalExpression(path, self._c_ctxt)
        if self._exc_info is not None:
            type, value, traceback = self._exc_info
            self._exc_info = None
            raise type, value, traceback
        if xpathObj is NULL:
            raise SyntaxError, "Error in xpath expression."
        try:
            result = _unwrapXPathObject(xpathObj, self._doc)
        except XPathResultError:
            #self._release()
            xpath.xmlXPathFreeObject(xpathObj)
            raise
        xpath.xmlXPathFreeObject(xpathObj)
        # release temporarily held python stuff
        #self._release()
        return result
        
    #def clone(self):
    #    # XXX pretty expensive so calling this from callback is probably
    #    # not desirable
    #    return XPathEvaluator(self._doc, self._namespaces, self._extensions)

    def _release(self):
        self._temp_elements = {}
        self._temp_docs = {}
        
    def _hold(self, obj):
        """A way to temporarily hold references to nodes in the evaluator.

        This is needed because otherwise nodes created in XPath extension
        functions would be reference counted too soon, during the
        XPath evaluation.
        """
        cdef _NodeBase element
        if isinstance(obj, _NodeBase):
            obj = [obj]
        if not type(obj) in (type([]), type(())):
            return
        for o in obj:
            if isinstance(o, _NodeBase):
                element = <_NodeBase>o
                #print "Holding element:", <int>element._c_node
                self._temp_elements[id(element)] = element
                #print "Holding document:", <int>element._doc._c_doc
                self._temp_docs[id(element._doc)] = element._doc

cdef class XPathElementEvaluator(XPathDocumentEvaluator):
    """Create an XPath evaluator for an element.
    """
    cdef _Element _element
    
    def __init__(self, _Element element, namespaces=None, extensions=None):
        XPathDocumentEvaluator.__init__(
            self, element._doc, namespaces, extensions)
        self._element = element
        
    def evaluate(self, path):
        return self._evaluate(path, self._element._c_node)

def XPathEvaluator(doc_or_element, namespaces=None, extensions=None):
    if isinstance(doc_or_element, _DocumentBase):
        return XPathDocumentEvaluator(doc_or_element, namespaces, extensions)
    else:
        return XPathElementEvaluator(doc_or_element, namespaces, extensions)
    
def Extension(module, function_mapping, ns_uri=None):
    result = {}
    for function_name, xpath_name in function_mapping.items():
        result[(ns_uri, xpath_name)] = getattr(module, function_name)
    return result

cdef xpath.xmlXPathObject* _wrapXPathObject(object obj) except NULL:
    cdef xpath.xmlNodeSet* resultSet
    cdef _NodeBase node
    if isinstance(obj, str):
        # XXX use the Wrap variant? Or leak...
        return xpath.xmlXPathNewCString(obj)
    if isinstance(obj, unicode):
        obj = obj.encode("utf-8")
        return xpath.xmlXPathNewCString(obj)
    if isinstance(obj, types.BooleanType):
        return xpath.xmlXPathNewBoolean(obj)
    if isinstance(obj, (int, float)):
        return xpath.xmlXPathNewFloat(obj)
    if isinstance(obj, _NodeBase):
        obj = [obj]
    if isinstance(obj, (types.ListType, types.TupleType)):
        resultSet = xpath.xmlXPathNodeSetCreate(NULL)
        for element in obj:
            if isinstance(element, _NodeBase):
                node = <_NodeBase>element
                xpath.xmlXPathNodeSetAdd(resultSet, node._c_node)
            else:
                raise XPathResultError, "This is not a node: %s" % element
        return xpath.xmlXPathWrapNodeSet(resultSet)
    else:
        raise XPathResultError, "Unknown return type: %s" % obj
    return NULL

cdef object _unwrapXPathObject(xpath.xmlXPathObject* xpathObj,
                               _ElementTree doc):
    if xpathObj.type == xpath.XPATH_UNDEFINED:
        raise XPathResultError, "Undefined xpath result"
    elif xpathObj.type == xpath.XPATH_NODESET:
        return _createNodeSetResult(doc, xpathObj)
    elif xpathObj.type == xpath.XPATH_BOOLEAN:
        return bool(xpathObj.boolval)
    elif xpathObj.type == xpath.XPATH_NUMBER:
        return xpathObj.floatval
    elif xpathObj.type == xpath.XPATH_STRING:
        return funicode(xpathObj.stringval)
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
        raise XPathResultError, "Unknown xpath result %s" % str(xpathObj.type)

cdef object _createNodeSetResult(_ElementTree doc,
                                 xpath.xmlXPathObject* xpathObj):
    cdef xmlNode* c_node
    cdef char* s
    cdef _NodeBase element
    result = []
    if xpathObj.nodesetval is NULL:
        return result
    for i from 0 <= i < xpathObj.nodesetval.nodeNr:
        c_node = xpathObj.nodesetval.nodeTab[i]
        if c_node.type == tree.XML_ELEMENT_NODE:
            element = _elementFactory(doc, c_node)
            result.append(element)
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

cdef void _xpathCallback(xpath.xmlXPathParserContext* ctxt, int nargs):
    cdef xpath.xmlXPathContext* rctxt
    cdef _ElementTree doc
    cdef xpath.xmlXPathObject* obj
    cdef XPathDocumentEvaluator evaluator
    
    rctxt = ctxt.context
    
    # get information on what function is called
    name = rctxt.function
    if rctxt.functionURI is not NULL:
        uri = rctxt.functionURI
    else:
        uri = None

    # get our evaluator
    evaluator = <XPathDocumentEvaluator>(rctxt.userData)

    # lookup up the extension function in the evaluator
    f = evaluator._extension_functions[(uri, name)]
    
    args = []
    doc = evaluator._doc
    for i from 0 <= i < nargs:
        args.append(_unwrapXPathObject(xpath.valuePop(ctxt), doc))
    args.reverse()

    try:
        # call the function
        res = f(evaluator, *args)
        # hold python objects temporarily so that they won't get deallocated
        # during processing
        evaluator._hold(res)
        # now wrap for XPath consumption
        obj = _wrapXPathObject(res)
    except:
        xpath.xmlXPathErr(
            ctxt,
            xmlerror.XML_XPATH_EXPR_ERROR - xmlerror.XML_XPATH_EXPRESSION_OK)
        evaluator._exc_info = sys.exc_info()
        return
    xpath.valuePush(ctxt, obj)

cdef class XSLT:
    """Turn a document into an XSLT object.
    """
    cdef xslt.xsltStylesheet* _c_style
    
    def __init__(self, _ElementTree doc):
        # make a copy of the document as stylesheet needs to assume it
        # doesn't change
        cdef xslt.xsltStylesheet* c_style
        cdef xmlDoc* c_doc
        c_doc = tree.xmlCopyDoc(doc._c_doc, 1)
        # XXX work around bug in xmlCopyDoc (fix is upcoming in new release
        # of libxml2)
        if doc._c_doc.URL is not NULL:
            c_doc.URL = tree.xmlStrdup(doc._c_doc.URL)
            
        c_style = xslt.xsltParseStylesheetDoc(c_doc)
        if c_style is NULL:
            raise XSLTParseError, "Cannot parse style sheet"
        self._c_style = c_style
        # XXX is it worthwile to use xsltPrecomputeStylesheet here?
        
    def __dealloc__(self):
        # this cleans up copy of doc as well
        xslt.xsltFreeStylesheet(self._c_style)
        
    def apply(self, _ElementTree doc, **kw):
        cdef xmlDoc* c_result
        cdef char** params
        cdef int i
        cdef int j
        if kw:
            # encode as UTF-8; somehow can't put this in main params
            # array construction loop..
            new_kw = {}
            for key, value in kw.items():
                k = key.encode('UTF-8')
                v = value.encode('UTF-8')
                new_kw[k] = v
            # allocate space for parameters
            # * 2 as we want an entry for both key and value,
            # and + 1 as array is NULL terminated
            params = <char**>cstd.malloc(sizeof(char*) * (len(kw) * 2 + 1))
            i = 0
            for key, value in new_kw.items():
                params[i] = key
                i = i + 1
                params[i] = value
                i = i + 1
            params[i] = NULL
        else:
            params = NULL
        c_result = xslt.xsltApplyStylesheet(self._c_style, doc._c_doc, params)
        if params is not NULL:
            # deallocate space for parameters again
            cstd.free(params)
        if c_result is NULL:
            raise XSLTApplyError, "Error applying stylesheet"
        # XXX should set special flag to indicate this is XSLT result
        # so that xsltSaveResultTo* functional can be used during
        # serialize?
        return _elementTreeFactory(c_result)

    def tostring(self, _ElementTree doc):
        """Save result doc to string using stylesheet as guidance.
        """
        cdef char* s
        cdef int l
        cdef int r
        r = xslt.xsltSaveResultToString(&s, &l, doc._c_doc, self._c_style)
        if r == -1:
            raise XSLTSaveError, "Error saving stylesheet result to string"
        result = funicode(s)
        tree.xmlFree(s)
        return result

cdef class RelaxNG:
    """Turn a document into an Relax NG validator.
    Can also load from filesystem directly given file object or filename.
    """
    cdef relaxng.xmlRelaxNG* _c_schema
    
    def __init__(self, _ElementTree tree=None, file=None):
        cdef relaxng.xmlRelaxNGParserCtxt* parser_ctxt
                    
        if tree is not None:
            parser_ctxt = relaxng.xmlRelaxNGNewDocParserCtxt(tree._c_doc)
        elif file is not None:
            filename = _getFilenameForFile(file)
            if filename is None:
                # XXX assume a string object
                filename = file
            parser_ctxt = relaxng.xmlRelaxNGNewParserCtxt(filename)
        else:
            raise RelaxNGParseError, "No tree or file given"
        if parser_ctxt is NULL:
            raise RelaxNGParseError, "Document is not valid Relax NG"
        self._c_schema = relaxng.xmlRelaxNGParse(parser_ctxt)
        if self._c_schema is NULL:
            relaxng.xmlRelaxNGFreeParserCtxt(parser_ctxt)
            raise RelaxNGParseError, "Document is not valid Relax NG"
        relaxng.xmlRelaxNGFreeParserCtxt(parser_ctxt)
        
    def __dealloc__(self):
        relaxng.xmlRelaxNGFree(self._c_schema)
        
    def validate(self, _ElementTree doc):
        """Validate doc using Relax NG.

        Returns true if document is valid, false if not."""
        cdef relaxng.xmlRelaxNGValidCtxt* valid_ctxt
        cdef int ret
        valid_ctxt = relaxng.xmlRelaxNGNewValidCtxt(self._c_schema)
        ret = relaxng.xmlRelaxNGValidateDoc(valid_ctxt, doc._c_doc)
        relaxng.xmlRelaxNGFreeValidCtxt(valid_ctxt)
        if ret == -1:
            raise RelaxNGValidateError, "Internal error in Relax NG validation"
        return ret == 0

cdef class XMLSchema:
    """Turn a document into an XML Schema validator.
    """
    cdef xmlschema.xmlSchema* _c_schema
    
    def __init__(self, _ElementTree tree):
        cdef xmlschema.xmlSchemaParserCtxt* parser_ctxt
        parser_ctxt = xmlschema.xmlSchemaNewDocParserCtxt(tree._c_doc)
        if parser_ctxt is NULL:
            raise XMLSchemaParseError, "Document is not valid XML Schema"
        self._c_schema = xmlschema.xmlSchemaParse(parser_ctxt)
        if self._c_schema is NULL:
            xmlschema.xmlSchemaFreeParserCtxt(parser_ctxt)
            raise XMLSchemaParseError, "Document is not valid XML Schema"
        xmlschema.xmlSchemaFreeParserCtxt(parser_ctxt)
        
    def __dealloc__(self):
        xmlschema.xmlSchemaFree(self._c_schema)

    def validate(self, _ElementTree doc):
        """Validate doc using XML Schema.

        Returns true if document is valid, false if not.
        """
        cdef xmlschema.xmlSchemaValidCtxt* valid_ctxt
        cdef int ret
        valid_ctxt = xmlschema.xmlSchemaNewValidCtxt(self._c_schema)
        ret = xmlschema.xmlSchemaValidateDoc(valid_ctxt, doc._c_doc)
        xmlschema.xmlSchemaFreeValidCtxt(valid_ctxt)
        if ret == -1:
            raise XMLSchemaValidateError, "Internal error in XML Schema validation."
        return ret == 0
        
# Globally shared XML parser to enable dictionary sharing
cdef class Parser:

    cdef xmlDict* _c_dict
    cdef int _parser_initialized
    
    def __init__(self):
        self._c_dict = NULL
        self._parser_initialized = 0
        
    def __dealloc__(self):
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
        cdef xmlDict* d

        result = tree.xmlNewDoc("1.0")

        if self._c_dict is NULL:
            # we need to get dict from the new document if it's there,
            # otherwise make one
            if result.dict is not NULL:
                d = result.dict
            else:
                d = xmlparser.xmlDictCreate()
                result.dict = d
            self._c_dict = d
            xmlparser.xmlDictReference(self._c_dict)
        else:
            # we need to reuse the central dict and get rid of the new one
            if result.dict is not NULL:
                xmlparser.xmlDictFree(result.dict)
            result.dict = self._c_dict
            xmlparser.xmlDictReference(result.dict)
        return result

cdef Parser theParser
theParser = Parser()

# Private helper functions
cdef _dumpToFile(f, xmlDoc* c_doc, xmlNode* c_node):
    cdef tree.PyObject* o
    cdef tree.xmlOutputBuffer* c_buffer
    
    if not tree.PyFile_Check(f):
        raise ValueError, "Not a file"
    o = <tree.PyObject*>f
    c_buffer = tree.xmlOutputBufferCreateFile(tree.PyFile_AsFile(o), NULL)
    tree.xmlNodeDumpOutput(c_buffer, c_doc, c_node, 0, 0, NULL)
    # dump next node if it's a text node
    _dumpNextNode(c_buffer, c_doc, c_node, NULL)
    tree.xmlOutputBufferWriteString(c_buffer, '\n')
    tree.xmlOutputBufferFlush(c_buffer)

cdef _dumpNextNode(tree.xmlOutputBuffer* c_buffer, xmlDoc* c_doc,
                   xmlNode* c_node, char* encoding):
    cdef xmlNode* c_next
    c_next = c_node.next
    if not (c_next is not NULL and c_next.type == tree.XML_TEXT_NODE):
        c_next = NULL
    if c_next is not NULL:
        tree.xmlNodeDumpOutput(c_buffer, c_doc, c_next, 0, 0, encoding)   
    
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
    """Unlink and free a node and subnodes if possible.
    """
    tree.xmlUnlinkNode(c_node)
    attemptDeallocation(c_node)

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

cdef object _namespacedName(xmlNode* c_node):
    if c_node.ns is NULL or c_node.ns.href is NULL:
        return funicode(c_node.name)
    else:
        # XXX optimize
        s = "{%s}%s" % (c_node.ns.href, c_node.name)
        return funicode(s)

def _getFilenameForFile(source):
    """Given a Python File object, give filename back.

    Returns None if not a file object.
    """
    if tree.PyFile_Check(source):
        # this is a file object, so retrieve file name
        filename = tree.PyFile_Name(source)
        # XXX this is a hack that makes to seem a crash go away;
        # filename is a borrowed reference which may be what's tripping
        # things up
        tree.Py_INCREF(filename)
        return filename
    else:
        return None

cdef void nullGenericErrorFunc(void* ctxt, char* msg, ...):
    pass

cdef void nullStructuredErrorFunc(void* userData,
                                  xmlerror.xmlError* error):
    pass

cdef void _shutUpLibxmlErrors():
    xmlerror.xmlSetGenericErrorFunc(NULL, nullGenericErrorFunc)
    xmlerror.xmlSetStructuredErrorFunc(NULL, nullStructuredErrorFunc)

cdef void _shutUpLibxsltErrors():
    xslt.xsltSetGenericErrorFunc(NULL, nullGenericErrorFunc)
    # xslt.xsltSetTransformErrorFunc

# ugly global shutting up of all errors, but seems to work..
if not DEBUG:
    _shutUpLibxmlErrors()
    _shutUpLibxsltErrors()
    
# backpointer functionality

cdef struct _ProxyRef

cdef struct _ProxyRef:
    tree.PyObject* proxy
    int type
    _ProxyRef* next
        
ctypedef _ProxyRef ProxyRef

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
    result = <ProxyRef*>cstd.malloc(sizeof(ProxyRef))
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


cdef void changeDocumentBelow(_NodeBase node,
                              _DocumentBase doc):
    """For a node and all nodes below, change document.

    A node can change document in certain operations as an XML
    subtree can move. This updates all possible proxies in the
    tree below (including the current node). It also reconciliates
    namespaces so they're correct inside the new environment.
    """
    changeDocumentBelowHelper(node._c_node, doc)
    tree.xmlReconciliateNs(doc._c_doc, node._c_node)
    
cdef void changeDocumentBelowHelper(xmlNode* c_node,
                                    _DocumentBase doc):
    cdef ProxyRef* ref
    cdef xmlNode* c_current
    cdef xmlAttr* c_attr_current
    cdef _NodeBase proxy

    if c_node is NULL:
        return
    # different _c_doc
    c_node.doc = doc._c_doc
    
    if c_node._private is not NULL:
        ref = <ProxyRef*>c_node._private
        while ref is not NULL:
            proxy = <_NodeBase>ref.proxy
            proxy._doc = doc
            ref = ref.next

    # adjust all children
    c_current = c_node.children
    while c_current is not NULL:
        changeDocumentBelowHelper(c_current, doc)
        c_current = c_current.next
        
    # adjust all attributes
    c_attr_current = c_node.properties
    while c_attr_current is not NULL:
        changeDocumentBelowHelper(c_current, doc)
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
    #print "trying to do deallocating:", c_node.type
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
    # cannot free a top which has proxies pointing to it
    if c_top._private is not NULL:
        #print "Not freeing: proxies still exist"
        return NULL
    # see whether we have children to deallocate
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
