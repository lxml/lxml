# Configurable Element class lookup

################################################################################
# Custom Element classes

cdef public class ElementBase(_Element) [ type LxmlElementBaseType,
                                          object LxmlElementBase ]:
    """All custom Element classes must inherit from this one.

    Note that subclasses *must not* override __init__ or __new__ as it is
    absolutely undefined when these objects will be created or destroyed.  All
    persistent state of Elements must be stored in the underlying XML.  If you
    really need to initialize the object after creation, you can implement an
    ``_init(self)`` method that will be called after object creation.
    """

cdef class CommentBase(_Comment):
    """All custom Comment classes must inherit from this one.

    Note that subclasses *must not* override __init__ or __new__ as it is
    absolutely undefined when these objects will be created or destroyed.  All
    persistent state of Comments must be stored in the underlying XML.  If you
    really need to initialize the object after creation, you can implement an
    ``_init(self)`` method that will be called after object creation.
    """

cdef class PIBase(_ProcessingInstruction):
    """All custom Processing Instruction classes must inherit from this one.

    Note that subclasses *must not* override __init__ or __new__ as it is
    absolutely undefined when these objects will be created or destroyed.  All
    persistent state of PIs must be stored in the underlying XML.  If you
    really need to initialize the object after creation, you can implement an
    ``_init(self)`` method that will be called after object creation.
    """

cdef class EntityBase(_Entity):
    """All custom Entity classes must inherit from this one.

    Note that subclasses *must not* override __init__ or __new__ as it is
    absolutely undefined when these objects will be created or destroyed.  All
    persistent state of Entities must be stored in the underlying XML.  If you
    really need to initialize the object after creation, you can implement an
    ``_init(self)`` method that will be called after object creation.
    """
    

################################################################################
# Element class lookup

ctypedef public object (*_element_class_lookup_function)(object, _Document, xmlNode*)

# class to store element class lookup functions
cdef public class ElementClassLookup [ type LxmlElementClassLookupType,
                                       object LxmlElementClassLookup ]:
    """ElementClassLookup(self)

    Superclass of Element class lookups.
    """
    cdef _element_class_lookup_function _lookup_function
    def __cinit__(self):
        self._lookup_function = NULL # use default lookup

cdef public class FallbackElementClassLookup(ElementClassLookup) \
         [ type LxmlFallbackElementClassLookupType,
           object LxmlFallbackElementClassLookup ]:
    """FallbackElementClassLookup(self, fallback=None)

    Superclass of Element class lookups with additional fallback.
    """
    cdef readonly ElementClassLookup fallback
    cdef _element_class_lookup_function _fallback_function
    def __init__(self, ElementClassLookup fallback=None):
        if fallback is not None:
            self._setFallback(fallback)
        else:
            self._fallback_function = _lookupDefaultElementClass

    cdef void _setFallback(self, ElementClassLookup lookup):
        """Sets the fallback scheme for this lookup method.
        """
        self.fallback = lookup
        self._fallback_function = lookup._lookup_function
        if self._fallback_function is NULL:
            self._fallback_function = _lookupDefaultElementClass

    def set_fallback(self, ElementClassLookup lookup not None):
        """set_fallback(self, lookup)

        Sets the fallback scheme for this lookup method.
        """
        self._setFallback(lookup)

    def setFallback(self, ElementClassLookup lookup not None):
        """Sets the fallback scheme for this lookup method.

        :deprecated: use ``set_fallback()`` instead.
        """
        self._setFallback(lookup)

    cdef object _callFallback(self, _Document doc, xmlNode* c_node):
        return self._fallback_function(self.fallback, doc, c_node)


################################################################################
# Custom Element class lookup schemes

