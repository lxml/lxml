from etreepublic cimport _Document, _Element, ElementBase
from etreepublic cimport _ElementIterator, ElementClassLookup
from etreepublic cimport elementFactory, import_etree, textOf
from python cimport str, repr, isinstance, issubclass, callable, getattr
from python cimport _cstr, Py_ssize_t
cimport etreepublic as cetree
cimport python
cimport tree
cimport cstd

cdef object etree
from lxml import etree
# initialize C-API of lxml.etree
import_etree(etree)

cdef object SubElement
SubElement = etree.SubElement

cdef object re
import re
cdef object __builtin__
import __builtin__
cdef object int
int = __builtin__.int
cdef object long
long = __builtin__.long
cdef object float
float = __builtin__.float
cdef object bool
bool = __builtin__.bool
cdef object pow
pow = __builtin__.pow
cdef object abs
abs = __builtin__.abs
cdef object len
len = __builtin__.len

cdef object True
True = __builtin__.True
cdef object False
False = __builtin__.False

cdef object AttributeError
AttributeError = __builtin__.AttributeError
cdef object TypeError
TypeError = __builtin__.TypeError
cdef object ValueError
ValueError = __builtin__.ValueError
cdef object IndexError
IndexError = __builtin__.IndexError
cdef object StopIteration
StopIteration = __builtin__.StopIteration

cdef object IGNORABLE_ERRORS
IGNORABLE_ERRORS = (ValueError, TypeError)

cdef object list
list = __builtin__.list
cdef object set
try:
    set = __builtin__.set
except AttributeError:
    from sets import Set as set

cdef object islice
from itertools import islice


# namespace/name for "pytype" hint attribute
cdef object PYTYPE_NAMESPACE
cdef char* _PYTYPE_NAMESPACE

cdef object PYTYPE_ATTRIBUTE_NAME
cdef char* _PYTYPE_ATTRIBUTE_NAME

PYTYPE_ATTRIBUTE = None

cdef object TREE_PYTYPE
TREE_PYTYPE = "TREE"

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


