# -*- coding: UTF-8 -*-

"""
Test cases related to SAX I/O
"""

import unittest, doctest
from StringIO import StringIO

from common_imports import HelperTestCase
from lxml import sax

class ETreeSaxTestCase(HelperTestCase):

    def test_etree_sax_simple(self):
        tree = self.parse('<a>ab<b/>ba</a>')
        xml_out = self._saxify_serialize(tree)
        self.assertEquals('<a>ab<b/>ba</a>',
                          xml_out)

    def test_etree_sax_double(self):
        tree = self.parse('<a>ab<b>bb</b>ba</a>')
        xml_out = self._saxify_serialize(tree)
        self.assertEquals('<a>ab<b>bb</b>ba</a>',
                          xml_out)

    def test_etree_sax_ns1(self):
        tree = self.parse('<a xmlns="bla">ab<b>bb</b>ba</a>')
        new_tree = self._saxify_unsaxify(tree)
        root = new_tree.getroot()
        self.assertEqual(root.tag,
                         '{bla}a')
        self.assertEqual(root[0].tag,
                         '{bla}b')

    def test_etree_sax_ns2(self):
        tree = self.parse('<a xmlns="blaA">ab<b:b xmlns:b="blaB">bb</b:b>ba</a>')
        new_tree = self._saxify_unsaxify(tree)
        root = new_tree.getroot()
        self.assertEqual(root.tag,
                         '{blaA}a')
        self.assertEqual(root[0].tag,
                         '{blaB}b')

    def test_element_sax(self):
        tree = self.parse('<a><b/></a>')
        a = tree.getroot()
        b = a[0]

        xml_out = self._saxify_serialize(a)
        self.assertEquals('<a><b/></a>',
                          xml_out)

        xml_out = self._saxify_serialize(b)
        self.assertEquals('<b/>',
                          xml_out)

    def test_element_sax_ns(self):
        tree = self.parse('<a:a xmlns:a="blaA"><b/></a:a>')
        a = tree.getroot()
        b = a[0]

        new_tree = self._saxify_unsaxify(a)
        root = new_tree.getroot()
        self.assertEqual(root.tag,
                         '{blaA}a')
        self.assertEqual(root[0].tag,
                         'b')

        new_tree = self._saxify_unsaxify(b)
        root = new_tree.getroot()
        self.assertEqual(root.tag,
                         'b')
        self.assertEqual(len(root),
                         0)

    def _saxify_unsaxify(self, saxifiable):
        handler = sax.ElementTreeContentHandler()
        sax.ElementTreeProducer(saxifiable, handler).saxify()
        return handler.etree
        
    def _saxify_serialize(self, tree):
        new_tree = self._saxify_unsaxify(tree)
        f = StringIO()
        new_tree.write(f)
        return f.getvalue()

    
def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeSaxTestCase)])
    suite.addTests(
        [doctest.DocFileSuite('../../../doc/sax.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
