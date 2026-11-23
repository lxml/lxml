# XInclude processing

from lxml.includes cimport xinclude


class XIncludeError(LxmlError):
    """Error during XInclude processing.
    """


cdef class XInclude:
    """XInclude(self)
    XInclude processor.

    Create an instance and call it on an Element to run XInclude
    processing.
    """
    # Each run collects its errors in a new log that other threads cannot
    # clear or fill, and publishes it as 'error_log' when it finishes.
    cdef _ErrorLog _error_log
    # An unused, empty log for the next run.  It was never published.
    cdef _ErrorLog _spare_error_log

    def __init__(self):
        self._error_log = _newErrorLog()

    @property
    def error_log(self):
        cdef _ErrorLog error_log
        with cython.critical_section(self):
            error_log = self._error_log
        assert error_log is not None, "XInclude instance not initialised"
        return error_log.copy()

    @cython.final
    cdef _ErrorLog _new_error_log(self):
        cdef _ErrorLog error_log
        with cython.critical_section(self):
            error_log = self._spare_error_log
            self._spare_error_log = None
        if error_log is None:
            error_log = _newErrorLog()
        return error_log

    @cython.final
    cdef int _publish_error_log(self, _ErrorLog error_log, bint succeeded) except -1:
        # Only this thread has seen the new log so far.
        cdef bint is_empty = succeeded and not error_log._entries
        with cython.critical_section(self):
            if is_empty and self._error_log is not None and not self._error_log._entries:
                # Publishing an empty log would not change anything => keep it for the next run.
                self._spare_error_log = error_log
            else:
                self._error_log = error_log
        return 0

    def __call__(self, _Element node not None):
        "__call__(self, node)"
        # We cannot pass the XML_PARSE_NOXINCNODE option as this would free
        # the XInclude nodes - there may still be Python references to them!
        # Therefore, we allow XInclude nodes to be converted to
        # XML_XINCLUDE_START nodes.  XML_XINCLUDE_END nodes are added as
        # siblings.  Tree traversal will simply ignore them as they are not
        # typed as elements.  The included fragment is added between the two,
        # i.e. as a sibling, which does not conflict with traversal.
        cdef xinclude.xmlXIncludeCtxt* xctxt = NULL
        cdef int result
        _assertValidNode(node)
        cdef _ErrorLog error_log = self._new_error_log()
        if node._doc._parser is not None:
            parse_options = node._doc._parser._parse_options
            context = node._doc._parser._getParserContext()
            c_parser_ctxt = context._c_ctxt
            context_ptr = <void*> context
        else:
            parse_options = 0
            context = None
            c_parser_ctxt = context_ptr = NULL

        if tree.LIBXML_VERSION >= 21400:
            xctxt = xinclude.xmlXIncludeNewContext(node._c_node.doc)
            if xctxt is NULL:
                raise MemoryError()

            xinclude.xmlXIncludeSetResourceLoader(
                xctxt, <xmlparser.xmlResourceLoader> _local_resource_loader, c_parser_ctxt)
            if parse_options:
                xinclude.xmlXIncludeSetFlags(xctxt, parse_options)

        try:
            error_log.connect()
            old_loader = _register_resource_loader()
            try:
                doc = node._doc
                doc.lock_write()
                try:
                    with nogil:
                        if tree.LIBXML_VERSION >= 21400:
                            result = xinclude.xmlXIncludeProcessNode(xctxt, node._c_node)
                        else:
                            result = xinclude.xmlXIncludeProcessTreeFlagsData(
                                node._c_node, parse_options, context_ptr)
                finally:
                    doc.unlock_write()
            finally:
                _reset_resource_loader(old_loader)
                error_log.disconnect()
        finally:
            xinclude.xmlXIncludeFreeContext(xctxt)

        self._publish_error_log(error_log, result != -1)
        if result == -1:
            raise XIncludeError(
                error_log._buildExceptionMessage(
                    "XInclude processing failed"),
                error_log)
