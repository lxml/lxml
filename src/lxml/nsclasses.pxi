# module-level API for namespace implementations

class NamespaceRegistryError(LxmlError):
    pass

class ElementBase(_Element):
    """All classes in namespace implementations must inherit from this
    one.  Note that subclasses *must not* override __init__ or __new__
    as there is absolutely undefined when these objects will be
    created or destroyed.  All state must be kept in the underlying
    XML."""
    pass

class XSLTElement(object):
    "NOT IMPLEMENTED YET!"
    pass

cdef object __NAMESPACE_CLASSES
__NAMESPACE_CLASSES = {}

def Namespace(ns_uri):
    if ns_uri:
        ns_utf = _utf8(ns_uri)
    else:
        ns_utf = None
    try:
        return __NAMESPACE_CLASSES[ns_utf]
    except KeyError:
        registry = __NAMESPACE_CLASSES[ns_utf] = _NamespaceRegistry(ns_uri)
        return registry

cdef class _NamespaceRegistry:
    "Dictionary-like registry for namespace implementations"
    cdef object _ns_uri
    cdef object _classes
    cdef object _extensions
    cdef object _xslt_elements
    def __init__(self, ns_uri):
        self._ns_uri = ns_uri
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
        if isinstance(item, (type, types.ClassType)) and issubclass(item, ElementBase):
            d = self._classes
        elif name is None:
            raise NamespaceRegistryError, "Registered name can only be None for elements."
        elif isinstance(item, (type, types.ClassType)) and issubclass(item, XSLTElement):
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
        try:
            return self._classes[name]
        except KeyError:
            return self._extensions[name]

    def clear(self):
        self._classes.clear()
        self._extensions.clear()

cdef object _find_all_namespaces():
    "Hack to register all extension functions in XSLT"
    ns_uris = []
    for s in __NAMESPACE_CLASSES.keys():
        ns_uris.append(unicode(s, 'UTF-8'))
    return ns_uris

cdef _NamespaceRegistry _find_namespace_registry(object ns_uri):
    if ns_uri:
        ns_utf = _utf8(ns_uri)
    else:
        ns_utf = None
    return __NAMESPACE_CLASSES[ns_utf]

cdef _find_extensions(namespaces):
    extension_dict = {}
    for ns_uri in namespaces:
        try:
            extensions = _find_namespace_registry(ns_uri)._extensions
        except KeyError:
            continue
        if extensions:
            extension_dict[ns_uri] = extensions
    return extension_dict

cdef object _find_element_class(char* c_namespace_utf,
                                char* c_element_name_utf):
    cdef _NamespaceRegistry registry
    element_name_utf = c_element_name_utf
    if c_namespace_utf == NULL:
        if element_name_utf[:1] == '{':
            namespace_utf, element_name_utf = element_name_utf[1:].split('}', 1)
        else:
            namespace_utf = None
    else:
        namespace_utf = c_namespace_utf

    try:
        registry = __NAMESPACE_CLASSES[namespace_utf]
    except KeyError:
        return _Element
    classes = registry._classes
    try:
        return classes[element_name_utf]
    except KeyError:
        pass
    try:
        return classes[None]
    except KeyError:
        return _Element


