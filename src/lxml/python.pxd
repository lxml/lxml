from cstd cimport FILE
cimport cython

from libc.limits cimport INT_MAX

from cpython cimport (
    PyObject,
    PyThreadState,
    PY_VERSION_HEX,

    Py_INCREF,
    Py_DECREF,
    Py_XDECREF,

    PyBytes_Check,
    PyBytes_CheckExact,
    PyBytes_FromStringAndSize,
    PyBytes_FromFormat,
    PyBytes_GET_SIZE,

    PyUnicode_Check,
    PyUnicode_CheckExact,
    PyUnicode_AS_DATA,
    PyUnicode_GET_DATA_SIZE,
    PyUnicode_GET_SIZE,

    PyNumber_Int,
    PyInt_AsSsize_t,

#   PyDict_SetItemString,
#   PyDict_SetItem,
    PyDict_GetItemString,
    PyDict_GetItem,
#   PyDict_DelItem,
    PyDict_Clear,
#   PyDict_Copy,
    PyDictProxy_New,
#   PyDict_Contains, # Python 2.4+

    PyDict_Check,
    PyList_Check,
    PyTuple_Check,
    PyNumber_Check,
    PyBool_Check,
    PySequence_Check,
    PyType_Check,
    PyTuple_CheckExact,

    PyMem_Malloc,
    PyMem_Realloc,
    PyMem_Free,

    PyThread_type_lock,
    PyThread_allocate_lock,
    PyThread_free_lock,
    PyThread_acquire_lock,
    PyThread_get_thread_ident,
)

cdef extern from "Python.h":
    cdef int PY_SSIZE_T_MAX

    cdef FILE* PyFile_AsFile(object p)

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

    cdef Py_ssize_t PyTuple_GET_SIZE(object t)
    cdef object PyTuple_GET_ITEM(object o, Py_ssize_t pos)

    cdef object PyList_New(Py_ssize_t index)
    cdef Py_ssize_t PyList_GET_SIZE(object l)
    cdef object PyList_GET_ITEM(object l, Py_ssize_t index)
    cdef void PyList_SET_ITEM(object l, Py_ssize_t index, object value)
    cdef int PyList_Insert(object l, Py_ssize_t index, object o) except -1
    cdef object PyList_AsTuple(object l)
    cdef void PyList_Clear(object l)

    cdef Py_ssize_t PyDict_Size(object d)
    cdef object PySequence_List(object o)
    cdef object PySequence_Tuple(object o)

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
    cdef void PyThread_release_lock(PyThread_type_lock lock)

    ctypedef enum __WaitLock:
        WAIT_LOCK
        NOWAIT_LOCK

cdef extern from "etree_defs.h": # redefines some functions as macros
    cdef bint _isString(object obj)
    cdef char* _fqtypename(object t)
    cdef object PY_NEW(object t)
    cdef bint IS_PYTHON3
