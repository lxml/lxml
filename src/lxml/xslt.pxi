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


################################################################################
# Where do we store what?
#
# xsltStylesheet->doc->_private
#    == _XSLTResolverContext for XSL stylesheet
#
# xsltTransformContext->_private
#    == _XSLTResolverContext for transformed document
#
################################################################################


################################################################################
# XSLT document loaders

cdef class _XSLTResolverContext(_ResolverContext):
    cdef xmlDoc* _c_style_doc
    cdef _BaseParser _parser
    def __init__(self, _BaseParser parser not None):
        _ResolverContext.__init__(self, parser.resolvers)
        self._parser = parser
        self._c_style_doc = NULL

cdef xmlDoc* _xslt_resolve_stylesheet(char* c_uri, void* context):
    cdef xmlDoc* c_doc
    c_doc = (<_XSLTResolverContext>context)._c_style_doc
    if c_doc is not NULL and c_doc.URL is not NULL:
        if cstd.strcmp(c_uri, c_doc.URL) == 0:
            return _copyDoc(c_doc, 1)
    return NULL

cdef xmlDoc* _xslt_resolve_from_python(char* c_uri, void* context,
                                       int parse_options, int* error):
    # call the Python document loaders
    cdef _XSLTResolverContext resolver_context
    cdef _ResolverRegistry resolvers
    cdef _InputDocument doc_ref
    cdef xmlDoc* c_doc

    error[0] = 0
    resolver_context = <_XSLTResolverContext>context
    resolvers = resolver_context._resolvers
    try:
        uri = funicode(c_uri)
        doc_ref = resolvers.resolve(uri, None, resolver_context)

        c_doc = NULL
        if doc_ref is not None:
            if doc_ref._type == PARSER_DATA_EMPTY:
                c_doc = _newDoc()
            if doc_ref._type == PARSER_DATA_STRING:
                c_doc = _internalParseDoc(
                    _cstr(doc_ref._data_bytes), parse_options,
                    resolver_context)
            elif doc_ref._type == PARSER_DATA_FILE:
                data = doc_ref._file.read()
                c_doc = _internalParseDoc(
                    _cstr(data), parse_options,
                    resolver_context)
            elif doc_ref._type == PARSER_DATA_FILENAME:
                c_doc = _internalParseDocFromFile(
                    _cstr(doc_ref._data_bytes), parse_options,
                    resolver_context)
            if c_doc is not NULL and c_doc.URL is NULL:
                c_doc.URL = tree.xmlStrdup(c_uri)
        return c_doc
    except:
        resolver_context._store_raised()
        error[0] = 1
        return NULL

cdef void _xslt_store_resolver_exception(char* c_uri, void* context,
                                         xslt.xsltLoadType c_type):
    message = "Cannot resolve URI %s" % funicode(c_uri)
    if c_type == xslt.XSLT_LOAD_DOCUMENT:
        exception = XSLTApplyError(message)
    else:
        exception = XSLTParseError(message)
    (<_XSLTResolverContext>context)._store_exception(exception)

cdef xmlDoc* _xslt_doc_loader(char* c_uri, tree.xmlDict* c_dict,
                              int parse_options, void* c_ctxt,
                              xslt.xsltLoadType c_type):
    # no Python objects here, may be called without thread context !
    # when we declare a Python object, Pyrex will INCREF(None) !
    cdef xmlDoc* c_doc
    cdef xmlDoc* result
    cdef void* c_pcontext
    cdef int error
    cdef python.PyGILState_STATE gil_state
    # find resolver contexts of stylesheet and transformed doc
    if c_type == xslt.XSLT_LOAD_DOCUMENT:
        # transformation time
        c_pcontext = (<xslt.xsltTransformContext*>c_ctxt)._private
    elif c_type == xslt.XSLT_LOAD_STYLESHEET:
        # include/import resolution while parsing
        c_pcontext = (<xslt.xsltStylesheet*>c_ctxt).doc._private
    else:
        c_pcontext = NULL

    if c_pcontext is NULL:
        # can't call Python without context, fall back to default loader
        return XSLT_DOC_DEFAULT_LOADER(
            c_uri, c_dict, parse_options, c_ctxt, c_type)

    gil_state = python.PyGILState_Ensure()
    c_doc = _xslt_resolve_stylesheet(c_uri, c_pcontext)
    if c_doc is not NULL:
        python.PyGILState_Release(gil_state)
        return c_doc

    c_doc = _xslt_resolve_from_python(c_uri, c_pcontext, parse_options, &error)
    if c_doc is NULL and not error:
        c_doc = XSLT_DOC_DEFAULT_LOADER(
            c_uri, c_dict, parse_options, c_ctxt, c_type)
        if c_doc is NULL:
            _xslt_store_resolver_exception(c_uri, c_pcontext, c_type)

    python.PyGILState_Release(gil_state)
    return c_doc

