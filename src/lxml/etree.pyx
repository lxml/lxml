cimport tree, python
from tree cimport xmlDoc, xmlNode, xmlAttr, xmlNs, _isElement
from python cimport isinstance, hasattr
cimport xpath
cimport xslt
cimport xmlerror
cimport xinclude
cimport c14n
cimport cstd
import re

import _elementpath
from StringIO import StringIO
import sys

# the rules
# any libxml C argument/variable is prefixed with c_
# any non-public function/class is prefixed with an underscore
# instance creation is always through factories

ctypedef enum LXML_PROXY_TYPE:
    PROXY_ELEMENT
    PROXY_ATTRIB

# what to do with libxml2/libxslt error messages?
# 0 : drop
# 1 : use log
cdef int __DEBUG
__DEBUG = 1

# maximum number of lines in the libxml2/xslt log if __DEBUG == 1
cdef int __MAX_LOG_SIZE
__MAX_LOG_SIZE = 100

# make the compiled-in debug state publicly available
DEBUG = __DEBUG

# Error superclass for ElementTree compatibility
class Error(Exception):
    pass

# module level superclass for all exceptions
class LxmlError(Error):
    def __init__(self, *args):
        Error.__init__(self, *args)
        self.error_log = __copyGlobalErrorLog()

# superclass for all syntax errors
class LxmlSyntaxError(LxmlError, SyntaxError):
    pass

class XIncludeError(LxmlError):
    pass

class C14NError(LxmlError):
    pass

cdef class _Document:
    """Internal base class to reference a libxml document.

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

    def getroot(self):
        cdef xmlNode* c_node
        c_node = tree.xmlDocGetRootElement(self._c_doc)
        if c_node is NULL:
            return None
        return _elementFactory(self, c_node)

    def buildNewPrefix(self):
        ns = "ns%d" % self._ns_counter
        self._ns_counter = self._ns_counter + 1
        return ns

    cdef xmlNs* _findOrBuildNodeNs(self, xmlNode* c_node, char* href):
        """Get or create namespace structure for a node.
        """
        cdef xmlNs* c_ns
        # look for existing ns
        c_ns = tree.xmlSearchNsByHref(self._c_doc, c_node, href)
        if c_ns is not NULL:
            return c_ns
        # create ns if existing ns cannot be found
        # try to simulate ElementTree's namespace prefix creation
        prefix = self.buildNewPrefix()
        c_ns = tree.xmlNewNs(c_node, href, prefix)
        return c_ns

    cdef void _setNodeNs(self, xmlNode* c_node, char* href):
        "Lookup namespace structure and set it for the node."
        cdef xmlNs* c_ns
        c_ns = self._findOrBuildNodeNs(c_node, href)
        tree.xmlSetNs(c_node, c_ns)

    cdef void _setNodeNamespaces(self, xmlNode* c_node,
                                 object node_ns_utf, object nsmap):
        """Lookup current namespace prefixes, then set namespace structure for
        node and register new ns-prefix mappings.
        """
        cdef xmlNs*  c_ns
        cdef xmlDoc* c_doc
        cdef char*   c_prefix
        cdef char*   c_href
        if not nsmap:
            if node_ns_utf is not None:
                self._setNodeNs(c_node, node_ns_utf)
            return

        c_doc  = self._c_doc
        for prefix, href in nsmap.items():
            href_utf = _utf8(href)
            c_href = href_utf
            if prefix is not None:
                prefix_utf = _utf8(prefix)
                c_prefix = prefix_utf
            else:
                c_prefix = NULL
            # add namespace with prefix if ns is not already known
            c_ns = tree.xmlSearchNsByHref(c_doc, c_node, c_href)
            if c_ns is NULL:
                c_ns = tree.xmlNewNs(c_node, c_href, c_prefix)
            if href_utf == node_ns_utf:
                tree.xmlSetNs(c_node, c_ns)
                node_ns_utf = None

        if node_ns_utf is not None:
            self._setNodeNs(c_node, node_ns_utf)

cdef _Document _parseDocument(source, parser):
    cdef xmlDoc* c_doc
    # XXX simplistic (c)StringIO support
    if hasattr(source, 'getvalue'):
        c_doc = theParser.parseDoc(source.getvalue(), parser)
    else:
        filename = _getFilenameForFile(source)
        # Support for unamed file-like object (eg urlgrabber.urlopen)
        if not filename and hasattr(source, 'read'):
            c_doc = theParser.parseDoc(source.read(), parser)
        # Otherwise parse the file directly from the filesystem
        else:
            if filename is None:
                filename = source
            # open filename
            c_doc = theParser.parseDocFromFile(filename, parser)
    if c_doc is NULL:
        return None
    else:
        return _documentFactory(c_doc)

cdef _Document _documentFactory(xmlDoc* c_doc):
    cdef _Document result
    result = _Document()
    result._c_doc = c_doc
    result._ns_counter = 0
    return result

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

    By pointing to a Document instance, a reference is kept to
    _Document as long as there is some pointer to a node in it.
    """
    cdef _Document _doc
    cdef xmlNode* _c_node
    cdef int _proxy_type
    
    def __dealloc__(self):
        #print "trying to free node:", <int>self._c_node
        #displayNode(self._c_node, 0)
        if self._c_node is not NULL:
            unregisterProxy(self)
        attemptDeallocation(self._c_node)

    def _init(self):
        """Called after object initialisation. Subclasses may override
        this if they recursively call _init() in the superclasses.
        """

