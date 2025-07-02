import threading
import time
import unittest
from contextlib import contextmanager
from functools import partial, wraps

from lxml.tests._testlock import _RWLock as RWLock


class RWLockTest(unittest.TestCase):
    @contextmanager
    def run_threads(self, *functions):
        threads = [threading.Thread(target=function) for function in functions]
        for thread in threads:
            thread.start()
        yield
        for thread in threads:
            thread.join()

    def test_lock_read(self):
        lock = RWLock()
        assert lock.reader_count == 0, lock.reader_count
        lock.lock_read()
        assert lock.reader_count == 1, lock.reader_count
        lock.unlock_read()
        assert lock.reader_count == 0, lock.reader_count
        lock.lock_read()
        assert lock.reader_count == 1, lock.reader_count
        lock.unlock_read()
        assert lock.reader_count == 0, lock.reader_count

    def test_lock_read_reentry(self):
        lock = RWLock()
        lock.lock_read()
        assert lock.reader_count == 1, lock.reader_count

        lock.lock_read()
        assert lock.reader_count == 2, lock.reader_count
        lock.unlock_read()
        assert lock.reader_count == 1, lock.reader_count
        lock.lock_read()
        assert lock.reader_count == 2, lock.reader_count
        lock.unlock_read()
        assert lock.reader_count == 1, lock.reader_count

        lock.unlock_read()
        assert lock.reader_count == 0, lock.reader_count

        lock.lock_read()
        assert lock.reader_count == 1, lock.reader_count
        lock.unlock_read()
        assert lock.reader_count == 0, lock.reader_count

    def test_lock_write(self):
        lock = RWLock()

        assert not lock.writer_blocking_readers
        assert lock.reader_count == 0, lock.reader_count
        lock.lock_write()
        assert lock.writer_blocking_readers
        assert lock.reader_count == 0, lock.reader_count
        lock.unlock_write()
        assert not lock.writer_blocking_readers
        assert lock.reader_count == 0, lock.reader_count

        lock.lock_write()
        assert lock.reader_count == 0, lock.reader_count
        lock.unlock_write()
        assert lock.reader_count == 0, lock.reader_count

        lock.lock_write()
        assert lock.reader_count == 0, lock.reader_count
        lock.unlock_write()
        assert lock.reader_count == 0, lock.reader_count

    def test_lock_write_reentry(self):
        lock = RWLock()

        assert not lock.writer_blocking_readers
        assert lock.writer_reentry == 0, lock.writer_reentry
        lock.lock_write()
        assert lock.writer_blocking_readers
        assert lock.reader_count == 0, lock.reader_count
        assert lock.writer_reentry == 0, lock.writer_reentry

        lock.lock_write()
        assert lock.writer_blocking_readers
        assert lock.writer_reentry == 1, lock.writer_reentry
        lock.unlock_write()
        assert lock.writer_blocking_readers
        assert lock.writer_reentry == 0, lock.writer_reentry

        lock.lock_write()
        assert lock.writer_reentry == 1, lock.writer_reentry
        lock.unlock_write()
        assert lock.writer_reentry == 0, lock.writer_reentry

        lock.lock_write()
        assert lock.writer_reentry == 1, lock.writer_reentry
        lock.unlock_write()
        assert lock.writer_blocking_readers
        assert lock.writer_reentry == 0, lock.writer_reentry

        lock.unlock_write()
        assert not lock.writer_blocking_readers
        assert lock.writer_reentry == 0, lock.writer_reentry

        lock.lock_write()
        assert lock.writer_reentry == 0, lock.writer_reentry
        lock.unlock_write()
        assert lock.writer_reentry == 0, lock.writer_reentry

    def test_lock_write_wait_writers(self):
        lock = RWLock()

        order = []

        start = threading.Barrier(2)
        waiting = threading.Event()
        release = threading.Event()

        def thread_lock():
            order.append("locking (1)")
            lock.lock_write()
            assert lock.writer_blocking_readers
            order.append("locked (1)")
            start.wait()

            order.append("waiting (1)")
            release.wait()

            order.append("releasing (1)")
            lock.unlock_write()
            order.append("released (1)")

        def thread_wait():
            start.wait()
            order.append("waiting (2)")
            waiting.set()
            lock.lock_write()
            order.append("locked (2)")
            lock.unlock_write()
            order.append("released (2)")

        with self.run_threads(thread_lock, thread_wait):
            waiting.wait()
            release.set()

        self.assertListEqual(['locking (1)', 'locked (1)', 'waiting (2)', 'waiting (1)', 'releasing (1)'], order[:5])
        self.assertListEqual(['locked (2)', 'released (1)', 'released (2)'], sorted(order[5:]))

    def test_lock_write_wait_readers(self):
        lock = RWLock()

        order = []

        start = threading.Barrier(9 + 1)
        waiting = threading.Barrier(9 + 1)
        release = threading.Event()

        def thread_lock_read(n):
            order.append(f"locking ({n})")
            lock.lock_read()
            order.append(f"locked ({n})")
            assert not lock.writer_blocking_readers
            start.wait()

            order.append(f"waiting ({n})")
            waiting.wait()

            assert "locked (write)" not in order

            order.append(f"releasing ({n})")
            lock.unlock_read()
            order.append(f"released ({n})")

        def thread_wait_write():
            start.wait()
            order.append(f"waiting (write)")
            lock.lock_write()
            assert lock.writer_blocking_readers
            release.wait()
            order.append(f"locked (write)")
            assert lock.writer_blocking_readers
            lock.unlock_write()
            order.append(f"released (write)")

        readers = [partial(thread_lock_read, i) for i in range(1, 10)]

        with self.run_threads(*readers, thread_wait_write):
            waiting.wait()
            release.set()

        self.assertListEqual(
            [f'locked ({n})' for n in range(1, 10)] + [f'locking ({n})' for n in range(1, 10)] + [f'waiting ({n})' for n in range(1, 10)] + ["waiting (write)"],
            sorted(order[:9+9+10]))

        #self.assertListEqual(['locking (1)', 'locked (1)', 'waiting (2)', 'waiting (1)', 'releasing (1)'], order[:5])
        #self.assertListEqual(['locked (2)', 'released (1)', 'released (2)'], sorted(order[5:]))

    def test_concurrent_read_write(self):
        lock = RWLock()

        # Thread monitoring:

        local = threading.local()

        reader_count = 0
        writer_count = 0

        def lock_read():
            nonlocal reader_count
            lock.lock_read()
            print("LOCK-R", reader_count, writer_count)
            reader_count += 1

        def unlock_read():
            nonlocal reader_count
            reader_count -= 1
            print("UNLOCK-R", reader_count, writer_count)
            lock.unlock_read()

        def lock_write():
            nonlocal writer_count
            lock.lock_write()
            print("LOCK-W", reader_count, writer_count)
            writer_count += 1

        def unlock_write():
            nonlocal writer_count
            writer_count -= 1
            print("UNLOCK-W", reader_count, writer_count)
            lock.unlock_write()

        def expect(readers, writers):
            rw = (reader_count, writer_count)
            if readers >= 0:
                ok = rw == (readers, writers)
            else:
                ok = writer_count == writers and rw[0] >= - readers

            try:
                counts = local.counts
            except AttributeError:
                counts = local.counts = []
            counts.append("(ok)" if ok else {'expected': (readers, writers), 'actual': rw})

        def check():
            counts = local.counts
            self.assertListEqual(counts, ['(ok)'] * len(counts))

        # The test threads:

        def wait(t=0.1):
            time.sleep(t)

        def read():
            start.wait()

            lock_read()
            expect(-1,0)
            wait()
            expect(-1,0)
            unlock_read()

        def write():
            start.wait()

            lock_write()
            expect(0, 1)
            wait()
            expect(0, 1)
            unlock_write()

        def readwrite_once():
            start.wait()

            lock_write()
            expect(0, 1)
            wait()
            expect(0, 1)

            lock_read()
            expect(1, 1)
            wait()
            expect(1, 1)
            unlock_read()

            expect(0, 1)
            unlock_write()

        def readwrite_many():
            start.wait()

            lock_write()
            expect(0, 1)
            wait()
            expect(0, 1)

            lock_read()
            expect(1, 1)
            wait()
            expect(1, 1)

            lock_read()
            expect(2, 1)
            unlock_read()

            expect(1, 1)

            lock_read()
            expect(2, 1)
            wait()
            expect(2, 1)
            unlock_read()

            expect(1, 1)
            unlock_read()

            expect(0, 1)

            lock_read()
            expect(1, 1)
            wait()
            expect(1, 1)
            unlock_read()

            expect(0, 1)
            unlock_write()

        failures = []

        def guard(func):
            @wraps(func)
            def wrapped():
                try:
                    func()
                    print(func.__name__, "done")
                except Exception as exc:
                    print(func.__name__, "failed:", exc)
                    import traceback
                    traceback.print_exc()
                    if not failures:
                        failures.append(str(exc))

                    # Try to clean up
                    while reader_count:
                        unlock_read()
                    while writer_count:
                        unlock_write()

                try:
                    check()
                except AssertionError as exc:
                    print(func.__name__, "check failed:", exc)
                    failures.append(str(exc))

            return wrapped

        threads = [
            guard(func)
            for func in (
                read,
                write,
                #readwrite_once,
                #readwrite_many,
            )
            for _ in range(2)
        ]

        start = threading.Barrier(len(threads))

        with self.run_threads(*threads):
            pass

        self.assertFalse(failures)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(RWLockTest)])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
