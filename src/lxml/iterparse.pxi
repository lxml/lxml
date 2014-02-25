# iterparse -- event-driven parsing

DEF __ITERPARSE_CHUNK_SIZE = 32768

cdef class iterparse:
    u"""iterparse(self, source, events=("end",), tag=None, \
                  attribute_defaults=False, dtd_validation=False, \
                  load_dtd=False, no_network=True, remove_blank_text=False, \
                  remove_comments=False, remove_pis=False, encoding=None, \
                  html=False, recover=None, huge_tree=False, schema=None)

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
     - html: parse input as HTML (default: XML)
     - recover: try hard to parse through broken input (default: True for HTML,
                False otherwise)

    Other keyword arguments:
     - encoding: override the document encoding
     - schema: an XMLSchema to validate against
    """
    cdef _FeedParser _parser
    cdef object _tag
    cdef object _events
    cdef readonly object root
    cdef object _source
    cdef object _filename
    cdef object _error
    cdef bint _close_source_after_read

    def __init__(self, source, events=(u"end",), *, tag=None,
                 attribute_defaults=False, dtd_validation=False,
                 load_dtd=False, no_network=True, remove_blank_text=False,
                 compact=True, resolve_entities=True, remove_comments=False,
                 remove_pis=False, strip_cdata=True, encoding=None,
                 html=False, recover=None, huge_tree=False,
                 XMLSchema schema=None):
        if not hasattr(source, 'read'):
            self._filename = source
            if not python.IS_PYTHON3:
                source = _encodeFilename(source)
            source = open(source, 'rb')
            self._close_source_after_read = True
        else:
            self._filename = _getFilenameForFile(source)
            self._close_source_after_read = False

        if recover is None:
            recover = html

        if html:
            # make sure we're not looking for namespaces
            events = [event for event in events
                      if event not in ('start-ns', 'end-ns')]
            parser = HTMLPullParser(
                events,
                tag=tag,
                recover=recover,
                base_url=self._filename,
                encoding=encoding,
                remove_blank_text=remove_blank_text,
                remove_comments=remove_comments,
                remove_pis=remove_pis,
                strip_cdata=strip_cdata,
                no_network=no_network,
                target=None,  # TODO
                schema=schema,
                compact=compact)
        else:
            parser = XMLPullParser(
                events,
                tag=tag,
                recover=recover,
                base_url=self._filename,
                encoding=encoding,
                attribute_defaults=attribute_defaults,
                dtd_validation=dtd_validation,
                load_dtd=load_dtd,
                no_network=no_network,
                schema=schema,
                huge_tree=huge_tree,
                remove_blank_text=remove_blank_text,
                resolve_entities=resolve_entities,
                remove_comments=remove_comments,
                remove_pis=remove_pis,
                strip_cdata=strip_cdata,
                target=None,  # TODO
                compact=compact)

        self._events = parser.read_events()
        self._parser = parser
        self._source = source

    property error_log:
        u"""The error log of the last (or current) parser run.
        """
        def __get__(self):
            return self._parser.feed_error_log

    property resolvers:
        u"""The custom resolver registry of the last (or current) parser run.
        """
        def __get__(self):
            return self._parser.resolvers

    property version:
        u"""The version of the underlying XML parser."""
        def __get__(self):
            return self._parser.version

    def set_element_class_lookup(self, ElementClassLookup lookup = None):
        u"""set_element_class_lookup(self, lookup = None)

        Set a lookup scheme for element classes generated from this parser.

        Reset it by passing None or nothing.
        """
        self._parser.set_element_class_lookup(lookup)

    def makeelement(self, _tag, attrib=None, nsmap=None, **_extra):
        u"""makeelement(self, _tag, attrib=None, nsmap=None, **_extra)

        Creates a new element associated with this parser.
        """
        self._parser.makeelement(
            _tag, attrib=None, nsmap=None, **_extra)

    @cython.final
    cdef _close_source(self):
        if self._source is None:
            return
        if not self._close_source_after_read:
            self._source = None
            return
        try:
            close = self._source.close
        except AttributeError:
            close = None
        finally:
            self._source = None
        if close is not None:
            close()

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return next(self._events)
        except StopIteration:
            pass
        context = <_SaxParserContext>self._parser._getPushParserContext()
        if self._source is not None:
            done = False
            while not done:
                try:
                    done = self._read_more_events(context)
                    return next(self._events)
                except StopIteration:
                    pass  # no events yet
                except Exception, e:
                    self._error = e
                    self._close_source()
                    try:
                        return next(self._events)
                    except StopIteration:
                        break
        # nothing left to read or return
        if self._error is not None:
            error = self._error
            self._error = None
            raise error
        if (context._validator is not None
                and not context._validator.isvalid()):
            _raiseParseError(context._c_ctxt, self._filename,
                             context._error_log)
        # no errors => all done
        raise StopIteration

    @cython.final
    cdef bint _read_more_events(self, _SaxParserContext context) except -123:
        data = self._source.read(__ITERPARSE_CHUNK_SIZE)
        if not isinstance(data, bytes):
            self._close_source()
            raise TypeError("reading file objects must return bytes objects")
        if not data:
            try:
                self.root = self._parser.close()
            finally:
                self._close_source()
            return True
        self._parser.feed(data)
        return False


