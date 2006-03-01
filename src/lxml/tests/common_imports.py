import unittest
import os.path
from StringIO import StringIO

from lxml import etree

try:
    from elementtree import ElementTree
except ImportError:
    ElementTree = None

class HelperTestCase(unittest.TestCase):
    def parse(self, text):
        f = StringIO(text)
        return etree.parse(f)
    
    def _rootstring(self, tree):
        return etree.tostring(tree.getroot()).replace(' ', '').replace('\n', '')

class SillyFileLike:
    def __init__(self, xml_data='<foo><bar/></foo>'):
        self.xml_data = xml_data
        self.done = False
        
    def read(self, amount=None):
        if not self.done:
            self.done = True
            return self.xml_data
        return ''

def fileInTestDir(name):
    _testdir = os.path.split(__file__)[0]
    return os.path.join(_testdir, name)

def canonicalize(xml):
    f = StringIO(xml)
    tree = etree.parse(f)
    f = StringIO()
    tree.write_c14n(f)
    return f.getvalue()
