cimport tree, python
from tree cimport xmlDoc, xmlNode, xmlAttr, xmlNs, _isElement
from python cimport isinstance, issubclass, hasattr, callable
from python cimport iter, str, _cstr, Py_ssize_t
cimport xpath
cimport xinclude
cimport c14n
cimport cstd
import re

import __builtin__
cdef object True
cdef object False
True  = __builtin__.True
False = __builtin__.False

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

def initThread():
    "Call this method to set up the library from within a new thread."
    _initThreadLogging()
    tree.xmlKeepBlanksDefault(0)

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

class DocumentInvalid(LxmlError):
    pass

class XIncludeError(LxmlError):
    pass

class C14NError(LxmlError):
    pass

# version information
cdef __unpackDottedVersion(version):
    version_list = []
    l = (version.replace('-', '.').split('.') + [0]*4)[:4]
    for item in l:
        try:
            item = int(item)
        except ValueError:
            if item == 'alpha':
                item = -2
            elif item == 'beta':
                item = -1
        version_list.append(item)
    return tuple(version_list)

cdef __unpackIntVersion(int c_version):
    return (
        ((c_version / (100*100)) % 100),
        ((c_version / 100)       % 100),
        (c_version               % 100)
        )

cdef int _LIBXML_VERSION_INT
try:
    _LIBXML_VERSION_INT = int((tree.xmlParserVersion).split('-')[0])
except Exception:
    _LIBXML_VERSION_INT = 0

LIBXML_VERSION = __unpackIntVersion(_LIBXML_VERSION_INT)
LIBXML_COMPILED_VERSION = __unpackIntVersion(tree.LIBXML_VERSION)
LXML_VERSION = __unpackDottedVersion(tree.LXML_VERSION_STRING)

__version__ = tree.LXML_VERSION_STRING


# class for temporary storage of Python references
cdef class _TempStore:
    cdef object _storage
    def __init__(self):
        self._storage = {}

    cdef void add(self, obj):
        python.PyDict_SetItem(self._storage, id(obj), obj)

    cdef void clear(self):
        python.PyDict_Clear(self._storage)

    cdef object dictcopy(self):
        return self._storage.copy()

# class for temporarily storing exceptions raised in extensions
cdef class _ExceptionContext:
    cdef object _exc_info
    cdef void clear(self):
        self._exc_info = None

    cdef void _store_raised(self):
        self._exc_info = sys.exc_info()

    cdef void _store_exception(self, exception):
        self._exc_info = (exception, None, None)

    cdef _has_raised(self):
        return self._exc_info is not None

    cdef _raise_if_stored(self):
        _exc_info = self._exc_info
        if _exc_info is not None:
            self._exc_info = None
            type, value, traceback = _exc_info
            if traceback is None and value is None:
                raise type
            else:
                raise type, value, traceback


cdef class _BaseParser # forward declaration

cdef class _Document:
    """Internal base class to reference a libxml document.

    When instances of this class are garbage collected, the libxml
    document is cleaned up.
    """
    cdef int _ns_counter
    cdef xmlDoc* _c_doc
    cdef _BaseParser _parser
    
    def __dealloc__(self):
        # if there are no more references to the document, it is safe
        # to clean the whole thing up, as all nodes have a reference to
        # the document
        #print "freeing document:", <int>self._c_doc
        #displayNode(<xmlNode*>self._c_doc, 0)
        #print <int>self._c_doc, self._c_doc.dict is __GLOBAL_PARSER_CONTEXT._c_dict
        tree.xmlFreeDoc(self._c_doc)

    cdef getroot(self):
        cdef xmlNode* c_node
        c_node = tree.xmlDocGetRootElement(self._c_doc)
        if c_node is NULL:
            return None
        return _elementFactory(self, c_node)

    cdef getdoctype(self):
        cdef tree.xmlDtd* dtd
        cdef xmlNode* c_root_node
        public_id = None
        sys_url   = None
        dtd = self._c_doc.intSubset
        if dtd is not NULL:
            if dtd.ExternalID is not NULL:
                public_id = funicode(dtd.ExternalID)
            if dtd.SystemID is not NULL:
                sys_url = funicode(dtd.SystemID)
        dtd = self._c_doc.extSubset
        if dtd is not NULL:
            if not public_id and dtd.ExternalID is not NULL:
                public_id = funicode(dtd.ExternalID)
            if not sys_url and dtd.SystemID is not NULL:
                sys_url = funicode(dtd.SystemID)
        c_root_node = tree.xmlDocGetRootElement(self._c_doc)
        if c_root_node is NULL:
            root_name = None
        else:
            root_name = funicode(c_root_node.name)
        return (root_name, public_id, sys_url)

    cdef getxmlinfo(self):
        cdef xmlDoc* c_doc
        c_doc = self._c_doc
        if c_doc.version is NULL:
            version = None
        else:
            version = c_doc.version
        if c_doc.encoding is NULL:
            encoding = None
        else:
            encoding = c_doc.encoding
        return (version, encoding)

    cdef getURL(self):
        if self._c_doc.URL is NULL:
            return None
        else:
            return self._c_doc.URL

    cdef buildNewPrefix(self):
        ns = python.PyString_FromFormat("ns%d", self._ns_counter)
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
        c_ns = tree.xmlNewNs(c_node, href, _cstr(prefix))
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
            c_href = _cstr(href_utf)
            if prefix is not None:
                prefix_utf = _utf8(prefix)
                c_prefix = _cstr(prefix_utf)
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

