# XSLT

cimport xslt

class XSLTError(LxmlError):
    """Base class of all XSLT errors.
    """
    pass

class XSLTParseError(XSLTError):
    """Error parsing a stylesheet document.
    """
    pass

class XSLTApplyError(XSLTError):
    """Error running an XSL transformation.
    """
    pass

class XSLTSaveError(XSLTError):
    """Error serialising an XSLT result.
    """
    pass

class XSLTExtensionError(XSLTError):
    """Error registering an XSLT extension.
    """
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
            if doc_ref._type == PARSER_DATA_STRING:
                c_doc = _internalParseDoc(
                    _cstr(doc_ref._data_bytes), parse_options,
                    resolver_context)
            elif doc_ref._type == PARSER_DATA_FILENAME:
                c_doc = _internalParseDocFromFile(
                    _cstr(doc_ref._data_bytes), parse_options,
                    resolver_context)
            elif doc_ref._type == PARSER_DATA_FILE:
                data = doc_ref._file.read()
                c_doc = _internalParseDoc(
                    _cstr(data), parse_options,
                    resolver_context)
            elif doc_ref._type == PARSER_DATA_EMPTY:
                c_doc = _newDoc()
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
        if c_type == xslt.XSLT_LOAD_STYLESHEET:
            c_doc._private = c_pcontext
        return c_doc

    c_doc = _xslt_resolve_from_python(c_uri, c_pcontext, parse_options, &error)
    if c_doc is NULL and not error:
        c_doc = XSLT_DOC_DEFAULT_LOADER(
            c_uri, c_dict, parse_options, c_ctxt, c_type)
        if c_doc is NULL:
            _xslt_store_resolver_exception(c_uri, c_pcontext, c_type)

    python.PyGILState_Release(gil_state)
    if c_doc is not NULL and c_type == xslt.XSLT_LOAD_STYLESHEET:
        c_doc._private = c_pcontext
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

cdef int _register_xslt_function(void* ctxt, name_utf, ns_utf):
    if ns_utf is None:
        return 0
    return xslt.xsltRegisterExtFunction(
        <xslt.xsltTransformContext*>ctxt, _cstr(name_utf), _cstr(ns_utf),
        _xpath_function_call)

cdef int _unregister_xslt_function(void* ctxt, name_utf, ns_utf):
    if ns_utf is None:
        return 0
    return xslt.xsltRegisterExtFunction(
        <xslt.xsltTransformContext*>ctxt, _cstr(name_utf), _cstr(ns_utf),
        NULL)


cdef class _XSLTContext(_BaseContext):
    cdef xslt.xsltTransformContext* _xsltCtxt
    def __init__(self, namespaces, extensions, enable_regexp):
        self._xsltCtxt = NULL
        if extensions is not None:
            for ns, prefix in extensions:
                if ns is None:
                    raise XSLTExtensionError, \
                          "extensions must not have empty namespaces"
        _BaseContext.__init__(self, namespaces, extensions, enable_regexp)

    cdef register_context(self, xslt.xsltTransformContext* xsltCtxt,
                               _Document doc):
        self._xsltCtxt = xsltCtxt
        self._set_xpath_context(xsltCtxt.xpathCtxt)
        self._register_context(doc)
        self.registerLocalFunctions(xsltCtxt, _register_xslt_function)
        self.registerGlobalFunctions(xsltCtxt, _register_xslt_function)

    cdef free_context(self):
        self._cleanup_context()
        self._release_context()
        if self._xsltCtxt is not NULL:
            xslt.xsltFreeTransformContext(self._xsltCtxt)
            self._xsltCtxt = NULL
        self._release_temp_refs()


