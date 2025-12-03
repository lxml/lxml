"""Read-write lock implementation.
"""

cdef extern from * nogil:
    """
#include <pythread.h>
#include <stdint.h>

#ifndef LXML_ATOMICS_ENABLED
    #define LXML_ATOMICS_ENABLED 1
#endif

#ifndef LXML_LOCK_PERFORMANCE
    #define LXML_LOCK_PERFORMANCE 0
#endif

#define __lxml_atomic_int_type int32_t
#define __lxml_nonatomic_int_type int32_t

/* For standard C atomics, get the headers first so we have ATOMIC_INT_LOCK_FREE */
/* defined when we decide to use them. */
#if LXML_ATOMICS_ENABLED && (defined(__STDC_VERSION__) && \
                        (__STDC_VERSION__ >= 201112L) && \
                        !defined(__STDC_NO_ATOMICS__))
    #include <stdatomic.h>
#endif

#if LXML_ATOMICS_ENABLED && (defined(__STDC_VERSION__) && \
                        (__STDC_VERSION__ >= 201112L) && \
                        !defined(__STDC_NO_ATOMICS__) && \
                       ATOMIC_INT_LOCK_FREE == 2)
    /* C11 atomics are available and  ATOMIC_INT_LOCK_FREE is definitely on */
    /* Prefer this over pyatomics.h, which enforces strict memory ordering. We only need atomic operations. */
    #undef __lxml_atomic_int_type
    #define __lxml_atomic_int_type _Atomic __lxml_nonatomic_int_type

    #define __lxml_atomic_compare_exchange(value, expected, desired)  atomic_compare_exchange_weak((value), (expected), (desired))
    #define __lxml_atomic_add(value, arg)     atomic_fetch_add_explicit((value), (arg), memory_order_relaxed)
    #define __lxml_atomic_incr_relaxed(value) __lxml_atomic_add((value),  1)
    #define __lxml_atomic_decr_relaxed(value) __lxml_atomic_add((value), -1)
    #define __lxml_atomic_load(value)         atomic_load((value))

    #if defined(__lxml_DEBUG_ATOMICS) && defined(_MSC_VER)
        #pragma message ("Using standard C11 atomics")
    #elif defined(__lxml_DEBUG_ATOMICS)
        #warning "Using standard C11 atomics"
    #endif

#elif LXML_ATOMICS_ENABLED && defined(Py_ATOMIC_H)
    /* "Python.h" included "pyatomics.h" */

    #define __lxml_atomic_compare_exchange(value, expected, desired)  _Py_atomic_compare_exchange_int32((value), (expected), (desired))
    #define __lxml_atomic_add(value, arg)     _Py_atomic_add_int32((value), (arg))
    #define __lxml_atomic_incr_relaxed(value) __lxml_atomic_add((value),  1)
    #define __lxml_atomic_decr_relaxed(value) __lxml_atomic_add((value), -1)
    #define __lxml_atomic_load(value)         _Py_atomic_load_int32((value))

    #if defined(__lxml_DEBUG_ATOMICS) && defined(_MSC_VER)
        #pragma message ("Using pyatomics.h atomics")
    #elif defined(__lxml_DEBUG_ATOMICS)
        #warning "Using pyatomics.h atomics"
    #endif

#elif LXML_ATOMICS_ENABLED && (__GNUC__ >= 5 || (__GNUC__ == 4 && \
                    (__GNUC_MINOR__ > 1 ||  \
                    (__GNUC_MINOR__ == 1 && __GNUC_PATCHLEVEL__ >= 2))))

    /* gcc >= 4.1.2 */
    #define __lxml_atomic_add(value, arg)     __sync_fetch_and_add((value), (arg))
    #define __lxml_atomic_incr_relaxed(value) __sync_fetch_and_add((value), 1)
    #define __lxml_atomic_decr_relaxed(value) __sync_fetch_and_sub((value), 1)
    #define __lxml_atomic_load(value)         __sync_fetch_and_add((value), 0)

    /* UNUSED
    static int __lxml_atomic_compare_exchange(__lxml_atomic_int_type *value, __lxml_nonatomic_int_type *expected, __lxml_nonatomic_int_type desired) {
        __lxml_nonatomic_int_type old_value = __sync_val_compare_and_swap(value, *expected, desired);
        if (old_value != *expected) {
            *expected = old_value;
            return 0;
        }
        return 1;
    }
    */

    #ifdef __lxml_DEBUG_ATOMICS
        #warning "Using GNU atomics"
    #endif

#elif LXML_ATOMICS_ENABLED && defined(_MSC_VER)
    /* msvc */
    #include <intrin.h>

    #pragma intrinsic (_InterlockedExchangeAdd, _InterlockedCompareExchange)

    #define __lxml_atomic_add(value, arg) _InterlockedExchangeAdd((value), (arg))
    #define __lxml_atomic_incr_relaxed(value) __lxml_atomic_add((value),  1)
    #define __lxml_atomic_decr_relaxed(value) __lxml_atomic_add((value), -1)
    #define __lxml_atomic_load(value)          (*(value))

    /* UNUSED
    static int __lxml_atomic_compare_exchange(__lxml_atomic_int_type *value, __lxml_nonatomic_int_type *expected, __lxml_nonatomic_int_type desired) {
        __lxml_nonatomic_int_type old_value = _InterlockedCompareExchange(value, *expected, desired);
        if (old_value != *expected) {
            *expected = old_value;
            return 0;
        }
        return 1;
    }
    */

    #ifdef __lxml_DEBUG_ATOMICS
        #pragma message ("Using MSVC atomics")
    #endif

#elif PY_VERSION_HEX >= 0x030d0000
    /* Python critical section */
    #undef LXML_ATOMICS_ENABLED
    #define LXML_ATOMICS_ENABLED 0

    static __lxml_nonatomic_int_type __lxml_atomic_add_cs(PyObject *cs, __lxml_atomic_int_type *value, __lxml_nonatomic_int_type arg) {
        __lxml_nonatomic_int_type old_value;
        Py_BEGIN_CRITICAL_SECTION(cs);
        old_value = *value;
        *value = old_value + arg;
        Py_END_CRITICAL_SECTION();
        return old_value;
    }

    #define __lxml_atomic_add(value, arg)   __lxml_atomic_add_cs(__pyx_v_self, value, arg)
    #define __lxml_atomic_incr_relaxed(value) __lxml_atomic_add((value),  1)
    #define __lxml_atomic_decr_relaxed(value) __lxml_atomic_add((value), -1)
    #define __lxml_atomic_load(value)          (*(value))

    /* UNUSED
    static int __lxml_atomic_compare_exchange_cs(PyObject *cs, __lxml_atomic_int_type *value, __lxml_nonatomic_int_type *expected, __lxml_nonatomic_int_type desired) {
        __lxml_nonatomic_int_type old_value;
        int retval;
        Py_BEGIN_CRITICAL_SECTION(cs);
        old_value = *value;
        if (old_value == *expected) {
            *value = desired;
            retval = 1;
        } else {
            *expected = old_value;
            retval = 0;
        }
        Py_END_CRITICAL_SECTION();
        return retval;
    }

    #define __lxml_atomic_compare_exchange(value, expected, desired)  __lxml_atomic_compare_exchange_cs(__pyx_v_self, (value), (expected), (desired))
    */

    #ifdef __lxml_DEBUG_ATOMICS
        #warning "Not using atomics, using CPython critical section"
    #endif

#else
    #undef LXML_ATOMICS_ENABLED
    #define LXML_ATOMICS_ENABLED 0

    #define __lxml_atomic_add(value, arg)      ((*(value)) += (arg), (*(value) - (arg)))
    #define __lxml_atomic_incr_relaxed(value)  (*(value))++
    #define __lxml_atomic_decr_relaxed(value)  (*(value))--
    #define __lxml_atomic_load(value)          (*(value))

    /* UNUSED
    static int __lxml_atomic_compare_exchange(__lxml_atomic_int_type *value, __lxml_nonatomic_int_type *expected, __lxml_nonatomic_int_type desired) {
        __lxml_nonatomic_int_type old_value = *value;
        if (old_value == *expected) {
            *value = desired;
            return 1;
        } else {
            *expected = old_value;
            return 0;
        }
    }
    */

    #ifdef __lxml_DEBUG_ATOMICS
        #warning "Not using atomics, using the GIL"
    #endif
#endif

#if LXML_LOCK_PERFORMANCE
    #define __lxml_inc_counter(counter)  __lxml_atomic_incr_relaxed((counter))
    typedef struct {
        __lxml_atomic_int_type read_acquired;
        __lxml_atomic_int_type write_acquired;
        __lxml_atomic_int_type write_reentry;
        __lxml_atomic_int_type read_wait_on_writer;
        __lxml_atomic_int_type write_wait_on_reader;
        __lxml_atomic_int_type write_wait_on_writer;
    } __lxml_lock_perf;
#else
    /* Fake counter struct that just provides all attributes. */
    #define __lxml_inc_counter(counter)
    typedef struct {
        unsigned int read_acquired: 1;
        unsigned int write_acquired: 1;
        unsigned int write_reentry: 1;
        unsigned int read_wait_on_writer: 1;
        unsigned int write_wait_on_reader: 1;
        unsigned int write_wait_on_writer: 1;
    } __lxml_lock_perf;
#endif
    """
    const bint ATOMICS_ENABLED "LXML_ATOMICS_ENABLED"
    ctypedef long atomic_int "__lxml_atomic_int_type"
    ctypedef long nonatomic_int "__lxml_nonatomic_int_type"

    nonatomic_int atomic_add  "__lxml_atomic_add"          (atomic_int *value, nonatomic_int arg) noexcept
    nonatomic_int atomic_incr "__lxml_atomic_incr_relaxed" (atomic_int *value) noexcept
    nonatomic_int atomic_decr "__lxml_atomic_decr_relaxed" (atomic_int *value) noexcept
    nonatomic_int atomic_load "__lxml_atomic_load"         (atomic_int *value) noexcept
    int atomic_compare_exchange "__lxml_atomic_compare_exchange"  (atomic_int *value, nonatomic_int *expected, nonatomic_int desired) noexcept

    const bint COUNT_LOCK_PERFORMANCE "LXML_LOCK_PERFORMANCE"
    void inc_perf_counter "__lxml_inc_counter" (atomic_int *counter)

    ctypedef struct lock_perf "__lxml_lock_perf":
        atomic_int read_acquired
        atomic_int write_acquired
        atomic_int write_reentry
        atomic_int read_wait_on_writer
        atomic_int write_wait_on_reader
        atomic_int write_wait_on_writer


