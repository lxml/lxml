cimport tree, python
from tree cimport xmlDoc, xmlNode, xmlAttr, xmlNs, _isElement, _getNs
from python cimport isinstance, issubclass, hasattr, getattr, callable
from python cimport iter, str, _cstr, _isString, Py_ssize_t
cimport xpath
cimport xinclude
cimport c14n
cimport cstd

import __builtin__
cdef object True
cdef object False
True  = __builtin__.True
False = __builtin__.False

cdef object set
try:
    set = __builtin__.set
except AttributeError:
    from sets import Set as set

cdef object id
id = __builtin__.id
cdef object super
super = __builtin__.super

del __builtin__

cdef object _elementpath
import _elementpath

cdef object sys
import sys

cdef object re
import re

cdef object thread
try:
    import thread
except ImportError:
    pass

# the rules
# any libxml C argument/variable is prefixed with c_
# any non-public function/class is prefixed with an underscore
# instance creation is always through factories

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

# global per-thread setup
tree.xmlThrDefIndentTreeOutput(1)
tree.xmlThrDefLineNumbersDefaultValue(1)

_initThreadLogging()

# initialize parser (and threading)
xmlparser.xmlInitParser()

# filename encoding
cdef object _FILENAME_ENCODING
_FILENAME_ENCODING = sys.getfilesystemencoding()
if _FILENAME_ENCODING is None:
    _FILENAME_ENCODING = sys.getdefaultencoding()
if _FILENAME_ENCODING is None:
    _FILENAME_ENCODING = 'ascii'
cdef char* _C_FILENAME_ENCODING
_C_FILENAME_ENCODING = _cstr(_FILENAME_ENCODING)


# Error superclass for ElementTree compatibility
class Error(Exception):
    pass

# module level superclass for all exceptions
class LxmlError(Error):
    def __init__(self, *args):
        _initError(self, *args)
        self.error_log = __copyGlobalErrorLog()

cdef object _LxmlError
_LxmlError = LxmlError

def _superError(obj, *args):
    super(_LxmlError, obj).__init__(*args)

cdef object _initError
if isinstance(_LxmlError, type):
    _initError = _superError    # Python >= 2.5
else:
    _initError = Error.__init__ # Python <= 2.4

del _superError


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
            if item == 'dev':
                item = -3
            elif item == 'alpha':
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

    cdef int _has_raised(self):
        return self._exc_info is not None

    cdef _raise_if_stored(self):
        if self._exc_info is None:
            return
        type, value, traceback = self._exc_info
        self._exc_info = None
        if value is None and traceback is None:
            raise type
        else:
            raise type, value, traceback


# forward declaration of _BaseParser, see parser.pxi
cdef class _BaseParser


