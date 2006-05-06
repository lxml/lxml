# XSLT and XPath classes, supports for extension functions

cimport xslt

class XSLTError(LxmlError):
    pass

class XSLTParseError(XSLTError):
    pass

class XSLTApplyError(XSLTError):
    pass

class XSLTSaveError(XSLTError):
    pass

class XSLTExtensionError(XSLTError):
    pass

# version information
LIBXSLT_COMPILED_VERSION = __unpackIntVersion(xslt.LIBXSLT_VERSION)
LIBXSLT_VERSION = __unpackIntVersion(xslt.xsltLibxsltVersion)

cdef void _logLibxsltErrors():
    xslt.xsltSetGenericErrorFunc(NULL, _receiveGenericError)


################################################################################
# XSLT document loaders

cdef class _XSLTResolverContext(_ResolverContext):
    cdef xmlDoc* _c_style_doc
    cdef BaseParser _parser
    def __init__(self, BaseParser parser not None):
        _ResolverContext.__init__(self, parser.resolvers)
        self._parser = parser
        self._c_style_doc = NULL

cdef xmlDoc* _doc_loader(char* c_uri, tree.xmlDict* c_dict, int parse_options,
                         void* c_ctxt, xslt.xsltLoadType c_type):
    cdef xmlDoc* c_doc
    cdef _ResolverRegistry resolvers
    cdef _InputDocument doc_ref
    cdef _XSLTResolverContext xslt_resolver_context
    cdef _XSLTResolverContext doc_resolver_context
    cdef _XSLTResolverContext resolver_context
    cdef XMLParser parser
    # find resolver contexts of stylesheet and transformed doc
    c_doc = NULL
    doc_resolver_context = None
    if c_type == xslt.XSLT_LOAD_DOCUMENT:
        c_doc = (<xslt.xsltTransformContext*>c_ctxt).document.doc
        if c_doc is not NULL and c_doc._private is not NULL:
            if isinstance(<object>c_doc._private, _XSLTResolverContext):
                doc_resolver_context = <_XSLTResolverContext>c_doc._private
        c_doc = (<xslt.xsltTransformContext*>c_ctxt).style.doc
    elif c_type == xslt.XSLT_LOAD_STYLESHEET:
        c_doc = (<xslt.xsltStylesheet*>c_ctxt).doc

    if c_doc is NULL or c_doc._private is NULL or \
           not isinstance(<object>c_doc._private, _XSLTResolverContext):
        # can't call Python without context, fall back to default loader
        return XSLT_DOC_DEFAULT_LOADER(
            c_uri, c_dict, parse_options, c_ctxt, c_type)

    xslt_resolver_context = <_XSLTResolverContext>c_doc._private

    # quick check if we are looking for the current stylesheet
    c_doc = xslt_resolver_context._c_style_doc
    if c_doc is not NULL and c_doc.URL is not NULL:
        if cstd.strcmp(c_uri, c_doc.URL) == 0:
            return tree.xmlCopyDoc(c_doc, 1)

    # call the Python document loaders
    c_doc = NULL
    resolver_context = xslt_resolver_context # currently use only XSLT resolvers
    resolvers = resolver_context._resolvers
    try:
        uri = funicode(c_uri)
        doc_ref = resolvers.resolve(uri, None, resolver_context)

        if doc_ref is not None:
            if doc_ref._type == PARSER_DATA_EMPTY:
                c_doc = _newDoc()
            if doc_ref._type == PARSER_DATA_STRING:
                c_doc = _internalParseDoc(
                    _cstr(doc_ref._data_utf), parse_options,
                    resolver_context)
            elif doc_ref._type == PARSER_DATA_FILE:
                data = doc_ref._file.read()
                c_doc = _internalParseDoc(
                    _cstr(data), parse_options,
                    resolver_context)
            elif doc_ref._type == PARSER_DATA_FILENAME:
                c_doc = _internalParseDocFromFile(
                    _cstr(doc_ref._data_utf), parse_options,
                    resolver_context)
            if c_doc is not NULL and c_doc.URL is NULL:
                c_doc.URL = tree.xmlStrdup(c_uri)

    except Exception, e:
        xslt_resolver_context._store_raised()
        return NULL

    if c_doc is NULL:
        c_doc = XSLT_DOC_DEFAULT_LOADER(
            c_uri, c_dict, parse_options, c_ctxt, c_type)
        if c_doc is NULL:
            message = "Cannot resolve URI %s" % funicode(c_uri)
            if c_type == xslt.XSLT_LOAD_DOCUMENT:
                exception = XSLTApplyError(message)
            else:
                exception = XSLTParseError(message)
            xslt_resolver_context._store_exception(exception)
            return NULL
    if c_doc is not NULL and c_doc._private is NULL:
        c_doc._private = <python.PyObject*>xslt_resolver_context
    return c_doc

