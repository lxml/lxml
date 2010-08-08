
import os
import sys
import unittest

# make sure we import test.py from the right place
script_path = os.path.abspath(os.path.dirname(sys.argv[0]))
sys.path.insert(0, script_path)

test_base_path = os.path.join(script_path, 'src')
sys.path.insert(1, test_base_path)

import test
from DD import DD

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

class DDTester(DD):
    def _test(self, test_cases):
        if not test_cases:
            return self.PASS
        write('Running subset of %d tests %s',
              len(test_cases), self.coerce(test_cases))
        test_cases = [ item[-1] for item in test_cases ]
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
        if (retval % 0xFF) > 2: # signal received?
            return self.FAIL
        return self.PASS

    def coerce(self, test_cases):
        if not test_cases:
            return '[]'
        test_cases = [ item[-1] for item in test_cases ]
        return '[%s .. %s]' % (test_cases[0].id(), test_cases[-1].id())

def dd_tests():
    tests = find_tests()
    write('Found %d tests', len(tests))
    dd = DDTester()
    min_tests = dd.ddmin( list(enumerate(tests)) )
    return [ item[-1] for item in min_tests ]

if __name__ == '__main__':
    write('Failing tests:\n%s', '\n'.join([test.id() for test in dd_tests()]))
