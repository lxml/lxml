# XML serialization and output functions

tree.xmlKeepBlanksDefault(0)

cdef _tostring(_NodeBase element, encoding,
               int write_xml_declaration, int pretty_print):
    "Serialize an element to an encoded string representation of its XML tree."
    cdef tree.xmlOutputBuffer* c_buffer
    cdef tree.xmlBuffer* c_result_buffer
    cdef tree.xmlCharEncodingHandler* enchandler
    cdef char* c_enc
    cdef char* c_version
    if element is None:
        return None
    if encoding is None:
        c_enc = NULL
    else:
        c_enc = encoding
    # it is necessary to *and* find the encoding handler *and* use
    # encoding during output
    enchandler = tree.xmlFindCharEncodingHandler(c_enc)
    if enchandler is NULL:
        raise LookupError, python.PyString_FromFormat(
            "unknown encoding: '%s'", c_enc)
    c_buffer = tree.xmlAllocOutputBuffer(enchandler)
    if c_buffer is NULL:
        tree.xmlCharEncCloseFunc(enchandler)
        raise LxmlError, "Failed to create output buffer"

    try:
        _writeNodeToBuffer(c_buffer, element._c_node, c_enc,
                           write_xml_declaration, pretty_print)
        tree.xmlOutputBufferFlush(c_buffer)
        if c_buffer.conv is not NULL:
            c_result_buffer = c_buffer.conv
        else:
            c_result_buffer = c_buffer.buffer
        result = python.PyString_FromStringAndSize(
            tree.xmlBufferContent(c_result_buffer),
            tree.xmlBufferLength(c_result_buffer))
    finally:
        tree.xmlOutputBufferClose(c_buffer)
        tree.xmlCharEncCloseFunc(enchandler)
    return result

cdef _tounicode(_NodeBase element, int pretty_print):
    "Serialize an element to the Python unicode representation of its XML tree."
    cdef tree.xmlOutputBuffer* c_buffer
    cdef tree.xmlBuffer* c_result_buffer
    if element is None:
        return None
    c_buffer = tree.xmlAllocOutputBuffer(NULL)
    if c_buffer is NULL:
        raise LxmlError, "Failed to create output buffer"
    try:
        _writeNodeToBuffer(c_buffer, element._c_node, NULL, 0, pretty_print)
        tree.xmlOutputBufferFlush(c_buffer)
        if c_buffer.conv is not NULL:
            c_result_buffer = c_buffer.conv
        else:
            c_result_buffer = c_buffer.buffer
        result = python.PyUnicode_DecodeUTF8(
            tree.xmlBufferContent(c_result_buffer),
            tree.xmlBufferLength(c_result_buffer),
            'strict')
    finally:
        tree.xmlOutputBufferClose(c_buffer)
    return result

cdef void _writeNodeToBuffer(tree.xmlOutputBuffer* c_buffer,
                             xmlNode* c_node, char* encoding,
                             int write_xml_declaration, int pretty_print):
    cdef xmlDoc* c_doc
    c_doc = c_node.doc
    if write_xml_declaration:
        _writeDeclarationToBuffer(c_buffer, c_doc.version, encoding)

    tree.xmlNodeDumpOutput(c_buffer, c_doc, c_node, 0, pretty_print, encoding)
    _writeTail(c_buffer, c_node, encoding, pretty_print)

cdef void _writeDeclarationToBuffer(tree.xmlOutputBuffer* c_buffer,
                                    char* version, char* encoding):
    if version is NULL:
        version = "1.0"
    tree.xmlOutputBufferWriteString(c_buffer, "<?xml version='")
    tree.xmlOutputBufferWriteString(c_buffer, version)
    tree.xmlOutputBufferWriteString(c_buffer, "' encoding='")
    tree.xmlOutputBufferWriteString(c_buffer, encoding)
    tree.xmlOutputBufferWriteString(c_buffer, "'?>\n")

