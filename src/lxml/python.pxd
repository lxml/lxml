from tree cimport FILE

cdef extern from "Python.h":
    ctypedef struct PyObject
    
    cdef FILE* PyFile_AsFile(PyObject* p)
    cdef int PyFile_Check(object p)
    cdef object PyFile_Name(object p)

    cdef int PyUnicode_Check(object obj)
    cdef int PyString_Check(object obj)

    cdef object PyUnicode_FromEncodedObject(object s, char* encoding,
                                            char* errors)
    cdef object PyUnicode_DecodeUTF8(char* s, int size, char* errors)
    cdef object PyUnicode_AsUTF8String(object ustring)
    cdef object PyString_FromStringAndSize(char* s, int size)
    cdef object PyString_FromString(char* s)
    cdef object PyString_FromFormat(char* format, ...)
    cdef object PyBool_FromLong(long value)

    cdef int PyList_GET_SIZE(object l)
    cdef int PyList_Append(object l, object obj)
    cdef int PyList_Reverse(object l)
    cdef int PyDict_SetItemString(object d, char* key, object value)
    cdef int PyDict_SetItem(object d, object key, object value)
    cdef PyObject* PyDict_GetItemString(object d, char* key)
    cdef PyObject* PyDict_GetItem(object d, object key)
    cdef int PyDict_DelItem(object d, object key)
    cdef int PyDict_Clear(object d)
    cdef object PyList_AsTuple(object o)
    cdef object PySequence_List(object o)
    cdef object PySequence_Tuple(object o)
    cdef object PyTuple_GET_ITEM(object o, int pos)

    cdef int PyNumber_Check(object instance)
    cdef int PyBool_Check(object instance)
    cdef int PySequence_Check(object instance)
    cdef int PyType_Check(object instance)

cdef extern from "etree.h": # redefines some functions as macros
    cdef int isinstance(object instance, object classes)
    cdef int issubclass(object derived,  object superclasses)
    cdef int hasattr(object obj, object attr)
    cdef int callable(object obj)
    cdef object str(object obj)
    cdef object iter(object obj)
    cdef char* _cstr(object s)
