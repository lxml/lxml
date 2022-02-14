# -*- coding: utf-8 -*-

"""
Tests that ElementMaker works properly.
"""

from __future__ import absolute_import

import unittest

from lxml import etree
from lxml.builder import E, ElementMaker
from lxml.html.builder import E as HE

from .common_imports import HelperTestCase, _bytes


class BuilderTestCase(HelperTestCase):
    etree = etree

    def test_build_from_xpath_result(self):
        class StringSubclass(str): pass
        wrapped = E.b(StringSubclass('Hello'))
        self.assertEqual(_bytes('<b>Hello</b>'), etree.tostring(wrapped))

    def test_unknown_type_raises(self):
        class UnknownType(object):
            pass
        self.assertRaises(TypeError, E.b, UnknownType())

    def test_cdata(self):
        wrapped = E.b(etree.CDATA('Hello'))
        self.assertEqual(_bytes('<b><![CDATA[Hello]]></b>'), etree.tostring(wrapped))

    def test_cdata_solo(self):
        self.assertRaises(ValueError, E.b, 'Hello', etree.CDATA('World'))

    def test_html_builder(self):
        html = HE.html(
            HE.head(HE.title("H-T-M-L!")),
            HE.body(HE.p("TexT"))
        )
        self.assertEqual("TexT", html.findtext(".//p"))

    def test_qname_tag(self):
        p = E(etree.QName("http://lxml.de/nsp", "p"), "xyz")
        self.assertEqual(p.tag, "{http://lxml.de/nsp}p")

    def test_qname_tag_default_namespace(self):
        em = ElementMaker(namespace="http://python.org")

        p = em(etree.QName("http://lxml.de/nsp", "p"), "xyz")
        self.assertEqual(p.tag, "{http://lxml.de/nsp}p")

        p = em("{http://lxml.de/nsp}p", "xyz")
        self.assertEqual(p.tag, "{http://lxml.de/nsp}p")

        # safety check
        p = em("p", "xyz")
        self.assertEqual(p.tag, "{http://python.org}p")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(BuilderTestCase)])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
