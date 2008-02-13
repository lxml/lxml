# support for extension functions in XPath and XSLT

class XPathError(LxmlError):
    """Base class of all XPath errors.
    """
    pass

class XPathEvalError(XPathError):
    """Error during XPath evaluation.
    """
    pass

class XPathFunctionError(XPathEvalError):
    """Internal error looking up an XPath extension function.
    """
    pass

class XPathResultError(XPathEvalError):
    """Error handling an XPath result.
    """
    pass

# forward declarations

ctypedef int (*_register_function)(void* ctxt, name_utf, ns_uri_utf)
cdef class _ExsltRegExp

################################################################################
# Base class for XSLT and XPath evaluation contexts: functions, namespaces, ...

cdef class _BaseContext:
    cdef xpath.xmlXPathContext* _xpathCtxt
    cdef _Document _doc
    cdef object _extensions
    cdef object _namespaces
    cdef object _global_namespaces
    cdef object _utf_refs
    cdef object _function_cache
    cdef object _eval_context_dict
    # for exception handling and temporary reference keeping:
    cdef _TempStore _temp_refs
    cdef _ExceptionContext _exc

    def __init__(self, namespaces, extensions, enable_regexp):
        cdef _ExsltRegExp _regexp 
        self._utf_refs = {}
        self._global_namespaces = []
        self._function_cache = {}
        self._eval_context_dict = None

        if extensions is not None:
            # convert extensions to UTF-8
            if python.PyDict_Check(extensions):
                extensions = (extensions,)
            # format: [ {(ns, name):function} ] -> {(ns_utf, name_utf):function}
            new_extensions = {}
            for extension in extensions:
                for (ns_uri, name), function in extension.items():
                    if name is None:
                        raise ValueError(
                            "extensions must have non empty names")
                    ns_utf   = self._to_utf(ns_uri)
                    name_utf = self._to_utf(name)
                    python.PyDict_SetItem(
                        new_extensions, (ns_utf, name_utf), function)
            extensions = new_extensions or None

        if namespaces is not None:
            if python.PyDict_Check(namespaces):
                namespaces = namespaces.items()
            if namespaces:
                ns = []
                for prefix, ns_uri in namespaces:
                    if prefix is None or not prefix:
                        raise TypeError(
                            "empty namespace prefix is not supported in XPath")
                    if ns_uri is None or not ns_uri:
                        raise TypeError(
                            "setting default namespace is not supported in XPath")
                    prefix_utf = self._to_utf(prefix)
                    ns_uri_utf = self._to_utf(ns_uri)
                    python.PyList_Append(ns, (prefix_utf, ns_uri_utf))
                namespaces = ns
            else:
                namespaces = None

        self._doc        = None
        self._exc        = _ExceptionContext()
        self._extensions = extensions
        self._namespaces = namespaces
        self._temp_refs  = _TempStore()

        if enable_regexp:
            _regexp = _ExsltRegExp()
            _regexp._register_in_context(self)

    cdef _BaseContext _copy(self):
        cdef _BaseContext context
        if self._namespaces is not None:
            namespaces = self._namespaces[:]
        context = self.__class__(namespaces, None, False)
        if self._extensions is not None:
            context._extensions = python.PyDict_Copy(self._extensions)
        return context

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

    cdef _register_context(self, _Document doc):
        self._doc = doc
        self._exc.clear()

    cdef _cleanup_context(self):
        #xpath.xmlXPathRegisteredNsCleanup(self._xpathCtxt)
        #self.unregisterGlobalNamespaces()
        python.PyDict_Clear(self._utf_refs)
        self._eval_context_dict = None
        self._doc = None

    cdef _release_context(self):
        if self._xpathCtxt is not NULL:
            self._xpathCtxt.userData = NULL
            self._xpathCtxt = NULL

    # namespaces (internal UTF-8 methods with leading '_')

    cdef addNamespace(self, prefix, ns_uri):
        if prefix is None:
            raise TypeError("empty prefix is not supported in XPath")
        prefix_utf = self._to_utf(prefix)
        ns_uri_utf = self._to_utf(ns_uri)
        new_item = (prefix_utf, ns_uri_utf)
        if self._namespaces is None:
            self._namespaces = [new_item]
        else:
            namespaces = []
            for item in self._namespaces:
                if item[0] == prefix_utf:
                    item = new_item
                    new_item = None
                python.PyList_Append(namespaces, item)
            if new_item is not None:
                python.PyList_Append(namespaces, new_item)
            self._namespaces = namespaces
        if self._xpathCtxt is not NULL:
            xpath.xmlXPathRegisterNs(
                self._xpathCtxt, _cstr(prefix_utf), _cstr(ns_uri_utf))

    cdef registerNamespace(self, prefix, ns_uri):
        if prefix is None:
            raise TypeError("empty prefix is not supported in XPath")
        prefix_utf = self._to_utf(prefix)
        ns_uri_utf = self._to_utf(ns_uri)
        python.PyList_Append(self._global_namespaces, prefix_utf)
        xpath.xmlXPathRegisterNs(self._xpathCtxt,
                                 _cstr(prefix_utf), _cstr(ns_uri_utf))

    cdef registerLocalNamespaces(self):
        if self._namespaces is None:
            return
        for prefix_utf, ns_uri_utf in self._namespaces:
            xpath.xmlXPathRegisterNs(
                self._xpathCtxt, _cstr(prefix_utf), _cstr(ns_uri_utf))

    cdef registerGlobalNamespaces(self):
        ns_prefixes = _find_all_extension_prefixes()
        if python.PyList_GET_SIZE(ns_prefixes) > 0:
            for prefix_utf, ns_uri_utf in ns_prefixes:
                python.PyList_Append(self._global_namespaces, prefix_utf)
                xpath.xmlXPathRegisterNs(
                    self._xpathCtxt, _cstr(prefix_utf), _cstr(ns_uri_utf))

    cdef unregisterGlobalNamespaces(self):
        if python.PyList_GET_SIZE(self._global_namespaces) > 0:
            for prefix_utf in self._global_namespaces:
                xpath.xmlXPathRegisterNs(self._xpathCtxt,
                                         _cstr(prefix_utf), NULL)
            del self._global_namespaces[:]
    
    cdef void _unregisterNamespace(self, prefix_utf):
        xpath.xmlXPathRegisterNs(self._xpathCtxt,
                                 _cstr(prefix_utf), NULL)
    
    # extension functions

    cdef void _addLocalExtensionFunction(self, ns_utf, name_utf, function):
        if self._extensions is None:
            self._extensions = {}
        python.PyDict_SetItem(self._extensions, (ns_utf, name_utf), function)

    cdef void registerGlobalFunctions(self, void* ctxt,
                                    _register_function reg_func):
        cdef python.PyObject* dict_result
        for ns_utf, ns_functions in _iter_ns_extension_functions():
            dict_result = python.PyDict_GetItem(
                self._function_cache, ns_utf)
            if dict_result is not NULL:
                d = <object>dict_result
            else:
                d = {}
                python.PyDict_SetItem(
                    self._function_cache, ns_utf, d)
            for name_utf, function in ns_functions.iteritems():
                python.PyDict_SetItem(d, name_utf, function)
                reg_func(ctxt, name_utf, ns_utf)

    cdef void registerLocalFunctions(self, void* ctxt,
                                      _register_function reg_func):
        cdef python.PyObject* dict_result
        if self._extensions is None:
            return # done
        last_ns = None
        d = None
        for (ns_utf, name_utf), function in self._extensions.iteritems():
            if ns_utf is not last_ns or d is None:
                last_ns = ns_utf
                dict_result = python.PyDict_GetItem(
                    self._function_cache, ns_utf)
                if dict_result is not NULL:
                    d = <object>dict_result
                else:
                    d = {}
                    python.PyDict_SetItem(self._function_cache,
                                          ns_utf, d)
            python.PyDict_SetItem(d, name_utf, function)
            reg_func(ctxt, name_utf, ns_utf)

    cdef unregisterAllFunctions(self, void* ctxt,
                                      _register_function unreg_func):
        for ns_utf, functions in self._function_cache.iteritems():
            for name_utf in functions:
                unreg_func(ctxt, name_utf, ns_utf)

    cdef unregisterGlobalFunctions(self, void* ctxt,
                                         _register_function unreg_func):
        for ns_utf, functions in self._function_cache.iteritems():
            for name_utf in functions:
                if self._extensions is None or \
                       (ns_utf, name_utf) not in self._extensions:
                    unreg_func(ctxt, name_utf, ns_utf)

    cdef _find_cached_function(self, char* c_ns_uri, char* c_name):
        """Lookup an extension function in the cache and return it.

        Parameters: c_ns_uri may be NULL, c_name must not be NULL
        """
        cdef python.PyObject* c_dict
        cdef python.PyObject* dict_result
        if c_ns_uri is NULL:
            c_dict = python.PyDict_GetItem(
                self._function_cache, None)
        else:
            c_dict = python.PyDict_GetItemString(
                self._function_cache, c_ns_uri)

        if c_dict is not NULL:
            dict_result = python.PyDict_GetItemString(
                <object>c_dict, c_name)
            if dict_result is not NULL:
                return <object>dict_result
        return None

    # Python access to the XPath context for extension functions

    property context_node:
        def __get__(self):
            cdef xmlNode* c_node
            if self._xpathCtxt is NULL:
                raise XPathError(
                    "XPath context is only usable during the evaluation")
            c_node = self._xpathCtxt.node
            if c_node is NULL:
                raise XPathError("no context node")
            if c_node.doc != self._xpathCtxt.doc:
                raise XPathError(
                    "document-external context nodes are not supported")
            if self._doc is None:
                raise XPathError(
                      "document context is missing")
            return _elementFactory(self._doc, c_node)

    property eval_context:
        def __get__(self):
            if self._eval_context_dict is None:
                self._eval_context_dict = {}
            return self._eval_context_dict

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
        cdef _Element element
        if isinstance(obj, _Element):
            self._temp_refs.add(obj)
            self._temp_refs.add((<_Element>obj)._doc)
            return
        elif _isString(obj) or not python.PySequence_Check(obj):
            return
        for o in obj:
            if isinstance(o, _Element):
                #print "Holding element:", <int>element._c_node
                self._temp_refs.add(o)
                #print "Holding document:", <int>element._doc._c_doc
                self._temp_refs.add((<_Element>o)._doc)

