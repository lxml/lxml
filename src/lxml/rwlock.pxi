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

#if LXML_ATOMICS_ENABLED && defined(Py_ATOMIC_H)
    /* "Python.h" included "pyatomics.h" */

    #define __lxml_atomic_compare_exchange(value, expected, desired)  _Py_atomic_compare_exchange_int32((value), (expected), (desired))
    #define __lxml_atomic_add(value, arg)     _Py_atomic_add_int32((value), (arg))
    #define __lxml_atomic_incr(value)  __lxml_atomic_add((value),  1)
    #define __lxml_atomic_decr(value)  __lxml_atomic_add((value), -1)
    #define __lxml_atomic_load(value)  _Py_atomic_load_int32((value))

    #if defined(LXML_DEBUG_ATOMICS) && defined(_MSC_VER)
        #pragma message ("Using pyatomics.h atomics")
    #elif defined(LXML_DEBUG_ATOMICS)
        #warning "Using pyatomics.h atomics"
    #endif

#elif LXML_ATOMICS_ENABLED && (defined(__STDC_VERSION__) && \
                        (__STDC_VERSION__ >= 201112L) && \
                        !defined(__STDC_NO_ATOMICS__) && \
                       ATOMIC_INT_LOCK_FREE == 2)
    /* C11 atomics are available and ATOMIC_INT_LOCK_FREE is definitely on */
    #undef __lxml_atomic_int_type
    #define __lxml_atomic_int_type _Atomic __lxml_nonatomic_int_type

    #define __lxml_atomic_compare_exchange(value, expected, desired)  atomic_compare_exchange_strong((value), (expected), (desired))
    #define __lxml_atomic_add(value, arg)     atomic_fetch_add_explicit((value), (arg), memory_order_seq_cst)
    #define __lxml_atomic_incr(value)  __lxml_atomic_add((value),  1)
    #define __lxml_atomic_decr(value)  __lxml_atomic_add((value), -1)
    #define __lxml_atomic_load(value)  atomic_load((value))

    #if defined(LXML_DEBUG_ATOMICS) && defined(_MSC_VER)
        #pragma message ("Using standard C11 atomics")
    #elif defined(LXML_DEBUG_ATOMICS)
        #warning "Using standard C11 atomics"
    #endif

#elif LXML_ATOMICS_ENABLED && (__GNUC__ >= 5 || (__GNUC__ == 4 && \
                    (__GNUC_MINOR__ > 1 ||  \
                    (__GNUC_MINOR__ == 1 && __GNUC_PATCHLEVEL__ >= 2))))

    /* gcc >= 4.1.2 */
    #define __lxml_atomic_add(value, arg)     __sync_fetch_and_add((value), (arg))
    #define __lxml_atomic_incr(value)  __sync_fetch_and_add((value), 1)
    #define __lxml_atomic_decr(value)  __sync_fetch_and_sub((value), 1)
    #define __lxml_atomic_load(value)  __sync_fetch_and_add((value), 0)

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

    #ifdef LXML_DEBUG_ATOMICS
        #warning "Using GNU atomics"
    #endif

#elif LXML_ATOMICS_ENABLED && defined(_MSC_VER)
    /* msvc */
    #include <intrin.h>

    #pragma intrinsic (_InterlockedExchangeAdd, _InterlockedCompareExchange)

    #define __lxml_atomic_add(value, arg) _InterlockedExchangeAdd((value), (arg))
    #define __lxml_atomic_incr(value)  __lxml_atomic_add((value),  1)
    #define __lxml_atomic_decr(value)  __lxml_atomic_add((value), -1)
    #define __lxml_atomic_load(value)  (*(value))

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

    #ifdef LXML_DEBUG_ATOMICS
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
    #define __lxml_atomic_incr(value)  __lxml_atomic_add((value),  1)
    #define __lxml_atomic_decr(value)  __lxml_atomic_add((value), -1)
    #define __lxml_atomic_load(value)  (*(value))

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

    #if defined(LXML_DEBUG_ATOMICS) && defined(_MSC_VER)
        #pragma message ("Not using atomics, using CPython critical section")
    #elif defined(LXML_DEBUG_ATOMICS)
        #warning "Not using atomics, using CPython critical section"
    #endif

