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

class XPathResultError(XPathError):
    pass

class XPathSyntaxError(LxmlSyntaxError):
    pass

################################################################################
# support for extension functions in XPath/XSLT

cdef class _BaseContext:
    cdef xpath.xmlXPathContext* _xpathCtxt
    cdef _Document _doc
    cdef object _extensions
    cdef object _namespaces
    cdef object _registered_namespaces
    cdef object _extension_functions
    cdef object _utf_refs
    # for exception handling and temporary reference keeping:
    cdef object _temp_elements
    cdef object _temp_docs
    cdef object _exc_info

    def __init__(self, namespaces, extensions):
        self._xpathCtxt = NULL
        self._utf_refs = {}

        # fix old format extensions
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
        self._exc_info   = None
        self._extensions = extensions
        self._namespaces = namespaces
        self._registered_namespaces = []
        self._extension_functions = {}
        self._temp_elements = {}
        self._temp_docs = {}

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
        self._doc      = doc
        self._exc_info = None
        namespaces = self._namespaces
        if namespaces is not None:
            self.registerNamespaces(namespaces)
            extensions = _find_extensions(namespaces.values())
        else:
            extensions = _find_all_extensions()
        if self._extensions is not None:
            # add user provided extensions
            extensions.update(self._extensions)
        if extensions:
            if not allow_none_namespace:
                python.PyDict_DelItem(extensions, None)
            self._registerExtensionFunctions(extensions)

    cdef _unregister_context(self):
        self._unregisterExtensionFunctions()
        self._unregisterNamespaces()
        self._free_context()

    cdef _free_context(self):
        del self._registered_namespaces[:]
        python.PyDict_Clear(self._extension_functions)
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
    
    # extension functions (internal UTF-8 methods with leading '_')

    def registerExtensionFunctions(self, extensions):
        for ns_uri, extension in extensions.items():
            for name, function in extension.items():
                self._registerExtensionFunction(
                    self._to_utf(ns_uri), self._to_utf(name), function)

    def registerExtensionFunction(self, ns_uri, name, function):
        self._registerExtensionFunction(
            self._to_utf(ns_uri), self._to_utf(name), function)

    cdef _registerExtensionFunctions(self, extensions_utf):
        for ns_uri_utf, extension in extensions_utf.items():
            for name_utf, function in extension.items():
                self._registerExtensionFunction(ns_uri_utf, name_utf, function)

    cdef _registerExtensionFunction(self, ns_uri_utf, name_utf, function):
        self._contextRegisterExtensionFunction(ns_uri_utf, name_utf)
        self._extension_functions[(ns_uri_utf, name_utf)] = function

    cdef _unregisterExtensionFunctions(self):
        for ns_uri_utf, name_utf in self._extension_functions:
            self._contextUnregisterExtensionFunction(ns_uri_utf, name_utf)

    def find_extension(self, ns_uri_utf, name_utf):
        return self._extension_functions[(ns_uri_utf, name_utf)]

    # Python reference keeping during XPath function evaluation

    cdef _release_temp_refs(self):
        "Free temporarily referenced objects from this context."
        python.PyDict_Clear(self._temp_elements)
        python.PyDict_Clear(self._temp_docs)
        
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
                python.PyDict_SetItem(self._temp_elements, id(element), element)
                #print "Holding document:", <int>element._doc._c_doc
                python.PyDict_SetItem(self._temp_docs, id(element._doc), element._doc)

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

    cdef void _register_exslt_regexp(self, _BaseContext context):
        ns = "http://exslt.org/regular-expressions"
        context._registerExtensionFunction(ns, "test",    self.test)
        context._registerExtensionFunction(ns, "match",   self.match)
        context._registerExtensionFunction(ns, "replace", self.replace)

################################################################################
# XSLT

