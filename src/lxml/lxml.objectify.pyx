"""The ``lxml.objectify`` module implements a Python object API for
XML.  It is based on `lxml.etree`.
"""

from etreepublic cimport _Document, _Element, ElementBase
from etreepublic cimport _ElementIterator, ElementClassLookup
from etreepublic cimport elementFactory, import_lxml__etree, textOf
from python cimport callable, _cstr
cimport etreepublic as cetree
cimport python
cimport tree
cimport cstd

cdef object etree
from lxml import etree
# initialize C-API of lxml.etree
import_lxml__etree()

__version__ = etree.__version__

cdef object re
import re

cdef object __builtin__
import __builtin__

cdef object set
try:
    set = __builtin__.set
except AttributeError:
    from sets import Set as set

cdef object IGNORABLE_ERRORS
IGNORABLE_ERRORS = (ValueError, TypeError)

cdef object islice
from itertools import islice

cdef object _typename(object t):
    cdef char* c_name
    cdef char* s
    c_name = python._fqtypename(t)
    s = cstd.strrchr(c_name, c'.')
    if s == NULL:
        return c_name
    else:
        return (s+1)

# namespace/name for "pytype" hint attribute
cdef object PYTYPE_NAMESPACE
cdef char* _PYTYPE_NAMESPACE

cdef object PYTYPE_ATTRIBUTE_NAME
cdef char* _PYTYPE_ATTRIBUTE_NAME

PYTYPE_ATTRIBUTE = None

cdef object TREE_PYTYPE_NAME
TREE_PYTYPE_NAME = "TREE"

def setPytypeAttributeTag(attribute_tag=None):
    """Changes name and namespace of the XML attribute that holds Python type
    information.

    Reset by calling without argument.

    Default: "{http://codespeak.net/lxml/objectify/pytype}pytype"
    """
    global PYTYPE_ATTRIBUTE, _PYTYPE_NAMESPACE, _PYTYPE_ATTRIBUTE_NAME
    global PYTYPE_NAMESPACE, PYTYPE_ATTRIBUTE_NAME
    if attribute_tag is None:
        PYTYPE_NAMESPACE      = "http://codespeak.net/lxml/objectify/pytype"
        PYTYPE_ATTRIBUTE_NAME = "pytype"
    else:
        PYTYPE_NAMESPACE, PYTYPE_ATTRIBUTE_NAME = cetree.getNsTag(attribute_tag)
    _PYTYPE_NAMESPACE      = _cstr(PYTYPE_NAMESPACE)
    _PYTYPE_ATTRIBUTE_NAME = _cstr(PYTYPE_ATTRIBUTE_NAME)
    PYTYPE_ATTRIBUTE = cetree.namespacedNameFromNsName(
        _PYTYPE_NAMESPACE, _PYTYPE_ATTRIBUTE_NAME)

setPytypeAttributeTag()


# namespaces for XML Schema
cdef object XML_SCHEMA_NS
XML_SCHEMA_NS = "http://www.w3.org/2001/XMLSchema"
cdef char* _XML_SCHEMA_NS
_XML_SCHEMA_NS = _cstr(XML_SCHEMA_NS)

cdef object XML_SCHEMA_INSTANCE_NS
XML_SCHEMA_INSTANCE_NS = "http://www.w3.org/2001/XMLSchema-instance"
cdef char* _XML_SCHEMA_INSTANCE_NS
_XML_SCHEMA_INSTANCE_NS = _cstr(XML_SCHEMA_INSTANCE_NS)

cdef object XML_SCHEMA_INSTANCE_NIL_ATTR
XML_SCHEMA_INSTANCE_NIL_ATTR = "{%s}nil" % XML_SCHEMA_INSTANCE_NS
cdef object XML_SCHEMA_INSTANCE_TYPE_ATTR
XML_SCHEMA_INSTANCE_TYPE_ATTR = "{%s}type" % XML_SCHEMA_INSTANCE_NS


################################################################################
# Element class for the main API

cdef class ObjectifiedElement(ElementBase):
    """Main XML Element class.

    Element children are accessed as object attributes.  Multiple children
    with the same name are available through a list index.  Example:

       >>> root = etree.XML("<root><c1><c2>0</c2><c2>1</c2></c1></root>")
       >>> second_c2 = root.c1.c2[1]
    """
    def __iter__(self):
        """Iterate over self and all siblings with the same tag.
        """
        parent = self.getparent()
        if parent is None:
            return iter([self])
        return etree.ElementChildIterator(parent, tag=self.tag)

    def __str__(self):
        if __RECURSIVE_STR:
            return _dump(self, 0)
        else:
            return textOf(self._c_node) or ''

    property text:
        def __get__(self):
            return textOf(self._c_node)

    property __dict__:
        """A fake implementation for __dict__ to support dir() etc.

        Note that this only considers the first child with a given name.
        """
        def __get__(self):
            cdef char* c_ns
            cdef char* c_child_ns
            cdef _Element child
            c_ns = tree._getNs(self._c_node)
            if c_ns is NULL:
                tag = None
            else:
                tag = "{%s}*" % c_ns
            children = {}
            for child in etree.ElementChildIterator(self, tag=tag):
                if c_ns is NULL and tree._getNs(child._c_node) is not NULL:
                    continue
                name = child._c_node.name
                if python.PyDict_GetItem(children, name) is NULL:
                    python.PyDict_SetItem(children, name, child)
            return children

    def __len__(self):
        """Count self and siblings with the same tag.
        """
        return _countSiblings(self._c_node)

    def countchildren(self):
        """countchildren(self)

        Return the number of children of this element, regardless of their
        name.
        """
        # copied from etree
        cdef Py_ssize_t c
        cdef tree.xmlNode* c_node
        c = 0
        c_node = self._c_node.children
        while c_node is not NULL:
            if tree._isElement(c_node):
                c = c + 1
            c_node = c_node.next
        return c

    def getchildren(self):
        """getchildren(self)

        Returns a sequence of all direct children.  The elements are
        returned in document order.
        """
        cdef tree.xmlNode* c_node
        result = []
        c_node = self._c_node.children
        while c_node is not NULL:
            if tree._isElement(c_node):
                python.PyList_Append(
                    result, cetree.elementFactory(self._doc, c_node))
            c_node = c_node.next
        return result

    def __getattr__(self, tag):
        """Return the (first) child with the given tag name.  If no namespace
        is provided, the child will be looked up in the same one as self.
        """
        return _lookupChildOrRaise(self, tag)

    def __setattr__(self, tag, value):
        """Set the value of the (first) child with the given tag name.  If no
        namespace is provided, the child will be looked up in the same one as
        self.
        """
        cdef _Element element
        # properties are looked up /after/ __setattr__, so we must emulate them
        if tag == 'text' or tag == 'pyval':
            # read-only !
            raise TypeError("attribute '%s' of '%s' objects is not writable" %
                            (tag, _typename(self)))
        elif tag == 'tail':
            cetree.setTailText(self._c_node, value)
            return
        elif tag == 'tag':
            ElementBase.tag.__set__(self, value)
            return

        tag = _buildChildTag(self, tag)
        element = _lookupChild(self, tag)
        if element is None:
            _appendValue(self, tag, value)
        else:
            _replaceElement(element, value)

    def __delattr__(self, tag):
        child = _lookupChildOrRaise(self, tag)
        self.remove(child)

    def addattr(self, tag, value):
        """addattr(self, tag, value)

        Add a child value to the element.

        As opposed to append(), it sets a data value, not an element.
        """
        _appendValue(self, _buildChildTag(self, tag), value)

    def __getitem__(self, key):
        """Return a sibling, counting from the first child of the parent.  The
        method behaves like both a dict and a sequence.

        * If argument is an integer, returns the sibling at that position.

        * If argument is a string, does the same as getattr().  This can be
          used to provide namespaces for element lookup, or to look up
          children with special names (``text`` etc.).

        * If argument is a slice object, returns the matching slice.
        """
        cdef tree.xmlNode* c_self_node
        cdef tree.xmlNode* c_parent
        cdef tree.xmlNode* c_node
        cdef Py_ssize_t start, stop, step, slicelength
        if python._isString(key):
            return _lookupChildOrRaise(self, key)
        elif python.PySlice_Check(key):
            return list(self)[key]
        # normal item access
        c_self_node = self._c_node
        c_parent = c_self_node.parent
        if c_parent is NULL:
            if key == 0:
                return self
            else:
                raise IndexError(key)
        if key < 0:
            c_node = c_parent.last
        else:
            c_node = c_parent.children
        c_node = _findFollowingSibling(
            c_node, tree._getNs(c_self_node), c_self_node.name, key)
        if c_node is NULL:
            raise IndexError(key)
        return elementFactory(self._doc, c_node)

    def __setitem__(self, key, value):
        """Set the value of a sibling, counting from the first child of the
        parent.  Implements key assignment, item assignment and slice
        assignment.

        * If argument is an integer, sets the sibling at that position.

        * If argument is a string, does the same as setattr().  This is used
          to provide namespaces for element lookup.

        * If argument is a sequence (list, tuple, etc.), assign the contained
          items to the siblings.
        """
        cdef _Element element
        cdef tree.xmlNode* c_node
        if python._isString(key):
            key = _buildChildTag(self, key)
            element = _lookupChild(self, key)
            if element is None:
                _appendValue(self, key, value)
            else:
                _replaceElement(element, value)
            return

        if self._c_node.parent is NULL:
            # the 'root[i] = ...' case
            raise TypeError("assignment to root element is invalid")

        if python.PySlice_Check(key):
            # slice assignment
            _setSlice(key, self, value)
        else:
            # normal index assignment
            if key < 0:
                c_node = self._c_node.parent.last
            else:
                c_node = self._c_node.parent.children
            c_node = _findFollowingSibling(
                c_node, tree._getNs(self._c_node), self._c_node.name, key)
            if c_node is NULL:
                raise IndexError(key)
            element = elementFactory(self._doc, c_node)
            _replaceElement(element, value)

    def __delitem__(self, key):
        cdef Py_ssize_t start, stop, step, slicelength
        parent = self.getparent()
        if parent is None:
            raise TypeError("deleting items not supported by root element")
        if python.PySlice_Check(key):
            # slice deletion
            del_items = list(self)[key]
            remove = parent.remove
            for el in del_items:
                remove(el)
        else:
            # normal index deletion
            sibling = self.__getitem__(key)
            parent.remove(sibling)

    def iterfind(self, path):
        "iterfind(self, path)"
        # Reimplementation of Element.iterfind() to make it work without child
        # iteration.
        xpath = etree.ETXPath(path)
        return iter(xpath(self))

    def findall(self, path):
        "findall(self, path)"
        # Reimplementation of Element.findall() to make it work without child
        # iteration.
        xpath = etree.ETXPath(path)
        return xpath(self)

    def find(self, path):
        "find(self, path)"
        # Reimplementation of Element.find() to make it work without child
        # iteration.
        result = self.findall(path)
        if isinstance(result, list) and len(result):
            return result[0]
        elif isinstance(result, _Element):
            return result
        else:
            return None

    def findtext(self, path, default=None):
        "findtext(self, path, default=None)"
        # Reimplementation of Element.findtext() to make it work without child
        # iteration.
        result = self.find(path)
        if isinstance(result, _Element):
            return result.text or ""
        else:
            return default

    def descendantpaths(self, prefix=None):
        """descendantpaths(self, prefix=None)

        Returns a list of object path expressions for all descendants.
        """
        if prefix is not None and not python._isString(prefix):
            prefix = '.'.join(prefix)
        return _buildDescendantPaths(self._c_node, prefix)

