# Parsers for XML and HTML

cimport xmlparser
cimport htmlparser

class ParseError(LxmlSyntaxError):
    """Syntax error while parsing an XML document.

    For compatibility with ElementTree 1.3 and later.
    """
    pass

class XMLSyntaxError(ParseError):
    """Syntax error while parsing an XML document.
    """
    def __init__(self, message, code, line, column):
        ParseError.__init__(self, message)        
        self.position = (line, column)
        self.code = code

class ParserError(LxmlError):
    """Internal lxml parser error.
    """
    pass

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
    def __dealloc__(self):
        if self._c_dict is not NULL:
            xmlparser.xmlDictFree(self._c_dict)

    cdef void initMainParserContext(self):
        """Put the global context into the thread dictionary of the main
        thread.  To be called once and only in the main thread."""
        cdef python.PyObject* thread_dict
        cdef python.PyObject* result
        thread_dict = python.PyThreadState_GetDict()
        if thread_dict is not NULL:
            python.PyDict_SetItem(<object>thread_dict, "_ParserDictionaryContext", self)

    cdef _ParserDictionaryContext _findThreadParserContext(self):
        "Find (or create) the _ParserDictionaryContext object for the current thread"
        cdef python.PyObject* thread_dict
        cdef python.PyObject* result
        cdef _ParserDictionaryContext context
        thread_dict = python.PyThreadState_GetDict()
        if thread_dict is NULL:
            return self
        d = <object>thread_dict
        result = python.PyDict_GetItem(d, "_ParserDictionaryContext")
        if result is not NULL:
            return <object>result
        context = _ParserDictionaryContext()
        python.PyDict_SetItem(d, "_ParserDictionaryContext", context)
        return context

    cdef void setDefaultParser(self, _BaseParser parser):
        "Set the default parser for the current thread"
        cdef _ParserDictionaryContext context
        context = self._findThreadParserContext()
        context._default_parser = parser

    cdef _BaseParser getDefaultParser(self):
        "Return (or create) the default parser of the current thread"
        cdef _ParserDictionaryContext context
        context = self._findThreadParserContext()
        if context._default_parser is None:
            if self._default_parser is None:
                self._default_parser = __DEFAULT_XML_PARSER._copy()
            if context is not self:
                context._default_parser = self._default_parser._copy()
        return context._default_parser

    cdef tree.xmlDict* _getThreadDict(self, tree.xmlDict* default):
        "Return the thread-local dict or create a new one if necessary."
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
        "Assure we always use the same string dictionary."
        self.initThreadDictRef(&pctxt.dict)

    cdef void initXPathParserDict(self, xpath.xmlXPathContext* pctxt):
        "Assure we always use the same string dictionary."
        self.initThreadDictRef(&pctxt.dict)

    cdef void initDocDict(self, xmlDoc* result):
        "Store dict of last object parsed if no shared dict yet"
        # XXX We also free the result dict here if there already was one.
        # This case should only occur for new documents with empty dicts,
        # otherwise we'd free data that's in use => segfault
        self.initThreadDictRef(&result.dict)

cdef _ParserDictionaryContext __GLOBAL_PARSER_CONTEXT
__GLOBAL_PARSER_CONTEXT = _ParserDictionaryContext()
__GLOBAL_PARSER_CONTEXT.initMainParserContext()

