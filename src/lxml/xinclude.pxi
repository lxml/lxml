# XInclude processing

cimport xinclude

class XIncludeError(LxmlError):
    u"""Error during XInclude processing.
    """
    pass

cdef class XInclude:
    u"""XInclude(self)
    XInclude processor.

    Create an instance and call it on an Element to run XInclude
    processing.
    """
    cdef _ErrorLog _error_log
    def __init__(self):
        self._error_log = _ErrorLog()

    property error_log:
        def __get__(self):
            assert self._error_log is not None, "XInclude instance not initialised"
            return self._error_log.copy()

    def __call__(self, _Element node not None):
        u"__call__(self, node)"
        # We cannot pass the XML_PARSE_NOXINCNODE option as this would free
        # the XInclude nodes - there may still be Python references to them!
        # Therefore, we allow XInclude nodes to be converted to
        # XML_XINCLUDE_START nodes.  XML_XINCLUDE_END nodes are added as
        # siblings.  Tree traversal will simply ignore them as they are not
        # typed as elements.  The included fragment is added between the two,
        # i.e. as a sibling, which does not conflict with traversal.
        cdef int result
        _assertValidNode(node)
        assert self._error_log is not None, "XPath evaluator not initialised"
        self._error_log.connect()
        __GLOBAL_PARSER_CONTEXT.pushImpliedContextFromParser(
            node._doc._parser)
        with nogil:
            if node._doc._parser is not None:
                result = xinclude.xmlXIncludeProcessTreeFlags(
                    node._c_node, node._doc._parser._parse_options)
            else:
                result = xinclude.xmlXIncludeProcessTree(node._c_node)
        __GLOBAL_PARSER_CONTEXT.popImpliedContext()
        self._error_log.disconnect()

        if result == -1:
            raise XIncludeError(
                self._error_log._buildExceptionMessage(
                    u"XInclude processing failed"),
                self._error_log)