cdef xslt.xsltDocLoaderFunc XSLT_DOC_DEFAULT_LOADER
XSLT_DOC_DEFAULT_LOADER = xslt.xsltDocDefaultLoader

xslt.xsltSetLoaderFunc(_doc_loader)


################################################################################
# XSLT

cdef class _XSLTContext(_BaseContext):
    cdef xslt.xsltTransformContext* _xsltCtxt
    def __init__(self, namespaces, extensions):
        self._xsltCtxt = NULL
        self._ext_lookup_function = _xslt_function_check
        if extensions and None in extensions:
            raise XSLTExtensionError, "extensions must not have empty namespaces"
        _BaseContext.__init__(self, namespaces, extensions)

    cdef register_context(self, xslt.xsltTransformContext* xsltCtxt,
                               _Document doc):
        self._xsltCtxt = xsltCtxt
        self._set_xpath_context(xsltCtxt.xpathCtxt)
        self._register_context(doc)
        xsltCtxt.xpathCtxt.userData = <void*>self

    cdef free_context(self):
        cdef xslt.xsltTransformContext* xsltCtxt
        xsltCtxt = self._xsltCtxt
        if xsltCtxt is NULL:
            return
        self._free_context()
        self._xsltCtxt = NULL
        xslt.xsltFreeTransformContext(xsltCtxt)
        self._release_temp_refs()

    cdef _registerLocalExtensionFunction(self, ns_utf, name_utf, function):
        if self._extensions is None:
            self._extensions = {}
        python.PyDict_SetItem(self._extensions, (ns_utf, name_utf), function)

cdef class _ExsltRegExp # forward declaration

