from libc cimport stdio
from libc.string cimport const_char
cimport cython


cdef extern from "Python.h":
    """
    #if defined(Py_LIMITED_API)
      #define LXML_IN_LIMITED_API 1
    #else
      #define LXML_IN_LIMITED_API 0
    #endif

    #if defined(Py_LIMITED_API) || PY_VERSION_HEX >= 0x030C0000
      #undef PyUnicode_IS_READY
      #define PyUnicode_IS_READY(s)  (1)
      #undef PyUnicode_READY
      #define PyUnicode_READY(s)  (0)
      #undef PyUnicode_AS_DATA
      #define PyUnicode_AS_DATA(s)  (0)
      #undef PyUnicode_GET_DATA_SIZE
      #define PyUnicode_GET_DATA_SIZE(s)  (0)
      #undef PyUnicode_GET_SIZE
      #define PyUnicode_GET_SIZE(s)  (0)
    #endif

    #if defined(Py_LIMITED_API)
      #undef PyUnicode_MAX_CHAR_VALUE
      #define PyUnicode_MAX_CHAR_VALUE(s)  (0)
      #undef PyUnicode_GET_LENGTH
      #define PyUnicode_GET_LENGTH(s)  (0)
      #undef PyUnicode_KIND
      #define PyUnicode_KIND(s)  (0)
      #undef PyUnicode_DATA
      #define PyUnicode_DATA(s)  (0)
    #endif

    #if !defined(Py_mod_gil) && (PY_VERSION_HEX < 0x030d0000 || defined(Py_LIMITED_API) && Py_LIMITED_API < 0x030d0000)
      #define Py_mod_gil 4
      #define Py_MOD_GIL_USED  NULL
      #define Py_MOD_GIL_NOT_USED  NULL
    #endif

    """

    ctypedef struct PyObject
    cdef const Py_ssize_t PY_SSIZE_T_MIN
    cdef const Py_ssize_t PY_SSIZE_T_MAX
    cdef const int PY_VERSION_HEX
    cdef const bint IN_LIMITED_API "LXML_IN_LIMITED_API"

    cdef void Py_INCREF(object o)
    cdef void Py_DECREF(object o)
    cdef void Py_XDECREF(PyObject* o)

    cdef stdio.FILE* PyFile_AsFile(object p)

    # PEP 393
    cdef bint PyUnicode_IS_READY(object u)
    cdef Py_ssize_t PyUnicode_GET_LENGTH(object u)
    cdef int PyUnicode_KIND(object u)
    cdef void* PyUnicode_DATA(object u)

    cdef bytes PyUnicode_AsEncodedString(object u, char* encoding,
                                         char* errors)
    cdef cython.unicode PyUnicode_FromFormat(char* format, ...) # Python 3
    cdef cython.unicode PyUnicode_Decode(char* s, Py_ssize_t size,
                                         char* encoding, char* errors)
    cdef cython.unicode PyUnicode_DecodeUTF8(char* s, Py_ssize_t size, char* errors)
    cdef cython.unicode PyUnicode_DecodeLatin1(char* s, Py_ssize_t size, char* errors)
    cdef object PyUnicode_RichCompare(object o1, object o2, int op)
    cdef bytes PyUnicode_AsUTF8String(object ustring)
    cdef bytes PyUnicode_AsASCIIString(object ustring)
    cdef char* PyUnicode_AS_DATA(object ustring)
    cdef Py_ssize_t PyUnicode_GET_DATA_SIZE(object ustring)
    cdef Py_ssize_t PyUnicode_GET_SIZE(object ustring)
    cdef Py_UCS4 PyUnicode_MAX_CHAR_VALUE(object ustring)
    cdef bytes PyBytes_FromStringAndSize(char* s, Py_ssize_t size)
    cdef bytes PyBytes_FromFormat(char* format, ...)
    cdef Py_ssize_t PyBytes_GET_SIZE(object s)

    cdef object PyNumber_Int(object value)

    cdef Py_ssize_t PyTuple_GET_SIZE(object t)
    cdef object PyTuple_GET_ITEM(object o, Py_ssize_t pos)

    cdef object PyList_New(Py_ssize_t index)
    cdef Py_ssize_t PyList_GET_SIZE(object l)
    cdef object PyList_GET_ITEM(object l, Py_ssize_t index)
    cdef void PyList_SET_ITEM(object l, Py_ssize_t index, object value)
    cdef int PyList_Insert(object l, Py_ssize_t index, object o) except -1
    cdef object PyList_AsTuple(object l)

    cdef PyObject* PyDict_GetItemString(object d, char* key)
    cdef PyObject* PyDict_GetItem(object d, object key)
    cdef PyObject* PyDict_GetItemWithError(object d, object key) except? NULL
    cdef object PyDict_GetItemRef(object d, object key)
    cdef object PyDictProxy_New(object d)
    cdef object PySequence_List(object o)
    cdef object PySequence_Tuple(object o)

    cdef bint PyNumber_Check(object instance)
    cdef bint PySequence_Check(object instance)
    cdef bint PyType_Check(object instance)
    cdef bint PyTuple_CheckExact(object instance)
    cdef bint PyIndex_Check(object instance)

    cdef int PySlice_GetIndicesEx(
            object slice, Py_ssize_t length,
            Py_ssize_t *start, Py_ssize_t *stop, Py_ssize_t *step,
            Py_ssize_t *slicelength) except -1

    cdef object PyObject_RichCompare(object o1, object o2, int op)

    PyObject* PyWeakref_NewRef(object ob, PyObject* callback) except NULL  # used for PyPy only
    object PyWeakref_LockObject(PyObject* ob) # PyPy only

    cdef void* PyMem_Malloc(size_t size)
    cdef void* PyMem_Realloc(void* p, size_t size)
    cdef void PyMem_Free(void* p)

    const int Py_mod_gil
    const void* Py_MOD_GIL_USED
    const void* Py_MOD_GIL_NOT_USED

    ctypedef struct PyModuleDef_Slot:
        int slot
        void* value

    ctypedef struct PyModuleDef:
        PyModuleDef_Slot* m_slots

    cdef PyModuleDef* PyModule_GetDef(object module) except? NULL

    # always returns NULL to pass on the exception
    cdef object PyErr_SetFromErrno(object type)
    cdef void PyException_SetContext(object exception, object context)
    cdef PyObject* PyException_GetContext(object exception)

    cdef PyObject* PyThreadState_GetDict()

    # some handy functions
    cdef const char* _cstr "__Pyx_PyBytes_AsString" (object s)
    cdef const char* __cstr "__Pyx_PyBytes_AsString" (PyObject* s)

    # Py_buffer related flags
    cdef const int PyBUF_SIMPLE
    cdef const int PyBUF_WRITABLE
    cdef const int PyBUF_LOCK
    cdef const int PyBUF_FORMAT
    cdef const int PyBUF_ND
    cdef const int PyBUF_STRIDES
    cdef const int PyBUF_C_CONTIGUOUS
    cdef const int PyBUF_F_CONTIGUOUS
    cdef const int PyBUF_ANY_CONTIGUOUS
    cdef const int PyBUF_INDIRECT


