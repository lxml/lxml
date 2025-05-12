
cimport cython

cdef double _calculate_ratio(Py_ssize_t matches, Py_ssize_t length)

cdef class SequenceMatcher:
    cdef public object a
    cdef public object b
    cdef dict b2j
    cdef dict fullbcount
    cdef list matching_blocks
    cdef list opcodes
    cdef object isjunk
    cdef set bjunk
    cdef set bpopular
    cdef bint autojunk

    @cython.locals(b2j=dict, j2len=dict, newj2len=dict,
                   besti=Py_ssize_t, bestj=Py_ssize_t, bestsize=Py_ssize_t,
                   ahi=Py_ssize_t, bhi=Py_ssize_t,
                   i=Py_ssize_t, j=Py_ssize_t, k=Py_ssize_t)
    cpdef find_longest_match(self, Py_ssize_t alo=*, ahi_=*, Py_ssize_t blo=*, bhi_=*)

    @cython.locals(matches=Py_ssize_t)
    cpdef quick_ratio(self)

    @cython.locals(la=Py_ssize_t, lb=Py_ssize_t)
    cpdef real_quick_ratio(self)