cdef public class _Document [ type LxmlDocumentType, object LxmlDocument ]:
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
        #print <long>self._c_doc, self._c_doc.dict is __GLOBAL_PARSER_CONTEXT._c_dict
        #print <long>self._c_doc, canDeallocateChildNodes(<xmlNode*>self._c_doc)
        #tree.xmlFreeDoc(c_doc)
        _deallocDocument(self._c_doc)

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

        This only works for a newly created node!
        """
        cdef xmlNs*  c_ns
        cdef xmlDoc* c_doc
        cdef char*   c_prefix
        cdef char*   c_href
        if not nsmap:
            if node_ns_utf is not None:
                self._setNodeNs(c_node, _cstr(node_ns_utf))
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
            self._setNodeNs(c_node, _cstr(node_ns_utf))

cdef _Document _documentFactory(xmlDoc* c_doc, _BaseParser parser):
    cdef _Document result
    result = _Document()
    result._c_doc = c_doc
    result._ns_counter = 0
    if parser is None:
        parser = __GLOBAL_PARSER_CONTEXT.getDefaultParser()
    result._parser = parser
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

cdef public class _NodeBase [ type LxmlNodeBaseType,
                              object LxmlNodeBase ]:
    """Base class to reference a document object and a libxml node.

    By pointing to a Document instance, a reference is kept to
    _Document as long as there is some pointer to a node in it.
    """
    cdef _Document _doc
    cdef xmlNode* _c_node
    
    def __dealloc__(self):
        #print "trying to free node:", <int>self._c_node
        #displayNode(self._c_node, 0)
        if self._c_node is not NULL:
            unregisterProxy(self)
            attemptDeallocation(self._c_node)

cdef public class _ElementTree [ type LxmlElementTreeType,
                                 object LxmlElementTree ]:
    cdef _Document _doc
    cdef _NodeBase _context_node

    # Note that _doc is only used to store the original document if we do not
    # have a _context_node.  All methods should prefer self._context_node._doc
    # to honour tree restructuring.  _doc can happily be None!

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
        if self._context_node is None:
            self._doc = doc
        else:
            self._doc = None
        return self._context_node

    def getroot(self):
        """Gets the root element for this tree.
        """
        return self._context_node

    def __copy__(self):
        return ElementTree(self._context_node)

    def __deepcopy__(self, memo):
        if self._context_node is None:
            return ElementTree()
        else:
            return ElementTree( self._context_node.__copy__() )

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
        """Returns a structural, absolute XPath expression to find that element.
        """
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
        """Creates an iterator for the root element. The iterator loops over all elements
        in this tree, in document order.
        """
        root = self.getroot()
        if root is None:
            return ()
        return root.getiterator(tag)

    def find(self, path):
        """Finds the first toplevel element with given tag. Same as getroot().find(path).
        """
        self._assertHasRoot()
        root = self.getroot()
        if path[:1] == "/":
            path = "." + path
        return root.find(path)

    def findtext(self, path, default=None):
        """Finds the element text for the first toplevel element with given tag. Same as getroot().findtext(path)
        """
        self._assertHasRoot()
        root = self.getroot()
        if path[:1] == "/":
            path = "." + path
        return root.findtext(path, default)

    def findall(self, path):
        """Finds all toplevel elements with the given tag. Same as getroot().findall(path).
        """
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
        """Validate this document using other document.

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
        """Process the XInclude nodes in this document and include the
        referenced XML fragments.
        """
        cdef int result
        # We cannot pass the XML_PARSE_NOXINCNODE option as this would free
        # the XInclude nodes - there may still be Python references to them!
        # Therefore, we allow XInclude nodes to be converted to
        # XML_XINCLUDE_START nodes.  XML_XINCLUDE_END nodes are added as
        # siblings.  Tree traversal will simply ignore them as they are not
        # typed as elements.  The included fragment is added between the two,
        # i.e. as a sibling, which does not conflict with traversal.
        self._assertHasRoot()
        result = xinclude.xmlXIncludeProcessTree(self._context_node._c_node)
        if result == -1:
            raise XIncludeError, "XInclude processing failed"

    def write_c14n(self, file):
        """C14N write of document. Always writes UTF-8.
        """
        self._assertHasRoot()
        _tofilelikeC14N(file, self._context_node)

cdef _ElementTree _elementTreeFactory(_Document doc, _NodeBase context_node):
    return _newElementTree(doc, context_node, _ElementTree)

cdef _ElementTree _newElementTree(_Document doc, _NodeBase context_node,
                                  object baseclass):
    cdef _ElementTree result
    result = baseclass()
    if context_node is None and doc is not None:
            context_node = doc.getroot()
    if context_node is None:
        result._doc = doc
    result._context_node = context_node
    return result

