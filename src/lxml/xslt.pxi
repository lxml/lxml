# XSLT and XPath classes, supports for extension functions

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

class XPathError(LxmlError):
    pass

class XPathContextError(XPathError):
    pass

class XPathFunctionError(XPathError):
    pass

class XPathResultError(XPathError):
    pass

class XPathSyntaxError(LxmlSyntaxError):
    pass

################################################################################
# support for extension functions in XPath/XSLT

cdef class _BaseContext:
    cdef xpath.xmlXPathContext* _xpathCtxt
    cdef xpath.xmlXPathFuncLookupFunc _ext_lookup_function
    cdef _Document _doc
    cdef object _extensions
    cdef object _namespaces
    cdef object _registered_namespaces
    cdef object _utf_refs
    cdef object _function_cache
    cdef object _called_function
    # for exception handling and temporary reference keeping:
    cdef _TempStore _temp_refs
    cdef _ExceptionContext _exc

    def __init__(self, namespaces, extensions):
        self._xpathCtxt = NULL
        self._utf_refs = {}
        self._function_cache = {}
        self._called_function = None

        # convert old format extensions to UTF-8
        if isinstance(extensions, (list, tuple)):
            new_extensions = {}
            for extension in extensions:
                for (ns_uri, name), function in extension.items():
                    ns_utf   = self._to_utf(ns_uri)
                    name_utf = self._to_utf(name)
                    try:
                        new_extensions[ns_utf][name_utf] = function
                    except KeyError:
                        new_extensions[ns_utf] = {name_utf : function}
            extensions = new_extensions or None

        self._doc        = None
        self._exc        = _ExceptionContext()
        self._extensions = extensions
        self._namespaces = namespaces
        self._registered_namespaces = []
        self._temp_refs = _TempStore()

    cdef object _to_utf(self, s):
        "Convert to UTF-8 and keep a reference to the encoded string"
        cdef python.PyObject* dict_result
        if s is None:
            return None
        dict_result = python.PyDict_GetItem(self._utf_refs, s)
        if dict_result is not NULL:
            return <object>dict_result
        utf = _utf8(s)
        python.PyDict_SetItem(self._utf_refs, s, utf)
        return utf

    cdef void _set_xpath_context(self, xpath.xmlXPathContext* xpathCtxt):
        self._xpathCtxt = xpathCtxt
        xpathCtxt.userData = <void*>self

    cdef _register_context(self, _Document doc, int allow_none_namespace):
        self._doc = doc
        self._exc.clear()
        python.PyDict_Clear(self._function_cache)
        namespaces = self._namespaces
        if namespaces is not None:
            self.registerNamespaces(namespaces)
        xpath.xmlXPathRegisterFuncLookup(
            self._xpathCtxt, self._ext_lookup_function, <python.PyObject*>self)

    cdef _unregister_context(self):
        self._unregisterNamespaces()
        self._free_context()

    cdef _free_context(self):
        del self._registered_namespaces[:]
        python.PyDict_Clear(self._utf_refs)
        self._doc = None
        if self._xpathCtxt is not NULL:
            self._xpathCtxt.userData = NULL
            self._xpathCtxt = NULL

    # namespaces (internal UTF-8 methods with leading '_')

    def addNamespace(self, prefix, uri):
        if self._namespaces is None:
            self._namespaces = {}
        python.PyDict_SetItem(self._namespaces, prefix, uri)

    def registerNamespaces(self, namespaces):
        for prefix, uri in namespaces.items():
            self.registerNamespace(prefix, uri)
    
    def registerNamespace(self, prefix, ns_uri):
        prefix_utf = self._to_utf(prefix)
        ns_uri_utf = self._to_utf(ns_uri)
        xpath.xmlXPathRegisterNs(self._xpathCtxt, prefix_utf, ns_uri_utf)
        python.PyList_Append(self._registered_namespaces, prefix_utf)

    cdef _unregisterNamespaces(self):
        cdef xpath.xmlXPathContext* xpathCtxt
        xpathCtxt = self._xpathCtxt
        for prefix_utf in self._registered_namespaces:
            xpath.xmlXPathRegisterNs(xpathCtxt, prefix_utf, NULL)
    
    # extension functions

    cdef int _prepare_function_call(self, ns_uri_utf, name_utf):
        cdef python.PyObject* dict_result
        key = (ns_uri_utf, name_utf)
        dict_result = python.PyDict_GetItem(self._function_cache, key)
        if dict_result is not NULL:
            function = <object>dict_result
            self._called_function = function
            return function is not None

        dict_result = python.PyDict_GetItem(self._extensions, ns_uri_utf)
        if dict_result is not NULL:
            dict_result = python.PyDict_GetItem(<object>dict_result, name_utf)
        if dict_result is not NULL:
            function = <object>dict_result
        else:
            function = _find_extension(ns_uri_utf, name_utf)

        python.PyDict_SetItem(self._function_cache, key, function)
        self._called_function = function
        return function is not None

    # Python reference keeping during XPath function evaluation

    cdef _release_temp_refs(self):
        "Free temporarily referenced objects from this context."
        self._temp_refs.clear()
        
    cdef _hold(self, obj):
        """A way to temporarily hold references to nodes in the evaluator.

        This is needed because otherwise nodes created in XPath extension
        functions would be reference counted too soon, during the XPath
        evaluation.  This is most important in the case of exceptions.
        """
        cdef _NodeBase element
        if isinstance(obj, _NodeBase):
            obj = (obj,)
        elif not python.PySequence_Check(obj):
            return
        for o in obj:
            if isinstance(o, _NodeBase):
                element = <_NodeBase>o
                #print "Holding element:", <int>element._c_node
                self._temp_refs.add(element)
                #print "Holding document:", <int>element._doc._c_doc
                self._temp_refs.add(element._doc)

