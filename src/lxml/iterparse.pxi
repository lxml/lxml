# iterparse -- incremental parsing

cdef object __ITERPARSE_CHUNK_SIZE
__ITERPARSE_CHUNK_SIZE = 32768

ctypedef enum _IterparseEventFilter:
    ITERPARSE_FILTER_START     =  1
    ITERPARSE_FILTER_END       =  2
    ITERPARSE_FILTER_START_NS  =  4
    ITERPARSE_FILTER_END_NS    =  8
    ITERPARSE_FILTER_COMMENT   = 16
    ITERPARSE_FILTER_PI        = 32

cdef int _buildIterparseEventFilter(events) except -1:
    cdef int event_filter
    event_filter = 0
    for event in events:
        if event == 'start':
            event_filter |= ITERPARSE_FILTER_START
        elif event == 'end':
            event_filter |= ITERPARSE_FILTER_END
        elif event == 'start-ns':
            event_filter |= ITERPARSE_FILTER_START_NS
        elif event == 'end-ns':
            event_filter |= ITERPARSE_FILTER_END_NS
        elif event == 'comment':
            event_filter |= ITERPARSE_FILTER_COMMENT
        elif event == 'pi':
            event_filter |= ITERPARSE_FILTER_PI
        else:
            raise ValueError("invalid event name '%s'" % event)
    return event_filter

cdef int _countNsDefs(xmlNode* c_node):
    cdef xmlNs* c_ns
    cdef int count
    count = 0
    c_ns = c_node.nsDef
    while c_ns is not NULL:
        count = count + 1
        c_ns = c_ns.next
    return count

cdef int _appendStartNsEvents(xmlNode* c_node, event_list):
    cdef xmlNs* c_ns
    cdef int count
    count = 0
    c_ns = c_node.nsDef
    while c_ns is not NULL:
        if c_ns.prefix is NULL:
            prefix = ''
        else:
            prefix = funicode(c_ns.prefix)
        ns_tuple = (prefix, funicode(c_ns.href))
        python.PyList_Append(event_list, ("start-ns", ns_tuple))
        count = count + 1
        c_ns = c_ns.next
    return count