cdef public class _Element(_NodeBase) [ type LxmlElementType,
                                        object LxmlElement ]:
    cdef object _tag
    cdef object _attrib
    def _init(self):
        """Called after object initialisation.  Custom subclasses may override
        this if they recursively call _init() in the superclasses.
        """

    # MANIPULATORS

    def __setitem__(self, Py_ssize_t index, _NodeBase element not None):
        """Replaces the given subelement.
        """
        cdef xmlNode* c_node
        cdef xmlNode* c_next
        c_node = _findChild(self._c_node, index)
        if c_node is NULL:
            raise IndexError, index
        c_next = element._c_node.next
        _removeText(c_node.next)
        tree.xmlReplaceNode(c_node, element._c_node)
        _moveTail(c_next, element._c_node)
        moveNodeToDocument(element, self._doc)
        attemptDeallocation(c_node)

    def __delitem__(self, Py_ssize_t index):
        """Deletes the given subelement.
        """
        cdef xmlNode* c_node
        c_node = _findChild(self._c_node, index)
        if c_node is NULL:
            raise IndexError, index
        _removeText(c_node.next)
        _removeNode(c_node)

    def __delslice__(self, Py_ssize_t start, Py_ssize_t stop):
        """Deletes a number of subelements.
        """
        cdef xmlNode* c_node
        c_node = _findChild(self._c_node, start)
        _deleteSlice(c_node, start, stop)
        
    def __setslice__(self, Py_ssize_t start, Py_ssize_t stop, value):
        """Replaces a number of subelements with elements
        from a sequence.
        """
        cdef xmlNode* c_node
        cdef xmlNode* c_next
        cdef _Element mynode
        # first, find start of slice
        if start == python.PY_SSIZE_T_MAX:
            c_node = NULL
        else:
            c_node = _findChild(self._c_node, start)
            # now delete the slice
            if start != stop:
                c_node = _deleteSlice(c_node, start, stop)
        # if the insertion point is at the end, append there
        if c_node is NULL:
            for element in value:
                _appendChild(self, element)
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
        cdef xmlDoc* c_doc
        cdef _Document new_doc
        c_doc = _copyDocRoot(self._doc._c_doc, self._c_node) # recursive
        new_doc = _documentFactory(c_doc, self._doc._parser)
        return new_doc.getroot()

    def set(self, key, value):
        """Sets an element attribute.
        """
        _setAttributeValue(self, key, value)

    def append(self, _Element element not None):
        """Adds a subelement to the end of this element.
        """
        _appendChild(self, element)

    def extend(self, elements):
        """Extends the current children by the elements in the iterable.
        """
        for element in elements:
            _appendChild(self, element)

    def clear(self):
        """Resets an element. This function removes all subelements,
        clears all attributes and sets the text and tail
        attributes to None.
        """
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
        """Inserts a subelement at the given position in this element
        """
        cdef xmlNode* c_node
        cdef xmlNode* c_next
        c_node = _findChild(self._c_node, index)
        if c_node is NULL:
            _appendChild(self, element)
            return
        c_next = element._c_node.next
        tree.xmlAddPrevSibling(c_node, element._c_node)
        _moveTail(c_next, element._c_node)
        moveNodeToDocument(element, self._doc)

    def remove(self, _Element element not None):
        """Removes a matching subelement. Unlike the find methods, this
        method compares elements based on identity, not on tag value
        or contents.
        """
        cdef xmlNode* c_node
        cdef xmlNode* c_next
        c_node = element._c_node
        if c_node.parent is not self._c_node:
            raise ValueError, "Element is not a child of this node."
        c_next = element._c_node.next
        tree.xmlUnlinkNode(c_node)
        _moveTail(c_next, c_node)

    def replace(self, _Element old_element not None,
                _Element new_element not None):
        """Replaces a subelement with the element passed as second argument.
        """
        cdef xmlNode* c_old_node
        cdef xmlNode* c_old_next
        cdef xmlNode* c_new_node
        cdef xmlNode* c_new_next
        c_old_node = old_element._c_node
        if c_old_node.parent is not self._c_node:
            raise ValueError, "Element is not a child of this node."
        c_old_next = c_old_node.next
        c_new_node = new_element._c_node
        c_new_next = c_new_node.next
        tree.xmlReplaceNode(c_old_node, c_new_node)
        _moveTail(c_new_next, c_new_node)
        _moveTail(c_old_next, c_old_node)
        moveNodeToDocument(new_element, self._doc)
        
    # PROPERTIES
    property tag:
        """Element tag
        """
        def __get__(self):
            if self._tag is not None:
                return self._tag
            self._tag = _namespacedName(self._c_node)
            return self._tag
    
        def __set__(self, value):
            ns, text = _getNsTag(value)
            self._tag = value
            tree.xmlNodeSetName(self._c_node, _cstr(text))
            if ns is None:
                self._c_node.ns = NULL
            else:
                self._doc._setNodeNs(self._c_node, _cstr(ns))

    property attrib:
        """Element attribute dictionary. Where possible, use get(), set(),
        keys() and items() to access element attributes.
        """
        def __get__(self):
            if self._attrib is None:
                self._attrib = _Attrib(self)
            return self._attrib

    property text:
        """Text before the first subelement. This is either a string or 
        the value None, if there was no text.
        """
        def __get__(self):
            return _collectText(self._c_node.children)
        
        def __set__(self, value):
            _setNodeText(self._c_node, value)
        
    property tail:
        """Text after this element's end tag, but before the next sibling
        element's start tag. This is either a string or the value None, if
        there was no text.
        """
        def __get__(self):
            return _collectText(self._c_node.next)
           
        def __set__(self, value):
            _setTailText(self._c_node, value)

    # not in ElementTree, read-only
    property prefix:
        """Namespace prefix or None.
        """
        def __get__(self):
            if self._c_node.ns is not NULL:
                if self._c_node.ns.prefix is not NULL:
                    return funicode(self._c_node.ns.prefix)
            return None

    # not in ElementTree, read-only
    property nsmap:
        """Namespace prefix->URI mapping known in the context of this Element.
        """
        def __get__(self):
            cdef xmlNode* c_node
            cdef xmlNs* c_ns
            nsmap = {}
            c_node = self._c_node
            while c_node is not NULL and _isElement(c_node):
                c_ns = c_node.nsDef
                while c_ns is not NULL:
                    if c_ns.prefix is NULL:
                        prefix = None
                    else:
                        prefix = funicode(c_ns.prefix)
                    if prefix not in nsmap:
                        nsmap[prefix] = funicode(c_ns.href)
                    c_ns = c_ns.next
                c_node = c_node.parent
            return nsmap

    # ACCESSORS
    def __repr__(self):
        return "<Element %s at %x>" % (self.tag, id(self))
    
    def __getitem__(self, Py_ssize_t index):
        """Returns the given subelement.
        """        
        cdef xmlNode* c_node
        c_node = _findChild(self._c_node, index)
        if c_node is NULL:
            raise IndexError, "list index out of range"
        return _elementFactory(self._doc, c_node)

    def __getslice__(self, Py_ssize_t start, Py_ssize_t stop):
        """Returns a list containing subelements in the given range.
        """
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
        """Returns the number of subelements.
        """
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
        """Gets an element attribute.
        """
        return _getAttributeValue(self, key, default)

    def keys(self):
        """Gets a list of attribute names. The names are returned in an arbitrary
        order (just like for an ordinary Python dictionary).
        """
        return self.attrib.keys()

    def items(self):
        """Gets element attributes, as a sequence. The attributes are returned in
        an arbitrary order.
        """
        return self.attrib.items()

    def getchildren(self):
        """Returns all subelements. The elements are returned in document order.
        """
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
        """Returns the parent of this element or None for the root element.
        """
        cdef xmlNode* c_node
        c_node = _parentElement(self._c_node)
        if c_node is NULL:
            return None
        else:
            return _elementFactory(self._doc, c_node)

    def getnext(self):
        """Returns the following sibling of this element or None.
        """
        cdef xmlNode* c_node
        c_node = _nextElement(self._c_node)
        if c_node is not NULL:
            return _elementFactory(self._doc, c_node)
        return None

    def getprevious(self):
        """Returns the preceding sibling of this element or None.
        """
        cdef xmlNode* c_node
        c_node = _previousElement(self._c_node)
        if c_node is not NULL:
            return _elementFactory(self._doc, c_node)
        return None

    def itersiblings(self, preceding=False, tag=None):
        """Iterate over the following or preceding siblings of this element.

        The direction is determined by the 'preceding' keyword which defaults
        to False, i.e. forward iteration over the following siblings.  The
        generated elements can be restricted to a specific tag name with the
        'tag' keyword.
        """
        return SiblingsIterator(self, preceding, tag)

    def iterancestors(self, tag=None):
        """Iterate over the ancestors of this element (from parent to parent).

        The generated elements can be restricted to a specific tag name with
        the 'tag' keyword.
        """
        return AncestorsIterator(self, tag)

    def iterdescendants(self, tag=None):
        """Iterate over the descendants of this element in document order.

        As opposed to getiterator(), this iterator does not yield the element
        itself.  The generated elements can be restricted to a specific tag
        name with the 'tag' keyword.
        """
        return ElementDepthFirstIterator(self, tag, False)

    def iterchildren(self, reversed=False, tag=None):
        """Iterate over the children of this element.

        As opposed to using normal iteration on this element, the generated
        elements can be restricted to a specific tag name with the 'tag'
        keyword and reversed with the 'reversed' keyword.
        """
        return ElementChildIterator(self, reversed, tag)

    def getroottree(self):
        """Return an ElementTree for the root node of the document that
        contains this element.

        This is the same as following element.getparent() up the tree until it
        returns None (for the root element) and then build an ElementTree for
        the last parent that was returned."""
        return _elementTreeFactory(self._doc, None)

    def getiterator(self, tag=None):
        """Iterate over all elements in the subtree in document order (depth
        first pre-order), starting with this element.

        Can be restricted to find only elements with a specific tag or from a
        namespace.
        """
        return ElementDepthFirstIterator(self, tag)

    def makeelement(self, _tag, attrib=None, nsmap=None, **_extra):
        """Creates a new element associated with the same document.
        """
        return _makeElement(_tag, NULL, self._doc, None, attrib, nsmap, _extra)

    def find(self, path):
        """Finds the first matching subelement, by tag name or path.
        """
        return _elementpath.find(self, path)

    def findtext(self, path, default=None):
        """Finds text for the first matching subelement, by tag name or path.
        """
        return _elementpath.findtext(self, path, default)

    def findall(self, path):
        """Finds all matching subelements, by tag name or path.
        """
        return _elementpath.findall(self, path)

    def xpath(self, _path, namespaces=None, extensions=None, **_variables):
        """Evaluate an xpath expression using the element as context node.
        """
        evaluator = XPathElementEvaluator(self, namespaces, extensions)
        return evaluator.evaluate(_path, **_variables)