cdef class _XSLTContext(_BaseContext):
    cdef xslt.xsltTransformContext* _xsltCtxt
    def __init__(self, namespaces, extensions):
        self._xsltCtxt = NULL
        _BaseContext.__init__(self, namespaces, extensions)

    cdef register_context(self, xslt.xsltTransformContext* xsltCtxt, _Document doc):
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

    def _contextRegisterExtensionFunction(self, ns_uri_utf, name_utf):
        if ns_uri_utf is None:
            raise XSLTExtensionError, "extensions must have non-empty namespaces"
        xslt.xsltRegisterExtFunction(
            self._xsltCtxt, _cstr(name_utf), _cstr(ns_uri_utf),
            _xpathCallback)

    def _contextUnregisterExtensionFunction(self, ns_uri_utf, name_utf):
        if ns_uri_utf is not None:
            xslt.xsltRegisterExtFunction(
                self._xsltCtxt, _cstr(name_utf), _cstr(ns_uri_utf),
                _xpathCallback)


cdef class XSLT:
    """Turn a document into an XSLT object.
    """
    cdef _XSLTContext _context
    cdef xslt.xsltStylesheet* _c_style
    cdef _ExsltRegExp _regexp
    cdef object _doc_url_utf
    
    def __init__(self, xslt_input, extensions=None):
        # make a copy of the document as stylesheet needs to assume it
        # doesn't change
        cdef xslt.xsltStylesheet* c_style
        cdef xmlDoc* c_doc
        cdef xmlDoc* fake_c_doc
        cdef _Document doc
        cdef _NodeBase root_node

        doc = _documentOrRaise(xslt_input)
        root_node = _rootNodeOf(xslt_input)

        fake_c_doc = _fakeRootDoc(doc._c_doc, root_node._c_node)
        c_doc = tree.xmlCopyDoc(fake_c_doc, 1)
        _destroyFakeDoc(doc._c_doc, fake_c_doc)

        # XXX work around bug in xmlCopyDoc (fix is upcoming in new release
        # of libxml2)
        if c_doc.URL is not NULL and c_doc.URL != doc._c_doc.URL:
            tree.xmlFree(c_doc.URL)
        if doc._c_doc.URL is not NULL:
            self._doc_url_utf = doc._c_doc.URL
            c_doc.URL = tree.xmlStrdup(doc._c_doc.URL)
        else:
            self._doc_url_utf = "__STRING__XSLT__%s" % id(self)
            c_doc.URL = tree.xmlStrdup(_cstr(self._doc_url_utf))

        c_style = xslt.xsltParseStylesheetDoc(c_doc)
        if c_style is NULL:
            raise XSLTParseError, "Cannot parse style sheet"
        self._c_style = c_style

        self._context = _XSLTContext(None, extensions)
        self._regexp  = _ExsltRegExp()
        # XXX is it worthwile to use xsltPrecomputeStylesheet here?
        
    def __dealloc__(self):
        # this cleans up copy of doc as well
        xslt.xsltFreeStylesheet(self._c_style)

    def __call__(self, _input, **_kw):
        cdef _Document input_doc
        cdef _NodeBase root_node
        cdef _Document result_doc
        cdef xslt.xsltTransformContext* transform_ctxt
        cdef xmlDoc* c_result
        cdef xmlDoc* c_doc
        cdef char** params
        cdef int i
        cdef int j

        input_doc = _documentOrRaise(_input)
        root_node = _rootNodeOf(_input)

        c_doc = _fakeRootDoc(input_doc._c_doc, root_node._c_node)

        transform_ctxt = xslt.xsltNewTransformContext(self._c_style, c_doc)
        if transform_ctxt is NULL:
            _destroyFakeDoc(input_doc._c_doc, c_doc)
            raise XSLTApplyError, "Error preparing stylesheet run"

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

        self._context._release_temp_refs()
        self._context.register_context(transform_ctxt, input_doc)
        self._regexp._register_exslt_regexp(self._context)

        c_result = xslt.xsltApplyStylesheetUser(self._c_style, c_doc, params,
                                                NULL, NULL, transform_ctxt)

        if params is not NULL:
            # deallocate space for parameters
            cstd.free(params)

        self._context.free_context()
        _destroyFakeDoc(input_doc._c_doc, c_doc)

        if c_result is NULL:
            raise XSLTApplyError, "Error applying stylesheet"

        result_doc = _documentFactory(c_result)
        return _xsltResultTreeFactory(result_doc, self)

    def apply(self, _input, **_kw):
        return self(_input, **_kw)

    def tostring(self, _ElementTree result_tree):
        """Save result doc to string using stylesheet as guidance.
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

################################################################################
# XPath

cdef class _XPathContext(_BaseContext):
    cdef object _variables
    cdef object _registered_variables
    def __init__(self, namespaces, extensions, variables):
        _BaseContext.__init__(self, namespaces, extensions)
        self._variables = variables
        self._registered_variables  = []
        
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
        self._registered_variables  = []
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
                xpath.xmlXPathFreeObject(xpathVarValue)

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

    def _contextRegisterExtensionFunction(self, ns_uri_utf, name_utf):
        if ns_uri_utf is not None:
            xpath.xmlXPathRegisterFuncNS(
                self._xpathCtxt, _cstr(name_utf), _cstr(ns_uri_utf),
                _xpathCallback)
        else:
            xpath.xmlXPathRegisterFunc(
                self._xpathCtxt, _cstr(name_utf),
                _xpathCallback)

    def _contextUnregisterExtensionFunction(self, ns_uri_utf, name_utf):
        if ns_uri_utf is not None:
            xpath.xmlXPathRegisterFuncNS(
                self._xpathCtxt, _cstr(name_utf), _cstr(ns_uri_utf), NULL)
        else:
            xpath.xmlXPathRegisterFunc(
                self._xpathCtxt, _cstr(name_utf), NULL)


cdef class XPathEvaluatorBase:
    cdef _XPathContext _context

    def __init__(self, namespaces, extensions, variables=None):
        self._context = _XPathContext(namespaces, extensions, variables)

    cdef object _handle_result(self, xpath.xmlXPathObject* xpathObj, _Document doc):
        _exc_info = self._context._exc_info
        if _exc_info is not None:
            type, value, traceback = _exc_info
            raise type, value, traceback
        if xpathObj is NULL:
            raise XPathSyntaxError, "Error in xpath expression."
        try:
            result = _unwrapXPathObject(xpathObj, doc)
        except XPathResultError:
            xpath.xmlXPathFreeObject(xpathObj)
            raise
        xpath.xmlXPathFreeObject(xpathObj)
        return result


cdef class XPathDocumentEvaluator(XPathEvaluatorBase):
    """Create an XPath evaluator for a document.
    """
    cdef xpath.xmlXPathContext* _c_ctxt
    cdef _Document _doc
    
    def __init__(self, etree, namespaces=None, extensions=None):
        cdef xpath.xmlXPathContext* xpathCtxt
        cdef int ns_register_status
        cdef _Document doc

        if isinstance(etree, _Document):
            doc = <_Document>etree # for internal use only!
        elif isinstance(etree, _ElementTree):
            doc = (<_ElementTree>etree)._doc
        else:
            raise TypeError, "XPathDocumentEvaluator can only work on ElementTree objects"
        
        xpathCtxt = xpath.xmlXPathNewContext(doc._c_doc)
        if xpathCtxt is NULL:
            # XXX what triggers this exception?
            raise XPathContextError, "Unable to create new XPath context"

        self._doc = doc
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
        for prefix, uri in namespaces.items():
            self.registerNamespace(prefix, uri)
    
    def evaluate(self, _path, **_variables):
        """Evaluate an XPath expression on the document.  Variables
        may be given as keyword arguments. Note that namespaces are
        currently not supported for variables."""
        return self._evaluate(_path, NULL, _variables)

    cdef object _evaluate(self, path, xmlNode* c_ctxt_node, variable_dict):
        cdef xpath.xmlXPathContext* xpathCtxt
        cdef xpath.xmlXPathObject*  xpathObj
        cdef xmlNode* c_node
        
        xpathCtxt = self._c_ctxt
        # if element context is requested; unfortunately need to modify ctxt
        xpathCtxt.node = c_ctxt_node

        self._context._release_temp_refs()
        self._context.register_context(xpathCtxt, self._doc)
        self._context.registerVariables(variable_dict)

        path = _utf8(path)
        xpathObj = xpath.xmlXPathEvalExpression(_cstr(path), xpathCtxt)
        self._context.unregister_context()

        return self._handle_result(xpathObj, self._doc)

    #def clone(self):
    #    # XXX pretty expensive so calling this from callback is probably
    #    # not desirable
    #    return XPathEvaluator(self._doc, self._namespaces, self._extensions)

cdef class XPathElementEvaluator(XPathDocumentEvaluator):
    """Create an XPath evaluator for an element.
    """
    cdef _Element _element

    def __init__(self, _Element element not None, namespaces=None, extensions=None):
        XPathDocumentEvaluator.__init__(
            self, element._doc, namespaces, extensions)
        self._element = element

    def evaluate(self, _path, **_variables):
        """Evaluate an XPath expression on the element.  Variables may
        be given as keyword arguments. Note that namespaces are
        currently not supported for variables."""
        return self._evaluate(_path, self._element._c_node, _variables)

def XPathEvaluator(etree_or_element, namespaces=None, extensions=None):
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
            raise XPathSyntaxError, "Error in xpath expression."
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
        # XXX use the Wrap variant? Or leak...
        return xpath.xmlXPathNewCString(_cstr(obj))
    if python.PyBool_Check(obj):
        return xpath.xmlXPathNewBoolean(obj)
    if python.PyNumber_Check(obj):
        return xpath.xmlXPathNewFloat(obj)
    if isinstance(obj, _NodeBase):
        obj = (obj,)
    if python.PySequence_Check(obj):
        resultSet = xpath.xmlXPathNodeSetCreate(NULL)
        for element in obj:
            if isinstance(element, _NodeBase):
                node = <_NodeBase>element
                xpath.xmlXPathNodeSetAdd(resultSet, node._c_node)
            else:
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
        return _createNodeSetResult(doc, xpathObj)
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

cdef object _createNodeSetResult(_Document doc,
                                 xpath.xmlXPathObject* xpathObj):
    cdef xmlNode* c_node
    cdef char* s
    cdef _NodeBase element
    result = []
    if xpathObj.nodesetval is NULL:
        return result
    for i from 0 <= i < xpathObj.nodesetval.nodeNr:
        c_node = xpathObj.nodesetval.nodeTab[i]
        if _isElement(c_node):
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

cdef void _xpathCallback(xpath.xmlXPathParserContext* ctxt, int nargs):
    cdef xpath.xmlXPathContext* rctxt
    cdef _Document doc
    cdef xpath.xmlXPathObject* obj
    cdef _BaseContext extensions

    rctxt = ctxt.context

    # get information on what function is called
    name = rctxt.function
    if rctxt.functionURI is not NULL:
        uri = rctxt.functionURI
    else:
        uri = None

    # get our evaluator
    extensions = <_BaseContext>(rctxt.userData)

    # lookup up the extension function in the context
    f = extensions.find_extension(uri, name)

    args = []
    doc = extensions._doc
    for i from 0 <= i < nargs:
        args.append(_unwrapXPathObject(xpath.valuePop(ctxt), doc))
    args.reverse()

    try:
        # call the function
        res = f(None, *args)
        # hold python objects temporarily so that they won't get deallocated
        # during processing
        extensions._hold(res)
        # now wrap for XPath consumption
        obj = _wrapXPathObject(res)
    except:
        xpath.xmlXPathErr(
            ctxt,
            xmlerror.XML_XPATH_EXPR_ERROR - xmlerror.XML_XPATH_EXPRESSION_OK)
        extensions._exc_info = sys.exc_info()
        return
    xpath.valuePush(ctxt, obj)
