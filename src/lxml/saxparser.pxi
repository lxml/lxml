# SAX-like interfaces

class XMLSyntaxAssertionError(XMLSyntaxError, AssertionError):
    """
    An XMLSyntaxError that additionally inherits from AssertionError for
    ElementTree / backwards compatibility reasons.

    This class may get replaced by a plain XMLSyntaxError in a future version.
    """
    def __init__(self, message):
        XMLSyntaxError.__init__(self, message, None, 0, 1)


ctypedef enum _SaxParserEvents:
    SAX_EVENT_START    = 1 << 0
    SAX_EVENT_END      = 1 << 1
    SAX_EVENT_DATA     = 1 << 2
    SAX_EVENT_DOCTYPE  = 1 << 3
    SAX_EVENT_PI       = 1 << 4
    SAX_EVENT_COMMENT  = 1 << 5
    SAX_EVENT_START_NS = 1 << 6
    SAX_EVENT_END_NS   = 1 << 7

ctypedef enum _ParseEventFilter:
    PARSE_EVENT_FILTER_START     = 1 << 0
    PARSE_EVENT_FILTER_END       = 1 << 1
    PARSE_EVENT_FILTER_START_NS  = 1 << 2
    PARSE_EVENT_FILTER_END_NS    = 1 << 3
    PARSE_EVENT_FILTER_COMMENT   = 1 << 4
    PARSE_EVENT_FILTER_PI        = 1 << 5


cdef int _buildParseEventFilter(events) except -1:
    cdef int event_filter = 0
    for event in events:
        if event == 'start':
            event_filter |= PARSE_EVENT_FILTER_START
        elif event == 'end':
            event_filter |= PARSE_EVENT_FILTER_END
        elif event == 'start-ns':
            event_filter |= PARSE_EVENT_FILTER_START_NS
        elif event == 'end-ns':
            event_filter |= PARSE_EVENT_FILTER_END_NS
        elif event == 'comment':
            event_filter |= PARSE_EVENT_FILTER_COMMENT
        elif event == 'pi':
            event_filter |= PARSE_EVENT_FILTER_PI
        else:
            raise ValueError, f"invalid event name '{event}'"
    return event_filter


cdef class _SaxParserTarget:
    cdef int _sax_event_filter

    cdef _handleSaxStart(self, tag, attrib, nsmap):
        return None
    cdef _handleSaxEnd(self, tag):
        return None
    cdef int _handleSaxData(self, data) except -1:
        return 0
    cdef int _handleSaxDoctype(self, root_tag, public_id, system_id) except -1:
        return 0
    cdef _handleSaxPi(self, target, data):
        return None
    cdef _handleSaxComment(self, comment):
        return None
    cdef _handleSaxStartNs(self, prefix, uri):
        return None
    cdef _handleSaxEndNs(self, prefix):
        return None


