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

    def test_firstChild(self):
        doc = makeDocument('<doc><entry><foo/></entry></doc>')
        self.assertEquals(
            'doc',
            doc.firstChild.nodeName)
        self.assertEquals(
            doc.childNodes[0],
            doc.firstChild)
        self.assertEquals(
            'entry',
            doc.firstChild.firstChild.nodeName)
        self.assertEquals(
            'foo',
            doc.firstChild.firstChild.firstChild.nodeName)
        self.assertEquals(
            doc.childNodes[0],
            doc.firstChild.firstChild.parentNode)
        self.assertEquals(
            doc.childNodes[0].childNodes[0].childNodes[0],
            doc.firstChild.firstChild.firstChild)
        self.assertEquals(
            None,
            doc.firstChild.firstChild.firstChild.firstChild)
        
    def test_lastChild(self):
        doc = makeDocument('<doc><one/><two/><three/></doc>')
        self.assertEquals(
            doc.childNodes[0].childNodes[2],
            doc.childNodes[0].lastChild)
        self.assertEquals(
            doc.childNodes[0],
            doc.lastChild)
        self.assertEquals(
            None,
            doc.childNodes[0].childNodes[0].lastChild)
        
    def test_previousSibling(self):
        doc = makeDocument('<doc><one/><two/><three/></doc>')
        self.assertEquals(
            doc.firstChild.childNodes[0],
            doc.firstChild.childNodes[1].previousSibling)
        self.assertEquals(
            None,
            doc.firstChild.firstChild.previousSibling)
        self.assertEquals(
            doc.firstChild.childNodes[1],
            doc.firstChild.lastChild.previousSibling)
        self.assertEquals(
            None,
            doc.previousSibling)

    def test_nextSibling(self):
        doc = makeDocument('<doc><one/><two/><three/></doc>')
        self.assertEquals(
            doc.firstChild.childNodes[1],
            doc.firstChild.childNodes[0].nextSibling)
        self.assertEquals(
            doc.firstChild.childNodes[2],
            doc.firstChild.childNodes[1].nextSibling)
        self.assertEquals(
            None,
            doc.firstChild.childNodes[2].nextSibling)
        self.assertEquals(
            None,
            doc.nextSibling)

    def test_ownerDocument(self):
        doc = makeDocument('<doc><one/></doc>')
        self.assertEquals(
            doc,
            doc.firstChild.ownerDocument)
        self.assertEquals(
            None,
            doc.ownerDocument)

    def test_nodeType(self):
        doc = makeDocument('<doc/>')
        self.assertEquals(
            doc.firstChild.ELEMENT_NODE,
            doc.firstChild.nodeType)
        self.assertEquals(
            doc.firstChild.DOCUMENT_NODE,
            doc.nodeType)
        
def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(DomTestCase)])
    return suite

if __name__ == '__main__':
    unittest.main()
