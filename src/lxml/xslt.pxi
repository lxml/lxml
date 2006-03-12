# XSLT and XPath classes, supports for extension functions

class XSLTError(LxmlError):
    pass

class XSLTParseError(XSLTError):
    pass

class XSLTApplyError(XSLTError):
    pass

class XSLTSaveError(XSLTError):
    pass

class XPathError(LxmlError):
    pass

class XPathContextError(XPathError):
    pass

class XPathNamespaceError(XPathError):
    pass

class XPathResultError(XPathError):
    pass

class XPathSyntaxError(LxmlSyntaxError):
    pass

cdef object _RE_STRINGS
cdef object _RE_NAMESPACES
_RE_STRINGS    = re.compile('("[^"]*")|(\'[^\']*\')')
_RE_NAMESPACES = re.compile('{([^}]+)}')

################################################################################
# XSLT

cdef class XSLT:
    """Turn a document into an XSLT object.
    """
    cdef xslt.xsltStylesheet* _c_style
    
    def __init__(self, xslt_input):
        # make a copy of the document as stylesheet needs to assume it
        # doesn't change
        cdef xslt.xsltStylesheet* c_style
        cdef xmlDoc* c_doc
        cdef _Document doc
        doc = _documentOrRaise(xslt_input)
        c_doc = tree.xmlCopyDoc(doc._c_doc, 1)
        # XXX work around bug in xmlCopyDoc (fix is upcoming in new release
        # of libxml2)
        if doc._c_doc.URL is not NULL:
            c_doc.URL = tree.xmlStrdup(doc._c_doc.URL)
            
        c_style = xslt.xsltParseStylesheetDoc(c_doc)
        if c_style is NULL:
            raise XSLTParseError, "Cannot parse style sheet"
        self._c_style = c_style
        # XXX is it worthwile to use xsltPrecomputeStylesheet here?
        
    def __dealloc__(self):
        # this cleans up copy of doc as well
        xslt.xsltFreeStylesheet(self._c_style)
        
    def __call__(self, _input, **_kw):
        cdef _Document input_doc
        cdef _NodeBase root_node
        cdef _Document result_doc
        cdef xmlDoc* c_result
        cdef xmlDoc* c_doc
        cdef char** params
        cdef int i
        cdef int j

        input_doc = _documentOrRaise(_input)
        root_node = _rootNodeOf(_input)

        if _kw:
            # allocate space for parameters
            # * 2 as we want an entry for both key and value,
            # and + 1 as array is NULL terminated
            params = <char**>cstd.malloc(sizeof(char*) * (len(_kw) * 2 + 1))
            i = 0
            keep_ref = []
            for key, value in _kw.items():
                k = _utf8(key)
                keep_ref.append(k)
                v = _utf8(value)
                keep_ref.append(v)
                params[i] = k
                i = i + 1
                params[i] = v
                i = i + 1
            params[i] = NULL
        else:
            params = NULL

        c_doc = _fakeRootDoc(input_doc._c_doc, root_node._c_node)
        c_result = xslt.xsltApplyStylesheet(self._c_style, c_doc, params)
        _destroyFakeDoc(input_doc._c_doc, c_doc)

        if params is not NULL:
            # deallocate space for parameters again
            cstd.free(params)

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

