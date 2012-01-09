# Parsers for XML and HTML

cimport xmlparser
cimport htmlparser

cdef class _ParserContext(_ResolverContext)
cdef class _SaxParserContext(_ParserContext)
cdef class _TargetParserContext(_SaxParserContext)
cdef class _ParserSchemaValidationContext
cdef class _Validator
cdef class XMLSchema(_Validator)

class ParseError(LxmlSyntaxError):
    u"""Syntax error while parsing an XML document.

    For compatibility with ElementTree 1.3 and later.
    """
    def __init__(self, message, code, line, column):
        if python.PY_VERSION_HEX >= 0x02050000:
            # Python >= 2.5 uses new style class exceptions
            super(_ParseError, self).__init__(message)
        else:
            _LxmlSyntaxError.__init__(self, message)
        self.position = (line, column)
        self.code = code

cdef object _LxmlSyntaxError = LxmlSyntaxError
cdef object _ParseError = ParseError

class XMLSyntaxError(ParseError):
    u"""Syntax error while parsing an XML document.
    """
    pass

class ParserError(LxmlError):
    u"""Internal lxml parser error.
    """
    pass

@cython.final
@cython.internal
cdef class _ParserDictionaryContext:
    # Global parser context to share the string dictionary.
    #
    # This class is a delegate singleton!
    #
    # It creates _ParserDictionaryContext objects for each thread to keep thread state,
    # but those must never be used directly.  Always stick to using the static
    # __GLOBAL_PARSER_CONTEXT as defined below the class.
    #

    cdef tree.xmlDict* _c_dict
    cdef _BaseParser _default_parser
    cdef list _implied_parser_contexts

    def __cinit__(self):
        self._c_dict = NULL
        self._implied_parser_contexts = []

    def __dealloc__(self):
        if self._c_dict is not NULL:
            xmlparser.xmlDictFree(self._c_dict)

    cdef void initMainParserContext(self):
        u"""Put the global context into the thread dictionary of the main
        thread.  To be called once and only in the main thread."""
        cdef python.PyObject* thread_dict
        cdef python.PyObject* result
        thread_dict = python.PyThreadState_GetDict()
        if thread_dict is not NULL:
            (<dict>thread_dict)[u"_ParserDictionaryContext"] = self

    cdef _ParserDictionaryContext _findThreadParserContext(self):
        u"Find (or create) the _ParserDictionaryContext object for the current thread"
        cdef python.PyObject* thread_dict
        cdef python.PyObject* result
        cdef _ParserDictionaryContext context
        thread_dict = python.PyThreadState_GetDict()
        if thread_dict is NULL:
            return self
        d = <dict>thread_dict
        result = python.PyDict_GetItem(d, u"_ParserDictionaryContext")
        if result is not NULL:
            return <object>result
        context = _ParserDictionaryContext()
        d[u"_ParserDictionaryContext"] = context
        return context

    cdef void setDefaultParser(self, _BaseParser parser):
        u"Set the default parser for the current thread"
        cdef _ParserDictionaryContext context
        context = self._findThreadParserContext()
        context._default_parser = parser

    cdef _BaseParser getDefaultParser(self):
        u"Return (or create) the default parser of the current thread"
        cdef _ParserDictionaryContext context
        context = self._findThreadParserContext()
        if context._default_parser is None:
            if self._default_parser is None:
                self._default_parser = __DEFAULT_XML_PARSER._copy()
            if context is not self:
                context._default_parser = self._default_parser._copy()
        return context._default_parser

    cdef tree.xmlDict* _getThreadDict(self, tree.xmlDict* default):
        u"Return the thread-local dict or create a new one if necessary."
        cdef _ParserDictionaryContext context
        context = self._findThreadParserContext()
        if context._c_dict is NULL:
            # thread dict not yet set up => use default or create a new one
            if default is not NULL:
                context._c_dict = default
                xmlparser.xmlDictReference(default)
                return default
            if self._c_dict is NULL:
                self._c_dict = xmlparser.xmlDictCreate()
            if context is not self:
                context._c_dict = xmlparser.xmlDictCreateSub(self._c_dict)
        return context._c_dict

    cdef void initThreadDictRef(self, tree.xmlDict** c_dict_ref):
        cdef tree.xmlDict* c_dict
        cdef tree.xmlDict* c_thread_dict
        c_dict = c_dict_ref[0]
        c_thread_dict = self._getThreadDict(c_dict)
        if c_dict is c_thread_dict:
            return
        if c_dict is not NULL:
            xmlparser.xmlDictFree(c_dict)
        c_dict_ref[0] = c_thread_dict
        xmlparser.xmlDictReference(c_thread_dict)

    cdef void initParserDict(self, xmlparser.xmlParserCtxt* pctxt):
        u"Assure we always use the same string dictionary."
        self.initThreadDictRef(&pctxt.dict)

    cdef void initXPathParserDict(self, xpath.xmlXPathContext* pctxt):
        u"Assure we always use the same string dictionary."
        self.initThreadDictRef(&pctxt.dict)

    cdef void initDocDict(self, xmlDoc* result):
        u"Store dict of last object parsed if no shared dict yet"
        # XXX We also free the result dict here if there already was one.
        # This case should only occur for new documents with empty dicts,
        # otherwise we'd free data that's in use => segfault
        self.initThreadDictRef(&result.dict)

    cdef _ParserContext findImpliedContext(self):
        u"""Return any current implied xml parser context for the current
        thread.  This is used when the resolver functions are called
        with an xmlParserCtxt that was generated from within libxml2
        (i.e. without a _ParserContext) - which happens when parsing
        schema and xinclude external references."""
        cdef _ParserDictionaryContext context
        cdef _ParserContext implied_context

        # see if we have a current implied parser
        context = self._findThreadParserContext()
        if python.PyList_GET_SIZE(context._implied_parser_contexts):
            implied_context = context._implied_parser_contexts[-1]
            return implied_context
        return None

    cdef void pushImpliedContextFromParser(self, _BaseParser parser):
        u"Push a new implied context object taken from the parser."
        if parser is not None:
            self.pushImpliedContext(parser._getParserContext())
        else:
            self.pushImpliedContext(None)

    cdef void pushImpliedContext(self, _ParserContext parser_context):
        u"Push a new implied context object."
        cdef _ParserDictionaryContext context
        context = self._findThreadParserContext()
        context._implied_parser_contexts.append(parser_context)

    cdef void popImpliedContext(self):
        u"Pop the current implied context object."
        cdef _ParserDictionaryContext context
        context = self._findThreadParserContext()
        context._implied_parser_contexts.pop()

cdef _ParserDictionaryContext __GLOBAL_PARSER_CONTEXT
__GLOBAL_PARSER_CONTEXT = _ParserDictionaryContext()
__GLOBAL_PARSER_CONTEXT.initMainParserContext()

cdef int _checkThreadDict(tree.xmlDict* c_dict):
    u"""Check that c_dict is either the local thread dictionary or the global
    parent dictionary.
    """
    #if __GLOBAL_PARSER_CONTEXT._c_dict is c_dict:
    #    return 1 # main thread
    if __GLOBAL_PARSER_CONTEXT._getThreadDict(NULL) is c_dict:
        return 1 # local thread dict
    return 0

############################################################
## support for Python unicode I/O
############################################################

# name of Python unicode encoding as known to libxml2
cdef char* _UNICODE_ENCODING = NULL