# namespace for XML Schema instance
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
        cdef tree.xmlNode* c_self_node
        cdef tree.xmlNode* c_node
        cdef char* c_href
        cdef char* c_tag
        cdef Py_ssize_t count
        c_self_node = self._c_node
        c_tag  = c_self_node.name
        c_href = tree._getNs(c_self_node)
        count = 1
        c_node = c_self_node.next
        while c_node is not NULL:
            if c_node.type == tree.XML_ELEMENT_NODE and \
                   cetree.tagMatches(c_node, c_href, c_tag):
                count = count + 1
            c_node = c_node.next
        c_node = c_self_node.prev
        while c_node is not NULL:
            if c_node.type == tree.XML_ELEMENT_NODE and \
                   cetree.tagMatches(c_node, c_href, c_tag):
                count = count + 1
            c_node = c_node.prev
        return count

    def countchildren(self):
        """Return the number of children of this element, regardless of their
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
            raise TypeError, "attribute '%s' of '%s' objects is not writable"% \
                  (tag, type(self).__name__)
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
        """Add a child value to the element.

        As opposed to append(), it sets a data value, not an element.
        """
        _appendValue(self, _buildChildTag(self, tag), value)

    def __getitem__(self, key):
        """Return a sibling, counting from the first child of the parent.

        * If argument is an integer, returns the sibling at that position.

        * If argument is a string, does the same as getattr().  This is used
          to provide namespaces for element lookup.
        """
        cdef tree.xmlNode* c_self_node
        cdef tree.xmlNode* c_parent
        cdef tree.xmlNode* c_node
        if python._isString(key):
            return _lookupChildOrRaise(self, key)
        c_self_node = self._c_node
        c_parent = c_self_node.parent
        if c_parent is NULL:
            if key == 0:
                return self
            else:
                raise IndexError, key
        if key < 0:
            c_node = c_parent.last
        else:
            c_node = c_parent.children
        c_node = _findFollowingSibling(
            c_node, tree._getNs(c_self_node), c_self_node.name, key)
        if c_node is NULL:
            raise IndexError, key
        return elementFactory(self._doc, c_node)

    def __setitem__(self, key, value):
        """Set the value of a sibling, counting from the first child of the
        parent.

        * If argument is an integer, sets the sibling at that position.

        * If argument is a string, does the same as setattr().  This is used
          to provide namespaces for element lookup.

        * If argument is a sequence (list, tuple, etc.), assign the contained
          items to the siblings.
        """
        cdef _Element element
        cdef _Element new_element
        cdef tree.xmlNode* c_self_node
        cdef tree.xmlNode* c_parent
        cdef tree.xmlNode* c_node
        if python._isString(key):
            key = _buildChildTag(self, key)
            element = _lookupChild(self, key)
            if element is None:
                _appendValue(self, key, value)
            else:
                _replaceElement(element, value)
            return

        c_self_node = self._c_node
        c_parent = c_self_node.parent
        if c_parent is NULL:
            # the 'root[i] = ...' case
            raise TypeError, "index assignment to root element is invalid"
        if key < 0:
            c_node = c_parent.last
        else:
            c_node = c_parent.children
        c_node = _findFollowingSibling(
            c_node, tree._getNs(c_self_node), c_self_node.name, key)
        if c_node is NULL:
            raise IndexError, key
        element = elementFactory(self._doc, c_node)
        _replaceElement(element, value)

    def __getslice__(self, Py_ssize_t start, Py_ssize_t end):
        return list(islice(self, start, end))

    def __setslice__(self, Py_ssize_t start, Py_ssize_t end, values):
        cdef _Element el
        parent = self.getparent()
        if parent is None:
            raise TypeError, "deleting slices of root element not supported"
        # replace existing items
        new_items = iter(values)
        del_items = iter(list(islice(self, start, end)))
        try:
            for el in del_items:
                item = new_items.next()
                _replaceElement(el, item)
        except StopIteration:
            remove = parent.remove
            remove(el)
            for el in del_items:
                remove(el)
            return

        # append remaining new items
        tag = self.tag
        for item in new_items:
            _appendValue(parent, tag, item)

    def __delslice__(self, Py_ssize_t start, Py_ssize_t end):
        parent = self.getparent()
        if parent is None:
            raise TypeError, "deleting slices of root element not supported"
        remove = parent.remove
        for el in list(islice(self, start, end)):
            remove(el)

    def __delitem__(self, key):
        parent = self.getparent()
        if parent is None:
            raise TypeError, "deleting items not supported by root element"
        sibling = self.__getitem__(key)
        parent.remove(sibling)

    def findall(self, path):
        # Reimplementation of Element.findall() to make it work without child
        # iteration.
        xpath = etree.ETXPath(path)
        return xpath(self)

    def find(self, path):
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
        # Reimplementation of Element.findtext() to make it work without child
        # iteration.
        result = self.find(path)
        if isinstance(result, _Element):
            return result.text or ""
        else:
            return default

    def descendantpaths(self, prefix=None):
        """Returns a list of object path expressions for all descendants.
        """
        if prefix is not None and not python._isString(prefix):
            prefix = '.'.join(prefix)
        return _buildDescendantPaths(self._c_node, prefix)

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
        raise AttributeError, "no such child: " + \
              _buildChildTag(parent, tag)
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
        element.__setslice__(0, python.PY_SSIZE_T_MAX, value)
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
        new_element = SubElement(parent, tag)
        _setElementValue(new_element, value)

cdef _setElementValue(_Element element, value):
    if value is None:
        cetree.setAttributeValue(
            element, XML_SCHEMA_INSTANCE_NIL_ATTR, "true")
    elif isinstance(value, _Element):
        _replaceElement(element, value)
    else:
        cetree.delAttributeFromNsName(
            element._c_node, _XML_SCHEMA_INSTANCE_NS, "nil")
        if not python._isString(value):
            if isinstance(value, bool):
                value = str(value).lower()
            else:
                value = str(value)
    cetree.setNodeText(element._c_node, value)

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
            raise TypeError, "invalid types for * operator"

    def __mod__(self, other):
        if python.PyTuple_Check(other):
            l = []
            for item in other:
                python.PyList_Append(l, _strValueOf(item))
            other = tuple(l)
        else:
            other = _strValueOf(other)
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
        text = textOf(self._c_node)
        if text is None:
            return 0
        text = text.lower()
        if text == 'false':
            return 0
        elif text == 'true':
            return 1
        else:
            raise ValueError, "Invalid boolean value: '%s'" % text
        
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
    if s != 'true' and s != 'false':
        raise ValueError

cdef object _strValueOf(obj):
    if python._isString(obj):
        return obj
    if isinstance(obj, _Element):
        return textOf((<_Element>obj)._c_node)
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
    """User defined type.

    Named type that contains a type check function and a type class that
    inherits from ObjectifiedDataElement.  The type check must take a string
    as argument and raise ValueError or TypeError if it cannot handle the
    string value.  It may be None in which case it is not considered for type
    guessing.

    Example:
        PyType('int', int, MyIntClass).register()

    Note that the order in which types are registered matters.  The first
    matching type will be used.
    """
    cdef readonly object name
    cdef readonly object type_check
    cdef object _type
    cdef object _schema_types
    def __init__(self, name, type_check, type_class):
        if not python._isString(name):
            raise TypeError, "Type name must be a string"
        elif name == TREE_PYTYPE:
            raise ValueError, "Invalid type name"
        if type_check is not None and not callable(type_check):
            raise TypeError, "Type check function must be callable (or None)"
        if not issubclass(type_class, ObjectifiedDataElement):
            raise TypeError, \
                  "Data classes must inherit from ObjectifiedDataElement"
        self.name  = name
        self._type = type_class
        self.type_check = type_check
        self._schema_types = []

    def __repr__(self):
        return "PyType(%s, %s)" % (self.name, self._type.__name__)

    def register(self, before=None, after=None):
        """Register the type.

        The additional keyword arguments 'before' and 'after' accept a
        sequence of type names that must appear before/after the new type in
        the type list.  If any of them is not currently known, it is simply
        ignored.  Raises ValueError if the dependencies cannot be fulfilled.
        """
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
                raise ValueError, "inconsistent before/after dependencies"
            else:
                _TYPE_CHECKS.insert(last_pos, entry)

        _PYTYPE_DICT[self.name] = self
        for xs_type in self._schema_types:
            _SCHEMA_TYPE_DICT[xs_type] = self

    def unregister(self):
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

cdef object _PYTYPE_DICT
_PYTYPE_DICT = {}

cdef object _SCHEMA_TYPE_DICT
_SCHEMA_TYPE_DICT = {}

cdef object _TYPE_CHECKS
_TYPE_CHECKS = []

cdef _registerPyTypes():
    pytype = PyType('int', int, IntElement)
    pytype.xmlSchemaTypes = ("integer", "positiveInteger", "negativeInteger",
                             "nonNegativeInteger", "nonPositiveInteger",
                             "int", "unsignedInt", "short", "unsignedShort")
    pytype.register()

    pytype = PyType('long', long, LongElement)
    pytype.xmlSchemaTypes = ("long", "unsignedLong")
    pytype.register()

    pytype = PyType('float', float, FloatElement)
    pytype.xmlSchemaTypes = ("float", "double")
    pytype.register()

    pytype = PyType('bool', __checkBool, BoolElement)
    pytype.xmlSchemaTypes = ("boolean",)
    pytype.register()

    pytype = PyType('str', None, StringElement)
    pytype.xmlSchemaTypes = ("string", "normalizedString")
    pytype.register()

    pytype = PyType('none', None, NoneElement)
    pytype.register()

_registerPyTypes()

def getRegisteredTypes():
    """Returns a list of the currently registered PyType objects.

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
# Recursive element dumping