cdef class _ElementTree:
    cdef _Document _doc
    cdef _NodeBase _context_node

    def parse(self, source, parser=None):
        """Updates self with the content of source and returns its root
        """
        self._doc          = _parseDocument(source, parser)
        self._context_node = self._doc.getroot()
        return self._context_node
    
    def getroot(self):
        return self._context_node
    
    def write(self, file, encoding='us-ascii'):
        if not hasattr(file, 'write'):
            # file is a filename, we want a file object
            file = open(file, 'wb')

        m = tostring(self._context_node, encoding)
        # XXX this is purely for ElementTree compatibility..
        if encoding == 'UTF-8' or encoding == 'us-ascii':
            m = _stripDeclaration(m)
            if m[-1:] == '\n':
                m = m[:-1]
        file.write(m)

    def getiterator(self, tag=None):
        root = self.getroot()
        if root is None:
            return ()
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
    def xpath(self, _path, namespaces=None, **_variables):
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
        return XPathDocumentEvaluator(self._doc, namespaces).evaluate(_path, **_variables)

    def xslt(self, _xslt, extensions=None, **_kw):
        """Transform this document using other document.

        xslt is a tree that should be XSLT
        keyword parameters are XSLT transformation parameters.

        Returns the transformed tree.

        Note: if you are going to apply the same XSLT stylesheet against
        multiple documents, it is more efficient to use the XSLT
        class directly.
        """
        style = XSLT(_xslt, extensions)
        return style(self, **_kw)

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
        result = xinclude.xmlXIncludeProcessTree(self._context_node._c_node)
        if result == -1:
            raise XIncludeError, "XInclude processing failed"
        
    def write_c14n(self, file):
        """C14N write of document. Always writes UTF-8.
        """
        cdef xmlDoc* c_base_doc
        cdef xmlDoc* c_doc
        cdef char* data
        cdef int bytes
        c_base_doc = self._doc._c_doc

        c_doc = _fakeRootDoc(c_base_doc, self._context_node._c_node)
        bytes = c14n.xmlC14NDocDumpMemory(c_doc, NULL, 0, NULL, 1, &data)
        _destroyFakeDoc(c_base_doc, c_doc)

        if bytes < 0:
            raise C14NError, "C14N failed"
        if not hasattr(file, 'write'):
            file = open(file, 'wb')
        file.write(data)
        tree.xmlFree(data)
    
cdef _ElementTree _elementTreeFactory(_Document doc,
                                      _NodeBase context_node):
    return _newElementTree(doc, context_node, _ElementTree)

cdef _ElementTree _newElementTree(_Document doc, _NodeBase context_node,
                                  object baseclass):
    cdef _ElementTree result
    result = baseclass()
    result._doc = doc
    if context_node is None and doc is not None:
        context_node = doc.getroot()
    result._context_node = context_node
    return result

