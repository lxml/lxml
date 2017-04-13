# Parsers for XML and HTML

cimport lxml.includes.etreepublic as cetree

# import the lxml.etree module in Python
cdef object etree
from lxml import etree

# initialize the access to the C-API of lxml.etree
cetree.import_lxml__etree()

from lxml.includes.etreepublic cimport _Document, elementFactory, documentFactory
from lxml.includes cimport tree

from lxml.includes.gumboparser cimport gumbo_libxml_parse

_html_parser = etree.HTMLParser()

def fromstring(html, *args, **kw):
    cdef _Document doc
    cdef tree.xmlDoc* c_doc
    cdef tree.xmlNode* c_node
    if not isinstance(html, unicode):
        raise ValueError, u"can only parse unicode"
    c_doc = gumbo_libxml_parse(html.encode('utf-8'))
    doc = documentFactory(c_doc, _html_parser)

    c_node = tree.xmlDocGetRootElement(c_doc)
    if c_node is NULL:
        return None

    return elementFactory(doc, c_node)
