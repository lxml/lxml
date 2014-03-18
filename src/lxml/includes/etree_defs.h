#ifndef HAS_ETREE_DEFS_H
#define HAS_ETREE_DEFS_H

/* quick check for Python/libxml2/libxslt devel setup */
#include "Python.h"
#ifndef PY_VERSION_HEX
#  error the development package of Python (header files etc.) is not installed correctly
#endif
#include "libxml/xmlversion.h"
#ifndef LIBXML_VERSION
#  error the development package of libxml2 (header files etc.) is not installed correctly
#endif
#include "libxslt/xsltconfig.h"
#ifndef LIBXSLT_VERSION
#  error the development package of libxslt (header files etc.) is not installed correctly
#endif


/* v_arg functions */
#define va_int(ap)     va_arg(ap, int)
#define va_charptr(ap) va_arg(ap, char *)

#ifdef PYPY_VERSION
#    define IS_PYPY 1
#else
#    define IS_PYPY 0
#endif

#if PY_VERSION_HEX >= 0x03000000
#  define IS_PYTHON3 1
#else
#  define IS_PYTHON3 0
#endif

#if IS_PYTHON3
#undef LXML_UNICODE_STRINGS
#define LXML_UNICODE_STRINGS 1
#else
#ifndef LXML_UNICODE_STRINGS
#define LXML_UNICODE_STRINGS 0
#endif
#endif

#if !IS_PYPY
#  define PyWeakref_LockObject(obj)          (NULL)
#endif

/* Threading can crash under Python <= 2.4.1 and is not currently supported by PyPy */
#if PY_VERSION_HEX < 0x02040200 || IS_PYPY
#  ifndef WITHOUT_THREADING
#    define WITHOUT_THREADING
#  endif
#endif

/* Python 3 doesn't have PyFile_*() anymore */
#if PY_VERSION_HEX >= 0x03000000
#  define PyFile_AsFile(o)                   (NULL)
#else
#if IS_PYPY
#  undef PyFile_AsFile
#  define PyFile_AsFile(o)                   (NULL)
#  undef PyUnicode_FromFormat
#  define PyUnicode_FromFormat(s, a, b)      (NULL)
#else
#if PY_VERSION_HEX < 0x02060000
/* Cython defines these already, but we may not be compiling in Cython code */
#ifndef PyBytes_CheckExact
#  define PyBytes_CheckExact(o)              PyString_CheckExact(o)
#  define PyBytes_Check(o)                   PyString_Check(o)
#  define PyBytes_FromStringAndSize(s, len)  PyString_FromStringAndSize(s, len)
#  define PyBytes_FromFormat                 PyString_FromFormat
#  define PyBytes_GET_SIZE(s)                PyString_GET_SIZE(s)
#  define PyBytes_AS_STRING(s)               PyString_AS_STRING(s)
#endif
/* we currently only use three parameters - MSVC can't compile (s, ...) */
#  define PyUnicode_FromFormat(s, a, b)      (NULL)
#endif
#endif
#endif

#if PY_VERSION_HEX <= 0x03030000 && !(defined(CYTHON_PEP393_ENABLED) && CYTHON_PEP393_ENABLED)
  #define PyUnicode_IS_READY(op)    (0)
  #define PyUnicode_GET_LENGTH(u)   PyUnicode_GET_SIZE(u)
  #define PyUnicode_KIND(u)         (sizeof(Py_UNICODE))
  #define PyUnicode_DATA(u)         ((void*)PyUnicode_AS_UNICODE(u))
#endif

/* PySlice_GetIndicesEx() has wrong signature in Py<=3.1 */
#if PY_VERSION_HEX >= 0x03020000
#  define _lx_PySlice_GetIndicesEx(o, l, b, e, s, sl) PySlice_GetIndicesEx(o, l, b, e, s, sl)
#else
#  define _lx_PySlice_GetIndicesEx(o, l, b, e, s, sl) PySlice_GetIndicesEx(((PySliceObject*)o), l, b, e, s, sl)
#endif