cdef extern from *:
    """
    #if !CYTHON_COMPILING_IN_CPYTHON || PY_VERSION_HEX < 0x030e0000 || !defined(Py_GIL_DISABLED)
        #define PyUnstable_EnableTryIncRef(obj)
        #define PyUnstable_TryIncRef(obj) (Py_INCREF(obj), 1)
        #define __lxml_HAS_TryIncRef (0)
    #else
        #define __lxml_HAS_TryIncRef (1)
    #endif
    """
    cdef const bint HAS_TryIncRef "__lxml_HAS_TryIncRef"

    void PyUnstable_EnableTryIncRef(object o)
    # Enables subsequent uses of PyUnstable_TryIncRef() on obj.
    # The caller must hold a strong reference to obj when calling this.
    #
    # Added in CPython 3.14.

    bint PyUnstable_TryIncRef(PyObject *o)
    # Increments the reference count of obj if it is not zero.
    # Returns 1 if the object’s reference count was successfully incremented.
    # Otherwise, this function returns 0.
    #
    # PyUnstable_EnableTryIncRef() must have been called earlier on obj
    # or this function may spuriously return 0 in the free threading build.
    #
    # Added in CPython 3.14.


cdef extern from "pythread.h":
    ctypedef void* PyThread_type_lock
    cdef PyThread_type_lock PyThread_allocate_lock()
    cdef void PyThread_free_lock(PyThread_type_lock lock)
    cdef int  PyThread_acquire_lock(PyThread_type_lock lock, int mode) nogil
    cdef void PyThread_release_lock(PyThread_type_lock lock) nogil
    cdef unsigned long PyThread_get_thread_ident()

    ctypedef enum __WaitLock:
        WAIT_LOCK
        NOWAIT_LOCK

cdef extern from "etree_defs.h": # redefines some functions as macros
    cdef void* lxml_malloc(size_t count, size_t item_size)
    cdef void* lxml_realloc(void* mem, size_t count, size_t item_size)
    cdef void lxml_free(void* mem)
    cdef void* lxml_unpack_xmldoc_capsule(object capsule, bint* is_owned) except? NULL
    cdef bint _isString(object obj)
    cdef str _typename "__lxml_typename" (object t)
    cdef str _fqtypename "__lxml_fqtypename" (object t)
    cdef bint IS_PYPY
    cdef object PyOS_FSPath(object obj)


cdef extern from *:
    """
    #ifndef PY_BIG_ENDIAN

    #ifdef _MSC_VER
    typedef unsigned __int32 uint32_t;
    #else
    #include <stdint.h>
    #endif

    static CYTHON_INLINE int _lx__is_big_endian(void) {
        union {uint32_t i; char c[4];} x = {0x01020304};
        return x.c[0] == 1;
    }
    #define PY_BIG_ENDIAN _lx__is_big_endian()
    #endif
    """
    cdef bint PY_BIG_ENDIAN  # defined in later Py3.x versions