cdef _Document _documentFactory(xmlDoc* c_doc, _BaseParser parser):
    cdef _Document result
    result = _Document()
    result._c_doc = c_doc
    result._ns_counter = 0
    if parser is None:
        parser = __DEFAULT_PARSER
    result._parser = parser.copy()
    return result

cdef class DocInfo:
    "Document information provided by parser and DTD."
    cdef readonly object root_name
    cdef readonly object public_id
    cdef readonly object system_url
    cdef readonly object xml_version
    cdef readonly object encoding
    cdef readonly object URL
    def __init__(self, tree):
        "Create a DocInfo object for an ElementTree object or root Element."
        cdef _Document doc
        doc = _documentOrRaise(tree)
        self.root_name, self.public_id, self.system_url = doc.getdoctype()
        if not self.root_name and (self.public_id or self.system_url):
            raise ValueError, "Could not find root node"
        self.xml_version, self.encoding = doc.getxmlinfo()
        self.URL = doc.getURL()

    property doctype:
        def __get__(self):
            if self.public_id:
                if self.system_url:
                    return '<!DOCTYPE %s PUBLIC "%s" "%s">' % (
                        self.root_name, self.public_id, self.system_url)
                else:
                    return '<!DOCTYPE %s PUBLIC "%s">' % (
                        self.root_name, self.public_id)
            elif self.system_url:
                return '<!DOCTYPE %s SYSTEM "%s">' % (
                    self.root_name, self.system_url)
            else:
                return ""

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

    # Note that _doc is only used to store the original document if we do not
    # have a _context_node.  All methods should prefer self._context_node._doc
    # to honour tree restructuring

    cdef _assertHasRoot(self):
        """We have to take care here: the document may not have a root node!
        This can happen if ElementTree() is called without any argument and
        the caller 'forgets' to call parse() afterwards, so this is a bug in
        the caller program.
        """
        assert self._context_node is not None, \
               "ElementTree not initialized, missing root"

    def parse(self, source, _BaseParser parser=None):
        """Updates self with the content of source and returns its root
        """
        cdef _Document doc
        doc = _parseDocument(source, parser)
        self._context_node = doc.getroot()
        return self._context_node

    def getroot(self):
        return self._context_node

    property docinfo:
        """Information about the document provided by parser and DTD.  This
        value is only defined for ElementTree objects based on the root node
        of a parsed document (e.g.  those returned by the parse functions).
        """
        def __get__(self):
            self._assertHasRoot()
            return DocInfo(self._context_node._doc)

    def write(self, file, encoding=None,
              pretty_print=False, xml_declaration=None):
        """Write the tree to a file or file-like object.
        
        Defaults to ASCII encoding and writing a declaration as needed.
        """
        cdef int c_write_declaration
        self._assertHasRoot()
        # suppress decl. in default case (purely for ElementTree compatibility)
        if xml_declaration is not None:
            c_write_declaration = bool(xml_declaration)
            if encoding is None:
                encoding = 'ASCII'
        elif encoding is None:
            encoding = 'ASCII'
            c_write_declaration = 0
        else:
            encoding = encoding.upper()
            c_write_declaration = encoding not in \
                                  ('US-ASCII', 'ASCII', 'UTF8', 'UTF-8')
        _tofilelike(file, self._context_node, encoding,
                    c_write_declaration, bool(pretty_print))

    def getpath(self, _NodeBase element not None):
        cdef _Document doc
        cdef xmlDoc* c_doc
        cdef char* c_path
        doc = self._context_node._doc
        if element._doc is not doc:
            raise ValueError, "Element is not in this tree."
        c_doc = _fakeRootDoc(doc._c_doc, self._context_node._c_node)
        c_path = tree.xmlGetNodePath(element._c_node)
        _destroyFakeDoc(doc._c_doc, c_doc)
        if c_path is NULL:
            raise LxmlError, "Error creating node path."
        path = c_path
        tree.xmlFree(c_path)
        return path

    def getiterator(self, tag=None):
        root = self.getroot()
        if root is None:
            return ()
        return root.getiterator(tag)

    def find(self, path):
        self._assertHasRoot()
        root = self.getroot()
        if path[:1] == "/":
            path = "." + path
        return root.find(path)

    def findtext(self, path, default=None):
        self._assertHasRoot()
        root = self.getroot()
        if path[:1] == "/":
            path = "." + path
        return root.findtext(path, default)

    def findall(self, path):
        self._assertHasRoot()
        root = self.getroot()
        if path[:1] == "/":
            path = "." + path
        return root.findall(path)
    
    # extensions to ElementTree API
    def xpath(self, _path, namespaces=None, extensions=None, **_variables):
        """XPath evaluate in context of document.

        ``namespaces`` is an optional dictionary with prefix to namespace URI
        mappings, used by XPath.  ``extensions`` defines additional extension
        functions.
        
        Returns a list (nodeset), or bool, float or string.

        In case of a list result, return Element for element nodes,
        string for text and attribute values.

        Note: if you are going to apply multiple XPath expressions
        against the same document, it is more efficient to use
        XPathEvaluator directly.
        """
        self._assertHasRoot()
        evaluator = XPathDocumentEvaluator(self, namespaces, extensions)
        return evaluator.evaluate(_path, **_variables)

    def xslt(self, _xslt, extensions=None, **_kw):
        """Transform this document using other document.

        xslt is a tree that should be XSLT
        keyword parameters are XSLT transformation parameters.

        Returns the transformed tree.

        Note: if you are going to apply the same XSLT stylesheet against
        multiple documents, it is more efficient to use the XSLT
        class directly.
        """
        self._assertHasRoot()
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
        self._assertHasRoot()
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
        self._assertHasRoot()
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
        self._assertHasRoot()
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
        self._assertHasRoot()
        c_base_doc = self._context_node._doc._c_doc

        c_doc = _fakeRootDoc(c_base_doc, self._context_node._c_node)
        bytes = c14n.xmlC14NDocDumpMemory(c_doc, NULL, 0, NULL, 1, &data)
        _destroyFakeDoc(c_base_doc, c_doc)

        if bytes < 0:
            raise C14NError, "C14N failed"
        try:
            if not hasattr(file, 'write'):
                file = open(file, 'wb')
            file.write(data)
        finally:
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
    cdef object _tag

    # MANIPULATORS

    def __setitem__(self, Py_ssize_t index, _NodeBase element not None):
        cdef xmlNode* c_node
        cdef xmlNode* c_next
        c_node = _findChild(self._c_node, index)
        if c_node is NULL:
            raise IndexError
        c_next = element._c_node.next
        _removeText(c_node.next)
        tree.xmlReplaceNode(c_node, element._c_node)
        _moveTail(c_next, element._c_node)
        moveNodeToDocument(element, self._doc)
        
    def __delitem__(self, Py_ssize_t index):
        cdef xmlNode* c_node
        c_node = _findChild(self._c_node, index)
        if c_node is NULL:
            raise IndexError
        _removeText(c_node.next)
        _removeNode(c_node)

    def __delslice__(self, Py_ssize_t start, Py_ssize_t stop):
        cdef xmlNode* c_node
        c_node = _findChild(self._c_node, start)
        _deleteSlice(c_node, start, stop)
        
    def __setslice__(self, Py_ssize_t start, Py_ssize_t stop, value):
        cdef xmlNode* c_node
        cdef xmlNode* c_next
        cdef _Element mynode
        # first, find start of slice
        c_node = _findChild(self._c_node, start)
        # now delete the slice
        if start != stop:
            c_node = _deleteSlice(c_node, start, stop)
        # if the insertion point is at the end, append there
        if c_node is NULL:
            append = self.append
            for node in value:
                append(node)
            return
        # if the next element is in the list, insert before it
        for mynode in value:
            if mynode is None:
                raise TypeError, "Node must not be None."
            # store possible text tail
            c_next = mynode._c_node.next
            # now move node previous to insertion point
            tree.xmlUnlinkNode(mynode._c_node)
            tree.xmlAddPrevSibling(c_node, mynode._c_node)
            # and move tail just behind his node
            _moveTail(c_next, mynode._c_node)
            # move it into a new document
            moveNodeToDocument(mynode, self._doc)

    def __deepcopy__(self, memo):
        return self.__copy__()
        
    def __copy__(self):
        cdef xmlNode* c_node
        cdef xmlDoc* c_doc
        cdef _Document doc
        cdef _Document new_doc
        doc = self._doc
        c_doc = _copyDocRoot(doc._c_doc, self._c_node) # recursive
        new_doc = _documentFactory(c_doc, doc._parser)
        return new_doc.getroot()

    def set(self, key, value):
        _setAttributeValue(self, key, value)
        
    def append(self, _Element element not None):
        cdef xmlNode* c_next
        cdef xmlNode* c_node
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
        moveNodeToDocument(element, self._doc)

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
    
    def insert(self, index, _Element element not None):
        cdef xmlNode* c_node
        cdef xmlNode* c_next
        c_node = _findChild(self._c_node, index)
        if c_node is NULL:
            self.append(element)
            return
        c_next = element._c_node.next
        tree.xmlAddPrevSibling(c_node, element._c_node)
        _moveTail(c_next, element._c_node)
        moveNodeToDocument(element, self._doc)

    def remove(self, _Element element not None):
        cdef xmlNode* c_node
        c_node = element._c_node
        if c_node.parent is not self._c_node:
            raise ValueError, "Element is not a child of this node."
        _removeText(c_node.next)
        tree.xmlUnlinkNode(c_node)
        
    # PROPERTIES
    property tag:
        def __get__(self):
            if self._tag is not None:
                return self._tag
            self._tag = _namespacedName(self._c_node)
            return self._tag
    
        def __set__(self, value):
            cdef xmlNs* c_ns
            ns, text = _getNsTag(value)
            self._tag = value
            tree.xmlNodeSetName(self._c_node, _cstr(text))
            if ns is None:
                return
            self._doc._setNodeNs(self._c_node, _cstr(ns))

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
                                             _cstr(text))
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
            c_text_node = tree.xmlNewDocText(self._doc._c_doc, _cstr(text))
            # XXX what if we're the top element?
            tree.xmlAddNextSibling(self._c_node, c_text_node)

    # ACCESSORS
    def __repr__(self):
        return "<Element %s at %x>" % (self.tag, id(self))
    
    def __getitem__(self, Py_ssize_t index):
        cdef xmlNode* c_node
        c_node = _findChild(self._c_node, index)
        if c_node is NULL:
            raise IndexError, "list index out of range"
        return _elementFactory(self._doc, c_node)

    def __getslice__(self, Py_ssize_t start, Py_ssize_t stop):
        cdef xmlNode* c_node
        cdef _Document doc
        cdef Py_ssize_t c
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
        cdef Py_ssize_t c
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

    def __contains__(self, element):
        cdef xmlNode* c_node
        if not isinstance(element, _NodeBase):
            return 0
        c_node = (<_NodeBase>element)._c_node
        return c_node is not NULL and c_node.parent is self._c_node

    def __iter__(self):
        return ElementChildIterator(self)

    def __reversed__(self):
        return ElementChildIterator(self, reversed=True)

    def index(self, _Element x not None, start=None, stop=None):
        """Find the position of the child within the parent.

        This method is not part of the original ElementTree API.
        """
        cdef Py_ssize_t k, l
        cdef Py_ssize_t c_start, c_stop
        cdef xmlNode* c_child
        cdef xmlNode* c_start_node
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
        if c_start != 0 or c_stop != 0:
            raise ValueError, "list.index(x): x not in slice"
        else:
            raise ValueError, "list.index(x): x not in list"

    def get(self, key, default=None):
        return _getAttributeValue(self, key, default)

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

    def getroottree(self):
        """Return an ElementTree for the root node of the document that
        contains this element."""
        return _elementTreeFactory(self._doc, None)

    def getiterator(self, tag=None):
        return ElementDepthFirstIterator(self, tag)

    def makeelement(self, _tag, attrib=None, nsmap=None, **_extra):
        "Creates a new element associated with the same document."
        # a little code duplication, but less overhead through doc reuse
        cdef xmlNode*  c_node
        cdef xmlDoc*   c_doc
        cdef _Document doc
        ns_utf, name_utf = _getNsTag(_tag)
        doc = self._doc
        c_doc = doc._c_doc
        c_node = _createElement(c_doc, name_utf)
        # add namespaces to node if necessary
        doc._setNodeNamespaces(c_node, ns_utf, nsmap)
        _initNodeAttributes(c_node, doc, attrib, _extra)
        return _elementFactory(doc, c_node)

    def find(self, path):
        return _elementpath.find(self, path)

    def findtext(self, path, default=None):
        return _elementpath.findtext(self, path, default)

    def findall(self, path):
        return _elementpath.findall(self, path)

    def xpath(self, _path, namespaces=None, extensions=None, **_variables):
        evaluator = XPathElementEvaluator(self, namespaces, extensions)
        return evaluator.evaluate(_path, **_variables)

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
    result._tag = None
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
            if self._c_node.content is NULL:
                return ''
            else:
                return funicode(self._c_node.content)

        def __set__(self, value):
            cdef tree.xmlDict* c_dict
            cdef char* c_text
            if value is None:
                c_text = NULL
            else:
                value = _utf8(value)
                c_text = _cstr(value)
            tree.xmlNodeSetContent(self._c_node, c_text)

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
        _setAttributeValue(self, key, value)

    def __delitem__(self, key):
        cdef xmlAttr* c_attr
        cdef char* c_tag
        ns, tag = _getNsTag(key)
        c_tag = _cstr(tag)
        if ns is None:
            c_attr = tree.xmlHasProp(self._c_node, c_tag)
        else:
            c_attr = tree.xmlHasNsProp(self._c_node, c_tag, _cstr(ns))
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
        result = _getAttributeValue(self, key, None)
        if result is None:
            raise KeyError, key
        else:
            return result

    def __nonzero__(self):
        cdef xmlNode* c_node
        c_node = <xmlNode*>(self._c_node.properties)
        while c_node is not NULL:
            if c_node.type == tree.XML_ATTRIBUTE_NODE:
                return 1
            c_node = c_node.next
        return 0

    def __len__(self):
        cdef Py_ssize_t c
        cdef xmlNode* c_node
        c = 0
        c_node = <xmlNode*>(self._c_node.properties)
        while c_node is not NULL:
            if c_node.type == tree.XML_ATTRIBUTE_NODE:
                c = c + 1
            c_node = c_node.next
        return c
    
    def get(self, key, default=None):
        return _getAttributeValue(self, key, default)

    def keys(self):
        result = []
        cdef xmlNode* c_node
        c_node = <xmlNode*>(self._c_node.properties)
        while c_node is not NULL:
            if c_node.type == tree.XML_ATTRIBUTE_NODE:
                python.PyList_Append(result, _namespacedName(c_node))
            c_node = c_node.next
        return result

    def __iter__(self):
        return iter(self.keys())
    
    def iterkeys(self):
        return iter(self.keys())

    def values(self):
        cdef xmlNode* c_node
        result = []
        c_node = <xmlNode*>(self._c_node.properties)
        while c_node is not NULL:
            if c_node.type == tree.XML_ATTRIBUTE_NODE:
                python.PyList_Append(
                    result, _attributeValue(self._c_node, c_node))
            c_node = c_node.next
        return result

    def itervalues(self):
        return iter(self.values())

    def items(self):
        result = []
        cdef xmlNode* c_node
        c_node = <xmlNode*>(self._c_node.properties)
        while c_node is not NULL:
            if c_node.type == tree.XML_ATTRIBUTE_NODE:
                python.PyList_Append(result, (
                    _namespacedName(c_node),
                    _attributeValue(self._c_node, c_node)
                    ))
            c_node = c_node.next
        return result

    def iteritems(self):
        return iter(self.items())

    def has_key(self, key):
        if key in self:
            return True
        else:
            return False

    def __contains__(self, key):
        cdef char* c_result
        cdef char* c_tag
        ns, tag = _getNsTag(key)
        c_tag = _cstr(tag)
        if ns is None:
            c_result = tree.xmlGetNoNsProp(self._c_node, c_tag)
        else:
            c_result = tree.xmlGetNsProp(self._c_node, c_tag, _cstr(ns))
        if c_result is NULL:
            return 0
        else:
            tree.xmlFree(c_result)
            return 1

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

