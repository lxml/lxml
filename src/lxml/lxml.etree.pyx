"""The ``lxml.etree`` module implements the extended ElementTree API
for XML.
"""

__docformat__ = "restructuredtext en"

cimport tree, python, config
from tree cimport xmlDoc, xmlNode, xmlAttr, xmlNs, _isElement, _getNs
from python cimport callable, _cstr, _isString
cimport xpath
cimport c14n
cimport cstd

import __builtin__

cdef object set
try:
    set = __builtin__.set
except AttributeError:
    from sets import Set as set

cdef object _unicode
_unicode = __builtin__.unicode

del __builtin__

cdef object os_path_join
from os.path import join as os_path_join

cdef object _elementpath
import _elementpath

cdef object sys
import sys

cdef object re
import re

cdef object ITER_EMPTY
ITER_EMPTY = iter(())

cdef object EMPTY_READ_ONLY_DICT
EMPTY_READ_ONLY_DICT = python.PyDictProxy_New({})

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

# set up some default namespace prefixes
cdef object _DEFAULT_NAMESPACE_PREFIXES
_DEFAULT_NAMESPACE_PREFIXES = {
    "http://www.w3.org/1999/xhtml": "html",
    "http://www.w3.org/1999/XSL/Transform": "xsl",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
    "http://schemas.xmlsoap.org/wsdl/": "wsdl",
    # xml schema
    "http://www.w3.org/2001/XMLSchema": "xs",
    "http://www.w3.org/2001/XMLSchema-instance": "xsi",
    # dublic core
    "http://purl.org/dc/elements/1.1/": "dc",
    # objectify
    "http://codespeak.net/lxml/objectify/pytype" : "py",
}

# Error superclass for ElementTree compatibility
class Error(Exception):
    pass

# module level superclass for all exceptions
class LxmlError(Error):
    """Main exception base class for lxml.  All other exceptions inherit from
    this one.
    """
    def __init__(self, message, error_log=None):
        _initError(self, message)
        if error_log is None:
            error_log = __copyGlobalErrorLog()
        self.error_log = error_log.copy()

cdef object _LxmlError
_LxmlError = LxmlError

def _superError(obj, message):
    super(_LxmlError, obj).__init__(message)

cdef object _initError
if isinstance(_LxmlError, type):
    _initError = _superError    # Python >= 2.5
else:
    _initError = Error.__init__ # Python <= 2.4

del _superError


# superclass for all syntax errors
class LxmlSyntaxError(LxmlError, SyntaxError):
    """Base class for all syntax errors.
    """
    pass

class C14NError(LxmlError):
    """Error during C14N serialisation.
    """
    pass

# version information
cdef __unpackDottedVersion(version):
    version_list = []
    l = (version.replace('-', '.').split('.') + [0]*4)[:4]
    for item in l:
        try:
            item = int(item)
        except ValueError:
            if item.startswith('dev'):
                count = item[3:]
                item = -300
            elif item.startswith('alpha'):
                count = item[5:]
                item = -200
            elif item.startswith('beta'):
                count = item[4:]
                item = -100
            else:
                count = 0
            if count:
                item = item + int(count)
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
    _LIBXML_VERSION_INT = int(re.match('[0-9]+', tree.xmlParserVersion).group(0))
except Exception:
    print "Unknown libxml2 version:", tree.xmlParserVersion
    _LIBXML_VERSION_INT = 0

LIBXML_VERSION = __unpackIntVersion(_LIBXML_VERSION_INT)
LIBXML_COMPILED_VERSION = __unpackIntVersion(tree.LIBXML_VERSION)
LXML_VERSION = __unpackDottedVersion(tree.LXML_VERSION_STRING)

__version__ = tree.LXML_VERSION_STRING


# class for temporary storage of Python references
cdef class _TempStore:
    cdef object _storage
    def __init__(self):
        self._storage = []

    cdef int add(self, obj) except -1:
        python.PyList_Append(self._storage, obj)
        return 0

    cdef int clear(self) except -1:
        del self._storage[:]
        return 0

# class for temporarily storing exceptions raised in extensions
cdef class _ExceptionContext:
    cdef object _exc_info
    cdef void clear(self):
        self._exc_info = None

    cdef void _store_raised(self):
        self._exc_info = sys.exc_info()

    cdef void _store_exception(self, exception):
        self._exc_info = (exception, None, None)

    cdef bint _has_raised(self):
        return self._exc_info is not None

    cdef int _raise_if_stored(self) except -1:
        if self._exc_info is None:
            return 0
        type, value, traceback = self._exc_info
        self._exc_info = None
        if value is None and traceback is None:
            raise type
        else:
            raise type, value, traceback


cdef class QName:
    """QName(text_or_uri, tag=None)

    QName wrapper.

    Pass a tag name by itself or a namespace URI and a tag name to
    create a qualified name.  The ``text`` property holds the
    qualified name in ``{namespace}tagname`` notation.

    You can pass QName objects wherever a tag name is expected.  Also,
    setting Element text from a QName will resolve the namespace
    prefix and set a qualified text value.
    """
    cdef readonly object text
    def __init__(self, text_or_uri, tag=None):
        if tag is not None:
            _tagValidOrRaise(_utf8(tag))
            text_or_uri = "{%s}%s" % (text_or_uri, tag)
        else:
            if not _isString(text_or_uri):
                text_or_uri = str(text_or_uri)
            tag = _getNsTag(text_or_uri)[1]
            _tagValidOrRaise(tag)
        self.text = text_or_uri
    def __str__(self):
        return self.text
    def __hash__(self):
        return self.text.__hash__()
    def __richcmp__(one, other, int op):
        if not _isString(one):
            one = str(one)
        if not _isString(other):
            other = str(other)
        return python.PyObject_RichCompare(one, other, op)


# forward declaration of _BaseParser, see parser.pxi
cdef class _BaseParser

ctypedef public xmlNode* (*_node_to_node_function)(xmlNode*)


cdef public class _Document [ type LxmlDocumentType, object LxmlDocument ]:
    """Internal base class to reference a libxml document.

    When instances of this class are garbage collected, the libxml
    document is cleaned up.
    """
    cdef int _ns_counter
    cdef object _prefix_tail
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
        tree.xmlFreeDoc(self._c_doc)
        #_deallocDocument(self._c_doc)

    cdef getroot(self):
        cdef xmlNode* c_node
        c_node = tree.xmlDocGetRootElement(self._c_doc)
        if c_node is NULL:
            return None
        return _elementFactory(self, c_node)

    cdef getdoctype(self):
        cdef tree.xmlDtd* c_dtd
        cdef xmlNode* c_root_node
        public_id = None
        sys_url   = None
        c_dtd = self._c_doc.intSubset
        if c_dtd is not NULL:
            if c_dtd.ExternalID is not NULL:
                public_id = funicode(c_dtd.ExternalID)
            if c_dtd.SystemID is not NULL:
                sys_url = funicode(c_dtd.SystemID)
        c_dtd = self._c_doc.extSubset
        if c_dtd is not NULL:
            if not public_id and c_dtd.ExternalID is not NULL:
                public_id = funicode(c_dtd.ExternalID)
            if not sys_url and c_dtd.SystemID is not NULL:
                sys_url = funicode(c_dtd.SystemID)
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
        if self._prefix_tail is not None:
            ns = ns + self._prefix_tail
        self._ns_counter = self._ns_counter + 1
        if self._ns_counter < 0:
            # overflow!
            self._ns_counter = 0
            if self._prefix_tail is None:
                self._prefix_tail = "A"
            else:
                self._prefix_tail = self._prefix_tail + "A"
        return ns

    cdef xmlNs* _findOrBuildNodeNs(self, xmlNode* c_node,
                                   char* c_href, char* c_prefix) except NULL:
        """Get or create namespace structure for a node.  Reuses the prefix if
        possible.
        """
        cdef xmlNs* c_ns
        cdef xmlNs* c_doc_ns
        cdef python.PyObject* dict_result
        if c_node.type != tree.XML_ELEMENT_NODE:
            assert c_node.type == tree.XML_ELEMENT_NODE, \
                "invalid node type %d, expected %d" % (
                c_node.type, tree.XML_ELEMENT_NODE)
        # look for existing ns
        c_ns = tree.xmlSearchNsByHref(self._c_doc, c_node, c_href)
        if c_ns is not NULL:
            return c_ns

        if c_prefix is NULL:
            dict_result = python.PyDict_GetItemString(
                _DEFAULT_NAMESPACE_PREFIXES, c_href)
            if dict_result is not NULL:
                c_prefix = _cstr(<object>dict_result)

        if c_prefix is NULL or \
               tree.xmlSearchNs(self._c_doc, c_node, c_prefix) is not NULL:
            # try to simulate ElementTree's namespace prefix creation
            while 1:
                prefix = self.buildNewPrefix()
                c_prefix = _cstr(prefix)
                # make sure it's not used already
                if tree.xmlSearchNs(self._c_doc, c_node, c_prefix) is NULL:
                    break

        c_ns = tree.xmlNewNs(c_node, c_href, c_prefix)
        if c_ns is NULL:
            python.PyErr_NoMemory()
        return c_ns

    cdef int _setNodeNs(self, xmlNode* c_node, char* href) except -1:
        "Lookup namespace structure and set it for the node."
        cdef xmlNs* c_ns
        c_ns = self._findOrBuildNodeNs(c_node, href, NULL)
        tree.xmlSetNs(c_node, c_ns)

    cdef int _setNodeNamespaces(self, xmlNode* c_node,
                                object node_ns_utf, object nsmap) except -1:
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
            return 0

        c_doc  = self._c_doc
        for prefix, href in nsmap.items():
            href_utf = _utf8(href)
            c_href = _cstr(href_utf)
            if prefix is not None and prefix:
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
        return 0