cdef Py_ssize_t _countSiblings(tree.xmlNode* c_start_node):
    cdef tree.xmlNode* c_node
    cdef char* c_href
    cdef char* c_tag
    cdef Py_ssize_t count
    c_tag  = c_start_node.name
    c_href = tree._getNs(c_start_node)
    count = 1
    c_node = c_start_node.next
    while c_node is not NULL:
        if c_node.type == tree.XML_ELEMENT_NODE and \
               cetree.tagMatches(c_node, c_href, c_tag):
            count = count + 1
        c_node = c_node.next
    c_node = c_start_node.prev
    while c_node is not NULL:
        if c_node.type == tree.XML_ELEMENT_NODE and \
               cetree.tagMatches(c_node, c_href, c_tag):
            count = count + 1
        c_node = c_node.prev
    return count

cdef tree.xmlNode* _findFollowingSibling(tree.xmlNode* c_node,
                                         char* href, char* name,
                                         Py_ssize_t index):
    cdef tree.xmlNode* (*next)(tree.xmlNode*)
    if index >= 0:
        next = cetree.nextElement
    else:
        index = -1 - index
        next = cetree.previousElement
    while c_node is not NULL:
        if c_node.type == tree.XML_ELEMENT_NODE and \
               cetree.tagMatches(c_node, href, name):
            index = index - 1
            if index < 0:
                return c_node
        c_node = next(c_node)
    return NULL

cdef object _lookupChild(_Element parent, tag):
    cdef tree.xmlNode* c_result
    cdef tree.xmlNode* c_node
    cdef char* c_href
    cdef char* c_tag
    ns, tag = cetree.getNsTag(tag)
    c_tag = _cstr(tag)
    c_node = parent._c_node
    if ns is None:
        c_href = tree._getNs(c_node)
    else:
        c_href = _cstr(ns)
    c_result = _findFollowingSibling(c_node.children, c_href, c_tag, 0)
    if c_result is NULL:
        return None
    return elementFactory(parent._doc, c_result)

cdef object _lookupChildOrRaise(_Element parent, tag):
    element = _lookupChild(parent, tag)
    if element is None:
        raise AttributeError("no such child: " +
                             _buildChildTag(parent, tag))
    return element

cdef object _buildChildTag(_Element parent, tag):
    cdef char* c_href
    cdef char* c_tag
    ns, tag = cetree.getNsTag(tag)
    c_tag = _cstr(tag)
    if ns is None:
        c_href = tree._getNs(parent._c_node)
    else:
        c_href = _cstr(ns)
    return cetree.namespacedNameFromNsName(c_href, c_tag)

cdef object _replaceElement(_Element element, value):
    cdef _Element new_element
    if isinstance(value, _Element):
        # deep copy the new element
        new_element = cetree.deepcopyNodeToDocument(
            element._doc, (<_Element>value)._c_node)
        new_element.tag = element.tag
    elif python.PyList_Check(value) or python.PyTuple_Check(value):
        element[:] = value
        return
    else:
        new_element = element.makeelement(element.tag)
        _setElementValue(new_element, value)
    element.getparent().replace(element, new_element)

cdef object _appendValue(_Element parent, tag, value):
    cdef _Element new_element
    if isinstance(value, _Element):
        # deep copy the new element
        new_element = cetree.deepcopyNodeToDocument(
            parent._doc, (<_Element>value)._c_node)
        new_element.tag = tag
        cetree.appendChild(parent, new_element)
    elif python.PyList_Check(value) or python.PyTuple_Check(value):
        for item in value:
            _appendValue(parent, tag, item)
    else:
        new_element = cetree.makeSubElement(
            parent, tag, None, None, None, None)
        _setElementValue(new_element, value)