cdef _Element _elementFactory(_Document doc, xmlNode* c_node):
    cdef _Element result
    result = getProxy(c_node)
    if result is not None:
        return result
    if c_node is NULL:
        return None
    element_class = LOOKUP_ELEMENT_CLASS(ELEMENT_CLASS_LOOKUP_STATE,
                                         doc, c_node)
    result = element_class()
    result._doc = doc
    result._c_node = c_node
    registerProxy(result)
    result._init()
    return result

cdef class __ContentOnlyElement(_Element):
    cdef int _raiseImmutable(self) except -1:
        raise TypeError, "this element does not have children or attributes"

    def set(self, key, value):
        self._raiseImmutable()

    def append(self, value):
        self._raiseImmutable()

    def insert(self, index, value):
        self._raiseImmutable()

    def __setitem__(self, index, value):
        self._raiseImmutable()

    def __setslice__(self, start, end, value):
        self._raiseImmutable()

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

cdef class _Comment(__ContentOnlyElement):
    property tag:
        def __get__(self):
            return Comment

    def __repr__(self):
        return "<!--%s-->" % self.text
    
cdef class _ProcessingInstruction(__ContentOnlyElement):
    property tag:
        def __get__(self):
            return ProcessingInstruction

    property target:
        # not in ElementTree
        def __get__(self):
            return funicode(self._c_node.name)

        def __set__(self, value):
            value = _utf8(value)
            c_text = _cstr(value)
            tree.xmlNodeSetName(self._c_node, c_text)

    def __repr__(self):
        text = self.text
        if text:
            return "<?%s %s?>" % (self.target, text)
        else:
            return "<?%s?>" % self.target