cdef xslt.xsltDocLoaderFunc XSLT_DOC_DEFAULT_LOADER
XSLT_DOC_DEFAULT_LOADER = xslt.xsltDocDefaultLoader

xslt.xsltSetLoaderFunc(_xslt_doc_loader)

################################################################################
# XSLT file/network access control

cdef class XSLTAccessControl:
    """Access control for XSLT: reading/writing files, directories and network
    I/O.  Access to a type of resource is granted or denied by passing any of
    the following keyword arguments.  All of them default to True to allow
    access.

    * read_file
    * write_file
    * create_dir
    * read_network
    * write_network
    """
    cdef xslt.xsltSecurityPrefs* _prefs
    def __init__(self, read_file=True, write_file=True, create_dir=True,
                 read_network=True, write_network=True):
        self._prefs = xslt.xsltNewSecurityPrefs()
        if self._prefs is NULL:
            raise XSLTError, "Error preparing access control context"
        self._setAccess(xslt.XSLT_SECPREF_READ_FILE, read_file)
        self._setAccess(xslt.XSLT_SECPREF_WRITE_FILE, write_file)
        self._setAccess(xslt.XSLT_SECPREF_CREATE_DIRECTORY, create_dir)
        self._setAccess(xslt.XSLT_SECPREF_READ_NETWORK, read_network)
        self._setAccess(xslt.XSLT_SECPREF_WRITE_NETWORK, write_network)

    def __dealloc__(self):
        if self._prefs is not NULL:
            xslt.xsltFreeSecurityPrefs(self._prefs)

    cdef _setAccess(self, xslt.xsltSecurityOption option, allow):
        cdef xslt.xsltSecurityCheck function
        if allow:
            function = xslt.xsltSecurityAllow
        else:
            function = xslt.xsltSecurityForbid
        xslt.xsltSetSecurityPrefs(self._prefs, option, function)

    cdef void _register_in_context(self, xslt.xsltTransformContext* ctxt):
        xslt.xsltSetCtxtSecurityPrefs(self._prefs, ctxt)

################################################################################
# XSLT

cdef class _XSLTContext(_BaseContext):
    cdef xslt.xsltTransformContext* _xsltCtxt
    def __init__(self, namespaces, extensions):
        self._xsltCtxt = NULL
        if extensions and None in extensions:
            raise XSLTExtensionError, "extensions must not have empty namespaces"
        _BaseContext.__init__(self, namespaces, extensions)

    cdef register_context(self, xslt.xsltTransformContext* xsltCtxt,
                               _Document doc):
        self._xsltCtxt = xsltCtxt
        self._set_xpath_context(xsltCtxt.xpathCtxt)
        self._register_context(doc)
        xsltCtxt.xpathCtxt.userData = <void*>self
        self._registerExtensionFunctions()

    cdef free_context(self):
        cdef xslt.xsltTransformContext* xsltCtxt
        xsltCtxt = self._xsltCtxt
        if xsltCtxt is NULL:
            return
        self._free_context()
        self._xsltCtxt = NULL
        xslt.xsltFreeTransformContext(xsltCtxt)
        self._release_temp_refs()

    cdef void _addLocalExtensionFunction(self, ns_utf, name_utf, function):
        if self._extensions is None:
            self._extensions = {}
        python.PyDict_SetItem(self._extensions, (ns_utf, name_utf), function)

    cdef void _registerExtensionFunctions(self):
        cdef python.PyObject* dict_result
        for ns_utf, functions in _iter_extension_function_names():
            if ns_utf is None:
                continue
            dict_result = python.PyDict_GetItem(self._function_cache_ns, ns_utf)
            if dict_result is NULL:
                d = {}
                python.PyDict_SetItem(self._function_cache_ns, ns_utf, d)
            else:
                d = <object>dict_result
            for name_utf, function in functions.iteritems():
                python.PyDict_SetItem(d, name_utf, function)
                xslt.xsltRegisterExtFunction(
                    self._xsltCtxt, _cstr(name_utf), _cstr(ns_utf),
                    _xpath_function_call)
        if self._extensions is None:
            return # done
        last_ns = None
        for (ns_utf, name_utf), function in self._extensions.iteritems():
            if ns_utf is None:
                raise ValueError, \
                      "extensions must have non empty namespaces"
            elif ns_utf is not last_ns:
                last_ns = ns_utf
                dict_result = python.PyDict_GetItem(
                    self._function_cache_ns, ns_utf)
                if dict_result is NULL:
                    d = {}
                    python.PyDict_SetItem(self._function_cache_ns, ns_utf, d)
                else:
                    d = <object>dict_result
            python.PyDict_SetItem(d, name_utf, function)
            xslt.xsltRegisterExtFunction(
                self._xsltCtxt, _cstr(name_utf), _cstr(ns_utf),
                _xpath_function_call)

