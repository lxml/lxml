# -*- coding: utf-8 -*-

"""
IO test cases that apply to both etree and ElementTree
"""

import unittest
import tempfile, gzip, os, os.path, sys, gc, shutil

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

from common_imports import etree, ElementTree, fileInTestDir, _str, _bytes
from common_imports import SillyFileLike, LargeFileLike, HelperTestCase
from common_imports import read_file, write_to_file

class IOTestCaseBase(HelperTestCase):
    """(c)ElementTree compatibility for IO functions/methods
    """
    etree = None
    
    def setUp(self):
        """Setting up a minimal tree
        """
        self.root = self.etree.Element('a')
        self.root_str = self.etree.tostring(self.root)
        self.tree = self.etree.ElementTree(self.root)
        self._temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        gc.collect()
        shutil.rmtree(self._temp_dir)

    def getTestFilePath(self, name):
        return os.path.join(self._temp_dir, name)

    def buildNodes(self, element, children, depth):
        Element = self.etree.Element
        
        if depth == 0:
            return
        for i in range(children):
            new_element = Element('element_%s_%s' % (depth, i))
            self.buildNodes(new_element, children, depth - 1)
            element.append(new_element)

    def test_tree_io(self):
        Element = self.etree.Element
        ElementTree = self.etree.ElementTree
    
        element = Element('top')
        element.text = _str("qwrtioüöä\uAABB")
        tree = ElementTree(element)
        self.buildNodes(element, 10, 3)
        f = open(self.getTestFilePath('testdump.xml'), 'wb')
        tree.write(f, encoding='UTF-8')
        f.close()
        f = open(self.getTestFilePath('testdump.xml'), 'rb')
        tree = ElementTree(file=f)
        f.close()
        f = open(self.getTestFilePath('testdump2.xml'), 'wb')
        tree.write(f, encoding='UTF-8')
        f.close()
        f = open(self.getTestFilePath('testdump.xml'), 'rb')
        data1 = f.read()
        f.close()
        f = open(self.getTestFilePath('testdump2.xml'), 'rb')
        data2 = f.read()
        f.close()
        self.assertEquals(data1, data2)

    def test_tree_io_latin1(self):
        Element = self.etree.Element
        ElementTree = self.etree.ElementTree

        element = Element('top')
        element.text = _str("qwrtioüöäßÃ¡")
        tree = ElementTree(element)
        self.buildNodes(element, 10, 3)
        f = open(self.getTestFilePath('testdump.xml'), 'wb')
        tree.write(f, encoding='iso-8859-1')
        f.close()
        f = open(self.getTestFilePath('testdump.xml'), 'rb')
        tree = ElementTree(file=f)
        f.close()
        f = open(self.getTestFilePath('testdump2.xml'), 'wb')
        tree.write(f, encoding='iso-8859-1')
        f.close()
        f = open(self.getTestFilePath('testdump.xml'), 'rb')
        data1 = f.read()
        f.close()
        f = open(self.getTestFilePath('testdump2.xml'), 'rb')
        data2 = f.read()
        f.close()
        self.assertEquals(data1, data2)
        
    def test_write_filename(self):
        # (c)ElementTree  supports filename strings as write argument
        
        handle, filename = tempfile.mkstemp(suffix=".xml")
        self.tree.write(filename)
        try:
            self.assertEqual(read_file(filename, 'rb').replace(_bytes('\n'), _bytes('')),
                             self.root_str)
        finally:
            os.close(handle)
            os.remove(filename)
        
    def test_write_invalid_filename(self):
        filename = os.path.join(
            os.path.join('hopefullynonexistingpathname'),
            'invalid_file.xml')
        try:
            self.tree.write(filename)
        except IOError:
            pass
        else:
            self.assertTrue(
                False, "writing to an invalid file path should fail")

    def test_module_parse_gzipobject(self):
        # (c)ElementTree supports gzip instance as parse argument
        handle, filename = tempfile.mkstemp(suffix=".xml.gz")
        f = gzip.open(filename, 'wb')
        f.write(self.root_str)
        f.close()
        try:
            f_gz = gzip.open(filename, 'rb')
            tree = self.etree.parse(f_gz)
            f_gz.close()
            self.assertEqual(self.etree.tostring(tree.getroot()), self.root_str)
        finally:
            os.close(handle)
            os.remove(filename)

    def test_class_parse_filename(self):
        # (c)ElementTree class ElementTree has a 'parse' method that returns
        # the root of the tree

        # parse from filename
        
        handle, filename = tempfile.mkstemp(suffix=".xml")
        write_to_file(filename, self.root_str, 'wb')
        try:
            tree = self.etree.ElementTree()
            root = tree.parse(filename)
            self.assertEqual(self.etree.tostring(root), self.root_str)
        finally:
            os.close(handle)
            os.remove(filename)

    def test_class_parse_filename_remove_previous(self):
        handle, filename = tempfile.mkstemp(suffix=".xml")
        write_to_file(filename, self.root_str, 'wb')
        try:
            tree = self.etree.ElementTree()
            root = tree.parse(filename)
            # and now do it again; previous content should still be there
            root2 = tree.parse(filename)
            self.assertEquals('a', root.tag)
            self.assertEquals('a', root2.tag)
            # now remove all references to root2, and parse again
            del root2
            root3 = tree.parse(filename)
            self.assertEquals('a', root.tag)
            self.assertEquals('a', root3.tag)
            # root2's memory should've been freed here
            # XXX how to check?
        finally:
            os.close(handle)
            os.remove(filename)
        
    def test_class_parse_fileobject(self):
        # (c)ElementTree class ElementTree has a 'parse' method that returns
        # the root of the tree

        # parse from file object
        
        handle, filename = tempfile.mkstemp(suffix=".xml")
        try:
            os.write(handle, self.root_str)
            f = open(filename, 'rb')
            tree = self.etree.ElementTree()
            root = tree.parse(f)
            f.close()
            self.assertEqual(self.etree.tostring(root), self.root_str)
        finally:
            os.close(handle)
            os.remove(filename)

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
            try:
                next_char = iter(data).next
            except AttributeError:
                # Python 3
                next_char = iter(data).__next__
            counter = 0
            def read(self, amount=None):
                if amount is None:
                    while True:
                        self.read(1)
                else:
                    try:
                        self.counter += 1
                        return _bytes(self.next_char())
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
    print('to test use test.py %s' % __file__)