cdef int _checkThreadDict(tree.xmlDict* c_dict):
    """Check that c_dict is either the local thread dictionary or the global
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
cdef char* _UNICODE_ENCODING
_UNICODE_ENCODING = NULL

cdef void _setupPythonUnicode():
    """Sets _UNICODE_ENCODING to the internal encoding name of Python unicode
    strings if libxml2 supports reading native Python unicode.  This depends
    on iconv and the local Python installation, so we simply check if we find
    a matching encoding handler.
    """
    cdef tree.xmlCharEncodingHandler* enchandler
    cdef Py_ssize_t l
    cdef char* buffer
    cdef char* enc
    utext = python.PyUnicode_DecodeUTF8("<test/>", 7, 'strict')
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
            return
    enchandler = tree.xmlFindCharEncodingHandler(enc)
    if enchandler is not NULL:
        global _UNICODE_ENCODING
        tree.xmlCharEncCloseFunc(enchandler)
        _UNICODE_ENCODING = enc

cdef char* _findEncodingName(char* buffer, int size):
    "Work around bug in libxml2: find iconv name of encoding on our own."
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
        return tree.xmlGetCharEncodingName(enc)

_setupPythonUnicode()

############################################################
## support for file-like objects
############################################################

cdef class _FileReaderContext:
    cdef object _filelike
    cdef object _encoding
    cdef object _url
    cdef object _bytes
    cdef _ExceptionContext _exc_context
    cdef cstd.size_t _bytes_read
    cdef char* _c_url
    def __init__(self, filelike, exc_context, url, encoding):
        self._exc_context = exc_context
        self._filelike = filelike
        self._encoding = encoding
        self._url = url
        if url is None:
            self._c_url = NULL
        else:
            self._c_url = _cstr(url)
        self._bytes  = ''
        self._bytes_read = 0

    cdef xmlparser.xmlParserInput* _createParserInput(
            self, xmlparser.xmlParserCtxt* ctxt):
        cdef xmlparser.xmlParserInputBuffer* c_buffer
        c_buffer = xmlparser.xmlAllocParserInputBuffer(0)
        c_buffer.context = <python.PyObject*>self
        c_buffer.readcallback = _readFilelikeParser
        return xmlparser.xmlNewIOInputStream(ctxt, c_buffer, 0)

    cdef xmlDoc* _readDoc(self, xmlparser.xmlParserCtxt* ctxt, int options):
        cdef xmlDoc* result
        cdef char* c_encoding

        if self._encoding is None:
            c_encoding = NULL
        else:
            c_encoding = _cstr(self._encoding)

        with nogil:
            if ctxt.html:
                result = htmlparser.htmlCtxtReadIO(
                    ctxt, _readFilelikeParser, NULL, <python.PyObject*>self,
                    self._c_url, c_encoding, options)
            else:
                result = xmlparser.xmlCtxtReadIO(
                    ctxt, _readFilelikeParser, NULL, <python.PyObject*>self,
                    self._c_url, c_encoding, options)
        return result

    cdef tree.xmlDtd* _readDtd(self):
        cdef xmlparser.xmlParserInputBuffer* c_buffer
        c_buffer = xmlparser.xmlAllocParserInputBuffer(0)
        c_buffer.context = <python.PyObject*>self
        c_buffer.readcallback = _readFilelikeParser
        with nogil:
            return xmlparser.xmlIOParseDTD(NULL, c_buffer, 0)

    cdef int copyToBuffer(self, char* c_buffer, int c_size):
        cdef char* c_start
        cdef Py_ssize_t byte_count, remaining
        if self._bytes_read < 0:
            return 0
        try:
            byte_count = python.PyString_GET_SIZE(self._bytes)
            remaining = byte_count - self._bytes_read
            if remaining <= 0:
                self._bytes = self._filelike.read(c_size)
                if not python.PyString_Check(self._bytes):
                    raise TypeError(
                        "reading file objects must return plain strings")
                remaining = python.PyString_GET_SIZE(self._bytes)
                self._bytes_read = 0
                if remaining == 0:
                    self._bytes_read = -1
                    return 0
            if c_size > remaining:
                c_size = remaining
            c_start = _cstr(self._bytes) + self._bytes_read
            self._bytes_read = self._bytes_read + c_size
            cstd.memcpy(c_buffer, c_start, c_size)
            return c_size
        except:
            self._exc_context._store_raised()
            return -1

cdef int _readFilelikeParser(void* ctxt, char* c_buffer, int c_size) with gil:
    return (<_FileReaderContext>ctxt).copyToBuffer(c_buffer, c_size)

############################################################
## support for custom document loaders
############################################################

cdef  xmlparser.xmlParserInput* _parser_resolve_from_python(
    char* c_url, char* c_pubid, xmlparser.xmlParserCtxt* c_context,
    int* error) with gil:
    # call the Python document loaders
    cdef xmlparser.xmlParserInput* c_input
    cdef _ResolverContext context
    cdef _InputDocument   doc_ref
    cdef _FileReaderContext file_context
    error[0] = 0
    context = <_ResolverContext>c_context._private
    try:
        if c_url is NULL:
            url = None
        elif c_context.myDoc is NULL or c_context.myDoc.URL is NULL:
            # parsing a main document, so URL was passed verbatimly by user
            url = c_url
        else:
            # parsing a related document (DTD etc.) => UTF-8 encoded URL
            url = funicode(c_url)
        if c_pubid is NULL:
            pubid = None
        else:
            pubid = funicode(c_pubid) # always UTF-8

        doc_ref = context._resolvers.resolve(url, pubid, context)
        if doc_ref is None:
            return NULL
    except:
        context._store_raised()
        error[0] = 1
        return NULL

    c_input = NULL
    data = None
    if doc_ref._type == PARSER_DATA_STRING:
        data = doc_ref._data_bytes
        c_input = xmlparser.xmlNewStringInputStream(
            c_context, _cstr(data))
    elif doc_ref._type == PARSER_DATA_FILENAME:
        c_input = xmlparser.xmlNewInputFromFile(
            c_context, _cstr(doc_ref._data_bytes))
    elif doc_ref._type == PARSER_DATA_FILE:
        file_context = _FileReaderContext(doc_ref._file, context, url)
        c_input = file_context._createParserInput(c_context)
        data = file_context

    if data is not None:
        context._storage.add(data)
    return c_input

cdef xmlparser.xmlParserInput* _local_resolver(char* c_url, char* c_pubid,
                                               xmlparser.xmlParserCtxt* c_context):
    # no Python objects here, may be called without thread context !
    # when we declare a Python object, Pyrex will INCREF(None) !
    cdef xmlparser.xmlParserInput* c_input
    cdef int error
    if c_context._private is NULL:
        if __DEFAULT_ENTITY_LOADER is NULL:
            return NULL
        return __DEFAULT_ENTITY_LOADER(c_url, c_pubid, c_context)

    c_input = _parser_resolve_from_python(c_url, c_pubid, c_context, &error)

    if c_input is not NULL:
        return c_input
    if error:
        return NULL
    if __DEFAULT_ENTITY_LOADER is NULL:
        return NULL
    return __DEFAULT_ENTITY_LOADER(c_url, c_pubid, c_context)

cdef xmlparser.xmlExternalEntityLoader __DEFAULT_ENTITY_LOADER
__DEFAULT_ENTITY_LOADER = xmlparser.xmlGetExternalEntityLoader()

xmlparser.xmlSetExternalEntityLoader(_local_resolver)

############################################################
## Parsers
############################################################

cdef class _ParserContext(_ResolverContext)
cdef class _SaxParserContext(_ParserContext)
cdef class _TargetParserContext(_SaxParserContext)
cdef class _ParserSchemaValidationContext
cdef class _Validator
cdef class XMLSchema(_Validator)

cdef class _ParserContext(_ResolverContext):
    cdef _ErrorLog _error_log
    cdef _ParserSchemaValidationContext _validator
    cdef xmlparser.xmlParserCtxt* _c_ctxt
    cdef python.PyThread_type_lock _lock

    def __dealloc__(self):
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
                raise ParserError("parser locking failed")
        self._error_log.connect()
        if self._validator is not None:
            self._validator.connect(self._c_ctxt)
        return 0

    cdef int cleanup(self) except -1:
        self._resetParserContext()
        self.clear()
        if self._validator is not None:
            self._validator.disconnect()
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
    if not config.ENABLE_THREADING:
        context._lock = NULL
    else:
        context._lock = python.PyThread_allocate_lock()
    if c_ctxt is not NULL:
        context._initParserContext(c_ctxt)
    context._error_log = _ErrorLog()

cdef int _raiseParseError(xmlparser.xmlParserCtxt* ctxt, filename,
                          _ErrorLog error_log) except 0:
    if filename is not None and \
           ctxt.lastError.domain == xmlerror.XML_FROM_IO:
        if ctxt.lastError.message is not NULL:
            message = "Error reading file '%s': %s" % (
                filename, (ctxt.lastError.message).strip())
        else:
            message = "Error reading '%s'" % filename
        raise IOError(message)
    elif error_log:
        raise error_log._buildParseException(
            XMLSyntaxError, "Document is not well formed")
    elif ctxt.lastError.message is not NULL:
        message = (ctxt.lastError.message).strip()
        code = ctxt.lastError.code
        line = ctxt.lastError.line
        column = ctxt.lastError.int2
        if ctxt.lastError.line > 0:
            message = "line %d: %s" % (line, message)
        raise XMLSyntaxError(message, code, line, column)
    else:
        raise XMLSyntaxError(None, xmlerror.XML_ERR_INTERNAL_ERROR, 0, 0)

cdef xmlDoc* _handleParseResult(_ParserContext context,
                                xmlparser.xmlParserCtxt* c_ctxt,
                                xmlDoc* result, filename,
                                bint recover) except NULL:
    cdef bint well_formed
    if c_ctxt.myDoc is not NULL:
        if c_ctxt.myDoc != result:
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

        if well_formed:
            __GLOBAL_PARSER_CONTEXT.initDocDict(result)
        else:
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
    elif result.URL is NULL and filename is not None:
        result.URL = tree.xmlStrdup(_cstr(filename))
    return result


cdef class _BaseParser:
    cdef ElementClassLookup _class_lookup
    cdef _ResolverRegistry _resolvers
    cdef _ParserContext _parser_context
    cdef _ParserContext _push_parser_context
    cdef int _parse_options
    cdef bint _for_html
    cdef bint _remove_comments
    cdef bint _remove_pis
    cdef XMLSchema _schema
    cdef object _filename
    cdef object _target
    cdef object _default_encoding
    cdef int _default_encoding_int

    def __init__(self, int parse_options, bint for_html, XMLSchema schema,
                 remove_comments, remove_pis, target, filename, encoding):
        cdef int c_encoding
        if not isinstance(self, HTMLParser) and \
                not isinstance(self, XMLParser) and \
                not isinstance(self, iterparse):
            raise TypeError("This class cannot be instantiated")

        self._parse_options = parse_options
        self._filename = filename
        self._target = target
        self._for_html = for_html
        self._remove_comments = remove_comments
        self._remove_pis = remove_pis
        self._schema = schema

        self._resolvers = _ResolverRegistry()

        if encoding is None:
            self._default_encoding = None
            self._default_encoding_int = tree.XML_CHAR_ENCODING_NONE
        else:
            encoding = _utf8(encoding)
            c_encoding = tree.xmlParseCharEncoding(_cstr(encoding))
            if c_encoding == tree.XML_CHAR_ENCODING_ERROR or \
                   c_encoding == tree.XML_CHAR_ENCODING_NONE:
                raise LookupError("unknown encoding: '%s'" % encoding)
            self._default_encoding = encoding
            self._default_encoding_int = c_encoding

    cdef _ParserContext _getParserContext(self):
        cdef xmlparser.xmlParserCtxt* pctxt
        if self._parser_context is None:
            self._parser_context = self._createContext(self._target)
            if self._schema is not None:
                self._parser_context._validator = \
                    self._schema._newSaxValidator()
            pctxt = self._newParserCtxt()
            if pctxt is NULL:
                python.PyErr_NoMemory()
            _initParserContext(self._parser_context, self._resolvers, pctxt)
            if self._remove_comments:
                pctxt.sax.comment = NULL
            if self._remove_pis:
                pctxt.sax.processingInstruction = NULL
            # hard switch-off for CDATA nodes => makes them plain text
            pctxt.sax.cdataBlock = NULL
        return self._parser_context

    cdef _ParserContext _getPushParserContext(self):
        cdef xmlparser.xmlParserCtxt* pctxt
        if self._push_parser_context is None:
            self._push_parser_context = self._createContext(self._target)
            if self._schema is not None:
                self._push_parser_context._validator = \
                    self._schema._newSaxValidator()
            pctxt = self._newPushParserCtxt()
            if pctxt is NULL:
                python.PyErr_NoMemory()
            _initParserContext(
                self._push_parser_context, self._resolvers, pctxt)
            if self._remove_comments:
                pctxt.sax.comment = NULL
            if self._remove_pis:
                pctxt.sax.processingInstruction = NULL
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
                NULL, NULL, NULL, 0, c_filename, self._default_encoding_int)
            if c_ctxt is not NULL:
                htmlparser.htmlCtxtUseOptions(c_ctxt, self._parse_options)
        else:
            c_ctxt = xmlparser.xmlCreatePushParserCtxt(
                NULL, NULL, NULL, 0, c_filename)
            if c_ctxt is not NULL:
                xmlparser.xmlCtxtUseOptions(c_ctxt, self._parse_options)
                if self._default_encoding_int != tree.XML_CHAR_ENCODING_NONE:
                    xmlparser.xmlSwitchEncoding(
                        c_ctxt, self._default_encoding_int)
        return c_ctxt

    property error_log:
        """The error log of the last parser run.
        """
        def __get__(self):
            cdef _ParserContext context
            context = self._getParserContext()
            return context._error_log.copy()

    property resolvers:
        "The custom resolver registry of this parser."
        def __get__(self):
            return self._resolvers

    property version:
        "The version of the underlying XML parser."
        def __get__(self):
            return "libxml2 %d.%d.%d" % LIBXML_VERSION

    def setElementClassLookup(self, ElementClassLookup lookup = None):
        "@deprecated: use ``parser.set_element_class_lookup(lookup)`` instead."
        self.set_element_class_lookup(lookup)

    def set_element_class_lookup(self, ElementClassLookup lookup = None):
        """set_element_class_lookup(self, lookup = None)

        Set a lookup scheme for element classes generated from this parser.

        Reset it by passing None or nothing.
        """
        self._class_lookup = lookup

    cdef _BaseParser _copy(self):
        "Create a new parser with the same configuration."
        cdef _BaseParser parser
        parser = self.__class__()
        parser._parse_options = self._parse_options
        parser._for_html = self._for_html
        parser._remove_comments = self._remove_comments
        parser._remove_pis = self._remove_pis
        parser._filename = self._filename
        parser._resolvers = self._resolvers
        parser._target = self._target
        parser._class_lookup  = self._class_lookup
        return parser

    def copy(self):
        """copy(self)

        Create a new parser with the same configuration.
        """
        return self._copy()

    def makeelement(self, _tag, attrib=None, nsmap=None, **_extra):
        """makeelement(self, _tag, attrib=None, nsmap=None, **_extra)

        Creates a new element associated with this parser.
        """
        return _makeElement(_tag, NULL, None, self, None, None,
                            attrib, nsmap, _extra)

    # internal parser methods

    cdef xmlDoc* _parseUnicodeDoc(self, utext, char* c_filename) except NULL:
        """Parse unicode document, share dictionary if possible.
        """
        cdef _ParserContext context
        cdef xmlDoc* result
        cdef xmlparser.xmlParserCtxt* pctxt
        cdef Py_ssize_t py_buffer_len
        cdef int buffer_len
        cdef char* c_text
        py_buffer_len = python.PyUnicode_GET_DATA_SIZE(utext)
        if py_buffer_len > python.INT_MAX or _UNICODE_ENCODING is NULL:
            text_utf = python.PyUnicode_AsUTF8String(utext)
            py_buffer_len = python.PyString_GET_SIZE(text_utf)
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
                else:
                    result = xmlparser.xmlCtxtReadMemory(
                        pctxt, c_text, buffer_len, c_filename, _UNICODE_ENCODING,
                        self._parse_options)

            return context._handleParseResultDoc(self, result, None)
        finally:
            context.cleanup()

    cdef xmlDoc* _parseDoc(self, char* c_text, Py_ssize_t c_len,
                           char* c_filename) except NULL:
        """Parse document, share dictionary if possible.
        """
        cdef _ParserContext context
        cdef xmlDoc* result
        cdef xmlparser.xmlParserCtxt* pctxt
        cdef char* c_encoding
        if c_len > python.INT_MAX:
            raise ParserError("string is too long to parse it with libxml2")

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
        """The error log of the last (or current) run of the feed parser.

        Note that this is local to the feed parser and thus is
        different from what the ``error_log`` property returns.
        """
        def __get__(self):
            cdef _ParserContext context
            context = self._getPushParserContext()
            return context._error_log.copy()

    def feed(self, data):
        """feed(self, data)

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
        if python.PyString_Check(data):
            if self._default_encoding is None:
                c_encoding = NULL
            else:
                c_encoding = self._default_encoding
            c_data = _cstr(data)
            py_buffer_len = python.PyString_GET_SIZE(data)
        elif python.PyUnicode_Check(data):
            if _UNICODE_ENCODING is NULL:
                raise ParserError(
                    "Unicode parsing is not supported on this platform")
            c_encoding = _UNICODE_ENCODING
            c_data = python.PyUnicode_AS_DATA(data)
            py_buffer_len = python.PyUnicode_GET_DATA_SIZE(data)
        else:
            raise TypeError("Parsing requires string data")

        context = self._getPushParserContext()
        pctxt = context._c_ctxt
        error = 0
        if not self._feed_parser_running:
            context.prepare()
            self._feed_parser_running = 1
            __GLOBAL_PARSER_CONTEXT.initParserDict(pctxt)

            if py_buffer_len > python.INT_MAX:
                buffer_len = python.INT_MAX
            else:
                buffer_len = <int>py_buffer_len
            if self._for_html:
                error = _htmlCtxtResetPush(pctxt, c_data, buffer_len,
                                           c_encoding, self._parse_options)
            else:
                xmlparser.xmlCtxtUseOptions(pctxt, self._parse_options)
                error = xmlparser.xmlCtxtResetPush(
                    pctxt, c_data, buffer_len, NULL, c_encoding)
            py_buffer_len = py_buffer_len - buffer_len
            c_data = c_data + buffer_len

        while error == 0 and py_buffer_len > 0:
            if py_buffer_len > python.INT_MAX:
                buffer_len = python.INT_MAX
            else:
                buffer_len = <int>py_buffer_len
            if self._for_html:
                error = htmlparser.htmlParseChunk(pctxt, c_data, buffer_len, 0)
            else:
                error = xmlparser.xmlParseChunk(pctxt, c_data, buffer_len, 0)
            py_buffer_len = py_buffer_len - buffer_len
            c_data = c_data + buffer_len

        if error:
            self._feed_parser_running = 0
            try:
                context._handleParseResult(self, NULL, None)
            finally:
                context.cleanup()

    def close(self):
        """close(self)

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
            raise XMLSyntaxError("no element found",
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
## SAX event handler
############################################################

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
    """This class maps SAX2 events to method calls.
    """
    cdef _SaxParserTarget _target
    cdef xmlparser.startElementNsSAX2Func _origSaxStart
    cdef xmlparser.endElementNsSAX2Func   _origSaxEnd
    cdef xmlparser.startElementSAXFunc    _origSaxStartNoNs
    cdef xmlparser.endElementSAXFunc      _origSaxEndNoNs
    cdef xmlparser.charactersSAXFunc      _origSaxData
    cdef xmlparser.internalSubsetSAXFunc  _origSaxDoctype
    cdef xmlparser.commentSAXFunc         _origSaxComment
    cdef xmlparser.processingInstructionSAXFunc    _origSaxPi

    cdef void _setSaxParserTarget(self, _SaxParserTarget target):
        self._target = target

    cdef void _initParserContext(self, xmlparser.xmlParserCtxt* c_ctxt):
        "wrap original SAX2 callbacks"
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
        else:
            self._origSaxData = sax.characters = NULL
        if self._target._sax_event_filter & SAX_EVENT_DATA:
            sax.characters = _handleSaxData

        if self._target._sax_event_propagate & SAX_EVENT_DOCTYPE:
            self._origSaxDoctype = sax.internalSubset
        else:
            self._origSaxDoctype = sax.internalSubset = NULL
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

    cdef void _handleSaxException(self, xmlparser.xmlParserCtxt* c_ctxt):
        self._store_raised()
        if c_ctxt.errNo == xmlerror.XML_ERR_OK:
            c_ctxt.errNo = xmlerror.XML_ERR_INTERNAL_ERROR
        c_ctxt.disableSAX = 1

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
                    value = ""
                else:
                    value = python.PyUnicode_DecodeUTF8(
                        c_attributes[3], c_attributes[4] - c_attributes[3],
                        "strict")
                python.PyDict_SetItem(attrib, name, value)
                c_attributes = c_attributes + 5
        if c_nb_namespaces == 0:
            nsmap = EMPTY_READ_ONLY_DICT
        else:
            nsmap = {}
            for i from 0 <= i < c_nb_namespaces:
                if c_namespaces[0] is NULL:
                    prefix = None
                else:
                    prefix = funicode(c_namespaces[0])
                python.PyDict_SetItem(
                    nsmap, prefix, funicode(c_namespaces[1]))
                c_namespaces = c_namespaces + 2
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
                    value = ""
                else:
                    value = funicode(c_attributes[1])
                c_attributes = c_attributes + 2
                python.PyDict_SetItem(attrib, name, value)
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
    if c_ctxt._private is NULL:
        return
    context = <_SaxParserContext>c_ctxt._private
    if context._origSaxData is not NULL:
        context._origSaxData(c_ctxt, c_data, data_len)
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
    if c_ctxt._private is NULL:
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
    """TreeBuilder(self, element_factory=None, parser=None)
    Parser target that builds a tree.

    The final tree is returned by the ``close()`` method.
    """
    cdef _BaseParser _parser
    cdef object _factory
    cdef object _data
    cdef object _element_stack
    cdef object _element_stack_pop
    cdef _Element _last
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
                text = "".join(self._data)
                if self._in_tail:
                    assert self._last.tail is None, "internal error (tail)"
                    self._last.tail = text
                else:
                    assert self._last.text is None, "internal error (text)"
                    self._last.text = text
            del self._data[:]
        return 0

    # Python level event handlers

    def close(self):
        """close(self)

        Flushes the builder buffers, and returns the toplevel document
        element.
        """
        assert python.PyList_GET_SIZE(self._element_stack) == 0, "missing end tags"
        assert self._last is not None, "missing toplevel element"
        return self._last

    def data(self, data):
        """data(self, data)

        Adds text to the current element.  The value should be either an
        8-bit string containing ASCII text, or a Unicode string.
        """
        self._handleSaxData(data)

    def start(self, tag, attrs, nsmap=None):
        """start(self, tag, attrs, nsmap=None)

        Opens a new element.
        """
        if nsmap is None:
            nsmap = EMPTY_READ_ONLY_DICT
        return self._handleSaxStart(tag, attrs, nsmap)

    def end(self, tag):
        """end(self, tag)

        Closes the current element.
        """
        element = self._handleSaxEnd(tag)
        assert self._last.tag == tag,\
               "end tag mismatch (expected %s, got %s)" % (
                   self._last.tag, tag)
        return element

    def pi(self, target, data):
        """pi(self, target, data)
        """
        return self._handleSaxPi(target, data)

    def comment(self, comment):
        """comment(self, comment)
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
        python.PyList_Append(self._element_stack, self._last)
        self._in_tail = 0
        return self._last

    cdef _handleSaxEnd(self, tag):
        self._flush()
        self._last = self._element_stack_pop()
        self._in_tail = 1
        return self._last

    cdef int _handleSaxData(self, data) except -1:
        python.PyList_Append(self._data, data)

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
    """XMLParser(self, attribute_defaults=False, dtd_validation=False, load_dtd=False, no_network=True, ns_clean=False, recover=False, remove_blank_text=False, compact=True, resolve_entities=True, remove_comments=False, remove_pis=False, target=None, encoding=None, schema=None)
    The XML parser.

    Parsers can be supplied as additional argument to various parse
    functions of the lxml API.  A default parser is always available
    and can be replaced by a call to the global function
    'set_default_parser'.  New parsers can be created at any time
    without a major run-time overhead.

    The keyword arguments in the constructor are mainly based on the libxml2
    parser configuration.  A DTD will also be loaded if validation or
    attribute default values are requested.

    Available boolean keyword arguments:

    - attribute_defaults - read default attributes from DTD
    - dtd_validation     - validate (if DTD is available)
    - load_dtd           - use DTD for parsing
    - no_network         - prevent network access for related files (default: True)
    - ns_clean           - clean up redundant namespace declarations
    - recover            - try hard to parse through broken XML
    - remove_blank_text  - discard blank text nodes
    - remove_comments    - discard comments
    - remove_pis         - discard processing instructions
    - compact            - safe memory for short text content (default: True)
    - resolve_entities   - replace entities by their text value (default: True)

    Other keyword arguments:

    - encoding - override the document encoding
    - target   - a parser target object that will receive the parse events
    - schema   - an XMLSchema to validate against

    Note that you should avoid sharing parsers between threads.  While this is
    not harmful, it is more efficient to use separate parsers.  This does not
    apply to the default parser.
    """
    def __init__(self, *, attribute_defaults=False, dtd_validation=False,
                 load_dtd=False, no_network=True, ns_clean=False,
                 recover=False, remove_blank_text=False, compact=True,
                 resolve_entities=True, remove_comments=False,
                 remove_pis=False, target=None, encoding=None,
                 XMLSchema schema=None):
        cdef int parse_options
        parse_options = _XML_DEFAULT_PARSE_OPTIONS
        if load_dtd:
            parse_options = parse_options | xmlparser.XML_PARSE_DTDLOAD
        if dtd_validation:
            parse_options = parse_options | xmlparser.XML_PARSE_DTDVALID | \
                            xmlparser.XML_PARSE_DTDLOAD
        if attribute_defaults:
            parse_options = parse_options | xmlparser.XML_PARSE_DTDATTR | \
                            xmlparser.XML_PARSE_DTDLOAD
        if ns_clean:
            parse_options = parse_options | xmlparser.XML_PARSE_NSCLEAN
        if recover:
            parse_options = parse_options | xmlparser.XML_PARSE_RECOVER
        if remove_blank_text:
            parse_options = parse_options | xmlparser.XML_PARSE_NOBLANKS
        if not no_network:
            parse_options = parse_options ^ xmlparser.XML_PARSE_NONET
        if not compact:
            parse_options = parse_options ^ xmlparser.XML_PARSE_COMPACT
        if not resolve_entities:
            parse_options = parse_options ^ xmlparser.XML_PARSE_NOENT

        _BaseParser.__init__(self, parse_options, 0, schema,
                             remove_comments, remove_pis,
                             target, None, encoding)