cdef extern from "etree_defs.h":
    # macro call to 't->tp_new()' for fast instantiation
    cdef _Document NEW_DOCUMENT "PY_NEW" (object t)

cdef _Document _documentFactory(xmlDoc* c_doc, _BaseParser parser):
    cdef _Document result
    result = NEW_DOCUMENT(_Document)
    result._c_doc = c_doc
    result._ns_counter = 0
    result._prefix_tail = None
    if parser is None:
        parser = __GLOBAL_PARSER_CONTEXT.getDefaultParser()
    result._parser = parser
    return result


cdef class DocInfo:
    "Document information provided by parser and DTD."
    cdef _Document _doc
    def __init__(self, tree):
        "Create a DocInfo object for an ElementTree object or root Element."
        self._doc = _documentOrRaise(tree)
        root_name, public_id, system_url = self._doc.getdoctype()
        if not root_name and (public_id or system_url):
            raise ValueError("Could not find root node")

    property root_name:
        "Returns the name of the root node as defined by the DOCTYPE."
        def __get__(self):
            root_name, public_id, system_url = self._doc.getdoctype()
            return root_name

    property public_id:
        "Returns the public ID of the DOCTYPE."
        def __get__(self):
            root_name, public_id, system_url = self._doc.getdoctype()
            return public_id

    property system_url:
        "Returns the system ID of the DOCTYPE."
        def __get__(self):
            root_name, public_id, system_url = self._doc.getdoctype()
            return system_url

    property xml_version:
        "Returns the XML version as declared by the document."
        def __get__(self):
            xml_version, encoding = self._doc.getxmlinfo()
            return xml_version

    property encoding:
        "Returns the encoding name as declared by the document."
        def __get__(self):
            xml_version, encoding = self._doc.getxmlinfo()
            return encoding

    property URL:
        "Returns the source URL of the document (or None if unknown)."
        def __get__(self):
            return self._doc.getURL()

    property doctype:
        "Returns a DOCTYPE declaration string for the document."
        def __get__(self):
            root_name, public_id, system_url = self._doc.getdoctype()
            if public_id:
                if system_url:
                    return '<!DOCTYPE %s PUBLIC "%s" "%s">' % (
                        root_name, public_id, system_url)
                else:
                    return '<!DOCTYPE %s PUBLIC "%s">' % (
                        root_name, public_id)
            elif system_url:
                return '<!DOCTYPE %s SYSTEM "%s">' % (
                    root_name, system_url)
            else:
                return ""

    property internalDTD:
        "Returns a DTD validator based on the internal subset of the document."
        def __get__(self):
            return _dtdFactory(self._doc._c_doc.intSubset)

    property externalDTD:
        "Returns a DTD validator based on the external subset of the document."
        def __get__(self):
            return _dtdFactory(self._doc._c_doc.extSubset)


