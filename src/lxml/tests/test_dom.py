import unittest

from lxml.dom import makeDocument

class DomTestCase(unittest.TestCase):
    def test_nodeName(self):
        doc = makeDocument('<doc><el1/><el2/></doc>')
        self.assertEquals(
            'el1',
            doc.childNodes[0].childNodes[0].nodeName)

    def test_namespace(self):
        doc = makeDocument('<doc xmlns:foo="http://www.infrae.com"><foo:el/></doc>')
        node = doc.childNodes[0].childNodes[0]
        self.assertEquals(
            'foo:el',
            node.nodeName)
        self.assertEquals(
            'foo:el',
            node.tagName)
        self.assertEquals(
            'el',
            node.localName)
        self.assertEquals(
            'foo',
            node.prefix)

    def test_parentNode(self):
        doc = makeDocument('<doc><entry/></doc>')
        node = doc.childNodes[0]
        node2 = node.childNodes[0]
        self.assertEquals(
            node,
            node2.parentNode)
        self.assert_(node2.parentNode != node2)
            
                              
def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(DomTestCase)])
    return suite

if __name__ == '__main__':
    unittest.main()
