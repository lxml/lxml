# -*- coding: utf-8 -*-

"""
Test cases related to SAX I/O
"""

from __future__ import absolute_import

import unittest
from xml.dom import pulldom
from xml.sax.handler import ContentHandler

from .common_imports import HelperTestCase, make_doctest, BytesIO, _bytes
from lxml import sax


class ETreeSaxTestCase(HelperTestCase):

    def test_etree_sax_simple(self):
        tree = self.parse('<a>ab<b/>ba</a>')
        xml_out = self._saxify_serialize(tree)
        self.assertEqual(_bytes('<a>ab<b/>ba</a>'),
                          xml_out)

    def test_etree_sax_double(self):
        tree = self.parse('<a>ab<b>bb</b>ba</a>')
        xml_out = self._saxify_serialize(tree)
        self.assertEqual(_bytes('<a>ab<b>bb</b>ba</a>'),
                          xml_out)

    def test_etree_sax_comment(self):
        tree = self.parse('<a>ab<!-- TEST -->ba</a>')
        xml_out = self._saxify_serialize(tree)
        self.assertEqual(_bytes('<a>abba</a>'),
                          xml_out)

    def test_etree_sax_pi(self):
        tree = self.parse('<a>ab<?this and that?>ba</a>')
        xml_out = self._saxify_serialize(tree)
        self.assertEqual(_bytes('<a>ab<?this and that?>ba</a>'),
                          xml_out)

    def test_etree_sax_comment_root(self):
        tree = self.parse('<!-- TEST --><a>ab</a>')
        xml_out = self._saxify_serialize(tree)
        self.assertEqual(_bytes('<a>ab</a>'),
                          xml_out)

    def test_etree_sax_pi_root(self):
        tree = self.parse('<?this and that?><a>ab</a>')
        xml_out = self._saxify_serialize(tree)
        self.assertEqual(_bytes('<?this and that?><a>ab</a>'),
                          xml_out)

    def test_etree_sax_attributes(self):
        tree = self.parse('<a aa="5">ab<b b="5"/>ba</a>')
        xml_out = self._saxify_serialize(tree)
        self.assertEqual(_bytes('<a aa="5">ab<b b="5"/>ba</a>'),
                          xml_out)

    def test_etree_sax_ns1(self):
        tree = self.parse('<a xmlns="bla">ab<b>bb</b>ba</a>')
        new_tree = self._saxify_unsaxify(tree)
        root = new_tree.getroot()
        self.assertEqual('{bla}a',
                         root.tag)
        self.assertEqual('{bla}b',
                         root[0].tag)

    def test_etree_sax_ns2(self):
        tree = self.parse('<a xmlns="blaA">ab<b:b xmlns:b="blaB">bb</b:b>ba</a>')
        new_tree = self._saxify_unsaxify(tree)
        root = new_tree.getroot()
        self.assertEqual('{blaA}a',
                         root.tag)
        self.assertEqual('{blaB}b',
                         root[0].tag)

    def test_sax_to_pulldom(self):
        tree = self.parse('<a xmlns="blaA">ab<b:b xmlns:b="blaB">bb</b:b>ba</a>')
        handler = pulldom.SAX2DOM()
        sax.saxify(tree, handler)
        dom = handler.document

        self.assertEqual('a',
                         dom.firstChild.localName)
        self.assertEqual('blaA',
                         dom.firstChild.namespaceURI)
        self.assertEqual(None,
                         dom.firstChild.prefix)

        children = dom.firstChild.childNodes
        self.assertEqual('ab',
                         children[0].nodeValue)
        self.assertEqual('blaB',
                         children[1].namespaceURI)
        self.assertEqual('ba',
                         children[2].nodeValue)

    def test_sax_to_pulldom_multiple_namespaces(self):
        tree = self.parse('<a xmlns="blaA" xmlns:a="blaA"></a>')
        handler = pulldom.SAX2DOM()
        sax.saxify(tree, handler)
        dom = handler.document

        # With multiple prefix definitions, the node should keep the one
        # that was actually used, even if the others also are valid.
        self.assertEqual('a',
                         dom.firstChild.localName)
        self.assertEqual('blaA',
                         dom.firstChild.namespaceURI)
        self.assertEqual(None,
                         dom.firstChild.prefix)

        tree = self.parse('<a:a xmlns="blaA" xmlns:a="blaA"></a:a>')
        handler = pulldom.SAX2DOM()
        sax.saxify(tree, handler)
        dom = handler.document

        self.assertEqual('a',
                         dom.firstChild.localName)
        self.assertEqual('blaA',
                         dom.firstChild.namespaceURI)
        self.assertEqual('a',
                         dom.firstChild.prefix)

    def test_element_sax(self):
        tree = self.parse('<a><b/></a>')
        a = tree.getroot()
        b = a[0]

        xml_out = self._saxify_serialize(a)
        self.assertEqual(_bytes('<a><b/></a>'),
                          xml_out)

        xml_out = self._saxify_serialize(b)
        self.assertEqual(_bytes('<b/>'),
                          xml_out)

    def test_element_sax_ns(self):
        tree = self.parse('<a:a xmlns:a="blaA"><b/></a:a>')
        a = tree.getroot()
        b = a[0]

        new_tree = self._saxify_unsaxify(a)
        root = new_tree.getroot()
        self.assertEqual('{blaA}a',
                         root.tag)
        self.assertEqual('b',
                         root[0].tag)

        new_tree = self._saxify_unsaxify(b)
        root = new_tree.getroot()
        self.assertEqual('b',
                         root.tag)
        self.assertEqual(0,
                         len(root))

    def test_etree_sax_handler_default_ns(self):
        handler = sax.ElementTreeContentHandler()
        handler.startDocument()
        handler.startPrefixMapping(None, 'blaA')
        handler.startElementNS(('blaA', 'a'), 'a', {})
        handler.startPrefixMapping(None, 'blaB')
        handler.startElementNS(('blaB', 'b'), 'b', {})
        handler.endElementNS(  ('blaB', 'b'), 'b')
        handler.endPrefixMapping(None)
        handler.startElementNS(('blaA', 'c'), 'c', {})
        handler.endElementNS(  ('blaA', 'c'), 'c')
        handler.endElementNS(  ('blaA', 'a'), 'a')
        handler.endPrefixMapping(None)
        handler.endDocument()

        new_tree = handler.etree
        root = new_tree.getroot()
        self.assertEqual('{blaA}a',
                         root.tag)
        self.assertEqual('{blaB}b',
                         root[0].tag)
        self.assertEqual('{blaA}c',
                         root[1].tag)

    def test_etree_sax_handler_default_ns_None(self):
        handler = sax.ElementTreeContentHandler()
        handler.startDocument()
        handler.startPrefixMapping(None, 'blaA')
        handler.startElementNS((None, 'a'), 'a', {})
        handler.startPrefixMapping(None, 'blaB')
        handler.startElementNS((None, 'b'), 'b', {})
        handler.endElementNS(  (None, 'b'), 'b')
        handler.endPrefixMapping(None)
        handler.startElementNS((None, 'c'), 'c', {})
        handler.endElementNS(  (None, 'c'), 'c')
        handler.endElementNS(  (None, 'a'), 'a')
        handler.endPrefixMapping(None)
        handler.endDocument()

        new_tree = handler.etree
        root = new_tree.getroot()
        self.assertEqual('{blaA}a',
                         root.tag)
        self.assertEqual('{blaB}b',
                         root[0].tag)
        self.assertEqual('{blaA}c',
                         root[1].tag)

    def test_etree_sax_redefine_ns(self):
        handler = sax.ElementTreeContentHandler()
        handler.startDocument()
        handler.startPrefixMapping('ns', 'blaA')
        handler.startElementNS(('blaA', 'a'), 'ns:a', {})
        handler.startPrefixMapping('ns', 'blaB')
        handler.startElementNS(('blaB', 'b'), 'ns:b', {})
        handler.endElementNS(  ('blaB', 'b'), 'ns:b')
        handler.endPrefixMapping('ns')
        handler.startElementNS(('blaA', 'c'), 'ns:c', {})
        handler.endElementNS(  ('blaA', 'c'), 'ns:c')
        handler.endElementNS(  ('blaA', 'a'), 'ns:a')
        handler.endPrefixMapping('ns')
        handler.endDocument()

        new_tree = handler.etree
        root = new_tree.getroot()
        self.assertEqual('{blaA}a',
                         root.tag)
        self.assertEqual('{blaB}b',
                         root[0].tag)
        self.assertEqual('{blaA}c',
                         root[1].tag)

    def test_etree_sax_no_ns(self):
        handler = sax.ElementTreeContentHandler()
        handler.startDocument()
        handler.startElement('a', {})
        handler.startElement('b', {})
        handler.endElement('b')
        handler.startElement('c') # with empty attributes
        handler.endElement('c')
        handler.endElement('a')
        handler.endDocument()

        new_tree = handler.etree
        root = new_tree.getroot()
        self.assertEqual('a', root.tag)
        self.assertEqual('b', root[0].tag)
        self.assertEqual('c', root[1].tag)

    def test_etree_sax_no_ns_attributes(self):
        handler = sax.ElementTreeContentHandler()
        handler.startDocument()
        handler.startElement('a', {"attr_a1": "a1"})
        handler.startElement('b', {"attr_b1": "b1"})
        handler.endElement('b')
        handler.endElement('a')
        handler.endDocument()

        new_tree = handler.etree
        root = new_tree.getroot()
        self.assertEqual('a', root.tag)
        self.assertEqual('b', root[0].tag)
        self.assertEqual('a1', root.attrib["attr_a1"])
        self.assertEqual('b1', root[0].attrib["attr_b1"])

    def test_etree_sax_ns_attributes(self):
        handler = sax.ElementTreeContentHandler()
        handler.startDocument()

        self.assertRaises(ValueError,
            handler.startElement,
            'a', {"blaA:attr_a1": "a1"}
        )

    def test_etree_sax_error(self):
        handler = sax.ElementTreeContentHandler()
        handler.startDocument()
        handler.startElement('a')
        self.assertRaises(sax.SaxError, handler.endElement, 'b')

    def test_etree_sax_error2(self):
        handler = sax.ElementTreeContentHandler()
        handler.startDocument()
        handler.startElement('a')
        handler.startElement('b')
        self.assertRaises(sax.SaxError, handler.endElement, 'a')

    def _saxify_unsaxify(self, saxifiable):
        handler = sax.ElementTreeContentHandler()
        sax.ElementTreeProducer(saxifiable, handler).saxify()
        return handler.etree

    def _saxify_serialize(self, tree):
        new_tree = self._saxify_unsaxify(tree)
        f = BytesIO()
        new_tree.write(f)
        return f.getvalue().replace(_bytes('\n'), _bytes(''))