#@cython.final
@cython.internal
@cython.no_gc_clear  # Required because parent class uses it - Cython bug.
cdef class _SaxParserContext(_ParserContext):
    """This class maps SAX2 events to parser target events.
    """
    cdef _SaxParserTarget _target
    cdef _BaseParser _parser
    cdef xmlparser.startElementNsSAX2Func _origSaxStart
    cdef xmlparser.endElementNsSAX2Func   _origSaxEnd
    cdef xmlparser.startElementSAXFunc    _origSaxStartNoNs
    cdef xmlparser.endElementSAXFunc      _origSaxEndNoNs
    cdef xmlparser.charactersSAXFunc      _origSaxData
    cdef xmlparser.cdataBlockSAXFunc      _origSaxCData
    cdef xmlparser.internalSubsetSAXFunc  _origSaxDoctype
    cdef xmlparser.commentSAXFunc         _origSaxComment
    cdef xmlparser.processingInstructionSAXFunc _origSaxPI
    cdef xmlparser.startDocumentSAXFunc   _origSaxStartDocument

    # for event collecting
    cdef int _event_filter
    cdef list _ns_stack
    cdef list _end_node_stack
    cdef list _pending_events  # None after running empty
    cdef _ParseEventsIterator events_iterator

    # for iterparse
    cdef _Element  _root
    cdef _MultiTagMatcher _matcher

    def __cinit__(self, _BaseParser parser):
        self._ns_stack = []
        self._end_node_stack = []
        self._pending_events = None
        self._parser = parser
        self.events_iterator = _ParseEventsIterator()

    cdef void _setSaxParserTarget(self, _SaxParserTarget target) noexcept:
        self._target = target

    cdef void _initParserContext(self, xmlparser.xmlParserCtxt* c_ctxt) noexcept:
        _ParserContext._initParserContext(self, c_ctxt)
        if self._target is not None:
            self._connectTarget(c_ctxt)
        elif self._event_filter:
            self._connectEvents(c_ctxt)

    cdef void _connectTarget(self, xmlparser.xmlParserCtxt* c_ctxt) noexcept:
        """Wrap original SAX2 callbacks to call into parser target.
        """
        sax = c_ctxt.sax
        self._origSaxStart = sax.startElementNs = NULL
        self._origSaxStartNoNs = sax.startElement = NULL
        if self._target._sax_event_filter & (SAX_EVENT_START |
                                             SAX_EVENT_START_NS |
                                             SAX_EVENT_END_NS):
            # intercept => overwrite orig callback
            # FIXME: also intercept on when collecting END events
            if sax.initialized == xmlparser.XML_SAX2_MAGIC:
                sax.startElementNs = _handleSaxTargetStart
            if self._target._sax_event_filter & SAX_EVENT_START:
                sax.startElement = _handleSaxTargetStartNoNs

        self._origSaxEnd = sax.endElementNs = NULL
        self._origSaxEndNoNs = sax.endElement = NULL
        if self._target._sax_event_filter & (SAX_EVENT_END |
                                             SAX_EVENT_END_NS):
            if sax.initialized == xmlparser.XML_SAX2_MAGIC:
                sax.endElementNs = _handleSaxEnd
            if self._target._sax_event_filter & SAX_EVENT_END:
                sax.endElement = _handleSaxEndNoNs

        self._origSaxData = sax.characters = sax.cdataBlock = NULL
        if self._target._sax_event_filter & SAX_EVENT_DATA:
            sax.characters = sax.cdataBlock = _handleSaxData

        # doctype propagation is always required for entity replacement
        self._origSaxDoctype = sax.internalSubset
        if self._target._sax_event_filter & SAX_EVENT_DOCTYPE:
            sax.internalSubset = _handleSaxTargetDoctype

        self._origSaxPI = sax.processingInstruction = NULL
        if self._target._sax_event_filter & SAX_EVENT_PI:
            sax.processingInstruction = _handleSaxTargetPI

        self._origSaxComment = sax.comment = NULL
        if self._target._sax_event_filter & SAX_EVENT_COMMENT:
            sax.comment = _handleSaxTargetComment

        # enforce entity replacement
        sax.reference = NULL
        c_ctxt.replaceEntities = 1

    cdef void _connectEvents(self, xmlparser.xmlParserCtxt* c_ctxt) noexcept:
        """Wrap original SAX2 callbacks to collect parse events without parser target.
        """
        sax = c_ctxt.sax
        self._origSaxStartDocument = sax.startDocument
        sax.startDocument = _handleSaxStartDocument

        # only override "start" event handler if needed
        self._origSaxStart = sax.startElementNs
        if self._event_filter == 0 or c_ctxt.html or \
               self._event_filter & (PARSE_EVENT_FILTER_START |
                                     PARSE_EVENT_FILTER_END |
                                     PARSE_EVENT_FILTER_START_NS |
                                     PARSE_EVENT_FILTER_END_NS):
            sax.startElementNs = <xmlparser.startElementNsSAX2Func>_handleSaxStart

        self._origSaxStartNoNs = sax.startElement
        if self._event_filter == 0 or c_ctxt.html or \
               self._event_filter & (PARSE_EVENT_FILTER_START |
                                     PARSE_EVENT_FILTER_END):
            sax.startElement = <xmlparser.startElementSAXFunc>_handleSaxStartNoNs

        # only override "end" event handler if needed
        self._origSaxEnd = sax.endElementNs
        if self._event_filter == 0 or \
               self._event_filter & (PARSE_EVENT_FILTER_END |
                                     PARSE_EVENT_FILTER_END_NS):
            sax.endElementNs = <xmlparser.endElementNsSAX2Func>_handleSaxEnd

        self._origSaxEndNoNs = sax.endElement
        if self._event_filter == 0 or \
               self._event_filter & PARSE_EVENT_FILTER_END:
            sax.endElement = <xmlparser.endElementSAXFunc>_handleSaxEndNoNs

        self._origSaxComment = sax.comment
        if self._event_filter & PARSE_EVENT_FILTER_COMMENT:
            sax.comment = <xmlparser.commentSAXFunc>_handleSaxComment

        self._origSaxPI = sax.processingInstruction
        if self._event_filter & PARSE_EVENT_FILTER_PI:
            sax.processingInstruction = <xmlparser.processingInstructionSAXFunc>_handleSaxPIEvent

    @cython.final
    cdef _setEventFilter(self, events, tag):
        self._event_filter = _buildParseEventFilter(events)
        if not self._event_filter or tag is None or tag == '*':
            self._matcher = None
        else:
            self._matcher = _MultiTagMatcher.__new__(_MultiTagMatcher, tag)

    cdef int startDocument(self, xmlDoc* c_doc) except -1:
        try:
            self._doc = _documentFactory(c_doc, self._parser)
        finally:
            self._parser = None  # clear circular reference ASAP
        if self._matcher is not None:
            self._matcher.cacheTags(self._doc, force_into_dict=True)
        return 0

    @cython.inline
    cdef bint _isRetainingEvents(self):
        cdef xmlparser.xmlParserCtxt* c_ctxt = self._c_ctxt
        if c_ctxt.inputNr > 1 and c_ctxt.options & xmlparser.XML_PARSE_NOENT:
            # libxml2 has started parsing a parsed (external) entity. Collect events until it's finished.
            if self._pending_events is None:
                self._pending_events = []
            return True
        else:
            return False

    @cython.final
    cdef object _pushNodeEvent(self, event_name, xmlNode* c_node):
        """Push a node event and return the corresponding Element or _PendingNodeEvent.
        """
        if self._isRetainingEvents():
            # Postpone the Element creation until we know that the c_node will persist.
            node = _nodeEventFactory(event_name, c_node)
            self._pending_events.append(node)
        else:
            node = _elementFactory(self._doc, c_node)
            if self._pending_events:
                self._flushPendingEvents()
            self.events_iterator.add_event( (event_name, node) )
        return node

    @cython.final
    cdef int pushNodeEvent(self, event_name, xmlNode* c_node) except -1:
        cdef _Element root
        if self._root is None:
            root = self._doc.getroot()
            if root is not None and root._c_node.type == tree.XML_ELEMENT_NODE:
                self._root = root
        self._pushNodeEvent(event_name, c_node)
        return 0

    @cython.final
    cdef int pushStartEndEvents(self, xmlNode* c_node) except -1:
        cdef bint needs_start_event = self._event_filter & PARSE_EVENT_FILTER_START
        cdef bint needs_end_event = self._target is None and self._event_filter & PARSE_EVENT_FILTER_END

        if not (needs_start_event | needs_end_event):
            return 0

        if self._isRetainingEvents():
            # Postpone the Element creation until we know that the c_node will persist.
            node = _nodeEventFactory('start', c_node)
            if needs_start_event:
                self._pending_events.append(node)
        else:
            node = _elementFactory(self._doc, c_node)
            if self._pending_events:
                self._flushPendingEvents()
            if needs_start_event:
                self.events_iterator.add_event( ('start', node) )

        if needs_end_event:
            self._end_node_stack.append(node)
        return 0

    @cython.final
    cdef int pushEndEventFromStack(self) except -1:
        node = self._end_node_stack.pop()
        if self._isRetainingEvents():
            self._pending_events.append(
                (<_PendingNodeEvent> node).for_event('end') if type(node) is _PendingNodeEvent else ('end', node))
            return 0
        if type(node) is _PendingNodeEvent:
            # Resolve only the node because we store _PendingNodeEvent('start') in self._end_node_stack
            # to avoid the double allocation.
            node = (<_PendingNodeEvent> node).resolve_node(self._doc)
        if self._pending_events:
            self._flushPendingEvents()
        self.events_iterator.add_event( ('end', node) )
        return 0

    @cython.final
    cdef int pushEvent(self, event_name, value) except -1:
        if self._isRetainingEvents():
            self._pending_events.append( (event_name, value) )
        else:
            if self._pending_events:
                self._flushPendingEvents()
            self.events_iterator.add_event( (event_name, value) )

    @cython.final
    cdef int _flushPendingEvents(self) except -1:
        events_queue = self.events_iterator._events
        # The pending events queue shouldn't change while processing it,
        # but it shouldn't hurt to allow it to extend.
        for event in self._pending_events:
            events_queue.append(
                (<_PendingNodeEvent> event).resolve(self._doc) if type(event) is _PendingNodeEvent else event)
        self._pending_events = None
        return 0

    @cython.final
    cdef int flushEvents(self) except -1:
        while self._end_node_stack:
            self.pushEndEventFromStack()
        while self._ns_stack:
            _pushSaxNsEndEvents(self)
        if self._pending_events:
            self._flushPendingEvents()

    @cython.final
    cdef void _handleSaxException(self, xmlparser.xmlParserCtxt* c_ctxt) noexcept:
        _abortParser(c_ctxt)
        # Delete pending events to prevent accessing incomplete state.
        self.events_iterator.abort()
        self._pending_events = None
        del self._end_node_stack[:]
        del self._ns_stack[:]
        self._store_raised()


