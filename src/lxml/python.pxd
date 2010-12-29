from cstd cimport FILE
cimport cython

cdef extern from "Python.h":
    ctypedef struct PyObject
    ctypedef struct PyThreadState
    cdef int INT_MAX
    cdef int PY_SSIZE_T_MAX
    cdef int PY_VERSION_HEX

    cdef void Py_INCREF(object o)
    cdef void Py_DECREF(object o)
    cdef void Py_XDECREF(PyObject* o)

    cdef FILE* PyFile_AsFile(object p)

    cdef bint PyUnicode_Check(object obj)
    cdef bint PyUnicode_CheckExact(object obj)
    cdef bint PyBytes_Check(object obj)
    cdef bint PyBytes_CheckExact(object obj)

    cdef cython.unicode PyUnicode_FromEncodedObject(object s, char* encoding,
                                                    char* errors)
    cdef bytes PyUnicode_AsEncodedString(object u, char* encoding,
                                         char* errors)
    cdef cython.unicode PyUnicode_FromFormat(char* format, ...) # Python 3
    cdef cython.unicode PyUnicode_Decode(char* s, Py_ssize_t size,
                                         char* encoding, char* errors)
    cdef cython.unicode PyUnicode_DecodeUTF8(char* s, Py_ssize_t size, char* errors)
    cdef cython.unicode PyUnicode_DecodeLatin1(char* s, Py_ssize_t size, char* errors)
    cdef bytes PyUnicode_AsUTF8String(object ustring)
    cdef bytes PyUnicode_AsASCIIString(object ustring)
    cdef char* PyUnicode_AS_DATA(object ustring)
    cdef Py_ssize_t PyUnicode_GET_DATA_SIZE(object ustring)
    cdef Py_ssize_t PyUnicode_GET_SIZE(object ustring)
    cdef bytes PyBytes_FromStringAndSize(char* s, Py_ssize_t size)
    cdef bytes PyBytes_FromFormat(char* format, ...)
    cdef Py_ssize_t PyBytes_GET_SIZE(object s)

    cdef object PyNumber_Int(object value)
    cdef Py_ssize_t PyInt_AsSsize_t(object value)

    cdef Py_ssize_t PyTuple_GET_SIZE(object t)
    cdef object PyTuple_GET_ITEM(object o, Py_ssize_t pos)

    cdef object PyList_New(Py_ssize_t index)
    cdef Py_ssize_t PyList_GET_SIZE(object l)
    cdef object PyList_GET_ITEM(object l, Py_ssize_t index)
    cdef void PyList_SET_ITEM(object l, Py_ssize_t index, object value)
    cdef int PyList_Insert(object l, Py_ssize_t index, object o) except -1
    cdef object PyList_AsTuple(object l)
    cdef void PyList_Clear(object l)

#    cdef int PyDict_SetItemString(object d, char* key, object value) except -1
#    cdef int PyDict_SetItem(object d, object key, object value) except -1
    cdef PyObject* PyDict_GetItemString(object d, char* key)
    cdef PyObject* PyDict_GetItem(object d, object key)
#    cdef int PyDict_DelItem(object d, object key) except -1
    cdef void PyDict_Clear(object d)
#    cdef object PyDict_Copy(object d)
    cdef object PyDictProxy_New(object d)
    # cdef int PyDict_Contains(object d, object key) except -1 # Python 2.4+
    cdef Py_ssize_t PyDict_Size(object d)
    cdef object PySequence_List(object o)
    cdef object PySequence_Tuple(object o)

    cdef bint PyDict_Check(object instance)
    cdef bint PyList_Check(object instance)
    cdef bint PyTuple_Check(object instance)
    cdef bint PyNumber_Check(object instance)
    cdef bint PyBool_Check(object instance)
    cdef bint PySequence_Check(object instance)
    cdef bint PyType_Check(object instance)
    cdef bint PyTuple_CheckExact(object instance)
    cdef bint PySlice_Check(object instance)

    cdef int _PyEval_SliceIndex(object value, Py_ssize_t* index) except 0
    cdef int PySlice_GetIndicesEx(slice slice, Py_ssize_t length,
                                  Py_ssize_t *start, Py_ssize_t *stop, Py_ssize_t *step,
                                  Py_ssize_t *slicelength) except -1

    cdef int PyObject_SetAttr(object o, object name, object value)
    cdef object PyObject_RichCompare(object o1, object o2, int op)
    cdef int PyObject_RichCompareBool(object o1, object o2, int op)

#    object PyWeakref_NewRef(object ob, PyObject* callback)
#    PyObject* PyWeakref_GET_OBJECT(object ref)

    cdef void* PyMem_Malloc(size_t size)
    cdef void* PyMem_Realloc(void* p, size_t size)
    cdef void PyMem_Free(void* p)

    # these two always return NULL to pass on the exception
    cdef object PyErr_NoMemory()
    cdef object PyErr_SetFromErrno(object type)

    cdef PyThreadState* PyEval_SaveThread()
    cdef void PyEval_RestoreThread(PyThreadState* state)
    cdef PyObject* PyThreadState_GetDict()

    # some handy functions
    cdef int callable "PyCallable_Check" (object obj)
    cdef char* _cstr "PyBytes_AS_STRING" (object s)

    # Py_buffer related flags
    cdef int PyBUF_SIMPLE
    cdef int PyBUF_WRITABLE
    cdef int PyBUF_LOCK
    cdef int PyBUF_FORMAT
    cdef int PyBUF_ND
    cdef int PyBUF_STRIDES
    cdef int PyBUF_C_CONTIGUOUS
    cdef int PyBUF_F_CONTIGUOUS
    cdef int PyBUF_ANY_CONTIGUOUS
    cdef int PyBUF_INDIRECT

cdef extern from "pythread.h":
    ctypedef void* PyThread_type_lock
    cdef PyThread_type_lock PyThread_allocate_lock()
    cdef void PyThread_free_lock(PyThread_type_lock lock)
    cdef int  PyThread_acquire_lock(PyThread_type_lock lock, int mode) nogil
    cdef void PyThread_release_lock(PyThread_type_lock lock)
    cdef long PyThread_get_thread_ident()

    ctypedef enum __WaitLock:
        WAIT_LOCK
        NOWAIT_LOCK

cdef extern from "etree_defs.h": # redefines some functions as macros
    cdef bint _isString(object obj)
    cdef char* _fqtypename(object t)
    cdef object PY_NEW(object t)
    cdef bint IS_PYTHON3
