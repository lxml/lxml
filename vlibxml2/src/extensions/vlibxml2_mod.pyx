import vlibxml2.nodecache
import vlibxml2.vlibxml2_subclasses

# stddef is required by just about everything
include "stddef.pxi"

# forward declarations for our custom Pyrex classes
include "forwarddecls.pxi"

# Now include the declarations from the various libxml2 modules
include "tree.pxi"
include "parser.pxi"
include "xpath.pxi"
include "xmlmemory.pxi"

include "tempclasses.pxi"
include "wrapfuncs.pxi"

libxmlMemoryDebug = 0
libxmlMemoryAllocatedBase = 0

cdef xmlFreeFunc freeFunc
cdef xmlMallocFunc mallocFunc
cdef xmlReallocFunc reallocFunc
cdef xmlStrdupFunc strdupFunc

debugMode = False

def initParser():
    xmlInitParser()

def cleanupParser():
    xmlCleanupParser()

def debugMemory(activate):
    '''
    Switch on the generation of line number for elements nodes.
    Also returns the number of bytes allocated and not freed
    by libxml2 since memory debugging was switched on.
    '''

    global libxmlMemoryDebug
    global libxmlMemoryAllocatedBase

    ret = 0
    if (activate != 0):
        if (libxmlMemoryDebug == 0):
            # First initialize the library and grab the old memory handlers
            # and switch the library to memory debugging
            xmlMemGet(<xmlFreeFunc *> freeFunc,
                      <xmlMallocFunc *> & mallocFunc,
                      <xmlReallocFunc *> & reallocFunc,
                      <xmlStrdupFunc *> & strdupFunc)
            if ((<void *>freeFunc == <void *>xmlMemFree) and \
                (<void *>mallocFunc == <void *>xmlMemMalloc) and \
                (<void *>reallocFunc == <void *>xmlMemRealloc) and \
                (<void *> strdupFunc == <void *>xmlMemoryStrdup)):
                libxmlMemoryAllocatedBase = xmlMemUsed()
            else:
                ret = <long> xmlMemSetup(xmlMemFree, xmlMemMalloc,
                                         xmlMemRealloc, xmlMemoryStrdup)
                if ret < 0:
                    raise RuntimeError("Error while calling xmlMemSetup!  Error code %s" % ret, ret)
                libxmlMemoryAllocatedBase = xmlMemUsed()
            xmlInitParser()
            ret = 0
        elif libxmlMemoryDebugActivated == 0:
            libxmlMemoryAllocatedBase = xmlMemUsed()
            ret = 0
        else:
            ret = xmlMemUsed() - libxmlMemoryAllocatedBase

        libxmlMemoryDebug = 1
        libxmlMemoryDebugActivated = 1
    else:
        if (libxmlMemoryDebugActivated == 1):
            ret = xmlMemUsed() - libxmlMemoryAllocatedBase
        else:
            ret = 0
        libxmlMemoryDebugActivated = 0

    return ret


def newDoc(char *version):
    '''
    create a new xmlDocument
    '''
    cdef xmlDocPtr docPtr
    cdef vlibxml2_tmpXMLDoc tmpDoc
    docPtr = xmlNewDoc(<xmlChar *> version)
    tmpDoc = vlibxml2_tmpXMLDoc()
    tmpDoc._xmlDocPtr = docPtr
    return wrapDoc(tmpDoc)

def newNode(char *tagname):
    '''
    create a new xmlNode. Note that this will also allocate a new xmlDoc
    per xmlNode.

    Order really matters a lot here.


    '''
    cdef xmlNodePtr nodePtr
    cdef vlibxml2_tmpXMLNode tmpNode
    cdef vlibxml2_xmlDoc xmlDoc

    # first create the new transient document
    xmlDoc = newDoc('1.0')
    nodePtr = xmlNewNode( NULL, <xmlChar *> tagname )
    xmlDocSetRootElement(xmlDoc._xmlDocPtr, nodePtr)
    tmpNode = vlibxml2_tmpXMLNode()
    tmpNode._xmlNodePtr = nodePtr
    return wrapNode(tmpNode)

def parseDoc(char *doc):
    '''
    parse a string into a new xmlDocument
    '''
    cdef xmlDocPtr docPtr
    cdef vlibxml2_tmpXMLDoc tmpDoc
    docPtr = xmlParseDoc(<xmlChar *> doc)
    tmpDoc = vlibxml2_tmpXMLDoc()
    tmpDoc._xmlDocPtr = docPtr
    return wrapDoc(tmpDoc)