@cython.final
@cython.internal
cdef class _ParseEventsIterator:
    """A reusable parse events iterator"""
    cdef list _events
    cdef int _event_index

    def __cinit__(self):
        self._events = []
        self._event_index = 0

    @cython.inline
    cdef int add_event(self, event) except -1:
        self._events.append(event)
        return 0

    cdef int abort(self) except -1:
        del self._events[:]
        self._event_index = 0
        return 0

    def __iter__(self):
        return self

    def __next__(self):
        cdef int event_index = self._event_index
        events = self._events
        if event_index >= 2**10 or event_index * 2 >= len(events):
            if event_index:
                # clean up from time to time
                del events[:event_index]
                self._event_index = event_index = 0
            if event_index >= len(events):
                raise StopIteration
        item = events[event_index]
        self._event_index = event_index + 1
        return item


@cython.final
@cython.internal
@cython.freelist(16)
cdef class _PendingNodeEvent:
    """C node wrapper to postpone Element creation until we know we can safely refer to it.
    libxml2 discards trees generated from parsed entity if the parsing fails.
    """
    cdef str event_name
    cdef xmlNode *_c_node

    cdef _PendingNodeEvent for_event(self, event_name):
        return _nodeEventFactory(event_name, self._c_node)

    cdef _Element resolve_node(self, _Document doc):
        return _elementFactory(doc, self._c_node)

    cdef tuple resolve(self, _Document doc):
        return (self.event_name, _elementFactory(doc, self._c_node))


