# cython: freethreading_compatible=True

cimport cython

cimport cpython.pythread as python

from contextlib import contextmanager

include "../rwlock.pxi"


cdef class _RWLock:
    cdef RWLock _lock

    def __cinit__(self):
        self._lock = RWLock()

    @property
    def reader_count(self):
        return self._lock._reader_count & (2**30 - 1)

    @property
    def writer_blocking_readers(self) -> bool:
        return self._lock._reader_count < 0

    @property
    def writer_reentry(self):
        return self._lock._writer_reentry

    @property
    def lock_thread_id(self):
        return self._lock._write_locked_id - 1

    def get_perf_counters(self):
        return self._lock.get_perf_counters()

    @contextmanager
    def read_lock(self):
        self.lock_read()
        try:
            yield
        finally:
            self.unlock_read()

    @contextmanager
    def write_lock(self):
        self.lock_write()
        try:
            yield
        finally:
            self.unlock_write()

    def lock_read(self):
        self._lock.lock_read()

    def unlock_read(self):
        self._lock.unlock_read()

    def lock_write(self):
        self._lock.lock_write()

    def unlock_write(self):
        self._lock.unlock_write()

    def lock_write_with(self, _RWLock second_lock):
        """Lock two locks for writing at the same time.
        """
        if self._lock is second_lock._lock:
            self._lock.lock_write()
        else:
            self._lock.lock_write_with(second_lock._lock)

    def unlock_write_with(self, _RWLock second_lock):
        """Unlock two locks for writing after locking them at the same time.
        """
        if self._lock is second_lock._lock:
            self._lock.unlock_write()
        else:
            self._lock.unlock_write_with(second_lock._lock)


def trace(test_function):
    """Compiled test trace helper.
    """
    import sys
    from functools import partial, wraps
    from threading import get_ident as get_thread_id

    _print = sys.stdout.write
    sysmon = sys.monitoring
    tool_id = sysmon.DEBUGGER_ID

    print_lock: cython.pymutex

    test_function_startline = test_function.__code__.co_firstlineno

    def trace_event(event, code, instruction_offset, *arg):
        filename: str = code.co_filename
        if 'test_' in filename and code.co_firstlineno < test_function_startline:
            return sysmon.DISABLE
        if 'lock' not in filename and 'etree' not in filename:
            return sysmon.DISABLE

        message = f"[{get_thread_id() & 0xffffffff:08x}] {event:6} {code.co_name}\n"
        with print_lock:
            _print(message)

    @wraps(test_function)
    def method(*args):
        sysmon.use_tool_id(tool_id, "tracer")
        sysmon.set_events(tool_id, sysmon.events.PY_START | sysmon.events.PY_RETURN)

        sysmon.register_callback(
            tool_id, sysmon.events.PY_START, partial(trace_event, 'call'))
        sysmon.register_callback(
            tool_id, sysmon.events.PY_RETURN, partial(trace_event, 'return'))

        test_function(*args)

        sysmon.clear_tool_id(tool_id)

    return method
