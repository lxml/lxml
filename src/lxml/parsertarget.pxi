# Parser target context (ET target interface)

class _TargetParserResult(Exception):
    # Admittedly, this is somewhat ugly, but it's the easiest way
    # to push the Python level parser result through the parser
    # machinery towards the API level functions
    def __init__(self, result):
        self.result = result

cdef class _TargetParserContext(_ParserContext):
    """This class maps SAX2 events to the ET parser target interface.
    """
    cdef object _target
    cdef object _target_start
    cdef object _target_end
    cdef object _target_data
    cdef object _target_doctype
    cdef object _target_pi
    cdef object _target_comment

    cdef void _setTarget(self, target):
        self._target = target

    cdef _ParserContext _copy(self):
        cdef _TargetParserContext context
        context = _ParserContext._copy(self)
        context._setTarget(self._target)
        return context

    cdef void _initParserContext(self, xmlparser.xmlParserCtxt* c_ctxt):
        "wrap original SAX2 callbacks"
        cdef xmlparser.xmlSAXHandler* sax
        _ParserContext._initParserContext(self, c_ctxt)
        sax = c_ctxt.sax
        cstd.memset(sax, 0, sizeof(xmlparser.xmlSAXHandler))
        try:
            self._target_start = self._target.start
            if self._target_start is not None:
                sax.startElementNs = _targetSaxStart
        except AttributeError:
            pass
        try:
            self._target_end = self._target.end
            if self._target_end is not None:
                sax.endElementNs = _targetSaxEnd
        except AttributeError:
            pass
        try:
            self._target_data = self._target.data
            if self._target_data is not None:
                sax.characters = _targetSaxData
        except AttributeError:
            pass
        try:
            self._target_doctype = self._target.doctype
            if self._target_doctype is not None:
                sax.internalSubset = _targetSaxDoctype
        except AttributeError:
            pass
        try:
            self._target_pi = self._target.pi
            if self._target_pi is not None:
                sax.processingInstruction = _targetSaxPI
        except AttributeError:
            pass
        try:
            self._target_comment = self._target.comment
            if self._target_comment is not None:
                sax.startElementNs = _targetSaxStart
        except AttributeError:
            pass

        sax.initialized = xmlparser.XML_SAX2_MAGIC

    cdef object _handleParseResult(self, _BaseParser parser, xmlDoc* result,
                                   filename):
        self._raise_if_stored()
        return self._target.close()

    cdef xmlDoc* _handleParseResultDoc(self, _BaseParser parser,
                                       xmlDoc* result, filename) except NULL:
        self._raise_if_stored()
        raise _TargetParserResult(self._target.close())


cdef void _targetSaxStart(void* ctxt, char* c_localname, char* c_prefix,
                          char* c_namespace, int c_nb_namespaces,
                          char** c_namespaces,
                          int c_nb_attributes, int c_nb_defaulted,
                          char** c_attributes) with GIL:
    cdef _TargetParserContext context
    cdef xmlparser.xmlParserCtxt* c_ctxt
    cdef int i
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL:
        return
    context = <_TargetParserContext>c_ctxt._private
    try:
        tag = _namespacedNameFromNsName(c_namespace, c_localname)
        if c_nb_defaulted > 0:
            # only add default attributes if we asked for them
            if c_ctxt.loadsubset & xmlparser.XML_COMPLETE_ATTRS == 0:
                c_nb_attributes = c_nb_attributes - c_nb_defaulted
        attrib = {}
        for i from 0 <= i < c_nb_attributes:
            name = _namespacedNameFromNsName(
                c_attributes[2], c_attributes[0])
            if c_attributes[3] is NULL:
                value = ""
            else:
                value = python.PyUnicode_DecodeUTF8(
                    c_attributes[3], c_attributes[4] - c_attributes[3],
                    "strict")
            python.PyDict_SetItem(attrib, name, value)
            c_attributes = c_attributes + 5
        context._target_start(tag, attrib)
    except:
        _handleSaxTargetException(context, c_ctxt)

cdef void _targetSaxEnd(void* ctxt, char* c_localname, char* c_prefix,
                        char* c_namespace) with GIL:
    cdef _TargetParserContext context
    cdef xmlparser.xmlParserCtxt* c_ctxt
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL:
        return
    context = <_TargetParserContext>c_ctxt._private
    try:
        tag = _namespacedNameFromNsName(c_namespace, c_localname)
        context._target_end(tag)
    except:
        _handleSaxTargetException(context, c_ctxt)

cdef void _targetSaxData(void* ctxt, char* c_data, int data_len) with GIL:
    cdef _TargetParserContext context
    cdef xmlparser.xmlParserCtxt* c_ctxt
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL:
        return
    context = <_TargetParserContext>c_ctxt._private
    try:
        context._target_data(
            python.PyUnicode_DecodeUTF8(c_data, data_len, NULL))
    except:
        _handleSaxTargetException(context, c_ctxt)

cdef void _targetSaxDoctype(void* ctxt, char* c_name, char* c_public,
                       char* c_system) with GIL:
    cdef _TargetParserContext context
    cdef xmlparser.xmlParserCtxt* c_ctxt
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL:
        return
    context = <_TargetParserContext>c_ctxt._private
    try:
        if c_public is not NULL:
            public_id = funicode(c_public)
        if c_system is not NULL:
            system_id = funicode(c_system)
        context._target_doctype(
            funicode(c_name), public_id, system_id)
    except:
        _handleSaxTargetException(context, c_ctxt)

cdef void _targetSaxPI(void* ctxt, char* c_target, char* c_data) with GIL:
    cdef _TargetParserContext context
    cdef xmlparser.xmlParserCtxt* c_ctxt
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL:
        return
    context = <_TargetParserContext>c_ctxt._private
    try:
        if c_data is not NULL:
            data = funicode(c_data)
        context._target_pi(funicode(c_target), data)
    except:
        _handleSaxTargetException(context, c_ctxt)

cdef void _targetSaxComment(void* ctxt, char* c_data, int data_len) with GIL:
    cdef _TargetParserContext context
    cdef xmlparser.xmlParserCtxt* c_ctxt
    c_ctxt = <xmlparser.xmlParserCtxt*>ctxt
    if c_ctxt._private is NULL:
        return
    context = <_TargetParserContext>c_ctxt._private
    try:
        context._target_comment(
            python.PyUnicode_DecodeUTF8(c_data, data_len, NULL))
    except:
        _handleSaxTargetException(context, c_ctxt)

cdef void _handleSaxTargetException(_TargetParserContext context,
                                    xmlparser.xmlParserCtxt* c_ctxt):
    context._store_raised()
    if c_ctxt.errNo == xmlerror.XML_ERR_OK:
        c_ctxt.errNo = xmlerror.XML_ERR_INTERNAL_ERROR
    c_ctxt.disableSAX = 1
