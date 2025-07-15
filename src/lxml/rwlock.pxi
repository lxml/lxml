"""Read-write lock implementation.
"""

cdef extern from *:
    """
#include <pythread.h>

#ifndef LXML_ATOMICS_ENABLED
    #define LXML_ATOMICS_ENABLED 1
#endif

#define __lxml_atomic_int_type int
#define __lxml_nonatomic_int_type int

// For standard C atomics, get the headers first so we have ATOMIC_INT_LOCK_FREE
// defined when we decide to use them.
#if LXML_ATOMICS_ENABLED && (defined(__STDC_VERSION__) && \
                        (__STDC_VERSION__ >= 201112L) && \
                        !defined(__STDC_NO_ATOMICS__))
    #include <stdatomic.h>
#endif

#if LXML_ATOMICS_ENABLED && defined(Py_ATOMIC_H)
    // "Python.h" included "pyatomics.h"
    #define __lxml_atomic_add(value, arg)     _Py_atomic_add_int((value), (arg))
    #define __lxml_atomic_incr_relaxed(value) __lxml_atomic_add((value),  1)
    #define __lxml_atomic_decr_relaxed(value) __lxml_atomic_add((value), -1)

    #ifdef __lxml_DEBUG_ATOMICS
        #warning "Using pyatomics.h atomics"
    #endif

#elif LXML_ATOMICS_ENABLED && (defined(__STDC_VERSION__) && \
                        (__STDC_VERSION__ >= 201112L) && \
                        !defined(__STDC_NO_ATOMICS__) && \
                       ATOMIC_INT_LOCK_FREE == 2)
    // C11 atomics are available and  ATOMIC_INT_LOCK_FREE is definitely on
    #undef __lxml_atomic_int_type
    #define __lxml_atomic_int_type atomic_int

    #define __lxml_atomic_add(value, arg)     atomic_fetch_add_explicit((value), (arg), memory_order_relaxed)
    #define __lxml_atomic_incr_relaxed(value) __lxml_atomic_add((value),  1)
    #define __lxml_atomic_decr_relaxed(value) __lxml_atomic_add((value), -1)

    #if defined(__lxml_DEBUG_ATOMICS) && defined(_MSC_VER)
        #pragma message ("Using standard C atomics")
    #elif defined(__lxml_DEBUG_ATOMICS)
        #warning "Using standard C atomics"
    #endif

#elif LXML_ATOMICS_ENABLED && (__GNUC__ >= 5 || (__GNUC__ == 4 && \
                    (__GNUC_MINOR__ > 1 ||  \
                    (__GNUC_MINOR__ == 1 && __GNUC_PATCHLEVEL__ >= 2))))
    /* gcc >= 4.1.2 */
    #define __lxml_atomic_add(value, arg)     __sync_fetch_and_add((value), (arg))
    #define __lxml_atomic_incr_relaxed(value) __sync_fetch_and_add((value), 1)
    #define __lxml_atomic_decr_relaxed(value) __sync_fetch_and_sub((value), 1)

    #ifdef __lxml_DEBUG_ATOMICS
        #warning "Using GNU atomics"
    #endif

#elif LXML_ATOMICS_ENABLED && defined(_MSC_VER)
    /* msvc */
    #include <intrin.h>
    #undef __lxml_atomic_int_type
    #define __lxml_atomic_int_type long
    #undef __lxml_nonatomic_int_type
    #define __lxml_nonatomic_int_type long
    #pragma intrinsic (_InterlockedExchangeAdd)

    #define __lxml_atomic_add(value, arg) _InterlockedExchangeAdd((value), (arg))
    #define __lxml_atomic_incr_relaxed(value) __lxml_atomic_add((value),  1)
    #define __lxml_atomic_decr_relaxed(value) __lxml_atomic_add((value), -1)

    #ifdef __lxml_DEBUG_ATOMICS
        #pragma message ("Using MSVC atomics")
    #endif

#elif PY_VERSION_HEX >= 0x030d0000
    #undef LXML_ATOMICS_ENABLED
    #define LXML_ATOMICS_ENABLED 0

    static _lxml_nonatomic_int_type __lxml_atomic_add_cs(PyObject *cs, _lxml_atomic_int_type *value, _lxml_nonatomic_int_type arg) {
        _lxml_nonatomic_int_type old_value;
        Py_BEGIN_CRITICAL_SECTION(cs);
        old_value = *value;
        *value = old_value + arg;
        Py_END_CRITICAL_SECTION();
        return old_value;
    }

    #define __lxml_atomic_add(value, arg)   __lxml_atomic_add_cs(__pyx_v_self, value, arg)
    #define __lxml_atomic_incr_relaxed(value) __lxml_atomic_add((value),  1)
    #define __lxml_atomic_decr_relaxed(value) __lxml_atomic_add((value), -1)

    #ifdef __lxml_DEBUG_ATOMICS
        #warning "Not using atomics, using CPython critical section"
    #endif

#else
    #undef LXML_ATOMICS_ENABLED
    #define LXML_ATOMICS_ENABLED 0

    #define __lxml_atomic_add(value, arg)      ((*(value)) += (arg), (*(value) - (arg)))
    #define __lxml_atomic_incr_relaxed(value)  (*(value))++
    #define __lxml_atomic_decr_relaxed(value)  (*(value))--

    #ifdef __lxml_DEBUG_ATOMICS
        #warning "Not using atomics, using the GIL"
    #endif
#endif
    """
    const bint LXML_ATOMICS_ENABLED
    ctypedef int atomic_int "__lxml_atomic_int_type"
    ctypedef int nonatomic_int "__lxml_nonatomic_int_type"

    nonatomic_int atomic_add  "__lxml_atomic_add"          (atomic_int *value, nonatomic_int arg) noexcept
    nonatomic_int atomic_incr "__lxml_atomic_incr_relaxed" (atomic_int *value) noexcept
    nonatomic_int atomic_decr "__lxml_atomic_decr_relaxed" (atomic_int *value) noexcept