cdef int __RECURSIVE_STR
__RECURSIVE_STR = 0 # default: off

def enableRecursiveStr(on=True):
    """Enable a recursively generated tree representation for str(element),
    based on objectify.dump(element).
    """
    global __RECURSIVE_STR
    __RECURSIVE_STR = bool(on)

def dump(_Element element not None):
    """Return a recursively generated string representation of an element.
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
                                   value, type(element).__name__)
    xsi_ns    = "{%s}" % XML_SCHEMA_INSTANCE_NS
    pytype_ns = "{%s}" % PYTYPE_NAMESPACE
    for name, value in cetree.iterattributes(element, 3):
        if name == PYTYPE_ATTRIBUTE:
            if value == TREE_PYTYPE:
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

cdef void _setupPickle(reduceFunction):
    import copy_reg
    copy_reg.constructor(fromstring)
    copy_reg.pickle(ObjectifiedElement, reduceFunction, fromstring)

def pickleReduce(obj):
    return (fromstring, (etree.tostring(obj),))

_setupPickle(pickleReduce)
del pickleReduce

################################################################################
# Element class lookup

cdef class ObjectifyElementClassLookup(ElementClassLookup):
    """Element class lookup method that uses the objectify classes.
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
    if cetree.findChildForwards(c_node, 0) is not NULL:
        return lookup.tree_class

    # if element is defined as xsi:nil, return NoneElement class
    if "true" == cetree.attributeValueFromNsName(
        c_node, _XML_SCHEMA_INSTANCE_NS, "nil"):
        return NoneElement

    # check for Python type hint
    value = cetree.attributeValueFromNsName(
        c_node, _PYTYPE_NAMESPACE, _PYTYPE_ATTRIBUTE_NAME)
    if value is not None:
        if value == TREE_PYTYPE:
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
# ObjectPath