ctypedef xmlNode* (*_node_to_node_function)(xmlNode*)

cdef class ElementChildIterator:
    # we keep Python references here to control GC
    cdef _NodeBase _node
    cdef _node_to_node_function _next_element
    def __init__(self, _NodeBase node, reversed=False): # Python ref!
        cdef xmlNode* c_node
        if reversed:
            c_node = _findChildBackwards(node._c_node, 0)
            self._next_element = _previousElement
        else:
            c_node = _findChildForwards(node._c_node, 0)
            self._next_element = _nextElement
        if c_node is not NULL:
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
        c_node = self._next_element(current_node._c_node)
        if c_node is NULL:
            self._node = None
        else:
            # Python ref:
            self._node = _elementFactory(current_node._doc, c_node)
        return current_node

cdef class ElementDepthFirstIterator:
    """Iterates over an element and its sub-elements in document order (depth
    first pre-order).

    If the optional 'tag' argument is not None, it returns only the elements
    that match the respective name and namespace.

    Note that the behaviour of this iterator is completely undefined if the
    tree it traverses is modified during iteration.
    """
    # we keep Python references here to control GC
    # keep next node to return and a depth counter in the tree
    cdef _NodeBase _next_node
    cdef Py_ssize_t _depth
    cdef object _pystrings
    cdef char* _href
    cdef char* _name
    def __init__(self, _NodeBase node not None, tag=None):
        self._next_node = node
        self._depth = 0
        if tag == '*':
            tag = None
        if tag is None:
            self._href = NULL
            self._name = NULL
        else:
            self._pystrings = _getNsTag(tag)
            if self._pystrings[0] is None:
                self._href = NULL
            else:
                self._href = _cstr(self._pystrings[0])
            self._name = _cstr(self._pystrings[1])

        if not _tagMatches(node._c_node, self._href, self._name):
            # this cannot raise StopIteration, self._next_node != None
            self.next()

    def __iter__(self):
        return self

    def __next__(self):
        cdef _NodeBase current_node
        current_node = self._next_node
        if current_node is None:
            raise StopIteration
        self._prepareNextNode()
        return current_node

    cdef void _prepareNextNode(self):
        cdef _NodeBase node
        cdef xmlNode* c_node
        cdef xmlNode* c_parent
        # find in descendants
        node = self._next_node
        c_parent = node._c_node
        c_node = _findDepthFirstInDescendents(c_parent, self._href, self._name)
        if c_node is NULL:
            if self._depth < 1:
                # nothing left to traverse
                self._next_node = None
                return
            # try siblings
            c_node = _findDepthFirstInFollowingSiblings(
                c_parent, self._href, self._name)

            while c_node is NULL and self._depth > 1:
                # walk up the parent pointers and continue with their siblings
                c_parent = c_parent.parent
                self._depth = self._depth - 1
                if c_parent is NULL or not _isElement(c_parent):
                    break
                c_node = _findDepthFirstInFollowingSiblings(
                    c_parent, self._href, self._name)

            if c_node is NULL or not _isElement(c_parent):
                self._next_node = None
                return # all found, nothing left
            # we are at a sibling, so set c_parent to our parent
            c_parent = c_parent.parent

        self._next_node = _elementFactory(node._doc, c_node)
        # fix depth counter by looking up path to original parent
        while c_node is not c_parent:
            self._depth = self._depth + 1
            c_node = c_node.parent

