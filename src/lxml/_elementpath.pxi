# _elementpath.pxi - Python-facing ElementPath API on top of iterfind.pxi.
#
# Replaces the pure-Python lxml._elementpath module. Public functions:
#   _elementpath_find(elem, path, namespaces=None, with_prefixes=True)
#   _elementpath_findall(elem, path, namespaces=None, with_prefixes=True)
#   _elementpath_iterfind(elem, path, namespaces=None, with_prefixes=True)
#   _elementpath_findtext(elem, path, default=None, namespaces=None, with_prefixes=True)
#
# This module performs no path tokenization or prefix substitution itself:
# the C-level compiler in iterfind.pxi handles ``{uri}name``, ``prefix:name``
# resolution and default-namespace application directly while building its
# step structs. Likewise the path-syntax rules (reject leading '/', treat
# trailing '/' as implicit '/*') live in the C compiler.
#
# Each entry point declares ``elem`` as ``_Element``, so Cython generates a
# C-level type check on argument unpacking -- equivalent to the old
# ``isinstance`` guard, just less code and one fewer Python attribute access.


cdef class _ElementPathIterator(_IterFindResult):
    """Python iterator over iterfind results.

    Inherits the C-level result holder from iterfind.pxi -- the compiled
    step array and the xmlNode* result list live in the inherited fields,
    so we avoid an extra heap allocation and one level of indirection on
    every ``__next__`` call. The base class stays purely C-level; this
    subclass adds the Python iterator protocol and a _Document anchor that
    keeps the underlying tree alive while iteration is in progress.
    """
    cdef _Document _doc

    def __iter__(self):
        return self

    def __next__(self):
        cdef xmlNode* c_node = self._next_node()
        if c_node is NULL:
            raise StopIteration
        return _elementFactory(self._doc, c_node)


cdef _ElementPathIterator _elementpath_iterfind(_Element elem, path,
                                                 namespaces=None,
                                                 with_prefixes=True):
    """Iterate over elements of *elem* matching *path*.

    Returns a Python iterator yielding _Element instances.
    """
    cdef bytes path_bytes = (<str>path).encode('utf-8')
    cdef const char* c_path = <const char*>path_bytes
    cdef _ElementPathIterator it = _ElementPathIterator.__new__(_ElementPathIterator)
    it._doc = elem._doc
    _iterfind_compile_into(it, elem._c_node, c_path,
                           namespaces if with_prefixes else None)
    return it


cdef object _elementpath_find(_Element elem, path,
                               namespaces=None, with_prefixes=True):
    """Return the first element matching *path*, or None."""
    cdef bytes path_bytes = (<str>path).encode('utf-8')
    cdef const char* c_path = <const char*>path_bytes
    cdef _IterFindResult res = _iterfind_run(
        elem._c_node, c_path,
        namespaces if with_prefixes else None)
    cdef xmlNode* c_result = res._next_node()
    if c_result is NULL:
        return None
    return _elementFactory(elem._doc, c_result)


cdef list _elementpath_findall(_Element elem, path,
                                namespaces=None, with_prefixes=True):
    """Return a list of all elements matching *path*."""
    cdef bytes path_bytes = (<str>path).encode('utf-8')
    cdef const char* c_path = <const char*>path_bytes
    cdef _IterFindResult res = _iterfind_run(
        elem._c_node, c_path,
        namespaces if with_prefixes else None)
    cdef xmlNode* c_result
    cdef list out = []
    while True:
        c_result = res._next_node()
        if c_result is NULL:
            break
        out.append(_elementFactory(elem._doc, c_result))
    return out


cdef object _elementpath_findtext(_Element elem, path, default=None,
                                   namespaces=None, with_prefixes=True):
    """Return the text of the first element matching *path*, or *default*."""
    el = _elementpath_find(elem, path, namespaces, with_prefixes=with_prefixes)
    if el is None:
        return default
    return el.text or ''
