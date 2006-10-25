#ifndef HAS_ETREE_DEFS_H
#define HAS_ETREE_DEFS_H

/* v_arg functions */
#define va_int(ap)     va_arg(ap, int)
#define va_charptr(ap) va_arg(ap, char *)

/* Py_ssize_t support was added in Python 2.5 */
#if PY_VERSION_HEX < 0x02050000
#ifndef PY_SSIZE_T_MAX /* patched Pyrex? */
  typedef int Py_ssize_t;
  #define PY_SSIZE_T_MAX INT_MAX
  #define PY_SSIZE_T_MIN INT_MIN
  #define PyInt_FromSsize_t(z) PyInt_FromLong(z)
  #define PyInt_AsSsize_t(o)   PyInt_AsLong(o)
#endif
#endif

/* libxml2 version specific setup */
#include "libxml/xmlversion.h"
#if LIBXML_VERSION < 20621
/* (X|HT)ML_PARSE_COMPACT were added in libxml2 2.6.21 */
#define XML_PARSE_COMPACT  0
#define HTML_PARSE_COMPACT 0

/* HTML_PARSE_RECOVER was added in libxml2 2.6.21 */
#define HTML_PARSE_RECOVER XML_PARSE_RECOVER
#endif

/* Redefinition of some Python builtins as C functions */
#define isinstance(o,c) PyObject_IsInstance(o,c)
#define issubclass(c,csuper) PyObject_IsSubclass(c,csuper)
#define hasattr(o,a)    PyObject_HasAttr(o,a)
#define getattr(o,a)    PyObject_GetAttr(o,a)
#define callable(o)     PyCallable_Check(o)
#define str(o)          PyObject_Str(o)
#define repr(o)         PyObject_Repr(o)
#define iter(o)         PyObject_GetIter(o)
#define _cstr(s)        PyString_AS_STRING(s)

#define _isString(obj)   PyObject_TypeCheck(obj, &PyBaseString_Type)

#define _isElement(c_node) \
        (((c_node)->type == XML_ELEMENT_NODE) || \
	 ((c_node)->type == XML_COMMENT_NODE) || \
         ((c_node)->type == XML_PI_NODE))

#define _getNs(c_node) \
        (((c_node)->ns == 0) ? 0 : ((c_node)->ns->href))

/* Macro pair implementation of a depth first tree walker
 *
 * Calls the code block between the BEGIN and END macros for all elements
 * below c_tree_top (exclusively), starting at c_node (inclusively iff
 * 'inclusive' is 1).
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

#define _ADVANCE_TO_NEXT_ELEMENT(c_node)             \
    while ((c_node != 0) && (!_isElement(c_node)))   \
        c_node = c_node->next;

#define _TRAVERSE_TO_NEXT_ELEMENT(c_stop_node, c_node)         \
{                                                              \
    /* walk through children first */                          \
    xmlNode* ___next = c_node->children;                       \
    _ADVANCE_TO_NEXT_ELEMENT(___next)                          \
    if ((___next == 0) && (c_node != c_stop_node)) {           \
        /* try siblings */                                     \
        ___next = c_node->next;                                \
        _ADVANCE_TO_NEXT_ELEMENT(___next)                      \
        /* back off through parents */                         \
        while (___next == 0) {                                 \
            c_node = c_node->parent;                           \
            if (c_node == 0)                                   \
                break;                                         \
            if (c_node == c_stop_node)                         \
                break;                                         \
            if (!_isElement(c_node))                           \
                break;                                         \
            /* we already traversed the parents -> siblings */ \
            ___next = c_node->next;                            \
            _ADVANCE_TO_NEXT_ELEMENT(___next)                  \
        }                                                      \
    }                                                          \
    c_node = ___next;                                          \
}

#define BEGIN_FOR_EACH_ELEMENT_FROM(c_tree_top, c_node, inclusive)    \
{                                                                     \
    if (c_node != 0) {                                                \
        const xmlNode* ___tree_top = (c_tree_top);                    \
        /* make sure we start at an element */                        \
        if (!_isElement(c_node)) {                                    \
            /* we skip the node, so 'inclusive' is irrelevant */      \
            if (c_node == ___tree_top)                                \
                c_node = 0; /* nothing to traverse */                 \
            else {                                                    \
                c_node = c_node->next;                                \
                _ADVANCE_TO_NEXT_ELEMENT(c_node)                      \
            }                                                         \
        } else if (! (inclusive)) {                                   \
            /* skip the first node */                                 \
            _TRAVERSE_TO_NEXT_ELEMENT(___tree_top, c_node)            \
        }                                                             \
                                                                      \
        /* now run the user code on the elements we find */           \
        while (c_node != 0) {                                         \
            /* here goes the code to be run for each element */

#define END_FOR_EACH_ELEMENT_FROM(c_node)                             \
            _TRAVERSE_TO_NEXT_ELEMENT(___tree_top, c_node)            \
        }                                                             \
    }                                                                 \
}


#endif /* HAS_ETREE_DEFS_H */