ctypedef struct _ObjectPath:
    char* href
    char* name
    Py_ssize_t index

cdef class ObjectPath:
    """Immutable object that represents a compiled object path.

    Example for a path: 'root.child[1].{other}child[25]'
    """
    cdef readonly object find
    cdef object _path
    cdef object _path_str
    cdef _ObjectPath*  _c_path
    cdef Py_ssize_t _path_len
    def __init__(self, path):
        if python._isString(path):
            self._path = _parseObjectPathString(path)
            self._path_str = path
        else:
            self._path = _parseObjectPathList(path)
            self._path_str = '.'.join(path)
        self._path_len = python.PyList_GET_SIZE(self._path)
        self._c_path = _buildObjectPathSegments(self._path)
        self.find = self.__call__

    def __dealloc__(self):
        if self._c_path is not NULL:
            python.PyMem_Free(self._c_path)

    def __str__(self):
        return self._path_str

    def __call__(self, _Element root not None, *default):
        """Follow the attribute path in the object structure and return the
        target attribute value.

        If it it not found, either returns a default value (if one was passed
        as second argument) or raises AttributeError.
        """
        cdef Py_ssize_t use_default
        use_default = python.PyTuple_GET_SIZE(default)
        if use_default == 1:
            default = python.PyTuple_GET_ITEM(default, 0)
            python.Py_INCREF(default)
            use_default = 1
        elif use_default > 1:
            raise TypeError, "invalid number of arguments: needs one or two"
        return _findObjectPath(root, self._c_path, self._path_len,
                               default, use_default)

    def hasattr(self, _Element root not None):
        try:
            _findObjectPath(root, self._c_path, self._path_len, None, 0)
        except AttributeError:
            return False
        return True

    def setattr(self, _Element root not None, value):
        """Set the value of the target element in a subtree.

        If any of the children on the path does not exist, it is created.
        """
        _createObjectPath(root, self._c_path, self._path_len, 1, value)

    def addattr(self, _Element root not None, value):
        """Append a value to the target element in a subtree.

        If any of the children on the path does not exist, it is created.
        """
        _createObjectPath(root, self._c_path, self._path_len, 0, value)