cdef class _Element(_NodeBase):
    # MANIPULATORS

    def __setitem__(self, index, _NodeBase element):
        cdef xmlNode* c_node
        cdef xmlNode* c_next
        cdef int foreign
        c_node = _findChild(self._c_node, index)
        if c_node is NULL:
            raise IndexError
        foreign = self._doc is not element._doc
        c_next = element._c_node.next
        _removeText(c_node.next)
        tree.xmlReplaceNode(c_node, element._c_node)
        _moveTail(c_next, element._c_node)
        changeDocumentBelow(element, self._doc, foreign)
        
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
        cdef int foreign
        # first, find start of slice
        c_node = _findChild(self._c_node, start)
        # now delete the slice
        if start != stop:
            c_node = _deleteSlice(c_node, start, stop)
        # if the insertion point is at the end, append there
        if c_node is NULL:
            for node in value:
                self.append(node)
            return
        # if the next element is in the list, insert before it
        for node in value:
            _raiseIfNone(node)
            mynode = node
            foreign = self._doc is not mynode._doc
            # store possible text tail
            c_next = mynode._c_node.next
            # now move node previous to insertion point
            tree.xmlUnlinkNode(mynode._c_node)
            tree.xmlAddPrevSibling(c_node, mynode._c_node)
            # and move tail just behind his node
            _moveTail(c_next, mynode._c_node)
            # move it into a new document
            changeDocumentBelow(mynode, self._doc, foreign)

    def __deepcopy__(self, memo):
        return self.__copy__()
        
    def __copy__(self):
        cdef xmlNode* c_node
        cdef xmlDoc* c_doc
        c_doc = theParser.newDoc()
        doc = _documentFactory(c_doc)
        c_node = tree.xmlDocCopyNode(self._c_node, c_doc, 1)
        tree.xmlDocSetRootElement(c_doc, c_node)
        return _elementFactory(doc, c_node)
        
    def set(self, key, value):
        self.attrib[key] = value
        
    def append(self, _Element element):
        cdef xmlNode* c_next
        cdef xmlNode* c_node
        cdef int foreign
        _raiseIfNone(element)
        foreign = self._doc is not element._doc
        c_node = element._c_node
        # store possible text node
        c_next = c_node.next
        # XXX what if element is coming from a different document?
        tree.xmlUnlinkNode(c_node)
        # move node itself
        tree.xmlAddChild(self._c_node, c_node)
        _moveTail(c_next, c_node)
        # uh oh, elements may be pointing to different doc when
        # parent element has moved; change them too..
        changeDocumentBelow(element, self._doc, foreign)

    def clear(self):
        cdef xmlAttr* c_attr
        cdef xmlAttr* c_attr_next
        cdef xmlNode* c_node
        cdef xmlNode* c_node_next
        c_node = self._c_node
        # remove self.text and self.tail
        _removeText(c_node.children)
        _removeText(c_node.next)
        # remove all attributes
        c_attr = c_node.properties
        while c_attr is not NULL:
            c_attr_next = c_attr.next
            tree.xmlRemoveProp(c_attr)
            c_attr = c_attr_next
        # remove all subelements
        c_node = c_node.children
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
        cdef int foreign
        _raiseIfNone(element)
        c_node = _findChild(self._c_node, index)
        if c_node is NULL:
            self.append(element)
            return
        foreign = self._doc is not element._doc
        c_next = element._c_node.next
        tree.xmlAddPrevSibling(c_node, element._c_node)
        _moveTail(c_next, element._c_node)
        changeDocumentBelow(element, self._doc, foreign)

    def remove(self, _Element element):
        cdef xmlNode* c_node
        _raiseIfNone(element)
        c_node = element._c_node
        if c_node.parent is not self._c_node:
            raise ValueError, "Element is not a child of this node."
        _removeText(c_node.next)
        tree.xmlUnlinkNode(c_node)
        
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
            self._doc._setNodeNs(self._c_node, ns)

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
            return _collectText(self._c_node.children)
        
        def __set__(self, value):
            cdef xmlNode* c_text_node
            # remove all text nodes at the start first
            _removeText(self._c_node.children)
            if value is None:
                return
            # now add new text node with value at start
            text = _utf8(value)
            c_text_node = tree.xmlNewDocText(self._doc._c_doc,
                                             text)
            if self._c_node.children is NULL:
                tree.xmlAddChild(self._c_node, c_text_node)
            else:
                tree.xmlAddPrevSibling(self._c_node.children,
                                       c_text_node)
        
    property tail:
        def __get__(self):
            return _collectText(self._c_node.next)
           
        def __set__(self, value):
            cdef xmlNode* c_text_node
            # remove all text nodes at the start first
            _removeText(self._c_node.next)
            if value is None:
                return
            text = _utf8(value)
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
        cdef _Document doc
        cdef int c
        # this does not work for negative start, stop, however,
        # python seems to convert these to positive start, stop before
        # calling, so this all works perfectly (at the cost of a len() call)
        c_node = _findChild(self._c_node, start)
        if c_node is NULL:
            return []
        c = start
        result = []
        doc = self._doc
        while c_node is not NULL and c < stop:
            if _isElement(c_node):
                ret = python.PyList_Append(result, _elementFactory(doc, c_node))
                if ret:
                    raise
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

    def __nonzero__(self):
        cdef xmlNode* c_node
        c_node = _findChildBackwards(self._c_node, 0)
        return c_node != NULL

    def __iter__(self):
        return ElementChildIterator(self)

    def index(self, _Element x, start=None, stop=None):
        cdef int k
        cdef int l
        cdef int c_stop
        cdef int c_start
        cdef xmlNode* c_child
        cdef xmlNode* c_start_node
        _raiseIfNone(x)
        c_child = x._c_node
        if c_child.parent is not self._c_node:
            raise ValueError, "Element is not a child of this node."

        if start is None:
            c_start = 0
        else:
            c_start = start
        if stop is None:
            c_stop = 0
        else:
            c_stop = stop
            if c_stop == 0 or \
                   c_start >= c_stop and (c_stop > 0 or c_start < 0):
                raise ValueError, "list.index(x): x not in slice"

        # for negative slice indices, check slice before searching index
        if c_start < 0 or c_stop < 0:
            # start from right, at most up to leftmost(c_start, c_stop)
            if c_start < c_stop:
                k = -c_start
            else:
                k = -c_stop
            c_start_node = self._c_node.last
            l = 1
            while c_start_node != c_child and l < k:
                if _isElement(c_start_node):
                    l = l + 1
                c_start_node = c_start_node.prev
            if c_start_node == c_child:
                # found! before slice end?
                if c_stop < 0 and l <= -c_stop:
                    raise ValueError, "list.index(x): x not in slice"
            elif c_start < 0:
                raise ValueError, "list.index(x): x not in slice"

        # now determine the index backwards from child
        c_child = c_child.prev
        k = 0
        if c_stop > 0:
            # we can optimize: stop after c_stop elements if not found
            while c_child != NULL and k < c_stop:
                if _isElement(c_child):
                    k = k + 1
                c_child = c_child.prev
            if k < c_stop:
                return k
        else:
            # traverse all
            while c_child != NULL:
                if _isElement(c_child):
                    k = k + 1
                c_child = c_child.prev
            if c_start > 0:
                if k >= c_start:
                    return k
            else:
                return k
        if c_start or c_stop:
            raise ValueError, "list.index(x): x not in slice"
        else:
            raise ValueError, "list.index(x): x not in list"

    def get(self, key, default=None):
        # XXX more redundancy, but might be slightly faster than
        #     return self.attrib.get(key, default)
        cdef char* cresult
        ns, tag = _getNsTag(key)
        if ns is None:
            cresult = tree.xmlGetNoNsProp(self._c_node, tag)
        else:
            cresult = tree.xmlGetNsProp(self._c_node, tag, ns)
        if cresult is NULL:
            result = default
        else:
            result = funicode(cresult)
            tree.xmlFree(cresult)
        return result

    def keys(self):
        return self.attrib.keys()

    def items(self):
        return self.attrib.items()

    def getchildren(self):
        cdef xmlNode* c_node
        cdef _Document doc
        cdef int ret
        result = []
        doc = self._doc
        c_node = self._c_node.children
        while c_node is not NULL:
            if _isElement(c_node):
                ret = python.PyList_Append(result, _elementFactory(doc, c_node))
                if ret:
                    raise
            c_node = c_node.next
        return result

    def getparent(self):
        cdef xmlNode* c_node
        c_node = self._c_node.parent
        if c_node is not NULL and _isElement(c_node):
            return _elementFactory(self._doc, c_node)
        return None

    def getiterator(self, tag=None):
        iterator = ElementDepthFirstIterator(self)
        if tag is None or tag == '*':
            return iterator
        else:
            return ElementTagFilter(iterator, tag)

    def makeelement(self, tag, attrib):
        return Element(tag, attrib)

    def find(self, path):
        return _elementpath.find(self, path)

    def findtext(self, path, default=None):
        return _elementpath.findtext(self, path, default)

    def findall(self, path):
        return _elementpath.findall(self, path)

    def xpath(self, _path, namespaces=None, **_variables):
        return XPathElementEvaluator(self, namespaces).evaluate(_path, **_variables)

