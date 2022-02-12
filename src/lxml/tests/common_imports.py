"""
Common helpers and adaptations for Py2/3.
To be used in tests.
"""

# Slows down test runs by factors. Enable to debug proxy handling issues.
DEBUG_PROXY_ISSUES = False  # True

import gc
import os
import os.path
import re
import sys
import tempfile
import unittest
from contextlib import contextmanager

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse 

try:
    from urllib import pathname2url
except:
    from urllib.request import pathname2url

from lxml import etree, html

def make_version_tuple(version_string):
    return tuple(
        int(part) if part.isdigit() else part
        for part in re.findall('([0-9]+|[^0-9.]+)', version_string)
    )

IS_PYPY = (getattr(sys, 'implementation', None) == 'pypy' or
           getattr(sys, 'pypy_version_info', None) is not None)

IS_PYTHON3 = sys.version_info[0] >= 3
IS_PYTHON2 = sys.version_info[0] < 3

from xml.etree import ElementTree

if hasattr(ElementTree, 'VERSION'):
    ET_VERSION = make_version_tuple(ElementTree.VERSION)
else:
    ET_VERSION = (0,0,0)

if IS_PYTHON2:
    from xml.etree import cElementTree

    if hasattr(cElementTree, 'VERSION'):
        CET_VERSION = make_version_tuple(cElementTree.VERSION)
    else:
        CET_VERSION = (0,0,0)
else:
    CET_VERSION = (0, 0, 0)
    cElementTree = None


def filter_by_version(test_class, version_dict, current_version):
    """Remove test methods that do not work with the current lib version.
    """
    find_required_version = version_dict.get
    def dummy_test_method(self):
        pass
    for name in dir(test_class):
        expected_version = find_required_version(name, (0,0,0))
        if expected_version > current_version:
            setattr(test_class, name, dummy_test_method)


def needs_libxml(*version):
    return unittest.skipIf(
        etree.LIBXML_VERSION < version,
        "needs libxml2 >= %s.%s.%s" % (version + (0, 0, 0))[:3])


import doctest

try:
    import pytest
except ImportError:
    class skipif(object):
        "Using a class because a function would bind into a method when used in classes"
        def __init__(self, *args): pass
        def __call__(self, func, *args): return func
else:
    skipif = pytest.mark.skipif

def _get_caller_relative_path(filename, frame_depth=2):
    module = sys.modules[sys._getframe(frame_depth).f_globals['__name__']]
    return os.path.normpath(os.path.join(
            os.path.dirname(getattr(module, '__file__', '')), filename))

from io import StringIO

unichr_escape = re.compile(r'\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}')

if sys.version_info[0] >= 3:
    # Python 3
    from builtins import str as unicode
    from codecs import unicode_escape_decode
    _chr = chr
    def _str(s, encoding="UTF-8"):
        return unichr_escape.sub(lambda x: unicode_escape_decode(x.group(0))[0], s)
    def _bytes(s, encoding="UTF-8"):
        return s.encode(encoding)
    from io import BytesIO as _BytesIO
    def BytesIO(*args):
        if args and isinstance(args[0], str):
            args = (args[0].encode("UTF-8"),)
        return _BytesIO(*args)

    doctest_parser = doctest.DocTestParser()
    _fix_unicode = re.compile(r'(\s+)u(["\'])').sub
    _fix_exceptions = re.compile(r'(.*except [^(]*),\s*(.*:)').sub
    def make_doctest(filename):
        filename = _get_caller_relative_path(filename)
        doctests = read_file(filename)
        doctests = _fix_unicode(r'\1\2', doctests)
        doctests = _fix_exceptions(r'\1 as \2', doctests)
        return doctest.DocTestCase(
            doctest_parser.get_doctest(
                doctests, {}, os.path.basename(filename), filename, 0))