def Extension(module, function_mapping=None, *, ns=None):
    """Extension(module, function_mapping=None, ns=None)

    Build a dictionary of extension functions from the functions
    defined in a module or the methods of an object.

    As second argument, you can pass an additional mapping of
    attribute names to XPath function names, or a list of function
    names that should be taken.

    The ``ns`` keyword argument accepts a namespace URI for the XPath
    functions.
    """
    functions = {}
    if python.PyDict_Check(function_mapping):
        for function_name, xpath_name in function_mapping.items():
            python.PyDict_SetItem(functions, (ns, xpath_name),
                                  getattr(module, function_name))
    else:
        if function_mapping is None:
            function_mapping = [ name for name in dir(module)
                                 if not name.startswith('_') ]
        for function_name in function_mapping:
            python.PyDict_SetItem(functions, (ns, function_name),
                                  getattr(module, function_name))
    return functions

################################################################################
# EXSLT regexp implementation

cdef class _ExsltRegExp:
    cdef object _compile_map
    def __init__(self):
        self._compile_map = {}

    cdef _make_string(self, value):
        cdef char* c_text
        if _isString(value):
            return value
        elif python.PyList_Check(value):
            # node set: take recursive text concatenation of first element
            if python.PyList_GET_SIZE(value) == 0:
                return ''
            firstnode = value[0]
            if _isString(firstnode):
                return firstnode
            elif isinstance(firstnode, _Element):
                c_text = tree.xmlNodeGetContent((<_Element>firstnode)._c_node)
                if c_text is NULL:
                    python.PyErr_NoMemory()
                try:
                    s = funicode(c_text)
                finally:
                    tree.xmlFree(c_text)
                return s
            else:
                return str(firstnode)
        else:
            return str(value)

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

    cdef _register_in_context(self, _BaseContext context):
        ns = "http://exslt.org/regular-expressions"
        context._addLocalExtensionFunction(ns, "test",    self.test)
        context._addLocalExtensionFunction(ns, "match",   self.match)
        context._addLocalExtensionFunction(ns, "replace", self.replace)