cdef class _Attrib:
    cdef _NodeBase _element
    def __init__(self, _NodeBase element not None):
        self._element = element

    # MANIPULATORS
    def __setitem__(self, key, value):
        _setAttributeValue(self._element, key, value)

    def __delitem__(self, key):
        _delAttribute(self._element, key)

    # ACCESSORS
    def __repr__(self):
        result = {}
        for key, value in self.items():
            result[key] = value
        return repr(result)
    
    def __getitem__(self, key):
        result = _getAttributeValue(self._element, key, None)
        if result is None:
            raise KeyError, key
        else:
            return result

    def __nonzero__(self):
        cdef xmlAttr* c_attr
        c_attr = self._element._c_node.properties
        while c_attr is not NULL:
            if c_attr.type == tree.XML_ATTRIBUTE_NODE:
                return 1
            c_attr = c_attr.next
        return 0

    def __len__(self):
        cdef xmlAttr* c_attr
        cdef Py_ssize_t c
        c = 0
        c_attr = self._element._c_node.properties
        while c_attr is not NULL:
            if c_attr.type == tree.XML_ATTRIBUTE_NODE:
                c = c + 1
            c_attr = c_attr.next
        return c
    
    def get(self, key, default=None):
        return _getAttributeValue(self._element, key, default)

    def keys(self):
        cdef xmlNode* c_node
        cdef xmlAttr* c_attr
        c_node = self._element._c_node
        c_attr = c_node.properties
        result = []
        while c_attr is not NULL:
            if c_attr.type == tree.XML_ATTRIBUTE_NODE:
                python.PyList_Append(
                    result, _namespacedName(<xmlNode*>c_attr))
            c_attr = c_attr.next
        return result

    def __iter__(self):
        return iter(self.keys())
    
    def iterkeys(self):
        return iter(self.keys())

    def values(self):
        cdef xmlNode* c_node
        cdef xmlAttr* c_attr
        c_node = self._element._c_node
        c_attr = c_node.properties
        result = []
        while c_attr is not NULL:
            if c_attr.type == tree.XML_ATTRIBUTE_NODE:
                python.PyList_Append(
                    result, _attributeValue(c_node, c_attr))
            c_attr = c_attr.next
        return result

    def itervalues(self):
        return iter(self.values())

    def items(self):
        result = []
        cdef xmlNode* c_node
        cdef xmlAttr* c_attr
        c_node = self._element._c_node
        c_attr = c_node.properties
        while c_attr is not NULL:
            if c_attr.type == tree.XML_ATTRIBUTE_NODE:
                python.PyList_Append(result, (
                    _namespacedName(<xmlNode*>c_attr),
                    _attributeValue(c_node, c_attr)
                    ))
            c_attr = c_attr.next
        return result

    def iteritems(self):
        return iter(self.items())

    def has_key(self, key):
        if key in self:
            return True
        else:
            return False

    def __contains__(self, key):
        cdef xmlNode* c_node
        cdef char* c_result
        cdef char* c_tag
        ns, tag = _getNsTag(key)
        c_tag = _cstr(tag)
        c_node = self._element._c_node
        if ns is None:
            c_result = tree.xmlGetNoNsProp(c_node, c_tag)
        else:
            c_result = tree.xmlGetNsProp(c_node, c_tag, _cstr(ns))
        if c_result is NULL:
            return 0
        else:
            tree.xmlFree(c_result)
            return 1