cdef _setElementValue(_Element element, value):
    cdef python.PyObject* dict_result
    if value is None:
        cetree.setAttributeValue(
            element, XML_SCHEMA_INSTANCE_NIL_ATTR, "true")
    elif isinstance(value, _Element):
        _replaceElement(element, value)
    else:
        cetree.delAttributeFromNsName(
            element._c_node, _XML_SCHEMA_INSTANCE_NS, "nil")
        if python._isString(value):
            pytype_name = "str"
        else:
            pytype_name = _typename(value)
            if isinstance(value, bool):
                value = _lower_bool(value)
            else:
                value = str(value)
        dict_result = python.PyDict_GetItem(_PYTYPE_DICT, pytype_name)
        if dict_result is not NULL:
            cetree.setAttributeValue(element, PYTYPE_ATTRIBUTE, pytype_name)
        else:
            cetree.delAttributeFromNsName(element._c_node, PYTYPE_NAMESPACE,
                                          PYTYPE_ATTRIBUTE_NAME)
    cetree.setNodeText(element._c_node, value)

cdef _setSlice(slice, _Element target, items):
    cdef _Element parent
    cdef tree.xmlNode* c_node
    cdef Py_ssize_t c_step, c_start, pos
    # collect existing slice
    if (<python.slice>slice).step is None:
        c_step = 1
    else:
        c_step = (<python.slice>slice).step
    if c_step == 0:
        raise ValueError("Invalid slice")
    del_items = target[slice]

    # collect new values
    new_items = []
    tag = target.tag
    for item in items:
        if isinstance(item, _Element):
            # deep copy the new element
            new_element = cetree.deepcopyNodeToDocument(
                target._doc, (<_Element>item)._c_node)
            new_element.tag = tag
        else:
            new_element = cetree.makeElement(
                tag, target._doc, None, None, None, None, None)
            _setElementValue(new_element, item)
        python.PyList_Append(new_items, new_element)

    # sanity check - raise what a list would raise
    if c_step != 1 and \
            python.PyList_GET_SIZE(del_items) != python.PyList_GET_SIZE(new_items):
        raise ValueError(
            "attempt to assign sequence of size %d to extended slice of size %d" % (
                python.PyList_GET_SIZE(new_items),
                python.PyList_GET_SIZE(del_items)))

    # replace existing items
    pos = 0
    parent = target.getparent()
    replace = parent.replace
    while pos < python.PyList_GET_SIZE(new_items) and \
            pos < python.PyList_GET_SIZE(del_items):
        replace(del_items[pos], new_items[pos])
        pos += 1
    # remove leftover items
    if pos < python.PyList_GET_SIZE(del_items):
        remove = parent.remove
        while pos < python.PyList_GET_SIZE(del_items):
            remove(del_items[pos])
            pos += 1
    # append remaining new items
    if pos < python.PyList_GET_SIZE(new_items):
        # the sanity check above guarantees (step == 1)
        if pos > 0:
            item = new_items[pos-1]
        else:
            if (<python.slice>slice).start > 0:
                c_node = parent._c_node.children
            else:
                c_node = parent._c_node.last
            c_node = _findFollowingSibling(
                c_node, tree._getNs(target._c_node), target._c_node.name,
                (<python.slice>slice).start - 1)
            if c_node is NULL:
                while pos < python.PyList_GET_SIZE(new_items):
                    cetree.appendChild(parent, new_items[pos])
                    pos += 1
                return
            item = cetree.elementFactory(parent._doc, c_node)
        while pos < python.PyList_GET_SIZE(new_items):
            add = item.addnext
            item = new_items[pos]
            add(item)
            pos += 1

################################################################################
# Data type support in subclasses

cdef class ObjectifiedDataElement(ObjectifiedElement):
    """This is the base class for all data type Elements.  Subclasses should
    override the 'pyval' property and possibly the __str__ method.
    """
    property pyval:
        def __get__(self):
            return textOf(self._c_node)

    def __str__(self):
        return textOf(self._c_node) or ''

    def __repr__(self):
        return textOf(self._c_node) or ''

    def _setText(self, s):
        """For use in subclasses only. Don't use unless you know what you are
        doing.
        """
        cetree.setNodeText(self._c_node, s)

cdef class NumberElement(ObjectifiedDataElement):
    cdef object _type
    def _setValueParser(self, function):
        "Set the function that parses the Python value from a string."
        self._type = function

    cdef _value(self):
        return self._type(textOf(self._c_node))

    property pyval:
        def __get__(self):
            return self._value()

    def __int__(self):
        return int(textOf(self._c_node))

    def __long__(self):
        return long(textOf(self._c_node))

    def __float__(self):
        return float(textOf(self._c_node))

    def __str__(self):
        return str(self._type(textOf(self._c_node)))

    def __repr__(self):
        return repr(self._type(textOf(self._c_node)))

#    def __oct__(self):
#    def __hex__(self):

    def __richcmp__(self, other, int op):
        if hasattr(other, 'pyval'):
            other = other.pyval
        return python.PyObject_RichCompare(
            _numericValueOf(self), other, op)

    def __add__(self, other):
        return _numericValueOf(self) + _numericValueOf(other)

    def __sub__(self, other):
        return _numericValueOf(self) - _numericValueOf(other)

    def __mul__(self, other):
        return _numericValueOf(self) * _numericValueOf(other)

    def __div__(self, other):
        return _numericValueOf(self) / _numericValueOf(other)

    def __truediv__(self, other):
        return _numericValueOf(self) / _numericValueOf(other)

    def __mod__(self, other):
        return _numericValueOf(self) % _numericValueOf(other)

    def __pow__(self, other, modulo):
        if modulo is None:
            return _numericValueOf(self) ** _numericValueOf(other)
        else:
            return pow(_numericValueOf(self), _numericValueOf(other), modulo)

    def __neg__(self):
        return - _numericValueOf(self)

    def __pos__(self):
        return + _numericValueOf(self)

    def __abs__(self):
        return abs( _numericValueOf(self) )

    def __nonzero__(self):
        return _numericValueOf(self) != 0

    def __invert__(self):
        return ~ _numericValueOf(self)

    def __lshift__(self, other):
        return _numericValueOf(self) << _numericValueOf(other)

    def __rshift__(self, other):
        return _numericValueOf(self) >> _numericValueOf(other)

    def __and__(self, other):
        return _numericValueOf(self) & _numericValueOf(other)

    def __or__(self, other):
        return _numericValueOf(self) | _numericValueOf(other)

    def __xor__(self, other):
        return _numericValueOf(self) ^ _numericValueOf(other)

cdef class IntElement(NumberElement):
    def _init(self):
        self._type = int

cdef class LongElement(NumberElement):
    def _init(self):
        self._type = long

cdef class FloatElement(NumberElement):
    def _init(self):
        self._type = float

cdef class StringElement(ObjectifiedDataElement):
    """String data class.

    Note that this class does *not* support the sequence protocol of strings:
    len(), iter(), str_attr[0], str_attr[0:1], etc. are *not* supported.
    Instead, use the .text attribute to get a 'real' string.
    """
    property pyval:
        def __get__(self):
            return textOf(self._c_node) or ''

    def __repr__(self):
        return repr(textOf(self._c_node) or '')

    def strlen(self):
        text = textOf(self._c_node)
        if text is None:
            return 0
        else:
            return len(text)

    def __nonzero__(self):
        text = textOf(self._c_node)
        if text is None:
            return False
        return len(text) > 0

    def __richcmp__(self, other, int op):
        if hasattr(other, 'pyval'):
            other = other.pyval
        return python.PyObject_RichCompare(
            _strValueOf(self), other, op)

    def __add__(self, other):
        text  = _strValueOf(self)
        other = _strValueOf(other)
        if text is None:
            return other
        if other is None:
            return text
        return text + other

    def __mul__(self, other):
        if isinstance(self, StringElement):
            return textOf((<StringElement>self)._c_node) * _numericValueOf(other)
        elif isinstance(other, StringElement):
            return _numericValueOf(self) * textOf((<StringElement>other)._c_node)
        else:
            raise TypeError("invalid types for * operator")

    def __mod__(self, other):
        return _strValueOf(self) % other