#ifdef WITHOUT_THREADING
#  define PyEval_SaveThread() (NULL)
#  define PyEval_RestoreThread(state)
#  define PyGILState_Ensure() (PyGILState_UNLOCKED)
#  define PyGILState_Release(state)
#  undef  Py_UNBLOCK_THREADS
#  define Py_UNBLOCK_THREADS
#  undef  Py_BLOCK_THREADS
#  define Py_BLOCK_THREADS
#endif

#ifdef WITHOUT_THREADING
#  define ENABLE_THREADING 0
#else
#  define ENABLE_THREADING 1
#endif

/* libxml2 version specific setup */
#if LIBXML_VERSION < 20621
/* (X|HT)ML_PARSE_COMPACT were added in libxml2 2.6.21 */
#  define XML_PARSE_COMPACT  1 << 16
#  define HTML_PARSE_COMPACT XML_PARSE_COMPACT

/* HTML_PARSE_RECOVER was added in libxml2 2.6.21 */
#  define HTML_PARSE_RECOVER XML_PARSE_RECOVER
#endif

#if LIBXML_VERSION < 20700
/* These were added in libxml2 2.7.0 */
#  define XML_PARSE_OLD10      1 << 17
#  define XML_PARSE_NOBASEFIX  1 << 18
#  define XML_PARSE_HUGE       1 << 19
#  define xmlMemDisplayLast(f,d)
#endif

#if LIBXML_VERSION < 20704
/* FIXME: hack to make new error reporting compile in old libxml2 versions */
#  define xmlStructuredErrorContext NULL
#endif

/* added to xmlsave API in libxml2 2.6.23 */
#if LIBXML_VERSION < 20623
#  define xmlSaveToBuffer(buffer, encoding, options)
#endif

/* added to xmlsave API in libxml2 2.6.22 */
#if LIBXML_VERSION < 20622
#  define XML_SAVE_NO_EMPTY   1<<2  /* no empty tags */
#  define XML_SAVE_NO_XHTML   1<<3  /* disable XHTML1 specific rules */
#endif

/* added to xmlsave API in libxml2 2.6.21 */
#if LIBXML_VERSION < 20621
#  define XML_SAVE_NO_DECL    1<<1  /* drop the xml declaration */
#endif

/* schematron was added in libxml2 2.6.21 */
#ifdef LIBXML_SCHEMATRON_ENABLED
#  define ENABLE_SCHEMATRON 1
#  if LIBXML_VERSION < 20632
     /* schematron error reporting was added in libxml2 2.6.32 */
#    define xmlSchematronSetValidStructuredErrors(ctxt, errorfunc, data)
#    define XML_SCHEMATRON_OUT_ERROR 0
#  endif
#else
#  define ENABLE_SCHEMATRON 0
#  define XML_SCHEMATRON_OUT_QUIET 0
#  define XML_SCHEMATRON_OUT_XML 0
#  define XML_SCHEMATRON_OUT_ERROR 0
   typedef void xmlSchematron;
   typedef void xmlSchematronParserCtxt;
   typedef void xmlSchematronValidCtxt;
#  define xmlSchematronNewDocParserCtxt(doc) NULL
#  define xmlSchematronNewParserCtxt(file) NULL
#  define xmlSchematronParse(ctxt) NULL
#  define xmlSchematronFreeParserCtxt(ctxt)
#  define xmlSchematronFree(schema)
#  define xmlSchematronNewValidCtxt(schema, options) NULL
#  define xmlSchematronValidateDoc(ctxt, doc) 0
#  define xmlSchematronFreeValidCtxt(ctxt)
#  define xmlSchematronSetValidStructuredErrors(ctxt, errorfunc, data)
#endif

#if LIBXML_VERSION < 20900
#  define XML_PARSE_BIG_LINES 4194304
#endif

#include "libxml/tree.h"
#ifndef LIBXML2_NEW_BUFFER
   typedef xmlBuffer xmlBuf;
