import unittest

from lxml.etree import Element, ElementTree
from StringIO import StringIO
import os, shutil, tempfile

class ETreeTestCase(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self._temp_dir)

    def getTestFilePath(self, name):
        return os.path.join(self._temp_dir, name)
    
    def test_element(self):
        for i in range(10000):
            e = Element('foo')

    def test_tree(self):

        element = Element('top')
        tree = ElementTree(element)
        self.buildNodes(element, 10, 4)
        f = open(self.getTestFilePath('testdump.xml'), 'w')
        tree.write(f, 'UTF-8')
        f.close()
        f = open(self.getTestFilePath('testdump.xml'), 'r')
        tree = ElementTree(file=f)
        f.close()
        f = open(self.getTestFilePath('testdump2.xml'), 'w')
        tree.write(f, 'UTF-8')
        f.close()
        f = open(self.getTestFilePath('testdump.xml'), 'r')
        data1 = f.read()
        f.close()
        f = open(self.getTestFilePath('testdump2.xml'), 'r')
        data2 = f.read()
        f.close()
        self.assertEquals(data1, data2)
        
    def buildNodes(self, element, children, depth):
        if depth == 0:
            return
        for i in range(children):
            new_element = Element('element_%s_%s' % (depth, i))
            self.buildNodes(new_element, children, depth - 1)
            element.append(new_element)

    def test_simple(self):
        root = Element('root')
        root.append(Element('one'))
        root.append(Element('two'))
        root.append(Element('three'))
        self.assertEquals(3, len(root))
        self.assertEquals('one', root[0].tag)
        self.assertEquals('two', root[1].tag)
        self.assertEquals('three', root[2].tag)
        self.assertRaises(IndexError, root.__getitem__, 3)
        
    
def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeTestCase)])
    return suite

if __name__ == '__main__':
    unittest.main()
