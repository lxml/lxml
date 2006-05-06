#ifndef HAS_ETREE_H
#define HAS_ETREE_H

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

/* v_arg functions */
#define va_int(ap)     va_arg(ap, int)
#define va_charptr(ap) va_arg(ap, char *)

#endif /*HAS_ETREE_H*/
