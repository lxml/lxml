
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
cfg.verbosity = 1
cfg.basedir = test_base_path
cfg.unit_tests = True

def find_tests():
    test_files = test.get_test_files(cfg)
    return test.get_test_cases(test_files, cfg)

def run_tests(test_cases):
    print('Running subset of %d tests' % len(test_cases))
    pid = os.fork()
    if not pid:
        # child executes tests
        runner = test.CustomTestRunner(cfg, None)
        suite = unittest.TestSuite()
        suite.addTests(test_cases)
        os._exit( not runner.run(suite).wasSuccessful() )
    cid, retval = os.waitpid(pid, 0)
    retval >>= 8
    return retval == 0

def bisect_tests():
    tests = find_tests()
    print('Found %d tests' % len(tests))
    shift = len(tests) // 4
    while len(tests) > 1 and shift > 0:
        mid = len(tests) // 2 + 1
        left, right = tests[:mid], tests[mid:]

        if not run_tests(left):
            tests = left
            shift = len(tests) // 4 + 1
            break
        if not run_tests(right):
            tests = right
            shift = len(tests) // 4 + 1
            break

        shift //= 2
        tests = tests[shift:] + tests[:shift]
    # looks like we can't make the set of tests any smaller
    return tests

if __name__ == '__main__':
    print('\n'.join([test.id() for test in bisect_tests()]))