cdef class ElementDefaultClassLookup(ElementClassLookup):
    """ElementDefaultClassLookup(self, element=None, comment=None, pi=None, entity=None)
    Element class lookup scheme that always returns the default Element
    class.

    The keyword arguments ``element``, ``comment``, ``pi`` and ``entity``
    accept the respective Element classes.
    """
    cdef readonly object element_class
    cdef readonly object comment_class
    cdef readonly object pi_class
    cdef readonly object entity_class
    def __init__(self, element=None, comment=None, pi=None, entity=None):
        self._lookup_function = _lookupDefaultElementClass
        if element is None:
            self.element_class = _Element
        elif issubclass(element, ElementBase):
            self.element_class = element
        else:
            raise TypeError("element class must be subclass of ElementBase")

        if comment is None:
            self.comment_class = _Comment
        elif issubclass(comment, CommentBase):
            self.comment_class = comment
        else:
            raise TypeError("comment class must be subclass of CommentBase")

        if entity is None:
            self.entity_class = _Entity
        elif issubclass(entity, EntityBase):
            self.entity_class = entity
        else:
            raise TypeError("Entity class must be subclass of EntityBase")

        if pi is None:
            self.pi_class = None # special case, see below
        elif issubclass(pi, PIBase):
            self.pi_class = pi
        else:
            raise TypeError("PI class must be subclass of PIBase")

cdef object _lookupDefaultElementClass(state, _Document _doc, xmlNode* c_node):
    "Trivial class lookup function that always returns the default class."
    if c_node.type == tree.XML_ELEMENT_NODE:
        if state is not None:
            return (<ElementDefaultClassLookup>state).element_class
        else:
            return _Element
    elif c_node.type == tree.XML_COMMENT_NODE:
        if state is not None:
            return (<ElementDefaultClassLookup>state).comment_class
        else:
            return _Comment
    elif c_node.type == tree.XML_ENTITY_REF_NODE:
        if state is not None:
            return (<ElementDefaultClassLookup>state).entity_class
        else:
            return _Entity
    elif c_node.type == tree.XML_PI_NODE:
        if state is not None:
            cls = (<ElementDefaultClassLookup>state).pi_class
        if cls is None:
            # special case XSLT-PI
            if c_node.name is not NULL and c_node.content is not NULL:
                if cstd.strcmp(c_node.name, "xml-stylesheet") == 0:
                    if cstd.strstr(c_node.content, "text/xsl") is not NULL or \
                           cstd.strstr(c_node.content, "text/xml") is not NULL:
                        return _XSLTProcessingInstruction
            return _ProcessingInstruction
        else:
            return cls
    else:
        assert 0, "Unknown node type: %s" % c_node.type

cdef class AttributeBasedElementClassLookup(FallbackElementClassLookup):
    """AttributeBasedElementClassLookup(self, attribute_name, class_mapping, fallback=None)
    Checks an attribute of an Element and looks up the value in a
    class dictionary.

    Arguments:
      - attribute name - '{ns}name' style string
      - class mapping  - Python dict mapping attribute values to Element classes
      - fallback       - optional fallback lookup mechanism

    A None key in the class mapping will be checked if the attribute is
    missing.
    """
    cdef object _class_mapping
    cdef object _pytag
    cdef char* _c_ns
    cdef char* _c_name
    def __init__(self, attribute_name, class_mapping,
                 ElementClassLookup fallback=None):
        self._pytag = _getNsTag(attribute_name)
        ns, name = self._pytag
        if ns is None:
            self._c_ns = NULL
        else:
            self._c_ns = _cstr(ns)
        self._c_name = _cstr(name)
        self._class_mapping = dict(class_mapping)

        FallbackElementClassLookup.__init__(self, fallback)
        self._lookup_function = _attribute_class_lookup

cdef object _attribute_class_lookup(state, _Document doc, xmlNode* c_node):
    cdef AttributeBasedElementClassLookup lookup
    cdef python.PyObject* dict_result

    lookup = <AttributeBasedElementClassLookup>state
    if c_node.type == tree.XML_ELEMENT_NODE:
        value = _attributeValueFromNsName(
            c_node, lookup._c_ns, lookup._c_name)
        dict_result = python.PyDict_GetItem(lookup._class_mapping, value)
        if dict_result is not NULL:
            return <object>dict_result
    return lookup._callFallback(doc, c_node)