################################################################################
# helper functions

cdef xpath.xmlXPathObject* _wrapXPathObject(object obj) except NULL:
    cdef xpath.xmlNodeSet* resultSet
    cdef _Element node
    if python.PyUnicode_Check(obj):
        obj = _utf8(obj)
    if python.PyString_Check(obj):
        return xpath.xmlXPathNewCString(_cstr(obj))
    if python.PyBool_Check(obj):
        return xpath.xmlXPathNewBoolean(obj)
    if python.PyNumber_Check(obj):
        return xpath.xmlXPathNewFloat(obj)
    if obj is None:
        resultSet = xpath.xmlXPathNodeSetCreate(NULL)
    elif isinstance(obj, _Element):
        resultSet = xpath.xmlXPathNodeSetCreate((<_Element>obj)._c_node)
    elif python.PySequence_Check(obj):
        resultSet = xpath.xmlXPathNodeSetCreate(NULL)
        for element in obj:
            if isinstance(element, _Element):
                node = <_Element>element
                xpath.xmlXPathNodeSetAdd(resultSet, node._c_node)
            else:
                xpath.xmlXPathFreeNodeSet(resultSet)
                raise XPathResultError("This is not a node: %r" % element)
    else:
        raise XPathResultError("Unknown return type: %s" % type(obj))
    return xpath.xmlXPathWrapNodeSet(resultSet)