cdef xpath.xmlXPathFunction _function_check(void* ctxt,
                                            char* c_name, char* c_ns_uri):
    cdef _BaseContext context
    if c_name is NULL:
        return NULL
    if c_ns_uri is NULL:
        ns_uri = None
    else:
        ns_uri = c_ns_uri
    context = <_BaseContext>ctxt
    if context._prepare_function_call(ns_uri, c_name):
        return _call_prepared_function
    else:
        return NULL

cdef xpath.xmlXPathFunction _xslt_function_check(void* ctxt,
                                                 char* c_name, char* c_ns_uri):
    cdef xpath.xmlXPathFunction result
    result = _function_check(ctxt, c_name, c_ns_uri)
    if result is NULL:
        return xslt.xsltExtModuleFunctionLookup(c_name, c_ns_uri)
    else:
        return result


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
        if tree.strcmp(c_uri, c_doc.URL) == 0:
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
        self._register_context(doc, 0)
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
        extensions = self._extensions
        if extensions is None:
            self._extensions = {ns_utf:{name_utf:function}}
        else:
            if ns_utf in extensions:
                ns_extensions = extensions[ns_utf]
            else:
                ns_extensions = extensions[ns_utf] = {}
            python.PyDict_SetItem(ns_extensions, name_utf, function)

cdef class _ExsltRegExp # forward declaration

cdef class XSLT:
    """Turn a document into an XSLT object.
    """
    cdef _XSLTContext _context
    cdef xslt.xsltStylesheet* _c_style
    cdef _XSLTResolverContext _xslt_resolver_context
    cdef _ExsltRegExp _regexp

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
        cdef int i

        input_doc = _documentOrRaise(_input)
        root_node = _rootNodeOf(_input)

        resolver_context = _XSLTResolverContext(input_doc._parser)
        resolver_context._c_style_doc = self._xslt_resolver_context._c_style_doc

        c_doc = _fakeRootDoc(input_doc._c_doc, root_node._c_node)

        transform_ctxt = xslt.xsltNewTransformContext(self._c_style, c_doc)
        if transform_ctxt is NULL:
            _destroyFakeDoc(input_doc._c_doc, c_doc)
            raise XSLTApplyError, "Error preparing stylesheet run"

        ptemp = c_doc._private
        c_doc._private = <python.PyObject*>resolver_context

        if _kw:
            # allocate space for parameters
            # * 2 as we want an entry for both key and value,
            # and + 1 as array is NULL terminated
            params = <char**>cstd.malloc(sizeof(char*) * (len(_kw) * 2 + 1))
            i = 0
            keep_ref = []
            for key, value in _kw.items():
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
            cstd.free(params)

        self._context.free_context()
        c_doc._private = ptemp # restore _private before _destroyFakeDoc!
        _destroyFakeDoc(input_doc._c_doc, c_doc)

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

