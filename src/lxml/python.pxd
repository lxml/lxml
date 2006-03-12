from tree cimport FILE

cdef extern from "Python.h":
    ctypedef struct PyObject
    
    cdef FILE* PyFile_AsFile(PyObject* p)
    cdef int PyFile_Check(object p)
    cdef object PyFile_Name(object p)

    cdef int PyUnicode_Check(object obj)
    cdef int PyString_Check(object obj)

    cdef object PyUnicode_DecodeUTF8(char* s, int size, char* errors)
    cdef object PyUnicode_AsUTF8String(object ustring)
    cdef object PyString_FromStringAndSize(char* s, int size)
    cdef object PyString_FromString(char* s)
    cdef object PyString_FromFormat(char* format, ...)

    cdef int PyList_Append(object l, object obj)
    cdef int PyDict_SetItemString(object d, char* key, object value)
    cdef PyObject* PyDict_GetItemString(object d, char* key)
    cdef PyObject* PyDict_GetItem(object d, object key)

    cdef int PyObject_IsInstance(object instance, object classes)
    cdef int PyObject_HasAttrString(object obj, char* attr)
