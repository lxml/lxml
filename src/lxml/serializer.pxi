# XML serialization and output functions

cdef _tostring(_Element element, encoding,
               int write_xml_declaration, int write_complete_document,
               int pretty_print):
    "Serialize an element to an encoded string representation of its XML tree."
    cdef python.PyThreadState* state
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
        state = python.PyEval_SaveThread()
        _writeNodeToBuffer(c_buffer, element._c_node, c_enc,
                           write_xml_declaration, write_complete_document,
                           pretty_print)
        tree.xmlOutputBufferFlush(c_buffer)
        python.PyEval_RestoreThread(state)
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

cdef _tounicode(_Element element, int write_complete_document, int pretty_print):
    "Serialize an element to the Python unicode representation of its XML tree."
    cdef python.PyThreadState* state
    cdef tree.xmlOutputBuffer* c_buffer
    cdef tree.xmlBuffer* c_result_buffer
    if element is None:
        return None
    c_buffer = tree.xmlAllocOutputBuffer(NULL)
    if c_buffer is NULL:
        raise LxmlError, "Failed to create output buffer"
    try:
        state = python.PyEval_SaveThread()
        _writeNodeToBuffer(c_buffer, element._c_node, NULL, 0,
                           write_complete_document, pretty_print)
        tree.xmlOutputBufferFlush(c_buffer)
        python.PyEval_RestoreThread(state)
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
                             int write_xml_declaration,
                             int write_complete_document,
                             int pretty_print):
    cdef xmlDoc* c_doc
    c_doc = c_node.doc
    if write_complete_document:
        _writeDeclarationToBuffer(c_buffer, c_doc.version, encoding)

    if write_complete_document:
        _writeDtdToBuffer(c_buffer, c_doc, c_node.name, encoding)
        _writePrevSiblings(c_buffer, c_node, encoding, pretty_print)
    tree.xmlNodeDumpOutput(c_buffer, c_doc, c_node, 0, pretty_print, encoding)
    _writeTail(c_buffer, c_node, encoding, pretty_print)
    if write_complete_document:
        _writeNextSiblings(c_buffer, c_node, encoding, pretty_print)

cdef void _writeDeclarationToBuffer(tree.xmlOutputBuffer* c_buffer,
                                    char* version, char* encoding):
    if version is NULL:
        version = "1.0"
    tree.xmlOutputBufferWriteString(c_buffer, "<?xml version='")
    tree.xmlOutputBufferWriteString(c_buffer, version)
    tree.xmlOutputBufferWriteString(c_buffer, "' encoding='")
    tree.xmlOutputBufferWriteString(c_buffer, encoding)
    tree.xmlOutputBufferWriteString(c_buffer, "'?>\n")

cdef void _writeDtdToBuffer(tree.xmlOutputBuffer* c_buffer,
                            xmlDoc* c_doc, char* c_root_name, char* encoding):
    cdef tree.xmlDtd* c_dtd
    cdef xmlNode* c_node
    c_dtd = c_doc.intSubset
    if c_dtd == NULL or c_dtd.name == NULL:
        return
    if c_dtd.ExternalID == NULL and c_dtd.SystemID == NULL:
        return
    if cstd.strcmp(c_root_name, c_dtd.name) != 0:
        return
    tree.xmlOutputBufferWrite(c_buffer, 10, "<!DOCTYPE ")
    tree.xmlOutputBufferWriteString(c_buffer, c_dtd.name)
    if c_dtd.ExternalID != NULL:
        tree.xmlOutputBufferWrite(c_buffer, 9, ' PUBLIC "')
        tree.xmlOutputBufferWriteString(c_buffer, c_dtd.ExternalID)
        tree.xmlOutputBufferWrite(c_buffer, 3, '" "')
    else:
        tree.xmlOutputBufferWrite(c_buffer, 9, ' SYSTEM "')
    tree.xmlOutputBufferWriteString(c_buffer, c_dtd.SystemID)
    if c_dtd.entities == NULL and c_dtd.elements == NULL and \
           c_dtd.attributes == NULL and c_dtd.notations == NULL and \
           c_dtd.pentities == NULL:
        tree.xmlOutputBufferWrite(c_buffer, 3, '">\n')
        return
    tree.xmlOutputBufferWrite(c_buffer, 4, '" [\n')
    if c_dtd.notations != NULL:
        tree.xmlDumpNotationTable(c_buffer.buffer,
                                  <tree.xmlNotationTable*>c_dtd.notations)
    c_node = c_dtd.children
    while c_node is not NULL:
        tree.xmlNodeDumpOutput(c_buffer, c_node.doc, c_node, 0, 0, encoding)
        c_node = c_node.next
    tree.xmlOutputBufferWrite(c_buffer, 3, "]>\n")

cdef void _writeTail(tree.xmlOutputBuffer* c_buffer, xmlNode* c_node,
                     char* encoding, int pretty_print):
    "Write the element tail."
    c_node = c_node.next
    while c_node is not NULL and c_node.type == tree.XML_TEXT_NODE:
        tree.xmlNodeDumpOutput(c_buffer, c_node.doc, c_node, 0,
                               pretty_print, encoding)
        c_node = c_node.next

