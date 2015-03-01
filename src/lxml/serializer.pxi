# XML serialization and output functions

cdef object GzipFile
from gzip import GzipFile

class SerialisationError(LxmlError):
    u"""A libxml2 error that occurred during serialisation.
    """

cdef enum _OutputMethods:
    OUTPUT_METHOD_XML
    OUTPUT_METHOD_HTML
    OUTPUT_METHOD_TEXT

cdef int _findOutputMethod(method) except -1:
    if method is None:
        return OUTPUT_METHOD_XML
    method = method.lower()
    if method == "xml":
        return OUTPUT_METHOD_XML
    if method == "html":
        return OUTPUT_METHOD_HTML
    if method == "text":
        return OUTPUT_METHOD_TEXT
    raise ValueError(u"unknown output method %r" % method)

cdef _textToString(xmlNode* c_node, encoding, bint with_tail):
    cdef bint needs_conversion
    cdef const_xmlChar* c_text
    cdef xmlNode* c_text_node
    cdef tree.xmlBuffer* c_buffer
    cdef int error_result

    c_buffer = tree.xmlBufferCreate()
    if c_buffer is NULL:
        raise MemoryError()

    with nogil:
        error_result = tree.xmlNodeBufGetContent(c_buffer, c_node)
        if with_tail:
            c_text_node = _textNodeOrSkip(c_node.next)
            while c_text_node is not NULL:
                tree.xmlBufferWriteChar(c_buffer, <const_char*>c_text_node.content)
                c_text_node = _textNodeOrSkip(c_text_node.next)
        c_text = tree.xmlBufferContent(c_buffer)

    if error_result < 0 or c_text is NULL:
        tree.xmlBufferFree(c_buffer)
        raise SerialisationError, u"Error during serialisation (out of memory?)"

    try:
        needs_conversion = 0
        if encoding is _unicode:
            needs_conversion = 1
        elif encoding is not None:
            # Python prefers lower case encoding names
            encoding = encoding.lower()
            if encoding not in (u'utf8', u'utf-8'):
                if encoding == u'ascii':
                    if isutf8(c_text):
                        # will raise a decode error below
                        needs_conversion = 1
                else:
                    needs_conversion = 1

        if needs_conversion:
            text = python.PyUnicode_DecodeUTF8(
                <const_char*>c_text, tree.xmlBufferLength(c_buffer), 'strict')
            if encoding is not _unicode:
                encoding = _utf8(encoding)
                text = python.PyUnicode_AsEncodedString(
                    text, encoding, 'strict')
        else:
            text = (<unsigned char*>c_text)[:tree.xmlBufferLength(c_buffer)]
    finally:
        tree.xmlBufferFree(c_buffer)
    return text


cdef _tostring(_Element element, encoding, doctype, method,
               bint write_xml_declaration, bint write_complete_document,
               bint pretty_print, bint with_tail, int standalone):
    u"""Serialize an element to an encoded string representation of its XML
    tree.
    """
    cdef tree.xmlOutputBuffer* c_buffer
    cdef tree.xmlBuf* c_result_buffer
    cdef tree.xmlCharEncodingHandler* enchandler
    cdef const_char* c_enc
    cdef const_xmlChar* c_version
    cdef const_xmlChar* c_doctype
    cdef int c_method
    cdef int error_result
    if element is None:
        return None
    _assertValidNode(element)
    c_method = _findOutputMethod(method)
    if c_method == OUTPUT_METHOD_TEXT:
        return _textToString(element._c_node, encoding, with_tail)
    if encoding is None or encoding is _unicode:
        c_enc = NULL
    else:
        encoding = _utf8(encoding)
        c_enc = _cstr(encoding)
    if doctype is None:
        c_doctype = NULL
    else:
        doctype = _utf8(doctype)
        c_doctype = _xcstr(doctype)
    # it is necessary to *and* find the encoding handler *and* use
    # encoding during output
    enchandler = tree.xmlFindCharEncodingHandler(c_enc)
    if enchandler is NULL and c_enc is not NULL:
        if encoding is not None:
            encoding = encoding.decode('UTF-8')
        raise LookupError, u"unknown encoding: '%s'" % encoding
    c_buffer = tree.xmlAllocOutputBuffer(enchandler)
    if c_buffer is NULL:
        tree.xmlCharEncCloseFunc(enchandler)
        raise MemoryError()

    with nogil:
        _writeNodeToBuffer(c_buffer, element._c_node, c_enc, c_doctype, c_method,
                           write_xml_declaration, write_complete_document,
                           pretty_print, with_tail, standalone)
        tree.xmlOutputBufferFlush(c_buffer)
        if c_buffer.conv is not NULL:
            c_result_buffer = c_buffer.conv
        else:
            c_result_buffer = c_buffer.buffer

    error_result = c_buffer.error
    if error_result != xmlerror.XML_ERR_OK:
        tree.xmlOutputBufferClose(c_buffer)
        _raiseSerialisationError(error_result)

    try:
        if encoding is _unicode:
            result = (<unsigned char*>tree.xmlBufContent(
                c_result_buffer))[:tree.xmlBufUse(c_result_buffer)].decode('UTF-8')
        else:
            result = <bytes>(<unsigned char*>tree.xmlBufContent(
                c_result_buffer))[:tree.xmlBufUse(c_result_buffer)]
    finally:
        error_result = tree.xmlOutputBufferClose(c_buffer)
    if error_result < 0:
        _raiseSerialisationError(error_result)
    return result