cdef _PendingNodeEvent _nodeEventFactory(str name, xmlNode *c_node):
    cdef _PendingNodeEvent event = _PendingNodeEvent.__new__(_PendingNodeEvent)
    event.event_name = name
    event._c_node = c_node
    return event


cdef list NO_SAX_NAMESPACES = []


cdef list _build_prefix_uri_list(_SaxParserContext context, int c_nb_namespaces,
                                 const_xmlChar** c_namespaces):
    "Build [(prefix, uri)] list of declared namespaces."
    cdef int i
    namespaces = [
        (funicodeOrEmpty(c_namespaces[i]), funicode(c_namespaces[i+1]))
       for i in range(0, c_nb_namespaces * 2, 2)
    ]
    return namespaces


cdef void _handleSaxStart(
        void* ctxt, const_xmlChar* c_localname, const_xmlChar* c_prefix,
        const_xmlChar* c_namespace, int c_nb_namespaces,
        const_xmlChar** c_namespaces,
        int c_nb_attributes, int c_nb_defaulted,
        const_xmlChar** c_attributes) noexcept with gil:
    cdef int i
    cdef size_t c_len
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL or xmlparser.xmlCtxtIsStopped(c_ctxt):
        return
    context = <_SaxParserContext>c_ctxt._private
    cdef int event_filter = context._event_filter
    try:
        if event_filter & (PARSE_EVENT_FILTER_START_NS |
                           PARSE_EVENT_FILTER_END_NS):
            if c_nb_namespaces:
                declared_namespaces = _build_prefix_uri_list(
                    context, c_nb_namespaces, c_namespaces)

                if event_filter & PARSE_EVENT_FILTER_START_NS:
                    for prefix_uri_tuple in declared_namespaces:
                        context.pushEvent("start-ns", prefix_uri_tuple)

                if not (event_filter & PARSE_EVENT_FILTER_END_NS):
                    declared_namespaces = None

            elif event_filter & PARSE_EVENT_FILTER_END_NS:
                # Must push something to allow popping it.
                declared_namespaces = NO_SAX_NAMESPACES
            else:
                declared_namespaces = None
        else:
            declared_namespaces = None

        context._origSaxStart(c_ctxt, c_localname, c_prefix, c_namespace,
                              c_nb_namespaces, c_namespaces, c_nb_attributes,
                              c_nb_defaulted, c_attributes)
        if c_ctxt.html:
            _fixHtmlDictNodeNames(c_ctxt.dict, c_ctxt.node)
            # The HTML parser in libxml2 reports the missing opening tags when it finds
            # misplaced ones, but with tag names from C string constants that ignore the
            # parser dict.  Thus, we need to intern the name ourselves.
            c_localname = tree.xmlDictLookup(c_ctxt.dict, c_localname, -1)
            if c_localname is NULL:
                raise MemoryError()

        if event_filter & (PARSE_EVENT_FILTER_START |
                           PARSE_EVENT_FILTER_END |
                           PARSE_EVENT_FILTER_END_NS):
            _pushSaxStartEvent(context, c_ctxt, c_namespace, c_localname, None, declared_namespaces)
    except:
        context._handleSaxException(c_ctxt)
    finally:
        return  # swallow any further exceptions