cdef class ETCompatXMLParser(XMLParser):
    """ETCompatXMLParser(self, attribute_defaults=False, dtd_validation=False, load_dtd=False, no_network=True, ns_clean=False, recover=False, remove_blank_text=False, compact=True, resolve_entities=True, remove_comments=True, remove_pis=True, target=None, encoding=None, schema=None)
    An XML parser with an ElementTree compatible default setup.

    See the XMLParser class for details.

    This parser has ``remove_comments`` and ``remove_pis`` enabled by default
    and thus ignores comments and processing instructions.
    """
    def __init__(self, *, attribute_defaults=False, dtd_validation=False,
                 load_dtd=False, no_network=True, ns_clean=False,
                 recover=False, remove_blank_text=False, compact=True,
                 resolve_entities=True, remove_comments=True,
                 remove_pis=True, target=None, encoding=None, schema=None):
        XMLParser.__init__(self,
                           attribute_defaults=attribute_defaults,
                           dtd_validation=dtd_validation,
                           load_dtd=load_dtd,
                           no_network=no_network,
                           ns_clean=ns_clean,
                           recover=recover,
                           remove_blank_text=remove_blank_text,
                           compact=compact,
                           resolve_entities=resolve_entities,
                           remove_comments=remove_comments,
                           remove_pis=remove_pis,
                           target=target,
                           encoding=encoding,
                           schema=schema)