cdef void _writeTail(tree.xmlOutputBuffer* c_buffer, xmlNode* c_node,
                     char* encoding, int pretty_print):
    "Write the element tail."
    c_node = c_node.next
    while c_node is not NULL and c_node.type == tree.XML_TEXT_NODE:
        tree.xmlNodeDumpOutput(c_buffer, c_node.doc, c_node, 0,
                               pretty_print, encoding)
        c_node = c_node.next

# output to file-like objects

cdef class _FilelikeWriter:
    cdef object _filelike
    cdef _ExceptionContext _exc_context
    def __init__(self, filelike, exc_context=None):
        self._filelike = filelike
        if exc_context is None:
            self._exc_context = _ExceptionContext()
        else:
            self._exc_context = exc_context

    cdef tree.xmlOutputBuffer* _createOutputBuffer(
        self, tree.xmlCharEncodingHandler* enchandler) except NULL:
        cdef tree.xmlOutputBuffer* c_buffer
        c_buffer = tree.xmlOutputBufferCreateIO(
            _writeFilelikeWriter, _closeFilelikeWriter,
            <python.PyObject*>self, enchandler)
        if c_buffer is NULL:
            raise IOError, "Could not create I/O writer context."
        return c_buffer

    cdef int write(self, char* c_buffer, int len):
        try:
            if self._filelike is None:
                raise IOError, "File is already closed"
            py_buffer = python.PyString_FromStringAndSize(c_buffer, len)
            self._filelike.write(py_buffer)
            return len
        except Exception:
            self._exc_context._store_raised()
            return -1

    cdef int close(self):
        # we should not close the file here as we didn't open it
        self._filelike = None
        return 0

cdef int _writeFilelikeWriter(void* ctxt, char* c_buffer, int len):
    return (<_FilelikeWriter>ctxt).write(c_buffer, len)

cdef int _closeFilelikeWriter(void* ctxt):
    return (<_FilelikeWriter>ctxt).close()

cdef _tofilelike(f, _NodeBase element, encoding,
                 int write_xml_declaration, int pretty_print):
    cdef _FilelikeWriter writer
    cdef tree.xmlOutputBuffer* c_buffer
    cdef tree.xmlCharEncodingHandler* enchandler
    cdef char* c_enc
    if encoding is None:
        c_enc = NULL
    else:
        c_enc = encoding
    enchandler = tree.xmlFindCharEncodingHandler(c_enc)
    if enchandler is NULL:
        raise LookupError, python.PyString_FromFormat(
            "unknown encoding: '%s'", c_enc)

    if python.PyString_Check(f) or python.PyUnicode_Check(f):
        filename = _utf8(f)
        c_buffer = tree.xmlOutputBufferCreateFilename(
            _cstr(filename), enchandler, 0)
    elif hasattr(f, 'write'):
        writer   = _FilelikeWriter(f)
        c_buffer = writer._createOutputBuffer(enchandler)
    else:
        tree.xmlCharEncCloseFunc(enchandler)
        raise TypeError, "File or filename expected, got '%s'" % type(f)

    _writeNodeToBuffer(c_buffer, element._c_node, c_enc,
                       write_xml_declaration, pretty_print)

    tree.xmlOutputBufferClose(c_buffer)
    tree.xmlCharEncCloseFunc(enchandler)
    if writer is not None:
        writer._exc_context._raise_if_stored()

# dump node to file (mainly for debug)

cdef _dumpToFile(f, xmlNode* c_node, int pretty_print):
    cdef tree.xmlOutputBuffer* c_buffer
    if not python.PyFile_Check(f):
        raise ValueError, "Not a file"
    c_buffer = tree.xmlOutputBufferCreateFile(python.PyFile_AsFile(f), NULL)
    tree.xmlNodeDumpOutput(c_buffer, c_node.doc, c_node, 0, pretty_print, NULL)
    _writeTail(c_buffer, c_node, NULL, 0)
    tree.xmlOutputBufferWriteString(c_buffer, '\n')
    tree.xmlOutputBufferFlush(c_buffer)
