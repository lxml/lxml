#
# Forward declarations of vlibxml2 classes
#

cdef class vlibxml2_xmlNode
cdef class vlibxml2_xmlDoc

cdef extern from "libxml/tree.h":
    cdef struct _xmlDoc 
    cdef struct _xmlNode 


