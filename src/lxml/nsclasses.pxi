# module-level API for namespace implementations

class NamespaceRegistryError(LxmlError):
    pass

cdef class ElementBase(_Element):
    """All classes in namespace implementations must inherit from this one.
    Note that subclasses *must not* override __init__ or __new__ as it is
    absolutely undefined when these objects will be created or destroyed.  All
    persistent state of elements must be stored in the underlying XML."""
    pass

cdef class XSLTElement:
    "NOT IMPLEMENTED YET!"
    pass

cdef object __NAMESPACE_REGISTRIES
__NAMESPACE_REGISTRIES = {}

cdef object __FUNCTION_NAMESPACE_REGISTRIES
__FUNCTION_NAMESPACE_REGISTRIES = {}

def Namespace(ns_uri):
    """Retrieve the namespace object associated with the given URI. Creates a
    new one if it does not yet exist."""
    if ns_uri:
        ns_utf = _utf8(ns_uri)
    else:
        ns_utf = None
    try:
        return __NAMESPACE_REGISTRIES[ns_utf]
    except KeyError:
        registry = __NAMESPACE_REGISTRIES[ns_utf] = \
                   _NamespaceRegistry(ns_uri)
        return registry

def FunctionNamespace(ns_uri):
    """Retrieve the function namespace object associated with the given
    URI. Creates a new one if it does not yet exist. A function namespace can
    only be used to register extension functions."""
    if ns_uri:
        ns_utf = _utf8(ns_uri)
    else:
        ns_utf = None
    try:
        return __FUNCTION_NAMESPACE_REGISTRIES[ns_utf]
    except KeyError:
        registry = __FUNCTION_NAMESPACE_REGISTRIES[ns_utf] = \
                   _FunctionNamespaceRegistry(ns_uri)
        return registry


cdef class _NamespaceRegistry:
    "Dictionary-like registry for namespace implementations"
    cdef object _ns_uri
    cdef object _ns_uri_utf
    cdef object _classes
    cdef object _extensions
    cdef object _xslt_elements
    cdef char* _c_ns_uri_utf
    def __init__(self, ns_uri):
        self._ns_uri = ns_uri
        if ns_uri is None:
            self._ns_uri_utf = None
            self._c_ns_uri_utf = NULL
        else:
            self._ns_uri_utf = _utf8(ns_uri)
            self._c_ns_uri_utf = _cstr(self._ns_uri_utf)
        self._classes = {}
        self._extensions = {}
        self._xslt_elements = {}

    def update(self, class_dict_iterable):
        """Forgivingly update the registry. If registered values are
        neither subclasses of ElementBase nor callable extension
        functions, or if their name starts with '_', they will be
        silently discarded. This allows registrations at the module or
        class level using vars(), globals() etc."""
        if hasattr(class_dict_iterable, 'iteritems'):
            class_dict_iterable = class_dict_iterable.iteritems()
        elif hasattr(class_dict_iterable, 'items'):
            class_dict_iterable = class_dict_iterable.items()
        for name, item in class_dict_iterable:
            if (name is None or name[:1] != '_') and callable(item):
                self[name] = item

    def __setitem__(self, name, item):
        if python.PyType_Check(item) and issubclass(item, ElementBase):
            d = self._classes
        elif name is None:
            raise NamespaceRegistryError, "Registered name can only be None for elements."
        elif python.PyType_Check(item) and issubclass(item, XSLTElement):
            d = self._xslt_elements
        elif callable(item):
            d = self._extensions
        else:
            raise NamespaceRegistryError, "Registered item must be callable."

        if name is None:
            name_utf = None
        else:
            name_utf = _utf8(name)
        d[name_utf] = item

    def __getitem__(self, name):
        cdef python.PyObject* dict_result
        name_utf = _utf8(name)
        dict_result = python.PyDict_GetItem(self._classes, name_utf)
        if dict_result is NULL:
            dict_result = python.PyDict_GetItem(self._extensions, name_utf)
        if dict_result is NULL:
            raise KeyError, "Name not registered."
        return <object>dict_result

    def clear(self):
        self._classes.clear()
        self._extensions.clear()
        #self.self._xslt_elements.clear()

    def __repr__(self):
        return "Namespace(%r)" % self._ns_uri

cdef class _FunctionNamespaceRegistry(_NamespaceRegistry):
    cdef object _prefix
    cdef object _prefix_utf
    property prefix:
        "Namespace prefix for extension functions."
        def __del__(self):
            self._prefix = None # no prefix configured
        def __get__(self):
            return self._prefix
        def __set__(self, prefix):
            if prefix is None:
                prefix = '' # empty prefix
            self._prefix_utf = _utf8(prefix)
            self._prefix = prefix

    def __setitem__(self, name, function):
        if not callable(function):
            raise NamespaceRegistryError, "Registered function must be callable."
        if name is None:
            name_utf = None
        else:
            name_utf = _utf8(name)
        self._extensions[name_utf] = function

    def __getitem__(self, name):
        cdef python.PyObject* dict_result
        name_utf = _utf8(name)
        dict_result = python.PyDict_GetItem(self._extensions, name_utf)
        if dict_result is NULL:
            raise KeyError, "Name not registered."
        return <object>dict_result

    def __repr__(self):
        return "FunctionNamespace(%r)" % self._ns_uri

cdef object _find_all_extension_prefixes():
    "Internal lookup function to find all function prefixes for XSLT/XPath."
    cdef _FunctionNamespaceRegistry registry
    ns_prefixes = {}
    for (ns_utf, registry) in __FUNCTION_NAMESPACE_REGISTRIES.iteritems():
        if registry._prefix_utf is not None:
            ns_prefixes[registry._prefix_utf] = ns_utf
    return ns_prefixes

cdef object _find_extension(ns_uri_utf, name_utf):
    cdef python.PyObject* dict_result
    dict_result = python.PyDict_GetItem(
        __FUNCTION_NAMESPACE_REGISTRIES, ns_uri_utf)
    if dict_result is NULL:
        return None
    extensions = (<_NamespaceRegistry>dict_result)._extensions
    dict_result = python.PyDict_GetItem(extensions, name_utf)
    if dict_result is NULL:
        return None
    else:
        return <object>dict_result

cdef object _find_element_class(char* c_namespace_utf,
                                char* c_element_name_utf):
    cdef python.PyObject* dict_result
    cdef _NamespaceRegistry registry
    if c_namespace_utf is not NULL:
        dict_result = python.PyDict_GetItemString(
            __NAMESPACE_REGISTRIES, c_namespace_utf)
    else:
        dict_result = python.PyDict_GetItem(
            __NAMESPACE_REGISTRIES, None)
    if dict_result is NULL:
        return _Element

    registry = <_NamespaceRegistry>dict_result
    classes = registry._classes

    if c_element_name_utf is not NULL:
        dict_result = python.PyDict_GetItemString(
            classes, c_element_name_utf)
    else:
        dict_result = NULL

    if dict_result is NULL:
        dict_result = python.PyDict_GetItem(classes, None)

    if dict_result is not NULL:
        return <object>dict_result
    else:
        return _Element