cdef int _setupPythonUnicode() except -1:
    u"""Sets _UNICODE_ENCODING to the internal encoding name of Python unicode
    strings if libxml2 supports reading native Python unicode.  This depends
    on iconv and the local Python installation, so we simply check if we find
    a matching encoding handler.
    """
    cdef tree.xmlCharEncodingHandler* enchandler
    cdef Py_ssize_t l
    cdef char* buffer
    cdef char* enc
    utext = python.PyUnicode_DecodeUTF8("<test/>", 7, NULL)
    l = python.PyUnicode_GET_DATA_SIZE(utext)
    buffer = python.PyUnicode_AS_DATA(utext)
    enc = _findEncodingName(buffer, l)
    if enc == NULL:
        # apparently, libxml2 can't detect UTF-16 on some systems
        if l >= 4 and \
               buffer[0] == c'<' and buffer[1] == c'\0' and \
               buffer[2] == c't' and buffer[3] == c'\0':
            enc = "UTF-16LE"
        elif l >= 4 and \
               buffer[0] == c'\0' and buffer[1] == c'<' and \
               buffer[2] == c'\0' and buffer[3] == c't':
            enc = "UTF-16BE"
        else:
            # not my fault, it's YOUR broken system :)
            return 0
    enchandler = tree.xmlFindCharEncodingHandler(enc)
    if enchandler is not NULL:
        global _UNICODE_ENCODING
        tree.xmlCharEncCloseFunc(enchandler)
        _UNICODE_ENCODING = enc
    return 0

cdef char* _findEncodingName(char* buffer, int size):
    u"Work around bug in libxml2: find iconv name of encoding on our own."
    cdef tree.xmlCharEncoding enc
    enc = tree.xmlDetectCharEncoding(buffer, size)
    if enc == tree.XML_CHAR_ENCODING_UTF16LE:
        return "UTF-16LE"
    elif enc == tree.XML_CHAR_ENCODING_UTF16BE:
        return "UTF-16BE"
    elif enc == tree.XML_CHAR_ENCODING_UCS4LE:
        return "UCS-4LE"
    elif enc == tree.XML_CHAR_ENCODING_UCS4BE:
        return "UCS-4BE"
    elif enc == tree.XML_CHAR_ENCODING_NONE:
        return NULL
    else:
        # returns a constant char*, no need to free it
        return tree.xmlGetCharEncodingName(enc)

_setupPythonUnicode()

############################################################
## support for file-like objects
############################################################

@cython.final
@cython.internal
cdef class _FileReaderContext:
    cdef object _filelike
    cdef object _encoding
    cdef object _url
    cdef object _bytes
    cdef _ExceptionContext _exc_context
    cdef Py_ssize_t _bytes_read
    cdef char* _c_url
    cdef bint _close_file_after_read

    def __cinit__(self, filelike, exc_context, url, encoding=None, bint close_file=False):
        self._exc_context = exc_context
        self._filelike = filelike
        self._close_file_after_read = close_file
        self._encoding = encoding
        if url is None:
            self._c_url = NULL
        else:
            url = _encodeFilename(url)
            self._c_url = _cstr(url)
        self._url = url
        self._bytes  = b''
        self._bytes_read = 0

    cdef _close_file(self):
        if self._filelike is None or not self._close_file_after_read:
            return
        try:
            close = self._filelike.close
        except AttributeError:
            close = None
        finally:
            self._filelike = None
        if close is not None:
            close()

    cdef xmlparser.xmlParserInputBuffer* _createParserInputBuffer(self):
        cdef stdio.FILE* c_stream
        cdef xmlparser.xmlParserInputBuffer* c_buffer
        c_buffer = xmlparser.xmlAllocParserInputBuffer(0)
        c_stream = python.PyFile_AsFile(self._filelike)
        if c_stream is NULL:
            c_buffer.readcallback  = _readFilelikeParser
            c_buffer.context = <python.PyObject*>self
        else:
            c_buffer.readcallback  = _readFileParser
            c_buffer.context = c_stream
        return c_buffer

    cdef xmlparser.xmlParserInput* _createParserInput(
            self, xmlparser.xmlParserCtxt* ctxt):
        cdef xmlparser.xmlParserInputBuffer* c_buffer
        c_buffer = self._createParserInputBuffer()
        return xmlparser.xmlNewIOInputStream(ctxt, c_buffer, 0)

    cdef tree.xmlDtd* _readDtd(self):
        cdef xmlparser.xmlParserInputBuffer* c_buffer
        c_buffer = self._createParserInputBuffer()
        with nogil:
            return xmlparser.xmlIOParseDTD(NULL, c_buffer, 0)

    cdef xmlDoc* _readDoc(self, xmlparser.xmlParserCtxt* ctxt, int options):
        cdef xmlDoc* result
        cdef char* c_encoding
        cdef stdio.FILE* c_stream
        cdef xmlparser.xmlInputReadCallback c_read_callback
        cdef xmlparser.xmlInputCloseCallback c_close_callback
        cdef void* c_callback_context

        if self._encoding is None:
            c_encoding = NULL
        else:
            c_encoding = _cstr(self._encoding)

        c_stream = python.PyFile_AsFile(self._filelike)
        if c_stream is NULL:
            c_read_callback  = _readFilelikeParser
            c_callback_context = <python.PyObject*>self
        else:
            c_read_callback  = _readFileParser
            c_callback_context = c_stream

        with nogil:
            if ctxt.html:
                result = htmlparser.htmlCtxtReadIO(
                        ctxt, c_read_callback, NULL, c_callback_context,
                        self._c_url, c_encoding, options)
                if result is not NULL:
                    if _fixHtmlDictNames(ctxt.dict, result) < 0:
                        tree.xmlFreeDoc(result)
                        result = NULL
            else:
                result = xmlparser.xmlCtxtReadIO(
                    ctxt, c_read_callback, NULL, c_callback_context,
                    self._c_url, c_encoding, options)
        self._close_file()
        return result

    cdef int copyToBuffer(self, char* c_buffer, int c_requested):
        cdef int c_byte_count
        cdef char* c_start
        cdef Py_ssize_t byte_count, remaining
        if self._bytes_read < 0:
            return 0
        try:
            c_byte_count = 0
            byte_count = python.PyBytes_GET_SIZE(self._bytes)
            remaining  = byte_count - self._bytes_read
            while c_requested > remaining:
                c_start = _cstr(self._bytes) + self._bytes_read
                cstring_h.memcpy(c_buffer, c_start, remaining)
                c_byte_count += remaining
                c_buffer += remaining
                c_requested -= remaining

                self._bytes = self._filelike.read(c_requested)
                if not python.PyBytes_Check(self._bytes):
                    if python.PyUnicode_Check(self._bytes):
                        if self._encoding is None:
                            self._bytes = python.PyUnicode_AsUTF8String(self._bytes)
                        else:
                            self._bytes = python.PyUnicode_AsEncodedString(
                                self._bytes, _cstr(self._encoding), NULL)
                    else:
                        self._close_file()
                        raise TypeError, \
                            u"reading from file-like objects must return byte strings or unicode strings"

                remaining = python.PyBytes_GET_SIZE(self._bytes)
                if remaining == 0:
                    self._bytes_read = -1
                    self._close_file()
                    return c_byte_count
                self._bytes_read = 0

            if c_requested > 0:
                c_start = _cstr(self._bytes) + self._bytes_read
                cstring_h.memcpy(c_buffer, c_start, c_requested)
                c_byte_count += c_requested
                self._bytes_read += c_requested
            return c_byte_count
        except:
            self._exc_context._store_raised()
            self._close_file()
            return -1

