"""Read-write lock implementation.
"""

cdef const long max_lock_reader_count = 1 << 30


@cython.final
@cython.internal
cdef class RWLock:
    """Read-write lock.

    Uses a critical section to guard lock operations and a PyMutex for write locking.
    """
    cdef unsigned long _write_locked_id
    cdef int _reader_count
    cdef int _readers_departing
    cdef int _writer_reentry
    cdef cython.pymutex _write_lock

    # Invariants:
    # - _write_lock is held whenever we need to wait for the lock.
    # - _write_lock is released whenever a writer or the last reader
    #   releases the lock *and* someone is waiting for it.
    # - _reader_count < 0 means a writer owns the lock or is waiting for it. This blocks new readers.

    @cython.inline
    cdef unsigned int _my_lock_id(self) noexcept:
        # "+1" to make sure that "== 0" really means "no thread waiting".
        return python.PyThread_get_thread_ident() + 1

    # Read locking.

    cdef void _wait_to_read(self) noexcept:
        if self._reader_count == 1 - max_lock_reader_count:
            # I am the first reader to need the lock => lock it before waiting for the release.
            with nogil:
                self._write_lock.acquire()

        # Wait for the writer to release the lock, thus notifying us.
        while self._write_locked_id:
            with nogil:
                self._write_lock.acquire()

        self._write_lock.release()

    @cython.critical_section
    cdef void lock_read(self) noexcept:
        self._reader_count += 1
        if self._reader_count > 0:
            # Only readers active => go!
            return
        if self._write_locked_id == self._my_lock_id():
            # I own the write lock => ready to read!
            return
        # A writer is waiting => wait for lock to become free.
        self._wait_to_read()

    @cython.critical_section
    cdef void unlock_read(self) noexcept:
        self._reader_count -= 1
        # PROBLEM: Wann .release()? Beim Arbeiten kann sich '_reader_count' erhöhen, aber die warten nur.
        if self._reader_count < 0:
            # A writer is waiting.
            if self._readers_departing > 0:
                self._readers_departing -= 1
                if not self._readers_departing:
                    # No more readers, notify the waiting writer.
                    self._write_lock.release()

    # Write locking.

    cdef void _wait_for_writer(self, unsigned long my_lock_id) noexcept:
        if self._reader_count == - max_lock_reader_count:
            # I am the first to need the lock => lock the mutex before waiting for the release.
            with nogil:
                self._write_lock.acquire()

        while self._reader_count < 0:
            self._reader_count += 1  # Tell everyone that we need to be notified.
            with nogil:
                self._write_lock.acquire()
            self._reader_count -= 1

        # No writer left => claim the lock.
        self._claim_write_lock(my_lock_id)

        # If readers started before us, wait for them to finish.
        self._wait_for_readers_locked(my_lock_id)

    cdef void _wait_for_readers(self, unsigned long my_lock_id) noexcept:
        self._claim_write_lock(my_lock_id)

        # Acquire the lock and wait for the last reader to release it.
        with nogil:
            self._write_lock.acquire()
        self._wait_for_readers_locked(my_lock_id)

    cdef void _wait_for_readers_locked(self, unsigned long my_lock_id) noexcept:
        # Owning the mutex, wait for readers to finish.
        while self._readers_departing > 0:
            self._reader_count += 1  # Tell everyone that we need to be notified.
            with nogil:
                self._write_lock.acquire()
            self._reader_count -= 1

    @cython.critical_section
    cdef void lock_write(self) noexcept:
        my_lock_id = self._my_lock_id()
        if self._reader_count == 0:
            # No readers, no writers => go
            self._claim_write_lock(my_lock_id)

        elif self._reader_count < 0:
            # A writer owns or claimed the lock already.
            if self._write_locked_id == my_lock_id:
                # I own the lock myself.
                self._writer_reentry += 1
                return
            self._wait_for_writer(my_lock_id)

        else:  #  self._reader_count > 0
            # Readers but no writers yet => block new readers, claim the lock.
            self._wait_for_readers(my_lock_id)

    cdef void _claim_write_lock(self, unsigned long my_lock_id) noexcept:
        # Mark the write lock as owned, but do not acquire the mutex.
        self._readers_departing = self._reader_count
        self._reader_count -= max_lock_reader_count
        self._write_locked_id = my_lock_id
        self._writer_reentry = 0

    @cython.critical_section
    cdef void unlock_write(self) noexcept:
        assert self._write_locked_id == self._my_lock_id()
        assert self._reader_count < 0, self._reader_count
        if self._writer_reentry > 0:
            self._writer_reentry -= 1
            return

        self._write_locked_id = 0
        self._reader_count += max_lock_reader_count

        if self._reader_count > 0:
            # Notify waiting readers and writers.
            self._write_lock.release()

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