cdef object __MATCH_PATH_SEGMENT
__MATCH_PATH_SEGMENT = re.compile(
    r"(\.?)\s*(?:\{([^}]*)\})?\s*([^.{}\[\]\s]+)\s*(?:\[\s*([-0-9]+)\s*\])?",
    re.U).match

cdef _parseObjectPathString(path):
    """Parse object path string into a 'hrefOnameOhrefOnameOOO' string and an
    index list.  The index list is None if no index was used in the path.
    """
    cdef int has_dot
    new_path = []
    path = cetree.utf8(path.strip())
    path_pos = 0
    while python.PyString_GET_SIZE(path) > 0:
        match = __MATCH_PATH_SEGMENT(path, path_pos)
        if match is None:
            break

        dot, ns, name, index = match.groups()
        if index is None or python.PyString_GET_SIZE(index) == 0:
            index = 0
        else:
            index = python.PyNumber_Int(index)
        has_dot = _cstr(dot)[0] == c'.'
        if python.PyList_GET_SIZE(new_path) == 0:
            if has_dot:
                # path '.child' => ignore root
                python.PyList_Append(new_path, (None, None, 0))
            elif index != 0:
                raise ValueError, "index not allowed on root node"
        elif not has_dot:
            raise ValueError, "invalid path"
        python.PyList_Append(new_path, (ns, name, index))
        
        path_pos = match.end()
    if python.PyList_GET_SIZE(new_path) == 0 or \
           python.PyString_GET_SIZE(path) > path_pos:
        raise ValueError, "invalid path"
    return new_path

cdef _parseObjectPathList(path):
    """Parse object path sequence into a 'hrefOnameOhrefOnameOOO' string and
    an index list.  The index list is None if no index was used in the path.
    """
    cdef char* index_pos
    cdef char* index_end
    cdef char* c_name
    new_path = []
    for item in path:
        item = item.strip()
        if python.PyList_GET_SIZE(new_path) == 0 and item == '':
            # path '.child' => ignore root
            ns = name = None
            index = 0
        else:
            ns, name = cetree.getNsTag(item)
            c_name = _cstr(name)
            index_pos = cstd.strchr(c_name, c'[')
            if index_pos is NULL:
                index = 0
            else:
                name = python.PyString_FromStringAndSize(
                    c_name, <Py_ssize_t>(index_pos - c_name))
                index_pos = index_pos + 1
                index_end = cstd.strchr(index_pos, c']')
                if index_end is NULL:
                    raise ValueError, "index must be enclosed in []"
                index = python.PyNumber_Int(
                    python.PyString_FromStringAndSize(
                    index_pos, <Py_ssize_t>(index_end - index_pos)))
                if python.PyList_GET_SIZE(new_path) == 0 and index != 0:
                    raise ValueError, "index not allowed on root node"
        python.PyList_Append(new_path, (ns, name, index))
    if python.PyList_GET_SIZE(new_path) == 0 or \
           (python.PyList_GET_SIZE(new_path) == 1 and \
            new_path[0] == (None, None, 0)):
        raise ValueError, "invalid path"
    return new_path

cdef _ObjectPath* _buildObjectPathSegments(path_list) except NULL:
    cdef _ObjectPath* c_path
    cdef _ObjectPath* c_path_segments
    cdef Py_ssize_t c_len
    c_len = python.PyList_GET_SIZE(path_list)
    c_path_segments = <_ObjectPath*>python.PyMem_Malloc(sizeof(_ObjectPath) *
                                                        c_len)
    if c_path_segments is NULL:
        PyErr_NoMemory()
        return NULL
    c_path = c_path_segments
    for href, name, index in path_list:
        if href is None:
            c_path[0].href = NULL
        else:
            c_path[0].href = _cstr(href)
        if name is None:
            c_path[0].name = NULL
        else:
            c_path[0].name = _cstr(name)
        c_path[0].index = index
        c_path = c_path + 1
    return c_path_segments