cdef class _IterparseContext(_ParserContext):
    cdef xmlparser.startElementNsSAX2Func _origSaxStart
    cdef xmlparser.endElementNsSAX2Func   _origSaxEnd
    cdef xmlparser.startElementSAXFunc    _origSaxStartNoNs
    cdef xmlparser.endElementSAXFunc      _origSaxEndNoNs
    cdef xmlparser.commentSAXFunc         _origSaxComment
    cdef xmlparser.processingInstructionSAXFunc _origSaxPI
    cdef _Element  _root
    cdef _Document _doc
    cdef int _event_filter
    cdef object _events
    cdef int _event_index
    cdef object _ns_stack
    cdef object _pop_ns
    cdef object _node_stack
    cdef object _pop_node
    cdef object _tag_tuple
    cdef char*  _tag_href
    cdef char*  _tag_name

    def __init__(self):
        self._ns_stack = []
        self._pop_ns = self._ns_stack.pop
        self._node_stack = []
        self._pop_node = self._node_stack.pop
        self._events = []
        self._event_index = 0

    cdef void _initParserContext(self, xmlparser.xmlParserCtxt* c_ctxt):
        "wrap original SAX2 callbacks"
        cdef xmlparser.xmlSAXHandler* sax
        _ParserContext._initParserContext(self, c_ctxt)
        sax = c_ctxt.sax
        self._origSaxStart = sax.startElementNs
        self._origSaxStartNoNs = sax.startElement
        # only override start event handler if needed
        if self._event_filter == 0 or \
               self._event_filter & (ITERPARSE_FILTER_START | \
                                     ITERPARSE_FILTER_START_NS | \
                                     ITERPARSE_FILTER_END_NS):
            sax.startElementNs = _iterparseSaxStart
            sax.startElement = _iterparseSaxStartNoNs

        self._origSaxEnd = sax.endElementNs
        self._origSaxEndNoNs = sax.endElement
        # only override end event handler if needed
        if self._event_filter == 0 or \
               self._event_filter & (ITERPARSE_FILTER_END | \
                                     ITERPARSE_FILTER_END_NS):
            sax.endElementNs = _iterparseSaxEnd
            sax.endElement = _iterparseSaxEndNoNs

        self._origSaxComment = sax.comment
        if self._event_filter & ITERPARSE_FILTER_COMMENT:
            sax.comment = _iterparseSaxComment

        self._origSaxPI = sax.processingInstruction
        if self._event_filter & ITERPARSE_FILTER_PI:
            sax.processingInstruction = _iterparseSaxPI

    cdef _setEventFilter(self, events, tag):
        self._event_filter = _buildIterparseEventFilter(events)
        if tag is None or tag == '*':
            self._tag_href  = NULL
            self._tag_name  = NULL
        else:
            self._tag_tuple = _getNsTag(tag)
            href, name = self._tag_tuple
            if href is None or href == '*':
                self._tag_href = NULL
            else:
                self._tag_href = _cstr(href)
            if name is None or name == '*':
                self._tag_name = NULL
            else:
                self._tag_name = _cstr(name)
            if self._tag_href is NULL and self._tag_name is NULL:
                self._tag_tuple = None

    cdef int startNode(self, xmlNode* c_node) except -1:
        cdef xmlNs* c_ns
        cdef int ns_count
        if self._event_filter & ITERPARSE_FILTER_START_NS:
            ns_count = _appendStartNsEvents(c_node, self._events)
        elif self._event_filter & ITERPARSE_FILTER_END_NS:
            ns_count = _countNsDefs(c_node)
        if self._event_filter & ITERPARSE_FILTER_END_NS:
            python.PyList_Append(self._ns_stack, ns_count)
        if self._doc is None:
            self._doc = _documentFactory(c_node.doc, None)
            self._root = self._doc.getroot()
        if self._tag_tuple is None or \
               _tagMatches(c_node, self._tag_href, self._tag_name):
            node = _elementFactory(self._doc, c_node)
            if self._event_filter & ITERPARSE_FILTER_END:
                python.PyList_Append(self._node_stack, node)
            if self._event_filter & ITERPARSE_FILTER_START:
                python.PyList_Append(self._events, ("start", node))
        return 0

    cdef int endNode(self, xmlNode* c_node) except -1:
        cdef xmlNs* c_ns
        cdef int ns_count
        if self._event_filter & ITERPARSE_FILTER_END:
            if self._tag_tuple is None or \
                   _tagMatches(c_node, self._tag_href, self._tag_name):
                if self._event_filter & (ITERPARSE_FILTER_START | \
                                         ITERPARSE_FILTER_START_NS | \
                                         ITERPARSE_FILTER_END_NS):
                    node = self._pop_node()
                else:
                    if self._doc is None:
                        self._doc = _documentFactory(c_node.doc, None)
                        self._root = self._doc.getroot()
                    node = _elementFactory(self._doc, c_node)
                python.PyList_Append(self._events, ("end", node))

        if self._event_filter & ITERPARSE_FILTER_END_NS:
            ns_count = self._pop_ns()
            if ns_count > 0:
                event = ("end-ns", None)
                for i from 0 <= i < ns_count:
                    python.PyList_Append(self._events, event)
        return 0

    cdef int pushEvent(self, event, xmlNode* c_node) except -1:
        cdef _Element root
        if self._doc is None:
            self._doc = _documentFactory(c_node.doc, None)
            root = self._doc.getroot()
            if root is not None and root._c_node.type == tree.XML_ELEMENT_NODE:
                self._root = root
        node = _elementFactory(self._doc, c_node)
        python.PyList_Append(self._events, (event, node))
        return 0


cdef inline void _pushSaxStartEvent(xmlparser.xmlParserCtxt* c_ctxt,
                                    xmlNode* c_node):
    cdef _IterparseContext context
    context = <_IterparseContext>c_ctxt._private
    try:
        context.startNode(c_node)
    except:
        if c_ctxt.errNo == xmlerror.XML_ERR_OK:
            c_ctxt.errNo = xmlerror.XML_ERR_INTERNAL_ERROR
        c_ctxt.disableSAX = 1
        context._store_raised()

cdef inline void _pushSaxEndEvent(xmlparser.xmlParserCtxt* c_ctxt,
                                  xmlNode* c_node):
    cdef _IterparseContext context
    context = <_IterparseContext>c_ctxt._private
    try:
        context.endNode(c_node)
    except:
        if c_ctxt.errNo == xmlerror.XML_ERR_OK:
            c_ctxt.errNo = xmlerror.XML_ERR_INTERNAL_ERROR
        c_ctxt.disableSAX = 1
        context._store_raised()

cdef inline void _pushSaxEvent(xmlparser.xmlParserCtxt* c_ctxt,
                               event, xmlNode* c_node):
    cdef _IterparseContext context
    context = <_IterparseContext>c_ctxt._private
    try:
        context.pushEvent(event, c_node)
    except:
        if c_ctxt.errNo == xmlerror.XML_ERR_OK:
            c_ctxt.errNo = xmlerror.XML_ERR_INTERNAL_ERROR
        c_ctxt.disableSAX = 1
        context._store_raised()