cdef void _handleSaxTargetStart(
        void* ctxt, const_xmlChar* c_localname, const_xmlChar* c_prefix,
        const_xmlChar* c_namespace, int c_nb_namespaces,
        const_xmlChar** c_namespaces,
        int c_nb_attributes, int c_nb_defaulted,
        const_xmlChar** c_attributes) noexcept with gil:
    cdef int i
    cdef size_t c_len
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL or xmlparser.xmlCtxtIsStopped(c_ctxt):
        return
    context = <_SaxParserContext>c_ctxt._private

    cdef int event_filter = context._event_filter
    cdef int sax_event_filter = context._target._sax_event_filter
    try:
        if (event_filter & PARSE_EVENT_FILTER_START_NS or
                sax_event_filter & (SAX_EVENT_START_NS | SAX_EVENT_END_NS)):
            if c_nb_namespaces:
                declared_namespaces = _build_prefix_uri_list(
                    context, c_nb_namespaces, c_namespaces)

                if event_filter & PARSE_EVENT_FILTER_START_NS:
                    for prefix_uri_tuple in declared_namespaces:
                        context.pushEvent("start-ns", prefix_uri_tuple)

                if sax_event_filter & SAX_EVENT_START_NS:
                    for prefix, uri in declared_namespaces:
                        context._target._handleSaxStartNs(prefix, uri)

                if not ((event_filter & PARSE_EVENT_FILTER_END_NS) | (sax_event_filter & SAX_EVENT_END_NS)):
                    declared_namespaces = None

            elif event_filter & PARSE_EVENT_FILTER_END_NS or sax_event_filter & SAX_EVENT_END_NS:
                # Must push something to allow popping it.
                declared_namespaces = NO_SAX_NAMESPACES
            else:
                declared_namespaces = None

        elif event_filter & PARSE_EVENT_FILTER_END_NS:
            # Must push something to allow popping it.
            declared_namespaces = [None] * c_nb_namespaces if c_nb_namespaces else NO_SAX_NAMESPACES
        else:
            c_nb_namespaces = 0
            declared_namespaces = None

        if sax_event_filter & SAX_EVENT_START:
            if c_nb_defaulted > 0:
                # only add default attributes if we asked for them
                if c_ctxt.loadsubset & xmlparser.XML_COMPLETE_ATTRS == 0:
                    c_nb_attributes -= c_nb_defaulted
            if c_nb_attributes == 0:
                attrib = IMMUTABLE_EMPTY_MAPPING
            else:
                attrib = {}
                for i in range(c_nb_attributes):
                    name = _namespacedNameFromNsName(
                        c_attributes[2], c_attributes[0])
                    if c_attributes[3] is NULL:
                        value = ''
                    else:
                        c_len = c_attributes[4] - c_attributes[3]
                        value = c_attributes[3][:c_len].decode('utf8')
                    attrib[name] = value
                    c_attributes += 5

            nsmap = dict(declared_namespaces) if c_nb_namespaces and declared_namespaces is not None else IMMUTABLE_EMPTY_MAPPING

            element = _callTargetSaxStart(
                context, c_ctxt,
                _namespacedNameFromNsName(c_namespace, c_localname),
                attrib, nsmap)
        else:
            element = None

        if event_filter & (PARSE_EVENT_FILTER_START |
                           PARSE_EVENT_FILTER_END |
                           PARSE_EVENT_FILTER_END_NS) or declared_namespaces is not None:
            _pushSaxStartEvent(context, c_ctxt, c_namespace,
                               c_localname, element, declared_namespaces)
    except:
        context._handleSaxException(c_ctxt)
    finally:
        return  # swallow any further exceptions


cdef void _handleSaxStartNoNs(void* ctxt, const_xmlChar* c_name,
                              const_xmlChar** c_attributes) noexcept with gil:
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL or xmlparser.xmlCtxtIsStopped(c_ctxt):
        return
    context = <_SaxParserContext>c_ctxt._private
    try:
        context._origSaxStartNoNs(c_ctxt, c_name, c_attributes)
        if c_ctxt.html:
            _fixHtmlDictNodeNames(c_ctxt.dict, c_ctxt.node)
            # The HTML parser in libxml2 reports the missing opening tags when it finds
            # misplaced ones, but with tag names from C string constants that ignore the
            # parser dict.  Thus, we need to intern the name ourselves.
            c_name = tree.xmlDictLookup(c_ctxt.dict, c_name, -1)
            if c_name is NULL:
                raise MemoryError()
        if context._event_filter & (PARSE_EVENT_FILTER_END |
                                    PARSE_EVENT_FILTER_START):
            _pushSaxStartEvent(context, c_ctxt, NULL, c_name, None, None)
    except:
        context._handleSaxException(c_ctxt)
    finally:
        return  # swallow any further exceptions


cdef void _handleSaxTargetStartNoNs(void* ctxt, const_xmlChar* c_name,
                                    const_xmlChar** c_attributes) noexcept with gil:
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL or xmlparser.xmlCtxtIsStopped(c_ctxt):
        return
    context = <_SaxParserContext>c_ctxt._private
    try:
        if c_attributes is NULL:
            attrib = IMMUTABLE_EMPTY_MAPPING
        else:
            attrib = {}
            while c_attributes[0] is not NULL:
                name = funicode(c_attributes[0])
                attrib[name] = funicodeOrEmpty(c_attributes[1])
                c_attributes += 2
        element = _callTargetSaxStart(
            context, c_ctxt, funicode(c_name),
            attrib, IMMUTABLE_EMPTY_MAPPING)
        if context._event_filter & (PARSE_EVENT_FILTER_END |
                                    PARSE_EVENT_FILTER_START):
            _pushSaxStartEvent(context, c_ctxt, NULL, c_name, element, None)
    except:
        context._handleSaxException(c_ctxt)
    finally:
        return  # swallow any further exceptions