cdef _Element _elementFactory(_Document doc, xmlNode* c_node):
    cdef _Element result
    cdef char* c_ns_href
    result = getProxy(c_node, PROXY_ELEMENT)
    if result is not None:
        return result
    if c_node is NULL:
        return None
    if c_node.type == tree.XML_ELEMENT_NODE:
        if c_node.ns == NULL:
            c_ns_href = NULL
        else:
            c_ns_href = c_node.ns.href
        element_class = _find_element_class(c_ns_href, c_node.name)
    elif c_node.type == tree.XML_COMMENT_NODE:
        element_class = _Comment
    else:
        assert 0, "Unknown node type: %s" % c_node.type
    result = element_class()
    result._doc = doc
    result._c_node = c_node
    result._proxy_type = PROXY_ELEMENT
    registerProxy(result, PROXY_ELEMENT)
    result._init()
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
        return "<Comment[%s]>" % self.text
    
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
    
cdef _Comment _commentFactory(_Document doc, xmlNode* c_node):
    cdef _Comment result
    result = getProxy(c_node, PROXY_ELEMENT)
    if result is not None:
        return result
    if c_node is NULL:
        return None
    result = _Comment()
    result._doc = doc
    result._c_node = c_node
    result._proxy_type = PROXY_ELEMENT
    registerProxy(result, PROXY_ELEMENT)
    return result

