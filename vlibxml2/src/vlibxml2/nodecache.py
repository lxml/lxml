import weakref, sets

'''
The nodeCache is managed has a structure has the following structure:

_nodeCache = {
    (int)xmlDocPtr : [ weakref.ref(PyXMLDocWrapper),
                       weakref.WeakValueDict{ (int)xmlNodePtr: PyXMLNodeWrapper,
                                              (int)xmlNodePtr: PyXMLNodeWrapper,
                                            }
                     ]
    }

'''

_xmlCache = {}

def size():
    '''
    Number of cached documents
    '''
    return len(_xmlCache)

def dumpCache():
    '''
    Just give a visual dump of the nodecache to see what's going on inside
    '''
    for docKey in _xmlCache.keys():
        print "--DocKey[%d]" % docKey
        print "\tHas reference to document: [%s]" % hasDocForDocKey(docKey)
        for nodeKey in _xmlCache[docKey][1].keys():
            print "\t\tNodeKey[%d]" % nodeKey

###
### Doc management
###

def clear():
    _xmlCache.clear()

def moveNodeToNewDoc(node, newDocKey):
    '''
    Move a node from one document's cache to another document's node cache.
    '''
    nodeKey = node.__hash__()
    oldDocKey = node.xmlDoc().__hash__()
    if oldDocKey == newDocKey:
        return
    _xmlCache[newDocKey][1][nodeKey] = node
    del _xmlCache[oldDocKey][1][nodeKey]

    if numNodesForDocKey(oldDocKey) == 0 and hasDocForDocKey(oldDocKey) == False:
        del _xmlCache[oldDocKey]

def hasCacheForDocKey(docKey):
    return _xmlCache.has_key(docKey)

def hasDocForDocKey(docKey):
    '''
    existence of a xmlDoc wrapper given a docKey (int cast of the xmlDoc ptr)
    '''
    if _xmlCache.has_key(docKey):
        if _xmlCache[docKey][0] is not None:
            return True
    return False

def docForDocKey(docKey):
    '''
    retrieve an xmlDoc given a key (int cast of the xmlDoc ptr)
    '''
    docRef = _xmlCache[docKey][0]
    doc = docRef()
    return doc

def initCacheForDocKey(docKey):
    if not _xmlCache.has_key(docKey):
        _xmlCache[docKey] = [None, weakref.WeakValueDictionary() ]

def cacheNewDoc(newDoc):
    '''
    Add xmlDoc to the xmlCache
    '''
    if hasDocForDocKey(newDoc.__hash__()):
        raise "Already caching this doc!"
    else:
        if not _xmlCache.has_key(newDoc.__hash__()):
            # setup the list with [xmlDoc, xmlNode(s)]
            _xmlCache[newDoc.__hash__()] = [None, weakref.WeakValueDictionary() ]
    _xmlCache[newDoc.__hash__()][0] = weakref.ref(newDoc, deallocDocCallback)

###
### Node management
###

def numNodesForDocKey(docKey):
    return len(_xmlCache[docKey][1])

def nodesForDocKey(docKey):
    return _xmlCache[docKey][1]

def hasNode(nodeKey, docKey):
    if _xmlCache.has_key(docKey):
        if _xmlCache[docKey][1].has_key(nodeKey):
            return True
    return False

def nodeForKey(nodeKey, docKey):
    if hasNode(nodeKey, docKey):
        return _xmlCache[docKey][1][nodeKey]
    return None

def cacheNewNode(newNode):
    nodeKey = newNode.__hash__()
    doc = newNode.xmlDoc()
    docKey  = doc.__hash__()
    if hasNode(nodeKey, docKey):
        raise "Already caching this node!"
    if _xmlCache.has_key(docKey):
        _xmlCache[docKey][1][nodeKey] = newNode
    else:
        raise "This document is not in the cache yet! DocKey[%d]" % docKey


def compressDocKey(docKey):
    '''
    Delete the docKey from the cache if there is no node in this graph
    '''
    # Delete the entry for curDoc if there is nothing left in the cache
    if hasDocForDocKey(docKey) == 0 and numNodesForDocKey(docKey) == 0:
        del _xmlCache[docKey]

def removeNodeFromDocKey(nodeKey, docKey):
    '''
    remove a node from the cache. 

    return True if the node was found, False if no node was removed
    '''
    docCache = _xmlCache.get(docKey, None)
    if docCache is not None:
        if docCache[1].has_key(nodeKey):
            del docCache[1][nodeKey]
            return True
    return False
    

###
### Deallocation callback functions
###

def deallocDocCallback(xmlDocRef):
    '''
    _nodeCache = {
        555: [ weakref.ref(None),
               weakref.WeakValueDict{ (int)xmlNodePtr: PyXMLNodeWrapper,
                                      (int)xmlNodePtr: PyXMLNodeWrapper,
                                    }
             ]
        }
    '''

    garbageCollect = False

    for docKey in _xmlCache.keys():
        if _xmlCache[docKey][0] == xmlDocRef:
            _xmlCache[docKey][0] = None
            return
    raise "Can't find xmlDoc to destroy!"

def deallocNodeCallback(xmlNode):
    garbageCollect = False
    xmlDoc = self.xmlDoc()
    docKey = doc.__hash__()
    if len(_nodeCache[docKey][1]) == 1 and _nodeCache[docKey][0] is None:
        # we're the last entry point into this graph of nodes
        garbageCollect = True

    if garbageCollect:
        xmlDoc.free()
        del _xmlCache[docKey]


def deleteDoc(docKey):
    if _xmlCache.has_key(docKey):
        del _xmlCache[docKey]

