# SAX-like interfaces

ctypedef enum _SaxParserEvents:
    SAX_EVENT_START   =  1
    SAX_EVENT_END     =  2
    SAX_EVENT_DATA    =  4
    SAX_EVENT_DOCTYPE =  8
    SAX_EVENT_PI      = 16
    SAX_EVENT_COMMENT = 32

cdef class _SaxParserTarget:
    cdef int _sax_event_filter
    cdef int _sax_event_propagate
    def __cinit__(self):
        self._sax_event_filter = 0
        self._sax_event_propagate = 0

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

cdef class _SaxParserContext(_ParserContext):
    u"""This class maps SAX2 events to method calls.
    """
    cdef _SaxParserTarget _target
    cdef xmlparser.startElementNsSAX2Func _origSaxStart
    cdef xmlparser.endElementNsSAX2Func   _origSaxEnd
    cdef xmlparser.startElementSAXFunc    _origSaxStartNoNs
    cdef xmlparser.endElementSAXFunc      _origSaxEndNoNs
    cdef xmlparser.charactersSAXFunc      _origSaxData
    cdef xmlparser.cdataBlockSAXFunc      _origSaxCData
    cdef xmlparser.internalSubsetSAXFunc  _origSaxDoctype
    cdef xmlparser.commentSAXFunc         _origSaxComment
    cdef xmlparser.processingInstructionSAXFunc    _origSaxPi

    cdef void _setSaxParserTarget(self, _SaxParserTarget target):
        self._target = target

    cdef void _initParserContext(self, xmlparser.xmlParserCtxt* c_ctxt):
        u"wrap original SAX2 callbacks"
        cdef xmlparser.xmlSAXHandler* sax
        _ParserContext._initParserContext(self, c_ctxt)
        sax = c_ctxt.sax
        if self._target._sax_event_propagate & SAX_EVENT_START:
            # propagate => keep orig callback
            self._origSaxStart = sax.startElementNs
            self._origSaxStartNoNs = sax.startElement
        else:
            # otherwise: never call orig callback
            self._origSaxStart = sax.startElementNs = NULL
            self._origSaxStartNoNs = sax.startElement = NULL
        if self._target._sax_event_filter & SAX_EVENT_START:
            # intercept => overwrite orig callback
            if sax.initialized == xmlparser.XML_SAX2_MAGIC:
                sax.startElementNs = _handleSaxStart
            sax.startElement = _handleSaxStartNoNs

        if self._target._sax_event_propagate & SAX_EVENT_END:
            self._origSaxEnd = sax.endElementNs
            self._origSaxEndNoNs = sax.endElement
        else:
            self._origSaxEnd = sax.endElementNs = NULL
            self._origSaxEndNoNs = sax.endElement = NULL
        if self._target._sax_event_filter & SAX_EVENT_END:
            if sax.initialized == xmlparser.XML_SAX2_MAGIC:
                sax.endElementNs = _handleSaxEnd
            sax.endElement = _handleSaxEndNoNs

        if self._target._sax_event_propagate & SAX_EVENT_DATA:
            self._origSaxData = sax.characters
            self._origSaxCData = sax.cdataBlock
        else:
            self._origSaxData = sax.characters = sax.cdataBlock = NULL
        if self._target._sax_event_filter & SAX_EVENT_DATA:
            sax.characters = _handleSaxData
            sax.cdataBlock = _handleSaxCData

        # doctype propagation is always required for entity replacement
        self._origSaxDoctype = sax.internalSubset
        if self._target._sax_event_filter & SAX_EVENT_DOCTYPE:
            sax.internalSubset = _handleSaxDoctype

        if self._target._sax_event_propagate & SAX_EVENT_PI:
            self._origSaxPi = sax.processingInstruction
        else:
            self._origSaxPi = sax.processingInstruction = NULL
        if self._target._sax_event_filter & SAX_EVENT_PI:
            sax.processingInstruction = _handleSaxPI

        if self._target._sax_event_propagate & SAX_EVENT_COMMENT:
            self._origSaxComment = sax.comment
        else:
            self._origSaxComment = sax.comment = NULL
        if self._target._sax_event_filter & SAX_EVENT_COMMENT:
            sax.comment = _handleSaxComment

        # enforce entity replacement
        sax.reference = NULL
        c_ctxt.replaceEntities = 1

    cdef void _handleSaxException(self, xmlparser.xmlParserCtxt* c_ctxt):
        if c_ctxt.errNo == xmlerror.XML_ERR_OK:
            c_ctxt.errNo = xmlerror.XML_ERR_INTERNAL_ERROR
        # stop parsing immediately
        c_ctxt.wellFormed = 0
        c_ctxt.disableSAX = 1
        self._store_raised()