class SimpleContentHandler(ContentHandler, object):
    """A SAX content handler that just stores the events"""

    def __init__(self):
        self.sax_events = []
        super(SimpleContentHandler, self).__init__()

    def startDocument(self):
        self.sax_events.append(('startDocument',))

    def endDocument(self):
        self.sax_events.append(('endDocument',))

    def startPrefixMapping(self, prefix, uri):
        self.sax_events.append(('startPrefixMapping', prefix, uri))

    def endPrefixMapping(self, prefix):
        self.sax_events.append(('endPrefixMapping', prefix))

    def startElement(self, name, attrs):
        self.sax_events.append(('startElement', name, dict(attrs)))

    def endElement(self, name):
        self.sax_events.append(('endElement', name))

    def startElementNS(self, name, qname, attrs):
        self.sax_events.append(('startElementNS', name, qname, attrs._qnames))

    def endElementNS(self, name, qname):
        self.sax_events.append(('endElementNS', name, qname))

    def characters(self, content):
        self.sax_events.append(('characters', content))

    def ignorableWhitespace(self, whitespace):
        self.sax_events.append(('ignorableWhitespace', whitespace))

    def processingInstruction(self, target, data):
        self.sax_events.append(('processingInstruction', target, data))

    def skippedEntity(self, name):
        self.sax_events.append(('skippedEntity', name))