cdef class NoneElement(ObjectifiedDataElement):
    def __str__(self):
        return "None"

    def __repr__(self):
        return "None"

    def __nonzero__(self):
        return False

    def __richcmp__(self, other, int op):
        if other is None or self is None:
            return python.PyObject_RichCompare(None, None, op)
        if isinstance(self, NoneElement):
            return python.PyObject_RichCompare(None, other, op)
        else:
            return python.PyObject_RichCompare(self, None, op)

    property pyval:
        def __get__(self):
            return None

cdef class BoolElement(ObjectifiedDataElement):
    """Boolean type base on string values: 'true' or 'false'.
    """
    cdef int _boolval(self) except -1:
        cdef char* c_str
        text = textOf(self._c_node)
        if text is None:
            return 0
        c_str = _cstr(text)
        if c_str[0] == c'0' or c_str[0] == c'f' or c_str[0] == c'F':
            if c_str[1] == c'\0' or text == "false" or text.lower() == "false":
                # '0' or 'f' or 'false'
                return 0
        elif c_str[0] == c'1' or c_str[0] == c't' or c_str[0] == c'T':
            if c_str[1] == c'\0' or text == "true" or text.lower() == "true":
                # '1' or 't' or 'true'
                return 1
        raise ValueError("Invalid boolean value: '%s'" % text)

    def __nonzero__(self):
        if self._boolval():
            return True
        else:
            return False

    def __richcmp__(self, other, int op):
        if hasattr(other, 'pyval'):
            other = other.pyval
        if hasattr(self, 'pyval'):
            self_val = self.pyval
        else:
            self_val = bool(self)
        return python.PyObject_RichCompare(self_val, other, op)

    def __str__(self):
        if self._boolval():
            return "True"
        else:
            return "False"

    def __repr__(self):
        if self._boolval():
            return "True"
        else:
            return "False"

    property pyval:
        def __get__(self):
            return self.__nonzero__()

def __checkBool(s):
    if s != 'true' and s != 'false' and s != '1' and s != '0':
        raise ValueError

cdef object _strValueOf(obj):
    if python._isString(obj):
        return obj
    if isinstance(obj, _Element):
        return textOf((<_Element>obj)._c_node) or ''
    if obj is None:
        return ''
    return str(obj)

cdef object _numericValueOf(obj):
    if isinstance(obj, NumberElement):
        return (<NumberElement>obj)._type(
            textOf((<NumberElement>obj)._c_node))
    elif hasattr(obj, 'pyval'):
        # not always numeric, but Python will raise the right exception
        return obj.pyval
    return obj

################################################################################
# Python type registry

cdef class PyType:
    """PyType(self, name, type_check, type_class, stringify=None)
    User defined type.

    Named type that contains a type check function and a type class that
    inherits from ObjectifiedDataElement.  The type check must take a string
    as argument and raise ValueError or TypeError if it cannot handle the
    string value.  It may be None in which case it is not considered for type
    guessing.

    Example::

        PyType('int', int, MyIntClass).register()

    Note that the order in which types are registered matters.  The first
    matching type will be used.
    """
    cdef readonly object name
    cdef readonly object type_check
    cdef object _add_text
    cdef object _type
    cdef object _schema_types
    def __init__(self, name, type_check, type_class, stringify=None):
        if not python._isString(name):
            raise TypeError("Type name must be a string")
        if type_check is not None and not callable(type_check):
            raise TypeError("Type check function must be callable (or None)")
        if name != TREE_PYTYPE_NAME and \
               not issubclass(type_class, ObjectifiedDataElement):
            raise TypeError(
                "Data classes must inherit from ObjectifiedDataElement")
        self.name  = name
        self._type = type_class
        self.type_check = type_check
        if stringify is None:
            self._add_text = _StringValueSetter(str)
        else:
            self._add_text = _StringValueSetter(stringify)
        self._schema_types = []

    def __repr__(self):
        return "PyType(%s, %s)" % (self.name, self._type.__name__)

    def register(self, before=None, after=None):
        """register(self, before=None, after=None)

        Register the type.

        The additional keyword arguments 'before' and 'after' accept a
        sequence of type names that must appear before/after the new type in
        the type list.  If any of them is not currently known, it is simply
        ignored.  Raises ValueError if the dependencies cannot be fulfilled.
        """
        if self.name == TREE_PYTYPE_NAME:
            raise ValueError("Cannot register tree type")
        if self.type_check is not None:
            for item in _TYPE_CHECKS:
                if item[0] is self.type_check:
                    _TYPE_CHECKS.remove(item)
                    break
            entry = (self.type_check, self)
            first_pos = 0
            last_pos = -1
            if before or after:
                if before is None:
                    before = ()
                elif after is None:
                    after = ()
                for i, (check, pytype) in enumerate(_TYPE_CHECKS):
                    if last_pos == -1 and pytype.name in before:
                        last_pos = i
                    if pytype.name in after:
                        first_pos = i+1
            if last_pos == -1:
                _TYPE_CHECKS.append(entry)
            elif first_pos > last_pos:
                raise ValueError("inconsistent before/after dependencies")
            else:
                _TYPE_CHECKS.insert(last_pos, entry)

        _PYTYPE_DICT[self.name] = self
        for xs_type in self._schema_types:
            _SCHEMA_TYPE_DICT[xs_type] = self

    def unregister(self):
        "unregister(self)"
        if _PYTYPE_DICT.get(self.name) is self:
            del _PYTYPE_DICT[self.name]
        for xs_type, pytype in _SCHEMA_TYPE_DICT.items():
            if pytype is self:
                del _SCHEMA_TYPE_DICT[xs_type]
        if self.type_check is None:
            return
        try:
            _TYPE_CHECKS.remove( (self.type_check, self) )
        except ValueError:
            pass

    property xmlSchemaTypes:
        """The list of XML Schema datatypes this Python type maps to.

        Note that this must be set before registering the type!
        """
        def __get__(self):
            return self._schema_types
        def __set__(self, types):
            self._schema_types = list(types)

cdef class _StringValueSetter:
    cdef object _stringify
    def __init__(self, stringify):
        self._stringify = stringify

    def __call__(self, elem, value):
        _add_text(elem, self._stringify(value))


cdef object _PYTYPE_DICT
_PYTYPE_DICT = {}

cdef object _SCHEMA_TYPE_DICT
_SCHEMA_TYPE_DICT = {}

cdef object _TYPE_CHECKS
_TYPE_CHECKS = []

cdef _lower_bool(b):
    if b:
        return "true"
    else:
        return "false"

def __lower_bool(b):
    return _lower_bool(b)

cdef _pytypename(obj):
    if python._isString(obj):
        return "str"
    else:
        return _typename(obj)

def pytypename(obj):
    """pytypename(obj)

    Find the name of the corresponding PyType for a Python object.
    """
    return _pytypename(obj)

cdef _registerPyTypes():
    pytype = PyType('int', int, IntElement)
    pytype.xmlSchemaTypes = ("int", "short", "byte", "unsignedShort",
                             "unsignedByte",)
    
    pytype.register()

    pytype = PyType('long', long, LongElement)
    pytype.xmlSchemaTypes = ("integer", "nonPositiveInteger", "negativeInteger",
                             "long", "nonNegativeInteger", "unsignedLong",
                             "unsignedInt", "positiveInteger",)
    pytype.register()

    pytype = PyType('float', float, FloatElement)
    pytype.xmlSchemaTypes = ("double", "float")
    pytype.register()

    pytype = PyType('bool', __checkBool, BoolElement, __lower_bool)
    pytype.xmlSchemaTypes = ("boolean",)
    pytype.register()

    pytype = PyType('str', None, StringElement)
    pytype.xmlSchemaTypes = ("string", "normalizedString", "token", "language",
                             "Name", "NCName", "ID", "IDREF", "ENTITY",
                             "NMTOKEN", )
    pytype.register()

    # since lxml 2.0
    pytype = PyType('NoneType', None, NoneElement)
    pytype.register()

    # backwards compatibility
    pytype = PyType('none', None, NoneElement)
    pytype.register()