cdef bytes _tostringC14N(element_or_tree, bint exclusive, bint with_comments, inclusive_ns_prefixes):
    cdef xmlDoc* c_doc
    cdef xmlChar* c_buffer = NULL
    cdef int byte_count = -1
    cdef bytes result
    cdef _Document doc
    cdef _Element element
    cdef xmlChar **c_inclusive_ns_prefixes

    if isinstance(element_or_tree, _Element):
        _assertValidNode(<_Element>element_or_tree)
        doc = (<_Element>element_or_tree)._doc
        c_doc = _plainFakeRootDoc(doc._c_doc, (<_Element>element_or_tree)._c_node, 0)
    else:
        doc = _documentOrRaise(element_or_tree)
        _assertValidDoc(doc)
        c_doc = doc._c_doc

    c_inclusive_ns_prefixes = _convert_ns_prefixes(c_doc.dict, inclusive_ns_prefixes) if inclusive_ns_prefixes else NULL
    try:
         with nogil:
             byte_count = c14n.xmlC14NDocDumpMemory(
                 c_doc, NULL, exclusive, c_inclusive_ns_prefixes, with_comments, &c_buffer)

    finally:
         _destroyFakeDoc(doc._c_doc, c_doc)
         if c_inclusive_ns_prefixes is not NULL:
            python.PyMem_Free(c_inclusive_ns_prefixes)

    if byte_count < 0 or c_buffer is NULL:
        if c_buffer is not NULL:
            tree.xmlFree(c_buffer)
        raise C14NError, u"C14N failed"
    try:
        result = c_buffer[:byte_count]
    finally:
        tree.xmlFree(c_buffer)
    return result

cdef _raiseSerialisationError(int error_result):
    if error_result == xmlerror.XML_ERR_NO_MEMORY:
        raise MemoryError()
    message = ErrorTypes._getName(error_result)
    if message is None:
        message = u"unknown error %d" % error_result
    raise SerialisationError, message

############################################################
# low-level serialisation functions

cdef void _writeDoctype(tree.xmlOutputBuffer* c_buffer,
                        const_xmlChar* c_doctype) nogil:
    tree.xmlOutputBufferWrite(c_buffer, tree.xmlStrlen(c_doctype),
                              <const_char*>c_doctype)
    tree.xmlOutputBufferWriteString(c_buffer, "\n")

cdef void _writeNodeToBuffer(tree.xmlOutputBuffer* c_buffer,
                             xmlNode* c_node, const_char* encoding, const_xmlChar* c_doctype,
                             int c_method, bint write_xml_declaration,
                             bint write_complete_document,
                             bint pretty_print, bint with_tail,
                             int standalone) nogil:
    cdef xmlNode* c_nsdecl_node
    cdef xmlDoc* c_doc = c_node.doc
    if write_xml_declaration and c_method == OUTPUT_METHOD_XML:
        _writeDeclarationToBuffer(c_buffer, c_doc.version, encoding, standalone)
    if c_doctype:
        _writeDoctype(c_buffer, c_doctype)
    # write internal DTD subset, preceding PIs/comments, etc.
    if write_complete_document and not c_buffer.error:
        if c_doctype is NULL:
            _writeDtdToBuffer(c_buffer, c_doc, c_node.name, encoding)
        _writePrevSiblings(c_buffer, c_node, encoding, pretty_print)

    c_nsdecl_node = c_node
    if not c_node.parent or c_node.parent.type != tree.XML_DOCUMENT_NODE:
        # copy the node and add namespaces from parents
        # this is required to make libxml write them
        c_nsdecl_node = tree.xmlCopyNode(c_node, 2)
        if not c_nsdecl_node:
            c_buffer.error = xmlerror.XML_ERR_NO_MEMORY
            return
        _copyParentNamespaces(c_node, c_nsdecl_node)

        c_nsdecl_node.parent = c_node.parent
        c_nsdecl_node.children = c_node.children
        c_nsdecl_node.last = c_node.last

    # write node
    if c_method == OUTPUT_METHOD_HTML:
        tree.htmlNodeDumpFormatOutput(
            c_buffer, c_doc, c_nsdecl_node, encoding, pretty_print)
    else:
        tree.xmlNodeDumpOutput(
            c_buffer, c_doc, c_nsdecl_node, 0, pretty_print, encoding)

    if c_nsdecl_node is not c_node:
        # clean up
        c_nsdecl_node.children = c_nsdecl_node.last = NULL
        tree.xmlFreeNode(c_nsdecl_node)

    if c_buffer.error:
        return

    # write tail, trailing comments, etc.
    if with_tail:
        _writeTail(c_buffer, c_node, encoding, c_method, pretty_print)
    if write_complete_document:
        _writeNextSiblings(c_buffer, c_node, encoding, pretty_print)
    if pretty_print:
        tree.xmlOutputBufferWrite(c_buffer, 1, "\n")