cdef class XSLT:
    """Turn a document into an XSLT object.
    """
    cdef _XSLTContext _context
    cdef xslt.xsltStylesheet* _c_style
    cdef _XSLTResolverContext _xslt_resolver_context
    cdef _ExsltRegExp _regexp
    cdef _ErrorLog _error_log

    def __init__(self, xslt_input, extensions=None, regexp=True):
        cdef xslt.xsltStylesheet* c_style
        cdef xmlDoc* c_doc
        cdef xmlDoc* fake_c_doc
        cdef _Document doc
        cdef _NodeBase root_node

        doc = _documentOrRaise(xslt_input)
        root_node = _rootNodeOf(xslt_input)

        # make a copy of the document as stylesheet parsing modifies it
        fake_c_doc = _fakeRootDoc(doc._c_doc, root_node._c_node)
        c_doc = tree.xmlCopyDoc(fake_c_doc, 1)
        _destroyFakeDoc(doc._c_doc, fake_c_doc)

        # make sure we always have a stylesheet URL
        if c_doc.URL is not NULL:
            # handle a bug in older libxml2 versions
            tree.xmlFree(c_doc.URL)
        if doc._c_doc.URL is not NULL:
            c_doc.URL = tree.xmlStrdup(doc._c_doc.URL)
        else:
            doc_url_utf = "XSLT:__STRING__XSLT__%s" % id(self)
            c_doc.URL = tree.xmlStrdup(_cstr(doc_url_utf))

        self._xslt_resolver_context = _XSLTResolverContext(doc._parser)
        # keep a copy in case we need to access the stylesheet via 'document()'
        self._xslt_resolver_context._c_style_doc = tree.xmlCopyDoc(c_doc, 1)
        c_doc._private = <python.PyObject*>self._xslt_resolver_context

        c_style = xslt.xsltParseStylesheetDoc(c_doc)
        if c_style is NULL:
            tree.xmlFreeDoc(c_doc)
            self._xslt_resolver_context._raise_if_stored()
            raise XSLTParseError, "Cannot parse style sheet"
        self._c_style = c_style

        self._context = _XSLTContext(None, extensions)
        self._error_log = _ErrorLog()
        if regexp:
            self._regexp  = _ExsltRegExp()
        else:
            self._regexp  = None
        # XXX is it worthwile to use xsltPrecomputeStylesheet here?

    def __dealloc__(self):
        if self._xslt_resolver_context is not None and \
               self._xslt_resolver_context._c_style_doc is not NULL:
            tree.xmlFreeDoc(self._xslt_resolver_context._c_style_doc)
        # this cleans up copy of doc as well
        xslt.xsltFreeStylesheet(self._c_style)

    property error_log:
        def __get__(self):
            return self._error_log.copy()

    def __call__(self, _input, **_kw):
        cdef _Document input_doc
        cdef _NodeBase root_node
        cdef _Document result_doc
        cdef _XSLTResolverContext resolver_context
        cdef xslt.xsltTransformContext* transform_ctxt
        cdef xmlDoc* c_result
        cdef xmlDoc* c_doc
        cdef char** params
        cdef void* ptemp
        cdef Py_ssize_t i, kw_count

        input_doc = _documentOrRaise(_input)
        root_node = _rootNodeOf(_input)

        resolver_context = _XSLTResolverContext(input_doc._parser)
        resolver_context._c_style_doc = self._xslt_resolver_context._c_style_doc

        c_doc = _fakeRootDoc(input_doc._c_doc, root_node._c_node)

        transform_ctxt = xslt.xsltNewTransformContext(self._c_style, c_doc)
        if transform_ctxt is NULL:
            _destroyFakeDoc(input_doc._c_doc, c_doc)
            raise XSLTApplyError, "Error preparing stylesheet run"

        self._error_log.connect()
        xslt.xsltSetTransformErrorFunc(transform_ctxt, <void*>self._error_log,
                                       _receiveGenericError)

        ptemp = c_doc._private
        c_doc._private = <python.PyObject*>resolver_context

        kw_count = python.PyDict_Size(_kw)
        if kw_count > 0:
            # allocate space for parameters
            # * 2 as we want an entry for both key and value,
            # and + 1 as array is NULL terminated
            params = <char**>python.PyMem_Malloc(
                sizeof(char*) * (kw_count * 2 + 1))
            i = 0
            keep_ref = []
            for key, value in _kw.iteritems():
                k = _utf8(key)
                python.PyList_Append(keep_ref, k)
                v = _utf8(value)
                python.PyList_Append(keep_ref, v)
                params[i] = _cstr(k)
                i = i + 1
                params[i] = _cstr(v)
                i = i + 1
            params[i] = NULL
        else:
            params = NULL

        self._context.register_context(transform_ctxt, input_doc)
        if self._regexp is not None:
            self._regexp._register_in_context(self._context)

        c_result = xslt.xsltApplyStylesheetUser(self._c_style, c_doc, params,
                                                NULL, NULL, transform_ctxt)

        if params is not NULL:
            # deallocate space for parameters
            python.PyMem_Free(params)

        self._context.free_context()
        c_doc._private = ptemp # restore _private before _destroyFakeDoc!
        _destroyFakeDoc(input_doc._c_doc, c_doc)

        self._error_log.disconnect()
        if self._xslt_resolver_context._has_raised():
            if c_result is not NULL:
                tree.xmlFreeDoc(c_result)
            self._xslt_resolver_context._raise_if_stored()

        if c_result is NULL:
            raise XSLTApplyError, "Error applying stylesheet"

        result_doc = _documentFactory(c_result, input_doc._parser)
        return _xsltResultTreeFactory(result_doc, self)

    def apply(self, _input, **_kw):
        return self.__call__(_input, **_kw)

    def tostring(self, _ElementTree result_tree):
        """Save result doc to string based on stylesheet output method.
        """
        return str(result_tree)

cdef class _XSLTResultTree(_ElementTree):
    cdef XSLT _xslt
    def __str__(self):
        cdef char* s
        cdef int l
        cdef int r
        r = xslt.xsltSaveResultToString(&s, &l, self._doc._c_doc,
                                        self._xslt._c_style)
        if r == -1:
            raise XSLTSaveError, "Error saving XSLT result to string"
        if s is NULL:
            return ''
        result = funicode(s)
        tree.xmlFree(s)
        return result