cdef class XPathDocumentEvaluator:
    """Create an XPath evaluator for a document.
    """
    cdef xpath.xmlXPathContext* _c_ctxt
    cdef _NodeBase _root_node
    cdef _Document _doc
    cdef object _extension_functions
    cdef object _exc_info
    cdef object _namespaces
    cdef object _extensions
    cdef object _temp_elements
    cdef object _temp_docs
    
    def __init__(self, input, namespaces=None, extensions=None):
        cdef xpath.xmlXPathContext* xpathCtxt
        cdef int ns_register_status
        cdef _Document input_doc
        cdef _NodeBase root_node

        input_doc = _documentOrRaise(input)
        root_node = _rootNodeOf(input)

        xpathCtxt = xpath.xmlXPathNewContext(input_doc._c_doc)
        if xpathCtxt is NULL:
            # XXX what triggers this exception?
            raise XPathContextError, "Unable to create new XPath context"

        self._doc = input_doc
        self._root_node = root_node
        self._c_ctxt = xpathCtxt
        self._c_ctxt.userData = <void*>self
        self._namespaces = namespaces
        self._extensions = extensions
        
        if namespaces is not None:
            self.registerNamespaces(namespaces)
        self._extension_functions = {}
        if extensions is not None:
            for extension in extensions:
                self._extension_functions.update(extension)
                for (ns_uri, name), function in extension.items():
                    if ns_uri is not None:
                        xpath.xmlXPathRegisterFuncNS(
                            xpathCtxt, name, ns_uri, _xpathCallback)
                    else:
                        xpath.xmlXPathRegisterFunc(
                            xpathCtxt, name, _xpathCallback)
                        
    def __dealloc__(self):
        xpath.xmlXPathFreeContext(self._c_ctxt)
    
    def registerNamespace(self, prefix, uri):
        """Register a namespace with the XPath context.
        """
        s_prefix = _utf8(prefix)
        s_uri = _utf8(uri)
        # XXX should check be done to verify namespace doesn't already exist?
        ns_register_status = xpath.xmlXPathRegisterNs(
            self._c_ctxt, s_prefix, s_uri)
        if ns_register_status != 0:
            # XXX doesn't seem to be possible to trigger this
            # from Python
            raise XPathNamespaceError, (
                "Unable to register namespaces with prefix "
                "%s and uri %s" % (prefix, uri))

    def registerNamespaces(self, namespaces):
        """Register a prefix -> uri dict.
        """
        for prefix, uri in namespaces.items():
            self.registerNamespace(prefix, uri)
    
    def evaluate(self, path):
        return self._evaluate(path, self._root_node._c_node)

    cdef object _evaluate(self, path, xmlNode* c_ctxt_node):
        cdef xpath.xmlXPathObject* xpathObj
        cdef xmlNode* c_node
        
        # if element context is requested; unfortunately need to modify ctxt
        self._c_ctxt.node = c_ctxt_node

        path = _utf8(path)
        self._exc_info = None
        self._release()
        xpathObj = xpath.xmlXPathEvalExpression(path, self._c_ctxt)
        if self._exc_info is not None:
            type, value, traceback = self._exc_info
            self._exc_info = None
            raise type, value, traceback
        if xpathObj is NULL:
            raise XPathSyntaxError, "Error in xpath expression."
        try:
            result = _unwrapXPathObject(xpathObj, self._doc)
        except XPathResultError:
            #self._release()
            xpath.xmlXPathFreeObject(xpathObj)
            raise
        xpath.xmlXPathFreeObject(xpathObj)
        # release temporarily held python stuff
        #self._release()
        return result
        
    #def clone(self):
    #    # XXX pretty expensive so calling this from callback is probably
    #    # not desirable
    #    return XPathEvaluator(self._doc, self._namespaces, self._extensions)

    def _release(self):
        self._temp_elements = {}
        self._temp_docs = {}
        
    def _hold(self, obj):
        """A way to temporarily hold references to nodes in the evaluator.

        This is needed because otherwise nodes created in XPath extension
        functions would be reference counted too soon, during the
        XPath evaluation.
        """
        cdef _NodeBase element
        if isinstance(obj, _NodeBase):
            obj = [obj]
        if not type(obj) in (type([]), type(())):
            return
        for o in obj:
            if isinstance(o, _NodeBase):
                element = <_NodeBase>o
                #print "Holding element:", <int>element._c_node
                self._temp_elements[id(element)] = element
                #print "Holding document:", <int>element._doc._c_doc
                self._temp_docs[id(element._doc)] = element._doc