cdef class _Attrib(_NodeBase):
    # MANIPULATORS
    def __setitem__(self, key, value):
        cdef xmlNs* c_ns
        ns, tag = _getNsTag(key)
        value = _utf8(value)
        if ns is None:
            tree.xmlSetProp(self._c_node, tag, value)
        else:
            c_ns = self._doc._findOrBuildNodeNs(self._c_node, ns)
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
        cdef char* cresult
        ns, tag = _getNsTag(key)
        if ns is None:
            cresult = tree.xmlGetNoNsProp(self._c_node, tag)
        else:
            cresult = tree.xmlGetNsProp(self._c_node, tag, ns)
        if cresult is NULL:
            # XXX free namespace that is not in use..?
            raise KeyError, key
        result = funicode(cresult)
        tree.xmlFree(cresult)
        return result

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
        return iter(self.keys())
    
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

    def has_key(self, key):
        cdef xmlNs* c_ns
        cdef char* result
        ns, tag = _getNsTag(key)
        if ns is None:
            result = tree.xmlGetNoNsProp(self._c_node, tag)
        else:
            result = tree.xmlGetNsProp(self._c_node, tag, ns)
        if result is not NULL:
            tree.xmlFree(result)
            return True
        else:
            return False

    def __contains__(self, key):
        cdef xmlNs* c_ns
        cdef char* result
        ns, tag = _getNsTag(key)
        if ns is None:
            result = tree.xmlGetNoNsProp(self._c_node, tag)
        else:
            result = tree.xmlGetNsProp(self._c_node, tag, ns)
        if result is not NULL:
            tree.xmlFree(result)
            return True
        else:
            return False
  
cdef _Attrib _attribFactory(_Document doc, xmlNode* c_node):
    cdef _Attrib result
    result = getProxy(c_node, PROXY_ATTRIB)
    if result is not None:
        return result
    result = _Attrib()
    result._doc = doc
    result._c_node = c_node
    result._proxy_type = PROXY_ATTRIB
    registerProxy(result, PROXY_ATTRIB)
    return result

cdef class ElementChildIterator:
    # we keep Python references here to control GC
    cdef _NodeBase _node
    def __init__(self, _NodeBase node): # Python ref!
        cdef xmlNode* c_node
        c_node = _findChildForwards(node._c_node, 0)
        if c_node is NULL:
            self._node = None
        else:
            self._node = _elementFactory(node._doc, c_node)
    def __iter__(self):
        return self
    def __next__(self):
        cdef xmlNode* c_node
        cdef _NodeBase current_node
        # Python ref:
        current_node = self._node
        if current_node is None:
            raise StopIteration
        c_node = _nextElement(current_node._c_node)
        if c_node is NULL:
            self._node = None
        else:
            # Python ref:
            self._node = _elementFactory(current_node._doc, c_node)
        return current_node

cdef class ElementDepthFirstIterator:
    """Iterates over an element and its sub-elements in document order (depth
    first pre-order)."""
    # we keep Python references here to control GC
    # keep next node to return and a stack of position state in the tree
    cdef object _stack
    cdef _NodeBase _next_node
    def __init__(self, _NodeBase node):
        cdef xmlNode* c_node
        _raiseIfNone(node)
        self._next_node = node
        self._stack = []
        self._findAndPushNextNode(node)
    def __iter__(self):
        return self
    def __next__(self):
        cdef xmlNode* c_node
        cdef _NodeBase next_node
        current_node = self._next_node
        if current_node is None:
            raise StopIteration
        stack = self._stack
        if python.PyList_GET_SIZE(stack) == 0:
            self._next_node = None
            return current_node
        next_node = stack[-1]
        self._next_node = next_node
        self._findAndPushNextNode(next_node)
        return current_node

    cdef void _findAndPushNextNode(self, _NodeBase node):
        cdef xmlNode* c_node
        stack = self._stack
        # try next child level until we hit a leaf
        c_node = _findChildForwards(node._c_node, 0)
        if c_node is NULL:
            pop = stack.pop
            while c_node is NULL and python.PyList_GET_SIZE(stack):
                # walk up the stack until we find a sibling
                node = pop()
                c_node = _nextElement(node._c_node)
        if c_node is not NULL:
            python.PyList_Append(
                stack, _elementFactory(node._doc, c_node))