#  define xmlBufContent(buf) xmlBufferContent(buf)
#  define xmlBufUse(buf) xmlBufferLength(buf)
#endif

/* libexslt 1.1.25+ support EXSLT functions in XPath */
#if LIBXSLT_VERSION < 10125
#define exsltDateXpathCtxtRegister(ctxt, prefix)
#define exsltSetsXpathCtxtRegister(ctxt, prefix)
#define exsltMathXpathCtxtRegister(ctxt, prefix)
#define exsltStrXpathCtxtRegister(ctxt, prefix)
#endif

/* work around MSDEV 6.0 */
#if (_MSC_VER == 1200) && (WINVER < 0x0500)
long _ftol( double ); //defined by VC6 C libs
long _ftol2( double dblSource ) { return _ftol( dblSource ); }
#endif

#ifdef __GNUC__
/* Test for GCC > 2.95 */
#if __GNUC__ > 2 || (__GNUC__ == 2 && (__GNUC_MINOR__ > 95)) 
#define unlikely_condition(x) __builtin_expect((x), 0)
#else /* __GNUC__ > 2 ... */
#define unlikely_condition(x) (x)
#endif /* __GNUC__ > 2 ... */
#else /* __GNUC__ */
#define unlikely_condition(x) (x)
#endif /* __GNUC__ */

#ifndef Py_TYPE
  #define Py_TYPE(ob)   (((PyObject*)(ob))->ob_type)
#endif

#define PY_NEW(T) \
     (((PyTypeObject*)(T))->tp_new( \
             (PyTypeObject*)(T), __pyx_empty_tuple, NULL))

#define _fqtypename(o)  ((Py_TYPE(o))->tp_name)

#if PY_MAJOR_VERSION < 3
#define _isString(obj)   (PyString_CheckExact(obj)  || \
                          PyUnicode_CheckExact(obj) || \
                          PyObject_TypeCheck(obj, &PyBaseString_Type))
#else
#define _isString(obj)   (PyUnicode_Check(obj) || PyBytes_Check(obj))
#endif

#define _isElement(c_node) \
        (((c_node)->type == XML_ELEMENT_NODE) || \
         ((c_node)->type == XML_COMMENT_NODE) || \
         ((c_node)->type == XML_ENTITY_REF_NODE) || \
         ((c_node)->type == XML_PI_NODE))

#define _isElementOrXInclude(c_node) \
        (_isElement(c_node)                     || \
         ((c_node)->type == XML_XINCLUDE_START) || \
         ((c_node)->type == XML_XINCLUDE_END))

#define _getNs(c_node) \
        (((c_node)->ns == 0) ? 0 : ((c_node)->ns->href))


/* Macro pair implementation of a depth first tree walker
 *
 * Calls the code block between the BEGIN and END macros for all elements
 * below c_tree_top (exclusively), starting at c_node (inclusively iff
 * 'inclusive' is 1).  The _ELEMENT_ variants will only stop on nodes
 * that match _isElement(), the normal variant will stop on every node
 * except text nodes.
 * 
 * To traverse the node and all of its children and siblings in Pyrex, call
 *    cdef xmlNode* some_node
 *    BEGIN_FOR_EACH_ELEMENT_FROM(some_node.parent, some_node, 1)
 *    # do something with some_node
 *    END_FOR_EACH_ELEMENT_FROM(some_node)
 *
 * To traverse only the children and siblings of a node, call
 *    cdef xmlNode* some_node
 *    BEGIN_FOR_EACH_ELEMENT_FROM(some_node.parent, some_node, 0)
 *    # do something with some_node
 *    END_FOR_EACH_ELEMENT_FROM(some_node)
 *
 * To traverse only the children, do:
 *    cdef xmlNode* some_node
 *    some_node = parent_node.children
 *    BEGIN_FOR_EACH_ELEMENT_FROM(parent_node, some_node, 1)
 *    # do something with some_node
 *    END_FOR_EACH_ELEMENT_FROM(some_node)
 *
 * NOTE: 'some_node' MUST be a plain 'xmlNode*' !
 *
 * NOTE: parent modification during the walk can divert the iterator, but
 *       should not segfault !
 */