# do not register all libxslt extra function, provide only "node-set"
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

################################################################################
# XPath

cdef class _XPathContext(_BaseContext):
    cdef object _variables
    cdef object _registered_variables
    def __init__(self, namespaces, extensions, variables):
        self._ext_lookup_function = _function_check
        self._variables = variables
        self._registered_variables  = []
        _BaseContext.__init__(self, namespaces, extensions)
        
    cdef register_context(self, xpath.xmlXPathContext* xpathCtxt, _Document doc):
        self._set_xpath_context(xpathCtxt)
        ns_prefixes = _find_all_extension_prefixes()
        if ns_prefixes:
            self.registerNamespaces(ns_prefixes)
        self._register_context(doc, 1)
        if self._variables is not None:
            self.registerVariables(self._variables)

    cdef unregister_context(self):
        cdef xpath.xmlXPathContext* xpathCtxt
        xpathCtxt = self._xpathCtxt
        if xpathCtxt is NULL:
            return
        self._unregisterVariables()
        del self._registered_variables[:]
        self._unregister_context()

    cdef void _unregisterVariables(self):
        cdef xpath.xmlXPathContext* xpathCtxt
        cdef xpath.xmlXPathObject* xpathVarValue
        cdef char* c_name
        xpathCtxt = self._xpathCtxt
        for name_utf in self._registered_variables:
            c_name = _cstr(name_utf)
            xpathVarValue = xpath.xmlXPathVariableLookup(xpathCtxt, c_name)
            if xpathVarValue is not NULL:
                xpath.xmlXPathRegisterVariable(xpathCtxt, c_name, NULL)
                _freeXPathObject(xpathVarValue)

    def registerVariables(self, variable_dict):
        for name, value in variable_dict.items():
            name_utf = self._to_utf(name)
            self._registerVariable(name_utf, value)
            python.PyList_Append(self._registered_variables, name_utf)

    def registerVariable(self, name, value):
        name_utf = self._to_utf(name)
        self._registerVariable(name_utf, value)
        python.PyList_Append(self._registered_variables, name_utf)

    cdef void _registerVariable(self, name_utf, value):
        xpath.xmlXPathRegisterVariable(
            self._xpathCtxt, _cstr(name_utf), _wrapXPathObject(value))


cdef class XPathEvaluatorBase:
    cdef _XPathContext _context

    def __init__(self, namespaces, extensions, variables=None):
        self._context = _XPathContext(namespaces, extensions, variables)

    cdef object _handle_result(self, xpath.xmlXPathObject* xpathObj, _Document doc):
        if self._context._exc._has_raised():
            if xpathObj is not NULL:
                _freeXPathObject(xpathObj)
                xpathObj = NULL
            self._context._release_temp_refs()
            self._context._exc._raise_if_stored()

        if xpathObj is NULL:
            self._context._release_temp_refs()
            raise XPathSyntaxError, "Error in xpath expression."

        try:
            result = _unwrapXPathObject(xpathObj, doc)
        except XPathResultError:
            _freeXPathObject(xpathObj)
            self._context._release_temp_refs()
            raise

        _freeXPathObject(xpathObj)
        self._context._release_temp_refs()
        return result


