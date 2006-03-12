#ifndef HAS_ETREE_H
#define HAS_ETREE_H

#define isinstance(a,b) PyObject_IsInstance(a,b)
#define hasattr(a,b)    PyObject_HasAttrString(a,b)
#define _isElement(c_node) \
        ((c_node)->type == XML_ELEMENT_NODE || \
	 (c_node)->type == XML_COMMENT_NODE)

typedef enum {
    PROXY_ELEMENT,
    PROXY_ATTRIB
} LXML_PROXY_TYPE;

#endif /*HAS_ETREE_H*/