cdef xmlNode* _createElement(xmlDoc* c_doc, object name_utf) except NULL:
    cdef xmlNode* c_node
    c_node = tree.xmlNewDocNode(c_doc, NULL, _cstr(name_utf), NULL)
    return c_node

cdef xmlNode* _createComment(xmlDoc* c_doc, char* text):
    cdef xmlNode* c_node
    c_node = tree.xmlNewDocComment(c_doc, text)
    return c_node

cdef _initNodeAttributes(xmlNode* c_node, _Document doc, attrib, extra):
    cdef xmlNs* c_ns
    # 'extra' is not checked here (expected to be a keyword dict)
    if attrib is not None and not hasattr(attrib, 'items'):
        raise TypeError, "Invalid attribute dictionary: %s" % type(attrib)
    if extra:
        if attrib is None:
            attrib = extra
        else:
            attrib.update(extra)
    if attrib:
        for name, value in attrib.items():
            attr_ns_utf, attr_name_utf = _getNsTag(name)
            value_utf = _utf8(value)
            if attr_ns_utf is None:
                tree.xmlNewProp(c_node, _cstr(attr_name_utf), _cstr(value_utf))
            else:
                c_ns = doc._findOrBuildNodeNs(c_node, _cstr(attr_ns_utf))
                tree.xmlNewNsProp(c_node, c_ns,
                                  _cstr(attr_name_utf), _cstr(value_utf))