cdef class _ExsltRegExp # forward declaration

cdef class XSLT:
    """Turn a document into an XSLT object.
    """
    cdef _XSLTContext _context
    cdef xslt.xsltStylesheet* _c_style
    cdef _XSLTResolverContext _xslt_resolver_context
    cdef XSLTAccessControl _access_control
    cdef _ExsltRegExp _regexp
    cdef _ErrorLog _error_log

    def __init__(self, xslt_input, extensions=None, regexp=True, access_control=None):
        cdef python.PyThreadState* state
        cdef xslt.xsltStylesheet* c_style
        cdef xmlDoc* c_doc
        cdef xmlDoc* fake_c_doc
        cdef _Document doc
        cdef _NodeBase root_node

        doc = _documentOrRaise(xslt_input)
        root_node = _rootNodeOrRaise(xslt_input)

        # set access control or raise TypeError
        self._access_control = access_control

        # make a copy of the document as stylesheet parsing modifies it
        c_doc = _copyDocRoot(doc._c_doc, root_node._c_node)

        # make sure we always have a stylesheet URL
        if c_doc.URL is NULL:
            doc_url_utf = "XSLT:__STRING__XSLT__%s" % id(self)
            c_doc.URL = tree.xmlStrdup(_cstr(doc_url_utf))

        self._error_log = _ErrorLog()
        self._xslt_resolver_context = _XSLTResolverContext(doc._parser)
        # keep a copy in case we need to access the stylesheet via 'document()'
        self._xslt_resolver_context._c_style_doc = _copyDoc(c_doc, 1)
        c_doc._private = <python.PyObject*>self._xslt_resolver_context

        self._error_log.connect()
        state = python.PyEval_SaveThread()
        c_style = xslt.xsltParseStylesheetDoc(c_doc)
        python.PyEval_RestoreThread(state)
        self._error_log.disconnect()

        if c_style is NULL:
            tree.xmlFreeDoc(c_doc)
            self._xslt_resolver_context._raise_if_stored()
            if self._error_log.last_error is not None:
                raise XSLTParseError, self._error_log.last_error.message
            else:
                raise XSLTParseError, "Cannot parse style sheet"

        c_doc._private = NULL # no longer used!
        self._c_style = c_style

        self._context = _XSLTContext(None, extensions)
        if regexp:
            self._regexp = _ExsltRegExp()
            self._regexp._register_in_context(self._context)
        else:
            self._regexp  = None
        # XXX is it worthwile to use xsltPrecomputeStylesheet here?

    def __dealloc__(self):
        if self._xslt_resolver_context is not None and \
               self._xslt_resolver_context._c_style_doc is not NULL:
            tree.xmlFreeDoc(self._xslt_resolver_context._c_style_doc)
        # this cleans up the doc copy as well
        xslt.xsltFreeStylesheet(self._c_style)

    property error_log:
        def __get__(self):
            return self._error_log.copy()

    def __call__(self, _input, profile_run=False, **_kw):
        cdef python.PyThreadState* state
        cdef _XSLTContext context
        cdef _Document input_doc
        cdef _NodeBase root_node
        cdef _Document result_doc
        cdef _Document profile_doc
        cdef xmlDoc* c_profile_doc
        cdef _XSLTResolverContext resolver_context
        cdef xslt.xsltTransformContext* transform_ctxt
        cdef xmlDoc* c_result
        cdef xmlDoc* c_doc
        cdef char** params
        cdef Py_ssize_t i, kw_count

        if not _checkThreadDict(self._c_style.doc.dict):
            raise RuntimeError, "stylesheet is not usable in this thread"

        input_doc = _documentOrRaise(_input)
        root_node = _rootNodeOrRaise(_input)

        resolver_context = _XSLTResolverContext(input_doc._parser)
        resolver_context._c_style_doc = self._xslt_resolver_context._c_style_doc

        c_doc = _fakeRootDoc(input_doc._c_doc, root_node._c_node)

        transform_ctxt = xslt.xsltNewTransformContext(self._c_style, c_doc)
        if transform_ctxt is NULL:
            _destroyFakeDoc(input_doc._c_doc, c_doc)
            raise XSLTApplyError, "Error preparing stylesheet run"

        initTransformDict(transform_ctxt)

        self._error_log.connect()
        xslt.xsltSetTransformErrorFunc(transform_ctxt, <void*>self._error_log,
                                       _receiveXSLTError)

        if self._access_control is not None:
            self._access_control._register_in_context(transform_ctxt)

        if profile_run:
            transform_ctxt.profile = 1

        transform_ctxt._private = <python.PyObject*>self._xslt_resolver_context

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

        context = self._context._copy()
        context.register_context(transform_ctxt, input_doc)

        state = python.PyEval_SaveThread()
        c_result = xslt.xsltApplyStylesheetUser(self._c_style, c_doc, params,
                                                NULL, NULL, transform_ctxt)
        python.PyEval_RestoreThread(state)

        if params is not NULL:
            # deallocate space for parameters
            python.PyMem_Free(params)

        if transform_ctxt.profile:
            c_profile_doc = xslt.xsltGetProfileInformation(transform_ctxt)
            if c_profile_doc is not NULL:
                profile_doc = _documentFactory(c_profile_doc, input_doc._parser)

        context.free_context()
        _destroyFakeDoc(input_doc._c_doc, c_doc)

        self._error_log.disconnect()
        try:
            if self._xslt_resolver_context._has_raised():
                if c_result is not NULL:
                    tree.xmlFreeDoc(c_result)
                self._xslt_resolver_context._raise_if_stored()

            if c_result is NULL:
                error = self._error_log.last_error
                if error is not None and error.message:
                    if error.line >= 0:
                        message = "%s, line %d" % (error.message, error.line)
                    else:
                        message = error.message
                elif error.line >= 0:
                    message = "Error applying stylesheet, line %d" % error.line
                else:
                    message = "Error applying stylesheet"
                raise XSLTApplyError, message
        finally:
            self._xslt_resolver_context.clear()

        result_doc = _documentFactory(c_result, input_doc._parser)
        return _xsltResultTreeFactory(result_doc, self, profile_doc)

    def apply(self, _input, profile_run=False, **_kw):
        return self.__call__(_input, profile_run, **_kw)

    def tostring(self, _ElementTree result_tree):
        """Save result doc to string based on stylesheet output method.
        """
        return str(result_tree)