cdef XMLParser __DEFAULT_XML_PARSER
__DEFAULT_XML_PARSER = XMLParser()

__GLOBAL_PARSER_CONTEXT.setDefaultParser(__DEFAULT_XML_PARSER)

def setDefaultParser(parser=None):
    ":deprecated: please use set_default_parser instead."
    set_default_parser(parser)

def getDefaultParser():
    ":deprecated: please use get_default_parser instead."
    return get_default_parser()

def set_default_parser(_BaseParser parser=None):
    """set_default_parser(parser=None)

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
    "get_default_parser()"
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
    """HTMLParser(self, recover=True, no_network=True, remove_blank_text=False, compact=True, remove_comments=False, remove_pis=False, target=None, encoding=None, schema=None)
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
    - compact            - safe memory for short text content (default: True)

    Other keyword arguments:

    - encoding - override the document encoding
    - target   - a parser target object that will receive the parse events
    - schema   - an XMLSchema to validate against

    Note that you should avoid sharing parsers between threads for performance
    reasons.
    """
    def __init__(self, *, recover=True, no_network=True,
                 remove_blank_text=False, compact=True, remove_comments=False,
                 remove_pis=False, target=None, encoding=None,
                 XMLSchema schema=None):
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
                             remove_comments, remove_pis,
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
        return (<_BaseParser>parser)._parseUnicodeDoc(text, c_filename)
    else:
        c_text = _cstr(text)
        c_len  = python.PyString_GET_SIZE(text)
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

cdef xmlDoc* _newDoc() except NULL:
    cdef xmlDoc* result
    result = tree.xmlNewDoc("1.0")
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
    "Recursively copy the document and make c_new_root the new root node."
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
    "Recursively copy the element into the document. c_doc is not modified."
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

cdef _Document _parseDocument(source, _BaseParser parser):
    filename = _getFilenameForFile(source)
    if hasattr(source, 'getvalue') and hasattr(source, 'tell'):
        # StringIO - reading from start?
        if source.tell() == 0:
            return _parseMemoryDocument(
                source.getvalue(), _encodeFilenameUTF8(filename), parser)

    # Support for file-like objects (urlgrabber.urlopen, ...)
    if hasattr(source, 'read'):
        return _parseFilelikeDocument(
            source, _encodeFilenameUTF8(filename), parser)

    # Otherwise parse the file directly from the filesystem
    if filename is None:
        filename = _encodeFilename(source)
    # open filename
    return _parseDocumentFromURL(filename, parser)

cdef _Document _parseDocumentFromURL(url, _BaseParser parser):
    cdef xmlDoc* c_doc
    c_doc = _parseDocFromFile(url, parser)
    return _documentFactory(c_doc, parser)

cdef _Document _parseMemoryDocument(text, url, _BaseParser parser):
    cdef xmlDoc* c_doc
    if python.PyUnicode_Check(text):
        if _hasEncodingDeclaration(text):
            raise ValueError(
                "Unicode strings with encoding declaration are not supported.")
        # pass native unicode only if libxml2 can handle it
        if _UNICODE_ENCODING is NULL:
            text = python.PyUnicode_AsUTF8String(text)
    elif not python.PyString_Check(text):
        raise ValueError("can only parse strings")
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