# module-level API for ElementTree

def Element(_tag, attrib=None, nsmap=None, **_extra):
    cdef xmlNode*  c_node
    cdef xmlDoc*   c_doc
    cdef _Document doc
    ns_utf, name_utf = _getNsTag(_tag)
    c_doc = _newDoc()
    c_node = _createElement(c_doc, name_utf)
    tree.xmlDocSetRootElement(c_doc, c_node)
    doc = _documentFactory(c_doc, None)
    # add namespaces to node if necessary
    doc._setNodeNamespaces(c_node, ns_utf, nsmap)
    _initNodeAttributes(c_node, doc, attrib, _extra)
    return _elementFactory(doc, c_node)

def Comment(text=None):
    cdef _Document doc
    cdef xmlNode*  c_node
    cdef xmlDoc*   c_doc
    if text is None:
        text = ''
    else:
        text = _utf8(text)
    c_doc = _newDoc()
    doc = _documentFactory(c_doc, None)
    c_node = _createComment(c_doc, _cstr(text))
    tree.xmlAddChild(<xmlNode*>c_doc, c_node)
    return _commentFactory(doc, c_node)

def SubElement(_Element _parent not None, _tag,
               attrib=None, nsmap=None, **_extra):
    cdef xmlNode*  c_node
    cdef _Document doc
    ns_utf, name_utf = _getNsTag(_tag)
    doc = _parent._doc
    c_node = _createElement(doc._c_doc, name_utf)
    tree.xmlAddChild(_parent._c_node, c_node)
    # add namespaces to node if necessary
    doc._setNodeNamespaces(c_node, ns_utf, nsmap)
    _initNodeAttributes(c_node, doc, attrib, _extra)
    return _elementFactory(doc, c_node)