cdef public class _Element [ type LxmlElementType, object LxmlElement ]:
    """Element class.

    References a document object and a libxml node.

    By pointing to a Document instance, a reference is kept to
    _Document as long as there is some pointer to a node in it.
    """
    cdef python.PyObject* _gc_doc
    cdef _Document _doc
    cdef xmlNode* _c_node
    cdef object _tag
    cdef object _attrib

    def _init(self):
        """_init(self)

        Called after object initialisation.  Custom subclasses may override
        this if they recursively call _init() in the superclasses.
        """

    def __dealloc__(self):
        #print "trying to free node:", <int>self._c_node
        #displayNode(self._c_node, 0)
        if self._c_node is not NULL:
            _unregisterProxy(self)
            attemptDeallocation(self._c_node)
        _releaseProxy(self)

    # MANIPULATORS

    def __setitem__(self, x, value):
        """__setitem__(self, x, value)

        Replaces the given subelement index or slice.
        """
        cdef xmlNode* c_node
        cdef xmlNode* c_next
        cdef _Element element
        cdef bint left_to_right
        cdef Py_ssize_t slicelength, step
        if value is None:
            raise ValueError("cannot assign None")
        if python.PySlice_Check(x):
            # slice assignment
            _findChildSlice(x, self._c_node, &c_node, &step, &slicelength)
            if step > 0:
                left_to_right = 1
            else:
                left_to_right = 0
                step = -step
            _replaceSlice(self, c_node, slicelength, step, left_to_right, value)
            return
        else:
            # otherwise: normal item assignment
            element = value
            c_node = _findChild(self._c_node, x)
            if c_node is NULL:
                raise IndexError("list index out of range")
            c_next = element._c_node.next
            _removeText(c_node.next)
            tree.xmlReplaceNode(c_node, element._c_node)
            _moveTail(c_next, element._c_node)
            moveNodeToDocument(self._doc, element._c_node)
            if not attemptDeallocation(c_node):
                moveNodeToDocument(self._doc, c_node)

    def __delitem__(self, x):
        """__delitem__(self, x)

        Deletes the given subelement or a slice.
        """
        cdef xmlNode* c_node
        cdef xmlNode* c_next
        cdef Py_ssize_t step, slicelength
        if python.PySlice_Check(x):
            # slice deletion
            if _isFullSlice(<python.slice>x):
                c_node = self._c_node.children
                if c_node is not NULL:
                    if not _isElement(c_node):
                        c_node = _nextElement(c_node)
                    while c_node is not NULL:
                        c_next = _nextElement(c_node)
                        _removeNode(self._doc, c_node)
                        c_node = c_next
            else:
                _findChildSlice(x, self._c_node, &c_node, &step, &slicelength)
                _deleteSlice(self._doc, c_node, slicelength, step)
        else:
            # item deletion
            c_node = _findChild(self._c_node, x)
            if c_node is NULL:
                raise IndexError("index out of range: %d" % x)
            _removeText(c_node.next)
            _removeNode(self._doc, c_node)

    def __deepcopy__(self, memo):
        "__deepcopy__(self, memo)"
        return self.__copy__()
        
    def __copy__(self):
        "__copy__(self)"
        cdef xmlDoc* c_doc
        cdef xmlNode* c_node
        cdef _Document new_doc
        c_doc = _copyDocRoot(self._doc._c_doc, self._c_node) # recursive
        new_doc = _documentFactory(c_doc, self._doc._parser)
        root = new_doc.getroot()
        if root is not None:
            return root
        # Comment/PI
        c_node = c_doc.children
        while c_node is not NULL and c_node.type != self._c_node.type:
            c_node = c_node.next
        if c_node is NULL:
            return None
        return _elementFactory(new_doc, c_node)

    def set(self, key, value):
        """set(self, key, value)

        Sets an element attribute.
        """
        _setAttributeValue(self, key, value)

    def append(self, _Element element not None):
        """append(self, element)

        Adds a subelement to the end of this element.
        """
        _appendChild(self, element)

    def addnext(self, _Element element):
        """addnext(self, element)

        Adds the element as a following sibling directly after this
        element.

        This is normally used to set a processing instruction or comment after
        the root node of a document.  Note that tail text is automatically
        discarded when adding at the root level.
        """
        if self._c_node.parent != NULL and not _isElement(self._c_node.parent):
            if element._c_node.type != tree.XML_PI_NODE:
                if element._c_node.type != tree.XML_COMMENT_NODE:
                    raise TypeError("Only processing instructions and comments can be siblings of the root element")
            element.tail = None
        _appendSibling(self, element)

    def addprevious(self, _Element element):
        """addprevious(self, element)

        Adds the element as a preceding sibling directly before this
        element.

        This is normally used to set a processing instruction or comment
        before the root node of a document.  Note that tail text is
        automatically discarded when adding at the root level.
        """
        if self._c_node.parent != NULL and not _isElement(self._c_node.parent):
            if element._c_node.type != tree.XML_PI_NODE:
                if element._c_node.type != tree.XML_COMMENT_NODE:
                    raise TypeError("Only processing instructions and comments can be siblings of the root element")
            element.tail = None
        _prependSibling(self, element)

    def extend(self, elements):
        """extend(self, elements)

        Extends the current children by the elements in the iterable.
        """
        for element in elements:
            _appendChild(self, element)

    def clear(self):
        """clear(self)

        Resets an element.  This function removes all subelements, clears
        all attributes and sets the text and tail properties to None.
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
        if c_node is not NULL:
            if not _isElement(c_node):
                c_node = _nextElement(c_node)
            while c_node is not NULL:
                c_node_next = _nextElement(c_node)
                _removeNode(self._doc, c_node)
                c_node = c_node_next

    def insert(self, index, _Element element not None):
        """insert(self, index, element)

        Inserts a subelement at the given position in this element
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
        moveNodeToDocument(self._doc, element._c_node)

    def remove(self, _Element element not None):
        """remove(self, element)

        Removes a matching subelement. Unlike the find methods, this
        method compares elements based on identity, not on tag value
        or contents.
        """
        cdef xmlNode* c_node
        cdef xmlNode* c_next
        c_node = element._c_node
        if c_node.parent is not self._c_node:
            raise ValueError("Element is not a child of this node.")
        c_next = element._c_node.next
        tree.xmlUnlinkNode(c_node)
        _moveTail(c_next, c_node)
        # fix namespace declarations
        moveNodeToDocument(self._doc, c_node)

    def replace(self, _Element old_element not None,
                _Element new_element not None):
        """replace(self, old_element, new_element)

        Replaces a subelement with the element passed as second argument.
        """
        cdef xmlNode* c_old_node
        cdef xmlNode* c_old_next
        cdef xmlNode* c_new_node
        cdef xmlNode* c_new_next
        c_old_node = old_element._c_node
        if c_old_node.parent is not self._c_node:
            raise ValueError("Element is not a child of this node.")
        c_old_next = c_old_node.next
        c_new_node = new_element._c_node
        c_new_next = c_new_node.next
        tree.xmlReplaceNode(c_old_node, c_new_node)
        _moveTail(c_new_next, c_new_node)
        _moveTail(c_old_next, c_old_node)
        moveNodeToDocument(self._doc, c_new_node)
        # fix namespace declarations
        moveNodeToDocument(self._doc, c_old_node)
        
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
            cdef _BaseParser parser
            ns, name = _getNsTag(value)
            parser = self._doc._parser
            if parser is not None and parser._for_html:
                _htmlTagValidOrRaise(name)
            else:
                _tagValidOrRaise(name)
            self._tag = value
            tree.xmlNodeSetName(self._c_node, _cstr(name))
            if ns is None:
                self._c_node.ns = NULL
            else:
                self._doc._setNodeNs(self._c_node, _cstr(ns))

    property attrib:
        """Element attribute dictionary. Where possible, use get(), set(),
        keys(), values() and items() to access element attributes.
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
            if isinstance(value, QName):
                value = python.PyUnicode_FromEncodedObject(
                    _resolveQNameText(self, value), 'UTF-8', 'strict')
            _setNodeText(self._c_node, value)

        # using 'del el.text' is the wrong thing to do
        #def __del__(self):
        #    _setNodeText(self._c_node, None)

    property tail:
        """Text after this element's end tag, but before the next sibling
        element's start tag. This is either a string or the value None, if
        there was no text.
        """
        def __get__(self):
            return _collectText(self._c_node.next)
           
        def __set__(self, value):
            _setTailText(self._c_node, value)

        # using 'del el.tail' is the wrong thing to do
        #def __del__(self):
        #    _setTailText(self._c_node, None)

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
    property sourceline:
        """Original line number as found by the parser or None if unknown.
        """
        def __get__(self):
            cdef long line
            line = tree.xmlGetLineNo(self._c_node)
            if line > 0:
                return line
            else:
                return None

        def __set__(self, line):
            if line < 0:
                self._c_node.line = 0
            else:
                self._c_node.line = line

    # not in ElementTree, read-only
    property nsmap:
        """Namespace prefix->URI mapping known in the context of this Element.
        """
        def __get__(self):
            cdef xmlNode* c_node
            cdef xmlNs* c_ns
            nsmap = {}
            c_node = self._c_node
            while c_node is not NULL and c_node.type == tree.XML_ELEMENT_NODE:
                c_ns = c_node.nsDef
                while c_ns is not NULL:
                    if c_ns.prefix is NULL:
                        prefix = None
                    else:
                        prefix = funicode(c_ns.prefix)
                    if not python.PyDict_GetItem(nsmap, prefix):
                        python.PyDict_SetItem(
                            nsmap, prefix, funicode(c_ns.href))
                    c_ns = c_ns.next
                c_node = c_node.parent
            return nsmap

    # ACCESSORS
    def __repr__(self):
        "__repr__(self)"
        return "<Element %s at %x>" % (self.tag, id(self))
    
    def __getitem__(self, x):
        """Returns the subelement at the given position or the requested
        slice.
        """
        cdef xmlNode* c_node
        cdef Py_ssize_t step, slicelength
        cdef Py_ssize_t c, i
        cdef _node_to_node_function next_element
        if python.PySlice_Check(x):
            # slicing
            if _isFullSlice(<python.slice>x):
                return _collectChildren(self)
            _findChildSlice(x, self._c_node, &c_node, &step, &slicelength)
            if c_node is NULL:
                return []
            if step > 0:
                next_element = _nextElement
            else:
                step = -step
                next_element = _previousElement
            result = []
            c = 0
            while c_node is not NULL and c < slicelength:
                python.PyList_Append(
                    result, _elementFactory(self._doc, c_node))
                c = c + 1
                for i from 0 <= i < step:
                    c_node = next_element(c_node)
            return result
        else:
            # indexing
            c_node = _findChild(self._c_node, x)
            if c_node is NULL:
                raise IndexError("list index out of range")
            return _elementFactory(self._doc, c_node)
            
    def __len__(self):
        """__len__(self)

        Returns the number of subelements.
        """
        return _countElements(self._c_node.children)

    def __nonzero__(self):
        "__nonzero__(self)"
        import warnings
        warnings.warn(
            "The behavior of this method will change in future versions. "
            "Use specific 'len(elem)' or 'elem is not None' test instead.",
            FutureWarning
            )
        # emulate old behaviour
        return _hasChild(self._c_node)

    def __contains__(self, element):
        "__contains__(self, element)"
        cdef xmlNode* c_node
        if not isinstance(element, _Element):
            return 0
        c_node = (<_Element>element)._c_node
        return c_node is not NULL and c_node.parent is self._c_node

    def __iter__(self):
        "__iter__(self)"
        return ElementChildIterator(self)

    def __reversed__(self):
        "__reversed__(self)"
        return ElementChildIterator(self, reversed=True)

    def index(self, _Element child not None, start=None, stop=None):
        """index(self, child, start=None, stop=None)

        Find the position of the child within the parent.

        This method is not part of the original ElementTree API.
        """
        cdef Py_ssize_t k, l
        cdef Py_ssize_t c_start, c_stop
        cdef xmlNode* c_child
        cdef xmlNode* c_start_node
        c_child = child._c_node
        if c_child.parent is not self._c_node:
            raise ValueError("Element is not a child of this node.")

        # handle the unbounded search straight away (normal case)
        if stop is None and (start is None or start == 0):
            k = 0
            c_child = c_child.prev
            while c_child is not NULL:
                if _isElement(c_child):
                    k = k + 1
                c_child = c_child.prev
            return k

        # check indices
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
                raise ValueError("list.index(x): x not in slice")

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
                    raise ValueError("list.index(x): x not in slice")
            elif c_start < 0:
                raise ValueError("list.index(x): x not in slice")

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
            raise ValueError("list.index(x): x not in slice")
        else:
            raise ValueError("list.index(x): x not in list")

    def get(self, key, default=None):
        """get(self, key, default=None)

        Gets an element attribute.
        """
        return _getAttributeValue(self, key, default)

    def keys(self):
        """keys(self)

        Gets a list of attribute names.  The names are returned in an
        arbitrary order (just like for an ordinary Python dictionary).
        """
        return _collectAttributes(self._c_node, 1)

    def values(self):
        """values(self)

        Gets element attribute values as a sequence of strings.  The
        attributes are returned in an arbitrary order.
        """
        return _collectAttributes(self._c_node, 2)

    def items(self):
        """items(self)

        Gets element attributes, as a sequence. The attributes are returned in
        an arbitrary order.
        """
        return _collectAttributes(self._c_node, 3)

    def getchildren(self):
        """getchildren(self)

        Returns all direct children.  The elements are returned in document
        order.

        :deprecated: Note that this method has been deprecated as of
          ElementTree 1.3 and lxml 2.0.  New code should use
          ``list(element)`` or simply iterate over elements.
        """
        return _collectChildren(self)

    def getparent(self):
        """getparent(self)

        Returns the parent of this element or None for the root element.
        """
        cdef xmlNode* c_node
        c_node = _parentElement(self._c_node)
        if c_node is NULL:
            return None
        else:
            return _elementFactory(self._doc, c_node)

    def getnext(self):
        """getnext(self)

        Returns the following sibling of this element or None.
        """
        cdef xmlNode* c_node
        c_node = _nextElement(self._c_node)
        if c_node is not NULL:
            return _elementFactory(self._doc, c_node)
        return None

    def getprevious(self):
        """getprevious(self)

        Returns the preceding sibling of this element or None.
        """
        cdef xmlNode* c_node
        c_node = _previousElement(self._c_node)
        if c_node is not NULL:
            return _elementFactory(self._doc, c_node)
        return None

    def itersiblings(self, tag=None, *, preceding=False):
        """itersiblings(self, tag=None, preceding=False)

        Iterate over the following or preceding siblings of this element.

        The direction is determined by the 'preceding' keyword which defaults
        to False, i.e. forward iteration over the following siblings.  The
        generated elements can be restricted to a specific tag name with the
        'tag' keyword.
        """
        return SiblingsIterator(self, tag, preceding=preceding)

    def iterancestors(self, tag=None):
        """iterancestors(self, tag=None)

        Iterate over the ancestors of this element (from parent to parent).

        The generated elements can be restricted to a specific tag name with
        the 'tag' keyword.
        """
        return AncestorsIterator(self, tag)

    def iterdescendants(self, tag=None):
        """iterdescendants(self, tag=None)

        Iterate over the descendants of this element in document order.

        As opposed to ``el.iter()``, this iterator does not yield the element
        itself.  The generated elements can be restricted to a specific tag
        name with the 'tag' keyword.
        """
        return ElementDepthFirstIterator(self, tag, inclusive=False)

    def iterchildren(self, tag=None, *, reversed=False):
        """iterchildren(self, tag=None, reversed=False)

        Iterate over the children of this element.

        As opposed to using normal iteration on this element, the generated
        elements can be restricted to a specific tag name with the 'tag'
        keyword and reversed with the 'reversed' keyword.
        """
        return ElementChildIterator(self, tag, reversed=reversed)

    def getroottree(self):
        """getroottree(self)

        Return an ElementTree for the root node of the document that
        contains this element.

        This is the same as following element.getparent() up the tree until it
        returns None (for the root element) and then build an ElementTree for
        the last parent that was returned."""
        return _elementTreeFactory(self._doc, None)

    def getiterator(self, tag=None):
        """getiterator(self, tag=None)

        Returns a sequence or iterator of all elements in the subtree in
        document order (depth first pre-order), starting with this
        element.

        Can be restricted to find only elements with a specific tag
        (pass ``tag="xyz"``) or from a namespace (pass ``tag="{ns}*"``).

        You can also pass the Element, Comment, ProcessingInstruction and
        Entity factory functions to look only for the specific element type.

        :deprecated: Note that this method is deprecated as of
          ElementTree 1.3 and lxml 2.0.  It returns an iterator in
          lxml, which diverges from the original ElementTree
          behaviour.  If you want an efficient iterator, use the
          ``element.iter()`` method instead.  You should only use this
          method in new code if you require backwards compatibility
          with older versions of lxml or ElementTree.
        """
        return ElementDepthFirstIterator(self, tag)

    def iter(self, tag=None):
        """iter(self, tag=None)

        Iterate over all elements in the subtree in document order (depth
        first pre-order), starting with this element.

        Can be restricted to find only elements with a specific tag
        (pass ``tag="xyz"``) or from a namespace (pass ``tag="{ns}*"``).

        You can also pass the Element, Comment, ProcessingInstruction and
        Entity factory functions to look only for the specific element type.
        """
        return ElementDepthFirstIterator(self, tag)

    def itertext(self, tag=None, *, with_tail=True):
        """itertext(self, tag=None, with_tail=True)

        Iterates over the text content of a subtree.

        You can pass the ``tag`` keyword argument to restrict text content to
        a specific tag name.

        You can set the ``with_tail`` keyword argument to ``False`` to skip
        over tail text.
        """
        return ElementTextIterator(self, tag, with_tail=with_tail)

    def makeelement(self, _tag, attrib=None, nsmap=None, **_extra):
        """makeelement(self, _tag, attrib=None, nsmap=None, **_extra)

        Creates a new element associated with the same document.
        """
        return _makeElement(_tag, NULL, self._doc, None, None, None,
                            attrib, nsmap, _extra)

    def find(self, path):
        """find(self, path)

        Finds the first matching subelement, by tag name or path.
        """
        if isinstance(path, QName):
            path = (<QName>path).text
        return _elementpath.find(self, path)

    def findtext(self, path, default=None):
        """findtext(self, path, default=None)

        Finds text for the first matching subelement, by tag name or path.
        """
        if isinstance(path, QName):
            path = (<QName>path).text
        return _elementpath.findtext(self, path, default)

    def findall(self, path):
        """findall(self, path)

        Finds all matching subelements, by tag name or path.
        """
        if isinstance(path, QName):
            path = (<QName>path).text
        return _elementpath.findall(self, path)

    def iterfind(self, path):
        """iterfind(self, path)

        Iterates over all matching subelements, by tag name or path.
        """
        if isinstance(path, QName):
            path = (<QName>path).text
        return _elementpath.iterfind(self, path)

    def xpath(self, _path, *, namespaces=None, extensions=None, **_variables):
        """xpath(self, _path, namespaces=None, extensions=None, **_variables)

        Evaluate an xpath expression using the element as context node.
        """
        evaluator = XPathElementEvaluator(self, namespaces=namespaces,
                                          extensions=extensions)
        return evaluator.evaluate(_path, **_variables)


cdef python.PyThread_type_lock ELEMENT_CREATION_LOCK
if config.ENABLE_THREADING:
    ELEMENT_CREATION_LOCK = python.PyThread_allocate_lock()
else:
    ELEMENT_CREATION_LOCK = NULL

cdef extern from "etree_defs.h":
    # macro call to 't->tp_new()' for fast instantiation
    cdef _Element NEW_ELEMENT "PY_NEW" (object t)

cdef _Element _elementFactory(_Document doc, xmlNode* c_node):
    cdef _Element result
    result = getProxy(c_node)
    if result is not None:
        return result
    if c_node is NULL:
        return None

    if config.ENABLE_THREADING:
        with nogil:
            python.PyThread_acquire_lock(
                ELEMENT_CREATION_LOCK, python.WAIT_LOCK)
        result = getProxy(c_node)
        if result is not None:
            python.PyThread_release_lock(ELEMENT_CREATION_LOCK)
            return result

    element_class = LOOKUP_ELEMENT_CLASS(
        ELEMENT_CLASS_LOOKUP_STATE, doc, c_node)
    if element_class is _Element:
        # fast path for standard _Element class
        result = NEW_ELEMENT(_Element)
    else:
        result = element_class()
    if hasProxy(c_node):
        # prevent re-entry race condition - we just called into Python
        if config.ENABLE_THREADING:
            python.PyThread_release_lock(ELEMENT_CREATION_LOCK)
        result._c_node = NULL
        return getProxy(c_node)
    result._doc = doc
    result._c_node = c_node
    _registerProxy(result)

    if config.ENABLE_THREADING:
        python.PyThread_release_lock(ELEMENT_CREATION_LOCK)

    if element_class is not _Element:
        result._init()
    return result


cdef class __ContentOnlyElement(_Element):
    cdef int _raiseImmutable(self) except -1:
        raise TypeError("this element does not have children or attributes")

    def set(self, key, value):
        "set(self, key, value)"
        self._raiseImmutable()

    def append(self, value):
        "append(self, value)"
        self._raiseImmutable()

    def insert(self, index, value):
        "insert(self, index, value)"
        self._raiseImmutable()

    def __setitem__(self, index, value):
        "__setitem__(self, index, value)"
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
    def __getitem__(self, x):
        "__getitem__(self, x)"
        if python.PySlice_Check(x):
            return []
        else:
            raise IndexError("list index out of range")

    def __len__(self):
        "__len__(self)"
        return 0

    def get(self, key, default=None):
        "get(self, key, default=None)"
        return None

    def keys(self):
        "keys(self)"
        return []
    
    def items(self):
        "items(self)"
        return []

    def values(self):
        "values(self)"
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

cdef class _Entity(__ContentOnlyElement):
    property tag:
        def __get__(self):
            return Entity

    property name:
        # not in ElementTree
        def __get__(self):
            return funicode(self._c_node.name)

        def __set__(self, value):
            value = _utf8(value)
            assert '&' not in value and ';' not in value, \
                "Invalid entity name '%s'" % value
            c_text = _cstr(value)
            tree.xmlNodeSetName(self._c_node, c_text)

    property text:
        # FIXME: should this be None or '&[VALUE];' or the resolved
        # entity value ?
        def __get__(self):
            return '&%s;' % funicode(self._c_node.name)

    def __repr__(self):
        return "&%s;" % self.name


cdef public class _ElementTree [ type LxmlElementTreeType,
                                 object LxmlElementTree ]:
    cdef _Document _doc
    cdef _Element _context_node

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

    def parse(self, source, _BaseParser parser=None, *, base_url=None):
        """parse(self, source, parser=None, base_url=None)

        Updates self with the content of source and returns its root
        """
        cdef _Document doc
        doc = _parseDocument(source, parser, base_url)
        self._context_node = doc.getroot()
        if self._context_node is None:
            self._doc = doc
        else:
            self._doc = None
        return self._context_node

    def _setroot(self, _Element root not None):
        """_setroot(self, root)

        Relocate the ElementTree to a new root node.
        """
        if root._c_node.type != tree.XML_ELEMENT_NODE:
            raise TypeError("Only elements can be the root of an ElementTree")
        self._context_node = root
        self._doc = None

    def getroot(self):
        """getroot(self)

        Gets the root element for this tree.
        """
        return self._context_node

    def __copy__(self):
        return _elementTreeFactory(self._doc, self._context_node)

    def __deepcopy__(self, memo):
        cdef _Element root
        if self._context_node is not None:
            root = self._context_node.__copy__()
        return _elementTreeFactory(None, root)

    property docinfo:
        """Information about the document provided by parser and DTD.  This
        value is only defined for ElementTree objects based on the root node
        of a parsed document (e.g.  those returned by the parse functions).
        """
        def __get__(self):
            self._assertHasRoot()
            return DocInfo(self._context_node._doc)

    property parser:
        """The parser that was used to parse the document in this ElementTree.
        """
        def __get__(self):
            if self._context_node is not None and \
                   self._context_node._doc is not None:
                return self._context_node._doc._parser
            if self._doc is not None:
                return self._doc._parser
            return None

    def write(self, file, *, encoding=None, method="xml",
              pretty_print=False, xml_declaration=None, with_tail=True):
        """write(self, file, encoding=None, method="xml",
                 pretty_print=False, xml_declaration=None, with_tail=True)

        Write the tree to a file or file-like object.

        Defaults to ASCII encoding and writing a declaration as needed.

        The keyword argument 'method' selects the output method: 'xml' or
        'html'.
        """
        cdef bint write_declaration
        self._assertHasRoot()
        # suppress decl. in default case (purely for ElementTree compatibility)
        if xml_declaration is not None:
            write_declaration = xml_declaration
            if encoding is None:
                encoding = 'ASCII'
        elif encoding is None:
            encoding = 'ASCII'
            write_declaration = 0
        else:
            encoding = encoding.upper()
            write_declaration = encoding not in \
                                  ('US-ASCII', 'ASCII', 'UTF8', 'UTF-8')
        _tofilelike(file, self._context_node, encoding, method,
                    write_declaration, 1, pretty_print, with_tail)

    def getpath(self, _Element element not None):
        """getpath(self, element)

        Returns a structural, absolute XPath expression to find that element.
        """
        cdef _Document doc
        cdef xmlDoc* c_doc
        cdef char* c_path
        doc = self._context_node._doc
        if element._doc is not doc:
            raise ValueError("Element is not in this tree.")
        c_doc = _fakeRootDoc(doc._c_doc, self._context_node._c_node)
        c_path = tree.xmlGetNodePath(element._c_node)
        _destroyFakeDoc(doc._c_doc, c_doc)
        if c_path is NULL:
            python.PyErr_NoMemory()
        path = c_path
        tree.xmlFree(c_path)
        return path

    def getiterator(self, tag=None):
        """getiterator(self, tag=None)

        Returns a sequence or iterator of all elements in document order
        (depth first pre-order), starting with the root element.

        Can be restricted to find only elements with a specific tag
        (pass ``tag="xyz"`` or ``tag="{ns}xyz"``) or from a namespace
        (pass ``tag="{ns}*"``).

        You can also pass the Element, Comment, ProcessingInstruction and
        Entity factory functions to look only for the specific element type.

        :deprecated: Note that this method is deprecated as of
          ElementTree 1.3 and lxml 2.0.  It returns an iterator in
          lxml, which diverges from the original ElementTree
          behaviour.  If you want an efficient iterator, use the
          ``tree.iter()`` method instead.  You should only use this
          method in new code if you require backwards compatibility
          with older versions of lxml or ElementTree.
        """
        root = self.getroot()
        if root is None:
            return ()
        return root.getiterator(tag)

    def iter(self, tag=None):
        """iter(self, tag=None)

        Creates an iterator for the root element.  The iterator loops over
        all elements in this tree, in document order.
        """
        root = self.getroot()
        if root is None:
            return ()
        return root.iter(tag)

    def find(self, path):
        """find(self, path)

        Finds the first toplevel element with given tag.  Same as
        ``tree.getroot().find(path)``.
        """
        self._assertHasRoot()
        root = self.getroot()
        if path[:1] == "/":
            path = "." + path
        return root.find(path)

    def findtext(self, path, default=None):
        """findtext(self, path, default=None)

        Finds the text for the first element matching the ElementPath
        expression.  Same as getroot().findtext(path)
        """
        self._assertHasRoot()
        root = self.getroot()
        if path[:1] == "/":
            path = "." + path
        return root.findtext(path, default)

    def findall(self, path):
        """findall(self, path)

        Finds all elements matching the ElementPath expression.  Same as
        getroot().findall(path).
        """
        self._assertHasRoot()
        root = self.getroot()
        if path[:1] == "/":
            path = "." + path
        return root.findall(path)

    def iterfind(self, path):
        """iterfind(self, path)

        Iterates over all elements matching the ElementPath expression.
        Same as getroot().finditer(path).
        """
        self._assertHasRoot()
        root = self.getroot()
        if path[:1] == "/":
            path = "." + path
        return root.iterfind(path)

    def xpath(self, _path, *, namespaces=None, extensions=None, **_variables):
        """xpath(self, _path, namespaces=None, extensions=None, **_variables)

        XPath evaluate in context of document.

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
        evaluator = XPathDocumentEvaluator(self, namespaces=namespaces,
                                           extensions=extensions)
        return evaluator.evaluate(_path, **_variables)

    def xslt(self, _xslt, extensions=None, access_control=None, **_kw):
        """xslt(self, _xslt, extensions=None, access_control=None, **_kw)

        Transform this document using other document.

        xslt is a tree that should be XSLT
        keyword parameters are XSLT transformation parameters.

        Returns the transformed tree.

        Note: if you are going to apply the same XSLT stylesheet against
        multiple documents, it is more efficient to use the XSLT
        class directly.
        """
        self._assertHasRoot()
        style = XSLT(_xslt, extensions=extensions,
                     access_control=access_control)
        return style(self, **_kw)

    def relaxng(self, relaxng):
        """relaxng(self, relaxng)

        Validate this document using other document.

        The relaxng argument is a tree that should contain a Relax NG schema.

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
        """xmlschema(self, xmlschema)

        Validate this document using other document.

        The xmlschema argument is a tree that should contain an XML Schema.

        Returns True or False, depending on whether validation
        succeeded.

        Note: If you are going to apply the same XML Schema against
        multiple documents, it is more efficient to use the XMLSchema
        class directly.
        """
        self._assertHasRoot()
        schema = XMLSchema(xmlschema)
        return schema.validate(self)

    def xinclude(self):
        """xinclude(self)

        Process the XInclude nodes in this document and include the
        referenced XML fragments.

        There is support for loading files through the file system, HTTP and
        FTP.

        Note that XInclude does not support custom resolvers in Python space
        due to restrictions of libxml2 <= 2.6.29.
        """
        cdef int result
        self._assertHasRoot()
        XInclude()(self._context_node)

    def write_c14n(self, file):
        """write_c14n(self, file)

        C14N write of document. Always writes UTF-8.
        """
        self._assertHasRoot()
        _tofilelikeC14N(file, self._context_node)

cdef _ElementTree _elementTreeFactory(_Document doc, _Element context_node):
    return _newElementTree(doc, context_node, _ElementTree)

cdef _ElementTree _newElementTree(_Document doc, _Element context_node,
                                  object baseclass):
    cdef _ElementTree result
    result = baseclass()
    if context_node is None and doc is not None:
        context_node = doc.getroot()
    if context_node is None:
        result._doc = doc
    result._context_node = context_node
    return result


cdef class _Attrib:
    """A dict-like proxy for the ``Element.attrib`` property.
    """
    cdef _Element _element
    def __init__(self, _Element element not None):
        self._element = element

    # MANIPULATORS
    def __setitem__(self, key, value):
        _setAttributeValue(self._element, key, value)

    def __delitem__(self, key):
        _delAttribute(self._element, key)

    def update(self, sequence_or_dict):
        if isinstance(sequence_or_dict, dict):
            sequence_or_dict = sequence_or_dict.iteritems()
        for key, value in sequence_or_dict:
            _setAttributeValue(self._element, key, value)

    def pop(self, key, *default):
        if python.PyTuple_GET_SIZE(default) > 1:
            raise TypeError("pop expected at most 2 arguments, got %d" % (
                    python.PyTuple_GET_SIZE(default)+1))
        result = _getAttributeValue(self._element, key, None)
        if result is None:
            if python.PyTuple_GET_SIZE(default) == 0:
                raise KeyError(key)
            else:
                result = python.PyTuple_GET_ITEM(default, 0)
                python.Py_INCREF(result)
        else:
            _delAttribute(self._element, key)
        return result

    def clear(self):
        cdef xmlNode* c_node
        c_node = self._element._c_node
        while c_node.properties is not NULL:
            tree.xmlRemoveProp(c_node.properties)

    # ACCESSORS
    def __repr__(self):
        return repr(dict( _attributeIteratorFactory(self._element, 3) ))
    
    def __getitem__(self, key):
        result = _getAttributeValue(self._element, key, None)
        if result is None:
            raise KeyError(key)
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
        return _collectAttributes(self._element._c_node, 1)

    def __iter__(self):
        return iter(_collectAttributes(self._element._c_node, 1))
    
    def iterkeys(self):
        return iter(_collectAttributes(self._element._c_node, 1))

    def values(self):
        return _collectAttributes(self._element._c_node, 2)

    def itervalues(self):
        return iter(_collectAttributes(self._element._c_node, 2))

    def items(self):
        return _collectAttributes(self._element._c_node, 3)

    def iteritems(self):
        return iter(_collectAttributes(self._element._c_node, 3))

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

    def __richcmp__(one, other, int op):
        if not python.PyDict_Check(one):
            one = dict(one)
        if not python.PyDict_Check(other):
            other = dict(other)
        return python.PyObject_RichCompare(one, other, op)

cdef class _AttribIterator:
    """Attribute iterator - for internal use only!
    """
    # XML attributes must not be removed while running!
    cdef _Element _node
    cdef xmlAttr* _c_attr
    cdef int _keysvalues # 1 - keys, 2 - values, 3 - items (key, value)
    def __iter__(self):
        return self

    def __next__(self):
        cdef xmlAttr* c_attr
        if self._node is None:
            raise StopIteration
        c_attr = self._c_attr
        while c_attr is not NULL and c_attr.type != tree.XML_ATTRIBUTE_NODE:
            c_attr = c_attr.next
        if c_attr is NULL:
            self._node = None
            raise StopIteration

        self._c_attr = c_attr.next
        if self._keysvalues == 1:
            return _namespacedName(<xmlNode*>c_attr)
        elif self._keysvalues == 2:
            return _attributeValue(self._node._c_node, c_attr)
        else:
            return (_namespacedName(<xmlNode*>c_attr),
                    _attributeValue(self._node._c_node, c_attr))

cdef object _attributeIteratorFactory(_Element element, int keysvalues):
    cdef _AttribIterator attribs
    if element._c_node.properties is NULL:
        return ITER_EMPTY
    attribs = _AttribIterator()
    attribs._node = element
    attribs._c_attr = element._c_node.properties
    attribs._keysvalues = keysvalues
    return attribs


cdef public class _ElementTagMatcher [ object LxmlElementTagMatcher,
                                       type LxmlElementTagMatcherType ]:
    cdef object _pystrings
    cdef int _node_type
    cdef char* _href
    cdef char* _name
    cdef _initTagMatch(self, tag):
        self._href = NULL
        self._name = NULL
        if tag is None:
            self._node_type = 0
        elif tag is Comment:
            self._node_type = tree.XML_COMMENT_NODE
        elif tag is ProcessingInstruction:
            self._node_type = tree.XML_PI_NODE
        elif tag is Entity:
            self._node_type = tree.XML_ENTITY_REF_NODE
        elif tag is Element:
            self._node_type = tree.XML_ELEMENT_NODE
        else:
            self._node_type = tree.XML_ELEMENT_NODE
            self._pystrings = _getNsTag(tag)
            if self._pystrings[0] is not None:
                self._href = _cstr(self._pystrings[0])
            self._name = _cstr(self._pystrings[1])
            if self._name[0] == c'*' and self._name[1] == c'\0':
                self._name = NULL

cdef public class _ElementIterator(_ElementTagMatcher) [
    object LxmlElementIterator, type LxmlElementIteratorType ]:
    # we keep Python references here to control GC
    cdef _Element _node
    cdef _node_to_node_function _next_element
    def __iter__(self):
        return self

    cdef void _storeNext(self, _Element node):
        cdef xmlNode* c_node
        c_node = self._next_element(node._c_node)
        while c_node is not NULL and \
                  self._node_type != 0 and \
                  (self._node_type != c_node.type or
                   not _tagMatches(c_node, self._href, self._name)):
            c_node = self._next_element(c_node)
        if c_node is NULL:
            self._node = None
        else:
            # Python ref:
            self._node = _elementFactory(node._doc, c_node)

    def __next__(self):
        cdef xmlNode* c_node
        cdef _Element current_node
        # Python ref:
        current_node = self._node
        if current_node is None:
            raise StopIteration
        self._storeNext(current_node)
        return current_node

cdef class ElementChildIterator(_ElementIterator):
    """ElementChildIterator(self, node, tag=None, reversed=False)
    Iterates over the children of an element.
    """
    def __init__(self, _Element node not None, tag=None, *, reversed=False):
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
                      self._node_type != 0 and \
                      (self._node_type != c_node.type or
                       not _tagMatches(c_node, self._href, self._name)):
                c_node = self._next_element(c_node)
        if c_node is not NULL:
            # store Python ref:
            self._node = _elementFactory(node._doc, c_node)

cdef class SiblingsIterator(_ElementIterator):
    """SiblingsIterator(self, node, tag=None, preceding=False)
    Iterates over the siblings of an element.

    You can pass the boolean keyword ``preceding`` to specify the direction.
    """
    def __init__(self, _Element node not None, tag=None, *, preceding=False):
        self._initTagMatch(tag)
        if preceding:
            self._next_element = _previousElement
        else:
            self._next_element = _nextElement
        self._storeNext(node)

cdef class AncestorsIterator(_ElementIterator):
    """AncestorsIterator(self, node, tag=None)
    Iterates over the ancestors of an element (from parent to parent).
    """
    def __init__(self, _Element node not None, tag=None):
        self._initTagMatch(tag)
        self._next_element = _parentElement
        self._storeNext(node)

cdef class ElementDepthFirstIterator(_ElementTagMatcher):
    """ElementDepthFirstIterator(self, node, tag=None, inclusive=True)
    Iterates over an element and its sub-elements in document order (depth
    first pre-order).

    Note that this also includes comments, entities and processing
    instructions.  To filter them out, check if the ``tag`` property
    of the returned element is a string (i.e. not None and not a
    factory function), or pass the ``Element`` factory for the ``tag``
    keyword.

    If the optional ``tag`` argument is not None, the iterator returns only
    the elements that match the respective name and namespace.

    The optional boolean argument 'inclusive' defaults to True and can be set
    to False to exclude the start element itself.

    Note that the behaviour of this iterator is completely undefined if the
    tree it traverses is modified during iteration.
    """
    # we keep Python references here to control GC
    # keep next node to return and the (s)top node
    cdef _Element _next_node
    cdef _Element _top_node
    def __init__(self, _Element node not None, tag=None, *, inclusive=True):
        self._top_node  = node
        self._next_node = node
        self._initTagMatch(tag)
        if not inclusive or \
               tag is not None and \
               self._node_type != 0 and \
               (self._node_type != node._c_node.type or
                not _tagMatches(node._c_node, self._href, self._name)):
            # this cannot raise StopIteration, self._next_node != None
            self.__next__()

    def __iter__(self):
        return self

    def __next__(self):
        cdef xmlNode* c_node
        cdef _Element current_node
        current_node = self._next_node
        if current_node is None:
            raise StopIteration
        c_node = self._next_node._c_node
        if self._name is NULL and self._href is NULL:
            c_node = self._nextNodeAnyTag(c_node)
        else:
            c_node = self._nextNodeMatchTag(c_node)
        if c_node is NULL:
            self._next_node = None
        else:
            self._next_node = _elementFactory(current_node._doc, c_node)
        return current_node

    cdef xmlNode* _nextNodeAnyTag(self, xmlNode* c_node):
        tree.BEGIN_FOR_EACH_ELEMENT_FROM(self._top_node._c_node, c_node, 0)
        if self._node_type == 0 or self._node_type == c_node.type:
            return c_node
        tree.END_FOR_EACH_ELEMENT_FROM(c_node)
        return NULL

    cdef xmlNode* _nextNodeMatchTag(self, xmlNode* c_node):
        tree.BEGIN_FOR_EACH_ELEMENT_FROM(self._top_node._c_node, c_node, 0)
        if c_node.type == tree.XML_ELEMENT_NODE:
            if _tagMatches(c_node, self._href, self._name):
                return c_node
        tree.END_FOR_EACH_ELEMENT_FROM(c_node)
        return NULL

cdef class ElementTextIterator:
    """ElementTextIterator(self, element, tag=None, with_tail=True)
    Iterates over the text content of a subtree.

    You can pass the ``tag`` keyword argument to restrict text content to a
    specific tag name.

    You can set the ``with_tail`` keyword argument to ``False`` to skip over
    tail text.
    """
    cdef object _nextEvent
    cdef _Element _start_element
    def __init__(self, _Element element not None, tag=None, *, with_tail=True):
        if with_tail:
            events = ("start", "end")
        else:
            events = ("start",)
        self._start_element = element
        self._nextEvent = iterwalk(element, events=events, tag=tag).next

    def __iter__(self):
        return self

    def __next__(self):
        cdef _Element element
        while result is None:
            event, element = self._nextEvent() # raises StopIteration
            if event == "start":
                result = element.text
            elif element is not self._start_element:
                result = element.tail
        return result

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

cdef xmlNode* _createEntity(xmlDoc* c_doc, char* name):
    cdef xmlNode* c_node
    c_node = tree.xmlNewReference(c_doc, name)
    return c_node

# module-level API for ElementTree

def Element(_tag, attrib=None, nsmap=None, **_extra):
    """Element(_tag, attrib=None, nsmap=None, **_extra)

    Element factory.  This function returns an object implementing the
    Element interface.
    """
    ### also look at _Element.makeelement() and _BaseParser.makeelement() ###
    return _makeElement(_tag, NULL, None, None, None, None,
                        attrib, nsmap, _extra)

def Comment(text=None):
    """Comment(text=None)

    Comment element factory. This factory function creates a special element that will
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
    """ProcessingInstruction(target, text=None)

    ProcessingInstruction element factory. This factory function creates a
    special element that will be serialized as an XML processing instruction.
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

PI = ProcessingInstruction

def Entity(name):
    """Entity(name)

    Entity factory.  This factory function creates a special element
    that will be serialized as an XML entity reference or character
    reference.  Note, however, that entities will not be automatically
    declared in the document.  A document that uses entity references
    requires a DTD to define the entities.
    """
    cdef _Document doc
    cdef xmlNode*  c_node
    cdef xmlDoc*   c_doc
    cdef char* c_name
    name_utf = _utf8(name)
    c_name = _cstr(name_utf)
    if c_name[0] == c'#':
        if not _characterReferenceIsValid(c_name + 1):
            raise ValueError("Invalid character reference: '%s'" % name)
    elif not _xmlNameIsValid(c_name):
        raise ValueError("Invalid entity reference: '%s'" % name)
    c_doc = _newDoc()
    doc = _documentFactory(c_doc, None)
    c_node = _createEntity(c_doc, c_name)
    tree.xmlAddChild(<xmlNode*>c_doc, c_node)
    return _elementFactory(doc, c_node)

def SubElement(_Element _parent not None, _tag,
               attrib=None, nsmap=None, **_extra):
    """SubElement(_parent, _tag, attrib=None, nsmap=None, **_extra)

    Subelement factory.  This function creates an element instance, and
    appends it to an existing element.
    """
    return _makeSubElement(_parent, _tag, None, None, attrib, nsmap, _extra)

def ElementTree(_Element element=None, *, file=None, _BaseParser parser=None):
    """ElementTree(element=None, file=None, parser=None)

    ElementTree wrapper class.
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
        try:
            doc = _parseDocument(file, parser, None)
        except _TargetParserResult, result_container:
            return result_container.result
    else:
        c_doc = _newDoc()
        doc = _documentFactory(c_doc, parser)

    return _elementTreeFactory(doc, element)

