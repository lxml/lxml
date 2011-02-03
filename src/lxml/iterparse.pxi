# iterparse -- event-driven parsing

DEF __ITERPARSE_CHUNK_SIZE = 32768

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
        if event == u'start':
            event_filter |= ITERPARSE_FILTER_START
        elif event == u'end':
            event_filter |= ITERPARSE_FILTER_END
        elif event == u'start-ns':
            event_filter |= ITERPARSE_FILTER_START_NS
        elif event == u'end-ns':
            event_filter |= ITERPARSE_FILTER_END_NS
        elif event == u'comment':
            event_filter |= ITERPARSE_FILTER_COMMENT
        elif event == u'pi':
            event_filter |= ITERPARSE_FILTER_PI
        else:
            raise ValueError, u"invalid event name '%s'" % event
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

cdef int _appendStartNsEvents(xmlNode* c_node, list event_list):
    cdef xmlNs* c_ns
    cdef int count
    count = 0
    c_ns = c_node.nsDef
    while c_ns is not NULL:
        if c_ns.prefix is NULL:
            if python.IS_PYTHON3:
                prefix = u''
            else:
                prefix = ''
        else:
            prefix = funicode(c_ns.prefix)
        ns_tuple = (prefix, funicode(c_ns.href))
        event_list.append( (u"start-ns", ns_tuple) )
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
    cdef list _events
    cdef int _event_index
    cdef list _ns_stack
    cdef object _pop_ns
    cdef list _node_stack
    cdef object _pop_node
    cdef tuple _tag_tuple
    cdef char*  _tag_href
    cdef char*  _tag_name

    def __cinit__(self):
        self._ns_stack = []
        self._pop_ns = self._ns_stack.pop
        self._node_stack = []
        self._pop_node = self._node_stack.pop
        self._events = []
        self._event_index = 0

    cdef void _initParserContext(self, xmlparser.xmlParserCtxt* c_ctxt):
        u"wrap original SAX2 callbacks"
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
        if tag is None or tag == u'*':
            self._tag_href  = NULL
            self._tag_name  = NULL
        else:
            self._tag_tuple = _getNsTag(tag)
            href, name = self._tag_tuple
            if href is None or href == b'*':
                self._tag_href = NULL
            else:
                self._tag_href = _cstr(href)
            if name is None or name == b'*':
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
            self._ns_stack.append(ns_count)
        if self._root is None:
            if self._doc is None:
                self._doc = _documentFactory(c_node.doc, None)
            self._root = self._doc.getroot()
        if self._tag_tuple is None or \
               _tagMatches(c_node, self._tag_href, self._tag_name):
            node = _elementFactory(self._doc, c_node)
            if self._event_filter & ITERPARSE_FILTER_END:
                self._node_stack.append(node)
            if self._event_filter & ITERPARSE_FILTER_START:
                self._events.append( (u"start", node) )
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
                    if self._root is None:
                        if self._doc is None:
                            self._doc = _documentFactory(c_node.doc, None)
                        self._root = self._doc.getroot()
                    node = _elementFactory(self._doc, c_node)
                self._events.append( (u"end", node) )

        if self._event_filter & ITERPARSE_FILTER_END_NS:
            ns_count = self._pop_ns()
            if ns_count > 0:
                event = (u"end-ns", None)
                for i from 0 <= i < ns_count:
                    self._events.append(event)
        return 0

    cdef int pushEvent(self, event, xmlNode* c_node) except -1:
        cdef _Element root
        if self._doc is None:
            self._doc = _documentFactory(c_node.doc, None)
            root = self._doc.getroot()
            if root is not None and root._c_node.type == tree.XML_ELEMENT_NODE:
                self._root = root
        node = _elementFactory(self._doc, c_node)
        self._events.append( (event, node) )
        return 0

    cdef void _assureDocGetsFreed(self):
        if self._c_ctxt.myDoc is not NULL and self._doc is None:
            tree.xmlFreeDoc(self._c_ctxt.myDoc)
            self._c_ctxt.myDoc = NULL