cdef class iterwalk:
    u"""iterwalk(self, element_or_tree, events=("end",), tag=None)

    A tree walker that generates events from an existing tree as if it
    was parsing XML data with ``iterparse()``.
    """
    cdef _MultiTagMatcher _matcher
    cdef list   _node_stack
    cdef int    _index
    cdef list   _events
    cdef object _pop_event
    cdef int    _event_filter

    def __init__(self, element_or_tree, events=(u"end",), tag=None):
        cdef _Element root
        cdef int ns_count
        root = _rootNodeOrRaise(element_or_tree)
        self._event_filter = _buildParseEventFilter(events)
        if tag is None or tag == '*':
            self._matcher = None
        else:
            self._matcher = _MultiTagMatcher(tag)
        self._node_stack  = []
        self._events = []
        self._pop_event = self._events.pop

        if self._event_filter:
            self._index = 0
            ns_count = self._start_node(root)
            self._node_stack.append( (root, ns_count) )
        else:
            self._index = -1

    def __iter__(self):
        return self

    def __next__(self):
        cdef xmlNode* c_child
        cdef _Element node
        cdef _Element next_node
        cdef int ns_count = 0
        if self._events:
            return self._pop_event(0)
        if self._matcher is not None and self._index >= 0:
            node = self._node_stack[self._index][0]
            self._matcher.cacheTags(node._doc)

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
                if self._event_filter & (PARSE_EVENT_FILTER_START |
                                         PARSE_EVENT_FILTER_START_NS):
                    ns_count = self._start_node(next_node)
                elif self._event_filter & PARSE_EVENT_FILTER_END_NS:
                    ns_count = _countNsDefs(next_node._c_node)
                self._node_stack.append( (next_node, ns_count) )
                self._index += 1
            if self._events:
                return self._pop_event(0)
        raise StopIteration

    cdef int _start_node(self, _Element node) except -1:
        cdef int ns_count
        if self._event_filter & PARSE_EVENT_FILTER_START_NS:
            ns_count = _appendStartNsEvents(node._c_node, self._events)
        elif self._event_filter & PARSE_EVENT_FILTER_END_NS:
            ns_count = _countNsDefs(node._c_node)
        else:
            ns_count = 0
        if self._event_filter & PARSE_EVENT_FILTER_START:
            if self._matcher is None or self._matcher.matches(node._c_node):
                self._events.append( (u"start", node) )
        return ns_count

    cdef _Element _end_node(self):
        cdef _Element node
        cdef int i, ns_count
        node, ns_count = self._node_stack.pop()
        if self._event_filter & PARSE_EVENT_FILTER_END:
            if self._matcher is None or self._matcher.matches(node._c_node):
                self._events.append( (u"end", node) )
        if self._event_filter & PARSE_EVENT_FILTER_END_NS:
            event = (u"end-ns", None)
            for i from 0 <= i < ns_count:
                self._events.append(event)
        return node


cdef int _countNsDefs(xmlNode* c_node):
    cdef xmlNs* c_ns
    cdef int count
    count = 0
    c_ns = c_node.nsDef
    while c_ns is not NULL:
        count += 1
        c_ns = c_ns.next
    return count


cdef int _appendStartNsEvents(xmlNode* c_node, list event_list) except -1:
    cdef xmlNs* c_ns
    cdef int count
    count = 0
    c_ns = c_node.nsDef
    while c_ns is not NULL:
        ns_tuple = (funicode(c_ns.prefix) if c_ns.prefix is not NULL else '',
                    funicode(c_ns.href))
        event_list.append( (u"start-ns", ns_tuple) )
        count += 1
        c_ns = c_ns.next
    return count