def HTML(text, _BaseParser parser=None, *, base_url=None):
    """HTML(text, parser=None, base_url=None)

    Parses an HTML document from a string constant. This function can be used
    to embed "HTML literals" in Python code.

    To override the parser with a different ``HTMLParser`` you can pass it to
    the ``parser`` keyword argument.

    The ``base_url`` keyword argument allows to set the original base URL of
    the document to support relative Paths when looking up external entities
    (DTD, XInclude, ...).
    """
    cdef _Document doc
    if parser is None:
        parser = __GLOBAL_PARSER_CONTEXT.getDefaultParser()
        if not isinstance(parser, HTMLParser):
            parser = __DEFAULT_HTML_PARSER
    try:
        doc = _parseMemoryDocument(text, base_url, parser)
        return doc.getroot()
    except _TargetParserResult, result_container:
        return result_container.result

def XML(text, _BaseParser parser=None, *, base_url=None):
    """XML(text, parser=None, base_url=None)

    Parses an XML document from a string constant. This function can be used
    to embed "XML literals" in Python code, like in

       >>> root = etree.XML("<root><test/></root>")

    To override the parser with a different ``XMLParser`` you can pass it to
    the ``parser`` keyword argument.

    The ``base_url`` keyword argument allows to set the original base URL of
    the document to support relative Paths when looking up external entities
    (DTD, XInclude, ...).
    """
    cdef _Document doc
    if parser is None:
        parser = __GLOBAL_PARSER_CONTEXT.getDefaultParser()
        if not isinstance(parser, XMLParser):
            parser = __DEFAULT_XML_PARSER
    try:
        doc = _parseMemoryDocument(text, base_url, parser)
        return doc.getroot()
    except _TargetParserResult, result_container:
        return result_container.result

