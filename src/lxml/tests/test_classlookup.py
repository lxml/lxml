# -*- coding: utf-8 -*-

"""
Tests specific to the extended etree API

Tests that apply to the general ElementTree API should go into
test_elementtree
"""


import unittest, doctest, operator

from common_imports import etree, StringIO, HelperTestCase, fileInTestDir
from common_imports import SillyFileLike, canonicalize

xml_str = '''\
<root xmlns="myNS" xmlns:other="otherNS">
  <c1 a1="A1" a2="A2" other:a3="A3">
    <c2 a1="C2">0</c2>
    <c2>1</c2>
    <other:c2>2</other:c2>
  </c1>
</root>'''

class ClassLookupTestCase(HelperTestCase):
    """Test cases for lxml.elementlib.classlookup
    """
    etree = etree

    def tearDown(self):
        etree.setElementClassLookup()
        etree.Namespace("myNS").clear()
        etree.Namespace("otherNS").clear()

    def test_namespace_lookup(self):
        class TestElement(etree.ElementBase):
            FIND_ME = "namespace class"

        ns = etree.Namespace("myNS")
        ns[None] = TestElement

        lookup = etree.ElementNamespaceClassLookup()
        etree.setElementClassLookup(lookup)

        root = etree.XML(xml_str)
        self.assertEquals(root.FIND_ME,
                          TestElement.FIND_ME)
        self.assertEquals(root[0].FIND_ME,
                          TestElement.FIND_ME)
        self.assertFalse(hasattr(root[0][-1], 'FIND_ME'))

    def test_default_class_lookup(self):
        class TestElement(etree.ElementBase):
            FIND_ME = "default element"
        class TestComment(etree.CommentBase):
            FIND_ME = "default comment"
        class TestPI(etree.PIBase):
            FIND_ME = "default pi"

        parser = etree.XMLParser()

        lookup = etree.ElementDefaultClassLookup(
            element=TestElement, comment=TestComment, pi=TestPI)
        parser.setElementClassLookup(lookup)

        root = etree.XML("""<?xml version='1.0'?>
        <root>
          <?myPI?>
          <!-- hi -->
        </root>
        """, parser)

        self.assertEquals("default element", root.FIND_ME)
        self.assertEquals("default pi", root[0].FIND_ME)
        self.assertEquals("default comment", root[1].FIND_ME)

    def test_default_class_lookup_is_not_nslookup(self):
        class TestElement(etree.ElementBase):
            FIND_ME = "namespace class"

        ns = etree.Namespace("myNS")
        ns[None] = TestElement

        lookup = etree.ElementDefaultClassLookup()
        etree.setElementClassLookup(lookup)

        root = etree.XML(xml_str)
        self.assertFalse(hasattr(root, 'FIND_ME'))
        self.assertFalse(hasattr(root[0][-1], 'FIND_ME'))

    def test_attribute_based_lookup(self):
        class TestElement(etree.ElementBase):
            FIND_ME = "attribute_based"

        class_dict = {"A1" : TestElement}

        lookup = etree.AttributeBasedElementClassLookup(
            "a1", class_dict)
        etree.setElementClassLookup(lookup)

        root = etree.XML(xml_str)
        self.assertFalse(hasattr(root, 'FIND_ME'))
        self.assertEquals(root[0].FIND_ME,
                          TestElement.FIND_ME)
        self.assertFalse(hasattr(root[0][0], 'FIND_ME'))

    def test_custom_lookup(self):
        class TestElement(etree.ElementBase):
            FIND_ME = "custom"

        class MyLookup(etree.CustomElementClassLookup):
            def lookup(self, t, d, ns, name):
                if name == 'c1':
                    return TestElement

        etree.setElementClassLookup( MyLookup() )

        root = etree.XML(xml_str)
        self.assertFalse(hasattr(root, 'FIND_ME'))
        self.assertEquals(root[0].FIND_ME,
                          TestElement.FIND_ME)
        self.assertFalse(hasattr(root[0][1], 'FIND_ME'))

    def test_custom_lookup_ns_fallback(self):
        class TestElement1(etree.ElementBase):
            FIND_ME = "custom"

        class TestElement2(etree.ElementBase):
            FIND_ME = "nsclasses"

        class MyLookup(etree.CustomElementClassLookup):
            def lookup(self, t, d, ns, name):
                if name == 'c1':
                    return TestElement1

        ns = etree.Namespace("otherNS")
        ns[None] = TestElement2

        lookup = etree.ElementNamespaceClassLookup( MyLookup() )
        etree.setElementClassLookup(lookup)

        root = etree.XML(xml_str)
        self.assertFalse(hasattr(root, 'FIND_ME'))
        self.assertEquals(root[0].FIND_ME,
                          TestElement1.FIND_ME)
        self.assertFalse(hasattr(root[0][1], 'FIND_ME'))
        self.assertEquals(root[0][-1].FIND_ME,
                          TestElement2.FIND_ME)

    def test_parser_based_lookup(self):
        class TestElement(etree.ElementBase):
            FIND_ME = "parser_based"

        lookup = etree.ParserBasedElementClassLookup()
        etree.setElementClassLookup(lookup)

        class MyLookup(etree.CustomElementClassLookup):
            def lookup(self, t, d, ns, name):
                return TestElement

        parser = etree.XMLParser()
        parser.setElementClassLookup( MyLookup() )

        root = etree.parse(StringIO(xml_str), parser).getroot()
        self.assertEquals(root.FIND_ME,
                          TestElement.FIND_ME)
        self.assertEquals(root[0].FIND_ME,
                          TestElement.FIND_ME)

        root = etree.parse(StringIO(xml_str)).getroot()
        self.assertFalse(hasattr(root, 'FIND_ME'))
        self.assertFalse(hasattr(root[0], 'FIND_ME'))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ClassLookupTestCase)])
    return suite

if __name__ == '__main__':
    unittest.main()
