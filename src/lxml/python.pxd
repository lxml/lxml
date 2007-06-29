from tree cimport FILE

cdef extern from "Python.h":
    ctypedef struct PyObject
    ctypedef struct PyThreadState
    ctypedef int size_t
    ctypedef int Py_ssize_t
    cdef int INT_MAX
    cdef int PY_SSIZE_T_MAX

    cdef void Py_INCREF(object o)
    cdef void Py_DECREF(object o)

    cdef FILE* PyFile_AsFile(object p)
    cdef int PyFile_Check(object p)
    cdef object PyFile_Name(object p)

    cdef int PyUnicode_Check(object obj)
    cdef int PyString_Check(object obj)

    cdef object PyUnicode_FromEncodedObject(object s, char* encoding,
                                            char* errors)
    cdef object PyUnicode_AsEncodedString(object u, char* encoding,
                                          char* errors)
    cdef object PyUnicode_Decode(char* s, Py_ssize_t size,
                                 char* encoding, char* errors)
    cdef object PyUnicode_DecodeUTF8(char* s, Py_ssize_t size, char* errors)
    cdef object PyUnicode_AsUTF8String(object ustring)
    cdef char* PyUnicode_AS_DATA(object ustring)
    cdef Py_ssize_t PyUnicode_GET_DATA_SIZE(object ustring)
    cdef object PyString_FromStringAndSize(char* s, Py_ssize_t size)
    cdef object PyString_FromString(char* s)
    cdef object PyString_FromFormat(char* format, ...)
    cdef Py_ssize_t PyString_GET_SIZE(object s)

    cdef object PyBool_FromLong(long value)
    cdef object PyNumber_Int(object value)
    cdef Py_ssize_t PyInt_AsSsize_t(object value)

    cdef Py_ssize_t PyTuple_GET_SIZE(object t)
    cdef object PyTuple_GET_ITEM(object o, Py_ssize_t pos)

    cdef Py_ssize_t PyList_GET_SIZE(object l)
    cdef object PyList_GET_ITEM(object l, Py_ssize_t index)
    cdef int PyList_Append(object l, object obj) except -1
    cdef int PyList_Reverse(object l) except -1
    cdef int PyList_Insert(object l, Py_ssize_t index, object o) except -1
    cdef object PyList_AsTuple(object l)
    cdef void PyList_Clear(object l)

    cdef int PyDict_SetItemString(object d, char* key, object value) except -1
    cdef int PyDict_SetItem(object d, object key, object value) except -1
    cdef PyObject* PyDict_GetItemString(object d, char* key)
    cdef PyObject* PyDict_GetItem(object d, object key)
    cdef int PyDict_DelItem(object d, object key) except -1
    cdef void PyDict_Clear(object d)
    cdef object PyDict_Copy(object d)
    cdef Py_ssize_t PyDict_Size(object d)
    cdef object PySequence_List(object o)
    cdef object PySequence_Tuple(object o)

    cdef int PyDict_Check(object instance)
    cdef int PyList_Check(object instance)
    cdef int PyTuple_Check(object instance)
    cdef int PyNumber_Check(object instance)
    cdef int PyBool_Check(object instance)
    cdef int PySequence_Check(object instance)
    cdef int PyType_Check(object instance)
    cdef int PyTuple_CheckExact(object instance)

    cdef int PyObject_SetAttr(object o, object name, object value)
    cdef object PyObject_RichCompare(object o1, object o2, int op)
    cdef int PyObject_RichCompareBool(object o1, object o2, int op)

    cdef void* PyMem_Malloc(size_t size)
    cdef void* PyMem_Realloc(void* p, size_t size)
    cdef void PyMem_Free(void* p)

    # these two always return NULL to pass on the exception
    cdef object PyErr_NoMemory()
    cdef object PyErr_SetFromErrno(object type)

    ctypedef enum PyGILState_STATE:
        PyGILState_LOCKED
        PyGILState_UNLOCKED

    cdef PyGILState_STATE PyGILState_Ensure()
    cdef void PyGILState_Release(PyGILState_STATE state)
    cdef PyThreadState* PyEval_SaveThread()
    cdef void PyEval_RestoreThread(PyThreadState* state)
    cdef PyObject* PyThreadState_GetDict()

cdef extern from "pythread.h":
    ctypedef void* PyThread_type_lock
    cdef PyThread_type_lock PyThread_allocate_lock()
    cdef void PyThread_free_lock(PyThread_type_lock lock)
    cdef int  PyThread_acquire_lock(PyThread_type_lock lock, int mode)
    cdef void PyThread_release_lock(PyThread_type_lock lock)
    cdef long PyThread_get_thread_ident()

    ctypedef enum __WaitLock:
        WAIT_LOCK
        NOWAIT_LOCK

cdef extern from "etree_defs.h": # redefines some functions as macros
    cdef int _isString(object obj)
    cdef int isinstance(object instance, object classes)
    cdef int issubclass(object derived,  object superclasses)
    cdef int hasattr(object obj, object attr)
    cdef object getattr(object obj, object attr)
    cdef int callable(object obj)
    cdef object str(object obj)
    cdef object repr(object obj)
    cdef object iter(object obj)
    cdef char* _cstr(object s)
    cdef object PY_NEW(object t)