def ElementTree(_Element element=None, file=None, _BaseParser parser=None):
    cdef xmlNode* c_next
    cdef xmlNode* c_node
    cdef xmlNode* c_node_copy
    cdef xmlDoc*  c_doc
    cdef _ElementTree etree
    cdef _Document doc

    if element is not None:
        doc  = element._doc
    elif file is not None:
        doc = _parseDocument(file, parser)
    else:
        c_doc = _newDoc()
        doc = _documentFactory(c_doc, parser)

    return _elementTreeFactory(doc, element)

def HTML(text):
    cdef _Document doc
    doc = _parseMemoryDocument(text, None, __DEFAULT_HTML_PARSER)
    return doc.getroot()

def XML(text):
    cdef _Document doc
    doc = _parseMemoryDocument(text, None, __DEFAULT_XML_PARSER)
    return doc.getroot()

fromstring = XML

cdef class QName:
    cdef readonly object text
    def __init__(self, text_or_uri, tag=None):
        if tag is not None:
            text_or_uri = "{%s}%s" % (text_or_uri, tag)
        elif not python.PyString_Check(text_or_uri) and \
             not python.PyUnicode_Check(text_or_uri):
            text_or_uri = str(text_or_uri)
        self.text = text_or_uri
    def __str__(self):
        return self.text
    def __hash__(self):
        return self.text.__hash__()