cdef int _readFilelikeParser(void* ctxt, char* c_buffer, int c_size) with gil:
    return (<_FileReaderContext>ctxt).copyToBuffer(c_buffer, c_size)

cdef int _readFileParser(void* ctxt, char* c_buffer, int c_size) nogil:
    return stdio.fread(c_buffer, 1,  c_size, <stdio.FILE*>ctxt)

############################################################
## support for custom document loaders
############################################################

cdef xmlparser.xmlParserInput* _local_resolver(char* c_url, char* c_pubid,
                                               xmlparser.xmlParserCtxt* c_context) with gil:
    cdef _ResolverContext context
    cdef xmlparser.xmlParserInput* c_input
    cdef _InputDocument doc_ref
    cdef _FileReaderContext file_context
    # if there is no _ParserContext associated with the xmlParserCtxt
    # passed, check to see if the thread state object has an implied
    # context.
    if c_context._private is not NULL:
        context = <_ResolverContext>c_context._private
    else:
        context = __GLOBAL_PARSER_CONTEXT.findImpliedContext()

    if context is None:
        if __DEFAULT_ENTITY_LOADER is NULL:
            return NULL
        return __DEFAULT_ENTITY_LOADER(c_url, c_pubid, c_context)

    try:
        if c_url is NULL:
            url = None
        else:
            # parsing a related document (DTD etc.) => UTF-8 encoded URL?
            url = _decodeFilename(c_url)
        if c_pubid is NULL:
            pubid = None
        else:
            pubid = funicode(c_pubid) # always UTF-8

        doc_ref = context._resolvers.resolve(url, pubid, context)
    except:
        context._store_raised()
        return NULL

    if doc_ref is not None:
        if doc_ref._type == PARSER_DATA_STRING:
            data = doc_ref._data_bytes
            c_input = xmlparser.xmlNewInputStream(c_context)
            if c_input is not NULL:
                c_input.base = _cstr(data)
                c_input.length = python.PyBytes_GET_SIZE(data)
                c_input.cur = c_input.base
                c_input.end = &c_input.base[c_input.length]
        elif doc_ref._type == PARSER_DATA_FILENAME:
            data = None
            c_input = xmlparser.xmlNewInputFromFile(
                c_context, _cstr(doc_ref._filename))
        elif doc_ref._type == PARSER_DATA_FILE:
            file_context = _FileReaderContext(doc_ref._file, context, url,
                                              None, doc_ref._close_file)
            c_input = file_context._createParserInput(c_context)
            data = file_context
        else:
            data = None
            c_input = NULL

        if data is not None:
            context._storage.add(data)
        if c_input is not NULL:
            return c_input

    if __DEFAULT_ENTITY_LOADER is NULL:
        return NULL
    return __DEFAULT_ENTITY_LOADER(c_url, c_pubid, c_context)

cdef xmlparser.xmlExternalEntityLoader __DEFAULT_ENTITY_LOADER
__DEFAULT_ENTITY_LOADER = xmlparser.xmlGetExternalEntityLoader()

xmlparser.xmlSetExternalEntityLoader(_local_resolver)

############################################################
## Parsers
############################################################

@cython.internal
cdef class _ParserContext(_ResolverContext):
    cdef _ErrorLog _error_log
    cdef _ParserSchemaValidationContext _validator
    cdef xmlparser.xmlParserCtxt* _c_ctxt
    cdef python.PyThread_type_lock _lock
    def __cinit__(self):
        self._c_ctxt = NULL
        if not config.ENABLE_THREADING:
            self._lock = NULL
        else:
            self._lock = python.PyThread_allocate_lock()
        self._error_log = _ErrorLog()

    def __dealloc__(self):
        if self._validator is not None:
            self._validator.disconnect()
        if self._lock is not NULL:
            python.PyThread_free_lock(self._lock)
        if self._c_ctxt is not NULL:
            xmlparser.xmlFreeParserCtxt(self._c_ctxt)

    cdef _ParserContext _copy(self):
        cdef _ParserContext context
        context = self.__class__()
        context._validator = self._validator.copy()
        _initParserContext(context, self._resolvers._copy(), NULL)
        return context

    cdef void _initParserContext(self, xmlparser.xmlParserCtxt* c_ctxt):
        self._c_ctxt = c_ctxt
        c_ctxt._private = <void*>self

    cdef void _resetParserContext(self):
        if self._c_ctxt is not NULL:
            if self._c_ctxt.html:
                htmlparser.htmlCtxtReset(self._c_ctxt)
                self._c_ctxt.disableSAX = 0 # work around bug in libxml2
            elif self._c_ctxt.spaceTab is not NULL or \
                    _LIBXML_VERSION_INT >= 20629: # work around bug in libxml2
                xmlparser.xmlClearParserCtxt(self._c_ctxt)

    cdef int prepare(self) except -1:
        cdef int result
        if config.ENABLE_THREADING and self._lock is not NULL:
            with nogil:
                result = python.PyThread_acquire_lock(
                    self._lock, python.WAIT_LOCK)
            if result == 0:
                raise ParserError, u"parser locking failed"
        self._error_log.connect()
        if self._validator is not None:
            self._validator.connect(self._c_ctxt)
        return 0

    cdef int cleanup(self) except -1:
        if self._validator is not None:
            self._validator.disconnect()
        self._resetParserContext()
        self.clear()
        self._error_log.disconnect()
        if config.ENABLE_THREADING and self._lock is not NULL:
            python.PyThread_release_lock(self._lock)
        return 0

    cdef object _handleParseResult(self, _BaseParser parser,
                                   xmlDoc* result, filename):
        cdef xmlDoc* c_doc
        cdef bint recover
        recover = parser._parse_options & xmlparser.XML_PARSE_RECOVER
        c_doc = _handleParseResult(self, self._c_ctxt, result,
                                   filename, recover)
        return _documentFactory(c_doc, parser)

    cdef xmlDoc* _handleParseResultDoc(self, _BaseParser parser,
                                       xmlDoc* result, filename) except NULL:
        cdef bint recover
        recover = parser._parse_options & xmlparser.XML_PARSE_RECOVER
        return _handleParseResult(self, self._c_ctxt, result,
                                   filename, recover)

cdef _initParserContext(_ParserContext context,
                        _ResolverRegistry resolvers,
                        xmlparser.xmlParserCtxt* c_ctxt):
    _initResolverContext(context, resolvers)
    if c_ctxt is not NULL:
        context._initParserContext(c_ctxt)

cdef int _raiseParseError(xmlparser.xmlParserCtxt* ctxt, filename,
                          _ErrorLog error_log) except 0:
    if filename is not None and \
           ctxt.lastError.domain == xmlerror.XML_FROM_IO:
        if ctxt.lastError.message is not NULL:
            message = u"Error reading file '%s': %s" % (
                filename, (ctxt.lastError.message).strip())
        else:
            message = u"Error reading '%s'" % filename
        raise IOError, message
    elif error_log:
        raise error_log._buildParseException(
            XMLSyntaxError, u"Document is not well formed")
    elif ctxt.lastError.message is not NULL:
        message = (ctxt.lastError.message).strip()
        code = ctxt.lastError.code
        line = ctxt.lastError.line
        column = ctxt.lastError.int2
        if ctxt.lastError.line > 0:
            message = u"line %d: %s" % (line, message)
        raise XMLSyntaxError(message, code, line, column)
    else:
        raise XMLSyntaxError(None, xmlerror.XML_ERR_INTERNAL_ERROR, 0, 0)