def fromstring(text, _BaseParser parser=None, *, base_url=None):
    """fromstring(text, parser=None, base_url=None)

    Parses an XML document from a string.

    To override the default parser with a different parser you can pass it to
    the ``parser`` keyword argument.

    The ``base_url`` keyword argument allows to set the original base URL of
    the document to support relative Paths when looking up external entities
    (DTD, XInclude, ...).
    """
    cdef _Document doc
    try:
        doc = _parseMemoryDocument(text, base_url, parser)
        return doc.getroot()
    except _TargetParserResult, result_container:
        return result_container.result

def fromstringlist(strings, _BaseParser parser=None):
    """fromstringlist(strings, parser=None)

    Parses an XML document from a sequence of strings.

    To override the default parser with a different parser you can pass it to
    the ``parser`` keyword argument.
    """
    cdef _Document doc
    if parser is None:
        parser = __GLOBAL_PARSER_CONTEXT.getDefaultParser()
    feed = parser.feed
    for data in strings:
        feed(data)
    return parser.close()

def iselement(element):
    """iselement(element)

    Checks if an object appears to be a valid element object.
    """
    return isinstance(element, _Element)

def dump(_Element elem not None, *, pretty_print=True, with_tail=True):
    """dump(elem, pretty_print=True, with_tail=True)

    Writes an element tree or element structure to sys.stdout. This function
    should be used for debugging only.
    """
    _dumpToFile(sys.stdout, elem._c_node, pretty_print, with_tail)