def iselement(element):
    return isinstance(element, _Element)

def dump(_NodeBase elem not None, pretty_print=True):
    _dumpToFile(sys.stdout, elem._c_node, bool(pretty_print))

def tostring(element_or_tree, encoding=None,
             xml_declaration=None, pretty_print=False):
    """Serialize an element to an encoded string representation of its XML
    tree.

    Defaults to ASCII encoding without XML declaration.
    """
    cdef int write_declaration
    cdef int c_pretty_print
    if encoding is None:
        encoding = 'ASCII'
    else:
        encoding = encoding.upper()
    c_pretty_print = bool(pretty_print)
    if xml_declaration is None:
        # by default, write an XML declaration only for non-standard encodings
        write_declaration = encoding not in \
                            ('ASCII', 'UTF-8', 'UTF8', 'US-ASCII')
    else:
        write_declaration = bool(xml_declaration)

    if isinstance(element_or_tree, _NodeBase):
        return _tostring(<_NodeBase>element_or_tree,
                         encoding, write_declaration, c_pretty_print)
    elif isinstance(element_or_tree, _ElementTree):
        return _tostring((<_ElementTree>element_or_tree)._context_node,
                         encoding, write_declaration, c_pretty_print)
    else:
        raise TypeError, "Type '%s' cannot be serialized." % type(element_or_tree)