# non-registered PyType for inner tree elements
cdef object TREE_PYTYPE
TREE_PYTYPE = PyType(TREE_PYTYPE_NAME, None, ObjectifiedElement)

_registerPyTypes()

def getRegisteredTypes():
    """getRegisteredTypes()

    Returns a list of the currently registered PyType objects.

    To add a new type, retrieve this list and call unregister() for all
    entries.  Then add the new type at a suitable position (possibly replacing
    an existing one) and call register() for all entries.

    This is necessary if the new type interferes with the type check functions
    of existing ones (normally only int/float/bool) and must the tried before
    other types.  To add a type that is not yet parsable by the current type
    check functions, you can simply register() it, which will append it to the
    end of the type list.
    """
    types = []
    known = set()
    add_to_known = known.add
    for check, pytype in _TYPE_CHECKS:
        name = pytype.name
        if name not in known:
            add_to_known(name)
            python.PyList_Append(types, pytype)
    for pytype in _PYTYPE_DICT.itervalues():
        name = pytype.name
        if name not in known:
            add_to_known(name)
            python.PyList_Append(types, pytype)
    return types

cdef PyType _guessPyType(value, PyType defaulttype):
    if value is None:
        return None
    for type_check, tested_pytype in _TYPE_CHECKS:
        try:
            type_check(value)
            return <PyType>tested_pytype
        except IGNORABLE_ERRORS:
            # could not be parsed as the specififed type => ignore
            pass
    return defaulttype

cdef object _guessElementClass(tree.xmlNode* c_node):
    value = textOf(c_node)
    if value is None:
        return None
    if value == '':
        return StringElement
    
    for type_check, pytype in _TYPE_CHECKS:
        try:
            type_check(value)
            return (<PyType>pytype)._type
        except IGNORABLE_ERRORS:
            pass
    return None

################################################################################
# adapted ElementMaker supports registered PyTypes

cdef class _ObjectifyElementMakerCaller # forward declaration

cdef extern from "etree_defs.h":
    # macro call to 't->tp_new()' for fast instantiation
    cdef _ObjectifyElementMakerCaller NEW_ELEMENT_MAKER "PY_NEW" (object t)

cdef class ElementMaker:
    """ElementMaker(self, namespace=None, nsmap=None, annotate=True, makeelement=None)
    """
    cdef object _makeelement
    cdef object _namespace
    cdef object _nsmap
    cdef bint _annotate
    def __init__(self, *, namespace=None, nsmap=None, annotate=True,
                 makeelement=None):
        if nsmap is None:
            nsmap = _DEFAULT_NSMAP
        self._nsmap = nsmap
        if namespace is None:
            self._namespace = None
        else:
            self._namespace = "{%s}" % namespace
        self._annotate = annotate
        if makeelement is not None:
            assert callable(makeelement)
            self._makeelement = makeelement
        else:
            self._makeelement = None

    def __getattr__(self, tag):
        cdef _ObjectifyElementMakerCaller element_maker
        if self._namespace is not None and tag[0] != "{":
            tag = self._namespace + tag
        element_maker = NEW_ELEMENT_MAKER(_ObjectifyElementMakerCaller)
        element_maker._tag = tag
        element_maker._nsmap = self._nsmap
        element_maker._annotate = self._annotate
        element_maker._element_factory = self._makeelement
        return element_maker

cdef class _ObjectifyElementMakerCaller:
    cdef object _tag
    cdef object _nsmap
    cdef object _element_factory
    cdef bint _annotate

    def __call__(self, *children, **attrib):
        "__call__(self, *children, **attrib)"
        cdef _ObjectifyElementMakerCaller elementMaker
        cdef python.PyObject* pytype
        cdef _Element element
        cdef _Element childElement
        cdef bint has_children
        cdef bint has_string_value
        if self._element_factory is None:
            element = _makeElement(self._tag, None, attrib, self._nsmap)
        else:
            element = self._element_factory(self._tag, attrib, self._nsmap)

        pytype_name = None
        has_children = 0
        has_string_value = 0
        for child in children:
            if child is None:
                if python.PyTuple_GET_SIZE(children) == 1:
                    cetree.setAttributeValue(
                        element, XML_SCHEMA_INSTANCE_NIL_ATTR, "true")
            elif python._isString(child):
                _add_text(element, child)
                has_string_value = 1
            elif isinstance(child, _Element):
                cetree.appendChild(element, <_Element>child)
                has_children = 1
            elif isinstance(child, _ObjectifyElementMakerCaller):
                elementMaker = <_ObjectifyElementMakerCaller>child
                if elementMaker._element_factory is None:
                    cetree.makeSubElement(element, elementMaker._tag,
                                          None, None, None, None)
                else:
                    childElement = elementMaker._element_factory(
                        elementMaker._tag)
                    cetree.appendChild(element, childElement)
                has_children = 1
            else:
                if pytype_name is not None:
                    # concatenation always makes the result a string
                    has_string_value = 1
                pytype_name = _typename(child)
                pytype = python.PyDict_GetItem(_PYTYPE_DICT, pytype_name)
                if pytype is not NULL:
                    (<PyType>pytype)._add_text(element, child)
                else:
                    has_string_value = 1
                    child = str(child)
                    _add_text(element, child)

        if self._annotate and not has_children:
            if has_string_value:
                cetree.setAttributeValue(element, PYTYPE_ATTRIBUTE, "str")
            elif pytype_name is not None:
                cetree.setAttributeValue(element, PYTYPE_ATTRIBUTE, pytype_name)

        return element

cdef _add_text(_Element elem, text):
    cdef tree.xmlNode* c_child
    c_child = cetree.findChildBackwards(elem._c_node, 0)
    if c_child is not NULL:
        old = cetree.tailOf(c_child)
        if old is not None:
            text = old + text
        cetree.setTailText(c_child, text)
    else:
        old = cetree.textOf(elem._c_node)
        if old is not None:
            text = old + text
        cetree.setNodeText(elem._c_node, text)

################################################################################
# Recursive element dumping

cdef bint __RECURSIVE_STR
__RECURSIVE_STR = 0 # default: off

def enableRecursiveStr(on=True):
    """enableRecursiveStr(on=True)

    Enable a recursively generated tree representation for str(element),
    based on objectify.dump(element).
    """
    global __RECURSIVE_STR
    __RECURSIVE_STR = on

def dump(_Element element not None):
    """dump(_Element element not None)

    Return a recursively generated string representation of an element.
    """
    return _dump(element, 0)

cdef object _dump(_Element element, int indent):
    indentstr = "    " * indent
    if isinstance(element, ObjectifiedDataElement):
        value = repr(element)
    else:
        value = textOf(element._c_node)
        if value is not None:
            if python.PyString_GET_SIZE( value.strip() ) == 0:
                value = None
            else:
                value = repr(value)
    result = "%s%s = %s [%s]\n" % (indentstr, element.tag,
                                   value, _typename(element))
    xsi_ns    = "{%s}" % XML_SCHEMA_INSTANCE_NS
    pytype_ns = "{%s}" % PYTYPE_NAMESPACE
    for name, value in cetree.iterattributes(element, 3):
        if '{' in name:
            if name == PYTYPE_ATTRIBUTE:
                if value == TREE_PYTYPE_NAME:
                    continue
                else:
                    name = name.replace(pytype_ns, 'py:')
            name = name.replace(xsi_ns, 'xsi:')
        result = result + "%s  * %s = %r\n" % (indentstr, name, value)

    indent = indent + 1
    for child in element.iterchildren():
        result = result + _dump(child, indent)
    if indent == 1:
        return result[:-1] # strip last '\n'
    else:
        return result