def tostring(element_or_tree, *, encoding=None, method="xml",
             xml_declaration=None, pretty_print=False, with_tail=True):
    """tostring(element_or_tree, encoding=None, method="xml",
                xml_declaration=None, pretty_print=False, with_tail=True)

    Serialize an element to an encoded string representation of its XML
    tree.

    Defaults to ASCII encoding without XML declaration.  This behaviour can be
    configured with the keyword arguments 'encoding' (string) and
    'xml_declaration' (bool).  Note that changing the encoding to a non UTF-8
    compatible encoding will enable a declaration by default.

    You can also serialise to a Unicode string without declaration by
    passing the ``unicode`` function as encoding.

    The keyword argument 'pretty_print' (bool) enables formatted XML.

    The keyword argument 'method' selects the output method: 'xml',
    'html' or plain 'text'.

    You can prevent the tail text of the element from being serialised
    by passing the boolean ``with_tail`` option.  This has no impact
    on the tail text of children, which will always be serialised.
    """
    cdef bint write_declaration
    if encoding is _unicode:
        if xml_declaration:
            raise ValueError(
                "Serialisation to unicode must not request an XML declaration")
        write_declaration = 0
    elif xml_declaration is None:
        # by default, write an XML declaration only for non-standard encodings
        write_declaration = encoding is not None and encoding.upper() not in \
                            ('ASCII', 'UTF-8', 'UTF8', 'US-ASCII')
    else:
        write_declaration = xml_declaration
    if encoding is None:
        encoding = 'ASCII'

    if isinstance(element_or_tree, _Element):
        return _tostring(<_Element>element_or_tree, encoding, method,
                         write_declaration, 0, pretty_print, with_tail)
    elif isinstance(element_or_tree, _ElementTree):
        return _tostring((<_ElementTree>element_or_tree)._context_node,
                         encoding, method, write_declaration, 1, pretty_print,
                         with_tail)
    else:
        raise TypeError("Type '%s' cannot be serialized." %
                        type(element_or_tree))

