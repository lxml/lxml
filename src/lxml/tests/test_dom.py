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

    def test_namespaceURI(self):
        doc = makeDocument('<doc xmlns="http://codespeak.net/ns"><a/><b/><c/></doc>')
        self.assertEquals(
            'http://codespeak.net/ns',
            doc.firstChild.namespaceURI)
        self.assertEquals(
            'http://codespeak.net/ns',
            doc.firstChild.firstChild.namespaceURI)

    def test_nodeList_length(self):
        doc = makeDocument('<doc><a/><b/><c/></doc>')
        self.assertEquals(
            3,
            doc.firstChild.childNodes.length)
        self.assertEquals(
            0,
            doc.firstChild.firstChild.childNodes.length)
        
    def test_isSameNode(self):
        doc = makeDocument('<doc><a/><b/></doc>')
        self.assert_(
            doc.firstChild.firstChild.isSameNode(doc.firstChild.childNodes[0]))
        
    def test_textNodes(self):
        doc = makeDocument('<doc>Foo</doc>')
        self.assertEquals('Foo', doc.firstChild.firstChild.data)

    def test_textNode_length(self):
        doc = makeDocument('<doc>Foo</doc>')
        self.assertEquals(3, doc.firstChild.firstChild.length)
        
    def test_attrnames(self):
        doc = makeDocument('<foo one="One"/>')
        self.assertEquals(
            'one',
            doc.firstChild.attributes.getNamedItemNS(None, 'one').name)
        self.assertEquals(
            'one',
            doc.firstChild.attributes.getNamedItemNS(None, 'one').localName)

    def test_attrnames_ns(self):
        doc = makeDocument(
            '<foo xmlns="http://www.foo.com" xmlns:hoi="http://www.infrae.com" one="One" hoi:two="Two" />')
        attributes = doc.firstChild.attributes
        
        self.assertEquals(
            'one',
            attributes.getNamedItemNS(None, 'one').name)
        self.assertEquals(
            'one',
            attributes.getNamedItemNS(None, 'one').localName)

        self.assertEquals(
            'hoi:two',
            attributes.getNamedItemNS('http://www.infrae.com', 'two').name)
        self.assertEquals(
            'two',
            attributes.getNamedItemNS('http://www.infrae.com', 'two').localName)

    def test_attr_parentNode_ownerElement(self):
        doc = makeDocument(
            '<foo a="A"/>')
        attr = doc.firstChild.attributes.getNamedItemNS(None, 'a')
        self.assertEquals(
            None,
            attr.parentNode)
        self.assertEquals(
            doc.firstChild,
            attr.ownerElement)

    def test_attr_value(self):
        doc = makeDocument(
            '<foo a="A" b="B"/>')
        attributes = doc.firstChild.attributes
        self.assertEquals(
            'A',
            attributes.getNamedItemNS(None, 'a').value)
        self.assertEquals(
            'B',
            attributes.getNamedItemNS(None, 'b').value)

    def test_documentElement(self):
        doc = makeDocument('<foo/>')
        self.assertEquals(
            doc.firstChild,
            doc.documentElement)
        doc = makeDocument('<!-- comment --><foo />')
        self.assertEquals(
            doc.childNodes[1],
            doc.documentElement)
        self.assertEquals(
            'foo',
            doc.documentElement.nodeName)

    def test_comment(self):
        doc = makeDocument('<foo><!-- comment --></foo>')
        self.assertEquals(
            ' comment ',
            doc.documentElement.firstChild.data)

    def test_nodeName_all(self):
        # Attr
        doc = makeDocument('<a href="foo"/>')
        self.assertEquals(
            'href',
            doc.documentElement.attributes.getNamedItemNS(
            None, 'href').nodeName)
        # XXX CDATASection
        doc = makeDocument('<foo><!--foo--></foo>')
        # Comment
        self.assertEquals(
            '#comment',
            doc.documentElement.childNodes[0].nodeName)
        # Document
        doc = makeDocument('<foo/>')
        self.assertEquals(
            '#document',
            doc.nodeName)
        # XXX DocumentFragment
        # XXX DocumentType
        # Element
        doc = makeDocument('<foo/>')
        self.assertEquals(
            'foo',
            doc.documentElement.nodeName)
        doc = makeDocument('<bar:foo xmlns:bar="http://www.bar.com"/>')
        self.assertEquals(
            'bar:foo',
            doc.documentElement.nodeName)
        # XXX Entity
        # XXX EntityReference
        # XXX Notation
        # XXX ProcessingInstruction
        # Text
        doc = makeDocument('<foo>Text</foo>')
        self.assertEquals(
            '#text',
            doc.documentElement.childNodes[0].nodeName)

    def test_nodeValue_all(self):
        # Attr
        doc = makeDocument('<a href="foo"/>')
        self.assertEquals(
            'foo',
            doc.documentElement.attributes.getNamedItemNS(
            None, 'href').nodeValue)
        # XXX CDATASection
        # Comment
        doc = makeDocument('<!--hey--><foo/>')
        self.assertEquals(
            'hey',
            doc.childNodes[0].nodeValue)
        # Document
        doc = makeDocument('<foo/>')
        self.assertEquals(
            None,
            doc.nodeValue)
        # XXX DocumentFragment
        # XXX DocumentType
        # Element
        doc = makeDocument('<foo/>')
        self.assertEquals(
            None,
            doc.documentElement.nodeValue)
        # XXX Entity
        # XXX EntityReference
        # XXX Notation
        # XXX ProcessingInstruction
        # Text
        doc = makeDocument('<foo>Hey</foo>')
        self.assertEquals(
            'Hey',
            doc.documentElement.childNodes[0].nodeValue)

    def test_nodeType_all(self):
        # Attr
        doc = makeDocument('<foo href="bar"/>')
        self.assertEquals(
            doc.ATTRIBUTE_NODE,
            doc.childNodes[0].attributes.getNamedItemNS(None, 'href').nodeType)
        # XXX CDATASection
        # Comment
        doc = makeDocument('<foo><!--hey--></foo>')
        self.assertEquals(
            doc.COMMENT_NODE,
            doc.documentElement.childNodes[0].nodeType)
        # Document
        doc = makeDocument('<foo/>')
        self.assertEquals(
            doc.DOCUMENT_NODE,
            doc.nodeType)
        # XXX DocumentFragment
        # XXX DocumentType
        # Element
        doc = makeDocument('<foo/>')
        self.assertEquals(
            doc.ELEMENT_NODE,
            doc.documentElement.nodeType)        
        # XXX Entity
        # XXX EntityReference
        # XXX Notation
        # XXX ProcessingInstruction
        # Text
        doc = makeDocument('<foo>Text</foo>')
        self.assertEquals(
            doc.TEXT_NODE,
            doc.documentElement.childNodes[0].nodeType)
    
def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(DomTestCase)])
    return suite

if __name__ == '__main__':
    unittest.main()
