# Custom resolver API

ctypedef enum _InputDocumentDataType:
    PARSER_DATA_EMPTY
    PARSER_DATA_STRING
    PARSER_DATA_FILENAME
    PARSER_DATA_FILE

cdef class _InputDocument:
    cdef _InputDocumentDataType _type
    cdef object _data_bytes
    cdef object _file

cdef class Resolver:
    "This is the base class of all resolvers."
    def resolve(self, system_url, public_id, context):
        return None

    def resolve_empty(self, context):
        "Return an empty input document."
        cdef _InputDocument doc_ref
        doc_ref = _InputDocument()
        doc_ref._type = PARSER_DATA_EMPTY
        return doc_ref

    def resolve_string(self, string, context):
        "Return a parsable string as input document."
        cdef _InputDocument doc_ref
        doc_ref = _InputDocument()
        doc_ref._type = PARSER_DATA_STRING
        doc_ref._data_bytes = _utf8(string)
        return doc_ref

    def resolve_filename(self, filename, context):
        "Return the name of a parsable file as input document."
        cdef _InputDocument doc_ref
        doc_ref = _InputDocument()
        doc_ref._type = PARSER_DATA_FILENAME
        doc_ref._data_bytes = _encodeFilename(filename)
        return doc_ref

    def resolve_file(self, f, context):
        "Return an open file-like object as input document."
        cdef _InputDocument doc_ref
        if not hasattr(f, 'read'):
            raise TypeError, "Argument is not a file-like object"
        doc_ref = _InputDocument()
        doc_ref._type = PARSER_DATA_FILE
        doc_ref._file = f
        return doc_ref

cdef class _ResolverRegistry:
    cdef object _resolvers
    cdef Resolver _default_resolver
    def __init__(self, Resolver default_resolver=None):
        self._resolvers = set()
        self._default_resolver = default_resolver

    def add(self, Resolver resolver not None):
        """Register a resolver.

        For each requested entity, the 'resolve' method of the resolver will
        be called and the result will be passed to the parser.  If this method
        returns None, the request will be delegated to other resolvers or the
        default resolver.  The resolvers will be tested in an arbitrary order
        until the first match is found.
        """
        self._resolvers.add(resolver)

    def remove(self, resolver):
        self._resolvers.discard(resolver)

    cdef _ResolverRegistry _copy(self):
        cdef _ResolverRegistry registry
        registry = _ResolverRegistry(self._default_resolver)
        registry._resolvers = self._resolvers.copy()
        return registry

    def copy(self):
        return self._copy()

    def resolve(self, system_url, public_id, context):
        for resolver in self._resolvers:
            result = resolver.resolve(system_url, public_id, context)
            if result is not None:
                return result
        if self._default_resolver is None:
            return None
        return self._default_resolver.resolve(system_url, public_id, context)

    def __repr__(self):
        return repr(self._resolvers)

cdef class _ResolverContext(_ExceptionContext):
    cdef _ResolverRegistry _resolvers
    cdef _TempStore _storage
    def __init__(self, _ResolverRegistry resolvers not None):
        _ExceptionContext.__init__(self)
        self._resolvers = resolvers
        self._storage = _TempStore()

    cdef void clear(self):
        _ExceptionContext.clear(self)
        self._storage.clear()