################################################################################
# Pickle support

cdef _setupPickle(reduceFunction):
    import copy_reg
    copy_reg.constructor(fromstring)
    copy_reg.pickle(ObjectifiedElement, reduceFunction, fromstring)

def pickleReduce(obj):
    "pickleReduce(obj)"
    return (fromstring, (etree.tostring(obj),))

_setupPickle(pickleReduce)
del pickleReduce

################################################################################
# Element class lookup

cdef class ObjectifyElementClassLookup(ElementClassLookup):
    """ObjectifyElementClassLookup(self, tree_class=None, empty_data_class=None)
    Element class lookup method that uses the objectify classes.
    """
    cdef object empty_data_class
    cdef object tree_class
    def __init__(self, tree_class=None, empty_data_class=None):
        """Lookup mechanism for objectify.

        The default Element classes can be replaced by passing subclasses of
        ObjectifiedElement and ObjectifiedDataElement as keyword arguments.
        'tree_class' defines inner tree classes (defaults to
        ObjectifiedElement), 'empty_data_class' defines the default class for
        empty data elements (defauls to StringElement).
        """
        self._lookup_function = _lookupElementClass
        if tree_class is None:
            tree_class = ObjectifiedElement
        self.tree_class = tree_class
        if empty_data_class is None:
            empty_data_class = StringElement
        self.empty_data_class = empty_data_class

cdef object _lookupElementClass(state, _Document doc, tree.xmlNode* c_node):
    cdef ObjectifyElementClassLookup lookup
    cdef python.PyObject* dict_result
    lookup = <ObjectifyElementClassLookup>state
    # if element has children => no data class
    if cetree.hasChild(c_node):
        return lookup.tree_class

    # if element is defined as xsi:nil, return NoneElement class
    if "true" == cetree.attributeValueFromNsName(
        c_node, _XML_SCHEMA_INSTANCE_NS, "nil"):
        return NoneElement

    # check for Python type hint
    value = cetree.attributeValueFromNsName(
        c_node, _PYTYPE_NAMESPACE, _PYTYPE_ATTRIBUTE_NAME)
    if value is not None:
        if value == TREE_PYTYPE_NAME:
            return lookup.tree_class
        dict_result = python.PyDict_GetItem(_PYTYPE_DICT, value)
        if dict_result is not NULL:
            return (<PyType>dict_result)._type
        # unknown 'pyval' => try to figure it out ourself, just go on

    # check for XML Schema type hint
    value = cetree.attributeValueFromNsName(
        c_node, _XML_SCHEMA_INSTANCE_NS, "type")

    if value is not None:
        dict_result = python.PyDict_GetItem(_SCHEMA_TYPE_DICT, value)
        if dict_result is NULL and ':' in value:
            prefix, value = value.split(':', 1)
            dict_result = python.PyDict_GetItem(_SCHEMA_TYPE_DICT, value)
        if dict_result is not NULL:
            return (<PyType>dict_result)._type

    # otherwise determine class based on text content type
    el_class = _guessElementClass(c_node)
    if el_class is not None:
        return el_class

    # if element is a root node => default to tree node
    if c_node.parent is NULL or not tree._isElement(c_node.parent):
        return lookup.tree_class

    return lookup.empty_data_class


################################################################################
# Type annotations

cdef PyType _check_type(tree.xmlNode* c_node, PyType pytype):
    if pytype is None:
        return None
    value = textOf(c_node)
    try:
        pytype.type_check(value)
        return pytype
    except IGNORABLE_ERRORS:
        # could not be parsed as the specified type => ignore
        pass
    return None

def pyannotate(element_or_tree, *, ignore_old=False, ignore_xsi=False,
             empty_pytype=None):
    """pyannotate(element_or_tree, ignore_old=False, ignore_xsi=False, empty_pytype=None)

    Recursively annotates the elements of an XML tree with 'pytype'
    attributes.

    If the 'ignore_old' keyword argument is True (the default), current 'pytype'
    attributes will be ignored and replaced.  Otherwise, they will be checked
    and only replaced if they no longer fit the current text value.

    Setting the keyword argument ``ignore_xsi`` to True makes the function
    additionally ignore existing ``xsi:type`` annotations.  The default is to
    use them as a type hint.

    The default annotation of empty elements can be set with the
    ``empty_pytype`` keyword argument.  The default is not to annotate empty
    elements.  Pass 'str', for example, to make string values the default.
    """
    cdef _Element  element
    element = cetree.rootNodeOrRaise(element_or_tree)
    _annotate(element, 0, 1, ignore_xsi, ignore_old, None, empty_pytype)

def xsiannotate(element_or_tree, *, ignore_old=False, ignore_pytype=False,
                empty_type=None):
    """xsiannotate(element_or_tree, ignore_old=False, ignore_pytype=False, empty_type=None)

    Recursively annotates the elements of an XML tree with 'xsi:type'
    attributes.

    If the 'ignore_old' keyword argument is True (the default), current
    'xsi:type' attributes will be ignored and replaced.  Otherwise, they will be
    checked and only replaced if they no longer fit the current text value.

    Note that the mapping from Python types to XSI types is usually ambiguous.
    Currently, only the first XSI type name in the corresponding PyType
    definition will be used for annotation.  Thus, you should consider naming
    the widest type first if you define additional types.

    Setting the keyword argument ``ignore_pytype`` to True makes the function
    additionally ignore existing ``pytype`` annotations.  The default is to
    use them as a type hint.

    The default annotation of empty elements can be set with the
    ``empty_type`` keyword argument.  The default is not to annotate empty
    elements.  Pass 'string', for example, to make string values the default.
    """
    cdef _Element  element
    element = cetree.rootNodeOrRaise(element_or_tree)
    _annotate(element, 1, 0, ignore_old, ignore_pytype, empty_type, None)

def annotate(element_or_tree, *, ignore_old=True, ignore_xsi=False,
             empty_pytype=None, empty_type=None, annotate_xsi=0,
             annotate_pytype=1):
    """annotate(element_or_tree, ignore_old=True, ignore_xsi=False, empty_pytype=None, empty_type=None, annotate_xsi=0, annotate_pytype=1)

    Recursively annotates the elements of an XML tree with 'xsi:type'
    and/or 'py:pytype' attributes.

    If the 'ignore_old' keyword argument is True (the default), current
    'py:pytype' attributes will be ignored for the type annotation. Set to False
    if you want reuse existing 'py:pytype' information (iff appropriate for the
    element text value).

    If the 'ignore_xsi' keyword argument is False (the default), existing
    'xsi:type' attributes will be used for the type annotation, if they fit the
    element text values. 
    
    Note that the mapping from Python types to XSI types is usually ambiguous.
    Currently, only the first XSI type name in the corresponding PyType
    definition will be used for annotation.  Thus, you should consider naming
    the widest type first if you define additional types.

    The default 'py:pytype' annotation of empty elements can be set with the
    ``empty_pytype`` keyword argument. Pass 'str', for example, to make
    string values the default.

    The default 'xsi:type' annotation of empty elements can be set with the
    ``empty_type`` keyword argument.  The default is not to annotate empty
    elements.  Pass 'string', for example, to make string values the default.

    The keyword arguments 'annotate_xsi' (default: 0) and 'annotate_pytype'
    (default: 1) control which kind(s) of annotation to use. 
    """
    cdef _Element  element
    element = cetree.rootNodeOrRaise(element_or_tree)
    _annotate(element, annotate_xsi, annotate_pytype, ignore_xsi,
              ignore_old, empty_type, empty_pytype)


