# iterparse -- incremental parsing

cdef object __ITERPARSE_CHUNK_SIZE
__ITERPARSE_CHUNK_SIZE = 16384

ctypedef enum IterparseEventFilter:
    ITERPARSE_FILTER_START     = 1
    ITERPARSE_FILTER_END       = 2
    ITERPARSE_FILTER_START_NS  = 4
    ITERPARSE_FILTER_END_NS    = 8

cdef int _buildIterparseEventFilter(events):
    cdef int event_filter
    event_filter = 0
    if 'start' in events:
        event_filter = event_filter | ITERPARSE_FILTER_START
    if 'end' in events:
        event_filter = event_filter | ITERPARSE_FILTER_END
    if 'start-ns' in events:
        event_filter = event_filter | ITERPARSE_FILTER_START_NS
    if 'end-ns' in events:
        event_filter = event_filter | ITERPARSE_FILTER_END_NS
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

cdef class _IterparseResolverContext(_ResolverContext):
    cdef xmlparser.startElementNsSAX2Func _origSaxStart
    cdef xmlparser.endElementNsSAX2Func   _origSaxEnd
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

    def __init__(self, *args):
        _ResolverContext.__init__(self, *args)
        self._ns_stack = []
        self._pop_ns = self._ns_stack.pop
        self._node_stack = []
        self._pop_node = self._node_stack.pop
        self._events = []
        self._event_index = 0

    cdef void _wrapCallbacks(self, xmlparser.xmlSAXHandler* sax):
        "wrap original SAX2 callbacks"
        self._origSaxStart = sax.startElementNs
        # only override start event handler if needed
        if self._event_filter == 0 or \
               self._event_filter & (ITERPARSE_FILTER_START | \
                                     ITERPARSE_FILTER_START_NS | \
                                     ITERPARSE_FILTER_END_NS):
           sax.startElementNs = _saxStart

        self._origSaxEnd = sax.endElementNs
        # only override end event handler if needed
        if self._event_filter == 0 or \
               self._event_filter & (ITERPARSE_FILTER_END | \
                                     ITERPARSE_FILTER_END_NS):
            sax.endElementNs = _saxEnd

    cdef void _setEventFilter(self, events, tag):
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

    cdef void startNode(self, xmlNode* c_node):
        cdef _Element node
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

    cdef void endNode(self, xmlNode* c_node):
        cdef _Element node
        cdef xmlNs* c_ns
        cdef int ns_count
        if self._event_filter & ITERPARSE_FILTER_END:
            if self._tag_tuple is None or \
                   _tagMatches(c_node, self._tag_href, self._tag_name):
                if self._event_filter & (ITERPARSE_FILTER_START | \
                                         ITERPARSE_FILTER_START_NS | \
                                         ITERPARSE_FILTER_END_NS):
                    node = self._pop_node()
                    assert node._c_node is c_node
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
                

cdef void _pushSaxStartEvent(xmlparser.xmlParserCtxt* c_ctxt, xmlNode* c_node):
    cdef _IterparseResolverContext context
    context = <_IterparseResolverContext>c_ctxt._private
    context.startNode(c_node)

cdef void _pushSaxEndEvent(xmlparser.xmlParserCtxt* c_ctxt, xmlNode* c_node):
    cdef _IterparseResolverContext context
    context = <_IterparseResolverContext>c_ctxt._private
    context.endNode(c_node)

cdef xmlparser.startElementNsSAX2Func _getOrigStart(xmlparser.xmlParserCtxt* c_ctxt):
    return (<_IterparseResolverContext>c_ctxt._private)._origSaxStart

cdef xmlparser.endElementNsSAX2Func _getOrigEnd(xmlparser.xmlParserCtxt* c_ctxt):
    return (<_IterparseResolverContext>c_ctxt._private)._origSaxEnd

cdef void _saxStart(void* ctxt, char* localname, char* prefix, char* URI,
                    int nb_namespaces, char** namespaces,
                    int nb_attributes, int nb_defaulted, char** attributes):
    # no Python in here!
    cdef xmlparser.xmlParserCtxt* c_ctxt
    cdef xmlparser.startElementNsSAX2Func origStart
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    origStart = _getOrigStart(c_ctxt)
    origStart(ctxt, localname, prefix, URI, nb_namespaces, namespaces,
              nb_attributes, nb_defaulted, attributes)
    _pushSaxStartEvent(c_ctxt, c_ctxt.node)

cdef void _saxEnd(void* ctxt, char* localname, char* prefix, char* URI):
    # no Python in here!
    cdef xmlparser.xmlParserCtxt* c_ctxt
    cdef xmlparser.endElementNsSAX2Func origEnd
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    _pushSaxEndEvent(c_ctxt, c_ctxt.node)
    origEnd = _getOrigEnd(c_ctxt)
    origEnd(ctxt, localname, prefix, URI)

