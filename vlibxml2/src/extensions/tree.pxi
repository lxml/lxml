
cdef extern from "libxml/tree.h":

    ctypedef unsigned char xmlChar

    cdef struct _xmlAttr:
        void *_private             # application data 
        xmlChar *name              # the name of the property 
        _xmlNode *children         # the value of the property 
        _xmlNode *last             # NULL 
        _xmlNode *parent           # child->parent link 
        _xmlAttr *next             # next sibling link  
        _xmlAttr *prev             # previous sibling link  
        _xmlDoc  *doc              # the containing document 
        
    ctypedef _xmlAttr xmlAttr
    ctypedef xmlAttr *xmlAttrPtr

    cdef struct _xmlNs
    ctypedef _xmlNs xmlNs
    ctypedef xmlNs *xmlNsPtr

    cdef enum xmlElementType:
        XML_ATTRIBUTE_DECL
        XML_ATTRIBUTE_NODE
        XML_CDATA_SECTION_NODE
        XML_COMMENT_NODE
        XML_DOCB_DOCUMENT_NODE
        XML_DOCUMENT_FRAG_NODE
        XML_DOCUMENT_NODE
        XML_DOCUMENT_TYPE_NODE
        XML_DTD_NODE
        XML_ELEMENT_DECL
        XML_ELEMENT_NODE
        XML_ENTITY_DECL
        XML_ENTITY_NODE
        XML_ENTITY_REF_NODE
        XML_HTML_DOCUMENT_NODE
        XML_NAMESPACE_DECL
        XML_NOTATION_NODE
        XML_PI_NODE
        XML_TEXT_NODE
        XML_XINCLUDE_END
        XML_XINCLUDE_START

    cdef struct _xmlNode:
        xmlChar *name                                               #  the name of the node, or the entity
        _xmlNode *children                                          #  parent->childs link
        _xmlNode *last                                              #  last child link
        _xmlNode *parent                                            #  child->parent link
        _xmlNode *next                                              #  next sibling link 
        _xmlNode *prev                                              #  previous sibling link 
        _xmlDoc *doc                                                #  the containing document End of common part
        xmlChar *content                                            #  the content 
        xmlElementType   type                                       # type number, must be second!
        _xmlAttr *properties                                        # properties list 

###

    ctypedef _xmlNode xmlNode
    ctypedef xmlNode *xmlNodePtr

    cdef struct _xmlDoc:
        char *name                                                  #  name/filename/URI of the document
        _xmlNode *children                                          #  the document tree
        _xmlNode *last                                              #  last child link
        _xmlNode *parent                                            #  child->parent link
        _xmlNode *next                                              #  next sibling link 
        _xmlNode *prev                                              #  previous sibling link 
        int compression                                             #  level of zlib compression
        int standalone                                              #  standalone document (no external refs)
        xmlChar *version                                            #  the XML version string
        xmlChar *encoding                                           #  external initial encoding, if any
        
    ctypedef _xmlDoc xmlDoc
    ctypedef xmlDoc *xmlDocPtr


    xmlNodePtr xmlNewNode (xmlNsPtr, xmlChar *)

    xmlNodePtr xmlReplaceNode(xmlNodePtr old, xmlNodePtr cur)
    xmlNodePtr xmlAddSibling(xmlNodePtr cur, xmlNodePtr elem)
    xmlNodePtr xmlAddNextSibling(xmlNodePtr cur, xmlNodePtr elem)
    xmlNodePtr xmlAddPrevSibling(xmlNodePtr cur, xmlNodePtr elem)

    xmlDocPtr xmlNewDoc(xmlChar *)
    void xmlFreeDoc(xmlDocPtr cur)

    cdef struct xmlBuffer:
        xmlChar *content    # The buffer content UTF8
        unsigned int use    # buffer size used
        unsigned int size   # buffer size 
    ctypedef xmlBuffer *xmlBufferPtr


    int xmlNodeDump (xmlBufferPtr buf, xmlDocPtr doc, xmlNodePtr cur, int level, int format)
    void xmlDocDumpFormatMemory (xmlDocPtr cur, xmlChar **mem, int *size, int format)
    void xmlFreeNode (xmlNodePtr cur)
    void xmlFreeNodeList (xmlNodePtr cur)
    void xmlUnlinkNode (xmlNodePtr cur)
    xmlNodePtr xmlAddChild(xmlNodePtr parent, xmlNodePtr cur)
    xmlNodePtr xmlDocGetRootElement (xmlDocPtr doc)
    int xmlSaveFormatFileEnc(char *filename, xmlDocPtr cur,char *encoding, int format)

    xmlNodePtr xmlDocSetRootElement(xmlDocPtr doc, xmlNodePtr root)
    xmlNodePtr xmlNewChild(xmlNodePtr parent, xmlNsPtr ns, xmlChar *name, xmlChar *content)
    xmlAttrPtr xmlNewProp(xmlNodePtr node, xmlChar *name, xmlChar *value)
    xmlNodePtr xmlNewText(xmlChar *content)
    xmlAttrPtr xmlSetProp  (xmlNodePtr node, xmlChar *name, xmlChar *value)
    xmlChar*   xmlGetProp  (xmlNodePtr node, xmlChar *name)
    void       xmlNodeSetContent(xmlNodePtr cur, xmlChar *content)
    xmlChar *  xmlNodeGetContent (xmlNodePtr cur)
    xmlChar *  xmlNodeListGetString (xmlDocPtr doc, xmlNodePtr list, int inLine)
