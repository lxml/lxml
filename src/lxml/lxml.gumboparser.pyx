# Parsers for XML and HTML

cimport lxml.includes.etreepublic as cetree

# import the lxml.etree module in Python
cdef object etree
from lxml import etree

# initialize the access to the C-API of lxml.etree
cetree.import_lxml__etree()

from lxml.includes.etreepublic cimport _Document, elementFactory
from lxml.includes cimport tree

from lxml.includes.gumboparser cimport gumbo_libxml_parse

cdef _Document make_document(tree.xmlDoc* c_doc):
    cdef _Document result
    result = _Document.__new__(_Document)
    result._c_doc = c_doc
    return result

def fromstring(html, *args, **kw):
    cdef _Document doc
    cdef tree.xmlDoc* c_doc
    cdef tree.xmlNode* c_node
    if not isinstance(html, unicode) and not isinstance(html, bytes):
        raise ValueError, u"can only parse strings"
    c_doc = gumbo_libxml_parse(html)
    doc = make_document(c_doc)

    c_node = tree.xmlDocGetRootElement(c_doc)
    if c_node is NULL:
        return None

    return elementFactory(doc, c_node)