cdef void _iterparseSaxStart(void* ctxt, char* localname, char* prefix,
                             char* URI, int nb_namespaces, char** namespaces,
                             int nb_attributes, int nb_defaulted,
                             char** attributes):
    cdef xmlparser.xmlParserCtxt* c_ctxt
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    (<_IterparseContext>c_ctxt._private)._origSaxStart(
        ctxt, localname, prefix, URI,
        nb_namespaces, namespaces,
        nb_attributes, nb_defaulted, attributes)
    _pushSaxStartEvent(c_ctxt, c_ctxt.node)

cdef void _iterparseSaxEnd(void* ctxt, char* localname, char* prefix, char* URI):
    cdef xmlparser.xmlParserCtxt* c_ctxt
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    _pushSaxEndEvent(c_ctxt, c_ctxt.node)
    (<_IterparseContext>c_ctxt._private)._origSaxEnd(ctxt, localname, prefix, URI)

cdef void _iterparseSaxStartNoNs(void* ctxt, char* name, char** attributes):
    cdef xmlparser.xmlParserCtxt* c_ctxt
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    (<_IterparseContext>c_ctxt._private)._origSaxStartNoNs(ctxt, name, attributes)
    _pushSaxStartEvent(c_ctxt, c_ctxt.node)

cdef void _iterparseSaxEndNoNs(void* ctxt, char* name):
    cdef xmlparser.xmlParserCtxt* c_ctxt
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    _pushSaxEndEvent(c_ctxt, c_ctxt.node)
    (<_IterparseContext>c_ctxt._private)._origSaxEndNoNs(ctxt, name)

cdef void _iterparseSaxComment(void* ctxt, char* text):
    cdef xmlNode* c_node
    cdef xmlparser.xmlParserCtxt* c_ctxt
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    (<_IterparseContext>c_ctxt._private)._origSaxComment(ctxt, text)
    c_node = _iterparseFindLastNode(c_ctxt)
    if c_node is not NULL:
        _pushSaxEvent(c_ctxt, "comment", c_node)

cdef void _iterparseSaxPI(void* ctxt, char* target, char* data):
    cdef xmlNode* c_node
    cdef xmlparser.xmlParserCtxt* c_ctxt
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    (<_IterparseContext>c_ctxt._private)._origSaxPI(ctxt, target, data)
    c_node = _iterparseFindLastNode(c_ctxt)
    if c_node is not NULL:
        _pushSaxEvent(c_ctxt, "pi", c_node)

cdef inline xmlNode* _iterparseFindLastNode(xmlparser.xmlParserCtxt* c_ctxt):
    # this mimics what libxml2 creates for comments/PIs
    if c_ctxt.inSubset == 1:
        return c_ctxt.myDoc.intSubset.last
    elif c_ctxt.inSubset == 2:
        return c_ctxt.myDoc.extSubset.last
    elif c_ctxt.node is NULL:
        return c_ctxt.myDoc.last
    elif c_ctxt.node.type == tree.XML_ELEMENT_NODE:
        return c_ctxt.node.last
    else:
        return c_ctxt.node.next

