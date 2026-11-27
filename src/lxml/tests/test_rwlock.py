import threading
import time
import unittest
from contextlib import contextmanager
from functools import partial, wraps

from lxml.tests._testlock import _RWLock as RWLock, trace


def diff_perf_counters(start_counters, end_counters):
    return {
        name: end_value - start_counters[name]
        for name, end_value in end_counters.items()
    }


def assert_perf_counters(**counter_diffs):
    def decorator(f):
        @wraps(f)
        def check_counters(self):
            lock = RWLock()
            start_counters = lock.get_perf_counters()

            f(self, lock)

            end_counters = lock.get_perf_counters()
            diff = diff_perf_counters(start_counters, end_counters)

            for name in counter_diffs:
                assert name in diff, f"Test bug: unknown counter name '{name}'"

            differences = []
            for name, diff_value in diff.items():
                if name in counter_diffs:
                    expected_diff_value = counter_diffs[name]
                    if expected_diff_value is None:
                        continue
                else:
                    expected_diff_value = 0

                if diff_value != expected_diff_value:
                    differences.append(f"{name} == {diff_value} != {expected_diff_value}")

            if differences:
                self.fail(', '.join(sorted(differences)))

        return check_counters
    return decorator


class RWLockTest(unittest.TestCase):
    @contextmanager
    def run_threads(self, *functions):

        def name(target, _counter={}):
            if isinstance(target, partial):
                target = target.func
            try:
                count = _counter[target]
            except KeyError:
                count = 1
            _counter[target] = count + 1
            return f"{target.__name__}-{count:02d}"

        threads = [threading.Thread(target=function, name=name(function)) for function in functions]
        for thread in threads:
            thread.start()
        yield
        for thread in threads:
            thread.join()

    @assert_perf_counters(read_acquired=2)
    def test_lock_read(self, lock):
        assert lock.reader_count == 0, lock.reader_count
        lock.lock_read()
        assert lock.reader_count == 1, lock.reader_count
        lock.unlock_read()
        assert lock.reader_count == 0, lock.reader_count
        lock.lock_read()
        assert lock.reader_count == 1, lock.reader_count
        lock.unlock_read()
        assert lock.reader_count == 0, lock.reader_count

    @assert_perf_counters(read_acquired=4)
    def test_lock_read_reentry(self, lock):
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

    def run_bounded(self, function):
        # Runs 'function' in a thread, so that a deadlock fails the test instead of the suite.
        errors = []

        def run():
            try:
                function()
            except BaseException as exc:
                errors.append(exc)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        thread.join(60)  # time out after x seconds
        self.assertFalse(thread.is_alive(), "deadlocked")
        if errors:
            raise errors[0]

    def wait_for_writer(self, lock):
        # Spins until another thread waits for the write lock (and blocks new readers).
        while not lock.writer_blocking_readers:
            pass

    def test_lock_read_reentry_while_writer_waits(self):
        lock = RWLock()
        writer = threading.Thread(target=lambda: (lock.lock_write(), lock.unlock_write()))

        def read_nested():
            lock.lock_read()
            writer.start()
            self.wait_for_writer(lock)
            # The writer waits for this thread's read lock, which it already holds.
            lock.lock_read()
            lock.unlock_read()
            lock.unlock_read()
            writer.join()

        self.run_bounded(read_nested)
        self.assertEqual(0, lock.reader_count)
        self.assertFalse(lock.writer_blocking_readers)

    def test_lock_read_reentry_while_writer_waits_after_other_reader(self):
        # Another thread took the read lock first, and this one releases another lock
        # in a different order than it took it.
        lock, other_lock = RWLock(), RWLock()
        first_reading = threading.Event()
        release_first = threading.Event()
        writer = threading.Thread(target=lambda: (lock.lock_write(), lock.unlock_write()))

        def first_reader():
            with lock.read_lock():
                first_reading.set()
                release_first.wait()

        def read_nested():
            first_reading.wait()
            other_lock.lock_read()
            lock.lock_read()
            other_lock.unlock_read()
            writer.start()
            self.wait_for_writer(lock)
            lock.lock_read()
            lock.unlock_read()
            lock.unlock_read()

        with self.run_threads(first_reader):
            try:
                self.run_bounded(read_nested)
            finally:
                release_first.set()
        writer.join()
        self.assertEqual(0, lock.reader_count)
        self.assertEqual(0, other_lock.reader_count)
        self.assertFalse(lock.writer_blocking_readers)

    def test_lock_write_while_holding_read(self):
        lock = RWLock()

        def upgrade():
            lock.lock_read()
            lock.lock_read()
            lock.lock_write()
            self.assertTrue(lock.writer_blocking_readers)
            self.assertEqual(0, lock.writer_reentry)
            lock.lock_read()
            lock.unlock_read()
            lock.lock_write()
            lock.unlock_write()
            lock.unlock_write()
            self.assertFalse(lock.writer_blocking_readers)
            self.assertEqual(2, lock.reader_count)
            lock.unlock_read()
            lock.unlock_read()

        self.run_bounded(upgrade)
        self.assertEqual(0, lock.reader_count)
        self.assertFalse(lock.writer_blocking_readers)
        self.assertEqual(1, lock.get_perf_counters()['write_upgrade'])

    def test_lock_write_while_holding_read_waits_for_other_readers(self):
        lock = RWLock()
        order = []
        reading = threading.Event()
        release = threading.Event()

        def other_reader():
            with lock.read_lock():
                order.append("reading")
                reading.set()
                release.wait()
                order.append("released read lock")

        def release_when_writer_waits():
            self.wait_for_writer(lock)
            release.set()

        def upgrade():
            reading.wait()
            # Not the first reader: its read lock is recorded in the thread-local stack.
            with lock.read_lock():
                releaser = threading.Thread(target=release_when_writer_waits)
                releaser.start()
                with lock.write_lock():
                    order.append("writing")
                releaser.join()

        with self.run_threads(other_reader):
            self.run_bounded(upgrade)
        self.assertEqual(["reading", "released read lock", "writing"], order)
        self.assertEqual(0, lock.reader_count)

    def test_lock_write_while_holding_read_keeps_writers_out(self):
        # A writer that comes while a thread upgrades its read lock waits until this thread
        # released its read lock, i.e. it cannot modify what the upgrading code still reads.
        lock = RWLock()
        order = []
        writer = threading.Thread(target=lambda: (lock.lock_write(), order.append("writer"), lock.unlock_write()))

        def upgrade():
            with lock.read_lock():
                with lock.write_lock():
                    writer.start()
                    # Spin until the writer waits for the end of the upgrade.
                    while not lock.writers_waiting_for_upgrade:
                        pass
                    order.append("upgraded")
                order.append("still reading")
            writer.join()

        self.run_bounded(upgrade)
        self.assertEqual(["upgraded", "still reading", "writer"], order)
        self.assertEqual(0, lock.reader_count)
        self.assertFalse(lock.writer_blocking_readers)

    def test_lock_write_while_holding_read_and_writer_waits(self):
        # The waiting writer waits for this thread's read lock => fail instead of letting it go first.
        lock = RWLock()
        writer = threading.Thread(target=lambda: (lock.lock_write(), lock.unlock_write()))

        def upgrade():
            with lock.read_lock():
                writer.start()
                self.wait_for_writer(lock)
                with self.assertRaises(RuntimeError):
                    lock.lock_write()
                self.assertEqual(1, lock.reader_count)
            writer.join()

        self.run_bounded(upgrade)
        self.assertEqual(0, lock.reader_count)
        self.assertFalse(lock.writer_blocking_readers)
        self.assertEqual(1, lock.get_perf_counters()['write_upgrade_conflict'])

    def test_lock_write_while_holding_read_in_two_threads(self):
        # The second thread that upgrades its read lock fails, the first one waits for it.
        lock = RWLock()
        reading = threading.Barrier(2)
        results = []

        def first():
            with lock.read_lock():
                reading.wait()
                with lock.write_lock():
                    results.append("first wrote")

        def second():
            with lock.read_lock():
                reading.wait()
                self.wait_for_writer(lock)
                try:
                    lock.lock_write()
                except RuntimeError:
                    results.append("second failed")
                else:
                    lock.unlock_write()
                    results.append("second wrote")

        def upgrade_in_two_threads():
            with self.run_threads(first, second):
                pass

        self.run_bounded(upgrade_in_two_threads)
        self.assertEqual(["first wrote", "second failed"], sorted(results))
        self.assertEqual(0, lock.reader_count)
        self.assertFalse(lock.writer_blocking_readers)

    def test_lock_write_while_holding_read_released_while_writing(self):
        # Read locks taken before the upgrade may be released before the write lock.
        lock = RWLock()

        def upgrade():
            lock.lock_read()
            lock.lock_write()
            lock.unlock_read()
            lock.unlock_write()
            self.assertEqual(0, lock.reader_count)
            self.assertFalse(lock.writer_blocking_readers)
            # Nothing is left behind that would block other writers.
            writer = threading.Thread(target=lambda: (lock.lock_write(), lock.unlock_write()))
            writer.start()
            writer.join()

        self.run_bounded(upgrade)
        self.assertEqual(0, lock.reader_count)

    @assert_perf_counters(read_acquired=None, update_acquired=1, write_acquired=3,
                          write_upgrade=2, write_reentry=None)
    def test_lock_update(self, lock):
        lock.lock_update()
        self.assertEqual(1, lock.reader_count)
        self.assertFalse(lock.writer_blocking_readers)
        lock.lock_update()
        lock.lock_read()
        self.assertEqual(2, lock.reader_count)
        lock.unlock_read()

        # Upgrade to the write lock and return to the update lock.
        lock.lock_write()
        self.assertTrue(lock.writer_blocking_readers)
        lock.lock_read()
        lock.unlock_read()
        lock.unlock_write()
        self.assertFalse(lock.writer_blocking_readers)
        self.assertEqual(1, lock.reader_count)
        lock.unlock_update()
        lock.unlock_update()
        self.assertEqual(0, lock.reader_count)

        # Within the write lock, the update lock is the write lock.
        lock.lock_write()
        lock.lock_update()
        lock.unlock_update()
        self.assertTrue(lock.writer_blocking_readers)
        lock.unlock_write()
        self.assertFalse(lock.writer_blocking_readers)

        # Within a read lock, the update lock is an upgrade to the write lock.
        lock.lock_read()
        lock.lock_update()
        self.assertTrue(lock.writer_blocking_readers)
        lock.unlock_update()
        self.assertFalse(lock.writer_blocking_readers)
        self.assertEqual(1, lock.reader_count)
        lock.unlock_read()
        self.assertEqual(0, lock.reader_count)

    def test_lock_update_downgrade(self):
        # The owner of the update lock returns from the write lock to the update lock while
        # other threads read, and takes the write lock again.
        lock = RWLock()
        order = []

        def reader():
            with lock.read_lock():
                order.append("read")

        def update():
            with lock.update_lock():
                self.assertFalse(lock.owns_upgraded_update_lock())
                lock.lock_read()
                with lock.write_lock():
                    self.assertTrue(lock.owns_upgraded_update_lock())
                    order.append("wrote")
                    holds = lock.downgrade_update()
                    self.assertFalse(lock.writer_blocking_readers)
                    self.assertFalse(lock.owns_upgraded_update_lock())
                    reader_thread = threading.Thread(target=reader)
                    reader_thread.start()
                    reader_thread.join()
                    lock.upgrade_update(holds)
                    self.assertTrue(lock.writer_blocking_readers)
                    self.assertTrue(lock.owns_upgraded_update_lock())
                    order.append("wrote again")
                    lock.lock_write()
                    self.assertFalse(lock.owns_upgraded_update_lock())
                    lock.unlock_write()
                lock.unlock_read()
                self.assertEqual(1, lock.reader_count)
            self.assertEqual(0, lock.reader_count)

        self.run_bounded(update)
        self.assertEqual(["wrote", "read", "wrote again"], order)
        self.assertFalse(lock.writer_blocking_readers)

    def test_lock_update_keeps_writers_out(self):
        # Readers do not wait for the update lock, writers do.
        lock = RWLock()
        order = []

        def reader():
            with lock.read_lock():
                order.append("read")

        def writer():
            with lock.write_lock():
                order.append("wrote")

        def update():
            with lock.update_lock():
                reader_thread = threading.Thread(target=reader)
                reader_thread.start()
                reader_thread.join()
                writer_thread = threading.Thread(target=writer)
                writer_thread.start()
                # Spin until the writer waits for the update lock.
                while not lock.writers_waiting_for_update:
                    pass
                order.append("releasing")
            writer_thread.join()

        self.run_bounded(update)
        self.assertEqual(["read", "releasing", "wrote"], order)
        self.assertEqual(0, lock.reader_count)
        self.assertFalse(lock.writer_blocking_readers)

    def test_lock_update_upgrade_waits_for_readers(self):
        # The upgrade waits for the other readers, new readers wait for the write lock
        # but not for the update lock.
        lock = RWLock()
        order = []
        reading = threading.Event()
        release_reader = threading.Event()

        def other_reader():
            with lock.read_lock():
                order.append("reading")
                reading.set()
                release_reader.wait()
                order.append("released read lock")

        def release_when_upgrading():
            self.wait_for_writer(lock)
            release_reader.set()

        def late_reader():
            with lock.read_lock():
                order.append("late reader")

        def update():
            reading.wait()
            with lock.update_lock():
                releaser = threading.Thread(target=release_when_upgrading)
                releaser.start()
                with lock.write_lock():
                    order.append("writing")
                    late = threading.Thread(target=late_reader)
                    late.start()
                    # Spin until the late reader waits for the write lock.
                    while not lock.readers_waiting_for_writer:
                        pass
                    order.append("downgrading")
                late.join()
                releaser.join()
                order.append("releasing update lock")

        with self.run_threads(other_reader):
            self.run_bounded(update)
        self.assertEqual(
            ["reading", "released read lock", "writing", "downgrading", "late reader",
             "releasing update lock"],
            order)
        self.assertEqual(0, lock.reader_count)
        self.assertFalse(lock.writer_blocking_readers)

    def test_lock_update_reserves_upgrade(self):
        # Other threads cannot upgrade their read locks while one thread holds the update lock,
        # which could then upgrade and wait for their read locks.
        lock = RWLock()
        updated = threading.Event()
        done = threading.Event()
        results = []

        def update():
            with lock.update_lock():
                updated.set()
                done.wait()

        def upgrade():
            updated.wait()
            try:
                with lock.read_lock():
                    try:
                        lock.lock_write()
                    except RuntimeError:
                        results.append("upgrade failed")
                    else:
                        lock.unlock_write()
                        results.append("upgraded")
            finally:
                done.set()

        def update_and_upgrade():
            with self.run_threads(update, upgrade):
                pass

        self.run_bounded(update_and_upgrade)
        self.assertEqual(["upgrade failed"], results)
        self.assertEqual(1, lock.get_perf_counters()['write_upgrade_conflict'])
        self.assertEqual(0, lock.reader_count)

    def test_lock_update_while_holding_read_and_writer_waits(self):
        # Like the upgrade, which lock_update() does when the thread holds the read lock.
        lock = RWLock()
        writer = threading.Thread(target=lambda: (lock.lock_write(), lock.unlock_write()))

        def update():
            with lock.read_lock():
                writer.start()
                self.wait_for_writer(lock)
                with self.assertRaises(RuntimeError):
                    lock.lock_update()
                self.assertEqual(1, lock.reader_count)
            writer.join()

        self.run_bounded(update)
        self.assertEqual(0, lock.reader_count)
        self.assertFalse(lock.writer_blocking_readers)

    @assert_perf_counters(write_acquired=3)
    def test_lock_write(self, lock):
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

    @assert_perf_counters(write_acquired=2, write_reentry=3)
    def test_lock_write_reentry(self, lock):
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

    @assert_perf_counters(write_acquired=2, write_wait_on_writer=1)
    def test_lock_write_wait_writers(self, lock):
        order = []

        start = threading.Barrier(2)
        release = threading.Event()

        def thread_lock():
            order.append("locking (1)")
            lock.lock_write()
            assert lock.writer_blocking_readers
            order.append("locked (1)")

            start.wait()
            order.append("waiting")

            release.wait()

            order.append("releasing (1)")
            lock.unlock_write()
            order.append("released (1)")

        def thread_wait():
            start.wait()
            order.append("waiting")

            lock.lock_write()
            order.append("locked (2)")
            lock.unlock_write()
            order.append("released (2)")

        with self.run_threads(thread_lock, thread_wait):
            # Release the first writer only when the second one waits for it.  (An event that
            # the second writer sets before calling lock_write() can let the first one release
            # the lock before, and then the second writer does not wait.)
            while not lock.writers_waiting_for_writer:
                pass
            release.set()

        self.assertListEqual(['locking (1)', 'locked (1)', 'waiting', 'waiting', 'releasing (1)'], order[:5])
        self.assertListEqual(['locked (2)', 'released (1)', 'released (2)'], sorted(order[5:]))

    def test_lock_write_wait_readers(self):
        lock = RWLock()

        order = []
        reader_ids = range(1, 10)

        start = threading.Barrier(len(reader_ids) + 1)
        waiting = threading.Barrier(len(reader_ids) + 1 + 1)
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

            waiting.wait()

            lock.lock_write()
            assert lock.writer_blocking_readers
            release.wait()
            order.append(f"locked (write)")
            assert lock.writer_blocking_readers
            lock.unlock_write()
            order.append(f"released (write)")

        readers = [partial(thread_lock_read, n) for n in reader_ids]

        with self.run_threads(thread_wait_write, *readers):
            waiting.wait()
            release.set()

        self.assertListEqual(
            [f'locked ({n})' for n in reader_ids] + [f'locking ({n})' for n in reader_ids] + [f'waiting ({n})' for n in reader_ids] + ["waiting (write)"],
            sorted(order[:3*len(reader_ids) + 1]))

        #self.assertListEqual(['locking (1)', 'locked (1)', 'waiting (2)', 'waiting (1)', 'releasing (1)'], order[:5])
        #self.assertListEqual(['locked (2)', 'released (1)', 'released (2)'], sorted(order[5:]))

    def test_concurrent_read_write_processing(self):
        lock = RWLock()

        memory = bytearray(range(50))
        failures = []

        def read():
            for i, ch in enumerate(memory, memory[0]):
                if ch != i:
                    failures.append(f"{ch} != {i}")

        def write():
            for i, ch in enumerate(memory):
                memory[i] = ch + 1

        def reader():
            start.wait()
            with lock.read_lock():
                read()

        def writer():
            start.wait()
            with lock.write_lock():
                write()

        def writereader():
            start.wait()
            with lock.write_lock():
                write()
                with lock.read_lock():
                    read()

        upgrade_conflicts = []

        def reader_writer():
            start.wait()
            with lock.read_lock():
                read()
                try:
                    lock.lock_write()
                except RuntimeError:
                    # Another thread waits for our read lock in order to write.
                    upgrade_conflicts.append(1)
                else:
                    try:
                        write()
                        read()
                    finally:
                        lock.unlock_write()
                read()

        threads = [reader, writer, writereader, reader_writer] * 25
        start = threading.Barrier(len(threads))

        def run_all():
            with self.run_threads(*threads):
                pass

        self.run_bounded(run_all)

        n_writers = len(threads) - threads.count(reader) - len(upgrade_conflicts)
        self.assertEqual(memory, bytearray(range(n_writers, n_writers + len(memory))))

        self.assertFalse(failures)

    def test_concurrent_read_write_update_processing(self):
        # Readers, writers, upgrading readers and update lock owners, which never fail to upgrade.
        lock = RWLock()

        memory = bytearray(range(50))
        failures = []

        def read():
            for i, ch in enumerate(memory, memory[0]):
                if ch != i:
                    failures.append(f"{ch} != {i}")

        def write():
            for i, ch in enumerate(memory):
                memory[i] = ch + 1

        def reader():
            start.wait()
            with lock.read_lock():
                read()

        def writer():
            start.wait()
            with lock.write_lock():
                write()

        upgrade_conflicts = []

        def reader_writer():
            start.wait()
            with lock.read_lock():
                read()
                try:
                    lock.lock_write()
                except RuntimeError:
                    upgrade_conflicts.append(1)
                else:
                    try:
                        write()
                    finally:
                        lock.unlock_write()
                read()

        def updater():
            start.wait()
            with lock.update_lock():
                read()
                with lock.read_lock():
                    with lock.write_lock():
                        write()
                        holds = lock.downgrade_update()
                        read()
                        lock.upgrade_update(holds)
                        read()
                    read()
                with lock.write_lock():
                    read()
                read()

        threads = [reader, writer, reader_writer, updater] * 20
        start = threading.Barrier(len(threads))

        def run_all():
            with self.run_threads(*threads):
                pass

        self.run_bounded(run_all)

        n_writers = (threads.count(writer) + threads.count(updater) + threads.count(reader_writer)
                     - len(upgrade_conflicts))
        self.assertEqual(memory, bytearray(range(n_writers, n_writers + len(memory))))
        self.assertFalse(failures)
        self.assertEqual(0, lock.reader_count)
        self.assertFalse(lock.writer_blocking_readers)

    def test_concurrent_read_write_locking(self):
        lock = RWLock()
        guard_lock = threading.Lock()

        # Thread monitoring:

        local = threading.local()

        reader_count = 0
        writer_count = 0

        def lock_read():
            nonlocal reader_count
            lock.lock_read()
            with guard_lock:
                reader_count += 1

        def unlock_read():
            nonlocal reader_count
            with guard_lock:
                reader_count -= 1
            lock.unlock_read()

        def lock_write():
            nonlocal writer_count
            lock.lock_write()
            writer_count += 1

        def unlock_write():
            nonlocal writer_count
            writer_count -= 1
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

        def rw_once():
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

        def rw_many():
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
                except Exception as exc:
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
                    failures.append(str(exc))

            return wrapped

        threads = [
            guard(func)
            for func in (
                read,
                write,
                #rw_once,
                #rw_many,
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
