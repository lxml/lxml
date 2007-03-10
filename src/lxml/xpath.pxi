# XPath evaluation

class XPathContextError(XPathError):
    pass

class XPathSyntaxError(LxmlSyntaxError, XPathError):
    pass

################################################################################
# XPath

cdef class _XPathContext(_BaseContext):
    cdef object _variables
    def __init__(self, namespaces, extensions, variables):
        self._variables = variables
        _BaseContext.__init__(self, namespaces, extensions)
        
    cdef register_context(self, xpath.xmlXPathContext* xpathCtxt, _Document doc):
        self._set_xpath_context(xpathCtxt)
        ns_prefixes = _find_all_extension_prefixes()
        if ns_prefixes:
            self.registerNamespaces(ns_prefixes)
        self._register_context(doc)
        if self._variables is not None:
            self.registerVariables(self._variables)
        xpath.xmlXPathRegisterFuncLookup(
            self._xpathCtxt, _function_check, <python.PyObject*>self)

    cdef unregister_context(self):
        cdef xpath.xmlXPathContext* xpathCtxt
        xpathCtxt = self._xpathCtxt
        if xpathCtxt is NULL:
            return
        xpath.xmlXPathRegisteredVariablesCleanup(xpathCtxt)
        self._unregister_context()

    def registerVariables(self, variable_dict):
        for name, value in variable_dict.items():
            name_utf = self._to_utf(name)
            xpath.xmlXPathRegisterVariable(
                self._xpathCtxt, _cstr(name_utf), _wrapXPathObject(value))

    def registerVariable(self, name, value):
        name_utf = self._to_utf(name)
        xpath.xmlXPathRegisterVariable(
            self._xpathCtxt, _cstr(name_utf), _wrapXPathObject(value))

    cdef void _registerVariable(self, name_utf, value):
        xpath.xmlXPathRegisterVariable(
            self._xpathCtxt, _cstr(name_utf), _wrapXPathObject(value))

cdef void _setupDict(xpath.xmlXPathContext* xpathCtxt):
    __GLOBAL_PARSER_CONTEXT.initXPathParserDict(xpathCtxt)

cdef class _XPathEvaluatorBase:
    cdef xpath.xmlXPathContext* _xpathCtxt
    cdef _XPathContext _context

    def __init__(self, namespaces, extensions, variables=None):
        self._context = _XPathContext(namespaces, extensions, variables)

    def __dealloc__(self):
        if self._xpathCtxt is not NULL:
            xpath.xmlXPathFreeContext(self._xpathCtxt)

    def evaluate(self, _eval_arg, **_variables):
        """Evaluate an XPath expression.

        Instead of calling this method, you can also call the evaluator object
        itself.

        Variables may be provided as keyword arguments.  Note that namespaces
        are currently not supported for variables.
        """
        return self(_eval_arg, **_variables)

    cdef int _checkAbsolutePath(self, char* path):
        cdef char c
        if path is NULL:
            return 0
        c = path[0]
        while c == c' ' or c == c'\t':
            path = path + 1
            c = path[0]
        return c == c'/'

    cdef _raise_parse_error(self):
        if self._xpathCtxt is not NULL and \
               self._xpathCtxt.lastError.message is not NULL:
            message = funicode(self._xpathCtxt.lastError.message)
        else:
            message = "error in xpath expression"
        raise XPathSyntaxError, message

    cdef object _handle_result(self, xpath.xmlXPathObject* xpathObj, _Document doc):
        if self._context._exc._has_raised():
            if xpathObj is not NULL:
                _freeXPathObject(xpathObj)
                xpathObj = NULL
            self._context._release_temp_refs()
            self._context._exc._raise_if_stored()

        if xpathObj is NULL:
            self._context._release_temp_refs()
            self._raise_parse_error()

        try:
            result = _unwrapXPathObject(xpathObj, doc)
        finally:
            _freeXPathObject(xpathObj)
            self._context._release_temp_refs()

        return result


cdef class XPathElementEvaluator(_XPathEvaluatorBase):
    """Create an XPath evaluator for an element.

    Absolute XPath expressions (starting with '/') will be evaluated against
    the ElementTree as returned by getroottree().

    XPath evaluators must not be shared between threads.
    """
    cdef _Element _element
    def __init__(self, _Element element not None, namespaces=None, extensions=None):
        cdef xpath.xmlXPathContext* xpathCtxt
        cdef int ns_register_status
        cdef _Document doc
        doc = element._doc
        xpathCtxt = xpath.xmlXPathNewContext(doc._c_doc)
        self._xpathCtxt = xpathCtxt
        if xpathCtxt is NULL:
            raise XPathContextError, "Unable to create new XPath context"
        _setupDict(xpathCtxt)
        self._element = element
        _XPathEvaluatorBase.__init__(self, namespaces, extensions)

    def registerNamespace(self, prefix, uri):
        """Register a namespace with the XPath context.
        """
        self._context.addNamespace(prefix, uri)

    def registerNamespaces(self, namespaces):
        """Register a prefix -> uri dict.
        """
        for prefix, uri in namespaces.items():
            self._context.addNamespace(prefix, uri)

    def __call__(self, _path, **_variables):
        """Evaluate an XPath expression on the document.

        Variables may be provided as keyword arguments.  Note that namespaces
        are currently not supported for variables.

        Absolute XPath expressions (starting with '/') will be evaluated
        against the ElementTree as returned by getroottree().
        """
        cdef xpath.xmlXPathContext* xpathCtxt
        cdef xpath.xmlXPathObject*  xpathObj
        cdef _Document doc
        cdef char* c_path
        path = _utf8(_path)
        xpathCtxt = self._xpathCtxt
        xpathCtxt.node = self._element._c_node
        doc = self._element._doc

        self._context.register_context(xpathCtxt, doc)
        try:
            self._context.registerVariables(_variables)
            xpathObj = xpath.xmlXPathEvalExpression(_cstr(path), xpathCtxt)
        finally:
            self._context.unregister_context()

        return self._handle_result(xpathObj, doc)