cdef class iterparse(_BaseParser):
    """iterparse(self, source, events=("end",), tag=None, attribute_defaults=False, dtd_validation=False, load_dtd=False, no_network=True, remove_blank_text=False, remove_comments=False, remove_pis=False, encoding=None, html=False, schema=None)
    Incremental parser.

    Parses XML into a tree and generates tuples (event, element) in a
    SAX-like fashion. ``event`` is any of 'start', 'end', 'start-ns',
    'end-ns'.

    For 'start' and 'end', ``element`` is the Element that the parser just
    found opening or closing.  For 'start-ns', it is a tuple (prefix, URI) of
    a new namespace declaration.  For 'end-ns', it is simply None.  Note that
    all start and end events are guaranteed to be properly nested.

    The keyword argument ``events`` specifies a sequence of event type names
    that should be generated.  By default, only 'end' events will be
    generated.

    The additional ``tag`` argument restricts the 'start' and 'end' events to
    those elements that match the given tag.  By default, events are generated
    for all elements.  Note that the 'start-ns' and 'end-ns' events are not
    impacted by this restriction.

    The other keyword arguments in the constructor are mainly based on the
    libxml2 parser configuration.  A DTD will also be loaded if validation or
    attribute default values are requested.

    Available boolean keyword arguments:
      - attribute_defaults - read default attributes from DTD
      - dtd_validation     - validate (if DTD is available)
      - load_dtd           - use DTD for parsing
      - no_network         - prevent network access for related files
      - remove_blank_text  - discard blank text nodes
      - remove_comments    - discard comments
      - remove_pis         - discard processing instructions
      - compact            - safe memory for short text content (default: True)
      - resolve_entities   - replace entities by their text value (default: True)

    Other keyword arguments:
      - encoding           - override the document encoding
      - schema             - an XMLSchema to validate against
    """
    cdef object _source
    cdef object _events
    cdef object _tag
    cdef readonly object root
    def __init__(self, source, events=("end",), *, tag=None,
                 attribute_defaults=False, dtd_validation=False,
                 load_dtd=False, no_network=True, remove_blank_text=False,
                 compact=True, resolve_entities=True, remove_comments=False,
                 remove_pis=False, encoding=None,
                 html=False, XMLSchema schema=None):
        cdef _IterparseContext context
        cdef char* c_encoding
        cdef int parse_options
        if not hasattr(source, 'read'):
            filename = _encodeFilename(source)
            source = open(filename, 'rb')
        else:
            filename = _encodeFilename(_getFilenameForFile(source))

        self._source = source
        if html:
            # make sure we're not looking for namespaces
            events = tuple([ event for event in events
                             if event != 'start-ns' and event != 'end-ns' ])

        self._events = events
        self._tag = tag

        parse_options = _XML_DEFAULT_PARSE_OPTIONS
        if load_dtd:
            parse_options = parse_options | xmlparser.XML_PARSE_DTDLOAD
        if dtd_validation:
            parse_options = parse_options | xmlparser.XML_PARSE_DTDVALID | \
                            xmlparser.XML_PARSE_DTDLOAD
        if attribute_defaults:
            parse_options = parse_options | xmlparser.XML_PARSE_DTDATTR | \
                            xmlparser.XML_PARSE_DTDLOAD
        if remove_blank_text:
            parse_options = parse_options | xmlparser.XML_PARSE_NOBLANKS
        if not no_network:
            parse_options = parse_options ^ xmlparser.XML_PARSE_NONET
        if not compact:
            parse_options = parse_options ^ xmlparser.XML_PARSE_COMPACT
        if not resolve_entities:
            parse_options = parse_options ^ xmlparser.XML_PARSE_NOENT

        _BaseParser.__init__(self, parse_options, html, schema,
                             remove_comments, remove_pis,
                             None, filename, encoding)

        context = <_IterparseContext>self._getPushParserContext()
        context.prepare()
        # parser will not be unlocked - no other methods supported

    property error_log:
        """The error log of the last (or current) parser run.
        """
        def __get__(self):
            cdef _ParserContext context
            context = self._getPushParserContext()
            return context._error_log.copy()

    cdef _ParserContext _createContext(self, target):
        cdef _IterparseContext context
        context = _IterparseContext()
        context._setEventFilter(self._events, self._tag)
        return context

    def copy(self):
        raise TypeError("iterparse parsers cannot be copied")

    def __iter__(self):
        return self

    def __next__(self):
        cdef _IterparseContext context
        cdef xmlparser.xmlParserCtxt* pctxt
        cdef int error
        if self._source is None:
            raise StopIteration

        context = <_IterparseContext>self._getPushParserContext()
        if python.PyList_GET_SIZE(context._events) > context._event_index:
            item = python.PyList_GET_ITEM(context._events, context._event_index)
            python.Py_INCREF(item) # 'borrowed reference' from PyList_GET_ITEM
            context._event_index = context._event_index + 1
            return item

        del context._events[:]
        pctxt = context._c_ctxt
        error = 0
        while python.PyList_GET_SIZE(context._events) == 0 and error == 0:
            data = self._source.read(__ITERPARSE_CHUNK_SIZE)
            if not python.PyString_Check(data):
                self._source = None
                raise TypeError("reading file objects must return plain strings")
            elif data:
                if self._for_html:
                    error = htmlparser.htmlParseChunk(
                        pctxt, _cstr(data), python.PyString_GET_SIZE(data), 0)
                else:
                    error = xmlparser.xmlParseChunk(
                        pctxt, _cstr(data), python.PyString_GET_SIZE(data), 0)
            else:
                if self._for_html:
                    error = htmlparser.htmlParseChunk(pctxt, NULL, 0, 1)
                else:
                    error = xmlparser.xmlParseChunk(pctxt, NULL, 0, 1)
                self._source = None
                break
        if error != 0 or (context._validator is not None and
                          not context._validator.isvalid()):
            self._source = None
            del context._events[:]
            _raiseParseError(pctxt, self._filename, context._error_log)
        if python.PyList_GET_SIZE(context._events) == 0:
            self.root = context._root
            self._source = None
            raise StopIteration

        context._event_index = 1
        element = python.PyList_GET_ITEM(context._events, 0)
        python.Py_INCREF(element) # 'borrowed reference' from PyList_GET_ITEM
        return element


