'''
Because of the nature of libxml2, we need to actually create temporary Python wrappers
for c-xmlNode and c-xmlDoc pointers.

The main reason for this is to be able to create a Python object that has a
unique hash value (based on the int value of the 32-bit xmlNodePtr or xmlDocPtr).
Once we have a Python object we can check if a prior reference to this pointer already
exists.

If we do have a reference, then we simply garbage collect the temporary
Python wrapper, but we do _not_ deallocate the underlying c-xmlNodePtr or c-xmlDocPtr.

On the other hand, if we do _not_ have a reference, then we convert the temporary
Python wrapper into something more permanent so that we can later do garbage collection
on the underlying c-xmlNodePtr or c-xmlDocPtr
'''


cdef class vlibxml2_tmpXMLNode:
    '''
    basic wrapper class for c-xmlNodePtr
    '''
    cdef xmlNodePtr _xmlNodePtr

cdef class vlibxml2_tmpXMLDoc:
    '''
    basic wrapper class for c-xmlDocPtr
    '''
    cdef xmlDocPtr _xmlDocPtr



