import unittest

from lxml.etree import Element, ElementTree
from StringIO import StringIO
import os

def getTestDir():
    return os.path.dirname(__file__)

class ETreeTestCase(unittest.TestCase):
    def test_element(self):
        for i in range(10000):
            e = Element('foo')

    def test_tree(self):
        element = Element('top')
        tree = ElementTree(element)
        self.buildNodes(element, 10, 5)
        f = open(os.path.join(getTestDir(), 'testdump.xml'), 'w')
        tree.write(f, 'UTF-8')
        f.close()
        f = open(os.path.join(getTestDir(), 'testdump.xml'), 'r')
        tree = ElementTree(file=f)
        f.close()
        f = open(os.path.join(getTestDir(), 'testdump2.xml'), 'w')
        tree.write(f, 'UTF-8')
        f.close()
        
    def buildNodes(self, element, children, depth):
        if depth == 0:
            return
        for i in range(children):
            new_element = Element('element_%s_%s' % (depth, i))
            self.buildNodes(new_element, children, depth - 1)
            element.append(new_element)

    
def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeTestCase)])
    return suite

if __name__ == '__main__':
    unittest.main()
