# -*- coding: utf-8 -*-

"""
Tests for different Element class lookup mechanisms.
"""


from __future__ import absolute_import

import unittest, gc

from .common_imports import etree, HelperTestCase, _bytes, BytesIO

xml_str = _bytes('''\
<root xmlns="myNS" xmlns:other="otherNS">
  <c1 a1="A1" a2="A2" other:a3="A3">
    <c2 a1="C2">0</c2>
    <c2>1</c2>
    <other:c2>2</other:c2>
  </c1>
</root>''')


class ProxyTestCase(HelperTestCase):
    """Basic tests for element proxy behaviour.
    """
    etree = etree

    def test_proxy_reuse(self):
        root = etree.XML('<a><b><c/></b></a>')
        b = root.find('b')
        self.assertTrue(b is root[0])

    def test_proxy_reuse_after_gc(self):
        root = etree.XML('<a><b><c/></b></a>')
        b = root.find('b')
        self.assertTrue(self.etree.iselement(b))
        gc.collect()
        self.assertTrue(b is root[0])

    def test_proxy_reuse_after_del_root(self):
        root = etree.XML('<a><b><c/></b></a>')
        b = root.find('b')
        self.assertTrue(self.etree.iselement(b))
        c = b.find('c')
        self.assertTrue(self.etree.iselement(c))
        del root
        gc.collect()
        self.assertTrue(b[0] is c)

    def test_proxy_hashing(self):
        root = etree.XML('<a><b><c/></b></a>')
        old_elements = set(root.iter())
        elements = root.iter()
        del root
        gc.collect()

        missing = len(old_elements)
        self.assertEqual(3, missing)
        for new in elements:
            for old in old_elements:
                if old == new:
                    self.assertTrue(old is new)
                    missing -= 1
                    break
            else:
                self.assertTrue(False, "element '%s' is missing" % new.tag)
        self.assertEqual(0, missing)

    def test_element_base(self):
        el = self.etree.ElementBase()
        self.assertEqual('ElementBase', el.tag)
        root = self.etree.ElementBase()
        root.append(el)
        self.assertEqual('ElementBase', root[0].tag)

    def test_element_base_children(self):
        el = self.etree.ElementBase(etree.ElementBase())
        self.assertEqual('ElementBase', el.tag)
        self.assertEqual(1, len(el))
        self.assertEqual('ElementBase', el[0].tag)

        root = self.etree.ElementBase()
        root.append(el)
        self.assertEqual('ElementBase', root[0].tag)
        self.assertEqual('ElementBase', root[0][0].tag)

    def test_comment_base(self):
        el = self.etree.CommentBase('some text')
        self.assertEqual(self.etree.Comment, el.tag)
        self.assertEqual('some text', el.text)
        root = self.etree.Element('root')
        root.append(el)
        self.assertEqual('some text', root[0].text)

    def test_pi_base(self):
        el = self.etree.PIBase('the target', 'some text')
        self.assertEqual(self.etree.ProcessingInstruction, el.tag)
        self.assertEqual('some text', el.text)
        root = self.etree.Element('root')
        root.append(el)
        self.assertEqual('some text', root[0].text)


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
        self.assertEqual(root.FIND_ME,
                          TestElement.FIND_ME)
        self.assertEqual(root[0].FIND_ME,
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

        self.assertEqual("default element", root.FIND_ME)
        self.assertEqual("default pi", root[0].FIND_ME)
        self.assertEqual("default comment", root[1].FIND_ME)

    def test_default_class_lookup_pull_parser(self):
        class TestElement(etree.ElementBase):
            FIND_ME = "default element"
        class TestComment(etree.CommentBase):
            FIND_ME = "default comment"
        class TestPI(etree.PIBase):
            FIND_ME = "default pi"

        parser = etree.XMLPullParser(events=('start', 'end', 'comment', 'pi'))
        lookup = etree.ElementDefaultClassLookup(
            element=TestElement, comment=TestComment, pi=TestPI)
        parser.set_element_class_lookup(lookup)

        events_seen = []

        def add_events(events):
            for ev, el in events:
                events_seen.append((ev, el.FIND_ME))

        parser.feed("""<?xml version='1.0'?>
        <root>
          <?myPI?>
        """)
        add_events(parser.read_events())

        parser.feed("<!-- hi -->")
        add_events(parser.read_events())

        parser.feed("</root>")
        root = parser.close()
        add_events(parser.read_events())

        self.assertEqual([
            ('start',   "default element"),
            ('pi',      "default pi"),
            ('comment', "default comment"),
            ('end',     "default element"),
        ], events_seen)

        self.assertEqual("default element", root.FIND_ME)
        self.assertEqual("default pi", root[0].FIND_ME)
        self.assertEqual("default comment", root[1].FIND_ME)

    def test_evil_class_lookup(self):
        class MyLookup(etree.CustomElementClassLookup):
            def lookup(self, t, d, ns, name):
                if name == 'none':
                    return None
                elif name == 'obj':
                    return object()
                else:
                    return etree.ElementBase

        parser = etree.XMLParser()
        parser.set_element_class_lookup(MyLookup())

        root = etree.XML(_bytes('<none/>'), parser)
        self.assertEqual('none', root.tag)

        self.assertRaises(
            TypeError,
            etree.XML, _bytes("<obj />"), parser)

        root = etree.XML(_bytes('<root/>'), parser)
        self.assertEqual('root', root.tag)

    def test_class_lookup_type_mismatch(self):
        class MyLookup(etree.CustomElementClassLookup):
            def lookup(self, t, d, ns, name):
                if t == 'element':
                    if name == 'root':
                        return etree.ElementBase
                    return etree.CommentBase
                elif t == 'comment':
                    return etree.PIBase
                elif t == 'PI':
                    return etree.EntityBase
                elif t == 'entity':
                    return etree.ElementBase
                else:
                    raise ValueError('got type %s' % t)

        parser = etree.XMLParser(resolve_entities=False)
        parser.set_element_class_lookup(MyLookup())

        root = etree.XML(_bytes('<root></root>'), parser)
        self.assertEqual('root', root.tag)
        self.assertEqual(etree.ElementBase, type(root))

        root = etree.XML(_bytes("<root><test/></root>"), parser)
        self.assertRaises(TypeError, root.__getitem__, 0)

        root = etree.XML(_bytes("<root><!-- test --></root>"), parser)
        self.assertRaises(TypeError, root.__getitem__, 0)

        root = etree.XML(_bytes("<root><?test?></root>"), parser)
        self.assertRaises(TypeError, root.__getitem__, 0)

        root = etree.XML(
            _bytes('<!DOCTYPE root [<!ENTITY myent "ent">]>'
                   '<root>&myent;</root>'),
            parser)
        self.assertRaises(TypeError, root.__getitem__, 0)

        root = etree.XML(_bytes('<root><root/></root>'), parser)
        self.assertEqual('root', root[0].tag)

    def test_attribute_based_lookup(self):
        class TestElement(etree.ElementBase):
            FIND_ME = "attribute_based"

        class_dict = {"A1" : TestElement}

        lookup = etree.AttributeBasedElementClassLookup(
            "a1", class_dict)
        etree.set_element_class_lookup(lookup)

        root = etree.XML(xml_str)
        self.assertFalse(hasattr(root, 'FIND_ME'))
        self.assertEqual(root[0].FIND_ME,
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
        self.assertEqual(root[0].FIND_ME,
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
        self.assertEqual(root[0].FIND_ME,
                          TestElement1.FIND_ME)
        self.assertFalse(hasattr(root[0][1], 'FIND_ME'))
        self.assertEqual(root[0][-1].FIND_ME,
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
        self.assertEqual(root.FIND_ME,
                          TestElement.FIND_ME)
        self.assertEqual(root[0].FIND_ME,
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
        self.assertEqual(a.tag, "a")
        self.assertEqual(root[0].tag, "a")
        del a
        self.assertEqual(root[0].tag, "a")

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

        self.assertEqual("test", root.custom())


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ProxyTestCase)])
    suite.addTests([unittest.makeSuite(ClassLookupTestCase)])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