cdef inline void _pushSaxStartEvent(_IterparseContext context,
                                    xmlNode* c_node):
    try:
        if context._c_ctxt.html:
            _fixHtmlDictNodeNames(context._c_ctxt.dict, c_node)
        context.startNode(c_node)
    except:
        if context._c_ctxt.errNo == xmlerror.XML_ERR_OK:
            context._c_ctxt.errNo = xmlerror.XML_ERR_INTERNAL_ERROR
        context._c_ctxt.disableSAX = 1
        context._store_raised()

cdef inline void _pushSaxEndEvent(_IterparseContext context,
                                  xmlNode* c_node):
    try:
        context.endNode(c_node)
    except:
        if context._c_ctxt.errNo == xmlerror.XML_ERR_OK:
            context._c_ctxt.errNo = xmlerror.XML_ERR_INTERNAL_ERROR
        context._c_ctxt.disableSAX = 1
        context._store_raised()

cdef inline void _pushSaxEvent(_IterparseContext context,
                               event, xmlNode* c_node):
    try:
        context.pushEvent(event, c_node)
    except:
        if context._c_ctxt.errNo == xmlerror.XML_ERR_OK:
            context._c_ctxt.errNo = xmlerror.XML_ERR_INTERNAL_ERROR
        context._c_ctxt.disableSAX = 1
        context._store_raised()

cdef void _iterparseSaxStart(void* ctxt, char* localname, char* prefix,
                             char* URI, int nb_namespaces, char** namespaces,
                             int nb_attributes, int nb_defaulted,
                             char** attributes):
    cdef xmlparser.xmlParserCtxt* c_ctxt
    cdef _IterparseContext context
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    context = <_IterparseContext>c_ctxt._private
    context._origSaxStart(
        ctxt, localname, prefix, URI,
        nb_namespaces, namespaces,
        nb_attributes, nb_defaulted, attributes)
    _pushSaxStartEvent(context, c_ctxt.node)

cdef void _iterparseSaxEnd(void* ctxt, char* localname, char* prefix, char* URI):
    cdef xmlparser.xmlParserCtxt* c_ctxt
    cdef _IterparseContext context
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    context = <_IterparseContext>c_ctxt._private
    _pushSaxEndEvent(context, c_ctxt.node)
    context._origSaxEnd(ctxt, localname, prefix, URI)

cdef void _iterparseSaxStartNoNs(void* ctxt, char* name, char** attributes):
    cdef xmlparser.xmlParserCtxt* c_ctxt
    cdef _IterparseContext context
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    context = <_IterparseContext>c_ctxt._private
    context._origSaxStartNoNs(ctxt, name, attributes)
    _pushSaxStartEvent(context, c_ctxt.node)

cdef void _iterparseSaxEndNoNs(void* ctxt, char* name):
    cdef xmlparser.xmlParserCtxt* c_ctxt
    cdef _IterparseContext context
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    context = <_IterparseContext>c_ctxt._private
    _pushSaxEndEvent(context, c_ctxt.node)
    context._origSaxEndNoNs(ctxt, name)

cdef void _iterparseSaxComment(void* ctxt, char* text):
    cdef xmlNode* c_node
    cdef xmlparser.xmlParserCtxt* c_ctxt
    cdef _IterparseContext context
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    context = <_IterparseContext>c_ctxt._private
    context._origSaxComment(ctxt, text)
    c_node = _iterparseFindLastNode(c_ctxt)
    if c_node is not NULL:
        _pushSaxEvent(context, u"comment", c_node)