cdef xmlDoc* _handleParseResult(_ParserContext context,
                                xmlparser.xmlParserCtxt* c_ctxt,
                                xmlDoc* result, filename,
                                bint recover) except NULL:
    cdef bint well_formed
    if result is not NULL:
        __GLOBAL_PARSER_CONTEXT.initDocDict(result)

    if c_ctxt.myDoc is not NULL:
        if c_ctxt.myDoc is not result:
            __GLOBAL_PARSER_CONTEXT.initDocDict(c_ctxt.myDoc)
            tree.xmlFreeDoc(c_ctxt.myDoc)
        c_ctxt.myDoc = NULL

    if result is not NULL:
        if context._validator is not None and \
                not context._validator.isvalid():
            well_formed = 0 # actually not 'valid', but anyway ...
        elif recover or (c_ctxt.wellFormed and \
                             c_ctxt.lastError.level < xmlerror.XML_ERR_ERROR):
            well_formed = 1
        elif not c_ctxt.replaceEntities and not c_ctxt.validate \
                 and context is not None:
            # in this mode, we ignore errors about undefined entities
            for error in context._error_log.filter_from_errors():
                if error.type != ErrorTypes.WAR_UNDECLARED_ENTITY and \
                       error.type != ErrorTypes.ERR_UNDECLARED_ENTITY:
                    well_formed = 0
                    break
            else:
                well_formed = 1
        else:
            well_formed = 0

        if not well_formed:
            # free broken document
            tree.xmlFreeDoc(result)
            result = NULL

    if context is not None and context._has_raised():
        if result is not NULL:
            tree.xmlFreeDoc(result)
            result = NULL
        context._raise_if_stored()

    if result is NULL:
        if context is not None:
            _raiseParseError(c_ctxt, filename, context._error_log)
        else:
            _raiseParseError(c_ctxt, filename, None)
    else:
        if result.URL is NULL and filename is not None:
            result.URL = tree.xmlStrdup(_cstr(filename))
        if result.encoding is NULL:
            result.encoding = tree.xmlStrdup("UTF-8")

    if context._validator is not None and \
           context._validator._add_default_attributes:
        # we currently need to do this here as libxml2 does not
        # support inserting default attributes during parse-time
        # validation
        context._validator.inject_default_attributes(result)

    return result

cdef int _fixHtmlDictNames(tree.xmlDict* c_dict, xmlDoc* c_doc) nogil:
    cdef xmlNode* c_node
    if c_doc is NULL:
        return 0
    c_node = c_doc.children
    tree.BEGIN_FOR_EACH_ELEMENT_FROM(<xmlNode*>c_doc, c_node, 0)
    if c_node.type == tree.XML_ELEMENT_NODE:
        if _fixHtmlDictNodeNames(c_dict, c_node) < 0:
            return -1
    tree.END_FOR_EACH_ELEMENT_FROM(c_node)
    return 0

cdef inline int _fixHtmlDictNodeNames(tree.xmlDict* c_dict,
                                      xmlNode* c_node) nogil:
    cdef xmlNode* c_attr
    cdef char* c_name
    c_name = tree.xmlDictLookup(c_dict, c_node.name, -1)
    if c_name is NULL:
        return -1
    if c_name is not c_node.name:
        tree.xmlFree(c_node.name)
        c_node.name = c_name
    c_attr = <xmlNode*>c_node.properties
    while c_attr is not NULL:
        c_name = tree.xmlDictLookup(c_dict, c_attr.name, -1)
        if c_name is NULL:
            return -1
        if c_name is not c_attr.name:
            tree.xmlFree(c_attr.name)
            c_attr.name = c_name
        c_attr = c_attr.next
    return 0