cdef _findObjectPath(_Element root, _ObjectPath* c_path, Py_ssize_t c_path_len,
                     default_value, int use_default):
    """Follow the path to find the target element.
    """
    cdef tree.xmlNode* c_node
    cdef char* c_href
    cdef char* c_name
    cdef Py_ssize_t c_index
    c_node = root._c_node
    c_name = c_path[0].name
    c_href = c_path[0].href
    if c_href is NULL or c_href[0] == c'\0':
        c_href = tree._getNs(c_node)
    if not cetree.tagMatches(c_node, c_href, c_name):
        raise ValueError, "root element does not match: need %s, got %s" % \
              (cetree.namespacedNameFromNsName(c_href, c_name), root.tag)

    while c_node is not NULL:
        c_path_len = c_path_len - 1
        if c_path_len <= 0:
            return cetree.elementFactory(root._doc, c_node)

        c_path = c_path + 1
        if c_path[0].href is not NULL:
            c_href = c_path[0].href # otherwise: keep parent namespace
        c_name = c_path[0].name
        c_index = c_path[0].index

        if c_index < 0:
            c_node = c_node.last
        else:
            c_node = c_node.children
        c_node = _findFollowingSibling(c_node, c_href, c_name, c_index)

    if use_default:
        return default_value
    else:
        tag = cetree.namespacedNameFromNsName(c_href, c_name)
        raise AttributeError, "no such child: " + tag

cdef _createObjectPath(_Element root, _ObjectPath* c_path,
                       Py_ssize_t c_path_len, int replace, value):
    """Follow the path to find the target element, build the missing children
    as needed and set the target element to 'value'.  If replace is true, an
    existing value is replaced, otherwise the new value is added.
    """
    cdef _Element child
    cdef tree.xmlNode* c_node
    cdef tree.xmlNode* c_child
    cdef char* c_href
    cdef char* c_name
    cdef Py_ssize_t c_index
    if c_path_len == 1:
        raise TypeError, "cannot update root node"

    c_node = root._c_node
    c_name = c_path[0].name
    c_href = c_path[0].href
    if c_href is NULL or c_href[0] == c'\0':
        c_href = tree._getNs(c_node)
    if not cetree.tagMatches(c_node, c_href, c_name):
        raise ValueError, "root element does not match: need %s, got %s" % \
              (cetree.namespacedNameFromNsName(c_href, c_name), root.tag)

    while c_path_len > 1:
        c_path_len = c_path_len - 1
        c_path = c_path + 1
        if c_path[0].href is not NULL:
            c_href = c_path[0].href # otherwise: keep parent namespace
        c_name = c_path[0].name
        c_index = c_path[0].index

        if c_index < 0:
            c_child = c_node.last
        else:
            c_child = c_node.children
        c_child = _findFollowingSibling(c_child, c_href, c_name, c_index)

        if c_child is not NULL:
            c_node = c_child
        elif c_index != 0:
            raise TypeError, \
                  "creating indexed path attributes is not supported"
        elif c_path_len == 1:
            _appendValue(cetree.elementFactory(root._doc, c_node),
                         cetree.namespacedNameFromNsName(c_href, c_name),
                         value)
            return
        else:
            child = SubElement(
                cetree.elementFactory(root._doc, c_node),
                cetree.namespacedNameFromNsName(c_href, c_name))
            c_node = child._c_node

    # if we get here, the entire path was already there
    if replace:
        element = cetree.elementFactory(root._doc, c_node)
        _replaceElement(element, value)
    else:
        _appendValue(cetree.elementFactory(root._doc, c_node.parent),
                     cetree.namespacedName(c_node), value)

cdef _buildDescendantPaths(tree.xmlNode* c_node, prefix_string):
    """Returns a list of all descendant paths.
    """
    tag = cetree.namespacedName(c_node)
    if prefix_string:
        if prefix_string[-1] != '.':
            prefix_string = prefix_string + '.'
        prefix_string = prefix_string + tag
    else:
        prefix_string = tag
    path = [prefix_string]
    path_list = []
    _recursiveBuildDescendantPaths(c_node, path, path_list)
    return path_list

