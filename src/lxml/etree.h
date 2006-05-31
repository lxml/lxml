#ifndef HAS_ETREE_H
#define HAS_ETREE_H

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

#define isinstance(o,c) PyObject_IsInstance(o,c)
#define issubclass(c,csuper) PyObject_IsSubclass(c,csuper)
#define hasattr(o,a)    PyObject_HasAttr(o,a)
#define callable(o)     PyCallable_Check(o)
#define str(o)          PyObject_Str(o)
#define iter(o)         PyObject_GetIter(o)
#define _cstr(s)        PyString_AS_STRING(s)

#define _isElement(c_node) \
        ((c_node)->type == XML_ELEMENT_NODE || \
	 (c_node)->type == XML_COMMENT_NODE)

/* Macro set implementation of a depth first tree walker
 *
 * Calls the code block between the BEGIN and END macros
 *   1) for the start element (or the first 'element' sibling)
 *   2) for all children (recursively)
 *   3) all siblings (recursively)
 *
 * Usage in Pyrex:
 *    cdef xmlNode* some_node
 *    some_node = parent_node.children
 *    BEGIN_FOR_EACH_ELEMENT_FROM(some_node)
 *    # do something with some_node
 *    END_FOR_EACH_ELEMENT_FROM(some_node)
 *
 * NOTE: 'some_node' MUST be a plain 'xmlNode*' !
 * NOTE: parent modification during the walk will segfault !
 */

#define BEGIN_FOR_EACH_ELEMENT_FROM(c_node)                       \
{                                                                 \
    while ((c_node != 0) && (!_isElement(c_node)))                \
        c_node = c_node->next;                                    \
    if (c_node != 0) {                                            \
        xmlNode* ___start_parent = c_node->parent;                \
        xmlNode* ___next;                                         \
        while (c_node != 0) {
            /* here goes the code to be run for each element */
#define END_FOR_EACH_ELEMENT_FROM(c_node)                         \
            /* walk through children */                           \
            ___next = c_node->children;                           \
            while ((___next != 0) && (!_isElement(___next)))      \
                ___next = ___next->next;                          \
            if (___next == 0) {                                   \
                /* try siblings */                                \
                ___next = c_node->next;                           \
                while ((___next != 0) && (!_isElement(___next)))  \
                   ___next = ___next->next;                       \
            }                                                     \
            /* back off through parents */                        \
            while (___next == 0) {                                \
                c_node = c_node->parent;                          \
                if (c_node == ___start_parent)                    \
                    break;                                        \
                ___next = c_node->next;                           \
                while ((___next != 0) && (!_isElement(___next)))  \
                    ___next = ___next->next;                      \
            }                                                     \
            c_node = ___next;                                     \
        }                                                         \
    }                                                             \
}

#endif /*HAS_ETREE_H*/