cdef const long max_lock_reader_count = 1 << 30


@cython.final
@cython.internal
cdef class RWLock:
    """Read-write lock.

    Uses a critical section to guard lock operations and a PyMutex for write locking.
    """
    cdef list _objects_pending_cleanup
    cdef unsigned long _write_locked_id
    cdef atomic_int _reader_count
    cdef atomic_int _readers_departing
    cdef nonatomic_int _writers_waiting
    cdef nonatomic_int _writer_reentry
    cdef cython.pymutex _readers_wait_lock
    cdef cython.pymutex _writers_wait_lock

    @cython.inline
    cdef unsigned int _my_lock_id(self) noexcept:
        # "+1" to make sure that "== 0" really means "no thread waiting".
        return python.PyThread_get_thread_ident() + 1

    # Deferred cleanup support.

    cdef int add_object_for_cleanup(self, obj):
        if self._objects_pending_cleanup is None:
            self._objects_pending_cleanup = []
        self._objects_pending_cleanup.append(obj)
        return 0

    cdef int clean_up_pending_objects(self):
        if self._objects_pending_cleanup is not None:
            self._objects_pending_cleanup = None
        return 0

    # Read locking.

    cdef void _wait_to_read(self) noexcept:
        # Wait for the writer to release the lock, thus notifying us.
        while self._reader_count < 0:
            self._readers_wait_lock.acquire()
        self._readers_wait_lock.release()

    @cython.critical_section
    cdef bint try_lock_read(self) noexcept:
        readers_before = atomic_incr(&self._reader_count)
        if readers_before >= 0:
            # Only readers active => go!
            return True
        if self._write_locked_id == self._my_lock_id():
            # I own the write lock => ignore the read lock and read!
            atomic_decr(&self._reader_count)
            return True

        # Give up and undo our claim.
        # We rely on the 'critical_section' to prevent writers from terminating concurrently.
        readers = atomic_decr(&self._reader_count)
        assert readers < 0, readers

        return False

    cdef void lock_read(self) noexcept:
        readers_before = atomic_incr(&self._reader_count)
        if readers_before >= 0:
            # Only readers active => go!
            return
        if self._write_locked_id == self._my_lock_id():
            # I own the write lock => ignore the read lock and read!
            atomic_decr(&self._reader_count)
            return

        # A writer is waiting => wait for lock to become free.
        self._wait_to_read()

    cdef void unlock_read(self) noexcept:
        readers = atomic_decr(&self._reader_count)
        if readers < 0:
            if self._write_locked_id == self._my_lock_id():
                # I own the write lock and ignored the read lock => undo the read claim.
                atomic_incr(&self._reader_count)
                return
            # A writer is waiting.
            if atomic_decr(&self._readers_departing) == 1:
                # No more readers after us, notify the waiting writer.
                self._writers_wait_lock.release()

    # Write locking.

    cdef void _wait_for_write_lock(self, unsigned long my_lock_id) noexcept:
        # No atomics, this is guarded by critical_section(self).
        self._writers_waiting += 1
        if self._writers_waiting == 1:
            # I am the first waiting writer and the mutex is not locked yet. Lock it now.
            self._writers_wait_lock.acquire()

        # Wait for the current writer or the last reader to release the mutex to us.
        while True:
            self._writers_wait_lock.acquire()
            if self._write_locked_id == 0:
                break
            self._writers_wait_lock.release()

        # Claim the write lock.
        self._write_locked_id = my_lock_id
        self._writers_waiting -= 1

        # If no one else is waiting, unlock the mutex.
        if self._writers_waiting == 0:
            self._writers_wait_lock.release()

    @cython.critical_section
    cdef void lock_write(self) noexcept:
        my_lock_id = self._my_lock_id()
        # Claim the lock and block new readers if no writers are waiting.
        cdef nonatomic_int readers = atomic_add(&self._reader_count, -max_lock_reader_count)

        if readers == 0:
            # Fast path: no readers, no writers => go
            self._write_locked_id = my_lock_id
            return

        elif readers < 0:
            # Another writer has already claimed the lock. Undo our claim and wait for the writer.
            atomic_add(&self._reader_count, max_lock_reader_count)
            if self._write_locked_id == my_lock_id:
                # I own the lock myself.
                self._writer_reentry += 1
                return
            self._wait_for_write_lock(my_lock_id)

        else:  # readers > 0:
            # Push current readers to '_readers_departing' and wait for them to exit.
            readers_departing = atomic_add(&self._readers_departing, readers) + readers
            if readers_departing == 0:
                # Race condition: the last reader ended before we could update 'self._readers_departing'. Claim the lock.
                self._write_locked_id = my_lock_id
            else:
                self._wait_for_write_lock(my_lock_id)

    @cython.critical_section
    cdef void unlock_write(self) noexcept:
        assert self._write_locked_id == self._my_lock_id(), f"{self._write_locked_id} != {self._my_lock_id()}"
        assert self._reader_count < 0, self._reader_count
        if self._writer_reentry > 0:
            self._writer_reentry -= 1
            return

        # Clean up any objects that needed the lock for their deallocation (and couldn't get it yet).
        self.clean_up_pending_objects()

        # Release the lock.
        self._write_locked_id = 0

        if self._writers_waiting > 0:
            # Notify the next waiting writer.
            self._writers_wait_lock.release()
            return

        # No writers waiting, unblock readers.
        readers = atomic_add(&self._reader_count, max_lock_reader_count) + max_lock_reader_count
        if readers > 0:
            # Notify waiting readers.
            self._readers_wait_lock.release()

    # Double locking.

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