cdef class _XSLTResultTree(_ElementTree):
    cdef XSLT _xslt
    cdef _Document _profile
    cdef _saveToStringAndSize(self, char** s, int* l):
        cdef _Document doc
        cdef int r
        if self._context_node is not None:
            doc = self._context_node._doc
        if doc is None:
            doc = self._doc
            if doc is None:
                s[0] = NULL
                return
        r = xslt.xsltSaveResultToString(s, l, doc._c_doc, self._xslt._c_style)
        if r == -1:
            raise XSLTSaveError, "Error saving XSLT result to string"

    def __str__(self):
        cdef char* s
        cdef int l
        self._saveToStringAndSize(&s, &l)
        if s is NULL:
            return ''
        # we must not use 'funicode' here as this is not always UTF-8
        try:
            result = python.PyString_FromStringAndSize(s, l)
        finally:
            tree.xmlFree(s)
        return result

    def __unicode__(self):
        cdef char* encoding
        cdef char* s
        cdef int l
        self._saveToStringAndSize(&s, &l)
        if s is NULL:
            return unicode()
        encoding = self._xslt._c_style.encoding
        if encoding is NULL:
            encoding = 'ascii'
        try:
            result = python.PyUnicode_Decode(s, l, encoding, 'strict')
        finally:
            tree.xmlFree(s)
        return _stripEncodingDeclaration(result)

    property xslt_profile:
        """Return an ElementTree with profiling data for the stylesheet run.
        """
        def __get__(self):
            cdef _Element root
            if self._profile is None:
                return None
            root = self._profile.getroot()
            if root is None:
                return None
            return ElementTree(root)

        def __del__(self):
            self._profile = None

