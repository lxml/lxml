#ifndef HAS_ETREE_H
#define HAS_ETREE_H

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

#endif /*HAS_ETREE_H*/