else:
    # Python 2
    from __builtin__ import unicode
    _chr = unichr
    def _str(s, encoding="UTF-8"):
        s = unicode(s, encoding=encoding)
        return unichr_escape.sub(lambda x:
                                     x.group(0).decode('unicode-escape'),
                                 s)
    def _bytes(s, encoding="UTF-8"):
        return s
    from io import BytesIO

    doctest_parser = doctest.DocTestParser()
    _fix_traceback = re.compile(r'^(\s*)(?:\w+\.)+(\w*(?:Error|Exception|Invalid):)', re.M).sub
    _fix_exceptions = re.compile(r'(.*except [^(]*)\s+as\s+(.*:)').sub
    _fix_bytes = re.compile(r'(\s+)b(["\'])').sub
    def make_doctest(filename):
        filename = _get_caller_relative_path(filename)
        doctests = read_file(filename)
        doctests = _fix_traceback(r'\1\2', doctests)
        doctests = _fix_exceptions(r'\1, \2', doctests)
        doctests = _fix_bytes(r'\1\2', doctests)
        return doctest.DocTestCase(
            doctest_parser.get_doctest(
                doctests, {}, os.path.basename(filename), filename, 0))

try:
    skipIf = unittest.skipIf
except AttributeError:
    def skipIf(condition, why):
        def _skip(thing):
            import types
            if isinstance(thing, (type, types.ClassType)):
                return type(thing.__name__, (object,), {})
            else:
                return None
        if condition:
            return _skip
        return lambda thing: thing


class HelperTestCase(unittest.TestCase):
    def tearDown(self):
        if DEBUG_PROXY_ISSUES:
            gc.collect()

    def parse(self, text, parser=None):
        f = BytesIO(text) if isinstance(text, bytes) else StringIO(text)
        return etree.parse(f, parser=parser)
    
    def _rootstring(self, tree):
        return etree.tostring(tree.getroot()).replace(
            _bytes(' '), _bytes('')).replace(_bytes('\n'), _bytes(''))


class SillyFileLike:
    def __init__(self, xml_data=_bytes('<foo><bar/></foo>')):
        self.xml_data = xml_data
        
    def read(self, amount=None):
        if self.xml_data:
            if amount:
                data = self.xml_data[:amount]
                self.xml_data = self.xml_data[amount:]
            else:
                data = self.xml_data
                self.xml_data = _bytes('')
            return data
        return _bytes('')

class LargeFileLike:
    def __init__(self, charlen=100, depth=4, children=5):
        self.data = BytesIO()
        self.chars  = _bytes('a') * charlen
        self.children = range(children)
        self.more = self.iterelements(depth)

    def iterelements(self, depth):
        yield _bytes('<root>')
        depth -= 1
        if depth > 0:
            for child in self.children:
                for element in self.iterelements(depth):
                    yield element
                yield self.chars
        else:
            yield self.chars
        yield _bytes('</root>')

    def read(self, amount=None):
        data = self.data
        append = data.write
        if amount:
            for element in self.more:
                append(element)
                if data.tell() >= amount:
                    break
        else:
            for element in self.more:
                append(element)
        result = data.getvalue()
        data.seek(0)
        data.truncate()
        if amount:
            append(result[amount:])
            result = result[:amount]
        return result

class LargeFileLikeUnicode(LargeFileLike):
    def __init__(self, charlen=100, depth=4, children=5):
        LargeFileLike.__init__(self, charlen, depth, children)
        self.data = StringIO()
        self.chars  = _str('a') * charlen
        self.more = self.iterelements(depth)

    def iterelements(self, depth):
        yield _str('<root>')
        depth -= 1
        if depth > 0:
            for child in self.children:
                for element in self.iterelements(depth):
                    yield element
                yield self.chars
        else:
            yield self.chars
        yield _str('</root>')

class SimpleFSPath(object):
    def __init__(self, path):
        self.path = path
    def __fspath__(self):
        return self.path

def fileInTestDir(name):
    _testdir = os.path.dirname(__file__)
    return os.path.join(_testdir, name)

def path2url(path):
    return urlparse.urljoin(
        'file:', pathname2url(path))

def fileUrlInTestDir(name):
    return path2url(fileInTestDir(name))

def read_file(name, mode='r'):
    with open(name, mode) as f:
        data = f.read()
    return data

def write_to_file(name, data, mode='w'):
    with open(name, mode) as f:
        f.write(data)

def readFileInTestDir(name, mode='r'):
    return read_file(fileInTestDir(name), mode)

def canonicalize(xml):
    tree = etree.parse(BytesIO(xml) if isinstance(xml, bytes) else StringIO(xml))
    f = BytesIO()
    tree.write_c14n(f)
    return f.getvalue()


@contextmanager
def tmpfile(**kwargs):
    handle, filename = tempfile.mkstemp(**kwargs)
    try:
        yield filename
    finally:
        os.close(handle)
        os.remove(filename)