cdef _xsltResultTreeFactory(_Document doc, XSLT xslt, _Document profile):
    cdef _XSLTResultTree result
    result = <_XSLTResultTree>_newElementTree(doc, None, _XSLTResultTree)
    result._xslt = xslt
    result._profile = profile
    return result

# functions like "output" and "write" are a potential security risk, but we
# rely on the user to configure XSLTAccessControl as needed
xslt.xsltRegisterAllExtras()

# enable EXSLT support for XSLT
xslt.exsltRegisterAll()

# extension function lookup for XSLT
cdef xpath.xmlXPathFunction _xslt_function_check(void* ctxt,
                                                 char* c_name, char* c_ns_uri):
    "Find XSLT extension function from set of XPath and XSLT functions"
    cdef xpath.xmlXPathFunction result
    result = _function_check(ctxt, c_name, c_ns_uri)
    if result is NULL:
        return xslt.xsltExtModuleFunctionLookup(c_name, c_ns_uri)
    else:
        return result

cdef void initTransformDict(xslt.xsltTransformContext* transform_ctxt):
    __GLOBAL_PARSER_CONTEXT.initThreadDictRef(&transform_ctxt.dict)


################################################################################
# XSLT PI support

cdef object _FIND_PI_HREF
_FIND_PI_HREF = re.compile('href\s*=\s*["\']([^"\']+)["\']').findall

cdef XPath _findStylesheetByID
_findStylesheetByID = XPath(
    "//xsl:stylesheet[@xml:id = $id]",
    {"xsl":"http://www.w3.org/1999/XSL/Transform"})

cdef class _XSLTProcessingInstruction(PIBase):
    def parseXSL(self, parser=None):
        """Try to parse the stylesheet referenced by this PI and return an
        ElementTree for it.  If the stylesheet is embedded in the same
        document (referenced via xml:id), find and return an ElementTree for
        the stylesheet Element.

        The optional ``parser`` keyword argument can be passed to specify the
        parser used to read from external stylesheet URLs.
        """
        cdef _Document result_doc
        cdef _Element  result_node
        cdef char* c_href
        cdef xmlAttr* c_attr
        if self._c_node.content is NULL:
            raise ValueError, "PI lacks content"
        hrefs_utf = _FIND_PI_HREF(self._c_node.content)
        if len(hrefs_utf) != 1:
            raise ValueError, "malformed PI attributes"
        href_utf = hrefs_utf[0]
        c_href = _cstr(href_utf)

        if c_href[0] != c'#':
            # normal URL, try to parse from it
            c_href = tree.xmlBuildURI(
                c_href,
                tree.xmlNodeGetBase(self._c_node.doc, self._c_node))
            if c_href is not NULL:
                href = funicode(c_href)
                tree.xmlFree(c_href)
            else:
                href = funicode(_cstr(href_utf))
            result_doc = _parseDocument(href, parser)
            return _elementTreeFactory(result_doc, None)

        # ID reference to embedded stylesheet
        # try XML:ID lookup
        c_href = c_href+1 # skip leading '#'
        c_attr = tree.xmlGetID(self._c_node.doc, c_href)
        if c_attr is not NULL and c_attr.doc is self._c_node.doc:
            result_node = _elementFactory(self._doc, c_attr.parent)
            return _elementTreeFactory(result_node._doc, result_node)

        # try XPath search
        root = _findStylesheetByID(self._doc, id=funicode(c_href))
        if not root:
            raise ValueError, "reference to non-existing embedded stylesheet"
        elif len(root) > 1:
            raise ValueError, "ambiguous reference to embedded stylesheet"
        result_node = root[0]
        return _elementTreeFactory(result_node._doc, result_node)


################################################################################
# EXSLT regexp implementation

cdef class _ExsltRegExp:
    cdef object _compile_map
    def __init__(self):
        self._compile_map = {}

    cdef _make_string(self, value):
        if _isString(value):
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
        rexp_compiled = re.compile(rexp, py_flags)
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
        else:
            result = rexpc.search(s)
            if not result:
                return ()
            results = [ result.group() ]
            results.extend( result.groups('') )
        result_list = []
        root = Element('matches')
        join_groups = ''.join
        for s_match in results:
            if python.PyTuple_CheckExact(s_match):
                s_match = join_groups(s_match)
            elem = SubElement(root, 'match')
            elem.text = s_match
            python.PyList_Append(result_list, elem)
        return result_list

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
        context._addLocalExtensionFunction(ns, "test",    self.test)
        context._addLocalExtensionFunction(ns, "match",   self.match)
        context._addLocalExtensionFunction(ns, "replace", self.replace)