def tostringlist(element_or_tree, *args, **kwargs):
    """tostringlist(element_or_tree, *args, **kwargs)

    Serialize an element to an encoded string representation of its XML
    tree, stored in a list of partial strings.

    This is purely for ElementTree 1.3 compatibility.  The result is a
    single string wrapped in a list.
    """
    return [tostring(element_or_tree, *args, **kwargs)]

def tounicode(element_or_tree, *, method="xml", pretty_print=False,
              with_tail=True):
    """tounicode(element_or_tree, method="xml", pretty_print=False,
                 with_tail=True)

    Serialize an element to the Python unicode representation of its XML
    tree.

    Note that the result does not carry an XML encoding declaration and is
    therefore not necessarily suited for serialization to byte streams without
    further treatment.

    The boolean keyword argument 'pretty_print' enables formatted XML.

    The keyword argument 'method' selects the output method: 'xml',
    'html' or plain 'text'.

    You can prevent the tail text of the element from being serialised
    by passing the boolean ``with_tail`` option.  This has no impact
    on the tail text of children, which will always be serialised.

    :deprecated: use ``tostring(el, encoding=unicode)`` instead.
    """
    if isinstance(element_or_tree, _Element):
        return _tounicode(<_Element>element_or_tree, method, 0, pretty_print,
                           with_tail)
    elif isinstance(element_or_tree, _ElementTree):
        return _tounicode((<_ElementTree>element_or_tree)._context_node,
                          method, 1, pretty_print, with_tail)
    else:
        raise TypeError("Type '%s' cannot be serialized." %
                        type(element_or_tree))

