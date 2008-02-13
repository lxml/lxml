# XPath evaluation

class XPathSyntaxError(LxmlSyntaxError, XPathError):
    pass

################################################################################
# XPath

cdef object _XPATH_SYNTAX_ERRORS
_XPATH_SYNTAX_ERRORS = (
    xmlerror.XML_XPATH_NUMBER_ERROR,
    xmlerror.XML_XPATH_UNFINISHED_LITERAL_ERROR,
    xmlerror.XML_XPATH_VARIABLE_REF_ERROR,
    xmlerror.XML_XPATH_INVALID_PREDICATE_ERROR,
    xmlerror.XML_XPATH_UNCLOSED_ERROR,
    xmlerror.XML_XPATH_INVALID_CHAR_ERROR
)

cdef object _XPATH_EVAL_ERRORS
_XPATH_EVAL_ERRORS = (
    xmlerror.XML_XPATH_UNDEF_VARIABLE_ERROR,
    xmlerror.XML_XPATH_UNDEF_PREFIX_ERROR,
    xmlerror.XML_XPATH_UNKNOWN_FUNC_ERROR,
    xmlerror.XML_XPATH_INVALID_OPERAND,
    xmlerror.XML_XPATH_INVALID_TYPE,
    xmlerror.XML_XPATH_INVALID_ARITY,
    xmlerror.XML_XPATH_INVALID_CTXT_SIZE,
    xmlerror.XML_XPATH_INVALID_CTXT_POSITION
)

cdef int _register_xpath_function(void* ctxt, name_utf, ns_utf):
    if ns_utf is None:
        return xpath.xmlXPathRegisterFunc(
            <xpath.xmlXPathContext*>ctxt, _cstr(name_utf),
            _xpath_function_call)
    else:
        return xpath.xmlXPathRegisterFuncNS(
            <xpath.xmlXPathContext*>ctxt, _cstr(name_utf), _cstr(ns_utf),
            _xpath_function_call)

cdef int _unregister_xpath_function(void* ctxt, name_utf, ns_utf):
    if ns_utf is None:
        return xpath.xmlXPathRegisterFunc(
            <xpath.xmlXPathContext*>ctxt, _cstr(name_utf), NULL)
    else:
        return xpath.xmlXPathRegisterFuncNS(
            <xpath.xmlXPathContext*>ctxt, _cstr(name_utf), _cstr(ns_utf), NULL)


cdef class _XPathContext(_BaseContext):
    cdef object _variables
    def __init__(self, namespaces, extensions, enable_regexp, variables):
        self._variables = variables
        _BaseContext.__init__(self, namespaces, extensions, enable_regexp)

    cdef set_context(self, xpath.xmlXPathContext* xpathCtxt):
        self._set_xpath_context(xpathCtxt)
        self._setupDict(xpathCtxt)
        self.registerLocalNamespaces()
        self.registerLocalFunctions(xpathCtxt, _register_xpath_function)

    cdef register_context(self, _Document doc):
        self._register_context(doc)
        self.registerGlobalNamespaces()
        self.registerGlobalFunctions(self._xpathCtxt, _register_xpath_function)
        if self._variables is not None:
            self.registerVariables(self._variables)

    cdef unregister_context(self):
        self.unregisterGlobalFunctions(
            self._xpathCtxt, _unregister_xpath_function)
        self.unregisterGlobalNamespaces()
        xpath.xmlXPathRegisteredVariablesCleanup(self._xpathCtxt)
        self._cleanup_context()

    cdef registerVariables(self, variable_dict):
        for name, value in variable_dict.items():
            name_utf = self._to_utf(name)
            xpath.xmlXPathRegisterVariable(
                self._xpathCtxt, _cstr(name_utf), _wrapXPathObject(value))

    cdef registerVariable(self, name, value):
        name_utf = self._to_utf(name)
        xpath.xmlXPathRegisterVariable(
            self._xpathCtxt, _cstr(name_utf), _wrapXPathObject(value))

    cdef void _registerVariable(self, name_utf, value):
        xpath.xmlXPathRegisterVariable(
            self._xpathCtxt, _cstr(name_utf), _wrapXPathObject(value))

    cdef void _setupDict(self, xpath.xmlXPathContext* xpathCtxt):
        __GLOBAL_PARSER_CONTEXT.initXPathParserDict(xpathCtxt)