cdef _callTargetSaxStart(_SaxParserContext context,
                         xmlparser.xmlParserCtxt* c_ctxt,
                         tag, attrib, nsmap):
    element = context._target._handleSaxStart(tag, attrib, nsmap)
    if element is not None and c_ctxt.input is not NULL:
        if isinstance(element, _Element):
            (<_Element>element)._c_node.line = (
                <unsigned short>c_ctxt.input.line
                if c_ctxt.input.line < 65535 else 65535)
    return element


cdef int _pushSaxStartEvent(_SaxParserContext context,
                            xmlparser.xmlParserCtxt* c_ctxt,
                            const_xmlChar* c_href,
                            const_xmlChar* c_name,
                            node, declared_namespaces) except -1:
    if declared_namespaces is not None:
        context._ns_stack.append(declared_namespaces)
    if (context._matcher is None or
            context._matcher.matchesNsTag(c_href, c_name)):
        if node is not None or context._target is not None:
            # Trust whatever 'node' the target gave us.
            if context._event_filter & PARSE_EVENT_FILTER_START:
                context.pushEvent('start', node)
            if (context._target is None and
                    context._event_filter & PARSE_EVENT_FILTER_END):
                context._end_node_stack.append(node)
        else:
            assert context._doc is not None
            if context._event_filter & (PARSE_EVENT_FILTER_START |
                                        PARSE_EVENT_FILTER_END):
                context.pushStartEndEvents(c_ctxt.node)
    return 0


cdef void _handleSaxEnd(void* ctxt, const_xmlChar* c_localname,
                        const_xmlChar* c_prefix,
                        const_xmlChar* c_namespace) noexcept with gil:
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL or xmlparser.xmlCtxtIsStopped(c_ctxt):
        return
    context = <_SaxParserContext>c_ctxt._private
    try:
        if context._target is not None:
            if context._target._sax_event_filter & SAX_EVENT_END:
                node = context._target._handleSaxEnd(
                    _namespacedNameFromNsName(c_namespace, c_localname))
            else:
                node = None
        else:
            context._origSaxEnd(c_ctxt, c_localname, c_prefix, c_namespace)
            node = None
        _pushSaxEndEvent(context, c_namespace, c_localname, node)
    except:
        context._handleSaxException(c_ctxt)
    finally:
        return  # swallow any further exceptions


cdef void _handleSaxEndNoNs(void* ctxt, const_xmlChar* c_name) noexcept with gil:
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL or xmlparser.xmlCtxtIsStopped(c_ctxt):
        return
    context = <_SaxParserContext>c_ctxt._private
    try:
        if context._target is not None:
            node = context._target._handleSaxEnd(funicode(c_name))
        else:
            context._origSaxEndNoNs(c_ctxt, c_name)
            node = None
        _pushSaxEndEvent(context, NULL, c_name, node)
    except:
        context._handleSaxException(c_ctxt)
    finally:
        return  # swallow any further exceptions


cdef int _pushSaxNsEndEvents(_SaxParserContext context) except -1:
    cdef bint build_events = context._event_filter & PARSE_EVENT_FILTER_END_NS
    cdef bint call_target = (
        context._target is not None
        and context._target._sax_event_filter & SAX_EVENT_END_NS)
    if not build_events and not call_target:
        return 0

    cdef list declared_namespaces = context._ns_stack.pop()
    if declared_namespaces is NO_SAX_NAMESPACES:
        return 0

    cdef tuple prefix_uri
    for prefix_uri in reversed(declared_namespaces):
        if call_target:
            context._target._handleSaxEndNs(prefix_uri[0])
        if build_events:
            context.pushEvent('end-ns', None)

    return 0


cdef int _pushSaxEndEvent(_SaxParserContext context,
                          const_xmlChar* c_href,
                          const_xmlChar* c_name, node) except -1:
    if context._event_filter & PARSE_EVENT_FILTER_END:
        if (context._matcher is None or
                context._matcher.matchesNsTag(c_href, c_name)):
            if context._target is not None:
                # Trust whatever 'node' the target gave us.
                context.pushEvent('end', node)
            else:
                context.pushEndEventFromStack()
    _pushSaxNsEndEvents(context)
    return 0


cdef void _handleSaxData(void* ctxt, const_xmlChar* c_data, int data_len) noexcept with gil:
    # can only be called if parsing with a target
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL or xmlparser.xmlCtxtIsStopped(c_ctxt):
        return
    context = <_SaxParserContext>c_ctxt._private
    try:
        context._target._handleSaxData(
            c_data[:data_len].decode('utf8'))
    except:
        context._handleSaxException(c_ctxt)
    finally:
        return  # swallow any further exceptions


