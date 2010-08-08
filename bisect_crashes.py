
import os
import sys
import unittest

# make sure we import test.py from the right place
script_path = os.path.abspath(os.path.dirname(sys.argv[0]))
sys.path.insert(0, script_path)

test_base_path = os.path.join(script_path, 'src')
sys.path.insert(1, test_base_path)

import test

cfg = test.Options()
cfg.verbosity = 0
cfg.basedir = test_base_path
cfg.unit_tests = True

def write(line, *args):
    if args:
        line = line % args
    sys.stderr.write(line + '\n')


def find_tests():
    test_files = test.get_test_files(cfg)
    return test.get_test_cases(test_files, cfg)

def run_tests(test_cases):
    if not test_cases:
        return True
    write('Running subset of %d tests [%s .. %s]',
          len(test_cases), test_cases[0].id(), test_cases[-1].id())
    pid = os.fork()
    if not pid:
        # child executes tests
        runner = test.CustomTestRunner(cfg, None)
        suite = unittest.TestSuite()
        suite.addTests(test_cases)
        os._exit( not runner.run(suite).wasSuccessful() )
    cid, retval = os.waitpid(pid, 0)
    if retval:
        write('exit status: %d, signal: %d', retval >> 8, retval % 0xFF)
    return (retval % 0xFF) == 0 # signal

def bisect_tests():
    tests = find_tests()
    write('Found %d tests', len(tests))
    shift = len(tests) // 4
    last_failed = False
    while len(tests) > 1 and shift > 0:
        mid = len(tests) // 2 + 1
        left, right = tests[:mid], tests[mid:]

        if not run_tests(left):
            last_failed = True
            tests = left
            shift = len(tests) // 4 + 1
        elif not run_tests(right):
            last_failed = True
            tests = right
            shift = len(tests) // 4 + 1
        else:
            # retry
            last_failed = False
            shift //= 2
            tests = tests[shift:] + tests[:shift]
    # looks like we can't make the set of tests any smaller
    return last_failed and tests or []

if __name__ == '__main__':
    write('Failing tests:\n%s', '\n'.join([test.id() for test in bisect_tests()]))