cdef bint _XPATH_VERSION_WARNING_REQUIRED
if _LIBXML_VERSION_INT == 20627:
    _XPATH_VERSION_WARNING_REQUIRED = 1
else:
    _XPATH_VERSION_WARNING_REQUIRED = 0

cdef class _XPathEvaluatorBase:
    cdef xpath.xmlXPathContext* _xpathCtxt
    cdef _XPathContext _context
    cdef python.PyThread_type_lock _eval_lock
    cdef _ErrorLog _error_log

    def __init__(self, namespaces, extensions, enable_regexp):
        global _XPATH_VERSION_WARNING_REQUIRED
        if _XPATH_VERSION_WARNING_REQUIRED:
            _XPATH_VERSION_WARNING_REQUIRED = 0
            import warnings
            warnings.warn("This version of libxml2 has a known XPath bug. " + \
                          "Use it at your own risk.")
        self._error_log = _ErrorLog()
        self._context = _XPathContext(namespaces, extensions,
                                      enable_regexp, None)

    property error_log:
        def __get__(self):
            return self._error_log.copy()

    def __dealloc__(self):
        if self._xpathCtxt is not NULL:
            xpath.xmlXPathFreeContext(self._xpathCtxt)

    cdef set_context(self, xpath.xmlXPathContext* xpathCtxt):
        self._xpathCtxt = xpathCtxt
        self._context.set_context(xpathCtxt)

    def evaluate(self, _eval_arg, **_variables):
        """evaluate(self, _eval_arg, **_variables)

        Evaluate an XPath expression.

        Instead of calling this method, you can also call the evaluator object
        itself.

        Variables may be provided as keyword arguments.  Note that namespaces
        are currently not supported for variables.

        :deprecated: call the object, not its method.
        """
        return self(_eval_arg, **_variables)

    cdef bint _checkAbsolutePath(self, char* path):
        cdef char c
        if path is NULL:
            return 0
        c = path[0]
        while c == c' ' or c == c'\t':
            path = path + 1
            c = path[0]
        return c == c'/'

    cdef int _lock(self) except -1:
        cdef int result
        if config.ENABLE_THREADING and self._eval_lock != NULL:
            with nogil:
                result = python.PyThread_acquire_lock(
                    self._eval_lock, python.WAIT_LOCK)
            if result == 0:
                raise ParserError("parser locking failed")
        return 0

    cdef void _unlock(self):
        if config.ENABLE_THREADING and self._eval_lock != NULL:
            python.PyThread_release_lock(self._eval_lock)

    cdef _raise_parse_error(self):
        cdef _BaseErrorLog entries
        entries = self._error_log.filter_types(_XPATH_SYNTAX_ERRORS)
        if entries:
            message = entries._buildExceptionMessage(None)
            if message is not None:
                raise XPathSyntaxError(message, self._error_log)
        raise XPathSyntaxError(self._error_log._buildExceptionMessage(
                "Error in xpath expression"),
                               self._error_log)

    cdef _raise_eval_error(self):
        cdef _BaseErrorLog entries
        entries = self._error_log.filter_types(_XPATH_EVAL_ERRORS)
        if not entries:
            entries = self._error_log.filter_types(_XPATH_SYNTAX_ERRORS)
        if entries:
            message = entries._buildExceptionMessage(None)
            if message is not None:
                raise XPathEvalError(message, self._error_log)
        raise XPathEvalError(self._error_log._buildExceptionMessage(
                "Error in xpath expression"),
                             self._error_log)

    cdef object _handle_result(self, xpath.xmlXPathObject* xpathObj, _Document doc):
        if self._context._exc._has_raised():
            if xpathObj is not NULL:
                _freeXPathObject(xpathObj)
                xpathObj = NULL
            self._context._release_temp_refs()
            self._context._exc._raise_if_stored()

        if xpathObj is NULL:
            self._context._release_temp_refs()
            self._raise_eval_error()

        try:
            result = _unwrapXPathObject(xpathObj, doc)
        finally:
            _freeXPathObject(xpathObj)
            self._context._release_temp_refs()

        return result