cdef void _writeDeclarationToBuffer(tree.xmlOutputBuffer* c_buffer,
                                    const_xmlChar* version, const_char* encoding,
                                    int standalone) nogil:
    if version is NULL:
        version = <unsigned char*>"1.0"
    tree.xmlOutputBufferWrite(c_buffer, 15, "<?xml version='")
    tree.xmlOutputBufferWriteString(c_buffer, <const_char*>version)
    tree.xmlOutputBufferWrite(c_buffer, 12, "' encoding='")
    tree.xmlOutputBufferWriteString(c_buffer, encoding)
    if standalone == 0:
        tree.xmlOutputBufferWrite(c_buffer, 20, "' standalone='no'?>\n")
    elif standalone == 1:
        tree.xmlOutputBufferWrite(c_buffer, 21, "' standalone='yes'?>\n")
    else:
        tree.xmlOutputBufferWrite(c_buffer, 4, "'?>\n")

cdef void _writeDtdToBuffer(tree.xmlOutputBuffer* c_buffer,
                            xmlDoc* c_doc, const_xmlChar* c_root_name,
                            const_char* encoding) nogil:
    cdef tree.xmlDtd* c_dtd
    cdef xmlNode* c_node
    cdef char* quotechar
    c_dtd = c_doc.intSubset
    if not c_dtd or not c_dtd.name:
        return
    if tree.xmlStrcmp(c_root_name, c_dtd.name) != 0:
        return
    tree.xmlOutputBufferWrite(c_buffer, 10, "<!DOCTYPE ")
    tree.xmlOutputBufferWriteString(c_buffer, <const_char*>c_dtd.name)
    if c_dtd.SystemID and c_dtd.SystemID[0] != c'\0':
        if c_dtd.ExternalID != NULL and c_dtd.ExternalID[0] != c'\0':
            tree.xmlOutputBufferWrite(c_buffer, 9, ' PUBLIC "')
            tree.xmlOutputBufferWriteString(c_buffer, <const_char*>c_dtd.ExternalID)
            tree.xmlOutputBufferWrite(c_buffer, 2, '" ')
        else:
            tree.xmlOutputBufferWrite(c_buffer, 8, ' SYSTEM ')

        if tree.xmlStrchr(<const_xmlChar*>c_dtd.SystemID, c'"'):
            quotechar = '\''
        else:
            quotechar = '"'
        tree.xmlOutputBufferWrite(c_buffer, 1, quotechar)
        tree.xmlOutputBufferWriteString(c_buffer, <const_char*>c_dtd.SystemID)
        tree.xmlOutputBufferWrite(c_buffer, 1, quotechar)
    if not c_dtd.entities and not c_dtd.elements and \
           not c_dtd.attributes and not c_dtd.notations and \
           not c_dtd.pentities:
        tree.xmlOutputBufferWrite(c_buffer, 2, '>\n')
        return
    tree.xmlOutputBufferWrite(c_buffer, 3, ' [\n')
    if c_dtd.notations and not c_buffer.error:
        c_buf = tree.xmlBufferCreate()
        if not c_buf:
            c_buffer.error = xmlerror.XML_ERR_NO_MEMORY
            return
        tree.xmlDumpNotationTable(c_buf, <tree.xmlNotationTable*>c_dtd.notations)
        tree.xmlOutputBufferWrite(
            c_buffer, tree.xmlBufferLength(c_buf),
            <const_char*>tree.xmlBufferContent(c_buf))
        tree.xmlBufferFree(c_buf)
    c_node = c_dtd.children
    while c_node and not c_buffer.error:
        tree.xmlNodeDumpOutput(c_buffer, c_node.doc, c_node, 0, 0, encoding)
        c_node = c_node.next
    tree.xmlOutputBufferWrite(c_buffer, 3, "]>\n")

cdef void _writeTail(tree.xmlOutputBuffer* c_buffer, xmlNode* c_node,
                     const_char* encoding, int c_method, bint pretty_print) nogil:
    u"Write the element tail."
    c_node = c_node.next
    while c_node and not c_buffer.error and c_node.type in (
            tree.XML_TEXT_NODE, tree.XML_CDATA_SECTION_NODE):
        if c_method == OUTPUT_METHOD_HTML:
            tree.htmlNodeDumpFormatOutput(
                c_buffer, c_node.doc, c_node, encoding, pretty_print)
        else:
            tree.xmlNodeDumpOutput(
                c_buffer, c_node.doc, c_node, 0, pretty_print, encoding)
        c_node = c_node.next