cdef class ElementTagFilter:
    cdef object _iterator
    cdef object _pystrings
    cdef char* _href
    cdef char* _name
    def __init__(self, element_iterator, tag):
        self._iterator = iter(element_iterator)
        ns_href, name = _getNsTag(tag)
        self._pystrings = (ns_href, name) # keep Python references
        self._name = name
        if ns_href is None:
            self._href = NULL
        else:
            self._href = ns_href
    def __iter__(self):
        return self
    def __next__(self):
        cdef _NodeBase node
        while 1:
            node = self._iterator.next()
            if self._tagMatches(node._c_node):
                return node

    cdef int _tagMatches(self, xmlNode* c_node):
        if tree.strcmp(c_node.name, self._name) == 0:
            if c_node.ns == NULL or c_node.ns.href == NULL:
                return self._href == NULL
            else:
                return tree.strcmp(c_node.ns.href, self._href) == 0
        return 0

cdef xmlNode* _createElement(xmlDoc* c_doc, object name_utf,
                             object attrib, object extra) except NULL:
    cdef xmlNode* c_node
    if extra:
        if attrib is None:
            attrib = extra
        else:
            attrib.update(extra)
    c_node = tree.xmlNewDocNode(c_doc, NULL, name_utf, NULL)
    if attrib:
        for name, value in attrib.items():
            attr_name_utf = _utf8(name)
            value_utf = _utf8(value)
            tree.xmlNewProp(c_node, attr_name_utf, value_utf)
    return c_node

cdef xmlNode* _createComment(xmlDoc* c_doc, char* text):
    cdef xmlNode* c_node
    c_node = tree.xmlNewDocComment(c_doc, text)
    return c_node


# module-level API for ElementTree

def Element(_tag, attrib=None, nsmap=None, **_extra):
    cdef xmlNode*  c_node
    cdef xmlDoc*   c_doc
    cdef _Document doc
    ns_utf, name_utf = _getNsTag(_tag)
    c_doc = theParser.newDoc()
    c_node = _createElement(c_doc, name_utf, attrib, _extra)
    tree.xmlDocSetRootElement(c_doc, c_node)
    doc = _documentFactory(c_doc)
    # add namespaces to node if necessary
    doc._setNodeNamespaces(c_node, ns_utf, nsmap)
    return _elementFactory(doc, c_node)

def Comment(text=None):
    cdef _Document doc
    cdef xmlNode*  c_node
    if text is None:
        text = '  '
    else:
        text = ' %s ' % _utf8(text)
    doc = _documentFactory( theParser.newDoc() )
    c_node = _createComment(doc._c_doc, text)
    tree.xmlAddChild(<xmlNode*>doc._c_doc, c_node)
    return _commentFactory(doc, c_node)

def SubElement(_Element _parent, _tag, attrib=None, nsmap=None, **_extra):
    cdef xmlNode*  c_node
    cdef _Document doc
    _raiseIfNone(_parent)
    ns_utf, name_utf = _getNsTag(_tag)
    doc = _parent._doc
    c_node = _createElement(doc._c_doc, name_utf, attrib, _extra)
    tree.xmlAddChild(_parent._c_node, c_node)
    # add namespaces to node if necessary
    doc._setNodeNamespaces(c_node, ns_utf, nsmap)
    return _elementFactory(doc, c_node)

def ElementTree(_Element element=None, file=None, parser=None):
    cdef xmlNode* c_next
    cdef xmlNode* c_node
    cdef xmlNode* c_node_copy
    cdef _ElementTree etree
    cdef _Document doc

    if element is not None:
        doc  = element._doc
    elif file is not None:
        doc = _parseDocument(file, parser)
    else:
        doc = _documentFactory( theParser.newDoc() )

    etree = _elementTreeFactory(doc, element)

##     # XXX what if element and file are both not None?
##     if element is not None:
##         c_next = element._c_node.next
##         tree.xmlDocSetRootElement(etree._c_doc, element._c_node)
##         _moveTail(c_next, element._c_node)
##         changeDocumentBelow(element, etree)
    
    return etree

def XML(text):
    cdef xmlDoc* c_doc
    if python.PyUnicode_Check(text):
        text = _stripDeclaration(_utf8(text))
    c_doc = theParser.parseDoc(text, None)
    return _documentFactory(c_doc).getroot()