cdef class XPathElementEvaluator(XPathEvaluatorBase):
    """Create an XPath evaluator for an element.

    XPath evaluators must not be shared between threads.
    """
    cdef xpath.xmlXPathContext* _c_ctxt
    cdef _Element _element
    def __init__(self, _NodeBase element not None, namespaces=None, extensions=None):
        cdef xpath.xmlXPathContext* xpathCtxt
        cdef int ns_register_status
        cdef _Document doc
        doc = element._doc
        xpathCtxt = xpath.xmlXPathNewContext(doc._c_doc)
        if xpathCtxt is NULL:
            raise XPathContextError, "Unable to create new XPath context"
        self._element = element
        self._c_ctxt = xpathCtxt
        XPathEvaluatorBase.__init__(self, namespaces, extensions)

    def __dealloc__(self):
        if self._c_ctxt is not NULL:
            xpath.xmlXPathFreeContext(self._c_ctxt)
    
    def registerNamespace(self, prefix, uri):
        """Register a namespace with the XPath context.
        """
        self._context.addNamespace(prefix, uri)

    def registerNamespaces(self, namespaces):
        """Register a prefix -> uri dict.
        """
        add = self._context.addNamespace
        for prefix, uri in namespaces.items():
            add(prefix, uri)
    
    def evaluate(self, _path, **_variables):
        """Evaluate an XPath expression on the document.  Variables may be
        provided as keyword arguments. Note that namespaces are currently not
        supported for variables."""
        cdef xpath.xmlXPathContext* xpathCtxt
        cdef xpath.xmlXPathObject*  xpathObj
        cdef xmlNode* c_node
        cdef _Document doc
        xpathCtxt = self._c_ctxt
        xpathCtxt.node = self._element._c_node
        doc = self._element._doc

        self._context.register_context(xpathCtxt, doc)
        self._context.registerVariables(_variables)

        path = _utf8(_path)
        xpathObj = xpath.xmlXPathEvalExpression(_cstr(path), xpathCtxt)
        self._context.unregister_context()

        return self._handle_result(xpathObj, doc)

    #def clone(self):
    #    # XXX pretty expensive so calling this from callback is probably
    #    # not desirable
    #    return XPathEvaluator(self._doc, self._namespaces, self._extensions)

cdef class XPathDocumentEvaluator(XPathElementEvaluator):
    """Create an XPath evaluator for an ElementTree.

    XPath evaluators must not be shared between threads.
    """
    def __init__(self, _ElementTree etree not None, namespaces=None, extensions=None):
        XPathElementEvaluator.__init__(
            self, etree._context_node, namespaces, extensions)

def XPathEvaluator(etree_or_element, namespaces=None, extensions=None):
    """Creates and XPath evaluator for an ElementTree or an Element.

    XPath evaluators must not be shared between threads.
    """
    if isinstance(etree_or_element, _ElementTree):
        return XPathDocumentEvaluator(etree_or_element, namespaces, extensions)
    else:
        return XPathElementEvaluator(etree_or_element, namespaces, extensions)

def Extension(module, function_mapping, ns_uri=None):
    functions = []
    for function_name, xpath_name in function_mapping.items():
        functions[xpath_name] = getattr(module, function_name)
    return {ns_uri : functions}

cdef class XPath(XPathEvaluatorBase):
    cdef xpath.xmlXPathContext* _xpathCtxt
    cdef xpath.xmlXPathCompExpr* _xpath
    cdef object _prefix_map
    cdef readonly object path

    def __init__(self, path, namespaces=None, extensions=None):
        XPathEvaluatorBase.__init__(self, namespaces, extensions, None)
        self.path = path
        path = _utf8(path)
        self._xpath = xpath.xmlXPathCompile(_cstr(path))
        if self._xpath is NULL:
            raise XPathSyntaxError, "Error in XPath expression"
        self._xpathCtxt = xpath.xmlXPathNewContext(NULL)

    def __call__(self, _etree_or_element, **_variables):
        cdef xpath.xmlXPathContext* xpathCtxt
        cdef xpath.xmlXPathObject*  xpathObj
        cdef _Document document
        cdef _NodeBase element
        cdef _XPathContext context

        document = _documentOrRaise(_etree_or_element)
        element  = _rootNodeOf(_etree_or_element)

        xpathCtxt = self._xpathCtxt
        xpathCtxt.doc = document._c_doc
        xpathCtxt.node = element._c_node

        context = self._context
        context._release_temp_refs()
        context.register_context(xpathCtxt, document)
        context.registerVariables(_variables)

        xpathObj = xpath.xmlXPathCompiledEval(self._xpath, xpathCtxt)
        context.unregister_context()
        return self._handle_result(xpathObj, document)

    def evaluate(self, _tree, **_variables):
        return self(_tree, **_variables)

    def __dealloc__(self):
        if self._xpathCtxt is not NULL:
            xpath.xmlXPathFreeContext(self._xpathCtxt)
        if self._xpath is not NULL:
            xpath.xmlXPathFreeCompExpr(self._xpath)