cdef void _writePrevSiblings(tree.xmlOutputBuffer* c_buffer, xmlNode* c_node,
                             const_char* encoding, bint pretty_print) nogil:
    cdef xmlNode* c_sibling
    if c_node.parent and _isElement(c_node.parent):
        return
    # we are at a root node, so add PI and comment siblings
    c_sibling = c_node
    while c_sibling.prev and \
            (c_sibling.prev.type == tree.XML_PI_NODE or
             c_sibling.prev.type == tree.XML_COMMENT_NODE):
        c_sibling = c_sibling.prev
    while c_sibling is not c_node and not c_buffer.error:
        tree.xmlNodeDumpOutput(c_buffer, c_node.doc, c_sibling, 0,
                               pretty_print, encoding)
        if pretty_print:
            tree.xmlOutputBufferWriteString(c_buffer, "\n")
        c_sibling = c_sibling.next

cdef void _writeNextSiblings(tree.xmlOutputBuffer* c_buffer, xmlNode* c_node,
                             const_char* encoding, bint pretty_print) nogil:
    cdef xmlNode* c_sibling
    if c_node.parent and _isElement(c_node.parent):
        return
    # we are at a root node, so add PI and comment siblings
    c_sibling = c_node.next
    while not c_buffer.error and c_sibling and \
            (c_sibling.type == tree.XML_PI_NODE or
             c_sibling.type == tree.XML_COMMENT_NODE):
        if pretty_print:
            tree.xmlOutputBufferWriteString(c_buffer, "\n")
        tree.xmlNodeDumpOutput(c_buffer, c_node.doc, c_sibling, 0,
                               pretty_print, encoding)
        c_sibling = c_sibling.next

############################################################
# output to file-like objects

@cython.final
@cython.internal
cdef class _FilelikeWriter:
    cdef object _filelike
    cdef object _close_filelike
    cdef _ExceptionContext _exc_context
    cdef _ErrorLog error_log
    def __cinit__(self, filelike, exc_context=None, compression=None, close=False):
        if compression is not None and compression > 0:
            filelike = GzipFile(
                fileobj=filelike, mode='wb', compresslevel=compression)
            self._close_filelike = filelike.close
        elif close:
            self._close_filelike = filelike.close
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
            <tree.xmlOutputWriteCallback>_writeFilelikeWriter, _closeFilelikeWriter,
            <python.PyObject*>self, enchandler)
        if c_buffer is NULL:
            raise IOError, u"Could not create I/O writer context."
        return c_buffer

    cdef int write(self, char* c_buffer, int size):
        try:
            if self._filelike is None:
                raise IOError, u"File is already closed"
            py_buffer = <bytes>c_buffer[:size]
            self._filelike.write(py_buffer)
        except:
            size = -1
            self._exc_context._store_raised()
        finally:
            return size  # and swallow any further exceptions

    cdef int close(self):
        retval = 0
        try:
            if self._close_filelike is not None:
                self._close_filelike()
            # we should not close the file here as we didn't open it
            self._filelike = None
        except:
            retval = -1
            self._exc_context._store_raised()
        finally:
            return retval  # and swallow any further exceptions

cdef int _writeFilelikeWriter(void* ctxt, char* c_buffer, int length):
    return (<_FilelikeWriter>ctxt).write(c_buffer, length)

cdef int _closeFilelikeWriter(void* ctxt):
    return (<_FilelikeWriter>ctxt).close()