cdef class XPathDocumentEvaluator(XPathElementEvaluator):
    """Create an XPath evaluator for an ElementTree.

    XPath evaluators must not be shared between threads.
    """
    def __init__(self, _ElementTree etree not None, namespaces=None, extensions=None):
        XPathElementEvaluator.__init__(
            self, etree._context_node, namespaces, extensions)

    def __call__(self, _path, **_variables):
        """Evaluate an XPath expression on the document.

        Variables may be provided as keyword arguments.  Note that namespaces
        are currently not supported for variables.
        """
        cdef xpath.xmlXPathContext* xpathCtxt
        cdef xpath.xmlXPathObject*  xpathObj
        cdef xmlDoc* c_doc
        cdef _Document doc
        path = _utf8(_path)
        xpathCtxt = self._xpathCtxt
        doc = self._element._doc

        self._context.register_context(xpathCtxt, doc)
        c_doc = _fakeRootDoc(doc._c_doc, self._element._c_node)
        try:
            self._context.registerVariables(_variables)
            xpathCtxt.doc  = c_doc
            xpathCtxt.node = tree.xmlDocGetRootElement(c_doc)
            xpathObj = xpath.xmlXPathEvalExpression(_cstr(path), xpathCtxt)
        finally:
            _destroyFakeDoc(doc._c_doc, c_doc)
            self._context.unregister_context()

        return self._handle_result(xpathObj, doc)


def XPathEvaluator(etree_or_element, namespaces=None, extensions=None):
    """Creates an XPath evaluator for an ElementTree or an Element.

    The resulting object can be called with an XPath expression as argument
    and XPath variables provided as keyword arguments.

    XPath evaluators must not be shared between threads.
    """
    if isinstance(etree_or_element, _ElementTree):
        return XPathDocumentEvaluator(etree_or_element, namespaces, extensions)
    else:
        return XPathElementEvaluator(etree_or_element, namespaces, extensions)


cdef class XPath(_XPathEvaluatorBase):
    """A compiled XPath expression that can be called on Elements and
    ElementTrees.

    Besides the XPath expression, you can pass namespace mappings and
    extensions to the constructor through the keyword arguments ``namespaces``
    and ``extensions``.
    """
    cdef xpath.xmlXPathCompExpr* _xpath
    cdef readonly object path

    def __init__(self, path, namespaces=None, extensions=None):
        _XPathEvaluatorBase.__init__(self, namespaces, extensions)
        self._xpath = NULL
        self.path = path
        path = _utf8(path)
        self._xpathCtxt = xpath.xmlXPathNewContext(NULL)
        _setupDict(self._xpathCtxt)
        self._xpath = xpath.xmlXPathCtxtCompile(self._xpathCtxt, _cstr(path))
        if self._xpath is NULL:
            self._raise_parse_error()

    def __call__(self, _etree_or_element, **_variables):
        cdef python.PyThreadState* state
        cdef xpath.xmlXPathContext* xpathCtxt
        cdef xpath.xmlXPathObject*  xpathObj
        cdef _Document document
        cdef _Element element
        cdef _XPathContext context

        document = _documentOrRaise(_etree_or_element)
        element  = _rootNodeOrRaise(_etree_or_element)

        xpathCtxt = self._xpathCtxt
        xpathCtxt.doc  = document._c_doc
        xpathCtxt.node = element._c_node

        context = self._context
        context.register_context(xpathCtxt, document)
        try:
            context.registerVariables(_variables)
            state = python.PyEval_SaveThread()
            xpathObj = xpath.xmlXPathCompiledEval(self._xpath, xpathCtxt)
            python.PyEval_RestoreThread(state)
        finally:
            context.unregister_context()
        return self._handle_result(xpathObj, document)

    def __dealloc__(self):
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
        path, namespaces = self._nsextract_path(path)
        XPath.__init__(self, path, namespaces, extensions)

    cdef _nsextract_path(self, path):
        # replace {namespaces} by new prefixes
        cdef int i
        path_utf = _utf8(path)
        stripped_path = _replace_strings('', path_utf) # remove string literals
        namespaces = {}
        namespace_defs = []
        i = 1
        for namespace_def in _find_namespaces(stripped_path):
            if namespace_def not in namespace_defs:
                prefix = python.PyString_FromFormat("xpp%02d", i)
                i = i+1
                python.PyList_Append(namespace_defs, namespace_def)
                namespace = namespace_def[1:-1] # remove '{}'
                namespace = python.PyUnicode_FromEncodedObject(
                    namespace, 'UTF-8', 'strict')
                python.PyDict_SetItem(namespaces, prefix, namespace)
                prefix_str = prefix + ':'
                # FIXME: this also replaces {namespaces} within strings!
                path_utf = path_utf.replace(namespace_def, prefix_str)
        path = python.PyUnicode_FromEncodedObject(path_utf, 'UTF-8', 'strict')
        return path, namespaces