def tounicode(element_or_tree, pretty_print=False):
    """Serialize an element to the Python unicode representation of its XML
    tree.

    Note that the result does not carry an XML encoding declaration and is
    therefore not necessarily suited for serialization to byte streams without
    further treatment.
    """
    cdef int c_pretty_print
    c_pretty_print = bool(pretty_print)
    if isinstance(element_or_tree, _NodeBase):
        return _tounicode(<_NodeBase>element_or_tree, c_pretty_print)
    elif isinstance(element_or_tree, _ElementTree):
        return _tounicode((<_ElementTree>element_or_tree)._context_node,
                          c_pretty_print)
    else:
        raise TypeError, "Type '%s' cannot be serialized." % type(element_or_tree)

def parse(source, _BaseParser parser=None):
    """Return an ElementTree object loaded with source elements.  If no parser
    is provided as second argument, the default parser is used.
    """
    cdef _Document doc
    doc = _parseDocument(source, parser)
    return ElementTree(doc.getroot())


# include submodules
include "proxy.pxi"      # Proxy handling (element backpointers/memory/etc.)
include "apihelpers.pxi" # Private helper functions
include "xmlerror.pxi"   # Error and log handling
include "nsclasses.pxi"  # Namespace implementation and registry
include "docloader.pxi"  # Support for custom document loaders
include "parser.pxi"     # XML Parser
include "serializer.pxi" # XML output functions
include "xmlid.pxi"      # XMLID and IDDict
include "extensions.pxi" # XPath/XSLT extension functions
include "xpath.pxi"      # XPath evaluation

# XSL transformations
# comment out to compile without libxslt
include "xslt.pxi"


################################################################################
# Validation

cdef class _Validator:
    "Base class for XML validators."
    cdef _ErrorLog _error_log
    def __init__(self):
        self._error_log = _ErrorLog()
        
    def validate(self, etree):
        """Validate the document using this schema.

        Returns true if document is valid, false if not."""
        return self(etree)

    def assertValid(self, etree):
        "Raises DocumentInvalid if the document does not comply with the schema."
        if not self(etree):
            raise DocumentInvalid, "Document does not comply with schema"

    def assert_(self, etree):
        "Raises AssertionError if the document does not comply with the schema."
        if not self(etree):
            raise AssertionError, "Document does not comply with schema"

    property error_log:
        def __get__(self):
            return self._error_log.copy()

include "relaxng.pxi"   # RelaxNG
include "xmlschema.pxi" # XMLSchema

# configure main thread
initThread()