cdef _tofilelike(f, _Element element, encoding, doctype, method,
                 bint write_xml_declaration, bint write_doctype,
                 bint pretty_print, bint with_tail, int standalone,
                 int compression):
    cdef python.PyThreadState* state = NULL
    cdef _FilelikeWriter writer = None
    cdef tree.xmlOutputBuffer* c_buffer
    cdef tree.xmlCharEncodingHandler* enchandler
    cdef const_char* c_enc
    cdef const_xmlChar* c_doctype
    cdef int error_result

    c_method = _findOutputMethod(method)
    if c_method == OUTPUT_METHOD_TEXT:
        data = _textToString(element._c_node, encoding, with_tail)
        if compression:
            bytes_out = BytesIO()
            gzip_file = GzipFile(
                fileobj=bytes_out, mode='wb', compresslevel=compression)
            try:
                gzip_file.write(data)
            finally:
                gzip_file.close()
            data = bytes_out.getvalue()
        if _isString(f):
            filename8 = _encodeFilename(f)
            f = open(filename8, 'wb')
            try:
                f.write(data)
            finally:
                f.close()
        else:
            f.write(data)
        return

    if encoding is None:
        c_enc = NULL
    else:
        encoding = _utf8(encoding)
        c_enc = _cstr(encoding)
    if doctype is None:
        c_doctype = NULL
    else:
        doctype = _utf8(doctype)
        c_doctype = _xcstr(doctype)

    writer = _create_output_buffer(f, c_enc, compression, &c_buffer, close=False)
    if writer is None:
        state = python.PyEval_SaveThread()

    _writeNodeToBuffer(c_buffer, element._c_node, c_enc, c_doctype, c_method,
                       write_xml_declaration, write_doctype,
                       pretty_print, with_tail, standalone)
    error_result = c_buffer.error
    if error_result == xmlerror.XML_ERR_OK:
        error_result = tree.xmlOutputBufferClose(c_buffer)
        if error_result > 0:
            error_result = xmlerror.XML_ERR_OK
    else:
        tree.xmlOutputBufferClose(c_buffer)
    if writer is None:
        python.PyEval_RestoreThread(state)
    else:
        writer._exc_context._raise_if_stored()
    if error_result != xmlerror.XML_ERR_OK:
        _raiseSerialisationError(error_result)

cdef _create_output_buffer(f, const_char* c_enc, int compression,
                           tree.xmlOutputBuffer** c_buffer_ret, bint close):
    cdef tree.xmlOutputBuffer* c_buffer
    cdef _FilelikeWriter writer
    enchandler = tree.xmlFindCharEncodingHandler(c_enc)
    if enchandler is NULL:
        raise LookupError(u"unknown encoding: '%s'" %
                          c_enc.decode(u'UTF-8') if c_enc is not NULL else u'')
    try:
        if _isString(f):
            filename8 = _encodeFilename(f)
            c_buffer = tree.xmlOutputBufferCreateFilename(
                _cstr(filename8), enchandler, compression)
            if c_buffer is NULL:
                return python.PyErr_SetFromErrno(IOError) # raises IOError
            writer = None
        elif hasattr(f, 'write'):
            writer = _FilelikeWriter(f, compression=compression, close=close)
            c_buffer = writer._createOutputBuffer(enchandler)
        else:
            raise TypeError(
                u"File or filename expected, got '%s'" %
                python._fqtypename(f).decode('UTF-8'))
    except:
        tree.xmlCharEncCloseFunc(enchandler)
        raise
    c_buffer_ret[0] = c_buffer
    return writer

cdef xmlChar **_convert_ns_prefixes(tree.xmlDict* c_dict, ns_prefixes) except NULL:
    cdef size_t i, num_ns_prefixes = len(ns_prefixes)
    # Need to allocate one extra memory block to handle last NULL entry
    c_ns_prefixes = <xmlChar **>python.PyMem_Malloc(sizeof(xmlChar*) * (num_ns_prefixes + 1))
    if not c_ns_prefixes:
        raise MemoryError()
    i = 0
    try:
        for prefix in ns_prefixes:
             prefix_utf = _utf8(prefix)
             c_prefix = tree.xmlDictExists(c_dict, _xcstr(prefix_utf), len(prefix_utf))
             if c_prefix:
                 # unknown prefixes do not need to get serialised
                 c_ns_prefixes[i] = <xmlChar*>c_prefix
                 i += 1
    except:
        python.PyMem_Free(c_ns_prefixes)
        raise

    c_ns_prefixes[i] = NULL  # append end marker
    return c_ns_prefixes

cdef _tofilelikeC14N(f, _Element element, bint exclusive, bint with_comments,
                     int compression, inclusive_ns_prefixes):
    cdef _FilelikeWriter writer = None
    cdef tree.xmlOutputBuffer* c_buffer
    cdef xmlChar **c_inclusive_ns_prefixes = NULL
    cdef char* c_filename
    cdef xmlDoc* c_base_doc
    cdef xmlDoc* c_doc
    cdef int bytes_count, error = 0

    c_base_doc = element._c_node.doc
    c_doc = _fakeRootDoc(c_base_doc, element._c_node)
    try:
        c_inclusive_ns_prefixes = (
            _convert_ns_prefixes(c_doc.dict, inclusive_ns_prefixes)
            if inclusive_ns_prefixes else NULL)

        if _isString(f):
            filename8 = _encodeFilename(f)
            c_filename = _cstr(filename8)
            with nogil:
                error = c14n.xmlC14NDocSave(
                    c_doc, NULL, exclusive, c_inclusive_ns_prefixes,
                    with_comments, c_filename, compression)
        elif hasattr(f, 'write'):
            writer   = _FilelikeWriter(f, compression=compression)
            c_buffer = writer._createOutputBuffer(NULL)
            with writer.error_log:
                bytes_count = c14n.xmlC14NDocSaveTo(
                    c_doc, NULL, exclusive, c_inclusive_ns_prefixes,
                    with_comments, c_buffer)
                error = tree.xmlOutputBufferClose(c_buffer)
            if bytes_count < 0:
                error = bytes_count
        else:
            raise TypeError(u"File or filename expected, got '%s'" %
                            python._fqtypename(f).decode('UTF-8'))
    finally:
        _destroyFakeDoc(c_base_doc, c_doc)
        if c_inclusive_ns_prefixes is not NULL:
            python.PyMem_Free(c_inclusive_ns_prefixes)

    if writer is not None:
        writer._exc_context._raise_if_stored()

    if error < 0:
        message = u"C14N failed"
        if writer is not None:
            errors = writer.error_log
            if len(errors):
                message = errors[0].message
        raise C14NError(message)