cdef _recursiveBuildDescendantPaths(tree.xmlNode* c_node, path, path_list):
    """Fills the list 'path_list' with all descendant paths, initial prefix
    being in the list 'path'.
    """
    cdef python.PyObject* dict_result
    cdef tree.xmlNode* c_child
    cdef char* c_href
    python.PyList_Append(path_list, '.'.join(path))
    tags = {}
    c_href = tree._getNs(c_node)
    c_child = c_node.children
    while c_child is not NULL:
        while c_child.type != tree.XML_ELEMENT_NODE:
            c_child = c_child.next
            if c_child is NULL:
                return
        if c_href is tree._getNs(c_child):
            tag = c_child.name
        elif c_href is not NULL and tree._getNs(c_child) is NULL:
            # special case: parent has namespace, child does not
            tag = '{}' + c_child.name
        else:
            tag = cetree.namespacedName(c_child)
        dict_result = python.PyDict_GetItem(tags, tag)
        if dict_result is NULL:
            count = 0
        else:
            count = (<object>dict_result) + 1
        python.PyDict_SetItem(tags, tag, count)
        if count > 0:
            tag = tag + '[%d]' % count
        python.PyList_Append(path, tag)
        _recursiveBuildDescendantPaths(c_child, path, path_list)
        del path[-1]
        c_child = c_child.next


################################################################################
# Type annotations

def annotate(element_or_tree, ignore_old=True):
    """Recursively annotates the elements of an XML tree with 'pytype'
    attributes.

    If the 'ignore_old' keyword argument is True (the default), current
    attributes will be ignored and replaced.  Otherwise, they will be checked
    and only replaced if they no longer fit the current text value.
    """
    cdef _Element  element
    cdef _Document doc
    cdef int ignore
    cdef tree.xmlNode* c_node
    cdef tree.xmlNs*   c_ns
    cdef python.PyObject* dict_result
    element = cetree.rootNodeOrRaise(element_or_tree)
    doc = element._doc
    ignore = bool(ignore_old)

    StrType = _PYTYPE_DICT.get('str')
    c_node = element._c_node
    tree.BEGIN_FOR_EACH_ELEMENT_FROM(c_node, c_node, 1)
    pytype = None
    value  = None
    if not ignore:
        # check that old value is valid
        old_value = cetree.attributeValueFromNsName(
            c_node, _PYTYPE_NAMESPACE, _PYTYPE_ATTRIBUTE_NAME)
        if old_value is not None and old_value != TREE_PYTYPE:
            pytype = _PYTYPE_DICT.get(old_value)
            if pytype is not None:
                value = textOf(c_node)
                try:
                    if not (<PyType>pytype).type_check(value):
                        pytype = None
                except ValueError:
                    pytype = None

    if pytype is None:
        # if element is defined as xsi:nil, return NoneElement class
        if cetree.attributeValueFromNsName(
            c_node, _XML_SCHEMA_INSTANCE_NS, "nil") == "true":
            pytype = _PYTYPE_DICT.get("none")

    if pytype is None:
        # check for XML Schema type hint
        value = cetree.attributeValueFromNsName(
            c_node, _XML_SCHEMA_INSTANCE_NS, "type")

        if value is not None:
            dict_result = python.PyDict_GetItem(_SCHEMA_TYPE_DICT, value)
            if dict_result is not NULL:
                pytype = <PyType>dict_result

    if pytype is None:
        # try to guess type
        if cetree.findChildForwards(c_node, 0) is NULL:
            # element has no children => data class
            if value is None:
                value = textOf(c_node)
            if value is not None:
                for type_check, tested_pytype in _TYPE_CHECKS:
                    try:
                        if type_check(value) is not False:
                            pytype = tested_pytype
                            break
                    except ValueError:
                        pass
                else:
                    pytype = StrType

    if pytype is None:
        # delete attribute if it exists
        cetree.delAttributeFromNsName(
            c_node, _PYTYPE_NAMESPACE, _PYTYPE_ATTRIBUTE_NAME)
    else:
        # update or create attribute
        c_ns = cetree.findOrBuildNodeNs(doc, c_node, _PYTYPE_NAMESPACE)
        tree.xmlSetNsProp(c_node, c_ns, _PYTYPE_ATTRIBUTE_NAME,
                          _cstr(pytype.name))
    tree.END_FOR_EACH_ELEMENT_FROM(c_node)