cdef class vlibxml2_xmlNode:
    cdef xmlNodePtr _xmlNodePtr
    cdef int invalidNode

    def __new__(self):
        self.invalidNode = 1

    def __hash__(self):
        return <int> self._xmlNodePtr

    def name(self):
        cdef char *buff
        buff = <char *> self._xmlNodePtr.name
        if buff == NULL:
            return None
        return buff

    def setName(self, char *name):
        self._xmlNodePtr.name = <xmlChar *>name


    def type(self):
        ''' the xmlElementType enum value for this node.  '''
        return self._xmlNodePtr.type


    def unlinkNode(self):
        '''
        unlink this node from the xmlNode/xmlDoc graph
        '''
        cdef xmlDocPtr  docPtr
        cdef xmlNodePtr nodePtr
        cdef vlibxml2_tmpXMLDoc tmpDoc

        nodePtr = self._xmlNodePtr
        docPtr  = self._xmlNodePtr.doc

        vlibxml2.nodecache.removeNodeFromDocKey(<int> nodePtr, <int> docPtr)
        vlibxml2.nodecache.compressDocKey(<int> docPtr)
        xmlUnlinkNode(nodePtr)

        # create a new tmp doc ptr
        docPtr = xmlNewDoc(<xmlChar *> '1.0')
        # set the rootelement to be the current node
        xmlDocSetRootElement(docPtr, nodePtr)

        # wrap it up in a new doc
        tmpDoc = vlibxml2_tmpXMLDoc()
        tmpDoc._xmlDocPtr = docPtr
        wrapDoc(tmpDoc)



    def addChild(self, vlibxml2_xmlNode cur):
        '''
        Ok - this is a little weird.  When you call doc.addChild(cur),
        cur may be the only entry point into cur's XML graph.  If that's the case,
        then you've got GC problems as the weakref cache will never kickoff a deallocation
        callback since the node wasn't actually destroyed - just moved.

        To solve this problem easily, we just create a temporary reference to the xmlDoc
        of the graph.  If there are _other_ references, then well - we ust incur the cost of
        a pointer create/destruction. No biggie.
        '''
        # Do _NOT_ delete this reference to curDoc as the moveNodeToNewDoc
        # will screw up if you don't hold a reference to the 'old' document
        # for cur
        cdef vlibxml2_xmlDoc curDoc
        curDoc = cur.xmlDoc()

        # unlink the cur from it's parent

        xmlUnlinkNode(cur._xmlNodePtr)

        # move node to new doc
        vlibxml2.nodecache.moveNodeToNewDoc(cur, <int> self._xmlNodePtr.doc)

        xmlAddChild(self._xmlNodePtr, cur._xmlNodePtr)

    def replaceNode(self, vlibxml2_xmlNode cur):
        '''
        Replace this node with another node's nodePtr.

        This is a DANGEROUS thing to do!!! Replacing the underlying nodePtr
        will mangle the __hash__ and __eq__ functions in the cache
        '''

        # the root node is the node
        cdef xmlDocPtr  thisDoc
        cdef xmlDocPtr  tmpDoc
        cdef xmlNodePtr thisNode

        cdef xmlNodePtr prevNode
        cdef xmlNodePtr nextNode
        cdef xmlNodePtr parentNode
        cdef xmlNodePtr curNode
        cdef xmlNodePtr curParentNode
        cdef xmlDocPtr  curDoc
        cdef int parentType

        # setup ptrs for thisNode
        thisNode = self._xmlNodePtr
        thisDoc = thisNode.doc
        prevNode = thisNode.prev
        nextNode = thisNode.next
        parentNode = thisNode.parent

        # Setup ptrs for curNode
        curNode = cur._xmlNodePtr
        curParentNode = curNode.parent
        curDoc = curNode.doc

        if curParentNode.type <> XML_DOCUMENT_NODE:
            raise "The element you are trying to use as a replacement must be the root node of a document.  Parent node type is :%d" % curParentNode.type



        if prevNode <> NULL:
            # Case 1 - we can get at this node through the previous node

            # remove nodes from the nodecache to make sure that we're not participating in automatic GC
            vlibxml2.nodecache.removeNodeFromDocKey(<int> thisNode, <int> thisDoc)
            vlibxml2.nodecache.removeNodeFromDocKey(<int> curNode, <int> curDoc)

            vlibxml2.nodecache.compressDocKey(<int> curDoc)

            # unlink this node
            xmlUnlinkNode(thisNode)
            xmlUnlinkNode(curNode)

            # add a new childnode to the parentNode
            xmlAddNextSibling(prevNode, curNode)

            # Manually assign the document pointer for the current node to 'this' document node
            curNode.doc = thisDoc

            # assign the curNode to self._xmlNodePtr
            self._xmlNodePtr = curNode

            vlibxml2.nodecache.cacheNewNode(self)

            # now manually destroy the old node
            xmlFreeNode(thisNode)
            xmlFreeDoc(curDoc)

        elif nextNode <> NULL:
            # Case 1 - we can get at this node through the previous node

            # remove nodes from the nodecache to make sure that we're not participating in automatic GC
            vlibxml2.nodecache.removeNodeFromDocKey(<int> thisNode, <int> thisDoc)
            vlibxml2.nodecache.removeNodeFromDocKey(<int> curNode, <int> curDoc)

            vlibxml2.nodecache.compressDocKey(<int> curDoc)

            # unlink this node
            xmlUnlinkNode(thisNode)
            xmlUnlinkNode(curNode)

            # add a new childnode to the parentNode
            xmlAddPrevSibling(nextNode, curNode)

            # Manually assign the document pointer for the current node to 'this' document node
            curNode.doc = thisDoc

            # assign the curNode to self._xmlNodePtr
            self._xmlNodePtr = curNode

            vlibxml2.nodecache.cacheNewNode(self)

            # now manually destroy the old node
            xmlFreeNode(thisNode)
            xmlFreeDoc(curDoc)

        else:
            # do the node replacement with reference to the parent node
            parentType = parentNode.type

            # Case 3 of replaceNode - the parentNode of the current node is a document

            # remove nodes from the nodecache to make sure that we're not participating in automatic GC
            vlibxml2.nodecache.removeNodeFromDocKey(<int> thisNode, <int> thisDoc)
            vlibxml2.nodecache.removeNodeFromDocKey(<int> curNode, <int> curDoc)

            vlibxml2.nodecache.compressDocKey(<int> curDoc)

            # unlink this node
            xmlUnlinkNode(thisNode)
            xmlUnlinkNode(curNode)

            # add a new childnode to the parentNode
            xmlAddChild(parentNode, curNode)

            # Manually assign the document pointer for the current node to 'this' document node
            curNode.doc = thisDoc

            # assign the curNode to self._xmlNodePtr
            self._xmlNodePtr = curNode

            vlibxml2.nodecache.cacheNewNode(self)

            # now manually destroy the old node
            xmlFreeNode(thisNode)
            xmlFreeDoc(curDoc)


        if debugMode:
            print "---End replaceNode"



    def xmlDoc(self):
        cdef xmlDocPtr docPtr
        cdef vlibxml2_tmpXMLDoc tmpDoc
        docPtr = self._xmlNodePtr.doc
        tmpDoc = vlibxml2_tmpXMLDoc()
        tmpDoc._xmlDocPtr = docPtr
        return wrapDoc(tmpDoc)

    def parent(self):
        '''
        return the parent of this node
        '''
        cdef vlibxml2_tmpXMLNode tmpNode
        if self._xmlNodePtr.parent.type == XML_DOCUMENT_NODE:
            # the parent is a document node!
            return None

        tmpNode = vlibxml2_tmpXMLNode()
        tmpNode._xmlNodePtr = self._xmlNodePtr.parent
        return wrapNode(tmpNode)

    def next(self):
        '''
        return the next sibling of this node
        '''
        cdef vlibxml2_tmpXMLNode tmpNode
        tmpNode = vlibxml2_tmpXMLNode()
        tmpNode._xmlNodePtr = self._xmlNodePtr.next
        return wrapNode(tmpNode)

    def prev(self):
        '''
        return the previous sibling of this node
        '''
        cdef vlibxml2_tmpXMLNode tmpNode
        tmpNode = vlibxml2_tmpXMLNode()
        tmpNode._xmlNodePtr = self._xmlNodePtr.prev
        return wrapNode(tmpNode)

    def children(self):
        '''
        return child nodes
        '''
        cdef xmlNodePtr childPtr
        cdef vlibxml2_tmpXMLNode tmpNode

        childPtr = self._xmlNodePtr.children

        nodeList = []
        while childPtr <> NULL:
            tmpNode = vlibxml2_tmpXMLNode()
            tmpNode._xmlNodePtr = childPtr
            resultNode = wrapNode(tmpNode)
            nodeList.append(resultNode)
            childPtr = childPtr.next

        return nodeList

    def setProp(self, char *key, char *value):
        '''
        Set attribute of hte xmlNode
        '''
        xmlSetProp(self._xmlNodePtr, <xmlChar *> key, <xmlChar *> value)

    def prop(self, char *value):
        '''
        get a location for america
        '''
        cdef char* buff
        buff = <char *> xmlGetProp(self._xmlNodePtr, <xmlChar *> value)
        if buff == NULL:
            return None
        result = str(buff)
        xmlFree(buff)
        return result

    def properties(self):
        '''
        Return a python dictionary for each of the attributes for this node
        '''
        cdef xmlAttr* prop
        cdef xmlChar* buff

        prop = self._xmlNodePtr.properties
        resultDict = {}
        while prop <> NULL:
            buff = xmlNodeGetContent(prop.children)
            value = str(<char *> buff)
            xmlFree(buff)
            resultDict[<char *> prop.name] = value
            prop = prop.next
        return resultDict


    def setContent(self, char *content):
        xmlNodeSetContent(self._xmlNodePtr, <xmlChar *>content)

    def content(self):
        cdef char *buff
        buff = <char *> xmlNodeGetContent(self._xmlNodePtr)

        if buff <> NULL:
            result = str(buff)
            xmlFree(buff)
            return result

    def __cmp__(self, other):
        return cmp(self.__hash__(), other.__hash__())


    def __str__(self):
        '''
        serialize the node - no formatting though
        '''
        cdef xmlBufferPtr buf
        buf = xmlBufferCreate()

        xmlNodeDump (buf, NULL, self._xmlNodePtr, 4, 0)
        result = str(<char *> buf.content)
        xmlBufferFree(buf)
        return result

    def __dealloc__(self):
        if debugMode:
            print "In dealloc for xmlNode"
        cdef xmlNodePtr nodePtr
        cdef xmlDocPtr docPtr

        nodePtr = self._xmlNodePtr

        docPtr = nodePtr.doc

        if vlibxml2.nodecache.hasCacheForDocKey(<int> docPtr):
            if vlibxml2.nodecache.hasDocForDocKey(<int> docPtr) == False and vlibxml2.nodecache.numNodesForDocKey(<int> docPtr) == 0:
                    del vlibxml2.nodecache._xmlCache[<int> docPtr]

                    if debugMode:
                        print "Auto Free doc: %d" % <int> docPtr
                    xmlFreeDoc(docPtr)

    def xpathEval(self, char *xpathExpr):
        '''
        simple xpath evaluation
        '''
        cdef vlibxml2_tmpXMLNode tmpNode
        cdef xmlNodePtr curNode
        cdef xmlNodeSetPtr nodesetval
        cdef xmlXPathContextPtr xpathCtx
        cdef xmlXPathObjectPtr xpathObject

        xpathCtx = xmlXPathNewContext(self._xmlNodePtr.doc)
        if (xpathCtx == NULL):
            raise "Error in xmlXPathNewContext\n"

        # manually override the nodePtr in the context with the current node
        # this will give us the expected behaviour for relative XPath searching
        xpathCtx.node = self._xmlNodePtr

        xpathObject = xmlXPathEvalExpression(<xmlChar *> xpathExpr, xpathCtx)
        xmlXPathFreeContext(xpathCtx)

        if (xpathObject == NULL):
            raise "Error in xmlXPathEvalExpression\n"

        nodesetval = xpathObject.nodesetval
        if ((nodesetval == NULL) or \
            (nodesetval.nodeNr == 0) or \
            (nodesetval.nodeTab == NULL)):
            xmlXPathFreeObject(xpathObject)
            return []

        # now we process the xpathObject

        retval = []
        if xpathObject:
            nodesetval = xpathObject.nodesetval
            for i from 0 <= i < nodesetval.nodeNr:

                tmpNode = vlibxml2_tmpXMLNode()
                tmpNode._xmlNodePtr = nodesetval.nodeTab[i]

                retval.append(wrapNode(tmpNode))
            xmlXPathFreeObject (xpathObject)
        return retval