ctypedef xmlNode* (*_node_to_node_function)(xmlNode*)

cdef public class _ElementTagMatcher [ object LxmlElementTagMatcher,
                                       type LxmlElementTagMatcherType ]:
    cdef object _pystrings
    cdef char* _href
    cdef char* _name
    cdef _initTagMatch(self, tag):
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
            if self._name[0] == c'*' and self._name[1] == c'\0':
                self._name = NULL

cdef public class _ElementIterator(_ElementTagMatcher) [
    object LxmlElementIterator, type LxmlElementIteratorType ]:
    # we keep Python references here to control GC
    cdef _NodeBase _node
    cdef _node_to_node_function _next_element
    def __iter__(self):
        return self

    cdef void _storeNext(self, _NodeBase node):
        cdef xmlNode* c_node
        c_node = self._next_element(node._c_node)
        while c_node is not NULL and \
                  not _tagMatches(c_node, self._href, self._name):
            c_node = self._next_element(c_node)
        if c_node is NULL:
            self._node = None
        else:
            # Python ref:
            self._node = _elementFactory(node._doc, c_node)

    def __next__(self):
        cdef xmlNode* c_node
        cdef _NodeBase current_node
        # Python ref:
        current_node = self._node
        if current_node is None:
            raise StopIteration
        self._storeNext(current_node)
        return current_node