cdef class XPathElementEvaluator(_XPathEvaluatorBase):
    """XPathElementEvaluator(self, element, namespaces=None, extensions=None, regexp=True)
    Create an XPath evaluator for an element.

    Absolute XPath expressions (starting with '/') will be evaluated against
    the ElementTree as returned by getroottree().

    Additional namespace declarations can be passed with the 'namespace'
    keyword argument.  EXSLT regular expression support can be disabled with
    the 'regexp' boolean keyword (defaults to True).
    """
    cdef _Element _element
    def __init__(self, _Element element not None, *, namespaces=None,
                 extensions=None, regexp=True):
        cdef xpath.xmlXPathContext* xpathCtxt
        cdef int ns_register_status
        cdef _Document doc
        self._element = element
        doc = element._doc
        _XPathEvaluatorBase.__init__(self, namespaces, extensions, regexp)
        xpathCtxt = xpath.xmlXPathNewContext(doc._c_doc)
        if xpathCtxt is NULL:
            python.PyErr_NoMemory()
        self.set_context(xpathCtxt)

    def registerNamespace(self, prefix, uri):
        """Register a namespace with the XPath context.

        :deprecated: use ``register_namespace()`` instead
        """
        self._context.addNamespace(prefix, uri)

    def register_namespace(self, prefix, uri):
        """Register a namespace with the XPath context.
        """
        self._context.addNamespace(prefix, uri)

    def registerNamespaces(self, namespaces):
        """Register a prefix -> uri dict.

        :deprecated: use ``register_namespaces()`` instead
        """
        for prefix, uri in namespaces.items():
            self._context.addNamespace(prefix, uri)

    def register_namespaces(self, namespaces):
        """Register a prefix -> uri dict.
        """
        for prefix, uri in namespaces.items():
            self._context.addNamespace(prefix, uri)

    def __call__(self, _path, **_variables):
        """__call__(self, _path, **_variables)

        Evaluate an XPath expression on the document.

        Variables may be provided as keyword arguments.  Note that namespaces
        are currently not supported for variables.

        Absolute XPath expressions (starting with '/') will be evaluated
        against the ElementTree as returned by getroottree().
        """
        cdef xpath.xmlXPathObject*  xpathObj
        cdef _Document doc
        cdef char* c_path
        path = _utf8(_path)
        doc = self._element._doc

        self._lock()
        self._error_log.connect()
        self._xpathCtxt.node = self._element._c_node
        try:
            self._context.register_context(doc)
            self._context.registerVariables(_variables)
            c_path = _cstr(path)
            with nogil:
                xpathObj = xpath.xmlXPathEvalExpression(
                    c_path, self._xpathCtxt)
            result = self._handle_result(xpathObj, doc)
        finally:
            self._error_log.disconnect()
            self._context.unregister_context()
            self._unlock()

        return result


cdef class XPathDocumentEvaluator(XPathElementEvaluator):
    """XPathDocumentEvaluator(self, etree, namespaces=None, extensions=None, regexp=True)
    Create an XPath evaluator for an ElementTree.

    Additional namespace declarations can be passed with the 'namespace'
    keyword argument.  EXSLT regular expression support can be disabled with
    the 'regexp' boolean keyword (defaults to True).
    """
    def __init__(self, _ElementTree etree not None, *, namespaces=None,
                 extensions=None, regexp=True):
        XPathElementEvaluator.__init__(
            self, etree._context_node, namespaces=namespaces, 
            extensions=extensions, regexp=regexp)

    def __call__(self, _path, **_variables):
        """__call__(self, _path, **_variables)

        Evaluate an XPath expression on the document.

        Variables may be provided as keyword arguments.  Note that namespaces
        are currently not supported for variables.
        """
        cdef xpath.xmlXPathObject*  xpathObj
        cdef xmlDoc* c_doc
        cdef _Document doc
        cdef char* c_path
        path = _utf8(_path)
        doc = self._element._doc

        self._lock()
        self._error_log.connect()
        try:
            self._context.register_context(doc)
            c_doc = _fakeRootDoc(doc._c_doc, self._element._c_node)
            try:
                self._context.registerVariables(_variables)
                c_path = _cstr(path)
                with nogil:
                    self._xpathCtxt.doc  = c_doc
                    self._xpathCtxt.node = tree.xmlDocGetRootElement(c_doc)
                    xpathObj = xpath.xmlXPathEvalExpression(
                        c_path, self._xpathCtxt)
                result = self._handle_result(xpathObj, doc)
            finally:
                _destroyFakeDoc(doc._c_doc, c_doc)
                self._context.unregister_context()
        finally:
            self._error_log.disconnect()
            self._unlock()

        return result