cdef void _writePrevSiblings(tree.xmlOutputBuffer* c_buffer, xmlNode* c_node,
                             char* encoding, int pretty_print):
    cdef xmlNode* c_sibling
    if c_node.parent is not NULL and _isElement(c_node.parent):
        return
    # we are at a root node, so add PI and comment siblings
    c_sibling = c_node
    while c_sibling.prev != NULL and \
              (c_sibling.prev.type == tree.XML_PI_NODE or \
               c_sibling.prev.type == tree.XML_COMMENT_NODE):
        c_sibling = c_sibling.prev
    while c_sibling != c_node:
        tree.xmlNodeDumpOutput(c_buffer, c_node.doc, c_sibling, 0,
                               pretty_print, encoding)
        c_sibling = c_sibling.next

cdef void _writeNextSiblings(tree.xmlOutputBuffer* c_buffer, xmlNode* c_node,
                             char* encoding, int pretty_print):
    cdef xmlNode* c_sibling
    if c_node.parent is not NULL and _isElement(c_node.parent):
        return
    # we are at a root node, so add PI and comment siblings
    c_sibling = c_node.next
    while c_sibling != NULL and \
              (c_sibling.type == tree.XML_PI_NODE or \
               c_sibling.type == tree.XML_COMMENT_NODE):
        tree.xmlNodeDumpOutput(c_buffer, c_node.doc, c_sibling, 0,
                               pretty_print, encoding)
        c_sibling = c_sibling.next

# output to file-like objects

cdef class _FilelikeWriter:
    cdef object _filelike
    cdef _ExceptionContext _exc_context
    cdef _ErrorLog error_log
    def __init__(self, filelike, exc_context=None):
        self._filelike = filelike
        if exc_context is None:
            self._exc_context = _ExceptionContext()
        else:
            self._exc_context = exc_context
        self.error_log = _ErrorLog()

    cdef tree.xmlOutputBuffer* _createOutputBuffer(
        self, tree.xmlCharEncodingHandler* enchandler) except NULL:
        cdef tree.xmlOutputBuffer* c_buffer
        c_buffer = tree.xmlOutputBufferCreateIO(
            _writeFilelikeWriter, _closeFilelikeWriter,
            <python.PyObject*>self, enchandler)
        if c_buffer is NULL:
            raise IOError, "Could not create I/O writer context."
        return c_buffer

    cdef int write(self, char* c_buffer, int size):
        try:
            if self._filelike is None:
                raise IOError, "File is already closed"
            py_buffer = python.PyString_FromStringAndSize(c_buffer, size)
            self._filelike.write(py_buffer)
            return size
        except:
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

cdef _tofilelike(f, _Element element, encoding,
                 int write_xml_declaration, int write_doctype,
                 int pretty_print):
    cdef python.PyThreadState* state
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

    if _isString(f):
        filename8 = _encodeFilename(f)
        c_buffer = tree.xmlOutputBufferCreateFilename(
            _cstr(filename8), enchandler, 0)
        if c_buffer is NULL:
            python.PyErr_SetFromErrno(IOError)
        state = python.PyEval_SaveThread()
    elif hasattr(f, 'write'):
        writer   = _FilelikeWriter(f)
        c_buffer = writer._createOutputBuffer(enchandler)
    else:
        tree.xmlCharEncCloseFunc(enchandler)
        raise TypeError, "File or filename expected, got '%s'" % type(f)

    _writeNodeToBuffer(c_buffer, element._c_node, c_enc,
                       write_xml_declaration, write_doctype, pretty_print)
    tree.xmlOutputBufferClose(c_buffer)
    tree.xmlCharEncCloseFunc(enchandler)
    if writer is None:
        python.PyEval_RestoreThread(state)
    else:
        writer._exc_context._raise_if_stored()

cdef _tofilelikeC14N(f, _Element element):
    cdef python.PyThreadState* state
    cdef _FilelikeWriter writer
    cdef tree.xmlOutputBuffer* c_buffer
    cdef char* c_filename
    cdef xmlDoc* c_base_doc
    cdef xmlDoc* c_doc
    cdef int bytes

    c_base_doc = element._c_node.doc
    c_doc = _fakeRootDoc(c_base_doc, element._c_node)
    try:
        if _isString(f):
            filename8 = _encodeFilename(f)
            c_filename = _cstr(filename8)
            state = python.PyEval_SaveThread()
            bytes = c14n.xmlC14NDocSave(c_doc, NULL, 0, NULL, 1, c_filename, 0)
            python.PyEval_RestoreThread(state)
        elif hasattr(f, 'write'):
            writer   = _FilelikeWriter(f)
            c_buffer = writer._createOutputBuffer(NULL)
            writer.error_log.connect()
            bytes = c14n.xmlC14NDocSaveTo(c_doc, NULL, 0, NULL, 1, c_buffer)
            writer.error_log.disconnect()
            tree.xmlOutputBufferClose(c_buffer)
        else:
            raise TypeError, "File or filename expected, got '%s'" % type(f)
    finally:
        _destroyFakeDoc(c_base_doc, c_doc)

    if writer is not None:
        writer._exc_context._raise_if_stored()

    if bytes < 0:
        message = "C14N failed"
        if writer is not None:
            errors = writer.error_log
            if len(errors):
                message = errors[0].message
        raise C14NError, message

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
