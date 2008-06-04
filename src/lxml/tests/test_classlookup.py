# -*- coding: utf-8 -*-

"""
Tests for different Element class lookup mechanisms.
"""


import unittest, doctest, operator, os.path, sys

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

from common_imports import etree, HelperTestCase, SillyFileLike, fileInTestDir
from common_imports import canonicalize, _bytes, _str, BytesIO, StringIO

xml_str = _bytes('''\
<root xmlns="myNS" xmlns:other="otherNS">
  <c1 a1="A1" a2="A2" other:a3="A3">
    <c2 a1="C2">0</c2>
    <c2>1</c2>
    <other:c2>2</other:c2>
  </c1>
</root>''')

class ClassLookupTestCase(HelperTestCase):
    """Test cases for different Element class lookup mechanisms.
    """
    etree = etree

    def tearDown(self):
        etree.set_element_class_lookup()
        super(ClassLookupTestCase, self).tearDown()

    def test_namespace_lookup(self):
        class TestElement(etree.ElementBase):
            FIND_ME = "namespace class"

        lookup = etree.ElementNamespaceClassLookup()
        etree.set_element_class_lookup(lookup)

        ns = lookup.get_namespace("myNS")
        ns[None] = TestElement

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
        parser.set_element_class_lookup(lookup)

        root = etree.XML(_bytes("""<?xml version='1.0'?>
        <root>
          <?myPI?>
          <!-- hi -->
        </root>
        """), parser)

        self.assertEquals("default element", root.FIND_ME)
        self.assertEquals("default pi", root[0].FIND_ME)
        self.assertEquals("default comment", root[1].FIND_ME)

    def test_attribute_based_lookup(self):
        class TestElement(etree.ElementBase):
            FIND_ME = "attribute_based"

        class_dict = {"A1" : TestElement}

        lookup = etree.AttributeBasedElementClassLookup(
            "a1", class_dict)
        etree.set_element_class_lookup(lookup)

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

        etree.set_element_class_lookup( MyLookup() )

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

        lookup = etree.ElementNamespaceClassLookup( MyLookup() )
        etree.set_element_class_lookup(lookup)

        ns = lookup.get_namespace("otherNS")
        ns[None] = TestElement2

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
        etree.set_element_class_lookup(lookup)

        class MyLookup(etree.CustomElementClassLookup):
            def lookup(self, t, d, ns, name):
                return TestElement

        parser = etree.XMLParser()
        parser.set_element_class_lookup( MyLookup() )

        root = etree.parse(BytesIO(xml_str), parser).getroot()
        self.assertEquals(root.FIND_ME,
                          TestElement.FIND_ME)
        self.assertEquals(root[0].FIND_ME,
                          TestElement.FIND_ME)

        root = etree.parse(BytesIO(xml_str)).getroot()
        self.assertFalse(hasattr(root, 'FIND_ME'))
        self.assertFalse(hasattr(root[0], 'FIND_ME'))

    def test_class_lookup_reentry(self):
        XML = self.etree.XML

        class TestElement(etree.ElementBase):
            FIND_ME = "here"

        root = None
        class MyLookup(etree.CustomElementClassLookup):
            el = None
            def lookup(self, t, d, ns, name):
                if root is not None: # not in the parser
                    if self.el is None and name == "a":
                        self.el = []
                        self.el.append(root.find(name))
                return TestElement

        parser = self.etree.XMLParser()
        parser.set_element_class_lookup(MyLookup())

        root = XML(_bytes('<root><a>A</a><b xmlns="test">B</b></root>'),
                   parser)

        a = root[0]
        self.assertEquals(a.tag, "a")
        self.assertEquals(root[0].tag, "a")
        del a
        self.assertEquals(root[0].tag, "a")

    def test_lookup_without_fallback(self):
        class Lookup(etree.CustomElementClassLookup):
             def __init__(self):
                 # no super call here, so no fallback is set
                 pass

             def lookup(self, node_type, document, namespace, name):
                 return Foo

        class Foo(etree.ElementBase):
             def custom(self):
                 return "test"

        parser = self.etree.XMLParser()
        parser.set_element_class_lookup( Lookup() )

        root = etree.XML('<foo/>', parser)

        self.assertEquals("test", root.custom())


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ClassLookupTestCase)])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