fromstring = XML

def XMLID(text):
    root = XML(text)
    dic = {}
    for elem in root.xpath('//*[string(@id)]'):
        python.PyDict_SetItem(dic, elem.get('id'), elem)
    return (root, dic)

def iselement(element):
    return isinstance(element, _Element)

def dump(_NodeBase elem):
    assert elem is not None, "Must supply element."
    # better, but not ET compatible : _raiseIfNone(elem)
    _dumpToFile(sys.stdout, elem._doc._c_doc, elem._c_node)

def tostring(_NodeBase element, encoding='us-ascii'):
    cdef _Document doc
    cdef tree.xmlOutputBuffer* c_buffer
    cdef tree.xmlCharEncodingHandler* enchandler
    cdef char* enc

    assert element is not None
    # better, but not ET compatible : _raiseIfNone(element)
    
    #if encoding is None:
    #    encoding = 'UTF-8'
    if encoding in ('utf8', 'UTF8', 'utf-8'):
        encoding = 'UTF-8'
    doc = element._doc
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
    """Return an ElementTree object loaded with source elements
    """
    cdef _Document doc
    doc = _parseDocument(source, parser)
    return ElementTree(doc.getroot())


# include submodules
include "xmlerror.pxi"  # error and log handling
include "nsclasses.pxi" # Namespace implementation and registry
include "xslt.pxi"      # XPath and XSLT
include "relaxng.pxi"   # RelaxNG
include "xmlschema.pxi" # XMLSchema
include "parser.pxi"    # XML Parser
include "proxy.pxi"     # Proxy handling (element backpointers/memory/etc.)


# Instantiate globally shared XML parser to enable dictionary sharing
cdef Parser theParser
theParser = Parser()


# Private helper functions
cdef void _raiseIfNone(el):
    if el is None:
        raise TypeError, "Argument must not be None."

cdef _Document _documentOrRaise(object input):
    cdef _Document doc
    doc = _documentOf(input)
    if doc is None:
        raise TypeError, "Invalid input object: %s" % type(input)
    else:
        return doc

cdef _Document _documentOf(object input):
    # call this to get the document of a
    # _Document, _ElementTree or _NodeBase object
    if isinstance(input, _ElementTree):
        return (<_ElementTree>input)._doc
    elif isinstance(input, _NodeBase):
        return (<_NodeBase>input)._doc
    elif isinstance(input, _Document):
        return <_Document>input
    else:
        return None

cdef _NodeBase _rootNodeOf(object input):
    # call this to get the root node of a
    # _Document, _ElementTree or _NodeBase object
    if hasattr(input, 'getroot'): # Document/ElementTree
        return <_NodeBase>(input.getroot())
    elif isinstance(input, _NodeBase):
        return <_NodeBase>input
    else:
        return None

cdef xmlDoc* _fakeRootDoc(xmlDoc* c_base_doc, xmlNode* c_node):
    # build a temporary document that has the given node as root node
    # note that copy and original must not be modified during its lifetime!!
    # always call _destroyFakeDoc() after use!
    cdef xmlNode* c_child
    cdef xmlNode* c_root
    cdef xmlDoc*  c_doc
    c_root = tree.xmlDocGetRootElement(c_base_doc)
    if c_root == c_node:
        # already the root node
        return c_base_doc

    c_doc  = tree.xmlCopyDoc(c_base_doc, 0)        # non recursive!
    c_root = tree.xmlDocCopyNode(c_node, c_doc, 2) # non recursive!

    c_root.children = c_node.children
    c_root.last = c_node.last
    c_root.next = c_root.prev = c_root.parent = NULL

    # store original node
    c_root._private = c_node

    # divert parent pointers of children
    c_child = c_root.children
    while c_child is not NULL:
        c_child.parent = c_root
        c_child = c_child.next

    c_doc.children = c_root
    return c_doc

cdef void _destroyFakeDoc(xmlDoc* c_base_doc, xmlDoc* c_doc):
    # delete a temporary document
    cdef xmlNode* c_child
    cdef xmlNode* c_parent
    cdef xmlNode* c_root
    if c_doc != c_base_doc:
        c_root = tree.xmlDocGetRootElement(c_doc)

        # restore parent pointers of children
        c_parent = <xmlNode*>c_root._private
        c_child = c_root.children
        while c_child is not NULL:
            c_child.parent = c_parent
            c_child = c_child.next

        # prevent recursive removal of children
        c_root.children = c_root.last = c_root._private = NULL
        tree.xmlFreeDoc(c_doc)


