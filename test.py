#!/usr/bin/env python2.3
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
SchoolTool test runner.

Syntax: test.py [options] [pathname-regexp [test-regexp]]

There are two kinds of tests:
  - unit tests (or programmer tests) test the internal workings of various
    components of the system
  - functional tests (acceptance tests, customer tests) test only externaly
    visible system behaviour

You can choose to run unit tests (this is the default mode), functional tests
(by giving a -f option to test.py) or both (by giving both -u and -f options).

Test cases are located in the directory tree starting at the location of this
script, in subdirectories named 'tests' for unit tests and 'ftests' for
functional tests, in Python modules named 'test*.py'.  They are then filtered
according to pathname and test regexes.  Alternatively, packages may just have
'tests.py' and 'ftests.py' instead of subpackages 'tests' and 'ftests'
respectively.

A leading "!" in a regexp is stripped and negates the regexp.  Pathname
regexp is applied to the whole path (package/package/module.py). Test regexp
is applied to a full test id (package.package.module.class.test_method).

Options:
  -h            print this help message
  -v            verbose (print dots for each test run)
  -vv           very verbose (print test names)
  -q            quiet (do not print anything on success)
  -w            enable warnings about omitted test cases
  -p            show progress bar (can be combined with -v or -vv)
  -u            select unit tests (default)
  -f            select functional tests
  --level n     select only tests at level n or lower
  --all-levels  select all tests
  --list-files  list all selected test files
  --list-tests  list all selected test cases
  --list-hooks  list all loaded test hooks
  --coverage    create code coverage reports