cdef class iterwalk:
    """iterwalk(self, element_or_tree, events=("end",), tag=None)

    A tree walker that generates events from an existing tree as if it
    was parsing XML data with ``iterparse()``.
    """
    cdef object _node_stack
    cdef object _pop_node
    cdef int    _index
    cdef object _events
    cdef object _pop_event
    cdef int    _event_filter
    cdef object _tag_tuple
    cdef char*  _tag_href
    cdef char*  _tag_name

    def __init__(self, element_or_tree, events=("end",), tag=None):
        cdef _Element root
        cdef int ns_count
        root = _rootNodeOrRaise(element_or_tree)
        self._event_filter = _buildIterparseEventFilter(events)
        self._setTagFilter(tag)
        self._node_stack  = []
        self._pop_node = self._node_stack.pop
        self._events = []
        self._pop_event = self._events.pop

        if self._event_filter != 0:
            self._index = 0
            ns_count = self._start_node(root)
            python.PyList_Append(self._node_stack, (root, ns_count))
        else:
            self._index = -1

    cdef void _setTagFilter(self, tag):
        if tag is None or tag == '*':
            self._tag_href  = NULL
            self._tag_name  = NULL
        else:
            self._tag_tuple = _getNsTag(tag)
            href, name = self._tag_tuple
            if href is None or href == '*':
                self._tag_href = NULL
            else:
                self._tag_href = _cstr(href)
            if name is None or name == '*':
                self._tag_name = NULL
            else:
                self._tag_name = _cstr(name)
            if self._tag_href is NULL and self._tag_name is NULL:
                self._tag_tuple = None

    def __iter__(self):
        return self

    def __next__(self):
        cdef xmlNode* c_child
        cdef _Element node
        cdef _Element next_node
        cdef int ns_count
        if python.PyList_GET_SIZE(self._events):
            return self._pop_event(0)
        ns_count = 0
        # find next node
        while self._index >= 0:
            node = self._node_stack[self._index][0]

            c_child = _findChildForwards(node._c_node, 0)
            if c_child is not NULL:
                # try children
                next_node = _elementFactory(node._doc, c_child)
            else:
                # back off
                next_node = None
                while next_node is None:
                    # back off through parents
                    self._index = self._index - 1
                    node = self._end_node()
                    if self._index < 0:
                        break
                    next_node = node.getnext()
            if next_node is not None:
                if self._event_filter & (ITERPARSE_FILTER_START | \
                                         ITERPARSE_FILTER_START_NS):
                    ns_count = self._start_node(next_node)
                elif self._event_filter & ITERPARSE_FILTER_END_NS:
                    ns_count = _countNsDefs(next_node._c_node)
                python.PyList_Append(self._node_stack, (next_node, ns_count))
                self._index = self._index + 1
            if python.PyList_GET_SIZE(self._events):
                return self._pop_event(0)
        raise StopIteration

    cdef int _start_node(self, _Element node):
        cdef int ns_count
        if self._event_filter & ITERPARSE_FILTER_START_NS:
            ns_count = _appendStartNsEvents(node._c_node, self._events)
        elif self._event_filter & ITERPARSE_FILTER_END_NS:
            ns_count = _countNsDefs(node._c_node)
        else:
            ns_count = 0
        if self._event_filter & ITERPARSE_FILTER_START:
            if self._tag_tuple is None or \
                   _tagMatches(node._c_node, self._tag_href, self._tag_name):
                python.PyList_Append(self._events, ("start", node))
        return ns_count

    cdef _Element _end_node(self):
        cdef _Element node
        cdef int i, ns_count
        node, ns_count = self._pop_node()
        if self._event_filter & ITERPARSE_FILTER_END:
            if self._tag_tuple is None or \
                   _tagMatches(node._c_node, self._tag_href, self._tag_name):
                python.PyList_Append(self._events, ("end", node))
        if self._event_filter & ITERPARSE_FILTER_END_NS:
            event = ("end-ns", None)
            for i from 0 <= i < ns_count:
                python.PyList_Append(self._events, event)
        return node
