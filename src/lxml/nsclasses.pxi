# module-level API for namespace implementations

class LxmlRegistryError(LxmlError):
    u"""Base class of lxml registry errors.
    """
    pass

class NamespaceRegistryError(LxmlRegistryError):
    u"""Error registering a namespace extension.
    """
    pass


cdef class _NamespaceRegistry:
    u"Dictionary-like namespace registry"
    cdef object _ns_uri
    cdef object _ns_uri_utf
    cdef dict _entries
    cdef char* _c_ns_uri_utf
    def __cinit__(self, ns_uri):
        self._ns_uri = ns_uri
        if ns_uri is None:
            self._ns_uri_utf = None
            self._c_ns_uri_utf = NULL
        else:
            self._ns_uri_utf = _utf8(ns_uri)
            self._c_ns_uri_utf = _cstr(self._ns_uri_utf)
        self._entries = {}

    def update(self, class_dict_iterable):
        u"""update(self, class_dict_iterable)

        Forgivingly update the registry.

        If registered values do not match the required type for this
        registry, or if their name starts with '_', they will be
        silently discarded. This allows registrations at the module or
        class level using vars(), globals() etc."""
        if hasattr(class_dict_iterable, u'items'):
            class_dict_iterable = class_dict_iterable.items()
        for name, item in class_dict_iterable:
            if (name is None or name[:1] != u'_') and callable(item):
                self[name] = item

    def __getitem__(self, name):
        if name is not None:
            name = _utf8(name)
        return self._get(name)

    def __delitem__(self, name):
        if name is not None:
            name = _utf8(name)
        del self._entries[name]

    cdef object _get(self, object name):
        cdef python.PyObject* dict_result
        dict_result = python.PyDict_GetItem(self._entries, name)
        if dict_result is NULL:
            raise KeyError, u"Name not registered."
        return <object>dict_result

    cdef object _getForString(self, char* name):
        cdef python.PyObject* dict_result
        dict_result = python.PyDict_GetItem(self._entries, name)
        if dict_result is NULL:
            raise KeyError, u"Name not registered."
        return <object>dict_result

    def __iter__(self):
        return iter(self._entries)

    def items(self):
        return list(self._entries.items())

    def iteritems(self):
        return iter(self._entries.items())

    def clear(self):
        python.PyDict_Clear(self._entries)

cdef class _ClassNamespaceRegistry(_NamespaceRegistry):
    u"Dictionary-like registry for namespace implementation classes"
    def __setitem__(self, name, item):
        if not python.PyType_Check(item) or not issubclass(item, ElementBase):
            raise NamespaceRegistryError, \
                u"Registered element classes must be subtypes of ElementBase"
        if name is not None:
            name = _utf8(name)
        self._entries[name] = item

    def __repr__(self):
        return u"Namespace(%r)" % self._ns_uri


cdef class ElementNamespaceClassLookup(FallbackElementClassLookup):
    u"""ElementNamespaceClassLookup(self, fallback=None)

    Element class lookup scheme that searches the Element class in the
    Namespace registry.
    """
    cdef dict _namespace_registries
    def __cinit__(self):
        self._namespace_registries = {}

    def __init__(self, ElementClassLookup fallback=None):
        FallbackElementClassLookup.__init__(self, fallback)
        self._lookup_function = _find_nselement_class

    def get_namespace(self, ns_uri):
        u"""get_namespace(self, ns_uri)

        Retrieve the namespace object associated with the given URI.

        Creates a new one if it does not yet exist."""
        if ns_uri:
            ns_utf = _utf8(ns_uri)
        else:
            ns_utf = None
        try:
            return self._namespace_registries[ns_utf]
        except KeyError:
            registry = self._namespace_registries[ns_utf] = \
                       _ClassNamespaceRegistry(ns_uri)
            return registry