cdef void _handleSaxTargetDoctype(void* ctxt, const_xmlChar* c_name,
                                  const_xmlChar* c_public,
                                  const_xmlChar* c_system) noexcept with gil:
    # can only be called if parsing with a target
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL or xmlparser.xmlCtxtIsStopped(c_ctxt):
        return
    context = <_SaxParserContext>c_ctxt._private
    try:
        context._target._handleSaxDoctype(
            funicodeOrNone(c_name),
            funicodeOrNone(c_public),
            funicodeOrNone(c_system))
    except:
        context._handleSaxException(c_ctxt)
    finally:
        return  # swallow any further exceptions


cdef void _handleSaxStartDocument(void* ctxt) noexcept with gil:
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL or xmlparser.xmlCtxtIsStopped(c_ctxt):
        return
    context = <_SaxParserContext>c_ctxt._private
    context._origSaxStartDocument(ctxt)
    c_doc = c_ctxt.myDoc
    try:
        context.startDocument(c_doc)
    except:
        context._handleSaxException(c_ctxt)
    finally:
        return  # swallow any further exceptions


cdef void _handleSaxTargetPI(void* ctxt, const_xmlChar* c_target,
                             const_xmlChar* c_data) noexcept with gil:
    # can only be called if parsing with a target
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL or xmlparser.xmlCtxtIsStopped(c_ctxt):
        return
    context = <_SaxParserContext>c_ctxt._private
    try:
        pi = context._target._handleSaxPi(
            funicodeOrNone(c_target),
            funicodeOrEmpty(c_data))
        if context._event_filter & PARSE_EVENT_FILTER_PI:
            context._pushEvent('pi', pi)
    except:
        context._handleSaxException(c_ctxt)
    finally:
        return  # swallow any further exceptions


cdef void _handleSaxPIEvent(void* ctxt, const_xmlChar* target,
                            const_xmlChar* data) noexcept with gil:
    # can only be called when collecting pi events
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL or xmlparser.xmlCtxtIsStopped(c_ctxt):
        return
    context = <_SaxParserContext>c_ctxt._private
    context._origSaxPI(ctxt, target, data)
    c_node = _findLastEventNode(c_ctxt)
    if c_node is NULL:
        return
    try:
        context.pushNodeEvent('pi', c_node)
    except:
        context._handleSaxException(c_ctxt)
    finally:
        return  # swallow any further exceptions


cdef void _handleSaxTargetComment(void* ctxt, const_xmlChar* c_data) noexcept with gil:
    # can only be called if parsing with a target
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL or xmlparser.xmlCtxtIsStopped(c_ctxt):
        return
    context = <_SaxParserContext>c_ctxt._private
    try:
        comment = context._target._handleSaxComment(funicodeOrEmpty(c_data))
        if context._event_filter & PARSE_EVENT_FILTER_COMMENT:
            context._pushEvent('comment', comment)
    except:
        context._handleSaxException(c_ctxt)
    finally:
        return  # swallow any further exceptions


cdef void _handleSaxComment(void* ctxt, const_xmlChar* text) noexcept with gil:
    # can only be called when collecting comment events
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL or xmlparser.xmlCtxtIsStopped(c_ctxt):
        return
    context = <_SaxParserContext>c_ctxt._private
    context._origSaxComment(ctxt, text)
    c_node = _findLastEventNode(c_ctxt)
    if c_node is NULL:
        return
    try:
        context.pushNodeEvent('comment', c_node)
    except:
        context._handleSaxException(c_ctxt)
    finally:
        return  # swallow any further exceptions


cdef inline xmlNode* _findLastEventNode(xmlparser.xmlParserCtxt* c_ctxt) noexcept:
    # this mimics what libxml2 creates for comments/PIs
    if c_ctxt.inSubset:
        # Ignore internal/external subset. libxml2 uses the following,
        # but we don't have a document node for the DTDs to create an element proxy.
        # if c_ctxt.inSubset == 1: return c_ctxt.myDoc.intSubset.last
        # if c_ctxt.inSubset == 2: return c_ctxt.myDoc.extSubset.last
        return NULL
    elif c_ctxt.node is NULL:
        return c_ctxt.myDoc.last
    elif c_ctxt.node.type == tree.XML_ELEMENT_NODE:
        return c_ctxt.node.last
    else:
        return c_ctxt.node.next


############################################################
## ET compatible XML tree builder
############################################################

