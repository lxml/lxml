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
    cdef _ErrorLog _error_log
    def __init__(self):
        self._error_log = _ErrorLog()

    @property
    def error_log(self):
        assert self._error_log is not None, "XInclude instance not initialised"
        return self._error_log.copy()

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
        assert self._error_log is not None, "XInclude processor not initialised"
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
            self._error_log.connect()
            old_loader = _register_resource_loader()
            try:
                doc = node._doc
                doc.lock_write()
                with nogil:
                    if tree.LIBXML_VERSION >= 21400:
                        result = xinclude.xmlXIncludeProcessNode(xctxt, node._c_node)
                    else:
                        result = xinclude.xmlXIncludeProcessTreeFlagsData(
                            node._c_node, parse_options, context_ptr)
                doc.unlock_write()
            finally:
                _reset_resource_loader(old_loader)
                self._error_log.disconnect()
        finally:
            xinclude.xmlXIncludeFreeContext(xctxt)

        if result == -1:
            raise XIncludeError(
                self._error_log._buildExceptionMessage(
                    "XInclude processing failed"),
                self._error_log)