cdef object _unwrapXPathObject(xpath.xmlXPathObject* xpathObj,
                               _Document doc):
    if xpathObj.type == xpath.XPATH_UNDEFINED:
        raise XPathResultError("Undefined xpath result")
    elif xpathObj.type == xpath.XPATH_NODESET:
        return _createNodeSetResult(xpathObj, doc)
    elif xpathObj.type == xpath.XPATH_BOOLEAN:
        return python.PyBool_FromLong(xpathObj.boolval)
    elif xpathObj.type == xpath.XPATH_NUMBER:
        return xpathObj.floatval
    elif xpathObj.type == xpath.XPATH_STRING:
        return _elementStringResultFactory(
            funicode(xpathObj.stringval), None, 0, 0)
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
        raise XPathResultError("Unknown xpath result %s" % str(xpathObj.type))

cdef object _createNodeSetResult(xpath.xmlXPathObject* xpathObj, _Document doc):
    cdef xmlNode* c_node
    cdef char* s
    cdef int i
    result = []
    if xpathObj.nodesetval is NULL:
        return result
    for i from 0 <= i < xpathObj.nodesetval.nodeNr:
        c_node = xpathObj.nodesetval.nodeTab[i]
        if _isElement(c_node):
            if c_node.doc != doc._c_doc and c_node.doc._private is NULL:
                # XXX: works, but maybe not always the right thing to do?
                # XPath: only runs when extensions create or copy trees
                #        -> we store Python refs to these, so that is OK
                # XSLT: can it leak when merging trees from multiple sources?
                c_node = tree.xmlDocCopyNode(c_node, doc._c_doc, 1)
            value = _fakeDocElementFactory(doc, c_node)
        elif c_node.type == tree.XML_TEXT_NODE or \
                c_node.type == tree.XML_ATTRIBUTE_NODE:
            value = _buildElementStringResult(doc, c_node)
        elif c_node.type == tree.XML_NAMESPACE_DECL:
            s = (<xmlNs*>c_node).href
            if s is NULL:
                href = None
            else:
                href = s
            s = (<xmlNs*>c_node).prefix
            if s is NULL:
                prefix = None
            else:
                prefix = s
            value = (prefix, href)
        elif c_node.type == tree.XML_DOCUMENT_NODE or \
                 c_node.type == tree.XML_HTML_DOCUMENT_NODE or \
                 c_node.type == tree.XML_XINCLUDE_START or \
                 c_node.type == tree.XML_XINCLUDE_END:
            continue
        else:
            raise NotImplementedError(
                "Not yet implemented result node type: %d" % c_node.type)
        python.PyList_Append(result, value)
    return result

cdef void _freeXPathObject(xpath.xmlXPathObject* xpathObj):
    """Free the XPath object, but *never* free the *content* of node sets.
    Python dealloc will do that for us.
    """
    if xpathObj.nodesetval is not NULL:
        xpath.xmlXPathFreeNodeSet(xpathObj.nodesetval)
        xpathObj.nodesetval = NULL
    xpath.xmlXPathFreeObject(xpathObj)

