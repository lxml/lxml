#ifndef HAS_ETREE_H
#define HAS_ETREE_H

#define isinstance(a,b) PyObject_IsInstance(a,b)
#define hasattr(a,b)    PyObject_HasAttrString(a,b)

#endif /*HAS_ETREE_H*/