cdef class _BaseParser:
    cdef ElementClassLookup _class_lookup
    cdef _ResolverRegistry _resolvers
    cdef _ParserContext _parser_context
    cdef _ParserContext _push_parser_context
    cdef int _parse_options
    cdef bint _for_html
    cdef bint _remove_comments
    cdef bint _remove_pis
    cdef bint _strip_cdata
    cdef XMLSchema _schema
    cdef object _filename
    cdef readonly object target
    cdef object _default_encoding

    def __init__(self, int parse_options, bint for_html, XMLSchema schema,
                 remove_comments, remove_pis, strip_cdata, target,
                 filename, encoding):
        cdef tree.xmlCharEncodingHandler* enchandler
        cdef int c_encoding
        if not isinstance(self, HTMLParser) and \
                not isinstance(self, XMLParser) and \
                not isinstance(self, iterparse):
            raise TypeError, u"This class cannot be instantiated"

        self._parse_options = parse_options
        self._filename = filename
        self.target = target
        self._for_html = for_html
        self._remove_comments = remove_comments
        self._remove_pis = remove_pis
        self._strip_cdata = strip_cdata
        self._schema = schema

        self._resolvers = _ResolverRegistry()

        if encoding is None:
            self._default_encoding = None
        else:
            encoding = _utf8(encoding)
            enchandler = tree.xmlFindCharEncodingHandler(_cstr(encoding))
            if enchandler is NULL:
                raise LookupError, u"unknown encoding: '%s'" % encoding
            tree.xmlCharEncCloseFunc(enchandler)
            self._default_encoding = encoding

    cdef _ParserContext _getParserContext(self):
        cdef xmlparser.xmlParserCtxt* pctxt
        if self._parser_context is None:
            self._parser_context = self._createContext(self.target)
            if self._schema is not None:
                self._parser_context._validator = \
                    self._schema._newSaxValidator(
                        self._parse_options & xmlparser.XML_PARSE_DTDATTR)
            pctxt = self._newParserCtxt()
            if pctxt is NULL:
                python.PyErr_NoMemory()
            _initParserContext(self._parser_context, self._resolvers, pctxt)
            if self._remove_comments:
                pctxt.sax.comment = NULL
            if self._remove_pis:
                pctxt.sax.processingInstruction = NULL
            if self._strip_cdata:
                # hard switch-off for CDATA nodes => makes them plain text
                pctxt.sax.cdataBlock = NULL
        return self._parser_context

    cdef _ParserContext _getPushParserContext(self):
        cdef xmlparser.xmlParserCtxt* pctxt
        if self._push_parser_context is None:
            self._push_parser_context = self._createContext(self.target)
            if self._schema is not None:
                self._push_parser_context._validator = \
                    self._schema._newSaxValidator(
                        self._parse_options & xmlparser.XML_PARSE_DTDATTR)
            pctxt = self._newPushParserCtxt()
            if pctxt is NULL:
                python.PyErr_NoMemory()
            _initParserContext(
                self._push_parser_context, self._resolvers, pctxt)
            if self._remove_comments:
                pctxt.sax.comment = NULL
            if self._remove_pis:
                pctxt.sax.processingInstruction = NULL
            if self._strip_cdata:
                # hard switch-off for CDATA nodes => makes them plain text
                pctxt.sax.cdataBlock = NULL
        return self._push_parser_context

    cdef _ParserContext _createContext(self, target):
        cdef _TargetParserContext context
        if target is None:
            return _ParserContext()
        context = _TargetParserContext()
        context._setTarget(target)
        return context

    cdef xmlparser.xmlParserCtxt* _newParserCtxt(self):
        if self._for_html:
            return htmlparser.htmlCreateMemoryParserCtxt('dummy', 5)
        else:
            return xmlparser.xmlNewParserCtxt()

    cdef xmlparser.xmlParserCtxt* _newPushParserCtxt(self):
        cdef xmlparser.xmlParserCtxt* c_ctxt
        cdef char* c_filename
        if self._filename is not None:
            c_filename = _cstr(self._filename)
        else:
            c_filename = NULL
        if self._for_html:
            c_ctxt = htmlparser.htmlCreatePushParserCtxt(
                NULL, NULL, NULL, 0, c_filename, tree.XML_CHAR_ENCODING_NONE)
            if c_ctxt is not NULL:
                htmlparser.htmlCtxtUseOptions(c_ctxt, self._parse_options)
        else:
            c_ctxt = xmlparser.xmlCreatePushParserCtxt(
                NULL, NULL, NULL, 0, c_filename)
            if c_ctxt is not NULL:
                xmlparser.xmlCtxtUseOptions(c_ctxt, self._parse_options)
        return c_ctxt

    property error_log:
        u"""The error log of the last parser run.
        """
        def __get__(self):
            cdef _ParserContext context
            context = self._getParserContext()
            return context._error_log.copy()

    property resolvers:
        u"The custom resolver registry of this parser."
        def __get__(self):
            return self._resolvers

    property version:
        u"The version of the underlying XML parser."
        def __get__(self):
            return u"libxml2 %d.%d.%d" % LIBXML_VERSION

    def setElementClassLookup(self, ElementClassLookup lookup = None):
        u":deprecated: use ``parser.set_element_class_lookup(lookup)`` instead."
        self.set_element_class_lookup(lookup)

    def set_element_class_lookup(self, ElementClassLookup lookup = None):
        u"""set_element_class_lookup(self, lookup = None)

        Set a lookup scheme for element classes generated from this parser.

        Reset it by passing None or nothing.
        """
        self._class_lookup = lookup

    cdef _BaseParser _copy(self):
        u"Create a new parser with the same configuration."
        cdef _BaseParser parser
        parser = self.__class__()
        parser._parse_options = self._parse_options
        parser._for_html = self._for_html
        parser._remove_comments = self._remove_comments
        parser._remove_pis = self._remove_pis
        parser._strip_cdata = self._strip_cdata
        parser._filename = self._filename
        parser._resolvers = self._resolvers
        parser.target = self.target
        parser._class_lookup  = self._class_lookup
        parser._default_encoding = self._default_encoding
        parser._schema = self._schema
        return parser

    def copy(self):
        u"""copy(self)

        Create a new parser with the same configuration.
        """
        return self._copy()

    def makeelement(self, _tag, attrib=None, nsmap=None, **_extra):
        u"""makeelement(self, _tag, attrib=None, nsmap=None, **_extra)

        Creates a new element associated with this parser.
        """
        return _makeElement(_tag, NULL, None, self, None, None,
                            attrib, nsmap, _extra)

    # internal parser methods

    cdef xmlDoc* _parseUnicodeDoc(self, utext, char* c_filename) except NULL:
        u"""Parse unicode document, share dictionary if possible.
        """
        cdef _ParserContext context
        cdef xmlDoc* result
        cdef xmlparser.xmlParserCtxt* pctxt
        cdef Py_ssize_t py_buffer_len
        cdef int buffer_len
        cdef char* c_text
        py_buffer_len = python.PyUnicode_GET_DATA_SIZE(utext)
        if py_buffer_len > limits.INT_MAX or _UNICODE_ENCODING is NULL:
            text_utf = python.PyUnicode_AsUTF8String(utext)
            py_buffer_len = python.PyBytes_GET_SIZE(text_utf)
            return self._parseDoc(_cstr(text_utf), py_buffer_len, c_filename)
        buffer_len = py_buffer_len

        context = self._getParserContext()
        context.prepare()
        try:
            pctxt = context._c_ctxt
            __GLOBAL_PARSER_CONTEXT.initParserDict(pctxt)

            c_text = python.PyUnicode_AS_DATA(utext)
            with nogil:
                if self._for_html:
                    result = htmlparser.htmlCtxtReadMemory(
                        pctxt, c_text, buffer_len, c_filename, _UNICODE_ENCODING,
                        self._parse_options)
                    if result is not NULL:
                        if _fixHtmlDictNames(pctxt.dict, result) < 0:
                            tree.xmlFreeDoc(result)
                            result = NULL
                else:
                    result = xmlparser.xmlCtxtReadMemory(
                        pctxt, c_text, buffer_len, c_filename, _UNICODE_ENCODING,
                        self._parse_options)

            return context._handleParseResultDoc(self, result, None)
        finally:
            context.cleanup()

    cdef xmlDoc* _parseDoc(self, char* c_text, Py_ssize_t c_len,
                           char* c_filename) except NULL:
        u"""Parse document, share dictionary if possible.
        """
        cdef _ParserContext context
        cdef xmlDoc* result
        cdef xmlparser.xmlParserCtxt* pctxt
        cdef char* c_encoding
        if c_len > limits.INT_MAX:
            raise ParserError, u"string is too long to parse it with libxml2"

        context = self._getParserContext()
        context.prepare()
        try:
            pctxt = context._c_ctxt
            __GLOBAL_PARSER_CONTEXT.initParserDict(pctxt)

            if self._default_encoding is None:
                c_encoding = NULL
            else:
                c_encoding = _cstr(self._default_encoding)

            with nogil:
                if self._for_html:
                    result = htmlparser.htmlCtxtReadMemory(
                        pctxt, c_text, c_len, c_filename,
                        c_encoding, self._parse_options)
                    if result is not NULL:
                        if _fixHtmlDictNames(pctxt.dict, result) < 0:
                            tree.xmlFreeDoc(result)
                            result = NULL
                else:
                    result = xmlparser.xmlCtxtReadMemory(
                        pctxt, c_text, c_len, c_filename,
                        c_encoding, self._parse_options)

            return context._handleParseResultDoc(self, result, None)
        finally:
            context.cleanup()

    cdef xmlDoc* _parseDocFromFile(self, char* c_filename) except NULL:
        cdef _ParserContext context
        cdef xmlDoc* result
        cdef xmlparser.xmlParserCtxt* pctxt
        cdef int orig_options
        cdef char* c_encoding
        result = NULL

        context = self._getParserContext()
        context.prepare()
        try:
            pctxt = context._c_ctxt
            __GLOBAL_PARSER_CONTEXT.initParserDict(pctxt)

            if self._default_encoding is None:
                c_encoding = NULL
            else:
                c_encoding = _cstr(self._default_encoding)

            orig_options = pctxt.options
            with nogil:
                if self._for_html:
                    result = htmlparser.htmlCtxtReadFile(
                        pctxt, c_filename, c_encoding, self._parse_options)
                    if result is not NULL:
                        if _fixHtmlDictNames(pctxt.dict, result) < 0:
                            tree.xmlFreeDoc(result)
                            result = NULL
                else:
                    result = xmlparser.xmlCtxtReadFile(
                        pctxt, c_filename, c_encoding, self._parse_options)
            pctxt.options = orig_options # work around libxml2 problem

            return context._handleParseResultDoc(self, result, c_filename)
        finally:
            context.cleanup()

    cdef xmlDoc* _parseDocFromFilelike(self, filelike, filename) except NULL:
        cdef _ParserContext context
        cdef _FileReaderContext file_context
        cdef xmlDoc* result
        cdef xmlparser.xmlParserCtxt* pctxt
        cdef char* c_filename
        if not filename:
            filename = None

        context = self._getParserContext()
        context.prepare()
        try:
            pctxt = context._c_ctxt
            __GLOBAL_PARSER_CONTEXT.initParserDict(pctxt)
            file_context = _FileReaderContext(
                filelike, context, filename, self._default_encoding)
            result = file_context._readDoc(pctxt, self._parse_options)

            return context._handleParseResultDoc(
                self, result, filename)
        finally:
            context.cleanup()