#define _LX__ELEMENT_MATCH(c_node, only_elements)  \
    ((only_elements) ? (_isElement(c_node)) : 1)

#define _LX__ADVANCE_TO_NEXT(c_node, only_elements)                        \
    while ((c_node != 0) && (!_LX__ELEMENT_MATCH(c_node, only_elements)))  \
        c_node = c_node->next;

#define _LX__TRAVERSE_TO_NEXT(c_stop_node, c_node, only_elements)   \
{                                                                   \
    /* walk through children first */                               \
    xmlNode* _lx__next = c_node->children;		            \
    if (_lx__next != 0) {                                           \
        if (c_node->type == XML_ENTITY_REF_NODE || c_node->type == XML_DTD_NODE) { \
            _lx__next = 0;                                          \
        } else {                                                    \
            _LX__ADVANCE_TO_NEXT(_lx__next, only_elements)	    \
        }                                                           \
    }							            \
    if ((_lx__next == 0) && (c_node != c_stop_node)) {              \
        /* try siblings */                                          \
        _lx__next = c_node->next;                                   \
        _LX__ADVANCE_TO_NEXT(_lx__next, only_elements)              \
        /* back off through parents */                              \
        while (_lx__next == 0) {                                    \
            c_node = c_node->parent;                                \
            if (c_node == 0)                                        \
                break;                                              \
            if (c_node == c_stop_node)                              \
                break;                                              \
            if ((only_elements) && !_isElement(c_node))	            \
                break;                                              \
            /* we already traversed the parents -> siblings */      \
            _lx__next = c_node->next;                               \
            _LX__ADVANCE_TO_NEXT(_lx__next, only_elements)	    \
        }                                                           \
    }                                                               \
    c_node = _lx__next;                                             \
}

#define _LX__BEGIN_FOR_EACH_FROM(c_tree_top, c_node, inclusive, only_elements)     \
{									      \
    if (c_node != 0) {							      \
        const xmlNode* _lx__tree_top = (c_tree_top);                          \
        const int _lx__only_elements = (only_elements);                       \
        /* make sure we start at an element */                   	      \
        if (!_LX__ELEMENT_MATCH(c_node, _lx__only_elements)) {		      \
            /* we skip the node, so 'inclusive' is irrelevant */              \
            if (c_node == _lx__tree_top)                                      \
                c_node = 0; /* nothing to traverse */                         \
            else {                                                            \
                c_node = c_node->next;                                        \
                _LX__ADVANCE_TO_NEXT(c_node, _lx__only_elements)              \
            }                                                                 \
        } else if (! (inclusive)) {                                           \
            /* skip the first node */                                         \
            _LX__TRAVERSE_TO_NEXT(_lx__tree_top, c_node, _lx__only_elements)  \
        }                                                                     \
                                                                              \
        /* now run the user code on the elements we find */                   \
        while (c_node != 0) {                                                 \
            /* here goes the code to be run for each element */

#define _LX__END_FOR_EACH_FROM(c_node)                                        \
            _LX__TRAVERSE_TO_NEXT(_lx__tree_top, c_node, _lx__only_elements)  \
        }                                                                     \
    }                                                                         \
}


#define BEGIN_FOR_EACH_ELEMENT_FROM(c_tree_top, c_node, inclusive)   \
    _LX__BEGIN_FOR_EACH_FROM(c_tree_top, c_node, inclusive, 1)

#define END_FOR_EACH_ELEMENT_FROM(c_node)   \
    _LX__END_FOR_EACH_FROM(c_node)

#define BEGIN_FOR_EACH_FROM(c_tree_top, c_node, inclusive)   \
    _LX__BEGIN_FOR_EACH_FROM(c_tree_top, c_node, inclusive, 0)

#define END_FOR_EACH_FROM(c_node)   \
    _LX__END_FOR_EACH_FROM(c_node)


#endif /* HAS_ETREE_DEFS_H */