################################################################################
# Module level parser setup

cdef object __DEFAULT_PARSER
__DEFAULT_PARSER = etree.XMLParser(remove_blank_text=True)
__DEFAULT_PARSER.setElementClassLookup( ObjectifyElementClassLookup() )

cdef object parser
parser = __DEFAULT_PARSER

def setDefaultParser(new_parser = None):
    """Replace the default parser used by objectify's Element() and
    fromstring() functions.

    The new parser must be an etree.XMLParser.

    Call without arguments to reset to the original parser.
    """
    global parser
    if new_parser is None:
        parser = __DEFAULT_PARSER
    elif isinstance(new_parser, etree.XMLParser):
        parser = new_parser
    else:
        raise TypeError, "parser must inherit from lxml.etree.XMLParser"

cdef _Element _makeElement(tag, text, attrib, nsmap):
    return cetree.makeElement(tag, None, parser, text, None, attrib, nsmap)

################################################################################
# Module level factory functions

cdef object _fromstring
_fromstring = etree.fromstring

def fromstring(xml):
    """Objectify specific version of the lxml.etree fromstring() function.

    NOTE: requires parser based element class lookup activated in lxml.etree!
    """
    return _fromstring(xml, parser)

XML = fromstring

def Element(_tag, attrib=None, nsmap=None, _pytype=None, **_attributes):
    """Objectify specific version of the lxml.etree Element() factory that
    always creates a structural (tree) element.

    NOTE: requires parser based element class lookup activated in lxml.etree!
    """
    if attrib is not None:
        if python.PyDict_Size(_attributes):
            attrib.update(_attributes)
        _attributes = attrib
    if _pytype is None:
        _pytype = TREE_PYTYPE
    _attributes[PYTYPE_ATTRIBUTE] = _pytype
    return _makeElement(_tag, None, _attributes, nsmap)

def DataElement(_value, attrib=None, nsmap=None, _pytype=None, _xsi=None,
                **_attributes):
    """Create a new element with a Python value and XML attributes taken from
    keyword arguments or a dictionary passed as second argument.

    Automatically adds a 'pyval' attribute for the Python type of the value,
    if the type can be identified.  If '_pyval' or '_xsi' are among the
    keyword arguments, they will be used instead.
    """
    cdef _Element element
    if attrib is not None:
        if python.PyDict_Size(_attributes):
            attrib.update(_attributes)
        _attributes = attrib
    if _xsi is not None:
        python.PyDict_SetItem(_attributes, XML_SCHEMA_INSTANCE_TYPE_ATTR, _xsi)
        if _pytype is None:
            _pytype = _SCHEMA_TYPE_DICT[_xsi].name

    if python._isString(_value):
        strval = _value
    elif python.PyBool_Check(_value):
        if _value:
            strval = "true"
        else:
            strval = "false"
    else:
        strval = str(_value)

    if _pytype is None:
        for type_check, pytype in _TYPE_CHECKS:
            try:
                type_check(strval)
                _pytype = (<PyType>pytype).name
                break
            except IGNORABLE_ERRORS:
                pass
        if _pytype is None:
            if _value is None:
                _pytype = "none"
            elif python._isString(_value):
                _pytype = "str"
    if _pytype is not None:
        python.PyDict_SetItem(_attributes, PYTYPE_ATTRIBUTE, _pytype)

    return _makeElement("value", strval, _attributes, nsmap)