############################################################
## ET feed parser
############################################################

cdef class _FeedParser(_BaseParser):
    cdef bint _feed_parser_running

    property feed_error_log:
        u"""The error log of the last (or current) run of the feed parser.

        Note that this is local to the feed parser and thus is
        different from what the ``error_log`` property returns.
        """
        def __get__(self):
            cdef _ParserContext context
            context = self._getPushParserContext()
            return context._error_log.copy()

    def feed(self, data):
        u"""feed(self, data)

        Feeds data to the parser.  The argument should be an 8-bit string
        buffer containing encoded data, although Unicode is supported as long
        as both string types are not mixed.

        This is the main entry point to the consumer interface of a
        parser.  The parser will parse as much of the XML stream as it
        can on each call.  To finish parsing or to reset the parser,
        call the ``close()`` method.  Both methods may raise
        ParseError if errors occur in the input data.  If an error is
        raised, there is no longer a need to call ``close()``.

        The feed parser interface is independent of the normal parser
        usage.  You can use the same parser as a feed parser and in
        the ``parse()`` function concurrently.
        """
        cdef _ParserContext context
        cdef xmlparser.xmlParserCtxt* pctxt
        cdef Py_ssize_t py_buffer_len
        cdef char* c_data
        cdef char* c_encoding
        cdef int buffer_len
        cdef int error
        cdef bint recover = self._parse_options & xmlparser.XML_PARSE_RECOVER
        if python.PyBytes_Check(data):
            if self._default_encoding is None:
                c_encoding = NULL
            else:
                c_encoding = self._default_encoding
            c_data = _cstr(data)
            py_buffer_len = python.PyBytes_GET_SIZE(data)
        elif python.PyUnicode_Check(data):
            if _UNICODE_ENCODING is NULL:
                raise ParserError, \
                    u"Unicode parsing is not supported on this platform"
            c_encoding = _UNICODE_ENCODING
            c_data = python.PyUnicode_AS_DATA(data)
            py_buffer_len = python.PyUnicode_GET_DATA_SIZE(data)
        else:
            raise TypeError, u"Parsing requires string data"

        context = self._getPushParserContext()
        pctxt = context._c_ctxt
        error = 0
        if not self._feed_parser_running:
            context.prepare()
            self._feed_parser_running = 1
            __GLOBAL_PARSER_CONTEXT.initParserDict(pctxt)

            if py_buffer_len > limits.INT_MAX:
                buffer_len = limits.INT_MAX
            else:
                buffer_len = <int>py_buffer_len
            if self._for_html:
                error = _htmlCtxtResetPush(pctxt, c_data, buffer_len,
                                           c_encoding, self._parse_options)
            else:
                xmlparser.xmlCtxtUseOptions(pctxt, self._parse_options)
                error = xmlparser.xmlCtxtResetPush(
                    pctxt, c_data, buffer_len, NULL, c_encoding)
            py_buffer_len -= buffer_len
            c_data += buffer_len

        #print pctxt.charset, 'NONE' if c_encoding is NULL else c_encoding

        while py_buffer_len > 0 and (error == 0 or recover):
            with nogil:
                if py_buffer_len > limits.INT_MAX:
                    buffer_len = limits.INT_MAX
                else:
                    buffer_len = <int>py_buffer_len
                if self._for_html:
                    error = htmlparser.htmlParseChunk(pctxt, c_data, buffer_len, 0)
                else:
                    error = xmlparser.xmlParseChunk(pctxt, c_data, buffer_len, 0)
                py_buffer_len -= buffer_len
                c_data += buffer_len

            if error and not pctxt.replaceEntities and not pctxt.validate:
                # in this mode, we ignore errors about undefined entities
                for entry in context._error_log.filter_from_errors():
                    if entry.type != ErrorTypes.WAR_UNDECLARED_ENTITY and \
                           entry.type != ErrorTypes.ERR_UNDECLARED_ENTITY:
                        break
                else:
                    error = 0

        if not recover and (error or not pctxt.wellFormed):
            self._feed_parser_running = 0
            try:
                context._handleParseResult(self, NULL, None)
            finally:
                context.cleanup()

    def close(self):
        u"""close(self)

        Terminates feeding data to this parser.  This tells the parser to
        process any remaining data in the feed buffer, and then returns the
        root Element of the tree that was parsed.

        This method must be called after passing the last chunk of data into
        the ``feed()`` method.  It should only be called when using the feed
        parser interface, all other usage is undefined.
        """
        cdef _ParserContext context
        cdef xmlparser.xmlParserCtxt* pctxt
        cdef xmlDoc* c_doc
        cdef _Document doc
        if not self._feed_parser_running:
            raise XMLSyntaxError(u"no element found",
                                 xmlerror.XML_ERR_INTERNAL_ERROR, 0, 0)

        context = self._getPushParserContext()
        pctxt = context._c_ctxt

        self._feed_parser_running = 0
        if self._for_html:
            htmlparser.htmlParseChunk(pctxt, NULL, 0, 1)
        else:
            xmlparser.xmlParseChunk(pctxt, NULL, 0, 1)
        try:
            result = context._handleParseResult(self, pctxt.myDoc, None)
        finally:
            context.cleanup()

        if isinstance(result, _Document):
            return (<_Document>result).getroot()
        else:
            return result

cdef int _htmlCtxtResetPush(xmlparser.xmlParserCtxt* c_ctxt,
                             char* c_data, int buffer_len,
                             char* c_encoding, int parse_options) except -1:
    cdef xmlparser.xmlParserInput* c_input_stream
    # libxml2 crashes if spaceTab is not initialised
    if _LIBXML_VERSION_INT < 20629 and c_ctxt.spaceTab is NULL:
        c_ctxt.spaceTab = <int*>tree.xmlMalloc(10 * sizeof(int))
        c_ctxt.spaceMax = 10

    # libxml2 lacks an HTML push parser setup function
    error = xmlparser.xmlCtxtResetPush(c_ctxt, NULL, 0, NULL, c_encoding)
    if error:
        return error

    # fix libxml2 setup for HTML
    c_ctxt.progressive = 1
    c_ctxt.html = 1
    htmlparser.htmlCtxtUseOptions(c_ctxt, parse_options)

    if c_data is not NULL and buffer_len > 0:
        return htmlparser.htmlParseChunk(c_ctxt, c_data, buffer_len, 0)
    return 0

############################################################
## XML parser
############################################################

cdef int _XML_DEFAULT_PARSE_OPTIONS
_XML_DEFAULT_PARSE_OPTIONS = (
    xmlparser.XML_PARSE_NOENT   |
    xmlparser.XML_PARSE_NOCDATA |
    xmlparser.XML_PARSE_NONET   |
    xmlparser.XML_PARSE_COMPACT
    )

