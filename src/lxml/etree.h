#ifndef HAS_ETREE_H
#define HAS_ETREE_H

#define isinstance(a,b) PyObject_IsInstance(a,b)
#define hasattr(a,b)    PyObject_HasAttr(a,b)
#define callable(a)     PyCallable_Check(a)
#define _cstr(s)        PyString_AS_STRING(s)
#define _isElement(c_node) \
        ((c_node)->type == XML_ELEMENT_NODE || \
	 (c_node)->type == XML_COMMENT_NODE)

#endif /*HAS_ETREE_H*/