cdef class vlibxml2_xmlDoc:
    cdef xmlDocPtr _xmlDocPtr

    def __hash__(self):
        return <int> self._xmlDocPtr

    def __cmp__(self, other):
        return cmp(self.__hash__(), other.__hash__())

    def setRootElement(self, vlibxml2_xmlNode cur):
        cdef vlibxml2_xmlDoc  tmpDoc

        if cur == None:
            # do nothing when we get None
            return

        # Grab the old root element
        oldRootElem = self.rootElement()
        oldDoc = cur.xmlDoc()

        # shuffle the caches around
        vlibxml2.nodecache.moveNodeToNewDoc(cur, <int> self._xmlDocPtr)

        # reset the root element
        xmlDocSetRootElement(self._xmlDocPtr, cur._xmlNodePtr)

        # now allocate a new doc for the old root element if necessary
        if oldRootElem is not None:
            tmpDoc = newDoc('1.0')
            tmpDoc.setRootElement(oldRootElem)


    def rootElement(self):
        cdef xmlNodePtr nodePtr
        cdef vlibxml2_xmlNode resultNode
        cdef vlibxml2_tmpXMLNode tmpNode

        nodePtr = xmlDocGetRootElement(self._xmlDocPtr)

        tmpNode = vlibxml2_tmpXMLNode()
        tmpNode._xmlNodePtr = nodePtr
        resultNode = wrapNode(tmpNode)

        return resultNode

    def xpathEval(self, char *xpathExpr):
        '''
        simple xpath evaluation
        '''
        return self.rootElement().xpathEval(xpathExpr)

    def __str__(self):
        '''
        Serialize the document - formatted mostly because it's easier to deal with.
        '''
        cdef unsigned char* xmlbuff
        cdef int buffersize
        xmlDocDumpFormatMemory(self._xmlDocPtr, &xmlbuff, &buffersize, 1)

        # copy out the char buffer into a GC managed Python string object
        result = str(<char *> xmlbuff)

        # now free the (char *) buffer
        xmlFree(xmlbuff)
        return result



    def __dealloc__(self):
        if <int> self._xmlDocPtr == -1:
            print "Don't need to dealloc this xmlDocPtr since it's -1"
            return

        if debugMode:
            print "In dealloc for xmlDoc"

        if vlibxml2.nodecache.hasDocForDocKey(<int> self._xmlDocPtr) == False and vlibxml2.nodecache.numNodesForDocKey(<int> self._xmlDocPtr) == 0:
            # free the C level xmlDoc structure
            if debugMode:
                print "Auto Free doc: %d" % <int> self._xmlDocPtr
            xmlFreeDoc(self._xmlDocPtr)

            # delete the xmlDocPtr entry in the xmlCache
            vlibxml2.nodecache.deleteDoc(<int> self._xmlDocPtr)
        else:
            vlibxml2.nodecache._xmlCache[<int> self._xmlDocPtr][0] = None