cdef class XSLT:
    """Turn a document into an XSLT object.

    Keyword arguments of the constructor:
    * regexp - enable exslt regular expression support in XPath (default: True)
    * access_control - access restrictions for network or file system

    Keyword arguments of the XSLT run:
    * profile_run - enable XSLT profiling

    Other keyword arguments are passed to the stylesheet.
    """
    cdef _XSLTContext _context
    cdef xslt.xsltStylesheet* _c_style
    cdef _XSLTResolverContext _xslt_resolver_context
    cdef XSLTAccessControl _access_control
    cdef _ErrorLog _error_log

    def __init__(self, xslt_input, extensions=None, regexp=True,
                 access_control=None):
        cdef python.PyThreadState* state
        cdef xslt.xsltStylesheet* c_style
        cdef xmlDoc* c_doc
        cdef xmlDoc* fake_c_doc
        cdef _Document doc
        cdef _Element root_node
        cdef _ExsltRegExp _regexp 

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
            # last error seems to be the most accurate here
            if self._error_log.last_error is not None:
                raise XSLTParseError, self._error_log.last_error.message
            else:
                raise XSLTParseError, "Cannot parse stylesheet"

        c_doc._private = NULL # no longer used!
        self._c_style = c_style

        self._context = _XSLTContext(None, extensions, regexp)

    def __dealloc__(self):
        if self._xslt_resolver_context is not None and \
               self._xslt_resolver_context._c_style_doc is not NULL:
            tree.xmlFreeDoc(self._xslt_resolver_context._c_style_doc)
        # this cleans up the doc copy as well
        xslt.xsltFreeStylesheet(self._c_style)

    property error_log:
        def __get__(self):
            return self._error_log.copy()

    def apply(self, _input, profile_run=False, **_kw):
        return self(_input, profile_run, **_kw)

    def tostring(self, _ElementTree result_tree):
        """Save result doc to string based on stylesheet output method.
        """
        return str(result_tree)

    def __call__(self, _input, profile_run=False, **_kw):
        cdef _XSLTContext context
        cdef _Document input_doc
        cdef _Element root_node
        cdef _Document result_doc
        cdef _Document profile_doc
        cdef xmlDoc* c_profile_doc
        cdef xslt.xsltTransformContext* transform_ctxt
        cdef xmlDoc* c_result
        cdef xmlDoc* c_doc

        if not _checkThreadDict(self._c_style.doc.dict):
            raise RuntimeError, "stylesheet is not usable in this thread"

        input_doc = _documentOrRaise(_input)
        root_node = _rootNodeOrRaise(_input)

        c_doc = _fakeRootDoc(input_doc._c_doc, root_node._c_node)

        transform_ctxt = xslt.xsltNewTransformContext(self._c_style, c_doc)
        if transform_ctxt is NULL:
            _destroyFakeDoc(input_doc._c_doc, c_doc)
            python.PyErr_NoMemory()

        initTransformDict(transform_ctxt)

        if profile_run:
            transform_ctxt.profile = 1

        try:
            self._error_log.connect()
            context = self._context._copy()
            context.register_context(transform_ctxt, input_doc)

            c_result = self._run_transform(
                input_doc, c_doc, _kw, context, transform_ctxt)

            if transform_ctxt.profile:
                c_profile_doc = xslt.xsltGetProfileInformation(transform_ctxt)
                if c_profile_doc is not NULL:
                    profile_doc = _documentFactory(
                        c_profile_doc, input_doc._parser)
        finally:
            if context is not None:
                context.free_context()
            _destroyFakeDoc(input_doc._c_doc, c_doc)
            self._error_log.disconnect()

        try:
            if self._xslt_resolver_context._has_raised():
                if c_result is not NULL:
                    tree.xmlFreeDoc(c_result)
                self._xslt_resolver_context._raise_if_stored()

            if c_result is NULL:
                # last error seems to be the most accurate here
                error = self._error_log.last_error
                if error is not None and error.message:
                    if error.line >= 0:
                        message = "%s, line %d" % (error.message, error.line)
                    else:
                        message = error.message
                elif error is not None and error.line >= 0:
                    message = "Error applying stylesheet, line %d" % error.line
                else:
                    message = "Error applying stylesheet"
                raise XSLTApplyError, message
        finally:
            self._xslt_resolver_context.clear()

        result_doc = _documentFactory(c_result, input_doc._parser)
        return _xsltResultTreeFactory(result_doc, self, profile_doc)

    cdef xmlDoc* _run_transform(self, _Document input_doc, xmlDoc* c_input_doc,
                               parameters, _XSLTContext context,
                               xslt.xsltTransformContext* transform_ctxt):
        cdef python.PyThreadState* state
        cdef _XSLTResolverContext resolver_context
        cdef xmlDoc* c_result
        cdef char** params
        cdef Py_ssize_t i, parameter_count

        resolver_context = _XSLTResolverContext(input_doc._parser)
        resolver_context._c_style_doc = self._xslt_resolver_context._c_style_doc

        xslt.xsltSetTransformErrorFunc(transform_ctxt, <void*>self._error_log,
                                       _receiveXSLTError)

        if self._access_control is not None:
            self._access_control._register_in_context(transform_ctxt)

        transform_ctxt._private = <python.PyObject*>self._xslt_resolver_context

        parameter_count = python.PyDict_Size(parameters)
        if parameter_count > 0:
            # allocate space for parameters
            # * 2 as we want an entry for both key and value,
            # and + 1 as array is NULL terminated
            params = <char**>python.PyMem_Malloc(
                sizeof(char*) * (parameter_count * 2 + 1))
            i = 0
            keep_ref = []
            for key, value in parameters.iteritems():
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

        state = python.PyEval_SaveThread()
        c_result = xslt.xsltApplyStylesheetUser(
            self._c_style, c_input_doc, params, NULL, NULL, transform_ctxt)
        python.PyEval_RestoreThread(state)

        if params is not NULL:
            # deallocate space for parameters
            python.PyMem_Free(params)

        return c_result

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
            return unicode('')
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
            cdef object root
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

cdef void initTransformDict(xslt.xsltTransformContext* transform_ctxt):
    __GLOBAL_PARSER_CONTEXT.initThreadDictRef(&transform_ctxt.dict)


################################################################################
# XSLT PI support

cdef object _FIND_PI_ATTRIBUTES
_FIND_PI_ATTRIBUTES = re.compile(r'\s+(\w+)\s*=\s*["\']([^"\']+)["\']', re.U).findall

cdef object _RE_PI_HREF
_RE_PI_HREF = re.compile(r'\s+href\s*=\s*["\']([^"\']+)["\']')

cdef object _FIND_PI_HREF
_FIND_PI_HREF = _RE_PI_HREF.findall

cdef object _REPLACE_PI_HREF
_REPLACE_PI_HREF = _RE_PI_HREF.sub

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
        hrefs_utf = _FIND_PI_HREF(' ' + self._c_node.content)
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

    def set(self, key, value):
        if key != "href":
            raise AttributeError, "only setting the 'href' attribute is supported on XSLT-PIs"
        if value is None:
            attrib = ""
        elif '"' in value or '>' in value:
            raise ValueError, "Invalid URL, must not contain '\"' or '>'"
        else:
            attrib = ' href="%s"' % value
        text = ' ' + self.text
        if _FIND_PI_HREF(text):
            self.text = _REPLACE_PI_HREF(attrib, text)
        else:
            self.text = text + attrib

    def get(self, key, default=None):
        for attr, value in _FIND_PI_ATTRIBUTES(' ' + self.text):
            if attr == key:
                return value
        return default