def XPathEvaluator(etree_or_element, *, namespaces=None, extensions=None,
                   regexp=True):
    """XPathEvaluator(etree_or_element, namespaces=None, extensions=None, regexp=True)

    Creates an XPath evaluator for an ElementTree or an Element.

    The resulting object can be called with an XPath expression as argument
    and XPath variables provided as keyword arguments.

    Additional namespace declarations can be passed with the 'namespace'
    keyword argument.  EXSLT regular expression support can be disabled with
    the 'regexp' boolean keyword (defaults to True).
    """
    if isinstance(etree_or_element, _ElementTree):
        return XPathDocumentEvaluator(
            etree_or_element, namespaces=namespaces,
            extensions=extensions, regexp=regexp)
    else:
        return XPathElementEvaluator(
            etree_or_element, namespaces=namespaces,
            extensions=extensions, regexp=regexp)


cdef class XPath(_XPathEvaluatorBase):
    """XPath(self, path, namespaces=None, extensions=None, regexp=True)
    A compiled XPath expression that can be called on Elements and ElementTrees.

    Besides the XPath expression, you can pass prefix-namespace mappings and
    extension functions to the constructor through the keyword arguments
    ``namespaces`` and ``extensions``.  EXSLT regular expression support can
    be disabled with the 'regexp' boolean keyword (defaults to True).
    """
    cdef xpath.xmlXPathCompExpr* _xpath
    cdef readonly object path

    def __init__(self, path, *, namespaces=None, extensions=None, regexp=True):
        cdef xpath.xmlXPathContext* xpathCtxt
        _XPathEvaluatorBase.__init__(self, namespaces, extensions, regexp)
        self.path = path
        path = _utf8(path)
        xpathCtxt = xpath.xmlXPathNewContext(NULL)
        if xpathCtxt is NULL:
            python.PyErr_NoMemory()
        self.set_context(xpathCtxt)
        self._error_log.connect()
        self._xpath = xpath.xmlXPathCtxtCompile(xpathCtxt, _cstr(path))
        self._error_log.disconnect()
        if self._xpath is NULL:
            self._raise_parse_error()

    def __call__(self, _etree_or_element, **_variables):
        "__call__(self, _etree_or_element, **_variables)"
        cdef xpath.xmlXPathObject*  xpathObj
        cdef _Document document
        cdef _Element element
        cdef _XPathContext context

        document = _documentOrRaise(_etree_or_element)
        element  = _rootNodeOrRaise(_etree_or_element)

        self._lock()
        self._error_log.connect()
        self._xpathCtxt.doc  = document._c_doc
        self._xpathCtxt.node = element._c_node

        try:
            self._context.register_context(document)
            self._context.registerVariables(_variables)
            with nogil:
                xpathObj = xpath.xmlXPathCompiledEval(
                    self._xpath, self._xpathCtxt)
            result = self._handle_result(xpathObj, document)
        finally:
            self._error_log.disconnect()
            self._context.unregister_context()
            self._unlock()
        return result

    def __dealloc__(self):
        if self._xpath is not NULL:
            xpath.xmlXPathFreeCompExpr(self._xpath)

    def __repr__(self):
        return self.path


cdef object _replace_strings
cdef object _find_namespaces
_replace_strings = re.compile('("[^"]*")|(\'[^\']*\')').sub
_find_namespaces = re.compile('({[^}]+})').findall

cdef class ETXPath(XPath):
    """ETXPath(self, path, extensions=None, regexp=True)
    Special XPath class that supports the ElementTree {uri} notation for namespaces.

    Note that this class does not accept the ``namespace`` keyword
    argument. All namespaces must be passed as part of the path string.
    """
    def __init__(self, path, *, extensions=None, regexp=True):
        path, namespaces = self._nsextract_path(path)
        XPath.__init__(self, path, namespaces=namespaces,
                       extensions=extensions, regexp=regexp)

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
                prefix = python.PyString_FromFormat("__xpp%02d", i)
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