cdef class XMLParser(_FeedParser):
    u"""XMLParser(self, encoding=None, attribute_defaults=False, dtd_validation=False, load_dtd=False, no_network=True, ns_clean=False, recover=False, XMLSchema schema=None, remove_blank_text=False, resolve_entities=True, remove_comments=False, remove_pis=False, strip_cdata=True, target=None, compact=True)

    The XML parser.

    Parsers can be supplied as additional argument to various parse
    functions of the lxml API.  A default parser is always available
    and can be replaced by a call to the global function
    'set_default_parser'.  New parsers can be created at any time
    without a major run-time overhead.

    The keyword arguments in the constructor are mainly based on the
    libxml2 parser configuration.  A DTD will also be loaded if DTD
    validation or attribute default values are requested (unless you
    additionally provide an XMLSchema from which the default
    attributes can be read).

    Available boolean keyword arguments:

    - attribute_defaults - inject default attributes from DTD or XMLSchema
    - dtd_validation     - validate against a DTD referenced by the document
    - load_dtd           - use DTD for parsing
    - no_network         - prevent network access for related files (default: True)
    - ns_clean           - clean up redundant namespace declarations
    - recover            - try hard to parse through broken XML
    - remove_blank_text  - discard blank text nodes
    - remove_comments    - discard comments
    - remove_pis         - discard processing instructions
    - strip_cdata        - replace CDATA sections by normal text content (default: True)
    - compact            - safe memory for short text content (default: True)
    - resolve_entities   - replace entities by their text value (default: True)
    - huge_tree          - disable security restrictions and support very deep trees
                           and very long text content (only affects libxml2 2.7+)

    Other keyword arguments:

    - encoding - override the document encoding
    - target   - a parser target object that will receive the parse events
    - schema   - an XMLSchema to validate against

    Note that you should avoid sharing parsers between threads.  While this is
    not harmful, it is more efficient to use separate parsers.  This does not
    apply to the default parser.
    """
    def __init__(self, *, encoding=None, attribute_defaults=False,
                 dtd_validation=False, load_dtd=False, no_network=True,
                 ns_clean=False, recover=False, XMLSchema schema=None,
                 huge_tree=False, remove_blank_text=False, resolve_entities=True,
                 remove_comments=False, remove_pis=False, strip_cdata=True,
                 target=None, compact=True):
        cdef int parse_options
        parse_options = _XML_DEFAULT_PARSE_OPTIONS
        if load_dtd:
            parse_options = parse_options | xmlparser.XML_PARSE_DTDLOAD
        if dtd_validation:
            parse_options = parse_options | xmlparser.XML_PARSE_DTDVALID | \
                            xmlparser.XML_PARSE_DTDLOAD
        if attribute_defaults:
            parse_options = parse_options | xmlparser.XML_PARSE_DTDATTR
            if schema is None:
                parse_options = parse_options | xmlparser.XML_PARSE_DTDLOAD
        if ns_clean:
            parse_options = parse_options | xmlparser.XML_PARSE_NSCLEAN
        if recover:
            parse_options = parse_options | xmlparser.XML_PARSE_RECOVER
        if remove_blank_text:
            parse_options = parse_options | xmlparser.XML_PARSE_NOBLANKS
        if huge_tree:
            parse_options = parse_options | xmlparser.XML_PARSE_HUGE
        if not no_network:
            parse_options = parse_options ^ xmlparser.XML_PARSE_NONET
        if not compact:
            parse_options = parse_options ^ xmlparser.XML_PARSE_COMPACT
        if not resolve_entities:
            parse_options = parse_options ^ xmlparser.XML_PARSE_NOENT
        if not strip_cdata:
            parse_options = parse_options ^ xmlparser.XML_PARSE_NOCDATA

        _BaseParser.__init__(self, parse_options, 0, schema,
                             remove_comments, remove_pis, strip_cdata,
                             target, None, encoding)

cdef class ETCompatXMLParser(XMLParser):
    u"""ETCompatXMLParser(self, encoding=None, attribute_defaults=False, \
                 dtd_validation=False, load_dtd=False, no_network=True, \
                 ns_clean=False, recover=False, schema=None, \
                 huge_tree=False, remove_blank_text=False, resolve_entities=True, \
                 remove_comments=True, remove_pis=True, strip_cdata=True, \
                 target=None, compact=True)

    An XML parser with an ElementTree compatible default setup.

    See the XMLParser class for details.

    This parser has ``remove_comments`` and ``remove_pis`` enabled by default
    and thus ignores comments and processing instructions.
    """
    def __init__(self, *, encoding=None, attribute_defaults=False,
                 dtd_validation=False, load_dtd=False, no_network=True,
                 ns_clean=False, recover=False, schema=None,
                 huge_tree=False, remove_blank_text=False, resolve_entities=True,
                 remove_comments=True, remove_pis=True, strip_cdata=True,
                 target=None, compact=True):
        XMLParser.__init__(self,
                           attribute_defaults=attribute_defaults,
                           dtd_validation=dtd_validation,
                           load_dtd=load_dtd,
                           no_network=no_network,
                           ns_clean=ns_clean,
                           recover=recover,
                           remove_blank_text=remove_blank_text,
                           huge_tree=huge_tree,
                           compact=compact,
                           resolve_entities=resolve_entities,
                           remove_comments=remove_comments,
                           remove_pis=remove_pis,
                           strip_cdata=strip_cdata,
                           target=target,
                           encoding=encoding,
                           schema=schema)

# ET 1.2 compatible name
XMLTreeBuilder = ETCompatXMLParser


cdef XMLParser __DEFAULT_XML_PARSER
__DEFAULT_XML_PARSER = XMLParser()

__GLOBAL_PARSER_CONTEXT.setDefaultParser(__DEFAULT_XML_PARSER)

def set_default_parser(_BaseParser parser=None):
    u"""set_default_parser(parser=None)

    Set a default parser for the current thread.  This parser is used
    globally whenever no parser is supplied to the various parse functions of
    the lxml API.  If this function is called without a parser (or if it is
    None), the default parser is reset to the original configuration.

    Note that the pre-installed default parser is not thread-safe.  Avoid the
    default parser in multi-threaded environments.  You can create a separate
    parser for each thread explicitly or use a parser pool.
    """
    if parser is None:
        parser = __DEFAULT_XML_PARSER
    __GLOBAL_PARSER_CONTEXT.setDefaultParser(parser)

def get_default_parser():
    u"get_default_parser()"
    return __GLOBAL_PARSER_CONTEXT.getDefaultParser()

############################################################
## HTML parser
############################################################

cdef int _HTML_DEFAULT_PARSE_OPTIONS
_HTML_DEFAULT_PARSE_OPTIONS = (
    htmlparser.HTML_PARSE_RECOVER |
    htmlparser.HTML_PARSE_NONET   |
    htmlparser.HTML_PARSE_COMPACT
    )

cdef class HTMLParser(_FeedParser):
    u"""HTMLParser(self, encoding=None, remove_blank_text=False, \
                   remove_comments=False, remove_pis=False, strip_cdata=True, \
                   no_network=True, target=None, XMLSchema schema=None, \
                   recover=True, compact=True)

    The HTML parser.

    This parser allows reading HTML into a normal XML tree.  By
    default, it can read broken (non well-formed) HTML, depending on
    the capabilities of libxml2.  Use the 'recover' option to switch
    this off.

    Available boolean keyword arguments:

    - recover            - try hard to parse through broken HTML (default: True)
    - no_network         - prevent network access for related files (default: True)
    - remove_blank_text  - discard empty text nodes
    - remove_comments    - discard comments
    - remove_pis         - discard processing instructions
    - strip_cdata        - replace CDATA sections by normal text content (default: True)
    - compact            - safe memory for short text content (default: True)

    Other keyword arguments:

    - encoding - override the document encoding
    - target   - a parser target object that will receive the parse events
    - schema   - an XMLSchema to validate against

    Note that you should avoid sharing parsers between threads for performance
    reasons.
    """
    def __init__(self, *, encoding=None, remove_blank_text=False,
                 remove_comments=False, remove_pis=False, strip_cdata=True,
                 no_network=True, target=None, XMLSchema schema=None,
                 recover=True, compact=True):
        cdef int parse_options
        parse_options = _HTML_DEFAULT_PARSE_OPTIONS
        if remove_blank_text:
            parse_options = parse_options | htmlparser.HTML_PARSE_NOBLANKS
        if not recover:
            parse_options = parse_options ^ htmlparser.HTML_PARSE_RECOVER
        if not no_network:
            parse_options = parse_options ^ htmlparser.HTML_PARSE_NONET
        if not compact:
            parse_options = parse_options ^ htmlparser.HTML_PARSE_COMPACT

        _BaseParser.__init__(self, parse_options, 1, schema,
                             remove_comments, remove_pis, strip_cdata,
                             target, None, encoding)

