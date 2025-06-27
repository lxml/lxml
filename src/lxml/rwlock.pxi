@cython.final
@cython.internal
cdef class RWLock:
    """Read-write lock.

    Uses a critical section to guard lock operations and a PyMutex for write locking.
    """
    cdef unsigned long _write_locked_id
    cdef int _reader_count
    cdef int _writer_reentry
    cdef cython.pymutex _write_lock

    @cython.inline
    cdef unsigned long _my_lock_id(self) noexcept:
        # "+1" to make sure that "== 0" really means "no thread waiting".
        return python.PyThread_get_thread_ident() + 1

    @cython.critical_section
    cdef int lock_read(self) noexcept:
        self._reader_count += 1
        if self._reader_count > 0:
            # Only readers active => go!
            return 0
        if self._write_locked_id == self._my_lock_id():
            # I own the write lock => go!
            return 0
        # A writer is waiting => wait for lock to become free.
        while self._write_locked_id:
            with nogil:
                self._write_lock.acquire()
                self._write_lock.release()
        return 0

    @cython.critical_section
    cdef int unlock_read(self) noexcept:
        self._reader_count -= 1

    @cython.critical_section
    cdef int lock_write(self) noexcept:
        my_lock_id = self._my_lock_id()
        if self._write_locked_id == my_lock_id:
            self._writer_reentry += 1
            return 0

        if self._reader_count == 0:
            # No readers, no writers => go
            self._reader_count -= max_lock_reader_count
            self._write_locked_id = my_lock_id
            self._writer_reentry = 0
            return 0

        if self._reader_count > 0:
            # Readers but no writers yet => block new readers, claim the lock.
            self._reader_count -= max_lock_reader_count
            self._write_locked_id = my_lock_id

        # Waiting readers or writers.
        while True:
            with nogil:
                self._write_lock.acquire()
                self._write_lock.release()
            if not self._write_locked_id:
                # Lock is free => block new readers and take ownership.
                self._reader_count -= max_lock_reader_count
                break
            elif self._write_locked_id == my_lock_id:
                break

        # My turn.
        self._write_locked_id = my_lock_id
        self._writer_reentry = 0
        return 0

    @cython.critical_section
    cdef int unlock_write(self) noexcept:
        assert self._write_locked_id == self._my_lock_id()
        assert self._reader_count < 0, self._reader_count
        if self._writer_reentry > 0:
            self._writer_reentry -= 1
            return 0
        self._write_locked_id = 0
        self._reader_count += max_lock_reader_count
        return 0

    cdef int lock_write_with(self, RWLock second_lock):
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
        return 0

    cdef int unlock_write_with(self, RWLock second_lock):
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
        return 0