cdef class XPathElementEvaluator(XPathDocumentEvaluator):
    """Create an XPath evaluator for an element.
    """
    cdef _Element _element
    
    def __init__(self, _Element element, namespaces=None, extensions=None):
        XPathDocumentEvaluator.__init__(
            self, element._doc, namespaces, extensions)
        self._element = element
        
    def evaluate(self, path):
        return self._evaluate(path, self._element._c_node)

def XPathEvaluator(doc_or_element, namespaces=None, extensions=None):
    if isinstance(doc_or_element, _ElementTree) or isinstance(doc_or_element, _Document):
        return XPathDocumentEvaluator(doc_or_element, namespaces, extensions)
    else:
        return XPathElementEvaluator(doc_or_element, namespaces, extensions)
    
def Extension(module, function_mapping, ns_uri=None):
    result = {}
    for function_name, xpath_name in function_mapping.items():
        result[(ns_uri, xpath_name)] = getattr(module, function_name)
    return result


################################################################################
# helper functions

cdef xpath.xmlXPathObject* _wrapXPathObject(object obj) except NULL:
    cdef xpath.xmlNodeSet* resultSet
    cdef _NodeBase node
    if python.PyString_Check(obj):
        # XXX use the Wrap variant? Or leak...
        return xpath.xmlXPathNewCString(obj)
    if python.PyUnicode_Check(obj):
        obj = _utf8(obj)
        return xpath.xmlXPathNewCString(obj)
    if python.PyBool_Check(obj):
        return xpath.xmlXPathNewBoolean(obj)
    if python.PyNumber_Check(obj):
        return xpath.xmlXPathNewFloat(obj)
    if isinstance(obj, _NodeBase):
        obj = [obj]
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
        if c_node.type == tree.XML_ELEMENT_NODE:
            element = _elementFactory(doc, c_node)
            result.append(element)
        elif c_node.type == tree.XML_TEXT_NODE:
            result.append(funicode(c_node.content))
        elif c_node.type == tree.XML_ATTRIBUTE_NODE:
            s = tree.xmlNodeGetContent(c_node)
            attr_value = funicode(s)
            tree.xmlFree(s)
            result.append(attr_value)
        elif c_node.type == tree.XML_COMMENT_NODE:
            s = tree.xmlNodeGetContent(c_node)
            s2 = '<!--%s-->' % s
            comment_value = funicode(s2)
            tree.xmlFree(s)
            result.append(comment_value)
        else:
            print "Not yet implemented result node type:", c_node.type
            raise NotImplementedError
    return result

cdef void _xpathCallback(xpath.xmlXPathParserContext* ctxt, int nargs):
    cdef xpath.xmlXPathContext* rctxt
    cdef _Document doc
    cdef xpath.xmlXPathObject* obj
    cdef XPathDocumentEvaluator evaluator
    
    rctxt = ctxt.context
    
    # get information on what function is called
    name = rctxt.function
    if rctxt.functionURI is not NULL:
        uri = rctxt.functionURI
    else:
        uri = None

    # get our evaluator
    evaluator = <XPathDocumentEvaluator>(rctxt.userData)

    # lookup up the extension function in the evaluator
    f = evaluator._extension_functions[(uri, name)]
    
    args = []
    doc = evaluator._doc
    for i from 0 <= i < nargs:
        args.append(_unwrapXPathObject(xpath.valuePop(ctxt), doc))
    args.reverse()

    try:
        # call the function
        res = f(evaluator, *args)
        # hold python objects temporarily so that they won't get deallocated
        # during processing
        evaluator._hold(res)
        # now wrap for XPath consumption
        obj = _wrapXPathObject(res)
    except:
        xpath.xmlXPathErr(
            ctxt,
            xmlerror.XML_XPATH_EXPR_ERROR - xmlerror.XML_XPATH_EXPRESSION_OK)
        evaluator._exc_info = sys.exc_info()
        return
    xpath.valuePush(ctxt, obj)
