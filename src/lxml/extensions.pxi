# support for extension functions in XPath and XSLT

class XPathError(LxmlError):
    u"""Base class of all XPath errors.
    """
    pass

class XPathEvalError(XPathError):
    u"""Error during XPath evaluation.
    """
    pass

class XPathFunctionError(XPathEvalError):
    u"""Internal error looking up an XPath extension function.
    """
    pass

class XPathResultError(XPathEvalError):
    u"""Error handling an XPath result.
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
    cdef dict _extensions
    cdef list _namespaces
    cdef list _global_namespaces
    cdef dict _utf_refs
    cdef dict _function_cache
    cdef dict _eval_context_dict
    cdef bint _build_smart_strings
    # for exception handling and temporary reference keeping:
    cdef _TempStore _temp_refs
    cdef set _temp_documents
    cdef _ExceptionContext _exc
    def __cinit__(self):
        self._xpathCtxt = NULL

    def __init__(self, namespaces, extensions, enable_regexp,
                 build_smart_strings):
        cdef _ExsltRegExp _regexp 
        cdef dict new_extensions
        cdef list ns
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
                        raise ValueError, u"extensions must have non empty names"
                    ns_utf   = self._to_utf(ns_uri)
                    name_utf = self._to_utf(name)
                    new_extensions[(ns_utf, name_utf)] = function
            extensions = new_extensions or None

        if namespaces is not None:
            if python.PyDict_Check(namespaces):
                namespaces = namespaces.items()
            if namespaces:
                ns = []
                for prefix, ns_uri in namespaces:
                    if prefix is None or not prefix:
                        raise TypeError, \
                            u"empty namespace prefix is not supported in XPath"
                    if ns_uri is None or not ns_uri:
                        raise TypeError, \
                            u"setting default namespace is not supported in XPath"
                    prefix_utf = self._to_utf(prefix)
                    ns_uri_utf = self._to_utf(ns_uri)
                    ns.append( (prefix_utf, ns_uri_utf) )
                namespaces = ns
            else:
                namespaces = None

        self._doc        = None
        self._exc        = _ExceptionContext()
        self._extensions = extensions
        self._namespaces = namespaces
        self._temp_refs  = _TempStore()
        self._temp_documents  = set()
        self._build_smart_strings = build_smart_strings

        if enable_regexp:
            _regexp = _ExsltRegExp()
            _regexp._register_in_context(self)

    cdef _BaseContext _copy(self):
        cdef _BaseContext context
        if self._namespaces is not None:
            namespaces = self._namespaces[:]
        context = self.__class__(namespaces, None, False,
                                 self._build_smart_strings)
        if self._extensions is not None:
            context._extensions = self._extensions.copy()
        return context

    cdef object _to_utf(self, s):
        u"Convert to UTF-8 and keep a reference to the encoded string"
        cdef python.PyObject* dict_result
        if s is None:
            return None
        dict_result = python.PyDict_GetItem(self._utf_refs, s)
        if dict_result is not NULL:
            return <object>dict_result
        utf = _utf8(s)
        self._utf_refs[s] = utf
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
        cdef list namespaces
        if prefix is None:
            raise TypeError, u"empty prefix is not supported in XPath"
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
                namespaces.append(item)
            if new_item is not None:
                namespaces.append(new_item)
            self._namespaces = namespaces
        if self._xpathCtxt is not NULL:
            xpath.xmlXPathRegisterNs(
                self._xpathCtxt, _cstr(prefix_utf), _cstr(ns_uri_utf))

    cdef registerNamespace(self, prefix, ns_uri):
        if prefix is None:
            raise TypeError, u"empty prefix is not supported in XPath"
        prefix_utf = self._to_utf(prefix)
        ns_uri_utf = self._to_utf(ns_uri)
        self._global_namespaces.append(prefix_utf)
        xpath.xmlXPathRegisterNs(self._xpathCtxt,
                                 _cstr(prefix_utf), _cstr(ns_uri_utf))

    cdef registerLocalNamespaces(self):
        if self._namespaces is None:
            return
        for prefix_utf, ns_uri_utf in self._namespaces:
            xpath.xmlXPathRegisterNs(
                self._xpathCtxt, _cstr(prefix_utf), _cstr(ns_uri_utf))

    cdef registerGlobalNamespaces(self):
        cdef list ns_prefixes = _find_all_extension_prefixes()
        if python.PyList_GET_SIZE(ns_prefixes) > 0:
            for prefix_utf, ns_uri_utf in ns_prefixes:
                self._global_namespaces.append(prefix_utf)
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
        self._extensions[(ns_utf, name_utf)] = function

    cdef void registerGlobalFunctions(self, void* ctxt,
                                      _register_function reg_func):
        cdef python.PyObject* dict_result
        cdef dict d
        for ns_utf, ns_functions in __FUNCTION_NAMESPACE_REGISTRIES.iteritems():
            dict_result = python.PyDict_GetItem(
                self._function_cache, ns_utf)
            if dict_result is not NULL:
                d = <dict>dict_result
            else:
                d = {}
                self._function_cache[ns_utf] = d
            for name_utf, function in ns_functions.iteritems():
                d[name_utf] = function
                reg_func(ctxt, name_utf, ns_utf)

    cdef void registerLocalFunctions(self, void* ctxt,
                                      _register_function reg_func):
        cdef python.PyObject* dict_result
        cdef dict d
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
                    d = <dict>dict_result
                else:
                    d = {}
                    self._function_cache[ns_utf] = d
            d[name_utf] = function
            reg_func(ctxt, name_utf, ns_utf)

    cdef unregisterAllFunctions(self, void* ctxt,
                                      _register_function unreg_func):
        for ns_utf, functions in self._function_cache.iteritems():
            for name_utf in functions:
                unreg_func(ctxt, name_utf, ns_utf)

    cdef unregisterGlobalFunctions(self, void* ctxt,
                                         _register_function unreg_func):
        for ns_utf, functions in self._function_cache.items():
            for name_utf in functions:
                if self._extensions is None or \
                       (ns_utf, name_utf) not in self._extensions:
                    unreg_func(ctxt, name_utf, ns_utf)

    cdef _find_cached_function(self, char* c_ns_uri, char* c_name):
        u"""Lookup an extension function in the cache and return it.

        Parameters: c_ns_uri may be NULL, c_name must not be NULL
        """
        cdef python.PyObject* c_dict
        cdef python.PyObject* dict_result
        if c_ns_uri is NULL:
            c_dict = python.PyDict_GetItem(
                self._function_cache, None)
        else:
            c_dict = python.PyDict_GetItem(
                self._function_cache, c_ns_uri)

        if c_dict is not NULL:
            dict_result = python.PyDict_GetItem(
                <object>c_dict, c_name)
            if dict_result is not NULL:
                return <object>dict_result
        return None

    # Python access to the XPath context for extension functions

    property context_node:
        def __get__(self):
            cdef xmlNode* c_node
            if self._xpathCtxt is NULL:
                raise XPathError, \
                    u"XPath context is only usable during the evaluation"
            c_node = self._xpathCtxt.node
            if c_node is NULL:
                raise XPathError, u"no context node"
            if c_node.doc != self._xpathCtxt.doc:
                raise XPathError, \
                    u"document-external context nodes are not supported"
            if self._doc is None:
                raise XPathError, u"document context is missing"
            return _elementFactory(self._doc, c_node)

    property eval_context:
        def __get__(self):
            if self._eval_context_dict is None:
                self._eval_context_dict = {}
            return self._eval_context_dict

    # Python reference keeping during XPath function evaluation

    cdef _release_temp_refs(self):
        u"Free temporarily referenced objects from this context."
        self._temp_refs.clear()
        self._temp_documents.clear()

    cdef _hold(self, obj):
        u"""A way to temporarily hold references to nodes in the evaluator.

        This is needed because otherwise nodes created in XPath extension
        functions would be reference counted too soon, during the XPath
        evaluation.  This is most important in the case of exceptions.
        """
        cdef _Element element
        if isinstance(obj, _Element):
            self._temp_refs.add(obj)
            self._temp_documents.add((<_Element>obj)._doc)
            return
        elif _isString(obj) or not python.PySequence_Check(obj):
            return
        for o in obj:
            if isinstance(o, _Element):
                #print "Holding element:", <int>element._c_node
                self._temp_refs.add(o)
                #print "Holding document:", <int>element._doc._c_doc
                self._temp_documents.add((<_Element>o)._doc)

    cdef _Document _findDocumentForNode(self, xmlNode* c_node):
        u"""If an XPath expression returns an element from a different
        document than the current context document, we call this to
        see if it was possibly created by an extension and is a known
        document instance.
        """
        cdef _Document doc
        for doc in self._temp_documents:
            if doc is not None and doc._c_doc is c_node.doc:
                return doc
        return None

def Extension(module, function_mapping=None, *, ns=None):
    u"""Extension(module, function_mapping=None, ns=None)

    Build a dictionary of extension functions from the functions
    defined in a module or the methods of an object.

    As second argument, you can pass an additional mapping of
    attribute names to XPath function names, or a list of function
    names that should be taken.

    The ``ns`` keyword argument accepts a namespace URI for the XPath
    functions.
    """
    cdef dict functions = {}
    if python.PyDict_Check(function_mapping):
        for function_name, xpath_name in function_mapping.items():
            functions[(ns, xpath_name)] = getattr(module, function_name)
    else:
        if function_mapping is None:
            function_mapping = [ name for name in dir(module)
                                 if not name.startswith(u'_') ]
        for function_name in function_mapping:
            functions[(ns, function_name)] = getattr(module, function_name)
    return functions

################################################################################
# EXSLT regexp implementation

cdef class _ExsltRegExp:
    cdef dict _compile_map
    def __cinit__(self):
        self._compile_map = {}

    cdef _make_string(self, value):
        cdef char* c_text
        if _isString(value):
            return value
        elif python.PyList_Check(value):
            # node set: take recursive text concatenation of first element
            if python.PyList_GET_SIZE(value) == 0:
                return u''
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
                return unicode(firstnode)
        else:
            return unicode(value)

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
        self._compile_map[key] = rexp_compiled
        return rexp_compiled

    def test(self, ctxt, s, rexp, flags=u''):
        flags = self._make_string(flags)
        s = self._make_string(s)
        rexpc = self._compile(rexp, u'i' in flags)
        if rexpc.search(s) is None:
            return False
        else:
            return True

    def match(self, ctxt, s, rexp, flags=u''):
        cdef list result_list
        flags = self._make_string(flags)
        s = self._make_string(s)
        rexpc = self._compile(rexp, u'i' in flags)
        if u'g' in flags:
            results = rexpc.findall(s)
            if not results:
                return ()
        else:
            result = rexpc.search(s)
            if not result:
                return ()
            results = [ result.group() ]
            results.extend( result.groups(u'') )
        result_list = []
        root = Element(u'matches')
        join_groups = u''.join
        for s_match in results:
            if python.PyTuple_CheckExact(s_match):
                s_match = join_groups(s_match)
            elem = SubElement(root, u'match')
            elem.text = s_match
            result_list.append(elem)
        return result_list

    def replace(self, ctxt, s, rexp, flags, replacement):
        replacement = self._make_string(replacement)
        flags = self._make_string(flags)
        s = self._make_string(s)
        rexpc = self._compile(rexp, u'i' in flags)
        if u'g' in flags:
            count = 0
        else:
            count = 1
        return rexpc.sub(replacement, s, count)

    cdef _register_in_context(self, _BaseContext context):
        ns = b"http://exslt.org/regular-expressions"
        context._addLocalExtensionFunction(ns, b"test",    self.test)
        context._addLocalExtensionFunction(ns, b"match",   self.match)
        context._addLocalExtensionFunction(ns, b"replace", self.replace)


################################################################################
# helper functions

cdef xpath.xmlXPathObject* _wrapXPathObject(object obj, _Document doc,
                                            _BaseContext context) except NULL:
    cdef xpath.xmlNodeSet* resultSet
    cdef _Element fake_node = None
    cdef xmlNode* c_node

    if python.PyUnicode_Check(obj):
        obj = _utf8(obj)
    if python.PyBytes_Check(obj):
        # libxml2 copies the string value
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
        try:
            for value in obj:
                if isinstance(value, _Element):
                    if context is not None:
                        context._hold(value)
                    xpath.xmlXPathNodeSetAdd(resultSet, (<_Element>value)._c_node)
                else:
                    if context is None or doc is None:
                        raise XPathResultError, \
                              u"Non-Element values not supported at this point - got %r" % value
                    # support strings by appending text nodes to an Element
                    if python.PyUnicode_Check(value):
                        value = _utf8(value)
                    if python.PyBytes_Check(value):
                        if fake_node is None:
                            fake_node = _makeElement("text-root", NULL, doc, None,
                                                     None, None, None, None, None)
                            context._hold(fake_node)
                        else:
                            # append a comment node to keep the text nodes separate
                            c_node = tree.xmlNewDocComment(doc._c_doc, "")
                            if c_node is NULL:
                                python.PyErr_NoMemory()
                            tree.xmlAddChild(fake_node._c_node, c_node)
                        context._hold(value)
                        c_node = tree.xmlNewDocText(doc._c_doc, _cstr(value))
                        if c_node is NULL:
                            python.PyErr_NoMemory()
                        tree.xmlAddChild(fake_node._c_node, c_node)
                        xpath.xmlXPathNodeSetAdd(resultSet, c_node)
                    else:
                        raise XPathResultError, \
                              u"This is not a supported node-set result: %r" % value
        except:
            xpath.xmlXPathFreeNodeSet(resultSet)
            raise
    else:
        raise XPathResultError, u"Unknown return type: %s" % \
            python._fqtypename(obj)
    return xpath.xmlXPathWrapNodeSet(resultSet)

cdef object _unwrapXPathObject(xpath.xmlXPathObject* xpathObj,
                               _Document doc, _BaseContext context):
    if xpathObj.type == xpath.XPATH_UNDEFINED:
        raise XPathResultError, u"Undefined xpath result"
    elif xpathObj.type == xpath.XPATH_NODESET:
        return _createNodeSetResult(xpathObj, doc, context)
    elif xpathObj.type == xpath.XPATH_BOOLEAN:
        return xpathObj.boolval
    elif xpathObj.type == xpath.XPATH_NUMBER:
        return xpathObj.floatval
    elif xpathObj.type == xpath.XPATH_STRING:
        stringval = funicode(xpathObj.stringval)
        if context._build_smart_strings:
            stringval = _elementStringResultFactory(
                stringval, None, None, 0)
        return stringval
    elif xpathObj.type == xpath.XPATH_POINT:
        raise NotImplementedError, u"XPATH_POINT"
    elif xpathObj.type == xpath.XPATH_RANGE:
        raise NotImplementedError, u"XPATH_RANGE"
    elif xpathObj.type == xpath.XPATH_LOCATIONSET:
        raise NotImplementedError, u"XPATH_LOCATIONSET"
    elif xpathObj.type == xpath.XPATH_USERS:
        raise NotImplementedError, u"XPATH_USERS"
    elif xpathObj.type == xpath.XPATH_XSLT_TREE:
        return _createNodeSetResult(xpathObj, doc, context)
    else:
        raise XPathResultError, u"Unknown xpath result %s" % unicode(xpathObj.type)

cdef object _createNodeSetResult(xpath.xmlXPathObject* xpathObj, _Document doc,
                                 _BaseContext context):
    cdef xmlNode* c_node
    cdef int i
    cdef list result
    result = []
    if xpathObj.nodesetval is NULL:
        return result
    for i in range(xpathObj.nodesetval.nodeNr):
        c_node = xpathObj.nodesetval.nodeTab[i]
        _unpackNodeSetEntry(result, c_node, doc, context,
                            xpathObj.type == xpath.XPATH_XSLT_TREE)
    return result

cdef _unpackNodeSetEntry(list results, xmlNode* c_node, _Document doc,
                         _BaseContext context, bint is_fragment):
    cdef xmlNode* c_child
    cdef char* s
    if _isElement(c_node):
        if c_node.doc != doc._c_doc and c_node.doc._private is NULL:
            # XXX: works, but maybe not always the right thing to do?
            # XPath: only runs when extensions create or copy trees
            #        -> we store Python refs to these, so that is OK
            # XSLT: can it leak when merging trees from multiple sources?
            c_node = tree.xmlDocCopyNode(c_node, doc._c_doc, 1)
            # FIXME: call _instantiateElementFromXPath() instead?
        results.append(
            _fakeDocElementFactory(doc, c_node))
    elif c_node.type == tree.XML_TEXT_NODE or \
             c_node.type == tree.XML_CDATA_SECTION_NODE or \
             c_node.type == tree.XML_ATTRIBUTE_NODE:
        results.append(
            _buildElementStringResult(doc, c_node, context))
    elif c_node.type == tree.XML_NAMESPACE_DECL:
        s = (<xmlNs*>c_node).href
        if s is NULL:
            href = None
        else:
            href = funicode(s)
        s = (<xmlNs*>c_node).prefix
        if s is NULL:
            prefix = None
        else:
            prefix = funicode(s)
        results.append( (prefix, href) )
    elif c_node.type == tree.XML_DOCUMENT_NODE or \
            c_node.type == tree.XML_HTML_DOCUMENT_NODE:
        # ignored for everything but result tree fragments
        if is_fragment:
            c_child = c_node.children
            while c_child is not NULL:
                _unpackNodeSetEntry(results, c_child, doc, context, 0)
                c_child = c_child.next
    elif c_node.type == tree.XML_XINCLUDE_START or \
            c_node.type == tree.XML_XINCLUDE_END:
        pass
    else:
        raise NotImplementedError, \
            u"Not yet implemented result node type: %d" % c_node.type

cdef void _freeXPathObject(xpath.xmlXPathObject* xpathObj):
    u"""Free the XPath object, but *never* free the *content* of node sets.
    Python dealloc will do that for us.
    """
    if xpathObj.nodesetval is not NULL:
        xpath.xmlXPathFreeNodeSet(xpathObj.nodesetval)
        xpathObj.nodesetval = NULL
    xpath.xmlXPathFreeObject(xpathObj)

cdef _Element _instantiateElementFromXPath(xmlNode* c_node, _Document doc,
                                           _BaseContext context):
    # NOTE: this may copy the element - only call this when it can't leak
    if c_node.doc != doc._c_doc and c_node.doc._private is NULL:
        # not from the context document and not from a fake document
        # either => may still be from a known document, e.g. one
        # created by an extension function
        doc = context._findDocumentForNode(c_node)
        if doc is None:
            # not from a known document at all! => can only make a
            # safety copy here
            c_node = tree.xmlDocCopyNode(c_node, doc._c_doc, 1)
    return _fakeDocElementFactory(doc, c_node)

################################################################################
# special str/unicode subclasses

cdef class _ElementUnicodeResult(unicode):
    cdef _Element _parent
    cdef readonly object is_tail
    cdef readonly object is_text
    cdef readonly object is_attribute
    cdef readonly object attrname

    def getparent(self):
        return self._parent

class _ElementStringResult(bytes):
    # we need to use a Python class here, bytes cannot be C-subclassed
    # in Pyrex/Cython
    def getparent(self):
        return self._parent

cdef object _elementStringResultFactory(string_value, _Element parent,
                                        attrname, bint is_tail):
    cdef _ElementUnicodeResult uresult
    cdef bint is_text
    cdef bint is_attribute = attrname is not None
    if parent is None:
        is_text = 0
    else:
        is_text = not (is_tail or is_attribute)

    if python.PyBytes_CheckExact(string_value):
        result = _ElementStringResult(string_value)
        result._parent = parent
        result.is_attribute = is_attribute
        result.is_tail = is_tail
        result.is_text = is_text
        result.attrname = attrname
        return result
    else:
        uresult = _ElementUnicodeResult(string_value)
        uresult._parent = parent
        uresult.is_attribute = is_attribute
        uresult.is_tail = is_tail
        uresult.is_text = is_text
        uresult.attrname = attrname
        return uresult

cdef object _buildElementStringResult(_Document doc, xmlNode* c_node,
                                      _BaseContext context):
    cdef _Element parent = None
    cdef object attrname = None
    cdef xmlNode* c_element
    cdef char* s
    cdef bint is_tail

    if c_node.type == tree.XML_ATTRIBUTE_NODE:
        attrname = _namespacedName(c_node)
        is_tail = 0
        s = tree.xmlNodeGetContent(c_node)
        try:
            value = funicode(s)
        finally:
            tree.xmlFree(s)
        c_element = NULL
    else:
        #assert c_node.type == tree.XML_TEXT_NODE or c_node.type == tree.XML_CDATA_SECTION_NODE, "invalid node type"
        # may be tail text or normal text
        value = funicode(c_node.content)
        c_element = _previousElement(c_node)
        is_tail = c_element is not NULL

    if not context._build_smart_strings:
        return value

    if c_element is NULL:
        # non-tail text or attribute text
        c_element = c_node.parent
        while c_element is not NULL and not _isElement(c_element):
            c_element = c_element.parent

    if c_element is not NULL:
        parent = _instantiateElementFromXPath(c_element, doc, context)

    return _elementStringResultFactory(
        value, parent, attrname, is_tail)

################################################################################
# callbacks for XPath/XSLT extension functions

cdef void _extension_function_call(_BaseContext context, function,
                                   xpath.xmlXPathParserContext* ctxt, int nargs):
    cdef _Document doc
    cdef xpath.xmlXPathObject* obj
    cdef list args
    cdef int i
    doc = context._doc
    try:
        args = []
        for i in range(nargs):
            obj = xpath.valuePop(ctxt)
            o = _unwrapXPathObject(obj, doc, context)
            _freeXPathObject(obj)
            args.append(o)
        args.reverse()

        res = function(context, *args)
        # wrap result for XPath consumption
        obj = _wrapXPathObject(res, doc, context)
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
            fref = u"{%s}%s" % (rctxt.functionURI, rctxt.function)
        else:
            fref = rctxt.function
        xpath.xmlXPathErr(ctxt, xpath.XPATH_UNKNOWN_FUNC_ERROR)
        context._exc._store_exception(
            XPathFunctionError(u"XPath function '%s' not found" % fref))