cdef object _replace_strings
cdef object _find_namespaces
_replace_strings = re.compile('("[^"]*")|(\'[^\']*\')').sub
_find_namespaces = re.compile('({[^}]+})').findall

cdef class ETXPath(XPath):
    """Special XPath class that supports the ElementTree {uri} notation for
    namespaces."""
    def __init__(self, path, extensions=None):
        path_utf, namespaces = self._nsextract_path(_utf8(path))
        XPath.__init__(self, funicode(path_utf), namespaces, extensions)

    cdef _nsextract_path(self, path_utf):
        # replace {namespaces} by new prefixes
        cdef int i
        namespaces = {}
        stripped_path = _replace_strings('', path_utf) # remove string literals
        namespace_defs = []
        i = 1
        for namespace_def in _find_namespaces(stripped_path):
            if namespace_def not in namespace_defs:
                prefix = python.PyString_FromFormat("xpp%02d", i)
                i = i+1
                python.PyList_Append(namespace_defs, namespace_def)
                namespace = namespace_def[1:-1] # remove '{}'
                python.PyDict_SetItem(namespaces, prefix, namespace)
                prefix_str = prefix + ':'
                # FIXME: this also replaces {namespaces} within strings!
                path_utf   = path_utf.replace(namespace_def, prefix_str)
        return path_utf, namespaces

################################################################################
# helper functions

cdef xpath.xmlXPathObject* _wrapXPathObject(object obj) except NULL:
    cdef xpath.xmlNodeSet* resultSet
    cdef _NodeBase node
    if python.PyUnicode_Check(obj):
        obj = _utf8(obj)
    if python.PyString_Check(obj):
        return xpath.xmlXPathNewCString(_cstr(obj))
    if python.PyBool_Check(obj):
        return xpath.xmlXPathNewBoolean(obj)
    if python.PyNumber_Check(obj):
        return xpath.xmlXPathNewFloat(obj)
    if obj is None:
        obj = ()
    elif isinstance(obj, _NodeBase):
        obj = (obj,)
    if python.PySequence_Check(obj):
        resultSet = xpath.xmlXPathNodeSetCreate(NULL)
        for element in obj:
            if isinstance(element, _NodeBase):
                node = <_NodeBase>element
                xpath.xmlXPathNodeSetAdd(resultSet, node._c_node)
            else:
                xpath.xmlXPathFreeNodeSet(resultSet)
                raise XPathResultError, "This is not a node: %s" % element
        return xpath.xmlXPathWrapNodeSet(resultSet)
    else:
        raise XPathResultError, "Unknown return type: %s" % obj
    return NULL

cdef object _unwrapXPathObject(xpath.xmlXPathObject* xpathObj,
                               _Document doc):
    if xpathObj.type == xpath.XPATH_UNDEFINED:
        raise XPathResultError, "Undefined xpath result"
    elif xpathObj.type == xpath.XPATH_NODESET:
        return _createNodeSetResult(xpathObj, doc)
    elif xpathObj.type == xpath.XPATH_BOOLEAN:
        return bool(xpathObj.boolval)
    elif xpathObj.type == xpath.XPATH_NUMBER:
        return xpathObj.floatval
    elif xpathObj.type == xpath.XPATH_STRING:
        return funicode(xpathObj.stringval)
    elif xpathObj.type == xpath.XPATH_POINT:
        raise NotImplementedError
    elif xpathObj.type == xpath.XPATH_RANGE:
        raise NotImplementedError
    elif xpathObj.type == xpath.XPATH_LOCATIONSET:
        raise NotImplementedError
    elif xpathObj.type == xpath.XPATH_USERS:
        raise NotImplementedError
    elif xpathObj.type == xpath.XPATH_XSLT_TREE:
        raise NotImplementedError
    else:
        raise XPathResultError, "Unknown xpath result %s" % str(xpathObj.type)