cdef class ElementChildIterator(_ElementIterator):
    "Iterates over the children of an element."
    def __init__(self, _NodeBase node not None, reversed=False, tag=None):
        cdef xmlNode* c_node
        self._initTagMatch(tag)
        if reversed:
            c_node = _findChildBackwards(node._c_node, 0)
            self._next_element = _previousElement
        else:
            c_node = _findChildForwards(node._c_node, 0)
            self._next_element = _nextElement
        if tag is not None:
            while c_node is not NULL and \
                      not _tagMatches(c_node, self._href, self._name):
                c_node = self._next_element(c_node)
        if c_node is not NULL:
            # store Python ref:
            self._node = _elementFactory(node._doc, c_node)

cdef class SiblingsIterator(_ElementIterator):
    """Iterates over the siblings of an element.

    You can pass the boolean keyword ``preceding`` to specify the direction.
    """
    def __init__(self, _NodeBase node not None, preceding=False, tag=None):
        self._initTagMatch(tag)
        if preceding:
            self._next_element = _previousElement
        else:
            self._next_element = _nextElement
        self._storeNext(node)

cdef class AncestorsIterator(_ElementIterator):
    "Iterates over the ancestors of an element (from parent to parent)."
    def __init__(self, _NodeBase node not None, tag=None):
        self._initTagMatch(tag)
        self._next_element = _parentElement
        self._storeNext(node)

cdef class ElementDepthFirstIterator(_ElementTagMatcher):
    """Iterates over an element and its sub-elements in document order (depth
    first pre-order).

    If the optional 'tag' argument is not None, it returns only the elements
    that match the respective name and namespace.

    The optional boolean 'inclusive' argument defaults to True and can be set
    to False to exclude the start element itself.

    Note that the behaviour of this iterator is completely undefined if the
    tree it traverses is modified during iteration.
    """
    # we keep Python references here to control GC
    # keep next node to return and a depth counter in the tree
    cdef _NodeBase _next_node
    cdef _NodeBase _top_node
    def __init__(self, _NodeBase node not None, tag=None, inclusive=True):
        self._top_node  = node
        self._next_node = node
        self._initTagMatch(tag)
        if tag is not None and \
               not _tagMatches(node._c_node, self._href, self._name) or \
               not inclusive:
            # this cannot raise StopIteration, self._next_node != None
            self.next()

    def __iter__(self):
        return self

    def __next__(self):
        cdef xmlNode* c_node
        cdef _NodeBase current_node
        current_node = self._next_node
        if current_node is None:
            raise StopIteration
        c_node = self._next_node._c_node
        if self._name is NULL and self._href is NULL:
            c_node = self._nextNodeAnyTag(c_node)
        else:
            c_node = self._nextNodeMatchTag(c_node)
        self._next_node = _elementFactory(current_node._doc, c_node)
        return current_node

    cdef xmlNode* _nextNodeAnyTag(self, xmlNode* c_node):
        tree.BEGIN_FOR_EACH_ELEMENT_FROM(self._top_node._c_node, c_node, 0)
        return c_node
        tree.END_FOR_EACH_ELEMENT_FROM(c_node)
        return NULL

    cdef xmlNode* _nextNodeMatchTag(self, xmlNode* c_node):
        tree.BEGIN_FOR_EACH_ELEMENT_FROM(self._top_node._c_node, c_node, 0)
        if _tagMatches(c_node, self._href, self._name):
            return c_node
        tree.END_FOR_EACH_ELEMENT_FROM(c_node)
        return NULL

cdef xmlNode* _createElement(xmlDoc* c_doc, object name_utf) except NULL:
    cdef xmlNode* c_node
    c_node = tree.xmlNewDocNode(c_doc, NULL, _cstr(name_utf), NULL)
    return c_node

cdef xmlNode* _createComment(xmlDoc* c_doc, char* text):
    cdef xmlNode* c_node
    c_node = tree.xmlNewDocComment(c_doc, text)
    return c_node

cdef xmlNode* _createPI(xmlDoc* c_doc, char* target, char* text):
    cdef xmlNode* c_node
    c_node = tree.xmlNewDocPI(c_doc, target, text)
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
    """Element factory. This function returns an object implementing the Element interface.
    """
    ### also look at _Element.makeelement() and _BaseParser.makeelement() ###
    return _makeElement(_tag, NULL, None, None, attrib, nsmap, _extra)