# incremental serialisation

cdef class xmlfile:
    """xmlfile(self, output_file, encoding=None, compression=None, close=False, buffered=True)

    A simple mechanism for incremental XML serialisation.

    Usage example::

         with xmlfile("somefile.xml", encoding='utf-8') as xf:
             xf.write_declaration(standalone=True)
             xf.write_doctype('<!DOCTYPE root SYSTEM "some.dtd">')

             # generate an element (the root element)
             with xf.element('root'):
                  # write a complete Element into the open root element
                  xf.write(etree.Element('test'))

                  # generate and write more Elements, e.g. through iterparse
                  for element in generate_some_elements():
                      # serialise generated elements into the XML file
                      xf.write(element)

                  # or write multiple Elements or strings at once
                  xf.write(etree.Element('start'), "text", etree.Element('end'))

    If 'output_file' is a file(-like) object, passing ``close=True`` will
    close it when exiting the context manager.  By default, it is left
    to the owner to do that.  When a file path is used, lxml will take care
    of opening and closing the file itself.  Also, when a compression level
    is set, lxml will deliberately close the file to make sure all data gets
    compressed and written.

    Setting ``buffered=False`` will flush the output after each operation,
    such as opening or closing an ``xf.element()`` block or calling
    ``xf.write()``.  Alternatively, calling ``xf.flush()`` can be used to
    explicitly flush any pending output when buffering is enabled.
    """
    cdef object output_file
    cdef bytes encoding
    cdef _IncrementalFileWriter writer
    cdef int compresslevel
    cdef bint close
    cdef bint buffered
    cdef int method

    def __init__(self, output_file not None, encoding=None, compression=None,
                 close=False, buffered=True):
        self.output_file = output_file
        self.encoding = _utf8orNone(encoding)
        self.compresslevel = compression or 0
        self.close = close
        self.buffered = buffered
        self.method = OUTPUT_METHOD_XML

    def __enter__(self):
        assert self.output_file is not None
        self.writer = _IncrementalFileWriter(
            self.output_file, self.encoding, self.compresslevel,
            self.close, self.buffered, self.method)
        return self.writer

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.writer is not None:
            old_writer, self.writer = self.writer, None
            raise_on_error = exc_type is None
            old_writer._close(raise_on_error)
            if self.close:
                self.output_file = None