cdef object _createNodeSetResult(xpath.xmlXPathObject* xpathObj, _Document doc):
    cdef xmlNode* c_node
    cdef char* s
    cdef _NodeBase element
    cdef int i
    result = []
    if xpathObj.nodesetval is NULL:
        return result
    for i from 0 <= i < xpathObj.nodesetval.nodeNr:
        c_node = xpathObj.nodesetval.nodeTab[i]
        if _isElement(c_node):
            if c_node.doc != doc._c_doc:
                # XXX: works, but maybe not always the right thing to do?
                # XPath: only runs when extensions create or copy trees
                #        -> we store Python refs to these, so that is OK
                # XSLT: can it leak when merging trees from multiple sources?
                c_node = tree.xmlDocCopyNode(c_node, doc._c_doc, 1)
            element = _elementFactory(doc, c_node)
            result.append(element)
        elif c_node.type == tree.XML_TEXT_NODE:
            result.append(funicode(c_node.content))
        elif c_node.type == tree.XML_ATTRIBUTE_NODE:
            s = tree.xmlNodeGetContent(c_node)
            attr_value = funicode(s)
            tree.xmlFree(s)
            result.append(attr_value)
        else:
            print "Not yet implemented result node type:", c_node.type
            raise NotImplementedError
    return result

cdef void _freeXPathObject(xpath.xmlXPathObject* xpathObj):
    """Free the XPath object, but *never* free the *content* of node sets.
    Python dealloc will do that for us.
    """
    if xpathObj.nodesetval is not NULL:
        xpath.xmlXPathFreeNodeSet(xpathObj.nodesetval)
        xpathObj.nodesetval = NULL
    xpath.xmlXPathFreeObject(xpathObj)

cdef void _xpath_function_call(xpath.xmlXPathParserContext* ctxt, int nargs):
    cdef xpath.xmlXPathContext* rctxt
    cdef _BaseContext context
    rctxt = ctxt.context
    context = <_BaseContext>(rctxt.userData)
    name = rctxt.function
    if rctxt.functionURI is not NULL:
        uri = rctxt.functionURI
    else:
        uri = None
    if context._prepare_function_call(uri, name):
        _extension_function_call(context, ctxt, nargs)
    else:
        xpath.xmlXPathErr(ctxt, xpath.XPATH_EXPR_ERROR)
        exception = XPathFunctionError("XPath function {%s}%s not found" % (uri, name))
        context._exc._store_exception(exception)

cdef void _call_prepared_function(xpath.xmlXPathParserContext* ctxt, int nargs):
    cdef xpath.xmlXPathContext* rctxt
    cdef _BaseContext context
    rctxt = ctxt.context
    context = <_BaseContext>(rctxt.userData)
    _extension_function_call(context, ctxt, nargs)

cdef void _extension_function_call(_BaseContext context,
                                   xpath.xmlXPathParserContext* ctxt, int nargs):
    cdef _NodeBase node
    cdef _Document doc
    cdef xpath.xmlXPathObject* obj
    cdef int i
    doc = context._doc
    try:
        args = []
        for i from 0 <= i < nargs:
            o = _unwrapXPathObject(xpath.valuePop(ctxt), doc)
            python.PyList_Append(args, o)
        python.PyList_Reverse(args)

        res = context._called_function(None, *args)
        # wrap result for XPath consumption
        obj = _wrapXPathObject(res)
        # prevent Python from deallocating elements handed to libxml2
        context._hold(res)
        xpath.valuePush(ctxt, obj)
    except:
        xpath.xmlXPathErr(ctxt, xpath.XPATH_EXPR_ERROR)
        context._exc._store_raised()