cdef class iterparse(_BaseParser):
    """Incremental parser.  Parses XML into a tree and generates tuples
    (event, element) in a SAX-like fashion. ``event`` is any of 'start',
    'end', 'start-ns', 'end-ns'.

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
    * attribute_defaults - read default attributes from DTD
    * dtd_validation     - validate (if DTD is available)
    * load_dtd           - use DTD for parsing
    * no_network         - prevent network access
    * remove_blank_text  - discard blank text nodes
    """
    cdef object _source
    cdef object _filename
    cdef readonly object root
    def __init__(self, source, events=("end",), tag=None,
                 attribute_defaults=False, dtd_validation=False,
                 load_dtd=False, no_network=False, remove_blank_text=False):
        cdef _IterparseResolverContext context
        cdef char* c_filename
        cdef int parse_options
        if not hasattr(source, 'read'):
            self._filename = _encodeFilename(source)
            source = open(self._filename, 'rb')
        else:
            self._filename = _getFilenameForFile(source)
            if self._filename is not None:
                self._filename = _encodeFilename(self._filename)
        if self._filename is not None:
            c_filename = self._filename
        else:
            c_filename = NULL

        self._source = source
        _BaseParser.__init__(self, _IterparseResolverContext)

        parse_options = _XML_DEFAULT_PARSE_OPTIONS
        if load_dtd:
            parse_options = parse_options | xmlparser.XML_PARSE_DTDLOAD
        if dtd_validation:
            parse_options = parse_options | xmlparser.XML_PARSE_DTDVALID | \
                            xmlparser.XML_PARSE_DTDLOAD
        if attribute_defaults:
            parse_options = parse_options | xmlparser.XML_PARSE_DTDATTR | \
                            xmlparser.XML_PARSE_DTDLOAD
        if no_network:
            parse_options = parse_options | xmlparser.XML_PARSE_NONET
        if remove_blank_text:
            parse_options = parse_options | xmlparser.XML_PARSE_NOBLANKS
        self._parse_options = parse_options

        context = <_IterparseResolverContext>self._context
        context._setEventFilter(events, tag)
        context._wrapCallbacks(self._parser_ctxt.sax)
        xmlparser.xmlCtxtUseOptions(self._parser_ctxt, parse_options)
        xmlparser.xmlCtxtResetPush(self._parser_ctxt, NULL, 0, c_filename, NULL)
        self._lockParser() # will not be unlocked - no other methods supported

    def __iter__(self):
        return self

    def __next__(self):
        cdef _IterparseResolverContext context
        cdef int error
        cdef char* c_filename
        if self._source is None:
            raise StopIteration
        context = <_IterparseResolverContext>self._context
        if python.PyList_GET_SIZE(context._events) > context._event_index:
            item = python.PyList_GET_ITEM(context._events, context._event_index)
            python.Py_INCREF(item) # 'borrowed reference' from PyList_GET_ITEM
            context._event_index = context._event_index + 1
            return item

        del context._events[:]
        error = 0
        while python.PyList_GET_SIZE(context._events) == 0 and error == 0:
            data = self._source.read(__ITERPARSE_CHUNK_SIZE)
            if not python.PyString_Check(data):
                #xmlparser.xmlParseChunk(self._parser_ctxt, NULL, 0, 1)
                self._source = None
                raise TypeError, "reading file objects must return plain strings"
            elif data:
                error = xmlparser.xmlParseChunk(
                    self._parser_ctxt, _cstr(data),
                    python.PyString_GET_SIZE(data), 0)
            else:
                error = xmlparser.xmlParseChunk(self._parser_ctxt, NULL, 0, 1)
                self._source = None
                break
        if error != 0:
            self._source = None
            _raiseParseError(self._parser_ctxt, self._filename)
        if python.PyList_GET_SIZE(context._events) == 0:
            self.root = context._root
            raise StopIteration

        context._event_index = 1
        element = python.PyList_GET_ITEM(context._events, 0)
        python.Py_INCREF(element) # 'borrowed reference' from PyList_GET_ITEM
        return element


cdef class iterwalk:
    """A tree walker that generates ``iterparse()`` events from an existing
    tree as if it was parsing XML data.
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
        cdef _NodeBase root
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
        cdef _NodeBase node
        cdef _NodeBase next_node
        cdef int ns_count
        if python.PyList_GET_SIZE(self._events):
            return self._pop_event(0)
        ns_count = 0
        # find next node
        while self._index >= 0:
            node_tuple = python.PyList_GET_ITEM(self._node_stack, self._index)
            python.Py_INCREF(node_tuple) # fix borrowed reference for Pyrex!
            node = python.PyTuple_GET_ITEM(node_tuple, 0)
            python.Py_INCREF(node) # fix borrowed reference for Pyrex!
            if node:
                # try children
                next_node = node[0]
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

    cdef int _start_node(self, _NodeBase node):
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

    cdef _NodeBase _end_node(self):
        cdef _NodeBase node
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