cdef _xsltResultTreeFactory(_Document doc, XSLT xslt):
    cdef _XSLTResultTree result
    result = <_XSLTResultTree>_newElementTree(doc, None, _XSLTResultTree)
    result._xslt = xslt
    return result

# do not register all libxslt extra functions, provide only "node-set"
# functions like "output" and "write" are a potential security risk
#xslt.xsltRegisterAllExtras()
xslt.xsltRegisterExtModuleFunction("node-set",
                                   xslt.XSLT_LIBXSLT_NAMESPACE,
                                   xslt.xsltFunctionNodeSet)
xslt.xsltRegisterExtModuleFunction("node-set",
                                   xslt.XSLT_SAXON_NAMESPACE,
                                   xslt.xsltFunctionNodeSet)
xslt.xsltRegisterExtModuleFunction("node-set",
                                   xslt.XSLT_XT_NAMESPACE,
                                   xslt.xsltFunctionNodeSet)

# enable EXSLT support for XSLT
xslt.exsltRegisterAll()

cdef xpath.xmlXPathFunction _xslt_function_check(void* ctxt,
                                                 char* c_name, char* c_ns_uri):
    "Find XSLT extension function from set of XPath and XSLT functions"
    cdef xpath.xmlXPathFunction result
    result = _function_check(ctxt, c_name, c_ns_uri)
    if result is NULL:
        return xslt.xsltExtModuleFunctionLookup(c_name, c_ns_uri)
    else:
        return result

################################################################################
# EXSLT regexp implementation

cdef object RE_COMPILE
RE_COMPILE = re.compile

cdef class _ExsltRegExp:
    cdef object _compile_map
    def __init__(self):
        self._compile_map = {}

    cdef _make_string(self, value):
        if python.PyString_Check(value) or python.PyUnicode_Check(value):
            return value
        else:
            raise TypeError, "Invalid argument type %s" % type(value)

    cdef _compile(self, rexp, ignore_case):
        cdef python.PyObject* c_result
        rexp = self._make_string(rexp)
        key = (rexp, ignore_case)
        c_result = python.PyDict_GetItem(self._compile_map, key)
        if c_result is not NULL:
            return <object>c_result
        py_flags = re.UNICODE
        if ignore_case:
            py_flags = py_flags | re.IGNORECASE
        rexp_compiled = RE_COMPILE(rexp, py_flags)
        python.PyDict_SetItem(self._compile_map, key, rexp_compiled)
        return rexp_compiled

    def test(self, ctxt, s, rexp, flags=''):
        flags = self._make_string(flags)
        s = self._make_string(s)
        rexpc = self._compile(rexp, 'i' in flags)
        if rexpc.search(s) is None:
            return False
        else:
            return True

    def match(self, ctxt, s, rexp, flags=''):
        flags = self._make_string(flags)
        s = self._make_string(s)
        rexpc = self._compile(rexp, 'i' in flags)
        if 'g' in flags:
            results = rexpc.findall(s)
            if not results:
                return ()
            result_list = []
            root = Element('matches')
            for s_match in results:
                elem = SubElement(root, 'match')
                elem.text = s_match
                python.PyList_Append(result_list, elem)
            return result_list
        else:
            result = rexpc.search(s)
            if result is None:
                return ()
            root = Element('match')
            root.text = result.group()
            return (root,)

    def replace(self, ctxt, s, rexp, flags, replacement):
        replacement = self._make_string(replacement)
        flags = self._make_string(flags)
        s = self._make_string(s)
        rexpc = self._compile(rexp, 'i' in flags)
        if 'g' in flags:
            count = 0
        else:
            count = 1
        return rexpc.sub(replacement, s, count)

    cdef _register_in_context(self, _XSLTContext context):
        ns = "http://exslt.org/regular-expressions"
        context._registerLocalExtensionFunction(ns, "test",    self.test)
        context._registerLocalExtensionFunction(ns, "match",   self.match)
        context._registerLocalExtensionFunction(ns, "replace", self.replace)
