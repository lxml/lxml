import unittest
import os.path
from lxml import demo

def getPath():
    return os.path.split(__file__)[0]

def getTestFile(name):
    return os.path.join(getPath(), name)

class TestCase(unittest.TestCase):
    def test_navigation(self):
        doc = demo.parseFile(getTestFile('test1.xml'))
        node = doc.firstChild()
        self.assertEquals('doc', node.name())
        node = node.firstChild()
        self.assertEquals('p1', node.name())
        self.assert_(isinstance(node.name(), unicode))
        node = node.nextSibling()
        self.assertEquals('p2', node.name())
        self.assertEquals(None, node.nextSibling())
        node = node.previousSibling()
        self.assertEquals('p1', node.name())
        self.assertEquals(None, node.previousSibling())
        node = node.parent()
        self.assertEquals('doc', node.name())

    def test_docnode_navigation(self):
        doc = demo.parseFile(getTestFile('test1.xml'))
        self.assertEquals(None, doc.nextSibling())
        self.assertEquals(None, doc.previousSibling())
        self.assertEquals(None, doc.parent())

    def test_content_navigation(self):
        doc = demo.parseFile(getTestFile('test1.xml'))
        node = doc.firstChild()
        node = node.firstChild()
        node = node.firstChild()
        self.assertEquals('One', node.content())
        self.assert_(isinstance(node.content(), unicode))
        
def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(TestCase)])
    return suite

if __name__ == '__main__':
    unittest.main()
    