#else
    #undef LXML_ATOMICS_ENABLED
    #define LXML_ATOMICS_ENABLED 0

    #define __lxml_atomic_add(value, arg)      ((*(value)) += (arg), (*(value) - (arg)))
    #define __lxml_atomic_incr(value)  (*(value))++
    #define __lxml_atomic_decr(value)  (*(value))--
    #define __lxml_atomic_load(value)  (*(value))

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

    #if defined(LXML_DEBUG_ATOMICS) && defined(_MSC_VER)
        #pragma message ("Not using atomics, using the GIL")
    #elif defined(LXML_DEBUG_ATOMICS)
        #warning "Not using atomics, using the GIL"
    #endif
#endif

/* Re-entrant read locks need to know which read locks a thread holds.  The read locks of
   a thread that reads alone (the "first reader") are counted in the RWLock itself, which
   only needs a cheap thread id.  Other readers record theirs in a thread-local stack.  */

/* Unique per running thread and cheap: the thread pointer where it is known to be one. */
#if defined(__linux__) && (defined(__x86_64__) || defined(__aarch64__) || defined(__i386__)) && defined(__has_builtin)
    #if __has_builtin(__builtin_thread_pointer)
        #define __LXML_THREAD_ID_FROM_POINTER 1
    #endif
#endif
#if defined(__LXML_THREAD_ID_FROM_POINTER)
    #define __lxml_thread_id()  ((uintptr_t) __builtin_thread_pointer())
#elif defined(_MSC_VER) && defined(_M_X64)
    #include <intrin.h>
    #define __lxml_thread_id()  ((uintptr_t) __readgsqword(0x30))
#elif defined(_MSC_VER) && defined(_M_IX86)
    #include <intrin.h>
    #define __lxml_thread_id()  ((uintptr_t) __readfsdword(0x18))
#else
    #define __lxml_thread_id()  ((uintptr_t) PyThread_get_thread_ident() + 1)
#endif

/* The thread ids of the first reader and of the write lock owner are read by other threads. */
#if defined(__GNUC__) || defined(__clang__)
    #define __lxml_load_relaxed(ptr)  __atomic_load_n((ptr), __ATOMIC_RELAXED)
    #define __lxml_store_relaxed(ptr, value)  __atomic_store_n((ptr), (value), __ATOMIC_RELAXED)
#else
    #define __lxml_load_relaxed(ptr)  (*(volatile uintptr_t *) (ptr))
    #define __lxml_store_relaxed(ptr, value)  (*(volatile uintptr_t *) (ptr) = (value))
#endif

#ifndef LXML_THREAD_LOCAL
    #if defined(_MSC_VER)
        #define LXML_THREAD_LOCAL __declspec(thread)
    #elif defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
        #define LXML_THREAD_LOCAL _Thread_local
    #else
        #define LXML_THREAD_LOCAL __thread
    #endif
#endif

/* The thread-local stack of read locks, as tagged RWLock pointers.  Read locks beyond
   __LXML_MAX_READ_HOLDS are counted but not recorded. */
#define __LXML_MAX_READ_HOLDS 16
/* A nested read lock that does not count as reader (the thread holds the lock already). */
#define __LXML_READ_HOLD_NESTED ((uintptr_t) 1)
typedef struct {
    Py_ssize_t count;
    uintptr_t holds[__LXML_MAX_READ_HOLDS];
} __lxml_read_holds;

static LXML_THREAD_LOCAL __lxml_read_holds __lxml_thread_read_holds;
#define __lxml_get_read_holds()  (&__lxml_thread_read_holds)

