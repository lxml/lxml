"""
Tests that ElementMaker works properly.
"""


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
        self.assertEqual(b'<b>Hello</b>', etree.tostring(wrapped))

    def test_unknown_type_raises(self):
        class UnknownType:
            pass
        self.assertRaises(TypeError, E.b, UnknownType())

    def test_cdata(self):
        wrapped = E.b(etree.CDATA('Hello'))
        self.assertEqual(b'<b><![CDATA[Hello]]></b>', etree.tostring(wrapped))

    def test_cdata_solo(self):
        self.assertRaises(ValueError, E.b, 'Hello', etree.CDATA('World'))

    def test_many_strings(self):
        p = E.p(*['w%d ' % i for i in range(100)])
        self.assertEqual(''.join('w%d ' % i for i in range(100)), p.text)

    def test_strings_and_other_children(self):
        class StringSubclass(str): pass
        p = E.p('a', 'b', E.i('x'), 'c', StringSubclass('d'), lambda: 'e', 'f',
                E.b(), 'g', 'h')
        self.assertEqual(b'<p>ab<i>x</i>cdef<b/>gh</p>', etree.tostring(p))

    def test_cdata_after_strings(self):
        self.assertRaises(ValueError, E.b, 'Hello', 'World', etree.CDATA('!'))

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
    suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(BuilderTestCase)])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