cdef class ParserBasedElementClassLookup(FallbackElementClassLookup):
    """ParserBasedElementClassLookup(self, fallback=None)
    Element class lookup based on the XML parser.
    """
    def __init__(self, ElementClassLookup fallback=None):
        FallbackElementClassLookup.__init__(self, fallback)
        self._lookup_function = _parser_class_lookup

cdef object _parser_class_lookup(state, _Document doc, xmlNode* c_node):
    if doc._parser._class_lookup is not None:
        return doc._parser._class_lookup._lookup_function(
            doc._parser._class_lookup, doc, c_node)
    return (<FallbackElementClassLookup>state)._callFallback(doc, c_node)


cdef class CustomElementClassLookup(FallbackElementClassLookup):
    """CustomElementClassLookup(self, fallback=None)
    Element class lookup based on a subclass method.

    You can inherit from this class and override the method::

        lookup(self, type, doc, namespace, name)

    to lookup the element class for a node. Arguments of the method:
    * type:      one of 'element', 'comment', 'PI', 'entity'
    * doc:       document that the node is in
    * namespace: namespace URI of the node (or None for comments/PIs/entities)
    * name:      name of the element/entity, None for comments, target for PIs

    If you return None from this method, the fallback will be called.
    """
    def __init__(self, ElementClassLookup fallback=None):
        FallbackElementClassLookup.__init__(self, fallback)
        self._lookup_function = _custom_class_lookup

    def lookup(self, type, doc, namespace, name):
        "lookup(self, type, doc, namespace, name)"
        return None

cdef object _custom_class_lookup(state, _Document doc, xmlNode* c_node):
    cdef CustomElementClassLookup lookup
    cdef char* c_str

    lookup = <CustomElementClassLookup>state

    if c_node.type == tree.XML_ELEMENT_NODE:
        element_type = "element"
    elif c_node.type == tree.XML_COMMENT_NODE:
        element_type = "comment"
    elif c_node.type == tree.XML_PI_NODE:
        element_type = "PI"
    elif c_node.type == tree.XML_ENTITY_REF_NODE:
        element_type = "entity"
    else:
        element_type = "element"
    if c_node.name is NULL:
        name = None
    else:
        name = c_node.name
    c_str = tree._getNs(c_node)
    if c_str is NULL:
        ns = None
    else:
        ns = c_str

    cls = lookup.lookup(element_type, doc, ns, name)
    if cls is not None:
        return cls
    return lookup._callFallback(doc, c_node)


################################################################################
# Global setup

cdef _element_class_lookup_function LOOKUP_ELEMENT_CLASS
cdef object ELEMENT_CLASS_LOOKUP_STATE

cdef void _setElementClassLookupFunction(
    _element_class_lookup_function function, object state):
    global LOOKUP_ELEMENT_CLASS, ELEMENT_CLASS_LOOKUP_STATE
    if function is NULL:
        state    = DEFAULT_ELEMENT_CLASS_LOOKUP
        function = DEFAULT_ELEMENT_CLASS_LOOKUP._lookup_function

    ELEMENT_CLASS_LOOKUP_STATE = state
    LOOKUP_ELEMENT_CLASS = function

def setElementClassLookup(ElementClassLookup lookup = None):
    ":deprecated: use ``set_element_class_lookup(lookup)`` instead"
    set_element_class_lookup(lookup)

def set_element_class_lookup(ElementClassLookup lookup = None):
    """set_element_class_lookup(lookup = None)

    Set the global default element class lookup method.
    """
    if lookup is None or lookup._lookup_function is NULL:
        _setElementClassLookupFunction(NULL, None)
    else:
        _setElementClassLookupFunction(lookup._lookup_function, lookup)

# default setup: parser delegation
cdef ParserBasedElementClassLookup DEFAULT_ELEMENT_CLASS_LOOKUP
DEFAULT_ELEMENT_CLASS_LOOKUP = ParserBasedElementClassLookup()

set_element_class_lookup(DEFAULT_ELEMENT_CLASS_LOOKUP)