"""
#
# This script borrows ideas from Zope 3's test runner heavily.  It is smaller
# and cleaner though, at the expense of more limited functionality.
#

import re
import os
import sys
import time
import types
import getopt
import unittest
import traceback

try:
    set
except NameError:
    from sets import Set as set

try:
    # Python >=2.7 and >=3.2
    from unittest.runner import _TextTestResult
except ImportError:
    from unittest import _TextTestResult

__metaclass__ = type

def stderr(text):
    sys.stderr.write(text)
    sys.stderr.write("\n")

class Options:
    """Configurable properties of the test runner."""

    # test location
    basedir = ''                # base directory for tests (defaults to
                                # basedir of argv[0] + 'src'), must be absolute
    follow_symlinks = True      # should symlinks to subdirectories be
                                # followed? (hardcoded, may cause loops)

    # which tests to run
    unit_tests = False          # unit tests (default if both are false)
    functional_tests = False    # functional tests

    # test filtering
    level = 1                   # run only tests at this or lower level
                                # (if None, runs all tests)
    pathname_regex = ''         # regexp for filtering filenames
    test_regex = ''             # regexp for filtering test cases

    # actions to take
    list_files = False          # --list-files
    list_tests = False          # --list-tests
    list_hooks = False          # --list-hooks
    run_tests = True            # run tests (disabled by --list-foo)

    # output verbosity
    verbosity = 0               # verbosity level (-v)
    quiet = 0                   # do not print anything on success (-q)
    warn_omitted = False        # produce warnings when a test case is
                                # not included in a test suite (-w)
    progress = False            # show running progress (-p)
    coverage = False            # produce coverage reports (--coverage)
    coverdir = 'coverage'       # where to put them (currently hardcoded)
    immediate_errors = False    # show tracebacks twice (currently hardcoded)
    screen_width = 80           # screen width (autodetected)


def compile_matcher(regex):
    """Returns a function that takes one argument and returns True or False.

    Regex is a regular expression.  Empty regex matches everything.  There
    is one expression: if the regex starts with "!", the meaning of it is
    reversed.
    """
    if not regex:
        return lambda x: True
    elif regex == '!':
        return lambda x: False
    elif regex.startswith('!'):
        rx = re.compile(regex[1:])
        return lambda x: rx.search(x) is None
    else:
        rx = re.compile(regex)
        return lambda x: rx.search(x) is not None


def walk_with_symlinks(top, func, arg):
    """Like os.path.walk, but follows symlinks on POSIX systems.

    If the symlinks create a loop, this function will never finish.
    """
    try:
        names = os.listdir(top)
    except os.error:
        return
    func(arg, top, names)
    exceptions = ('.', '..')
    for name in names:
        if name not in exceptions:
            name = os.path.join(top, name)
            if os.path.isdir(name):
                walk_with_symlinks(name, func, arg)


def get_test_files(cfg):
    """Returns a list of test module filenames."""
    matcher = compile_matcher(cfg.pathname_regex)
    results = []
    test_names = []
    if cfg.unit_tests:
        test_names.append('tests')
    if cfg.functional_tests:
        test_names.append('ftests')
    baselen = len(cfg.basedir) + 1
    def visit(ignored, dir, files):
        if os.path.basename(dir) not in test_names:
            for name in test_names:
                if name + '.py' in files:
                    path = os.path.join(dir, name + '.py')
                    if matcher(path[baselen:]):
                        results.append(path)
            return
        if '__init__.py' not in files:
            stderr("%s is not a package" % dir)
            return
        for file in files:
            if file.startswith('test') and file.endswith('.py'):
                path = os.path.join(dir, file)
                if matcher(path[baselen:]):
                    results.append(path)
    if cfg.follow_symlinks:
        walker = walk_with_symlinks
    else:
        walker = os.path.walk
    walker(cfg.basedir, visit, None)
    results.sort()
    return results


def import_module(filename, cfg, tracer=None):
    """Imports and returns a module."""
    filename = os.path.splitext(filename)[0]
    modname = filename[len(cfg.basedir):].replace(os.path.sep, '.')
    if modname.startswith('.'):
        modname = modname[1:]
    if tracer is not None:
        mod = tracer.runfunc(__import__, modname)
    else:
        mod = __import__(modname)
    components = modname.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


def filter_testsuite(suite, matcher, level=None):
    """Returns a flattened list of test cases that match the given matcher."""
    if not isinstance(suite, unittest.TestSuite):
        raise TypeError('not a TestSuite', suite)
    results = []
    for test in suite._tests:
        if level is not None and getattr(test, 'level', 0) > level:
            continue
        if isinstance(test, unittest.TestCase):
            testname = test.id() # package.module.class.method
            if matcher(testname):
                results.append(test)
        else:
            filtered = filter_testsuite(test, matcher, level)
            results.extend(filtered)
    return results


def get_all_test_cases(module):
    """Returns a list of all test case classes defined in a given module."""
    results = []
    for name in dir(module):
        if not name.startswith('Test'):
            continue
        item = getattr(module, name)
        if (isinstance(item, (type, types.ClassType)) and
            issubclass(item, unittest.TestCase)):
            results.append(item)
    return results


def get_test_classes_from_testsuite(suite):
    """Returns a set of test case classes used in a test suite."""
    if not isinstance(suite, unittest.TestSuite):
        raise TypeError('not a TestSuite', suite)
    results = set()
    for test in suite._tests:
        if isinstance(test, unittest.TestCase):
            results.add(test.__class__)
        else:
            classes = get_test_classes_from_testsuite(test)
            results.update(classes)
    return results


def get_test_cases(test_files, cfg, tracer=None):
    """Returns a list of test cases from a given list of test modules."""
    matcher = compile_matcher(cfg.test_regex)
    results = []
    for file in test_files:
        module = import_module(file, cfg, tracer=tracer)
        if tracer is not None:
            test_suite = tracer.runfunc(module.test_suite)
        else:
            test_suite = module.test_suite()
        if test_suite is None:
            continue
        if cfg.warn_omitted:
            all_classes = set(get_all_test_cases(module))
            classes_in_suite = get_test_classes_from_testsuite(test_suite)
            difference = all_classes - classes_in_suite
            for test_class in difference:
                # surround the warning with blank lines, otherwise it tends
                # to get lost in the noise
                stderr("\n%s: WARNING: %s not in test suite\n"
                                      % (file, test_class.__name__))
        if (cfg.level is not None and
            getattr(test_suite, 'level', 0) > cfg.level):
            continue
        filtered = filter_testsuite(test_suite, matcher, cfg.level)
        results.extend(filtered)
    return results


def get_test_hooks(test_files, cfg, tracer=None):
    """Returns a list of test hooks from a given list of test modules."""
    results = []
    dirs = set(map(os.path.dirname, test_files))
    for dir in list(dirs):
        if os.path.basename(dir) == 'ftests':
            dirs.add(os.path.join(os.path.dirname(dir), 'tests'))
    dirs = list(dirs)
    dirs.sort()
    for dir in dirs:
        filename = os.path.join(dir, 'checks.py')
        if os.path.exists(filename):
            module = import_module(filename, cfg, tracer=tracer)
            if tracer is not None:
                hooks = tracer.runfunc(module.test_hooks)
            else:
                hooks = module.test_hooks()
            results.extend(hooks)
    return results


class CustomTestResult(_TextTestResult):
    """Customised TestResult.

    It can show a progress bar, and displays tracebacks for errors and failures
    as soon as they happen, in addition to listing them all at the end.
    """

    __super = _TextTestResult
    __super_init = __super.__init__
    __super_startTest = __super.startTest
    __super_stopTest = __super.stopTest
    __super_printErrors = __super.printErrors

    def __init__(self, stream, descriptions, verbosity, count, cfg, hooks):
        self.__super_init(stream, descriptions, verbosity)
        self.count = count
        self.cfg = cfg
        self.hooks = hooks
        if cfg.progress:
            self.dots = False
            self._lastWidth = 0
            self._maxWidth = cfg.screen_width - len("xxxx/xxxx (xxx.x%): ") - 1

    def startTest(self, test):
        if self.cfg.progress:
            # verbosity == 0: 'xxxx/xxxx (xxx.x%)'
            # verbosity == 1: 'xxxx/xxxx (xxx.x%): test name'
            # verbosity >= 2: 'xxxx/xxxx (xxx.x%): test name ... ok'
            n = self.testsRun + 1
            self.stream.write("\r%4d" % n)
            if self.count:
                self.stream.write("/%d (%5.1f%%)"
                                  % (self.count, n * 100.0 / self.count))
            if self.showAll: # self.cfg.verbosity == 1
                self.stream.write(": ")
            elif self.cfg.verbosity:
                name = self.getShortDescription(test)
                width = len(name)
                if width < self._lastWidth:
                    name += " " * (self._lastWidth - width)
                self.stream.write(": %s" % name)
                self._lastWidth = width
            self.stream.flush()
        self.__super_startTest(test)
        for hook in self.hooks:
            hook.startTest(test)

    def stopTest(self, test):
        for hook in self.hooks:
            hook.stopTest(test)
        self.__super_stopTest(test)

    def getShortDescription(self, test):
        s = self.getDescription(test)
        if len(s) > self._maxWidth:
            # s is 'testname (package.module.class)'
            # try to shorten it to 'testname (...age.module.class)'
            # if it is still too long, shorten it to 'testnam...'
            # limit case is 'testname (...)'
            pos = s.find(" (")
            if pos + len(" (...)") > self._maxWidth:
                s = s[:self._maxWidth - 3] + "..."
            else:
                s = "%s...%s" % (s[:pos + 2], s[pos + 5 - self._maxWidth:])
        return s

    def printErrors(self):
        if self.cfg.progress and not (self.dots or self.showAll):
            self.stream.writeln()
        self.__super_printErrors()

    def formatError(self, err):
        return "".join(traceback.format_exception(*err))

    def printTraceback(self, kind, test, err):
        self.stream.writeln()
        self.stream.writeln()
        self.stream.writeln("%s: %s" % (kind, test))
        self.stream.writeln(self.formatError(err))
        self.stream.writeln()

    def addFailure(self, test, err):
        if self.cfg.immediate_errors:
            self.printTraceback("FAIL", test, err)
        self.failures.append((test, self.formatError(err)))

    def addError(self, test, err):
        if self.cfg.immediate_errors:
            self.printTraceback("ERROR", test, err)
        self.errors.append((test, self.formatError(err)))


class CustomTestRunner(unittest.TextTestRunner):
    """Customised TestRunner.

    See CustomisedTextResult for a list of extensions.
    """

    __super = unittest.TextTestRunner
    __super_init = __super.__init__
    __super_run = __super.run

    def __init__(self, cfg, hooks=None):
        self.__super_init(verbosity=cfg.verbosity)
        self.cfg = cfg
        if hooks is not None:
            self.hooks = hooks
        else:
            self.hooks = []

    def run(self, test):
        """Run the given test case or test suite."""
        self.count = test.countTestCases()
        result = self._makeResult()
        startTime = time.time()
        test(result)
        stopTime = time.time()
        timeTaken = float(stopTime - startTime)
        result.printErrors()
        run = result.testsRun
        if not self.cfg.quiet:
            self.stream.writeln(result.separator2)
            self.stream.writeln("Ran %d test%s in %.3fs" %
                                (run, run != 1 and "s" or "", timeTaken))
            self.stream.writeln()
        if not result.wasSuccessful():
            self.stream.write("FAILED (")
            failed, errored = list(map(len, (result.failures, result.errors)))
            if failed:
                self.stream.write("failures=%d" % failed)
            if errored:
                if failed: self.stream.write(", ")
                self.stream.write("errors=%d" % errored)
            self.stream.writeln(")")
        elif not self.cfg.quiet:
            self.stream.writeln("OK")
        return result

    def _makeResult(self):
        return CustomTestResult(self.stream, self.descriptions, self.verbosity,
                                cfg=self.cfg, count=self.count,
                                hooks=self.hooks)


def main(argv):
    """Main program."""

    # Environment
    if sys.version_info < (2, 3):
        stderr('%s: need Python 2.3 or later' % argv[0])
        stderr('your python is %s' % sys.version)
        return 1

    # Defaults
    cfg = Options()
    cfg.basedir = os.path.join(os.path.dirname(argv[0]), 'src')
    cfg.basedir = os.path.abspath(cfg.basedir)

    # Figure out terminal size
    try:
        import curses
    except ImportError:
        pass
    else:
        try:
            curses.setupterm()
            cols = curses.tigetnum('cols')
            if cols > 0:
                cfg.screen_width = cols
        except curses.error:
            pass

    # Option processing
    opts, args = getopt.gnu_getopt(argv[1:], 'hvpqufw',
                                   ['list-files', 'list-tests', 'list-hooks',
                                    'level=', 'all-levels', 'coverage'])
    for k, v in opts:
        if k == '-h':
            print(__doc__)
            return 0
        elif k == '-v':
            cfg.verbosity += 1
            cfg.quiet = False
        elif k == '-p':
            cfg.progress = True
            cfg.quiet = False
        elif k == '-q':
            cfg.verbosity = 0
            cfg.progress = False
            cfg.quiet = True
        elif k == '-u':
            cfg.unit_tests = True
        elif k == '-f':
            cfg.functional_tests = True
        elif k == '-w':
            cfg.warn_omitted = True
        elif k == '--list-files':
            cfg.list_files = True
            cfg.run_tests = False
        elif k == '--list-tests':
            cfg.list_tests = True
            cfg.run_tests = False
        elif k == '--list-hooks':
            cfg.list_hooks = True
            cfg.run_tests = False
        elif k == '--coverage':
            cfg.coverage = True
        elif k == '--level':
            try:
                cfg.level = int(v)
            except ValueError:
                stderr('%s: invalid level: %s' % (argv[0], v))
                stderr('run %s -h for help')
                return 1
        elif k == '--all-levels':
            cfg.level = None
        else:
            stderr('%s: invalid option: %s' % (argv[0], k))
            stderr('run %s -h for help')
            return 1
    if args:
        cfg.pathname_regex = args[0]
    if len(args) > 1:
        cfg.test_regex = args[1]
    if len(args) > 2:
        stderr('%s: too many arguments: %s' % (argv[0], args[2]))
        stderr('run %s -h for help')
        return 1
    if not cfg.unit_tests and not cfg.functional_tests:
        cfg.unit_tests = True

    # Set up the python path
    sys.path[0] = cfg.basedir

    # Set up tracing before we start importing things
    tracer = None
    if cfg.run_tests and cfg.coverage:
        import trace
        # trace.py in Python 2.3.1 is buggy:
        # 1) Despite sys.prefix being in ignoredirs, a lot of system-wide
        #    modules are included in the coverage reports
        # 2) Some module file names do not have the first two characters,
        #    and in general the prefix used seems to be arbitrary
        # These bugs are fixed in src/trace.py which should be in PYTHONPATH
        # before the official one.
        ignoremods = ['test']
        ignoredirs = [sys.prefix, sys.exec_prefix]
        tracer = trace.Trace(count=True, trace=False,
                    ignoremods=ignoremods, ignoredirs=ignoredirs)

    # Finding and importing
    test_files = get_test_files(cfg)
    if cfg.list_tests or cfg.run_tests:
        test_cases = get_test_cases(test_files, cfg, tracer=tracer)
    if cfg.list_hooks or cfg.run_tests:
        test_hooks = get_test_hooks(test_files, cfg, tracer=tracer)

    # Configure the logging module
    import logging
    logging.basicConfig()
    logging.root.setLevel(logging.CRITICAL)

    # Running
    success = True
    if cfg.list_files:
        baselen = len(cfg.basedir) + 1
        print("\n".join([fn[baselen:] for fn in test_files]))
    if cfg.list_tests:
        print("\n".join([test.id() for test in test_cases]))
    if cfg.list_hooks:
        print("\n".join([str(hook) for hook in test_hooks]))
    if cfg.run_tests:
        runner = CustomTestRunner(cfg, test_hooks)
        suite = unittest.TestSuite()
        suite.addTests(test_cases)
        if tracer is not None:
            success = tracer.runfunc(runner.run, suite).wasSuccessful()
            results = tracer.results()
            results.write_results(show_missing=True, coverdir=cfg.coverdir)
        else:
            success = runner.run(suite).wasSuccessful()

    # That's all
    if success:
        return 0
    else:
        return 1


if __name__ == '__main__':
    exitcode = main(sys.argv)
    sys.exit(exitcode)