cdef void _handleSaxStart(void* ctxt, char* c_localname, char* c_prefix,
                          char* c_namespace, int c_nb_namespaces,
                          char** c_namespaces,
                          int c_nb_attributes, int c_nb_defaulted,
                          char** c_attributes) with gil:
    cdef _SaxParserContext context
    cdef xmlparser.xmlParserCtxt* c_ctxt
    cdef _Element element
    cdef int i
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL:
        return
    context = <_SaxParserContext>c_ctxt._private
    if context._origSaxStart is not NULL:
        context._origSaxStart(c_ctxt, c_localname, c_prefix, c_namespace,
                              c_nb_namespaces, c_namespaces, c_nb_attributes,
                              c_nb_defaulted, c_attributes)
    try:
        tag = _namespacedNameFromNsName(c_namespace, c_localname)
        if c_nb_defaulted > 0:
            # only add default attributes if we asked for them
            if c_ctxt.loadsubset & xmlparser.XML_COMPLETE_ATTRS == 0:
                c_nb_attributes = c_nb_attributes - c_nb_defaulted
        if c_nb_attributes == 0:
            attrib = EMPTY_READ_ONLY_DICT
        else:
            attrib = {}
            for i from 0 <= i < c_nb_attributes:
                name = _namespacedNameFromNsName(
                    c_attributes[2], c_attributes[0])
                if c_attributes[3] is NULL:
                    if python.IS_PYTHON3:
                        value = u''
                    else:
                        value = ''
                else:
                    value = python.PyUnicode_DecodeUTF8(
                        c_attributes[3], c_attributes[4] - c_attributes[3],
                        "strict")
                attrib[name] = value
                c_attributes += 5
        if c_nb_namespaces == 0:
            nsmap = EMPTY_READ_ONLY_DICT
        else:
            nsmap = {}
            for i from 0 <= i < c_nb_namespaces:
                if c_namespaces[0] is NULL:
                    prefix = None
                else:
                    prefix = funicode(c_namespaces[0])
                nsmap[prefix] = funicode(c_namespaces[1])
                c_namespaces += 2
        element = context._target._handleSaxStart(tag, attrib, nsmap)
        if element is not None and c_ctxt.input is not NULL:
            if c_ctxt.input.line < 65535:
                element._c_node.line = <short>c_ctxt.input.line
            else:
                element._c_node.line = 65535
    except:
        context._handleSaxException(c_ctxt)

cdef void _handleSaxStartNoNs(void* ctxt, char* c_name,
                              char** c_attributes) with gil:
    cdef _SaxParserContext context
    cdef xmlparser.xmlParserCtxt* c_ctxt
    cdef _Element element
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL:
        return
    context = <_SaxParserContext>c_ctxt._private
    if context._origSaxStartNoNs is not NULL:
        context._origSaxStartNoNs(c_ctxt, c_name, c_attributes)
    try:
        tag = funicode(c_name)
        if c_attributes is NULL:
            attrib = EMPTY_READ_ONLY_DICT
        else:
            attrib = {}
            while c_attributes[0] is not NULL:
                name = funicode(c_attributes[0])
                if c_attributes[1] is NULL:
                    if python.IS_PYTHON3:
                        value = u''
                    else:
                        value = ''
                else:
                    value = funicode(c_attributes[1])
                c_attributes = c_attributes + 2
                attrib[name] = value
        element = context._target._handleSaxStart(
            tag, attrib, EMPTY_READ_ONLY_DICT)
        if element is not None and c_ctxt.input is not NULL:
            if c_ctxt.input.line < 65535:
                element._c_node.line = <short>c_ctxt.input.line
            else:
                element._c_node.line = 65535
    except:
        context._handleSaxException(c_ctxt)

