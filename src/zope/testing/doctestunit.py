##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Extension to use doctest tests as unit tests

This module provides a DocTestSuite contructor for converting doctest
tests to unit tests.

$Id: doctestunit.py,v 1.1 2004/05/28 18:08:58 faassen Exp $
"""

from StringIO import StringIO
import doctest
import os
import pdb
import sys
import tempfile
import unittest


class DocTestTestCase(unittest.TestCase):
    """A test case that wraps a test function.

    This is useful for slipping pre-existing test functions into the
    PyUnit framework. Optionally, set-up and tidy-up functions can be
    supplied. As with TestCase, the tidy-up ('tearDown') function will
    always be called if the set-up ('setUp') function ran successfully.
    """

    def __init__(self, tester, name, doc, filename, lineno,
                 setUp=None, tearDown=None):
        unittest.TestCase.__init__(self)
        (self.__tester, self.__name, self.__doc,
         self.__filename, self.__lineno,
         self.__setUp, self.__tearDown
         ) = tester, name, doc, filename, lineno, setUp, tearDown

    def setUp(self):
        if self.__setUp is not None:
            self.__setUp()

    def tearDown(self):
        if self.__tearDown is not None:
            self.__tearDown()

    def setDebugModeOn(self):
        self.__tester.optionflags |= (
            doctest.RUN_DEBUGGER_ON_UNEXPECTED_EXCEPTION)

    def runTest(self):
        old = sys.stdout
        new = StringIO()
        try:
            sys.stdout = new
            failures, tries = self.__tester.runstring(self.__doc, self.__name)
        finally:
            sys.stdout = old

        if failures:
            lname = '.'.join(self.__name.split('.')[-1:])
            lineno = self.__lineno or "0 (don't know line no)"
            raise self.failureException(
                'Failed doctest test for %s\n'
                '  File "%s", line %s, in %s\n\n%s'
                % (self.__name, self.__filename, lineno, lname, new.getvalue())
                )

    def id(self):
        return self.__name

    def __repr__(self):
        name = self.__name.split('.')
        return "%s (%s)" % (name[-1], '.'.join(name[:-1]))

    __str__ = __repr__

    def shortDescription(self):
        return "Doctest: " + self.__name

def DocFileSuite(package, *paths):
    """Creates a suite of doctest files.
    
    package is the source package containing the doctest files.
    
    Each subsequent argument is a string specifying the file name of the
    doctest relative to the package.
    """
    
    # It's not entirely obvious how to connection this single string
    # with unittest.  For now, re-use the _utest() function that comes
    # standard with doctest in Python 2.3.  One problem is that the
    # error indicator doesn't point to the line of the doctest file
    # that failed.
    import os, doctest, new
    t = doctest.Tester(globs={})
    suite = unittest.TestSuite()
    dir = os.path.split(package.__file__)[0]
    for path in paths:
        path = os.path.join(dir, path)
        source = open(path).read()
        def runit(path=path, source=source):
            doctest._utest(t, path, source, path, 0)
        runit = new.function(runit.func_code, runit.func_globals, path,
                             runit.func_defaults, runit.func_closure)
        f = unittest.FunctionTestCase(runit,
                                      description="doctest from %s" % path)
        suite.addTest(f)
    return suite

def DocTestSuite(module=None,
                 setUp=lambda: None,
                 tearDown=lambda: None,
                 ):
    """Convert doctest tests for a mudule to a unittest test suite

    This tests convers each documentation string in a module that
    contains doctest tests to a unittest test case. If any of the
    tests in a doc string fail, then the test case fails. An error is
    raised showing the name of the file containing the test and a
    (sometimes approximate) line number.

    A module argument provides the module to be tested. The argument
    can be either a module or a module name.

    If no argument is given, the calling module is used.

    """
    module = _normalizeModule(module)
    tests = _findTests(module)

    if not tests:
        raise ValueError(module, "has no tests")

    tests.sort()
    suite = unittest.TestSuite()
    tester = doctest.Tester(module)
    for name, doc, filename, lineno in tests:
        if not filename:
            filename = module.__file__
            if filename.endswith(".pyc"):
                filename = filename[:-1]
            elif filename.endswith(".pyo"):
                filename = filename[:-1]

        suite.addTest(DocTestTestCase(
            tester, name, doc, filename, lineno,
            setUp, tearDown))


    return suite

def _normalizeModule(module):
    # Normalize a module
    if module is None:
        # Test the calling module
        module = sys._getframe(2).f_globals['__name__']
        module = sys.modules[module]

    elif isinstance(module, (str, unicode)):
        module = __import__(module, globals(), locals(), ["*"])

    return module

def _doc(name, object, tests, prefix, filename='', lineno=''):
    doc = getattr(object, '__doc__', '')
    if doc and doc.find('>>>') >= 0:
        tests.append((prefix+name, doc, filename, lineno))


def _findTests(module, prefix=None):
    if prefix is None:
        prefix = module.__name__
    dict = module.__dict__
    tests = []
    _doc(prefix, module, tests, '',
         lineno="1 (or below)")
    prefix = prefix and (prefix + ".")
    _find(dict.items(), module, dict, tests, prefix)
    return tests

def _find(items, module, dict, tests, prefix, minlineno=0):
    for name, object in items:

        # Only interested in named objects
        if not hasattr(object, '__name__'):
            continue

        if hasattr(object, 'func_globals'):
            # Looks like a func
            if object.func_globals is not dict:
                # Non-local func
                continue
            code = getattr(object, 'func_code', None)
            filename = getattr(code, 'co_filename', '')
            lineno = getattr(code, 'co_firstlineno', -1) + 1
            if minlineno:
                minlineno = min(lineno, minlineno)
            else:
                minlineno = lineno
            _doc(name, object, tests, prefix, filename, lineno)

        elif hasattr(object, "__module__"):
            # Maybe a class-like things. In which case, we care
            if object.__module__ != module.__name__:
                continue # not the same module
            if not (hasattr(object, '__dict__')
                    and hasattr(object, '__bases__')):
                continue # not a class

            lineno = _find(object.__dict__.items(), module, dict, tests,
                           prefix+name+".")

            _doc(name, object, tests, prefix,
                 lineno="%s (or above)" % (lineno-3))

    return minlineno




####################################################################
# doctest debugger

def _expect(expect):
    # Return the expected output, if any
    if expect:
        expect = "\n# ".join(expect.split("\n"))
        expect = "\n# Expect:\n# %s" % expect
    return expect

def testsource(module, name):
    """Extract the test sources from a doctest test docstring as a script

    Provide the module (or dotted name of the module) containing the
    test to be debugged and the name (within the module) of the object
    with the doc string with tests to be debugged.

    """
    module = _normalizeModule(module)
    tests = _findTests(module, "")
    test = [doc for (tname, doc, f, l) in tests if tname == name]
    if not test:
        raise ValueError(name, "not found in tests")
    test = test[0]
    # XXX we rely on an internal doctest function:
    examples = doctest._extract_examples(test)
    testsrc = '\n'.join([
        "%s%s" % (source, _expect(expect))
        for (source, expect, lineno) in examples
        ])
    return testsrc

def debug_src(src, pm=False, globs=None):
    """Debug a single doctest test doc string

    The string is provided directly
    """
    # XXX we rely on an internal doctest function:
    examples = doctest._extract_examples(src)
    src = '\n'.join([
        "%s%s" % (source, _expect(expect))
        for (source, expect, lineno) in examples
        ])
    debug_script(src, pm, globs)

def debug_script(src, pm=False, globs=None):
    "Debug a test script"
    srcfilename = tempfile.mktemp("doctestdebug.py")
    open(srcfilename, 'w').write(src)
    if globs:
        globs = globs.copy()
    else:
        globs = {}

    try:
        if pm:
            try:
                execfile(srcfilename, globs, globs)
            except:
                print sys.exc_info()[1]
                pdb.post_mortem(sys.exc_info()[2])
        else:
            # Note that %r is vital here.  '%s' instead can, e.g., cause
            # backslashes to get treated as metacharacters on Windows.
            pdb.run("execfile(%r)" % srcfilename, globs, globs)
    finally:
        os.remove(srcfilename)

def debug(module, name, pm=False):
    """Debug a single doctest test doc string

    Provide the module (or dotted name of the module) containing the
    test to be debugged and the name (within the module) of the object
    with the doc string with tests to be debugged.

    """
    module = _normalizeModule(module)
    testsrc = testsource(module, name)
    debug_script(testsrc, pm, module.__dict__)
