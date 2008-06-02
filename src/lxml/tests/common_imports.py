import unittest
import os.path
import re, gc, sys

from lxml import etree

def make_version_tuple(version_string):
    l = []
    for part in re.findall('([0-9]+|[^0-9.]+)', version_string):
        try:
            l.append(int(part))
        except ValueError:
            l.append(part)
    return tuple(l)

try:
    from elementtree import ElementTree # standard ET
except ImportError:
    try:
        from xml.etree import ElementTree # Python 2.5+
    except ImportError:
        ElementTree = None

if hasattr(ElementTree, 'VERSION'):
    if make_version_tuple(ElementTree.VERSION)[:2] < (1,3):
        # compatibility tests require ET 1.3+
        ElementTree = None

try:
    import cElementTree # standard ET
except ImportError:
    try:
        from xml.etree import cElementTree # Python 2.5+
    except ImportError:
        cElementTree = None

if hasattr(cElementTree, 'VERSION'):
    if make_version_tuple(cElementTree.VERSION)[:2] <= (1,0):
        # compatibility tests do not run with cET 1.0.7
        cElementTree = None

try:
    import doctest
    # check if the system version has everything we need
    doctest.DocFileSuite
    doctest.DocTestParser
    doctest.NORMALIZE_WHITESPACE
    doctest.ELLIPSIS
except (ImportError, AttributeError):
    # we need our own version to make it work (Python 2.3?)
    import local_doctest as doctest

try:
    sorted
except NameError:
    def sorted(seq, **kwargs):
        seq = list(seq)
        seq.sort(**kwargs)
        return seq
else:
    locals()['sorted'] = sorted

def _get_caller_relative_path(filename, frame_depth=2):
    module = sys.modules[sys._getframe(frame_depth).f_globals['__name__']]
    return os.path.normpath(os.path.join(
            os.path.dirname(getattr(module, '__file__', '')), filename))

if sys.version_info[0] >= 3:
    # Python 3
    unicode = str
    def _str(s, encoding="UTF-8"):
        return s
    def _bytes(s, encoding="UTF-8"):
        return s.encode(encoding)
    from io import StringIO, BytesIO as _BytesIO
    def BytesIO(*args):
        if args and isinstance(args[0], str):
            args = (args[0].encode("UTF-8"),)
        return _BytesIO(*args)

    doctest_parser = doctest.DocTestParser()
    _fix_unicode = re.compile(r'(\s+)u(["\'])').sub
    _fix_exceptions = re.compile(r'(.*except [^(]*),\s*(.*:)').sub
    def make_doctest(filename):
        filename = _get_caller_relative_path(filename)
        doctests = open(filename).read()
        doctests = _fix_unicode(r'\1\2', doctests)
        doctests = _fix_exceptions(r'\1 as \2', doctests)
        return doctest.DocTestCase(
            doctest_parser.get_doctest(
                doctests, {}, os.path.basename(filename), filename, 0))
else:
    # Python 2
    def _str(s, encoding="UTF-8"):
        return unicode(s, encoding=encoding)
    def _bytes(s, encoding="UTF-8"):
        return s
    from StringIO import StringIO
    BytesIO = StringIO

    doctest_parser = doctest.DocTestParser()
    _fix_traceback = re.compile(r'^(\s*)(?:\w+\.)+(\w*(?:Error|Exception|Invalid):)', re.M).sub
    _fix_exceptions = re.compile(r'(.*except [^(]*)\s+as\s+(.*:)').sub
    _fix_bytes = re.compile(r'(\s+)b(["\'])').sub
    def make_doctest(filename):
        filename = _get_caller_relative_path(filename)
        doctests = open(filename).read()
        doctests = _fix_traceback(r'\1\2', doctests)
        doctests = _fix_exceptions(r'\1, \2', doctests)
        doctests = _fix_bytes(r'\1\2', doctests)
        return doctest.DocTestCase(
            doctest_parser.get_doctest(
                doctests, {}, os.path.basename(filename), filename, 0))

class HelperTestCase(unittest.TestCase):
    def tearDown(self):
        gc.collect()

    def parse(self, text, parser=None):
        f = BytesIO(text)
        return etree.parse(f, parser=parser)
    
    def _rootstring(self, tree):
        return etree.tostring(tree.getroot()).replace(
            _bytes(' '), _bytes('')).replace(_bytes('\n'), _bytes(''))

    # assertFalse doesn't exist in Python 2.3
    try:
        unittest.TestCase.assertFalse
    except AttributeError:
        assertFalse = unittest.TestCase.failIf
        
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

def fileInTestDir(name):
    _testdir = os.path.dirname(__file__)
    return os.path.join(_testdir, name)

def canonicalize(xml):
    f = BytesIO(xml)
    tree = etree.parse(f)
    f = BytesIO()
    tree.write_c14n(f)
    return f.getvalue()

def unentitify(xml):
    for entity_name, value in re.findall("(&#([0-9]+);)", xml):
        xml = xml.replace(entity_name, unichr(int(value)))
    return xml