cdef void _handleSaxEnd(void* ctxt, char* c_localname, char* c_prefix,
                        char* c_namespace) with gil:
    cdef _SaxParserContext context
    cdef xmlparser.xmlParserCtxt* c_ctxt
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL:
        return
    context = <_SaxParserContext>c_ctxt._private
    if context._origSaxEnd is not NULL:
        context._origSaxEnd(c_ctxt, c_localname, c_prefix, c_namespace)
    try:
        tag = _namespacedNameFromNsName(c_namespace, c_localname)
        context._target._handleSaxEnd(tag)
    except:
        context._handleSaxException(c_ctxt)

cdef void _handleSaxEndNoNs(void* ctxt, char* c_name) with gil:
    cdef _SaxParserContext context
    cdef xmlparser.xmlParserCtxt* c_ctxt
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL:
        return
    context = <_SaxParserContext>c_ctxt._private
    if context._origSaxEndNoNs is not NULL:
        context._origSaxEndNoNs(c_ctxt, c_name)
    try:
        context._target._handleSaxEnd(funicode(c_name))
    except:
        context._handleSaxException(c_ctxt)

cdef void _handleSaxData(void* ctxt, char* c_data, int data_len) with gil:
    cdef _SaxParserContext context
    cdef xmlparser.xmlParserCtxt* c_ctxt
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL or c_ctxt.disableSAX:
        return
    context = <_SaxParserContext>c_ctxt._private
    if context._origSaxData is not NULL:
        context._origSaxData(c_ctxt, c_data, data_len)
    try:
        context._target._handleSaxData(
            python.PyUnicode_DecodeUTF8(c_data, data_len, NULL))
    except:
        context._handleSaxException(c_ctxt)

cdef void _handleSaxCData(void* ctxt, char* c_data, int data_len) with gil:
    cdef _SaxParserContext context
    cdef xmlparser.xmlParserCtxt* c_ctxt
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL or c_ctxt.disableSAX:
        return
    context = <_SaxParserContext>c_ctxt._private
    if context._origSaxCData is not NULL:
        context._origSaxCData(c_ctxt, c_data, data_len)
    try:
        context._target._handleSaxData(
            python.PyUnicode_DecodeUTF8(c_data, data_len, NULL))
    except:
        context._handleSaxException(c_ctxt)

cdef void _handleSaxDoctype(void* ctxt, char* c_name, char* c_public,
                            char* c_system) with gil:
    cdef _SaxParserContext context
    cdef xmlparser.xmlParserCtxt* c_ctxt
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL or c_ctxt.disableSAX:
        return
    context = <_SaxParserContext>c_ctxt._private
    if context._origSaxDoctype is not NULL:
        context._origSaxDoctype(c_ctxt, c_name, c_public, c_system)
    try:
        if c_public is not NULL:
            public_id = funicode(c_public)
        if c_system is not NULL:
            system_id = funicode(c_system)
        context._target._handleSaxDoctype(
            funicode(c_name), public_id, system_id)
    except:
        context._handleSaxException(c_ctxt)

cdef void _handleSaxPI(void* ctxt, char* c_target, char* c_data) with gil:
    cdef _SaxParserContext context
    cdef xmlparser.xmlParserCtxt* c_ctxt
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL:
        return
    context = <_SaxParserContext>c_ctxt._private
    if context._origSaxPi is not NULL:
        context._origSaxPi(c_ctxt, c_target, c_data)
    try:
        if c_data is not NULL:
            data = funicode(c_data)
        context._target._handleSaxPi(funicode(c_target), data)
    except:
        context._handleSaxException(c_ctxt)

cdef void _handleSaxComment(void* ctxt, char* c_data) with gil:
    cdef _SaxParserContext context
    cdef xmlparser.xmlParserCtxt* c_ctxt
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL:
        return
    context = <_SaxParserContext>c_ctxt._private
    if context._origSaxComment is not NULL:
        context._origSaxComment(c_ctxt, c_data)
    try:
        context._target._handleSaxComment(funicode(c_data))
    except:
        context._handleSaxException(c_ctxt)


