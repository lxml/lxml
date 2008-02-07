import unittest
import os.path
from StringIO import StringIO
import re, gc

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

class HelperTestCase(unittest.TestCase):
    def tearDown(self):
        gc.collect()

    def parse(self, text, parser=None):
        f = StringIO(text)
        return etree.parse(f, parser=parser)
    
    def _rootstring(self, tree):
        return etree.tostring(tree.getroot()).replace(' ', '').replace('\n', '')

    # assertFalse doesn't exist in Python 2.3
    try:
        unittest.TestCase.assertFalse
    except AttributeError:
        assertFalse = unittest.TestCase.failIf
        
class SillyFileLike:
    def __init__(self, xml_data='<foo><bar/></foo>'):
        self.xml_data = xml_data
        
    def read(self, amount=None):
        if self.xml_data:
            if amount:
                data = self.xml_data[:amount]
                self.xml_data = self.xml_data[amount:]
            else:
                data = self.xml_data
                self.xml_data = ''
            return data
        return ''

class LargeFileLike:
    def __init__(self, charlen=100, depth=4, children=5):
        self.data = StringIO()
        self.chars  = 'a' * charlen
        self.children = range(children)
        self.more = self.iterelements(depth)

    def iterelements(self, depth):
        yield '<root>'
        depth -= 1
        if depth > 0:
            for child in self.children:
                for element in self.iterelements(depth):
                    yield element
                yield self.chars
        else:
            yield self.chars
        yield '</root>'

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
            self.data.write(result[amount:])
            result = result[:amount]
        return result

def fileInTestDir(name):
    _testdir = os.path.split(__file__)[0]
    return os.path.join(_testdir, name)

def canonicalize(xml):
    f = StringIO(xml)
    tree = etree.parse(f)
    f = StringIO()
    tree.write_c14n(f)
    return f.getvalue()

def unentitify(xml):
    for entity_name, value in re.findall("(&#([0-9]+);)", xml):
        xml = xml.replace(entity_name, unichr(int(value)))
    return xml