################################################################################
# special str/unicode subclasses

cdef class _ElementUnicodeResult(python.unicode):
    cdef _Element parent
    cdef readonly object is_tail
    cdef readonly object is_text
    cdef readonly object is_attribute

    def getparent(self):
        return self.parent

class _ElementStringResult(str):
    # we need to use a Python class here, str cannot be C-subclassed
    # in Pyrex/Cython
    def getparent(self):
        return self._parent

cdef object _elementStringResultFactory(string_value, _Element parent,
                                        bint is_attribute, bint is_tail):
    cdef _ElementUnicodeResult uresult
    cdef bint is_text
    if parent is None:
        is_text = 0
    else:
        is_text = not (is_tail or is_attribute)

    if python.PyString_CheckExact(string_value):
        result = _ElementStringResult(string_value)
        result._parent = parent
        result.is_attribute = is_attribute
        result.is_tail = is_tail
        result.is_text = is_text
        return result
    else:
        uresult = _ElementUnicodeResult(string_value)
        uresult.parent = parent
        uresult.is_attribute = is_attribute
        uresult.is_tail = is_tail
        uresult.is_text = is_text
        return uresult

cdef object _buildElementStringResult(_Document doc, xmlNode* c_node):
    cdef _Element parent
    cdef xmlNode* c_element
    cdef char* s
    cdef bint is_attribute, is_text, is_tail

    if c_node.type == tree.XML_ATTRIBUTE_NODE:
        is_attribute = 1
        is_tail = 0
        s = tree.xmlNodeGetContent(c_node)
        try:
            value = funicode(s)
        finally:
            tree.xmlFree(s)
        c_element = NULL
    else:
        #assert c_node.type == tree.XML_TEXT_NODE, "invalid node type"
        is_attribute = 0
        # may be tail text or normal text
        value = funicode(c_node.content)
        c_element = _previousElement(c_node)
        is_tail = c_element is not NULL

    if c_element is NULL:
        # non-tail text or attribute text
        c_element = c_node.parent
        while c_element is not NULL and not _isElement(c_element):
            c_element = c_element.parent

    if c_element is not NULL:
        parent = _fakeDocElementFactory(doc, c_element)

    return _elementStringResultFactory(
        value, parent, is_attribute, is_tail)


################################################################################
# callbacks for XPath/XSLT extension functions

cdef void _extension_function_call(_BaseContext context, function,
                                   xpath.xmlXPathParserContext* ctxt, int nargs):
    cdef _Document doc
    cdef xpath.xmlXPathObject* obj
    cdef int i
    doc = context._doc
    try:
        args = []
        for i from 0 <= i < nargs:
            obj = xpath.valuePop(ctxt)
            o = _unwrapXPathObject(obj, doc)
            _freeXPathObject(obj)
            python.PyList_Append(args, o)
        python.PyList_Reverse(args)

        res = function(context, *args)
        # wrap result for XPath consumption
        obj = _wrapXPathObject(res)
        # prevent Python from deallocating elements handed to libxml2
        context._hold(res)
        xpath.valuePush(ctxt, obj)
    except:
        xpath.xmlXPathErr(ctxt, xpath.XPATH_EXPR_ERROR)
        context._exc._store_raised()

# lookup the function by name and call it

cdef void _xpath_function_call(xpath.xmlXPathParserContext* ctxt,
                               int nargs) with gil:
    cdef xpath.xmlXPathContext* rctxt
    cdef _BaseContext context
    rctxt = ctxt.context
    context = <_BaseContext>(rctxt.userData)
    function = context._find_cached_function(rctxt.functionURI, rctxt.function)
    if function is not None:
        _extension_function_call(context, function, ctxt, nargs)
    else:
        if rctxt.functionURI is not NULL:
            fref = "{%s}%s" % (rctxt.functionURI, rctxt.function)
        else:
            fref = rctxt.function
        xpath.xmlXPathErr(ctxt, xpath.XPATH_UNKNOWN_FUNC_ERROR)
        exception = XPathFunctionError("XPath function '%s' not found" % fref)
        context._exc._store_exception(exception)