############################################################
## ET compatible XML tree builder
############################################################

cdef class TreeBuilder(_SaxParserTarget):
    u"""TreeBuilder(self, element_factory=None, parser=None)
    Parser target that builds a tree.

    The final tree is returned by the ``close()`` method.
    """
    cdef _BaseParser _parser
    cdef object _factory
    cdef list _data
    cdef list _element_stack
    cdef object _element_stack_pop
    cdef _Element _last # may be None
    cdef bint _in_tail

    def __init__(self, *, element_factory=None, parser=None):
        self._sax_event_filter = \
            SAX_EVENT_START | SAX_EVENT_END | SAX_EVENT_DATA | \
            SAX_EVENT_PI | SAX_EVENT_COMMENT
        self._data = [] # data collector
        self._element_stack = [] # element stack
        self._element_stack_pop = self._element_stack.pop
        self._last = None # last element
        self._in_tail = 0 # true if we're after an end tag
        self._factory = element_factory
        self._parser = parser

    cdef int _flush(self) except -1:
        if python.PyList_GET_SIZE(self._data) > 0:
            if self._last is not None:
                text = u"".join(self._data)
                if self._in_tail:
                    assert self._last.tail is None, u"internal error (tail)"
                    self._last.tail = text
                else:
                    assert self._last.text is None, u"internal error (text)"
                    self._last.text = text
            del self._data[:]
        return 0

    # Python level event handlers

    def close(self):
        u"""close(self)

        Flushes the builder buffers, and returns the toplevel document
        element.
        """
        assert python.PyList_GET_SIZE(self._element_stack) == 0, u"missing end tags"
        assert self._last is not None, u"missing toplevel element"
        return self._last

    def data(self, data):
        u"""data(self, data)

        Adds text to the current element.  The value should be either an
        8-bit string containing ASCII text, or a Unicode string.
        """
        self._handleSaxData(data)

    def start(self, tag, attrs, nsmap=None):
        u"""start(self, tag, attrs, nsmap=None)

        Opens a new element.
        """
        if nsmap is None:
            nsmap = EMPTY_READ_ONLY_DICT
        return self._handleSaxStart(tag, attrs, nsmap)

    def end(self, tag):
        u"""end(self, tag)

        Closes the current element.
        """
        element = self._handleSaxEnd(tag)
        assert self._last.tag == tag,\
               u"end tag mismatch (expected %s, got %s)" % (
                   self._last.tag, tag)
        return element

    def pi(self, target, data):
        u"""pi(self, target, data)
        """
        return self._handleSaxPi(target, data)

    def comment(self, comment):
        u"""comment(self, comment)
        """
        return self._handleSaxComment(comment)

    # internal SAX event handlers

    cdef _handleSaxStart(self, tag, attrib, nsmap):
        self._flush()
        if self._factory is not None:
            self._last = self._factory(tag, attrib)
            if python.PyList_GET_SIZE(self._element_stack) > 0:
                _appendChild(self._element_stack[-1], self._last)
        elif python.PyList_GET_SIZE(self._element_stack) > 0:
            self._last = _makeSubElement(
                self._element_stack[-1], tag, None, None, attrib, nsmap, None)
        else:
            self._last = _makeElement(
                tag, NULL, None, self._parser, None, None, attrib, nsmap, None)
        self._element_stack.append(self._last)
        self._in_tail = 0
        return self._last

    cdef _handleSaxEnd(self, tag):
        self._flush()
        self._last = self._element_stack_pop()
        self._in_tail = 1
        return self._last

    cdef int _handleSaxData(self, data) except -1:
        self._data.append(data)

    cdef _handleSaxPi(self, target, data):
        self._flush()
        self._last = ProcessingInstruction(target, data)
        if python.PyList_GET_SIZE(self._element_stack) > 0:
            _appendChild(self._element_stack[-1], self._last)
        self._in_tail = 1
        return self._last

    cdef _handleSaxComment(self, comment):
        self._flush()
        self._last = Comment(comment)
        if python.PyList_GET_SIZE(self._element_stack) > 0:
            _appendChild(self._element_stack[-1], self._last)
        self._in_tail = 1
        return self._last