cdef _annotate(_Element element, bint annotate_xsi, bint annotate_pytype,
               bint ignore_xsi, bint ignore_pytype,
               empty_type_name, empty_pytype_name):
    cdef _Document doc
    cdef tree.xmlNode* c_node
    cdef tree.xmlNs*   c_ns
    cdef python.PyObject* dict_result
    cdef PyType pytype, empty_pytype, StrType, NoneType

    if not annotate_xsi and not annotate_pytype:
        return

    doc = element._doc

    if empty_type_name is not None:
        dict_result = python.PyDict_GetItem(_SCHEMA_TYPE_DICT, empty_type_name)
    elif empty_pytype_name is not None:
        dict_result = python.PyDict_GetItem(_PYTYPE_DICT, empty_pytype_name)
    else:
        dict_result = NULL
    if dict_result is not NULL:
        empty_pytype = <PyType>dict_result
    else:
        empty_pytype = None

    StrType  = _PYTYPE_DICT.get('str')
    NoneType = _PYTYPE_DICT.get('NoneType')
    c_node = element._c_node
    tree.BEGIN_FOR_EACH_ELEMENT_FROM(c_node, c_node, 1)
    if c_node.type == tree.XML_ELEMENT_NODE:
        typename = None
        pytype = None
        value  = None
        istree = 0
        # if element is defined as xsi:nil, represent it as None
        if cetree.attributeValueFromNsName(
            c_node, _XML_SCHEMA_INSTANCE_NS, "nil") == "true":
            pytype = NoneType

        if  pytype is None and not ignore_xsi:
            # check that old xsi type value is valid
            typename = cetree.attributeValueFromNsName(
                c_node, _XML_SCHEMA_INSTANCE_NS, "type")
            if typename is not None:
                dict_result = python.PyDict_GetItem(
                    _SCHEMA_TYPE_DICT, typename)
                if dict_result is NULL and ':' in typename:
                    prefix, typename = typename.split(':', 1)
                    dict_result = python.PyDict_GetItem(
                        _SCHEMA_TYPE_DICT, typename)
                if dict_result is not NULL:
                    pytype = <PyType>dict_result
                    if pytype is not StrType:
                        # StrType does not have a typecheck but is the default
                        # anyway, so just accept it if given as type
                        # information
                        pytype = _check_type(c_node, pytype)
                        if pytype is None:
                            typename = None

        if pytype is None and not ignore_pytype:
            # check that old pytype value is valid
            old_pytypename = cetree.attributeValueFromNsName(
                c_node, _PYTYPE_NAMESPACE, _PYTYPE_ATTRIBUTE_NAME)
            if old_pytypename is not None:
                if old_pytypename == TREE_PYTYPE_NAME:
                    if not cetree.hasChild(c_node):
                        # only case where we should keep it,
                        # everything else is clear enough
                        pytype = TREE_PYTYPE
                else:
                    if old_pytypename == 'none':
                        # transition from lxml 1.x
                        old_pytypename = "NoneType"
                    dict_result = python.PyDict_GetItem(
                        _PYTYPE_DICT, old_pytypename)
                    if dict_result is not NULL:
                        pytype = <PyType>dict_result
                        if pytype is not StrType:
                            # StrType does not have a typecheck but is the
                            # default anyway, so just accept it if given as
                            # type information
                            pytype = _check_type(c_node, pytype)

        if pytype is None:
            # try to guess type
            if not cetree.hasChild(c_node):
                # element has no children => data class
                pytype = _guessPyType(textOf(c_node), StrType)
            else:
                istree = 1

        if pytype is None:
            # use default type for empty elements
            if cetree.hasText(c_node):
                pytype = StrType
            else:
                pytype = empty_pytype
                if typename is None:
                    typename = empty_type_name

        if pytype is not None:
            if typename is None:
                if not istree:
                    if python.PyList_GET_SIZE(pytype._schema_types) > 0:
                        # pytype->xsi:type is a 1:n mapping
                        # simply take the first
                        typename = pytype._schema_types[0]
            elif typename not in pytype._schema_types:
                typename = pytype._schema_types[0]

        if annotate_xsi:
            if typename is None or istree:
                cetree.delAttributeFromNsName(
                    c_node, _XML_SCHEMA_INSTANCE_NS, "type")
            else:
                # update or create attribute
                c_ns = cetree.findOrBuildNodeNsPrefix(
                    doc, c_node, _XML_SCHEMA_NS, 'xsd')
                if c_ns is not NULL:
                    if ':' in typename:
                        prefix, name = typename.split(':', 1)
                        if c_ns.prefix is NULL or c_ns.prefix[0] == c'\0':
                            typename = name
                        elif cstd.strcmp(_cstr(prefix), c_ns.prefix) != 0:
                            prefix = c_ns.prefix
                            typename = prefix + ':' + name
                    elif c_ns.prefix is not NULL or c_ns.prefix[0] != c'\0':
                        prefix = c_ns.prefix
                        typename = prefix + ':' + typename
                c_ns = cetree.findOrBuildNodeNsPrefix(
                    doc, c_node, _XML_SCHEMA_INSTANCE_NS, 'xsi')
                tree.xmlSetNsProp(c_node, c_ns, "type", _cstr(typename))

        if annotate_pytype:
            if pytype is None:
                # delete attribute if it exists
                cetree.delAttributeFromNsName(
                    c_node, _PYTYPE_NAMESPACE, _PYTYPE_ATTRIBUTE_NAME)
            else:
                # update or create attribute
                c_ns = cetree.findOrBuildNodeNsPrefix(
                    doc, c_node, _PYTYPE_NAMESPACE, 'py')
                tree.xmlSetNsProp(c_node, c_ns, _PYTYPE_ATTRIBUTE_NAME,
                                  _cstr(pytype.name))
                if pytype is NoneType:
                    c_ns = cetree.findOrBuildNodeNsPrefix(
                        doc, c_node, _XML_SCHEMA_INSTANCE_NS, 'xsi')
                    tree.xmlSetNsProp(c_node, c_ns, "nil", "true")
    tree.END_FOR_EACH_ELEMENT_FROM(c_node)

def deannotate(element_or_tree, *, pytype=True, xsi=True):
    """deannotate(element_or_tree, pytype=True, xsi=True)

    Recursively de-annotate the elements of an XML tree by removing 'pytype'
    and/or 'type' attributes.

    If the 'pytype' keyword argument is True (the default), 'pytype' attributes
    will be removed. If the 'xsi' keyword argument is True (the default),
    'xsi:type' attributes will be removed.
    """
    cdef _Element  element
    cdef tree.xmlNode* c_node

    element = cetree.rootNodeOrRaise(element_or_tree)
    c_node = element._c_node
    if pytype and xsi:
        tree.BEGIN_FOR_EACH_ELEMENT_FROM(c_node, c_node, 1)
        if c_node.type == tree.XML_ELEMENT_NODE:
            cetree.delAttributeFromNsName(
                c_node, _PYTYPE_NAMESPACE, _PYTYPE_ATTRIBUTE_NAME)
            cetree.delAttributeFromNsName(
                c_node, _XML_SCHEMA_INSTANCE_NS, "type")
        tree.END_FOR_EACH_ELEMENT_FROM(c_node)
    elif pytype:
        tree.BEGIN_FOR_EACH_ELEMENT_FROM(c_node, c_node, 1)
        if c_node.type == tree.XML_ELEMENT_NODE:
            cetree.delAttributeFromNsName(
                c_node, _PYTYPE_NAMESPACE, _PYTYPE_ATTRIBUTE_NAME)
        tree.END_FOR_EACH_ELEMENT_FROM(c_node)
    else:
        tree.BEGIN_FOR_EACH_ELEMENT_FROM(c_node, c_node, 1)
        if c_node.type == tree.XML_ELEMENT_NODE:
            cetree.delAttributeFromNsName(
                c_node, _XML_SCHEMA_INSTANCE_NS, "type")
        tree.END_FOR_EACH_ELEMENT_FROM(c_node)