#if LXML_LOCK_PERFORMANCE
    #define __lxml_inc_counter(counter)  __lxml_atomic_incr((counter))
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

    nonatomic_int atomic_add  "__lxml_atomic_add"   (atomic_int *value, nonatomic_int arg) noexcept
    nonatomic_int atomic_incr "__lxml_atomic_incr"  (atomic_int *value) noexcept
    nonatomic_int atomic_decr "__lxml_atomic_decr"  (atomic_int *value) noexcept
    nonatomic_int atomic_load "__lxml_atomic_load"  (atomic_int *value) noexcept
    int atomic_compare_exchange "__lxml_atomic_compare_exchange"  (atomic_int *value, nonatomic_int *expected, nonatomic_int desired) noexcept

    ctypedef size_t thread_id "uintptr_t"
    thread_id current_thread_id "__lxml_thread_id" () noexcept
    thread_id load_relaxed "__lxml_load_relaxed" (thread_id *value) noexcept
    void store_relaxed "__lxml_store_relaxed" (thread_id *value, thread_id new_value) noexcept

    ctypedef struct read_holds "__lxml_read_holds":
        Py_ssize_t count
        thread_id* holds
    read_holds* get_read_holds "__lxml_get_read_holds" () noexcept
    const Py_ssize_t MAX_READ_HOLDS "__LXML_MAX_READ_HOLDS"
    const thread_id READ_HOLD_NESTED "__LXML_READ_HOLD_NESTED"

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

    Read locks are re-entrant: a thread that holds the read lock takes it again without
    waiting for a waiting writer.
    """
    # The read locks of the "first reader", which took the read lock while no other thread
    # held it, are tracked here.  Other threads record theirs in a thread-local stack.
    cdef thread_id _first_reader
    cdef int _first_reader_holds   # counted read locks
    cdef int _first_reader_nested  # nested read locks that do not count as readers
    cdef thread_id _write_locked_id
    cdef atomic_int _reader_count
    cdef atomic_int _readers_departing
    cdef atomic_int _readers_waiting
    cdef cython.pymutex _readers_wait_lock
    cdef cython.pymutex _readers_wait_guard
    cdef cython.pymutex _writer_wait_lock
    cdef cython.pymutex _writer_lock
    cdef int _writer_reentry
    cdef lock_perf _perf_counters

    @cython.inline
    @cython.profile(False)
    cdef unsigned long _my_lock_id(self) noexcept:
        # "+1" to make sure that "== 0" really means "no thread waiting".
        return python.PyThread_get_thread_ident() + 1

    @cython.inline
    @cython.profile(False)
    cdef bint _owns_write_lock(self, unsigned long lock_id) noexcept nogil:
        return lock_id == load_relaxed(&self._write_locked_id)

    def get_perf_counters(self) -> dict:
        """Return the current performance counters as dict.
        """
        if COUNT_LOCK_PERFORMANCE:
            return self._perf_counters
        else:
            return {}

    # Read locking.

    cdef void _unblock_readers(self, nonatomic_int waiting_readers) noexcept:
        while atomic_load(&self._readers_waiting) == 0:
            # Wait for the first reader to acquire the lock.
            with nogil: pass

        # Signal to the reader that we noticed it taking the lock.
        waiting_already = atomic_add(&self._readers_waiting, waiting_readers)
        assert waiting_already == -1, waiting_already

        # Unlock the first reader.
        self._readers_wait_lock.release()

    cdef void _wait_for_pending_readers_to_start(self):
        """Wait for any pending readers to start running after a writer unblocked them."""
        while atomic_load(&self._readers_waiting) > 0:
            with nogil: pass

    cdef void _wait_to_read(self) noexcept:
        # Guard against concurrent readers.
        with self._readers_wait_guard:
            inc_perf_counter(&self._perf_counters.read_wait_on_writer)

            # Wait for writer to unblock us.
            with self._readers_wait_lock:
                # Signal the writer that we have acquired the lock.
                readers_waiting = atomic_decr(&self._readers_waiting)

                if readers_waiting == 0:
                    # We acquired the lock first and notified the writer about it.
                    # Wait for the writer to release the lock to us.
                    self._readers_wait_lock.acquire()

            inc_perf_counter(&self._perf_counters.read_acquired)

    cdef void lock_read(self) noexcept:
        cdef thread_id me = current_thread_id()
        readers_before = atomic_incr(&self._reader_count)
        if readers_before >= 0:
            # Only readers active => go!
            inc_perf_counter(&self._perf_counters.read_acquired)
            if readers_before == 0:
                # The only reader.
                self._first_reader_holds = 1
                store_relaxed(&self._first_reader, me)
            elif load_relaxed(&self._first_reader) == me:
                self._first_reader_holds += 1
            else:
                self._record_read_lock(0)
            return
        self._lock_read_writer_waiting(me)

    @cython.final
    cdef void _lock_read_writer_waiting(self, thread_id me) noexcept:
        cdef read_holds* holds
        if self._owns_write_lock(self._my_lock_id()):
            # I own the write lock => ignore the read lock and read!
            atomic_decr(&self._reader_count)
            inc_perf_counter(&self._perf_counters.read_acquired)
            self._record_read_lock(READ_HOLD_NESTED)
            return

        if load_relaxed(&self._first_reader) == me:
            # The waiting writer waits for my read lock => ignore the read lock and read!
            atomic_decr(&self._reader_count)
            inc_perf_counter(&self._perf_counters.read_acquired)
            self._first_reader_nested += 1
            return

        holds = get_read_holds()
        if holds.count < MAX_READ_HOLDS and self._holds_read_lock(holds):
            # Same, but recorded in the thread-local stack.
            atomic_decr(&self._reader_count)
            inc_perf_counter(&self._perf_counters.read_acquired)
            holds.holds[holds.count] = <thread_id> <void*> self | READ_HOLD_NESTED
            holds.count += 1
            return

        # A writer is waiting => wait for lock to become free.
        self._wait_to_read()
        self._record_read_lock(0)

    cdef void unlock_read(self) noexcept:
        cdef thread_id me = current_thread_id()
        if load_relaxed(&self._first_reader) == me:
            if self._first_reader_nested:
                self._first_reader_nested -= 1
                return
            self._first_reader_holds -= 1
            if self._first_reader_holds == 0:
                store_relaxed(&self._first_reader, 0)
        elif self._forget_read_lock():
            # A nested read lock that does not count as reader.
            return

        readers_before = atomic_decr(&self._reader_count)
        if readers_before > 0:
            return
        self._unlock_read_writer_waiting(readers_before)

    @cython.final
    cdef void _unlock_read_writer_waiting(self, nonatomic_int readers_before) noexcept:
        assert readers_before != 0
        if readers_before >= 0:
            return

        if self._owns_write_lock(self._my_lock_id()):
            # I own the write lock and ignored the read lock => undo the read claim.
            atomic_incr(&self._reader_count)
            return

        # A writer is waiting.
        readers_departing = atomic_decr(&self._readers_departing)
        if readers_departing == 1:
            # No more readers after us, notify the waiting writer.
            self._notify_writer()

    # Thread-local read lock records of readers that are not the first reader.

    @cython.final
    cdef void _record_read_lock(self, thread_id flags) noexcept:
        cdef read_holds* holds = get_read_holds()
        cdef Py_ssize_t i = holds.count
        holds.count = i + 1
        if i < MAX_READ_HOLDS:
            holds.holds[i] = <thread_id> <void*> self | flags

    @cython.final
    cdef bint _holds_read_lock(self, read_holds* holds) noexcept:
        """Check if this thread recorded a counted read lock of this RWLock.
        """
        cdef thread_id hold = <thread_id> <void*> self
        cdef Py_ssize_t i
        for i in range(min(holds.count, MAX_READ_HOLDS)):
            if holds.holds[i] == hold:
                return True
        return False

    @cython.final
    cdef thread_id _forget_read_lock(self) noexcept:
        """Remove the last record of a read lock of this RWLock and return its flags.
        """
        cdef read_holds* holds = get_read_holds()
        cdef thread_id hold
        cdef Py_ssize_t top = holds.count - 1, i
        if top >= MAX_READ_HOLDS or top < 0:
            # Not recorded.
            if top >= 0:
                holds.count = top
            return 0
        i = top
        while i >= 0:
            hold = holds.holds[i]
            if (hold & ~READ_HOLD_NESTED) == <thread_id> <void*> self:
                # (Read locks of different RWLocks may be released in a different order.)
                while i < top:
                    holds.holds[i] = holds.holds[i+1]
                    i += 1
                holds.count = top
                return hold & READ_HOLD_NESTED
            i -= 1
        # Not recorded (acquired beyond MAX_READ_HOLDS, but released in a different order),
        # which leaves the count too large: holds beyond it are not recorded either.
        return 0

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

        self._wait_for_pending_readers_to_start()

        # Claim the lock and block new readers if no writers are waiting.
        readers = atomic_add(&self._reader_count, -max_lock_reader_count)

        if readers != 0:
            if readers > 0:
                self._wait_for_readers_to_finish(readers)
            else:
                assert readers >= 0, "Writer claimed the lock but did not acquire it!"

        # No readers, no writers => go.
        store_relaxed(&self._write_locked_id, my_lock_id)
        inc_perf_counter(&self._perf_counters.write_acquired)

    cdef void unlock_write(self) noexcept:
        assert self._owns_write_lock(self._my_lock_id()), f"{self._write_locked_id} != {self._my_lock_id()}"
        assert atomic_load(&self._reader_count) < 0, atomic_load(&self._reader_count)

        if self._writer_reentry > 0:
            self._writer_reentry -= 1
            return

        store_relaxed(&self._write_locked_id, 0)

        readers = atomic_add(&self._reader_count, max_lock_reader_count) + max_lock_reader_count
        if readers > 0:
            self._unblock_readers(readers)

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