def parse(source, _BaseParser parser=None, *, base_url=None):
    """parse(source, parser=None, base_url=None)

    Return an ElementTree object loaded with source elements.  If no parser
    is provided as second argument, the default parser is used.

    The ``base_url`` keyword allows setting a URL for the document
    when parsing from a file-like object.  This is needed when looking
    up external entities (DTD, XInclude, ...) with relative paths.
    """
    cdef _Document doc
    try:
        doc = _parseDocument(source, parser, base_url)
        return _elementTreeFactory(doc, None)
    except _TargetParserResult, result_container:
        return result_container.result


################################################################################
# Include submodules

include "proxy.pxi"        # Proxy handling (element backpointers/memory/etc.)
include "apihelpers.pxi"   # Private helper functions
include "xmlerror.pxi"     # Error and log handling
include "classlookup.pxi"  # Element class lookup mechanisms
include "nsclasses.pxi"    # Namespace implementation and registry
include "docloader.pxi"    # Support for custom document loaders
include "parser.pxi"       # XML Parser
include "parsertarget.pxi" # ET Parser target
include "serializer.pxi"   # XML output functions
include "iterparse.pxi"    # incremental XML parsing
include "xmlid.pxi"        # XMLID and IDDict
include "xinclude.pxi"     # XInclude
include "extensions.pxi"   # XPath/XSLT extension functions
include "xpath.pxi"        # XPath evaluation
include "xslt.pxi"         # XSL transformations


################################################################################
# Validation

class DocumentInvalid(LxmlError):
    """Validation error.

    Raised by all document validators when their ``assertValid(tree)``
    method fails.
    """
    pass

cdef class _Validator:
    "Base class for XML validators."
    cdef _ErrorLog _error_log
    def __init__(self):
        "__init__(self)"
        self._error_log = _ErrorLog()

    def validate(self, etree):
        """validate(self, etree)

        Validate the document using this schema.

        Returns true if document is valid, false if not.
        """
        return self(etree)

    def assertValid(self, etree):
        """assertValid(self, etree)

        Raises `DocumentInvalid` if the document does not comply with the schema.
        """
        if not self(etree):
            raise DocumentInvalid(self._error_log._buildExceptionMessage(
                    "Document does not comply with schema"),
                                  self._error_log)

    def assert_(self, etree):
        """assert_(self, etree)

        Raises `AssertionError` if the document does not comply with the schema.
        """
        if not self(etree):
            raise AssertionError(self._error_log._buildExceptionMessage(
                "Document does not comply with schema"))

    property error_log:
        "The log of validation errors and warnings."
        def __get__(self):
            return self._error_log.copy()

include "dtd.pxi"        # DTD
include "relaxng.pxi"    # RelaxNG
include "xmlschema.pxi"  # XMLSchema
include "schematron.pxi" # Schematron (requires libxml2 2.6.21+)

################################################################################
# Public C API

include "public-api.pxi"