cdef const nonatomic_int max_lock_reader_count = 1 << 30


@cython.final
@cython.internal
@cython.profile(False)
@cython.linetrace(False)
cdef class RWLock:
    """Writer-preferring Read-Write lock.

    Uses atomics to avoid locking in the non-congested case.
    Uses 'PyMutex' to block readers and writers while writing.
    """
    cdef unsigned long _write_locked_id
    cdef atomic_int _reader_count
    cdef atomic_int _readers_departing
    cdef atomic_int _readers_waiting
    cdef cython.pymutex _readers_wait_lock
    cdef cython.pymutex _writer_wait_lock
    cdef cython.pymutex _writer_lock
    cdef int _writer_reentry
    cdef lock_perf _perf_counters

    @cython.inline
    cdef unsigned long _my_lock_id(self) noexcept:
        # "+1" to make sure that "== 0" really means "no thread waiting".
        return python.PyThread_get_thread_ident() + 1

    @cython.inline
    cdef bint _owns_write_lock(self, unsigned long lock_id) noexcept nogil:
        return lock_id == self._write_locked_id

    def get_perf_counters(self) -> dict:
        """Return the current performance counters as dict.
        """
        if COUNT_LOCK_PERFORMANCE:
            return self._perf_counters
        else:
            return {}

    # Read locking.

    cdef void _notify_readers(self, nonatomic_int waiting_readers) noexcept:
        while atomic_load(&self._readers_waiting) == 0:
            # Wait for the first reader to acquire the lock.
            with nogil: pass

        # Signal to the reader(s) that we noticed it taking the lock.
        waiting_already = atomic_add(&self._readers_waiting, -waiting_readers)

        # Unlock the first reader.
        self._readers_wait_lock.release()

    cdef void _wait_to_read(self) noexcept:
        self._readers_wait_lock.acquire()

        inc_perf_counter(&self._perf_counters.read_wait_on_writer)

        # Signal the writer that we have acquired the lock.
        readers_waiting = atomic_incr(&self._readers_waiting)

        if readers_waiting == 0:
            # We acquired the lock and notified the writer about it.
            # Wait for the writer to release the lock to us.
            self._readers_wait_lock.acquire()

        inc_perf_counter(&self._perf_counters.read_acquired)

        self._readers_wait_lock.release()

    cdef void lock_read(self) noexcept:
        readers_before = atomic_incr(&self._reader_count)
        if readers_before >= 0:
            # Only readers active => go!
            inc_perf_counter(&self._perf_counters.read_acquired)
            return

        if self._owns_write_lock(self._my_lock_id()):
            # I own the write lock => ignore the read lock and read!
            atomic_decr(&self._reader_count)
            inc_perf_counter(&self._perf_counters.read_acquired)
            return

        # A writer is waiting => wait for lock to become free.
        self._wait_to_read()

    cdef void unlock_read(self) noexcept:
        readers_before = atomic_decr(&self._reader_count)
        assert readers_before != 0
        if readers_before >= 0:
            return

        if self._owns_write_lock(self._my_lock_id()):
            # I own the write lock and ignored the read lock => undo the read claim.
            atomic_incr(&self._reader_count)
            return

        # A writer is waiting.
        if atomic_decr(&self._readers_departing) == 1:
            # No more readers after us, notify the waiting writer.
            self._notify_writer()

    # Write locking.

    @cython.inline
    cdef void _notify_writer(self) noexcept:
        self._writer_wait_lock.release()

    cdef void _wait_for_readers_to_finish(self, nonatomic_int readers) noexcept:
        self._writer_wait_lock.acquire()

        inc_perf_counter(&self._perf_counters.write_wait_on_reader)

        # Push current readers to '_readers_departing' and wait for them to exit.
        # Note that they might have departed already, making "self._readers_departing" negative
        # before we add to it.
        readers_departing = atomic_add(&self._readers_departing, readers) + readers
        if readers_departing > 0:
            # Wait for the readers to finish.
            self._writer_wait_lock.acquire()
        self._writer_wait_lock.release()

    cdef void lock_write(self) noexcept:
        my_lock_id = self._my_lock_id()

        if self._owns_write_lock(my_lock_id):
            inc_perf_counter(&self._perf_counters.write_reentry)
            self._writer_reentry += 1
            return

        if COUNT_LOCK_PERFORMANCE:
            if not self._owns_write_lock(0):
                # Risks race conditions if a writer finishes between now and us acquiring
                # the writer lock below, but that seems acceptable for a performance counter.
                inc_perf_counter(&self._perf_counters.write_wait_on_writer)

        self._writer_lock.acquire()

        # Claim the lock and block new readers if no writers are waiting.
        readers = atomic_add(&self._reader_count, -max_lock_reader_count)

        if readers != 0:
            if readers > 0:
                self._wait_for_readers_to_finish(readers)
            else:
                assert readers >= 0, "Writer claimed the lock but did not acquire it!"

        # No readers, no writers => go.
        self._write_locked_id = my_lock_id
        inc_perf_counter(&self._perf_counters.write_acquired)

    cdef void unlock_write(self) noexcept:
        assert self._owns_write_lock(self._my_lock_id()), f"{self._write_locked_id} != {self._my_lock_id()}"
        assert atomic_load(&self._reader_count) < 0, atomic_load(&self._reader_count)

        if self._writer_reentry > 0:
            self._writer_reentry -= 1
            return

        self._write_locked_id = 0

        readers = atomic_add(&self._reader_count, max_lock_reader_count) + max_lock_reader_count
        if readers > 0:
            # Unblock the waiting readers.
            self._notify_readers(readers)

        self._writer_lock.release()

    # Double lock locking.

    cdef void lock_write_with(self, RWLock second_lock) noexcept:
        """Acquire two locks for writing at the same time.
        """
        # Avoid deadlocks by deterministically locking an arbitrary lock first.
        if self is second_lock:
            self.lock_write()
        elif <void*>self < <void*>second_lock:
            second_lock.lock_write()
            self.lock_write()
        else:
            self.lock_write()
            second_lock.lock_write()

    cdef void unlock_write_with(self, RWLock second_lock) noexcept:
        """Release two locks for writing after locking them at the same time.
        """
        # Avoid deadlocks by deterministically locking an arbitrary lock first.
        if self is second_lock:
            self.unlock_write()
        elif <void*>self < <void*>second_lock:
            self.unlock_write()
            second_lock.unlock_write()
        else:
            second_lock.unlock_write()
            self.unlock_write()
