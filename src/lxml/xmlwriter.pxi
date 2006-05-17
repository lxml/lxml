# XML serialization and output functions

cdef _tostring(_NodeBase element, encoding, int write_xml_declaration):
    "Serialize an element to an encoded string representation of its XML tree."
    cdef _Document doc
    cdef tree.xmlOutputBuffer* c_buffer
    cdef tree.xmlBuffer* c_result_buffer
    cdef tree.xmlCharEncodingHandler* enchandler
    cdef char* c_enc
    cdef char* c_version
    if element is None:
        return None
    if encoding in ('utf8', 'UTF8', 'utf-8'):
        encoding = 'UTF-8'
    doc = element._doc
    c_enc = encoding
    # it is necessary to *and* find the encoding handler *and* use
    # encoding during output
    enchandler = tree.xmlFindCharEncodingHandler(c_enc)
    c_buffer = tree.xmlAllocOutputBuffer(enchandler)
    if c_buffer is NULL:
        raise LxmlError, "Failed to create output buffer"

    try:
        _writeNodeToBuffer(c_buffer, doc._c_doc, element._c_node,
                           doc._c_doc.version, c_enc, write_xml_declaration)
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
    return result

cdef _tounicode(_NodeBase element):
    "Serialize an element to the Python unicode representation of its XML tree."
    cdef _Document doc
    cdef tree.xmlOutputBuffer* c_buffer
    cdef tree.xmlBuffer* c_result_buffer
    if element is None:
        return None
    doc = element._doc
    c_buffer = tree.xmlAllocOutputBuffer(NULL)
    if c_buffer is NULL:
        raise LxmlError, "Failed to create output buffer"
    try:
        _writeNodeToBuffer(c_buffer, doc._c_doc, element._c_node,
                           NULL, NULL, 0)
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
                             xmlDoc* c_doc, xmlNode* c_node,
                             char* xml_version, char* encoding,
                             int write_xml_declaration):
    if write_xml_declaration:
        _writeDeclarationToBuffer(c_buffer, xml_version, encoding)

    tree.xmlNodeDumpOutput(c_buffer, c_doc, c_node, 0, 0, encoding)
    _dumpNextNode(c_buffer, c_doc, c_node, encoding)

cdef void _writeDeclarationToBuffer(tree.xmlOutputBuffer* c_buffer,
                                    char* version, char* encoding):
    if version is NULL:
        version = "1.0"
    tree.xmlOutputBufferWriteString(c_buffer, "<?xml version='")
    tree.xmlOutputBufferWriteString(c_buffer, version)
    tree.xmlOutputBufferWriteString(c_buffer, "' encoding='")
    tree.xmlOutputBufferWriteString(c_buffer, encoding)
    tree.xmlOutputBufferWriteString(c_buffer, "'?>\n")

# output to file-like objects

cdef class _FileWriter:
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
    return (<_FileWriter>ctxt).write(c_buffer, len)

cdef int _closeFilelikeWriter(void* ctxt):
    return (<_FileWriter>ctxt).close()

cdef _tofile(f, _NodeBase element, encoding, int write_declaration):
    cdef _FileWriter writer
    cdef tree.xmlOutputBuffer* c_buffer
    cdef tree.xmlCharEncodingHandler* enchandler
    cdef char* c_enc
    if encoding is None:
        c_enc = NULL
    else:
        c_enc = encoding

    enchandler = tree.xmlFindCharEncodingHandler(c_enc)
    if python.PyString_Check(f) or python.PyUnicode_Check(f):
        filename = _utf8(f)
        c_buffer = tree.xmlOutputBufferCreateFilename(
            _cstr(filename), enchandler, 0)
    elif hasattr(f, 'write'):
        writer   = _FileWriter(f)
        c_buffer = writer._createOutputBuffer(enchandler)
    else:
        raise TypeError, "File or filename expected, got '%s'" % type(f)

    _writeNodeToBuffer(c_buffer,
                       element._doc._c_doc, element._c_node,
                       element._doc._c_doc.version, c_enc,
                       write_declaration)

    tree.xmlOutputBufferClose(c_buffer)
    if writer is not None:
        writer._exc_context._raise_if_stored()

# node dump functions (mainly for debug)

cdef _dumpToFile(f, xmlDoc* c_doc, xmlNode* c_node):
    cdef python.PyObject* o
    cdef tree.xmlOutputBuffer* c_buffer
    
    if not python.PyFile_Check(f):
        raise ValueError, "Not a file"
    o = <python.PyObject*>f
    c_buffer = tree.xmlOutputBufferCreateFile(python.PyFile_AsFile(o), NULL)
    tree.xmlNodeDumpOutput(c_buffer, c_doc, c_node, 0, 0, NULL)
    # dump next node if it's a text node
    _dumpNextNode(c_buffer, c_doc, c_node, NULL)
    tree.xmlOutputBufferWriteString(c_buffer, '\n')
    tree.xmlOutputBufferFlush(c_buffer)

cdef void _dumpNextNode(tree.xmlOutputBuffer* c_buffer, xmlDoc* c_doc,
                        xmlNode* c_node, char* encoding):
    cdef xmlNode* c_next
    c_next = c_node.next
    if c_next is not NULL and c_next.type == tree.XML_TEXT_NODE:
        tree.xmlNodeDumpOutput(c_buffer, c_doc, c_next, 0, 0, encoding)