class NSPrefixSaxTestCase(HelperTestCase):
    """Testing that namespaces generate the right SAX events"""

    def _saxify(self, tree):
        handler = SimpleContentHandler()
        sax.ElementTreeProducer(tree, handler).saxify()
        return handler.sax_events

    def test_element_sax_ns_prefix(self):
        # The name of the prefix should be preserved, if the uri is unique
        tree = self.parse('<a:a xmlns:a="blaA" xmlns:c="blaC">'
                          '<d a:attr="value" c:attr="value" /></a:a>')
        a = tree.getroot()

        self.assertEqual(
            [('startElementNS', ('blaA', 'a'), 'a:a', {}),
             ('startElementNS', (None, 'd'), 'd',
              {('blaA', 'attr'): 'a:attr', ('blaC', 'attr'): 'c:attr'}),
             ('endElementNS', (None, 'd'), 'd'),
             ('endElementNS', ('blaA', 'a'), 'a:a'),
            ],
            self._saxify(a)[3:7])

    def test_element_sax_default_ns_prefix(self):
        # Default prefixes should also not get a generated prefix
        tree = self.parse('<a xmlns="blaA"><b attr="value" /></a>')
        a = tree.getroot()

        self.assertEqual(
            [('startDocument',),
             # NS prefix should be None:
             ('startPrefixMapping', None, 'blaA'),
             ('startElementNS', ('blaA', 'a'), 'a', {}),
             # Attribute prefix should be None:
             ('startElementNS', ('blaA', 'b'), 'b', {(None, 'attr'): 'attr'}),
             ('endElementNS', ('blaA', 'b'), 'b'),
             ('endElementNS', ('blaA', 'a'), 'a'),
             # Prefix should be None again:
             ('endPrefixMapping', None),
             ('endDocument',)],
            self._saxify(a))

        # Except for attributes, if there is both a default namespace
        # and a named namespace with the same uri
        tree = self.parse('<a xmlns="bla" xmlns:a="bla">'
                          '<b a:attr="value" /></a>')
        a = tree.getroot()

        self.assertEqual(
            ('startElementNS', ('bla', 'b'), 'b', {('bla', 'attr'): 'a:attr'}),
            self._saxify(a)[4])

    def test_element_sax_twin_ns_prefix(self):
        # Make an element with an doubly registered uri
        tree = self.parse('<a xmlns:b="bla" xmlns:c="bla">'
                          '<d c:attr="attr" /></a>')
        a = tree.getroot()

        self.assertEqual(
            # It should get the b prefix in this case
            ('startElementNS', (None, 'd'), 'd', {('bla', 'attr'): 'b:attr'}),
            self._saxify(a)[4])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeSaxTestCase)])
    suite.addTests([unittest.makeSuite(NSPrefixSaxTestCase)])
    suite.addTests(
        [make_doctest('../../../doc/sax.txt')])
    return suite


if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