cdef class const_xmlElementType:
    def getXML_ATTRIBUTE_DECL(self): 
        return XML_ATTRIBUTE_DECL
    def getXML_ATTRIBUTE_NODE(self): 
        return XML_ATTRIBUTE_NODE
    def getXML_CDATA_SECTION_NODE(self): 
        return XML_CDATA_SECTION_NODE
    def getXML_COMMENT_NODE(self): 
        return XML_COMMENT_NODE
    def getXML_DOCB_DOCUMENT_NODE(self): 
        return XML_DOCB_DOCUMENT_NODE
    def getXML_DOCUMENT_FRAG_NODE(self): 
        return XML_DOCUMENT_FRAG_NODE
    def getXML_DOCUMENT_NODE(self): 
        return XML_DOCUMENT_NODE
    def getXML_DOCUMENT_TYPE_NODE(self): 
        return XML_DOCUMENT_TYPE_NODE
    def getXML_DTD_NODE(self): 
        return XML_DTD_NODE
    def getXML_ELEMENT_DECL(self): 
        return XML_ELEMENT_DECL
    def getXML_ELEMENT_NODE(self): 
        return XML_ELEMENT_NODE
    def getXML_ENTITY_DECL(self): 
        return XML_ENTITY_DECL
    def getXML_ENTITY_NODE(self): 
        return XML_ENTITY_NODE
    def getXML_ENTITY_REF_NODE(self): 
        return XML_ENTITY_REF_NODE
    def getXML_HTML_DOCUMENT_NODE(self): 
        return XML_HTML_DOCUMENT_NODE
    def getXML_NAMESPACE_DECL(self): 
        return XML_NAMESPACE_DECL
    def getXML_NOTATION_NODE(self): 
        return XML_NOTATION_NODE
    def getXML_PI_NODE(self): 
        return XML_PI_NODE
    def getXML_TEXT_NODE(self): 
        return XML_TEXT_NODE
    def getXML_XINCLUDE_END(self): 
        return XML_XINCLUDE_END
    def getXML_XINCLUDE_START(self): 
        return XML_XINCLUDE_START