################################################################################
# Module level parser setup

cdef object __DEFAULT_PARSER
__DEFAULT_PARSER = etree.XMLParser(remove_blank_text=True)
__DEFAULT_PARSER.set_element_class_lookup( ObjectifyElementClassLookup() )

cdef object objectify_parser
objectify_parser = __DEFAULT_PARSER

def setDefaultParser(new_parser = None):
    ":deprecated: use ``set_default_parser()`` instead."
    set_default_parser(new_parser)

def set_default_parser(new_parser = None):
    """set_default_parser(new_parser = None)

    Replace the default parser used by objectify's Element() and
    fromstring() functions.

    The new parser must be an etree.XMLParser.

    Call without arguments to reset to the original parser.
    """
    global objectify_parser
    if new_parser is None:
        objectify_parser = __DEFAULT_PARSER
    elif isinstance(new_parser, etree.XMLParser):
        objectify_parser = new_parser
    else:
        raise TypeError("parser must inherit from lxml.etree.XMLParser")

def makeparser(**kw):
    """makeparser(remove_blank_text=True, **kw)

    Create a new XML parser for objectify trees.

    You can pass all keyword arguments that are supported by
    ``etree.XMLParser()``.  Note that this parser defaults to removing
    blank text.  You can disable this by passing the
    ``remove_blank_text`` boolean keyword option yourself.
    """
    if 'remove_blank_text' not in kw:
        kw['remove_blank_text'] = True
    parser = etree.XMLParser(**kw)
    parser.set_element_class_lookup( ObjectifyElementClassLookup() )
    return parser

cdef _Element _makeElement(tag, text, attrib, nsmap):
    return cetree.makeElement(tag, None, objectify_parser, text, None, attrib, nsmap)

################################################################################
# Module level factory functions

cdef object _fromstring
_fromstring = etree.fromstring

def fromstring(xml, parser=None):
    """fromstring(xml, parser=None)

    Objectify specific version of the lxml.etree fromstring() function
    that uses the objectify parser.

    You can pass a different parser as second argument.
    """
    if parser is None:
        parser = objectify_parser
    return _fromstring(xml, parser)

XML = fromstring

cdef object _parse
_parse = etree.parse

def parse(f, parser=None):
    """parse(f, parser=None)

    Parse a file or file-like object with the objectify parser.

    You can pass a different parser as second argument.
    """
    if parser is None:
        parser = objectify_parser
    return _parse(f, parser)

cdef object _DEFAULT_NSMAP
_DEFAULT_NSMAP = { "py"  : PYTYPE_NAMESPACE,
                   "xsi" : XML_SCHEMA_INSTANCE_NS,
                   "xsd" : XML_SCHEMA_NS}

E = ElementMaker()

def Element(_tag, attrib=None, nsmap=None, *, _pytype=None, **_attributes):
    """Element(_tag, attrib=None, nsmap=None, _pytype=None, **_attributes)

    Objectify specific version of the lxml.etree Element() factory that
    always creates a structural (tree) element.

    NOTE: requires parser based element class lookup activated in lxml.etree!
    """
    if attrib is not None:
        if python.PyDict_Size(_attributes):
            attrib.update(_attributes)
        _attributes = attrib
    if _pytype is None:
        _pytype = TREE_PYTYPE_NAME
    if nsmap is None:
        nsmap = _DEFAULT_NSMAP
    _attributes[PYTYPE_ATTRIBUTE] = _pytype
    return _makeElement(_tag, None, _attributes, nsmap)

def DataElement(_value, attrib=None, nsmap=None, *, _pytype=None, _xsi=None,
                **_attributes):
    """DataElement(_value, attrib=None, nsmap=None, _pytype=None, _xsi=None, **_attributes)

    Create a new element from a Python value and XML attributes taken from
    keyword arguments or a dictionary passed as second argument.

    Automatically adds a 'pytype' attribute for the Python type of the value,
    if the type can be identified.  If '_pytype' or '_xsi' are among the
    keyword arguments, they will be used instead.

    If the _value argument is an ObjectifiedDataElement instance, its py:pytype,
    xsi:type and other attributes and nsmap are reused unless they are redefined
    in attrib and/or keyword arguments.
    """
    cdef python.PyObject* dict_result
    if nsmap is None:
        nsmap = _DEFAULT_NSMAP
    if attrib is not None and attrib:
        if python.PyDict_Size(_attributes):
            attrib = dict(attrib)
            attrib.update(_attributes)
        _attributes = attrib
    if isinstance(_value, ObjectifiedElement):
        if _pytype is None:
            if _xsi is None and not _attributes and nsmap is _DEFAULT_NSMAP:
                # special case: no change!
                return _value.__copy__()
    if isinstance(_value, ObjectifiedDataElement):
        # reuse existing nsmap unless redefined in nsmap parameter
        temp = _value.nsmap
        if temp is not None and temp:
            temp = dict(temp)
            temp.update(nsmap)
            nsmap = temp
        # reuse existing attributes unless redefined in attrib/_attributes
        temp = _value.attrib
        if temp is not None and temp:
            temp = dict(temp)
            temp.update(_attributes)
            _attributes = temp
        # reuse existing xsi:type or py:pytype attributes, unless provided as
        # arguments
        if _xsi is None and _pytype is None:
            dict_result = python.PyDict_GetItem(_attributes,
                                                XML_SCHEMA_INSTANCE_TYPE_ATTR)
            if dict_result is not NULL:
                _xsi = <object>dict_result
            dict_result = python.PyDict_GetItem(_attributes, PYTYPE_ATTRIBUTE)
            if dict_result is not NULL:
                _pytype = <object>dict_result

    if _xsi is not None:
        if ':' in _xsi:
            prefix, name = _xsi.split(':', 1)
            ns = nsmap.get(prefix)
            if ns != XML_SCHEMA_NS:
                raise ValueError("XSD types require the XSD namespace")
        elif nsmap is _DEFAULT_NSMAP:
            name = _xsi
            _xsi = 'xsd:' + _xsi
        else:
            name = _xsi
            for prefix, ns in nsmap.items():
                if ns == XML_SCHEMA_NS:
                    if prefix is not None and prefix:
                        _xsi = prefix + ':' + _xsi
                    break
            else:
                raise ValueError("XSD types require the XSD namespace")
        python.PyDict_SetItem(_attributes, XML_SCHEMA_INSTANCE_TYPE_ATTR, _xsi)
        if _pytype is None:
            # allow using unregistered or even wrong xsi:type names
            dict_result = python.PyDict_GetItem(_SCHEMA_TYPE_DICT, _xsi)
            if dict_result is NULL:
                dict_result = python.PyDict_GetItem(_SCHEMA_TYPE_DICT, name)
            if dict_result is not NULL:
                _pytype = (<PyType>dict_result).name

    if _value is None and _pytype != "str":
        _pytype = _pytype or "NoneType"
        strval = None
    elif python._isString(_value):
        strval = _value
    elif python.PyBool_Check(_value):
        if _value:
            strval = "true"
        else:
            strval = "false"
    else:
        strval = str(_value)

    if _pytype is None:
        _pytype = _pytypename(_value)
    
    if _pytype is not None: 
        if _pytype == "NoneType" or _pytype == "none":
            strval = None
            python.PyDict_SetItem(_attributes, XML_SCHEMA_INSTANCE_NIL_ATTR, "true")
        else:
            # check if type information from arguments is valid
            dict_result = python.PyDict_GetItem(_PYTYPE_DICT, _pytype)
            if dict_result is not NULL:
                type_check = (<PyType>dict_result).type_check
                if type_check is not None:
                    type_check(strval)

                python.PyDict_SetItem(_attributes, PYTYPE_ATTRIBUTE, _pytype)

    return _makeElement("value", strval, _attributes, nsmap)


################################################################################
# ObjectPath

include "objectpath.pxi"