cdef class TreeBuilder(_SaxParserTarget):
    """TreeBuilder(self, element_factory=None, parser=None,
                    comment_factory=None, pi_factory=None,
                    insert_comments=True, insert_pis=True)

    Parser target that builds a tree from parse event callbacks.

    The factory arguments can be used to influence the creation of
    elements, comments and processing instructions.

    By default, comments and processing instructions are inserted into
    the tree, but they can be ignored by passing the respective flags.

    The final tree is returned by the ``close()`` method.
    """
    cdef _BaseParser _parser
    cdef object _factory
    cdef object _comment_factory
    cdef object _pi_factory
    cdef list _data
    cdef list _element_stack
    cdef object _element_stack_pop
    cdef _Element _last # may be None
    cdef bint _in_tail
    cdef bint _insert_comments
    cdef bint _insert_pis

    def __init__(self, *, element_factory=None, parser=None,
                 comment_factory=None, pi_factory=None,
                 bint insert_comments=True, bint insert_pis=True):
        self._sax_event_filter = \
            SAX_EVENT_START | SAX_EVENT_END | SAX_EVENT_DATA | \
            SAX_EVENT_PI | SAX_EVENT_COMMENT
        self._data = [] # data collector
        self._element_stack = [] # element stack
        self._element_stack_pop = self._element_stack.pop
        self._last = None # last element
        self._in_tail = 0 # true if we're after an end tag
        self._factory = element_factory
        self._comment_factory = comment_factory if comment_factory is not None else Comment
        self._pi_factory = pi_factory if pi_factory is not None else ProcessingInstruction
        self._insert_comments = insert_comments
        self._insert_pis = insert_pis
        self._parser = parser

    @cython.final
    cdef int _flush(self) except -1:
        if self._data:
            if self._last is not None:
                text = "".join(self._data)
                if self._in_tail:
                    assert self._last.tail is None, "internal error (tail)"
                    self._last.tail = text
                else:
                    assert self._last.text is None, "internal error (text)"
                    self._last.text = text
            del self._data[:]
        return 0

    # internal SAX event handlers

    @cython.final
    cdef _handleSaxStart(self, tag, attrib, nsmap):
        self._flush()
        if self._factory is not None:
            self._last = self._factory(tag, attrib)
            if self._element_stack:
                _appendChild(self._element_stack[-1], self._last)
        elif self._element_stack:
            self._last = _makeSubElement(
                self._element_stack[-1], tag, None, None, attrib, nsmap, None)
        else:
            self._last = _makeElement(
                tag, NULL, None, self._parser, None, None, attrib, nsmap, None)
        self._element_stack.append(self._last)
        self._in_tail = 0
        return self._last

    @cython.final
    cdef _handleSaxEnd(self, tag):
        self._flush()
        self._last = self._element_stack_pop()
        self._in_tail = 1
        return self._last

    @cython.final
    cdef int _handleSaxData(self, data) except -1:
        self._data.append(data)

    @cython.final
    cdef _handleSaxPi(self, target, data):
        elem = self._pi_factory(target, data)
        if self._insert_pis:
            self._flush()
            self._last = elem
            if self._element_stack:
                _appendChild(self._element_stack[-1], self._last)
            self._in_tail = 1
        return self._last

    @cython.final
    cdef _handleSaxComment(self, comment):
        elem = self._comment_factory(comment)
        if self._insert_comments:
            self._flush()
            self._last = elem
            if self._element_stack:
                _appendChild(self._element_stack[-1], self._last)
            self._in_tail = 1
        return elem

    # Python level event handlers

    def close(self):
        """close(self)

        Flushes the builder buffers, and returns the toplevel document
        element.  Raises XMLSyntaxError on inconsistencies.
        """
        if self._element_stack:
            raise XMLSyntaxAssertionError("missing end tags")
        # TODO: this does not necessarily seem like an error case.  Why not just return None?
        if self._last is None:
            raise XMLSyntaxAssertionError("missing toplevel element")
        return self._last

    def data(self, data):
        """data(self, data)

        Adds text to the current element.  The value should be either an
        8-bit string containing ASCII text, or a Unicode string.
        """
        self._handleSaxData(data)

    def start(self, tag, attrs, nsmap=None):
        """start(self, tag, attrs, nsmap=None)

        Opens a new element.
        """
        if nsmap is None:
            nsmap = IMMUTABLE_EMPTY_MAPPING
        return self._handleSaxStart(tag, attrs, nsmap)

    def end(self, tag):
        """end(self, tag)

        Closes the current element.
        """
        element = self._handleSaxEnd(tag)
        assert self._last.tag == tag,\
            f"end tag mismatch (expected {self._last.tag}, got {tag})"
        return element

    def pi(self, target, data=None):
        """pi(self, target, data=None)

        Creates a processing instruction using the factory, appends it
        (unless disabled) and returns it.
        """
        return self._handleSaxPi(target, data)

    def comment(self, comment):
        """comment(self, comment)

        Creates a comment using the factory, appends it (unless disabled)
        and returns it.
        """
        return self._handleSaxComment(comment)
