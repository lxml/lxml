# _elementpath.pxi - Python-facing ElementPath API on top of iterfind.pxi.
#
# Public entry points:
#   _elementpath_find(elem, path, namespaces=None, with_prefixes=True)
#   _elementpath_findall(elem, path, namespaces=None, with_prefixes=True)
#   _elementpath_iterfind(elem, path, namespaces=None, with_prefixes=True)
#   _elementpath_findtext(elem, path, default=None, namespaces=None, with_prefixes=True)
#
# Each entry point compiles a fresh _IfSearcher chain and drives it via
# the searcher's own _first / _next methods, which return matched
# xmlNode* directly (or NULL when exhausted). Chain-driving --
# descending into ``self.next._first`` on a match, cascading via
# ``self.prev._next`` on exhaustion -- happens inside the searcher,
# so callers never see the chain mechanics.
#
# Two entry-point shapes:
#
#   one-shot (find / findall):
#       head = _IfSearcher(); leaf = head.compile(path, ns)
#       match = head._first(elem._c_node)         # first leaf match (or NULL)
#       while match is not NULL:                  # findall continues
#           collect(match)
#           match = leaf._next(match)             # resume from leaf
#
#   stateful iterator (iterfind):
#       _ElementPathIterator inherits _IfSearcher, so the iterator IS
#       the head. ``_searcher`` caches the leaf returned by compile().
#       __next__ dispatches: first call -> self._first(root); subsequent
#       calls -> self._searcher._next(prev_match). On exhaustion
#       _searcher is set to None so subsequent __next__ calls keep
#       raising StopIteration (sticky-stop, per Python iterator protocol).
#
# Lifetime: every ``step.c_href`` and predicate URI/value pointer
# borrows into either the path str's UTF-8 cache or a value held by
# the namespaces dict. The iterator pins both via its own ``_path``
# and ``_namespaces`` (shallow dict copy) fields; find/findall pin
# them via the function-local parameters. ``_current_element`` on the
# iterator additionally anchors the xmlDoc lifetime AND provides
# ``_c_node`` as the leaf cursor for resume.


@cython.final
@cython.internal
cdef class _ElementPathIterator(_IfSearcher):
    """Python iterator over a path query.

    Inherits _IfSearcher so the iterator IS the head of the chain.
    Stores ``_current_element`` to anchor the xmlDoc lifetime AND to
    provide ``_c_node`` as the resume cursor for the leaf. Updated
    with each yielded match.
    """
    cdef _Element _current_element  # latest yielded match (or initial elem before first yield)
    cdef str _path                  # keeps the path str alive (step.c_tag etc. borrow into it)
    cdef dict _namespaces           # shallow copy of namespaces dict to keep it alive and unaffected
    cdef _IfSearcher _searcher      # last searcher in the chain which is the one that will return a result
    cdef bint _is_first             # True until the first __next__ call dispatches _first

    def __cinit__(self, _Element elem, str path, dict namespaces=None):
        self._current_element = elem
        self._path = path
        self._namespaces = dict(namespaces) if namespaces else None
        self._searcher = self.compile(path, self._namespaces)
        self._is_first = True

    def __iter__(self):
        return self

    def __next__(self):
        # Sticky stop: once exhausted, _searcher is None and stays None.
        if self._searcher is None:
            raise StopIteration

        cdef xmlNode* c_input = self._current_element._c_node
        cdef xmlNode* c_output

        if self._is_first:
            c_output = self._first(c_input)
            self._is_first = False
        else:
            c_output = self._searcher._next(c_input)

        if c_output is NULL:
            self._searcher = None
            raise StopIteration

        self._current_element = _elementFactory(self._current_element._doc, c_output)
        return self._current_element


cdef _ElementPathIterator _elementpath_iterfind(_Element elem, str path,
                                                 dict namespaces=None,
                                                 bint with_prefixes=True):
    """Iterate over elements of *elem* matching *path*. Returns a Python
    iterator yielding _Element instances.
    """
    return _ElementPathIterator(elem, path, namespaces if with_prefixes else None)


cdef _Element _elementpath_find(_Element elem, str path,
                                 dict namespaces=None, bint with_prefixes=True):
    """Return the first element matching *path*, or None.

    The function-local ``namespaces`` parameter pins all prefix/URI str
    objects for the call's duration -- which is also the chain's
    lifetime -- so the borrowed C pointers stored on each step stay
    valid until we return.
    """
    cdef _IfSearcher head = _IfSearcher()
    head.compile(path, namespaces if with_prefixes else None)
    cdef xmlNode* matched = head._first(elem._c_node)
    if matched is NULL:
        return None
    return _elementFactory(elem._doc, matched)


cdef list _elementpath_findall(_Element elem, str path,
                                dict namespaces=None, bint with_prefixes=True):
    """Return a list of all elements matching *path*.

    See ``_elementpath_find`` for the namespace-lifetime contract.
    """
    cdef _IfSearcher head = _IfSearcher()
    cdef _IfSearcher searcher = head.compile(path, namespaces if with_prefixes else None)
    cdef list out = []
    cdef xmlNode* matched = head._first(elem._c_node)
    while matched is not NULL:
        out.append(_elementFactory(elem._doc, matched))
        matched = searcher._next(matched)
    return out


cdef object _elementpath_findtext(_Element elem, str path, default=None,
                                   dict namespaces=None, bint with_prefixes=True):
    """Return the text of the first element matching *path*, or *default*."""
    el = _elementpath_find(elem, path, namespaces, with_prefixes=with_prefixes)
    if el is None:
        return default
    return el.text or ''