cdef _dumpToFile(f, xmlDoc* c_doc, xmlNode* c_node):
    cdef python.PyObject* o
    cdef tree.xmlOutputBuffer* c_buffer
    
    if not python.PyFile_Check(f):
        raise ValueError, "Not a file"
    o = <python.PyObject*>f
    c_buffer = tree.xmlOutputBufferCreateFile(python.PyFile_AsFile(o), NULL)
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
        
cdef object _stripDeclaration(object xml_string):
    xml_string = xml_string.strip()
    if xml_string[:5] == '<?xml':
        i = xml_string.find('?>')
        if i != -1:
            if xml_string[i+2:i+3] == '\n':
                i = i+1
            xml_string = xml_string[i + 2:]
    return xml_string

cdef _collectText(xmlNode* c_node):
    """Collect all text nodes and return them as a unicode string.

    Start collecting at c_node.
    
    If there was no text to collect, return None
    """
    cdef int scount
    cdef char* text
    cdef xmlNode* c_node_cur
    # check for multiple text nodes
    scount = 0
    text = NULL
    c_node_cur = c_node
    while c_node_cur is not NULL and c_node_cur.type == tree.XML_TEXT_NODE:
        if c_node_cur.content[0] != c'\0':
            text = c_node_cur.content
            scount = scount + 1
        c_node_cur = c_node_cur.next

    # handle two most common cases first
    if text is NULL:
        return None
    if scount == 1:
        return funicode(text)

    # the rest is not performance critical anymore
    result = ''
    while c_node is not NULL and c_node.type == tree.XML_TEXT_NODE:
        result = result + c_node.content
        c_node = c_node.next
    return funicode(result)

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

### see etree.h:
## cdef int _isElement(xmlNode* c_node):
##     return (c_node.type == tree.XML_ELEMENT_NODE or
##             c_node.type == tree.XML_COMMENT_NODE)

cdef xmlNode* _deleteSlice(xmlNode* c_node, int start, int stop):
    """Delete slice, starting with c_node, start counting at start, end at stop.
    """
    cdef xmlNode* c_next
    cdef int c
    if c_node is NULL:
        return NULL
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
    return c_node

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
        return python.PyUnicode_DecodeUTF8(s, tree.strlen(s), NULL)
    return python.PyString_FromString(s)

cdef object _utf8(object s):
    if python.PyString_Check(s):
        assert not isutf8(s), "All strings must be Unicode or ASCII"
        return s
    elif python.PyUnicode_Check(s):
        return python.PyUnicode_AsUTF8String(s)
    else:
        raise TypeError, "Argument must be string or unicode."

cdef _getNsTag(tag):
    """Given a tag, find namespace URI and tag name.
    Return None for NS uri if no namespace URI available.
    """
    cdef char* c_tag
    cdef char* c_pos
    cdef int nslen
    tag = _utf8(tag)
    c_tag = tag
    if c_tag[0] == c'{':
        c_pos = tree.xmlStrchr(c_tag+1, c'}')
        if c_pos is NULL:
            raise ValueError, "Invalid tag name"
        nslen = c_pos - c_tag - 1
        ns  = python.PyString_FromStringAndSize(c_tag+1, nslen)
        tag = python.PyString_FromString(c_pos+1)
    else:
        ns = None
    return ns, tag
    
cdef object _namespacedName(xmlNode* c_node):
    cdef char* href
    cdef char* name
    name = c_node.name
    if c_node.ns is NULL or c_node.ns.href is NULL:
        return funicode(name)
    else:
        href = c_node.ns.href
        s = python.PyString_FromFormat("{%s}%s", href, name)
        if isutf8(href) or isutf8(name):
            return python.PyUnicode_FromEncodedObject(s, 'UTF-8', NULL)
        else:
            return s

cdef _getFilenameForFile(source):
    """Given a Python File or Gzip object, give filename back.

    Returns None if not a file object.
    """
    # file instances have a name attribute
    if hasattr(source, 'name'):
        return source.name
    # gzip file instances have a filename attribute
    if hasattr(source, 'filename'):
        return source.filename
    return None

cdef void changeDocumentBelow(_NodeBase node, _Document doc, int recursive):
    """For a node and all nodes below, change document.

    A node can change document in certain operations as an XML
    subtree can move. This updates all possible proxies in the
    tree below (including the current node). It also reconciliates
    namespaces so they're correct inside the new environment.
    """
    if recursive:
        changeDocumentBelowHelper(node._c_node, doc)
    tree.xmlReconciliateNs(doc._c_doc, node._c_node)
    
cdef void changeDocumentBelowHelper(xmlNode* c_node, _Document doc):
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