cdef class htmlfile(xmlfile):
    """htmlfile(self, output_file, encoding=None, compression=None, close=False, buffered=True)

    A simple mechanism for incremental HTML serialisation.  Works the same as
    xmlfile.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.method = OUTPUT_METHOD_HTML


cdef enum _IncrementalFileWriterStatus:
    WRITER_STARTING = 0
    WRITER_DECL_WRITTEN = 1
    WRITER_DTD_WRITTEN = 2
    WRITER_IN_ELEMENT = 3
    WRITER_FINISHED = 4


@cython.final
@cython.internal
cdef class _IncrementalFileWriter:
    cdef tree.xmlOutputBuffer* _c_out
    cdef bytes _encoding
    cdef const_char* _c_encoding
    cdef _FilelikeWriter _target
    cdef list _element_stack
    cdef int _status
    cdef int _method
    cdef bint _buffered

    def __cinit__(self, outfile, bytes encoding, int compresslevel, bint close,
                  bint buffered, int method):
        self._status = WRITER_STARTING
        self._element_stack = []
        if encoding is None:
            encoding = b'ASCII'
        self._encoding = encoding
        self._c_encoding = _cstr(encoding) if encoding is not None else NULL
        self._buffered = buffered
        self._target = _create_output_buffer(
            outfile, self._c_encoding, compresslevel, &self._c_out, close)
        self._method = method

    def __dealloc__(self):
        if self._c_out is not NULL:
            tree.xmlOutputBufferClose(self._c_out)

    def write_declaration(self, version=None, standalone=None, doctype=None):
        """write_declaration(self, version=None, standalone=None, doctype=None)

        Write an XML declaration and (optionally) a doctype into the file.
        """
        assert self._c_out is not NULL
        cdef const_xmlChar* c_version
        cdef int c_standalone
        if self._method != OUTPUT_METHOD_XML:
            raise LxmlSyntaxError("only XML documents have declarations")
        if self._status >= WRITER_DECL_WRITTEN:
            raise LxmlSyntaxError("XML declaration already written")
        version = _utf8orNone(version)
        c_version = _xcstr(version) if version is not None else NULL
        doctype = _utf8orNone(doctype)
        if standalone is None:
            c_standalone = -1
        else:
            c_standalone = 1 if standalone else 0
        _writeDeclarationToBuffer(self._c_out, c_version, self._c_encoding, c_standalone)
        if doctype is not None:
            _writeDoctype(self._c_out, _xcstr(doctype))
            self._status = WRITER_DTD_WRITTEN
        else:
            self._status = WRITER_DECL_WRITTEN
        if not self._buffered:
            tree.xmlOutputBufferFlush(self._c_out)
        self._handle_error(self._c_out.error)

    def write_doctype(self, doctype):
        """write_doctype(self, doctype)

        Writes the given doctype declaration verbatimly into the file.
        """
        assert self._c_out is not NULL
        if doctype is None:
            return
        if self._status >= WRITER_DTD_WRITTEN:
            raise LxmlSyntaxError("DOCTYPE already written or cannot write it here")
        doctype = _utf8(doctype)
        _writeDoctype(self._c_out, _xcstr(doctype))
        self._status = WRITER_DTD_WRITTEN
        if not self._buffered:
            tree.xmlOutputBufferFlush(self._c_out)
        self._handle_error(self._c_out.error)

    def element(self, tag, attrib=None, nsmap=None, **_extra):
        """element(self, tag, attrib=None, nsmap=None, **_extra)

        Returns a context manager that writes an opening and closing tag.
        """
        assert self._c_out is not NULL
        attributes = []
        if attrib is not None:
            if isinstance(attrib, (dict, _Attrib)):
                attrib = attrib.items()
            for name, value in attrib:
                if name not in _extra:
                    ns, name = _getNsTag(name)
                    attributes.append((ns, name, _utf8(value)))
        if _extra:
            for name, value in _extra.iteritems():
                ns, name = _getNsTag(name)
                attributes.append((ns, name, _utf8(value)))
        reversed_nsmap = {}
        if nsmap:
            for prefix, ns in nsmap.items():
                if prefix is not None:
                    prefix = _utf8(prefix)
                    _prefixValidOrRaise(prefix)
                reversed_nsmap[_utf8(ns)] = prefix
        ns, name = _getNsTag(tag)
        return _FileWriterElement(self, (ns, name, attributes, reversed_nsmap))

    cdef _write_qname(self, bytes name, bytes prefix):
        if prefix:  # empty bytes for no prefix (not None to allow sorting)
            tree.xmlOutputBufferWrite(self._c_out, len(prefix), _cstr(prefix))
            tree.xmlOutputBufferWrite(self._c_out, 1, ':')
        tree.xmlOutputBufferWrite(self._c_out, len(name), _cstr(name))

    cdef _write_start_element(self, element_config):
        if self._status > WRITER_IN_ELEMENT:
            raise LxmlSyntaxError("cannot append trailing element to complete XML document")
        ns, name, attributes, nsmap = element_config
        flat_namespace_map, new_namespaces = self._collect_namespaces(nsmap)
        prefix = self._find_prefix(ns, flat_namespace_map, new_namespaces)
        tree.xmlOutputBufferWrite(self._c_out, 1, '<')
        self._write_qname(name, prefix)

        self._write_attributes_and_namespaces(
            attributes, flat_namespace_map, new_namespaces)

        tree.xmlOutputBufferWrite(self._c_out, 1, '>')
        if not self._buffered:
            tree.xmlOutputBufferFlush(self._c_out)
        self._handle_error(self._c_out.error)

        self._element_stack.append((ns, name, prefix, flat_namespace_map))
        self._status = WRITER_IN_ELEMENT

    cdef _write_attributes_and_namespaces(self, list attributes,
                                          dict flat_namespace_map,
                                          list new_namespaces):
        if attributes:
            # _find_prefix() may append to new_namespaces => build them first
            attributes = [
                (self._find_prefix(ns, flat_namespace_map, new_namespaces), name, value)
                for ns, name, value in attributes ]
        if new_namespaces:
            new_namespaces.sort()
            self._write_attributes_list(new_namespaces)
        if attributes:
            self._write_attributes_list(attributes)

    cdef _write_attributes_list(self, list attributes):
        for prefix, name, value in attributes:
            tree.xmlOutputBufferWrite(self._c_out, 1, ' ')
            self._write_qname(name, prefix)
            tree.xmlOutputBufferWrite(self._c_out, 2, '="')
            tree.xmlOutputBufferWriteEscape(self._c_out, _xcstr(value), NULL)
            tree.xmlOutputBufferWrite(self._c_out, 1, '"')

    cdef _write_end_element(self, element_config):
        if self._status != WRITER_IN_ELEMENT:
            raise LxmlSyntaxError("not in an element")
        if not self._element_stack or self._element_stack[-1][:2] != element_config[:2]:
            raise LxmlSyntaxError("inconsistent exit action in context manager")

        name, prefix = self._element_stack.pop()[1:3]
        tree.xmlOutputBufferWrite(self._c_out, 2, '</')
        self._write_qname(name, prefix)
        tree.xmlOutputBufferWrite(self._c_out, 1, '>')

        if not self._element_stack:
            self._status = WRITER_FINISHED
        if not self._buffered:
            tree.xmlOutputBufferFlush(self._c_out)
        self._handle_error(self._c_out.error)

    cdef _find_prefix(self, bytes href, dict flat_namespaces_map, list new_namespaces):
        if href is None:
            return None
        if href in flat_namespaces_map:
            return flat_namespaces_map[href]
        # need to create a new prefix
        prefixes = flat_namespaces_map.values()
        i = 0
        while True:
            prefix = _utf8('ns%d' % i)
            if prefix not in prefixes:
                new_namespaces.append((b'xmlns', prefix, href))
                flat_namespaces_map[href] = prefix
                return prefix
            i += 1

    cdef _collect_namespaces(self, dict nsmap):
        new_namespaces = []
        flat_namespaces_map = {}
        for ns, prefix in nsmap.iteritems():
            flat_namespaces_map[ns] = prefix
            if prefix is None:
                # use empty bytes rather than None to allow sorting
                new_namespaces.append((b'', b'xmlns', ns))
            else:
                new_namespaces.append((b'xmlns', prefix, ns))
        # merge in flat namespace map of parent
        if self._element_stack:
            for ns, prefix in (<dict>self._element_stack[-1][-1]).iteritems():
                if flat_namespaces_map.get(ns) is None:
                    # unknown or empty prefix => prefer a 'real' prefix
                    flat_namespaces_map[ns] = prefix
        return flat_namespaces_map, new_namespaces

    def write(self, *args, bint with_tail=True, bint pretty_print=False):
        """write(self, *args, with_tail=True, pretty_print=False)

        Write subtrees or strings into the file.
        """
        assert self._c_out is not NULL
        for content in args:
            if _isString(content):
                if self._status != WRITER_IN_ELEMENT:
                    if self._status > WRITER_IN_ELEMENT or content.strip():
                        raise LxmlSyntaxError("not in an element")
                content = _utf8(content)
                tree.xmlOutputBufferWriteEscape(self._c_out, _xcstr(content), NULL)
            elif iselement(content):
                if self._status > WRITER_IN_ELEMENT:
                    raise LxmlSyntaxError("cannot append trailing element to complete XML document")
                _writeNodeToBuffer(self._c_out, (<_Element>content)._c_node,
                                   self._c_encoding, NULL, self._method,
                                   False, False, pretty_print, with_tail, False)
                if (<_Element>content)._c_node.type == tree.XML_ELEMENT_NODE:
                    if not self._element_stack:
                        self._status = WRITER_FINISHED
            else:
                raise TypeError("got invalid input value of type %s, expected string or Element" % type(content))
            self._handle_error(self._c_out.error)
        if not self._buffered:
            tree.xmlOutputBufferFlush(self._c_out)

    def flush(self):
        """flush(self)

        Write any pending content of the current output buffer to the stream.
        """
        assert self._c_out is not NULL
        tree.xmlOutputBufferFlush(self._c_out)

    cdef _close(self, bint raise_on_error):
        if raise_on_error:
            if self._status < WRITER_IN_ELEMENT:
                raise LxmlSyntaxError("no content written")
            if self._element_stack:
                raise LxmlSyntaxError("pending open tags on close")
        error_result = self._c_out.error
        if error_result == xmlerror.XML_ERR_OK:
            error_result = tree.xmlOutputBufferClose(self._c_out)
            if error_result > 0:
                error_result = xmlerror.XML_ERR_OK
        else:
            tree.xmlOutputBufferClose(self._c_out)
        self._status = WRITER_FINISHED
        self._c_out = NULL
        del self._element_stack[:]
        if raise_on_error:
            self._handle_error(error_result)

    cdef _handle_error(self, int error_result):
        if error_result != xmlerror.XML_ERR_OK:
            if self._target is not None:
                self._target._exc_context._raise_if_stored()
            _raiseSerialisationError(error_result)

@cython.final
@cython.internal
@cython.freelist(8)
cdef class _FileWriterElement:
    cdef object _element
    cdef _IncrementalFileWriter _writer

    def __cinit__(self, _IncrementalFileWriter writer not None, element_config):
        self._writer = writer
        self._element = element_config

    def __enter__(self):
        self._writer._write_start_element(self._element)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._writer._write_end_element(self._element)