cdef void _iterparseSaxPI(void* ctxt, char* target, char* data):
    cdef xmlNode* c_node
    cdef xmlparser.xmlParserCtxt* c_ctxt
    cdef _IterparseContext context
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    context = <_IterparseContext>c_ctxt._private
    context._origSaxPI(ctxt, target, data)
    c_node = _iterparseFindLastNode(c_ctxt)
    if c_node is not NULL:
        _pushSaxEvent(context, u"pi", c_node)

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
    u"""iterparse(self, source, events=("end",), tag=None, attribute_defaults=False, dtd_validation=False, load_dtd=False, no_network=True, remove_blank_text=False, remove_comments=False, remove_pis=False, encoding=None, html=False, huge_tree=False, schema=None)

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
     - attribute_defaults: read default attributes from DTD
     - dtd_validation: validate (if DTD is available)
     - load_dtd: use DTD for parsing
     - no_network: prevent network access for related files
     - remove_blank_text: discard blank text nodes
     - remove_comments: discard comments
     - remove_pis: discard processing instructions
     - strip_cdata: replace CDATA sections by normal text content (default: True)
     - compact: safe memory for short text content (default: True)
     - resolve_entities: replace entities by their text value (default: True)
     - huge_tree: disable security restrictions and support very deep trees
                  and very long text content (only affects libxml2 2.7+)

    Other keyword arguments:
     - encoding: override the document encoding
     - schema: an XMLSchema to validate against
    """
    cdef object _tag
    cdef object _events
    cdef readonly object root
    cdef object _source
    cdef object _buffer
    cdef int (*_parse_chunk)(xmlparser.xmlParserCtxt* ctxt,
                             char* chunk, int size, int terminate) nogil

    def __init__(self, source, events=(u"end",), *, tag=None,
                 attribute_defaults=False, dtd_validation=False,
                 load_dtd=False, no_network=True, remove_blank_text=False,
                 compact=True, resolve_entities=True, remove_comments=False,
                 remove_pis=False, strip_cdata=True, encoding=None,
                 html=False, huge_tree=False, XMLSchema schema=None):
        cdef _IterparseContext context
        cdef char* c_encoding
        cdef int parse_options
        if not hasattr(source, u'read'):
            filename = _encodeFilename(source)
            if not python.IS_PYTHON3:
                source = filename
            source = open(source, u'rb')
        else:
            filename = _encodeFilename(_getFilenameForFile(source))

        self._source = source
        if html:
            # make sure we're not looking for namespaces
            events = tuple([ event for event in events
                             if event != u'start-ns' and event != u'end-ns' ])

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
        if huge_tree:
            parse_options = parse_options | xmlparser.XML_PARSE_HUGE
        if not no_network:
            parse_options = parse_options ^ xmlparser.XML_PARSE_NONET
        if not compact:
            parse_options = parse_options ^ xmlparser.XML_PARSE_COMPACT
        if not resolve_entities:
            parse_options = parse_options ^ xmlparser.XML_PARSE_NOENT
        if not strip_cdata:
            parse_options = parse_options ^ xmlparser.XML_PARSE_NOCDATA

        _BaseParser.__init__(self, parse_options, html, schema,
                             remove_comments, remove_pis, strip_cdata,
                             None, filename, encoding)

        if self._for_html:
            self._parse_chunk = htmlparser.htmlParseChunk
        else:
            self._parse_chunk = xmlparser.xmlParseChunk

        context = <_IterparseContext>self._getPushParserContext()
        __GLOBAL_PARSER_CONTEXT.initParserDict(context._c_ctxt)

        if self._default_encoding is not None:
            if self._for_html:
                error = _htmlCtxtResetPush(
                    context._c_ctxt, NULL, 0,
                    _cstr(self._default_encoding), self._parse_options)
            else:
                xmlparser.xmlCtxtUseOptions(
                    context._c_ctxt, self._parse_options)
                error = xmlparser.xmlCtxtResetPush(
                    context._c_ctxt, NULL, 0, NULL,
                    _cstr(self._default_encoding))

        context.prepare()
        # parser will not be unlocked - no other methods supported

    property error_log:
        u"""The error log of the last (or current) parser run.
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

    cdef _close_source(self):
        if self._source is None:
            return
        try:
            close = self._source.close
        except AttributeError:
            close = None
        finally:
            self._source = None
        if close is not None:
            close()

    def copy(self):
        raise TypeError, u"iterparse parsers cannot be copied"

    def __iter__(self):
        return self

    def __next__(self):
        cdef _IterparseContext context
        if self._source is None:
            raise StopIteration

        context = <_IterparseContext>self._push_parser_context
        if python.PyList_GET_SIZE(context._events) <= context._event_index:
            self._read_more_events(context)
        item = python.PyList_GET_ITEM(context._events, context._event_index)
        python.Py_INCREF(item) # 'borrowed reference' from PyList_GET_ITEM
        context._event_index += 1
        return item

    cdef _read_more_events(self, _IterparseContext context):
        cdef cstd.FILE* c_stream
        cdef char* c_data
        cdef Py_ssize_t c_data_len
        cdef xmlparser.xmlParserCtxt* pctxt = context._c_ctxt
        cdef int error = 0, done = 0

        del context._events[:]
        context._event_index = 0
        c_stream = python.PyFile_AsFile(self._source)
        while python.PyList_GET_SIZE(context._events) == 0:
            if c_stream is NULL:
                data = self._source.read(__ITERPARSE_CHUNK_SIZE)
                if not python.PyBytes_Check(data):
                    self._close_source()
                    raise TypeError, u"reading file objects must return plain strings"
                c_data_len = python.PyBytes_GET_SIZE(data)
                c_data = _cstr(data)
                done = (c_data_len == 0)
                error = self._parse_chunk(pctxt, c_data, c_data_len, done)
            else:
                if self._buffer is None:
                    self._buffer = python.PyBytes_FromStringAndSize(
                        NULL, __ITERPARSE_CHUNK_SIZE)
                c_data = _cstr(self._buffer)
                with nogil:
                    c_data_len = cstd.fread(
                        c_data, 1, __ITERPARSE_CHUNK_SIZE, c_stream)
                    if c_data_len < __ITERPARSE_CHUNK_SIZE:
                        if cstd.ferror(c_stream):
                            error = 1
                        elif cstd.feof(c_stream):
                            done = 1
                if not error:
                    error = self._parse_chunk(
                        pctxt, c_data, c_data_len, done)
            if error or done:
                self._buffer = None
                break

        if not error and context._validator is not None:
            error = not context._validator.isvalid()
        if error:
            self._close_source()
            del context._events[:]
            context._assureDocGetsFreed()
            _raiseParseError(pctxt, self._filename, context._error_log)
        if python.PyList_GET_SIZE(context._events) == 0:
            self.root = context._root
            self._close_source()
            raise StopIteration


cdef class iterwalk:
    u"""iterwalk(self, element_or_tree, events=("end",), tag=None)

    A tree walker that generates events from an existing tree as if it
    was parsing XML data with ``iterparse()``.
    """
    cdef list   _node_stack
    cdef object _pop_node
    cdef int    _index
    cdef list   _events
    cdef object _pop_event
    cdef int    _event_filter
    cdef tuple  _tag_tuple
    cdef char*  _tag_href
    cdef char*  _tag_name

    def __init__(self, element_or_tree, events=(u"end",), tag=None):
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
            self._node_stack.append( (root, ns_count) )
        else:
            self._index = -1

    cdef void _setTagFilter(self, tag):
        if tag is None or tag == u'*':
            self._tag_href  = NULL
            self._tag_name  = NULL
        else:
            self._tag_tuple = _getNsTag(tag)
            href, name = self._tag_tuple
            if href is None or href == b'*':
                self._tag_href = NULL
            else:
                self._tag_href = _cstr(href)
            if name is None or name == b'*':
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
        if self._events:
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
                    self._index -= 1
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
                self._node_stack.append( (next_node, ns_count) )
                self._index += 1
            if self._events:
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
                self._events.append( (u"start", node) )
        return ns_count

    cdef _Element _end_node(self):
        cdef _Element node
        cdef int i, ns_count
        node, ns_count = self._pop_node()
        if self._event_filter & ITERPARSE_FILTER_END:
            if self._tag_tuple is None or \
                   _tagMatches(node._c_node, self._tag_href, self._tag_name):
                self._events.append( (u"end", node) )
        if self._event_filter & ITERPARSE_FILTER_END_NS:
            event = (u"end-ns", None)
            for i from 0 <= i < ns_count:
                self._events.append(event)
        return node
