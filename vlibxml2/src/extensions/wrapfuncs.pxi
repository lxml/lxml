
def wrapNode(vlibxml2_tmpXMLNode tmpNode):
    '''
    Return an existing xmlNode wrapper or create one if necessary.  If the
    tmpNode is really just NULL, return None

    Do the same for the xmlDoc

    '''

    cdef xmlNodePtr nodePtr
    cdef xmlDocPtr  docPtr
    cdef vlibxml2_xmlNode newNode
    cdef vlibxml2_tmpXMLDoc tmpDoc

    if tmpNode._xmlNodePtr == NULL:
        return None

    nodePtr = tmpNode._xmlNodePtr
    docPtr = nodePtr.doc

    if not vlibxml2.nodecache.hasNode(<int> nodePtr, <int> docPtr):
        # !!! Note that we have to use a subclass of the vlibxml2_xmlNode to
        # get weakref support !!!

        vlibxml2.nodecache.initCacheForDocKey(<int> docPtr)

        newNode = vlibxml2.vlibxml2_subclasses.xmlNodeSub()
        newNode._xmlNodePtr = tmpNode._xmlNodePtr
        vlibxml2.nodecache.cacheNewNode(newNode)
        newNode.invalidNode = 0

        tmpDoc = vlibxml2_tmpXMLDoc()
        tmpDoc._xmlDocPtr = docPtr
        wrapDoc(tmpDoc)

    return vlibxml2.nodecache.nodeForKey(<int> nodePtr, <int> docPtr)


def wrapDoc(vlibxml2_tmpXMLDoc tmpDoc):
    '''
    Return an existing xmlDoc wrapper or create one if necessary
    '''
    cdef vlibxml2_xmlDoc newDoc

    if tmpDoc._xmlDocPtr == NULL:
        return None

    if not vlibxml2.nodecache.hasDocForDocKey(<int> tmpDoc._xmlDocPtr):
        newDoc = vlibxml2.vlibxml2_subclasses.xmlDocSub()
        newDoc._xmlDocPtr = tmpDoc._xmlDocPtr
        vlibxml2.nodecache.cacheNewDoc(newDoc)
    return vlibxml2.nodecache.docForDocKey(<int> tmpDoc._xmlDocPtr)
