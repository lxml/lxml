# XPath evaluation

class XPathContextError(XPathError):
    pass

class XPathSyntaxError(LxmlSyntaxError):
    pass

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