cdef object _find_nselement_class(state, _Document doc, xmlNode* c_node):
    cdef python.PyObject* dict_result
    cdef ElementNamespaceClassLookup lookup
    cdef _NamespaceRegistry registry
    cdef char* c_namespace_utf
    if state is None:
        return _lookupDefaultElementClass(None, doc, c_node)

    lookup = <ElementNamespaceClassLookup>state
    if c_node.type != tree.XML_ELEMENT_NODE:
        return _callLookupFallback(lookup, doc, c_node)

    c_namespace_utf = _getNs(c_node)
    if c_namespace_utf is not NULL:
        dict_result = python.PyDict_GetItem(
            lookup._namespace_registries, c_namespace_utf)
    else:
        dict_result = python.PyDict_GetItem(
            lookup._namespace_registries, None)
    if dict_result is not NULL:
        registry = <_NamespaceRegistry>dict_result
        classes = registry._entries

        if c_node.name is not NULL:
            dict_result = python.PyDict_GetItem(
                classes, c_node.name)
        else:
            dict_result = NULL

        if dict_result is NULL:
            dict_result = python.PyDict_GetItem(classes, None)

        if dict_result is not NULL:
            return <object>dict_result
    return _callLookupFallback(lookup, doc, c_node)


################################################################################
# XPath extension functions

cdef dict __FUNCTION_NAMESPACE_REGISTRIES
__FUNCTION_NAMESPACE_REGISTRIES = {}

def FunctionNamespace(ns_uri):
    u"""FunctionNamespace(ns_uri)

    Retrieve the function namespace object associated with the given
    URI.

    Creates a new one if it does not yet exist. A function namespace
    can only be used to register extension functions."""
    if ns_uri:
        ns_utf = _utf8(ns_uri)
    else:
        ns_utf = None
    try:
        return __FUNCTION_NAMESPACE_REGISTRIES[ns_utf]
    except KeyError:
        registry = __FUNCTION_NAMESPACE_REGISTRIES[ns_utf] = \
                   _XPathFunctionNamespaceRegistry(ns_uri)
        return registry

cdef class _FunctionNamespaceRegistry(_NamespaceRegistry):
    def __setitem__(self, name, item):
        if not callable(item):
            raise NamespaceRegistryError, \
                u"Registered functions must be callable."
        if not name:
            raise ValueError, \
                u"extensions must have non empty names"
        self._entries[_utf8(name)] = item

    def __repr__(self):
        return u"FunctionNamespace(%r)" % self._ns_uri

cdef class _XPathFunctionNamespaceRegistry(_FunctionNamespaceRegistry):
    cdef object _prefix
    cdef object _prefix_utf

    property prefix:
        u"Namespace prefix for extension functions."
        def __del__(self):
            self._prefix = None # no prefix configured
            self._prefix_utf = None
        def __get__(self):
            if self._prefix is None:
                return ''
            else:
                return self._prefix
        def __set__(self, prefix):
            if prefix == '':
                prefix = None # empty prefix
            if prefix is None:
                self._prefix_utf = None
            else:
                self._prefix_utf = _utf8(prefix)
            self._prefix = prefix

cdef list _find_all_extension_prefixes():
    u"Internal lookup function to find all function prefixes for XSLT/XPath."
    cdef _XPathFunctionNamespaceRegistry registry
    cdef list ns_prefixes = []
    for registry in __FUNCTION_NAMESPACE_REGISTRIES.itervalues():
        if registry._prefix_utf is not None:
            if registry._ns_uri_utf is not None:
                ns_prefixes.append(
                    (registry._prefix_utf, registry._ns_uri_utf))
    return ns_prefixes

cdef object _find_extension(ns_uri_utf, name_utf):
    cdef python.PyObject* dict_result
    dict_result = python.PyDict_GetItem(
        __FUNCTION_NAMESPACE_REGISTRIES, ns_uri_utf)
    if dict_result is NULL:
        return None
    extensions = (<_NamespaceRegistry>dict_result)._entries
    dict_result = python.PyDict_GetItem(extensions, name_utf)
    if dict_result is NULL:
        return None
    else:
        return <object>dict_result
