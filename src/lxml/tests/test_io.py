# -*- coding: utf-8 -*-

"""
IO test cases that apply to both etree and ElementTree
"""

import unittest
import tempfile, gzip

from common_imports import etree, ElementTree, fileInTestDir
from common_imports import SillyFileLike, LargeFileLike

class IOTestCaseBase(unittest.TestCase):
    """(c)ElementTree compatibility for IO functions/methods
    """
    etree = None
    
    def setUp(self):
        """Setting up a minimal tree
        """
        self.root = self.etree.Element('a')
        self.root_str = self.etree.tostring(self.root)
        self.tree = self.etree.ElementTree(self.root)

    def test_write_filename(self):
        # (c)ElementTree  supports filename strings as write argument
        
        filename = tempfile.mktemp(suffix=".xml")
        self.tree.write(filename)
        self.assertEqual(open(filename).read(), self.root_str)

    def test_module_parse_gzipobject(self):
        # (c)ElementTree supports gzip instance as parse argument
        filename = tempfile.mktemp(suffix=".xml.gz")
        gzip.open(filename, 'wb').write(self.root_str)
        f_gz = gzip.open(filename, 'r')
        tree = self.etree.parse(f_gz)
        self.assertEqual(self.etree.tostring(tree.getroot()), self.root_str)

    def test_class_parse_filename(self):
        # (c)ElementTree class ElementTree has a 'parse' method that returns
        # the root of the tree

        # parse from filename
        
        filename = tempfile.mktemp(suffix=".xml")
        open(filename, 'wb').write(self.root_str)
        tree = self.etree.ElementTree()
        root = tree.parse(filename)
        self.assertEqual(self.etree.tostring(root), self.root_str)

    def test_class_parse_filename_remove_previous(self):
        filename = tempfile.mktemp(suffix=".xml")
        open(filename, "wb").write(self.root_str)
        tree = self.etree.ElementTree()
        root = tree.parse(filename)
        # and now do it again; previous content should still be there
        root2 = tree.parse(filename)
        self.assertEquals('a', root.tag)
        # now remove all references to root2, and parse again
        del root2
        root3 = tree.parse(filename)
        # root2's memory should've been freed here
        # XXX how to check?
        
    def test_class_parse_fileobject(self):
        # (c)ElementTree class ElementTree has a 'parse' method that returns
        # the root of the tree

        # parse from file object
        
        filename = tempfile.mktemp(suffix=".xml")
        open(filename, 'wb').write(self.root_str)
        f = open(filename, 'r')
        tree = self.etree.ElementTree()
        root = tree.parse(f)
        self.assertEqual(self.etree.tostring(root), self.root_str)

    def test_class_parse_unamed_fileobject(self):
        # (c)ElementTree class ElementTree has a 'parse' method that returns
        # the root of the tree

        # parse from unamed file object    
        f = SillyFileLike()
        root = self.etree.ElementTree().parse(f)
        self.assert_(root.tag.endswith('foo'))

    def test_module_parse_large_fileobject(self):
        # parse from unamed file object
        f = LargeFileLike()
        tree = self.etree.parse(f)
        root = tree.getroot()
        self.assert_(root.tag.endswith('root'))

    def test_module_parse_fileobject_error(self):
        class LocalError(Exception):
            pass
        class TestFile:
            def read(*args):
                raise LocalError
        f = TestFile()
        self.assertRaises(LocalError, self.etree.parse, f)

    def test_module_parse_fileobject_late_error(self):
        class LocalError(Exception):
            pass
        class TestFile:
            data = '<root>test</'
            next_char = iter(data).next
            counter = 0
            def read(self, *args):
                try:
                    self.counter += 1
                    return self.next_char()
                except StopIteration:
                    raise LocalError
        f = TestFile()
        self.assertRaises(LocalError, self.etree.parse, f)
        self.assertEquals(f.counter, len(f.data)+1)

    def test_module_parse_fileobject_type_error(self):
        class TestFile:
            def read(*args):
                return 1
        f = TestFile()
        self.assertRaises(TypeError, self.etree.parse, f)

    
class ETreeIOTestCase(IOTestCaseBase):
    etree = etree
    
if ElementTree:
    class ElementTreeIOTestCase(IOTestCaseBase):
        etree = ElementTree

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeIOTestCase)])
    if ElementTree:
        suite.addTests([unittest.makeSuite(ElementTreeIOTestCase)])
    return suite

if __name__ == '__main__':
    unittest.main()
