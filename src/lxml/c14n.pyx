cimport c14n
cimport tree
from tree cimport xmlDoc
cimport xmlparser

def canonicalize(xml):
    """Very simple way of canonicalizing XML.

    Returns canonicalized form of XML input.
    
    Useful for tests if nothing else.
    """
    cdef char* data
    cdef int bytes
    cdef xmlparser.xmlParserCtxt* pctxt
    xmlparser.xmlInitParser()
    pctxt = xmlparser.xmlCreateDocParserCtxt(xml)
    xmlparser.xmlCtxtUseOptions(pctxt,
                                xmlparser.XML_PARSE_NOENT |
                                xmlparser.XML_PARSE_NOCDATA)
    xmlparser.xmlParseDocument(pctxt)
    # XXX exceptions
    if not pctxt.wellFormed:
        tree.xmlFreeDoc(pctxt.myDoc)
        raise ValueError, "not well-formed XML"
    # XXX exceptions
    if pctxt.myDoc is NULL:
        raise ValueError, "No XML"
    bytes = c14n.xmlC14NDocDumpMemory(pctxt.myDoc,           
                                      NULL, 0, NULL, 1, &data)
    # XXX exceptions
    if bytes < 0:
        raise ValueError, "c18n failed"
    result = unicode(data, 'UTF-8')

    tree.xmlFree(data)
    tree.xmlFreeDoc(pctxt.myDoc)
    xmlparser.xmlFreeParserCtxt(pctxt)
    return result