cdef HTMLParser __DEFAULT_HTML_PARSER
__DEFAULT_HTML_PARSER = HTMLParser()

############################################################
## helper functions for document creation
############################################################

cdef xmlDoc* _parseDoc(text, filename, _BaseParser parser) except NULL:
    cdef char* c_filename
    cdef char* c_text
    cdef Py_ssize_t c_len
    if parser is None:
        parser = __GLOBAL_PARSER_CONTEXT.getDefaultParser()
    if not filename:
        c_filename = NULL
    else:
        filename_utf = _encodeFilenameUTF8(filename)
        c_filename = _cstr(filename_utf)
    if python.PyUnicode_Check(text):
        c_len = python.PyUnicode_GET_DATA_SIZE(text)
        if c_len > limits.INT_MAX:
            return (<_BaseParser>parser)._parseDocFromFilelike(
                StringIO(text), filename)
        return (<_BaseParser>parser)._parseUnicodeDoc(text, c_filename)
    else:
        c_len = python.PyBytes_GET_SIZE(text)
        if c_len > limits.INT_MAX:
            return (<_BaseParser>parser)._parseDocFromFilelike(
                BytesIO(text), filename)
        c_text = _cstr(text)
        return (<_BaseParser>parser)._parseDoc(c_text, c_len, c_filename)

cdef xmlDoc* _parseDocFromFile(filename8, _BaseParser parser) except NULL:
    if parser is None:
        parser = __GLOBAL_PARSER_CONTEXT.getDefaultParser()
    return (<_BaseParser>parser)._parseDocFromFile(_cstr(filename8))

cdef xmlDoc* _parseDocFromFilelike(source, filename,
                                   _BaseParser parser) except NULL:
    if parser is None:
        parser = __GLOBAL_PARSER_CONTEXT.getDefaultParser()
    return (<_BaseParser>parser)._parseDocFromFilelike(source, filename)

cdef xmlDoc* _newXMLDoc() except NULL:
    cdef xmlDoc* result
    result = tree.xmlNewDoc(NULL)
    if result is NULL:
        python.PyErr_NoMemory()
    if result.encoding is NULL:
        result.encoding = tree.xmlStrdup("UTF-8")
    __GLOBAL_PARSER_CONTEXT.initDocDict(result)
    return result

cdef xmlDoc* _newHTMLDoc() except NULL:
    cdef xmlDoc* result
    result = tree.htmlNewDoc(NULL, NULL)
    if result is NULL:
        python.PyErr_NoMemory()
    __GLOBAL_PARSER_CONTEXT.initDocDict(result)
    return result

cdef xmlDoc* _copyDoc(xmlDoc* c_doc, int recursive) except NULL:
    cdef xmlDoc* result
    if recursive:
        with nogil:
            result = tree.xmlCopyDoc(c_doc, recursive)
    else:
        result = tree.xmlCopyDoc(c_doc, 0)
    if result is NULL:
        python.PyErr_NoMemory()
    __GLOBAL_PARSER_CONTEXT.initDocDict(result)
    return result

cdef xmlDoc* _copyDocRoot(xmlDoc* c_doc, xmlNode* c_new_root) except NULL:
    u"Recursively copy the document and make c_new_root the new root node."
    cdef xmlDoc* result
    cdef xmlNode* c_node
    result = tree.xmlCopyDoc(c_doc, 0) # non recursive
    __GLOBAL_PARSER_CONTEXT.initDocDict(result)
    with nogil:
        c_node = tree.xmlDocCopyNode(c_new_root, result, 1) # recursive
    if c_node is NULL:
        python.PyErr_NoMemory()
    tree.xmlDocSetRootElement(result, c_node)
    _copyTail(c_new_root.next, c_node)
    return result

cdef xmlNode* _copyNodeToDoc(xmlNode* c_node, xmlDoc* c_doc) except NULL:
    u"Recursively copy the element into the document. c_doc is not modified."
    cdef xmlNode* c_root
    c_root = tree.xmlDocCopyNode(c_node, c_doc, 1) # recursive
    if c_root is NULL:
        python.PyErr_NoMemory()
    _copyTail(c_node.next, c_root)
    return c_root


############################################################
## API level helper functions for _Document creation
## (here we convert to UTF-8)
############################################################

cdef _Document _parseDocument(source, _BaseParser parser, base_url):
    cdef _Document doc
    if _isString(source):
        # parse the file directly from the filesystem
        doc = _parseDocumentFromURL(_encodeFilename(source), parser)
        # fix base URL if requested
        if base_url is not None:
            base_url = _encodeFilenameUTF8(base_url)
            if doc._c_doc.URL is not NULL:
                tree.xmlFree(doc._c_doc.URL)
            doc._c_doc.URL = tree.xmlStrdup(_cstr(base_url))
        return doc

    if base_url is not None:
        url = base_url
    else:
        url = _getFilenameForFile(source)

    if hasattr(source, u'getvalue') and hasattr(source, u'tell'):
        # StringIO - reading from start?
        if source.tell() == 0:
            return _parseMemoryDocument(
                source.getvalue(), _encodeFilenameUTF8(url), parser)

    # Support for file-like objects (urlgrabber.urlopen, ...)
    if hasattr(source, u'read'):
        return _parseFilelikeDocument(
            source, _encodeFilenameUTF8(url), parser)

    raise TypeError, u"cannot parse from '%s'" % funicode(python._fqtypename(source))

cdef _Document _parseDocumentFromURL(url, _BaseParser parser):
    cdef xmlDoc* c_doc
    c_doc = _parseDocFromFile(url, parser)
    return _documentFactory(c_doc, parser)

cdef _Document _parseMemoryDocument(text, url, _BaseParser parser):
    cdef xmlDoc* c_doc
    if python.PyUnicode_Check(text):
        if _hasEncodingDeclaration(text):
            raise ValueError, \
                u"Unicode strings with encoding declaration are not supported."
        # pass native unicode only if libxml2 can handle it
        if _UNICODE_ENCODING is NULL:
            text = python.PyUnicode_AsUTF8String(text)
    elif not python.PyBytes_Check(text):
        raise ValueError, u"can only parse strings"
    if python.PyUnicode_Check(url):
        url = python.PyUnicode_AsUTF8String(url)
    c_doc = _parseDoc(text, url, parser)
    return _documentFactory(c_doc, parser)

cdef _Document _parseFilelikeDocument(source, url, _BaseParser parser):
    cdef xmlDoc* c_doc
    if python.PyUnicode_Check(url):
        url = python.PyUnicode_AsUTF8String(url)
    c_doc = _parseDocFromFilelike(source, url, parser)
    return _documentFactory(c_doc, parser)
