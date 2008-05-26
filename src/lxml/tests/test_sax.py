# -*- coding: utf-8 -*-

"""
Test cases related to SAX I/O
"""

import unittest, sys, os.path

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

from common_imports import HelperTestCase, doctest, make_doctest, BytesIO, _bytes
from lxml import sax
from xml.dom import pulldom

class ETreeSaxTestCase(HelperTestCase):

    def test_etree_sax_simple(self):
        tree = self.parse('<a>ab<b/>ba</a>')
        xml_out = self._saxify_serialize(tree)
        self.assertEquals(_bytes('<a>ab<b/>ba</a>'),
                          xml_out)

    def test_etree_sax_double(self):
        tree = self.parse('<a>ab<b>bb</b>ba</a>')
        xml_out = self._saxify_serialize(tree)
        self.assertEquals(_bytes('<a>ab<b>bb</b>ba</a>'),
                          xml_out)

    def test_etree_sax_comment(self):
        tree = self.parse('<a>ab<!-- TEST -->ba</a>')
        xml_out = self._saxify_serialize(tree)
        self.assertEquals(_bytes('<a>abba</a>'),
                          xml_out)

    def test_etree_sax_pi(self):
        tree = self.parse('<a>ab<?this and that?>ba</a>')
        xml_out = self._saxify_serialize(tree)
        self.assertEquals(_bytes('<a>ab<?this and that?>ba</a>'),
                          xml_out)

    def test_etree_sax_comment_root(self):
        tree = self.parse('<!-- TEST --><a>ab</a>')
        xml_out = self._saxify_serialize(tree)
        self.assertEquals(_bytes('<a>ab</a>'),
                          xml_out)

    def test_etree_sax_pi_root(self):
        tree = self.parse('<?this and that?><a>ab</a>')
        xml_out = self._saxify_serialize(tree)
        self.assertEquals(_bytes('<?this and that?><a>ab</a>'),
                          xml_out)

    def test_etree_sax_attributes(self):
        tree = self.parse('<a aa="5">ab<b b="5"/>ba</a>')
        xml_out = self._saxify_serialize(tree)
        self.assertEquals(_bytes('<a aa="5">ab<b b="5"/>ba</a>'),
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

        children = dom.firstChild.childNodes
        self.assertEqual('ab',
                         children[0].nodeValue)
        self.assertEqual('blaB',
                         children[1].namespaceURI)
        self.assertEqual('ba',
                         children[2].nodeValue)

    def test_element_sax(self):
        tree = self.parse('<a><b/></a>')
        a = tree.getroot()
        b = a[0]

        xml_out = self._saxify_serialize(a)
        self.assertEquals(_bytes('<a><b/></a>'),
                          xml_out)

        xml_out = self._saxify_serialize(b)
        self.assertEquals(_bytes('<b/>'),
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

    
def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeSaxTestCase)])
    suite.addTests(
        [make_doctest('../../../doc/sax.txt')])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