def Comment(text=None):
    """Comment element factory. This factory function creates a special element that will
    be serialized as an XML comment.
    """
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
    return _elementFactory(doc, c_node)

def ProcessingInstruction(target, text=None):
    """Comment element factory. This factory function creates a special element that will
    be serialized as an XML comment.
    """
    cdef _Document doc
    cdef xmlNode*  c_node
    cdef xmlDoc*   c_doc
    target = _utf8(target)
    if text is None:
        text = ''
    else:
        text = _utf8(text)
    c_doc = _newDoc()
    doc = _documentFactory(c_doc, None)
    c_node = _createPI(c_doc, _cstr(target), _cstr(text))
    tree.xmlAddChild(<xmlNode*>c_doc, c_node)
    return _elementFactory(doc, c_node)

def SubElement(_Element _parent not None, _tag,
               attrib=None, nsmap=None, **_extra):
    """Subelement factory. This function creates an element instance, and appends it to an
    existing element.
    """
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
    """ElementTree wrapper class.
    """
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

def HTML(text, _BaseParser parser=None):
    """Parses an HTML document from a string constant. This function can be used
    to embed "HTML literals" in Python code.
    """
    cdef _Document doc
    if parser is None:
        parser = __GLOBAL_PARSER_CONTEXT.getDefaultParser()
        if not isinstance(parser, HTMLParser):
            parser = __DEFAULT_HTML_PARSER
    doc = _parseMemoryDocument(text, None, parser)
    return doc.getroot()

def XML(text, _BaseParser parser=None):
    """Parses an XML document from a string constant. This function can be used
    to embed "XML literals" in Python code.
    """
    cdef _Document doc
    if parser is None:
        parser = __GLOBAL_PARSER_CONTEXT.getDefaultParser()
        if not isinstance(parser, XMLParser):
            parser = __DEFAULT_XML_PARSER
    doc = _parseMemoryDocument(text, None, parser)
    return doc.getroot()

fromstring = XML

cdef class QName:
    """QName wrapper.
    """
    cdef readonly object text
    def __init__(self, text_or_uri, tag=None):
        if tag is not None:
            text_or_uri = "{%s}%s" % (text_or_uri, tag)
        elif not _isString(text_or_uri):
            text_or_uri = str(text_or_uri)
        self.text = text_or_uri
    def __str__(self):
        return self.text
    def __hash__(self):
        return self.text.__hash__()

def iselement(element):
    """Checks if an object appears to be a valid element object.
    """
    return isinstance(element, _Element)

def dump(_NodeBase elem not None, pretty_print=True):
    """Writes an element tree or element structure to sys.stdout. This function
    should be used for debugging only.
    """
    _dumpToFile(sys.stdout, elem._c_node, bool(pretty_print))

def tostring(element_or_tree, encoding=None,
             xml_declaration=None, pretty_print=False):
    """Serialize an element to an encoded string representation of its XML
    tree.

    Defaults to ASCII encoding without XML declaration.  This behaviour can be
    configured with the keyword arguments 'encoding' (string) and
    'xml_declaration' (bool).  Note that changing the encoding to a non UTF-8
    compatible encoding will enable a declaration by default.

    The keyword argument 'pretty_print' (bool) enables formatted XML.
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

    The keyword argument 'pretty_print' (bool) enables formatted XML.
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


################################################################################
# Include submodules

include "proxy.pxi"      # Proxy handling (element backpointers/memory/etc.)
include "apihelpers.pxi" # Private helper functions
include "xmlerror.pxi"   # Error and log handling
include "classlookup.pxi"# Namespace implementation and registry
include "nsclasses.pxi"  # Namespace implementation and registry
include "docloader.pxi"  # Support for custom document loaders
include "parser.pxi"     # XML Parser
include "serializer.pxi" # XML output functions
include "iterparse.pxi"  # incremental XML parsing
include "xmlid.pxi"      # XMLID and IDDict
include "extensions.pxi" # XPath/XSLT extension functions
include "xpath.pxi"      # XPath evaluation
include "xslt.pxi"       # XSL transformations


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

################################################################################
# Public C API

include "public-api.pxi"
