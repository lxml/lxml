# -*- coding: utf-8 -*-

"""
Tests for the ElementTree API

Only test cases that apply equally well to etree and ElementTree
belong here. Note that there is a second test module called test_io.py
for IO related test cases.
"""

import unittest
import os, re, tempfile, copy, operator, sys

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

from common_imports import BytesIO, etree
from common_imports import ElementTree, cElementTree, ET_VERSION, CET_VERSION
from common_imports import filter_by_version, fileInTestDir, canonicalize, HelperTestCase
from common_imports import _str, _bytes, unicode, next

if cElementTree is not None and (CET_VERSION <= (1,0,7) or sys.version_info >= (3,3)):
    cElementTree = None

if ElementTree is not None:
    print("Comparing with ElementTree %s" % getattr(ElementTree, "VERSION", "?"))

if cElementTree is not None:
    print("Comparing with cElementTree %s" % getattr(cElementTree, "VERSION", "?"))

class _ETreeTestCaseBase(HelperTestCase):
    etree = None
    required_versions_ET = {}
    required_versions_cET = {}

    def XMLParser(self, **kwargs):
        try:
            XMLParser = self.etree.XMLParser
        except AttributeError:
            assert 'ElementTree' in self.etree.__name__
            XMLParser = self.etree.TreeBuilder
        return XMLParser(**kwargs)

    def test_element(self):
        for i in range(10):
            e = self.etree.Element('foo')
            self.assertEqual(e.tag, 'foo')
            self.assertEqual(e.text, None)
            self.assertEqual(e.tail, None)

    def test_simple(self):
        Element = self.etree.Element
        
        root = Element('root')
        root.append(Element('one'))
        root.append(Element('two'))
        root.append(Element('three'))
        self.assertEqual(3, len(root))
        self.assertEqual('one', root[0].tag)
        self.assertEqual('two', root[1].tag)
        self.assertEqual('three', root[2].tag)
        self.assertRaises(IndexError, operator.getitem, root, 3)

    # test weird dictionary interaction leading to segfault previously
    def test_weird_dict_interaction(self):
        root = self.etree.Element('root')
        self.assertEqual(root.tag, "root")
        add = self.etree.ElementTree(file=BytesIO('<foo>Foo</foo>'))
        self.assertEqual(add.getroot().tag, "foo")
        self.assertEqual(add.getroot().text, "Foo")
        root.append(self.etree.Element('baz'))
        self.assertEqual(root.tag, "root")
        self.assertEqual(root[0].tag, "baz")

    def test_subelement(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        root = Element('root')
        SubElement(root, 'one')
        SubElement(root, 'two')
        SubElement(root, 'three')
        self.assertEqual(3, len(root))
        self.assertEqual('one', root[0].tag)
        self.assertEqual('two', root[1].tag)
        self.assertEqual('three', root[2].tag)
        
    def test_element_contains(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        root1 = Element('root')
        SubElement(root1, 'one')
        self.assertTrue(root1[0] in root1)

        root2 = Element('root')
        SubElement(root2, 'two')
        SubElement(root2, 'three')
        self.assertTrue(root2[0] in root2)
        self.assertTrue(root2[1] in root2)

        self.assertFalse(root1[0] in root2)
        self.assertFalse(root2[0] in root1)
        self.assertFalse(None in root2)

    def test_element_indexing_with_text(self):
        ElementTree = self.etree.ElementTree
        
        f = BytesIO('<doc>Test<one>One</one></doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEqual(1, len(root))
        self.assertEqual('one', root[0].tag)
        self.assertRaises(IndexError, operator.getitem, root, 1)
        
    def test_element_indexing_with_text2(self):
        ElementTree = self.etree.ElementTree
        
        f = BytesIO('<doc><one>One</one><two>Two</two>hm<three>Three</three></doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEqual(3, len(root))
        self.assertEqual('one', root[0].tag)
        self.assertEqual('two', root[1].tag)
        self.assertEqual('three', root[2].tag)

    def test_element_indexing_only_text(self):
        ElementTree = self.etree.ElementTree
        
        f = BytesIO('<doc>Test</doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEqual(0, len(root))

    def test_element_indexing_negative(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')
        self.assertEqual(d, a[-1])
        self.assertEqual(c, a[-2])
        self.assertEqual(b, a[-3])
        self.assertRaises(IndexError, operator.getitem, a, -4)
        a[-1] = e = Element('e')
        self.assertEqual(e, a[-1])
        del a[-1]
        self.assertEqual(2, len(a))
        
    def test_elementtree(self):
        ElementTree = self.etree.ElementTree
        
        f = BytesIO('<doc><one>One</one><two>Two</two></doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEqual(2, len(root))
        self.assertEqual('one', root[0].tag)
        self.assertEqual('two', root[1].tag)

    def test_text(self):
        ElementTree = self.etree.ElementTree
        
        f = BytesIO('<doc>This is a text</doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEqual('This is a text', root.text)

    def test_text_empty(self):
        ElementTree = self.etree.ElementTree
        
        f = BytesIO('<doc></doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEqual(None, root.text)

    def test_text_other(self):
        ElementTree = self.etree.ElementTree
        
        f = BytesIO('<doc><one>One</one></doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEqual(None, root.text)
        self.assertEqual('One', root[0].text)

    def test_text_escape_in(self):
        ElementTree = self.etree.ElementTree

        f = BytesIO('<doc>This is &gt; than a text</doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEqual('This is > than a text', root.text)

    def test_text_escape_out(self):
        Element = self.etree.Element

        a = Element("a")
        a.text = "<>&"
        self.assertXML(_bytes('<a>&lt;&gt;&amp;</a>'),
                       a)

    def test_text_escape_tostring(self):
        tostring = self.etree.tostring
        Element  = self.etree.Element

        a = Element("a")
        a.text = "<>&"
        self.assertEqual(_bytes('<a>&lt;&gt;&amp;</a>'),
                         tostring(a))

    def test_text_str_subclass(self):
        Element = self.etree.Element

        class strTest(str):
            pass

        a = Element("a")
        a.text = strTest("text")
        self.assertXML(_bytes('<a>text</a>'),
                       a)

    def test_tail(self):
        ElementTree = self.etree.ElementTree
        
        f = BytesIO('<doc>This is <i>mixed</i> content.</doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEqual(1, len(root))
        self.assertEqual('This is ', root.text)
        self.assertEqual(None, root.tail)
        self.assertEqual('mixed', root[0].text)
        self.assertEqual(' content.', root[0].tail)

    def test_tail_str_subclass(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        class strTest(str):
            pass

        a = Element("a")
        SubElement(a, "t").tail = strTest("tail")
        self.assertXML(_bytes('<a><t></t>tail</a>'),
                       a)

    def _test_del_tail(self):
        # this is discouraged for ET compat, should not be tested...
        XML = self.etree.XML
        
        root = XML(_bytes('<doc>This is <i>mixed</i> content.</doc>'))
        self.assertEqual(1, len(root))
        self.assertEqual('This is ', root.text)
        self.assertEqual(None, root.tail)
        self.assertEqual('mixed', root[0].text)
        self.assertEqual(' content.', root[0].tail)

        del root[0].tail

        self.assertEqual(1, len(root))
        self.assertEqual('This is ', root.text)
        self.assertEqual(None, root.tail)
        self.assertEqual('mixed', root[0].text)
        self.assertEqual(None, root[0].tail)

        root[0].tail = "TAIL"

        self.assertEqual(1, len(root))
        self.assertEqual('This is ', root.text)
        self.assertEqual(None, root.tail)
        self.assertEqual('mixed', root[0].text)
        self.assertEqual('TAIL', root[0].tail)

    def test_ElementTree(self):
        Element = self.etree.Element
        ElementTree = self.etree.ElementTree
        
        el = Element('hoi')
        doc = ElementTree(el)
        root = doc.getroot()
        self.assertEqual(None, root.text)
        self.assertEqual('hoi', root.tag)

    def test_attrib(self):
        ElementTree = self.etree.ElementTree
        
        f = BytesIO('<doc one="One" two="Two"/>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEqual('One', root.attrib['one'])
        self.assertEqual('Two', root.attrib['two'])
        self.assertRaises(KeyError, operator.getitem, root.attrib, 'three')

    def test_attrib_get(self):
        ElementTree = self.etree.ElementTree
        
        f = BytesIO('<doc one="One" two="Two"/>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEqual('One', root.attrib.get('one'))
        self.assertEqual('Two', root.attrib.get('two'))
        self.assertEqual(None, root.attrib.get('three'))
        self.assertEqual('foo', root.attrib.get('three', 'foo'))

    def test_attrib_dict(self):
        ElementTree = self.etree.ElementTree

        f = BytesIO('<doc one="One" two="Two"/>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        attrib = dict(root.attrib)
        self.assertEqual('One', attrib['one'])
        self.assertEqual('Two', attrib['two'])
        self.assertRaises(KeyError, operator.getitem, attrib, 'three')

    def test_attrib_copy(self):
        ElementTree = self.etree.ElementTree

        f = BytesIO('<doc one="One" two="Two"/>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        attrib = copy.copy(root.attrib)
        self.assertEqual('One', attrib['one'])
        self.assertEqual('Two', attrib['two'])
        self.assertRaises(KeyError, operator.getitem, attrib, 'three')

    def test_attrib_deepcopy(self):
        ElementTree = self.etree.ElementTree

        f = BytesIO('<doc one="One" two="Two"/>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        attrib = copy.deepcopy(root.attrib)
        self.assertEqual('One', attrib['one'])
        self.assertEqual('Two', attrib['two'])
        self.assertRaises(KeyError, operator.getitem, attrib, 'three')

    def test_attributes_get(self):
        ElementTree = self.etree.ElementTree
        
        f = BytesIO('<doc one="One" two="Two"/>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEqual('One', root.get('one'))
        self.assertEqual('Two', root.get('two'))
        self.assertEqual(None, root.get('three'))
        self.assertEqual('foo', root.get('three', 'foo'))

    def test_attrib_clear(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc one="One" two="Two"/>'))
        self.assertEqual('One', root.get('one'))
        self.assertEqual('Two', root.get('two'))
        root.attrib.clear()
        self.assertEqual(None, root.get('one'))
        self.assertEqual(None, root.get('two'))

    def test_attrib_set_clear(self):
        Element = self.etree.Element
        
        root = Element("root", one="One")
        root.set("two", "Two")
        self.assertEqual('One', root.get('one'))
        self.assertEqual('Two', root.get('two'))
        root.attrib.clear()
        self.assertEqual(None, root.get('one'))
        self.assertEqual(None, root.get('two'))

    def test_attrib_ns_clear(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        attribNS = '{http://foo/bar}x'

        parent = Element('parent')
        parent.set(attribNS, 'a')
        child = SubElement(parent, 'child')
        child.set(attribNS, 'b')

        self.assertEqual('a', parent.get(attribNS))
        self.assertEqual('b', child.get(attribNS))

        parent.clear()
        self.assertEqual(None, parent.get(attribNS))
        self.assertEqual('b', child.get(attribNS))

    def test_attrib_pop(self):
        ElementTree = self.etree.ElementTree
        
        f = BytesIO('<doc one="One" two="Two"/>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEqual('One', root.attrib['one'])
        self.assertEqual('Two', root.attrib['two'])

        self.assertEqual('One', root.attrib.pop('one'))

        self.assertEqual(None, root.attrib.get('one'))
        self.assertEqual('Two', root.attrib['two'])

    def test_attrib_pop_unknown(self):
        root = self.etree.XML(_bytes('<doc one="One" two="Two"/>'))
        self.assertRaises(KeyError, root.attrib.pop, 'NONE')

        self.assertEqual('One', root.attrib['one'])
        self.assertEqual('Two', root.attrib['two'])

    def test_attrib_pop_default(self):
        root = self.etree.XML(_bytes('<doc one="One" two="Two"/>'))
        self.assertEqual('Three', root.attrib.pop('three', 'Three'))

    def test_attrib_pop_empty_default(self):
        root = self.etree.XML(_bytes('<doc/>'))
        self.assertEqual('Three', root.attrib.pop('three', 'Three'))

    def test_attrib_pop_invalid_args(self):
        root = self.etree.XML(_bytes('<doc one="One" two="Two"/>'))
        self.assertRaises(TypeError, root.attrib.pop, 'One', None, None)

    def test_attribute_update_dict(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc alpha="Alpha" beta="Beta"/>'))
        items = list(root.attrib.items())
        items.sort()
        self.assertEqual(
            [('alpha', 'Alpha'), ('beta', 'Beta')],
            items)

        root.attrib.update({'alpha' : 'test', 'gamma' : 'Gamma'})

        items = list(root.attrib.items())
        items.sort()
        self.assertEqual(
            [('alpha', 'test'), ('beta', 'Beta'), ('gamma', 'Gamma')],
            items)

    def test_attribute_update_sequence(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc alpha="Alpha" beta="Beta"/>'))
        items = list(root.attrib.items())
        items.sort()
        self.assertEqual(
            [('alpha', 'Alpha'), ('beta', 'Beta')],
            items)

        root.attrib.update({'alpha' : 'test', 'gamma' : 'Gamma'}.items())

        items = list(root.attrib.items())
        items.sort()
        self.assertEqual(
            [('alpha', 'test'), ('beta', 'Beta'), ('gamma', 'Gamma')],
            items)

    def test_attribute_update_iter(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc alpha="Alpha" beta="Beta"/>'))
        items = list(root.attrib.items())
        items.sort()
        self.assertEqual(
            [('alpha', 'Alpha'), ('beta', 'Beta')],
            items)

        root.attrib.update(iter({'alpha' : 'test', 'gamma' : 'Gamma'}.items()))

        items = list(root.attrib.items())
        items.sort()
        self.assertEqual(
            [('alpha', 'test'), ('beta', 'Beta'), ('gamma', 'Gamma')],
            items)

    def test_attribute_update_attrib(self):
        XML = self.etree.XML

        root = XML(_bytes('<doc alpha="Alpha" beta="Beta"/>'))
        items = list(root.attrib.items())
        items.sort()
        self.assertEqual(
            [('alpha', 'Alpha'), ('beta', 'Beta')],
                                                  items)

        other = XML(_bytes('<doc alpha="test" gamma="Gamma"/>'))
        root.attrib.update(other.attrib)

        items = list(root.attrib.items())
        items.sort()
        self.assertEqual(
            [('alpha', 'test'), ('beta', 'Beta'), ('gamma', 'Gamma')],
                                                                     items)

    def test_attribute_keys(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc alpha="Alpha" beta="Beta" gamma="Gamma"/>'))
        keys = list(root.attrib.keys())
        keys.sort()
        self.assertEqual(['alpha', 'beta', 'gamma'], keys)

    def test_attribute_keys2(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc alpha="Alpha" beta="Beta" gamma="Gamma"/>'))
        keys = list(root.keys())
        keys.sort()
        self.assertEqual(['alpha', 'beta', 'gamma'], keys)

    def test_attribute_items2(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc alpha="Alpha" beta="Beta" gamma="Gamma"/>'))
        items = list(root.items())
        items.sort()
        self.assertEqual(
            [('alpha','Alpha'), ('beta','Beta'), ('gamma','Gamma')],
            items)

    def test_attribute_keys_ns(self):
        XML = self.etree.XML

        root = XML(_bytes('<foo bar="Bar" xmlns:ns="http://ns.codespeak.net/test" ns:baz="Baz" />'))
        keys = list(root.keys())
        keys.sort()
        self.assertEqual(['bar', '{http://ns.codespeak.net/test}baz'],
                          keys)
        
    def test_attribute_values(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc alpha="Alpha" beta="Beta" gamma="Gamma"/>'))
        values = list(root.attrib.values())
        values.sort()
        self.assertEqual(['Alpha', 'Beta', 'Gamma'], values)

    def test_attribute_values_ns(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<foo bar="Bar" xmlns:ns="http://ns.codespeak.net/test" ns:baz="Baz" />'))
        values = list(root.attrib.values())
        values.sort()
        self.assertEqual(
            ['Bar', 'Baz'], values)
        
    def test_attribute_items(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc alpha="Alpha" beta="Beta" gamma="Gamma"/>'))
        items = list(root.attrib.items())
        items.sort()
        self.assertEqual([
            ('alpha', 'Alpha'),
            ('beta', 'Beta'),
            ('gamma', 'Gamma'),
            ], 
            items)

    def test_attribute_items_ns(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<foo bar="Bar" xmlns:ns="http://ns.codespeak.net/test" ns:baz="Baz" />'))
        items = list(root.attrib.items())
        items.sort()
        self.assertEqual(
            [('bar', 'Bar'), ('{http://ns.codespeak.net/test}baz', 'Baz')],
            items)

    def test_attribute_str(self):
        XML = self.etree.XML

        expected = "{'{http://ns.codespeak.net/test}baz': 'Baz', 'bar': 'Bar'}"
        alternative = "{'bar': 'Bar', '{http://ns.codespeak.net/test}baz': 'Baz'}"
        
        root = XML(_bytes('<foo bar="Bar" xmlns:ns="http://ns.codespeak.net/test" ns:baz="Baz" />'))
        try:
            self.assertEqual(expected, str(root.attrib))
        except AssertionError:
            self.assertEqual(alternative, str(root.attrib))

    def test_attribute_contains(self):
        XML = self.etree.XML

        root = XML(_bytes('<foo bar="Bar" xmlns:ns="http://ns.codespeak.net/test" ns:baz="Baz" />'))
        self.assertEqual(
            True, 'bar' in root.attrib)
        self.assertEqual(
            False, 'baz' in root.attrib)
        self.assertEqual(
            False, 'hah' in root.attrib)
        self.assertEqual(
            True,
            '{http://ns.codespeak.net/test}baz' in root.attrib)

    def test_attribute_set(self):
        Element = self.etree.Element

        root = Element("root")
        root.set("attr", "TEST")
        self.assertEqual("TEST", root.get("attr"))

    def test_attrib_as_attrib(self):
        Element = self.etree.Element

        root = Element("root")
        root.set("attr", "TEST")
        self.assertEqual("TEST", root.attrib["attr"])

        root2 = Element("root2", root.attrib)
        self.assertEqual("TEST", root2.attrib["attr"])

    def test_attribute_iterator(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc alpha="Alpha" beta="Beta" gamma="Gamma" />'))
        result = []
        for key in root.attrib:
            result.append(key)
        result.sort()
        self.assertEqual(['alpha', 'beta', 'gamma'], result)

    def test_attribute_manipulation(self):
        Element = self.etree.Element

        a = Element('a')
        a.attrib['foo'] = 'Foo'
        a.attrib['bar'] = 'Bar'
        self.assertEqual('Foo', a.attrib['foo'])
        del a.attrib['foo']
        self.assertRaises(KeyError, operator.getitem, a.attrib, 'foo')

    def test_del_attribute_ns(self):
        Element = self.etree.Element

        a = Element('a')
        a.attrib['{http://a/}foo'] = 'Foo'
        a.attrib['{http://a/}bar'] = 'Bar'
        self.assertEqual(None, a.get('foo'))
        self.assertEqual('Foo', a.get('{http://a/}foo'))
        self.assertEqual('Foo', a.attrib['{http://a/}foo'])

        self.assertRaises(KeyError, operator.delitem, a.attrib, 'foo')
        self.assertEqual('Foo', a.attrib['{http://a/}foo'])

        del a.attrib['{http://a/}foo']
        self.assertRaises(KeyError, operator.getitem, a.attrib, 'foo')

    def test_del_attribute_ns_parsed(self):
        XML = self.etree.XML

        a = XML(_bytes('<a xmlns:nsa="http://a/" nsa:foo="FooNS" foo="Foo" />'))

        self.assertEqual('Foo', a.attrib['foo'])
        self.assertEqual('FooNS', a.attrib['{http://a/}foo'])

        del a.attrib['foo']
        self.assertEqual('FooNS', a.attrib['{http://a/}foo'])
        self.assertRaises(KeyError, operator.getitem, a.attrib, 'foo')
        self.assertRaises(KeyError, operator.delitem, a.attrib, 'foo')

        del a.attrib['{http://a/}foo']
        self.assertRaises(KeyError, operator.getitem, a.attrib, '{http://a/}foo')
        self.assertRaises(KeyError, operator.getitem, a.attrib, 'foo')

        a = XML(_bytes('<a xmlns:nsa="http://a/" foo="Foo" nsa:foo="FooNS" />'))

        self.assertEqual('Foo', a.attrib['foo'])
        self.assertEqual('FooNS', a.attrib['{http://a/}foo'])

        del a.attrib['foo']
        self.assertEqual('FooNS', a.attrib['{http://a/}foo'])
        self.assertRaises(KeyError, operator.getitem, a.attrib, 'foo')

        del a.attrib['{http://a/}foo']
        self.assertRaises(KeyError, operator.getitem, a.attrib, '{http://a/}foo')
        self.assertRaises(KeyError, operator.getitem, a.attrib, 'foo')

    def test_XML(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc>This is a text.</doc>'))
        self.assertEqual(0, len(root))
        self.assertEqual('This is a text.', root.text)

    def test_XMLID(self):
        XMLID = self.etree.XMLID
        XML   = self.etree.XML
        xml_text = _bytes('''
        <document>
          <h1 id="chapter1">...</h1>
          <p id="note1" class="note">...</p>
          <p>Regular paragraph.</p>
          <p xml:id="xmlid">XML:ID paragraph.</p>
          <p id="warn1" class="warning">...</p>
        </document>
        ''')

        root, dic = XMLID(xml_text)
        root2 = XML(xml_text)
        self.assertEqual(self._writeElement(root),
                          self._writeElement(root2))
        expected = {
            "chapter1" : root[0],
            "note1"    : root[1],
            "warn1"    : root[4]
            }
        self.assertEqual(dic, expected)

    def test_fromstring(self):
        fromstring = self.etree.fromstring

        root = fromstring('<doc>This is a text.</doc>')
        self.assertEqual(0, len(root))
        self.assertEqual('This is a text.', root.text)

    required_versions_ET['test_fromstringlist'] = (1,3)
    def test_fromstringlist(self):
        fromstringlist = self.etree.fromstringlist

        root = fromstringlist(["<do", "c>T", "hi", "s is",
                               " a text.<", "/doc", ">"])
        self.assertEqual(0, len(root))
        self.assertEqual('This is a text.', root.text)

    required_versions_ET['test_fromstringlist_characters'] = (1,3)
    def test_fromstringlist_characters(self):
        fromstringlist = self.etree.fromstringlist

        root = fromstringlist(list('<doc>This is a text.</doc>'))
        self.assertEqual(0, len(root))
        self.assertEqual('This is a text.', root.text)

    required_versions_ET['test_fromstringlist_single'] = (1,3)
    def test_fromstringlist_single(self):
        fromstringlist = self.etree.fromstringlist

        root = fromstringlist(['<doc>This is a text.</doc>'])
        self.assertEqual(0, len(root))
        self.assertEqual('This is a text.', root.text)

    def test_iselement(self):
        iselement = self.etree.iselement
        Element = self.etree.Element
        ElementTree = self.etree.ElementTree
        XML = self.etree.XML
        Comment = self.etree.Comment
        ProcessingInstruction = self.etree.ProcessingInstruction
        
        el = Element('hoi')
        self.assertTrue(iselement(el))

        el2 = XML(_bytes('<foo/>'))
        self.assertTrue(iselement(el2))

        tree = ElementTree(element=Element('dag'))
        self.assertTrue(not iselement(tree))
        self.assertTrue(iselement(tree.getroot()))

        c = Comment('test')
        self.assertTrue(iselement(c))

        p = ProcessingInstruction("test", "some text")
        self.assertTrue(iselement(p))
        
    def test_iteration(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc><one/><two>Two</two>Hm<three/></doc>'))
        result = []
        for el in root:
            result.append(el.tag)
        self.assertEqual(['one', 'two', 'three'], result)

    def test_iteration_empty(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc></doc>'))
        result = []
        for el in root:
            result.append(el.tag)
        self.assertEqual([], result)

    def test_iteration_text_only(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc>Text</doc>'))
        result = []
        for el in root:
            result.append(el.tag)
        self.assertEqual([], result)

    def test_iteration_crash(self):
        # this would cause a crash in the past
        fromstring = self.etree.fromstring
        root = etree.fromstring('<html><p></p>x</html>')
        for elem in root:
            elem.tail = ''

    def test_iteration_reversed(self):
        XML = self.etree.XML
        root = XML(_bytes('<doc><one/><two>Two</two>Hm<three/></doc>'))
        result = []
        for el in reversed(root):
            result.append(el.tag)
        self.assertEqual(['three', 'two', 'one'], result)

    def test_iteration_subelement(self):
        XML = self.etree.XML

        root = XML(_bytes('<doc><one/><two>Two</two>Hm<three/></doc>'))
        result = []
        add = True
        for el in root:
            result.append(el.tag)
            if add:
                self.etree.SubElement(root, 'four')
                add = False
        self.assertEqual(['one', 'two', 'three', 'four'], result)

    def test_iteration_del_child(self):
        XML = self.etree.XML

        root = XML(_bytes('<doc><one/><two>Two</two>Hm<three/></doc>'))
        result = []
        for el in root:
            result.append(el.tag)
            del root[-1]
        self.assertEqual(['one', 'two'], result)

    def test_iteration_double(self):
        XML = self.etree.XML

        root = XML(_bytes('<doc><one/><two/></doc>'))
        result = []
        for el0 in root:
            result.append(el0.tag)
            for el1 in root:
                result.append(el1.tag)
        self.assertEqual(['one','one', 'two', 'two', 'one', 'two'], result)

    required_versions_ET['test_itertext'] = (1,3)
    def test_itertext(self):
        # ET 1.3+
        XML = self.etree.XML
        root = XML(_bytes("<root>RTEXT<a></a>ATAIL<b/><c>CTEXT</c>CTAIL</root>"))

        text = list(root.itertext())
        self.assertEqual(["RTEXT", "ATAIL", "CTEXT", "CTAIL"],
                          text)

    required_versions_ET['test_itertext_child'] = (1,3)
    def test_itertext_child(self):
        # ET 1.3+
        XML = self.etree.XML
        root = XML(_bytes("<root>RTEXT<a></a>ATAIL<b/><c>CTEXT</c>CTAIL</root>"))

        text = list(root[2].itertext())
        self.assertEqual(["CTEXT"],
                          text)

    def test_findall(self):
        XML = self.etree.XML
        root = XML(_bytes('<a><b><c/></b><b/><c><b/></c></a>'))
        self.assertEqual(len(list(root.findall("c"))), 1)
        self.assertEqual(len(list(root.findall(".//c"))), 2)
        self.assertEqual(len(list(root.findall(".//b"))), 3)
        self.assertEqual(len(list(root.findall(".//b"))[0]), 1)
        self.assertEqual(len(list(root.findall(".//b"))[1]), 0)
        self.assertEqual(len(list(root.findall(".//b"))[2]), 0)

    def test_findall_ns(self):
        XML = self.etree.XML
        root = XML(_bytes('<a xmlns:x="X" xmlns:y="Y"><x:b><c/></x:b><b/><c><x:b/><b/></c><b/></a>'))
        self.assertEqual(len(list(root.findall(".//{X}b"))), 2)
        self.assertEqual(len(list(root.findall(".//b"))), 3)
        self.assertEqual(len(list(root.findall("b"))), 2)

    def test_element_with_attributes_keywords(self):
        Element = self.etree.Element
        
        el = Element('tag', foo='Foo', bar='Bar')
        self.assertEqual('Foo', el.attrib['foo'])
        self.assertEqual('Bar', el.attrib['bar'])

    def test_element_with_attributes(self):
        Element = self.etree.Element
        
        el = Element('tag', {'foo': 'Foo', 'bar': 'Bar'})
        self.assertEqual('Foo', el.attrib['foo'])
        self.assertEqual('Bar', el.attrib['bar'])

    def test_element_with_attributes_extra(self):
        Element = self.etree.Element

        el = Element('tag', {'foo': 'Foo', 'bar': 'Bar'}, baz='Baz')
        self.assertEqual('Foo', el.attrib['foo'])
        self.assertEqual('Bar', el.attrib['bar'])
        self.assertEqual('Baz', el.attrib['baz'])

    def test_element_with_attributes_extra_duplicate(self):
        Element = self.etree.Element

        el = Element('tag', {'foo': 'Foo', 'bar': 'Bar'}, bar='Baz')
        self.assertEqual('Foo', el.attrib['foo'])
        self.assertEqual('Baz', el.attrib['bar'])

    def test_element_with_attributes_ns(self):
        Element = self.etree.Element

        el = Element('tag', {'{ns1}foo':'Foo', '{ns2}bar':'Bar'})
        self.assertEqual('Foo', el.attrib['{ns1}foo'])
        self.assertEqual('Bar', el.attrib['{ns2}bar'])

    def test_subelement_with_attributes(self):
        Element =  self.etree.Element
        SubElement = self.etree.SubElement
        
        el = Element('tag')
        SubElement(el, 'foo', {'foo':'Foo'}, baz="Baz")
        self.assertEqual("Baz", el[0].attrib['baz'])
        self.assertEqual('Foo', el[0].attrib['foo'])

    def test_subelement_with_attributes_ns(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        el = Element('tag')
        SubElement(el, 'foo', {'{ns1}foo':'Foo', '{ns2}bar':'Bar'})
        self.assertEqual('Foo', el[0].attrib['{ns1}foo'])
        self.assertEqual('Bar', el[0].attrib['{ns2}bar'])
        
    def test_write(self):
        ElementTree = self.etree.ElementTree
        XML = self.etree.XML

        for i in range(10):
            f = BytesIO() 
            root = XML(_bytes('<doc%s>This is a test.</doc%s>' % (i, i)))
            tree = ElementTree(element=root)
            tree.write(f)
            data = f.getvalue()
            self.assertEqual(
                _bytes('<doc%s>This is a test.</doc%s>' % (i, i)),
                canonicalize(data))

    required_versions_ET['test_write_method_html'] = (1,3)
    def test_write_method_html(self):
        ElementTree = self.etree.ElementTree
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        html = Element('html')
        body = SubElement(html, 'body')
        p = SubElement(body, 'p')
        p.text = "html"
        SubElement(p, 'br').tail = "test"

        tree = ElementTree(element=html)
        f = BytesIO() 
        tree.write(f, method="html")
        data = f.getvalue().replace(_bytes('\n'),_bytes(''))

        self.assertEqual(_bytes('<html><body><p>html<br>test</p></body></html>'),
                          data)

    required_versions_ET['test_write_method_text'] = (1,3)
    def test_write_method_text(self):
        ElementTree = self.etree.ElementTree
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        a.text = "A"
        a.tail = "tail"
        b = SubElement(a, 'b')
        b.text = "B"
        b.tail = "TAIL"
        c = SubElement(a, 'c')
        c.text = "C"
        
        tree = ElementTree(element=a)
        f = BytesIO() 
        tree.write(f, method="text")
        data = f.getvalue()

        self.assertEqual(_bytes('ABTAILCtail'),
                          data)
        
    def test_write_fail(self):
        ElementTree = self.etree.ElementTree
        XML = self.etree.XML

        tree = ElementTree( XML(_bytes('<doc>This is a test.</doc>')) )
        self.assertRaises(IOError, tree.write,
                          "definitely////\\-\\nonexisting\\-\\////FILE")

    # this could trigger a crash, apparently because the document
    # reference was prematurely garbage collected
    def test_crash(self):
        Element = self.etree.Element
        
        element = Element('tag')
        for i in range(10):
            element.attrib['key'] = 'value'
            value = element.attrib['key']
            self.assertEqual(value, 'value')
            
    # from doctest; for some reason this caused crashes too
    def test_write_ElementTreeDoctest(self):
        Element = self.etree.Element
        ElementTree = self.etree.ElementTree
        
        f = BytesIO()
        for i in range(10):
            element = Element('tag%s' % i)
            self._check_element(element)
            tree = ElementTree(element)
            tree.write(f)
            self._check_element_tree(tree)

    def test_subelement_reference(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        el = Element('foo')
        el2 = SubElement(el, 'bar')
        el3 = SubElement(el2, 'baz')

        al = Element('foo2')
        al2 = SubElement(al, 'bar2')
        al3 = SubElement(al2, 'baz2')

        # now move al2 into el
        el.append(al2)

        # now change al3 directly
        al3.text = 'baz2-modified'

        # it should have changed through this route too
        self.assertEqual(
            'baz2-modified',
            el[1][0].text)

    def test_set_text(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        a.text = 'hoi'
        self.assertEqual(
            'hoi',
            a.text)
        self.assertEqual(
            'b',
            a[0].tag)

    def test_set_text2(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        a.text = 'hoi'
        b = SubElement(a ,'b')
        self.assertEqual(
            'hoi',
            a.text)
        self.assertEqual(
            'b',
            a[0].tag)

    def test_set_text_none(self):
        Element = self.etree.Element

        a = Element('a')

        a.text = 'foo'
        a.text = None

        self.assertEqual(
            None,
            a.text)
        self.assertXML(_bytes('<a></a>'), a)
        
    def test_set_text_empty(self):
        Element = self.etree.Element

        a = Element('a')
        self.assertEqual(None, a.text)

        a.text = ''
        self.assertEqual('', a.text)
        self.assertXML(_bytes('<a></a>'), a)
        
    def test_tail1(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        a.tail = 'dag'
        self.assertEqual('dag',
                          a.tail)
        b = SubElement(a, 'b')
        b.tail = 'hoi'
        self.assertEqual('hoi',
                          b.tail)
        self.assertEqual('dag',
                          a.tail)

    def test_tail_append(self):
        Element = self.etree.Element
        
        a = Element('a')
        b = Element('b')
        b.tail = 'b_tail'
        a.append(b)
        self.assertEqual('b_tail',
                          b.tail)

    def test_tail_set_twice(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        b.tail = 'foo'
        b.tail = 'bar'
        self.assertEqual('bar',
                          b.tail)
        self.assertXML(_bytes('<a><b></b>bar</a>'), a)
        
    def test_tail_set_none(self):
        Element = self.etree.Element
        a = Element('a')
        a.tail = 'foo'
        a.tail = None
        self.assertEqual(
            None,
            a.tail)
        self.assertXML(_bytes('<a></a>'), a)

    required_versions_ET['test_extend'] = (1,3)
    def test_extend(self):
        root = self.etree.Element('foo')
        for i in range(3):
            element = self.etree.SubElement(root, 'a%s' % i)
            element.text = "text%d" % i
            element.tail = "tail%d" % i

        elements = []
        for i in range(3):
            new_element = self.etree.Element("test%s" % i)
            new_element.text = "TEXT%s" % i
            new_element.tail = "TAIL%s" % i
            elements.append(new_element)

        root.extend(elements)

        self.assertEqual(
            ["a0", "a1", "a2", "test0", "test1", "test2"],
            [ el.tag for el in root ])
        self.assertEqual(
            ["text0", "text1", "text2", "TEXT0", "TEXT1", "TEXT2"],
            [ el.text for el in root ])
        self.assertEqual(
            ["tail0", "tail1", "tail2", "TAIL0", "TAIL1", "TAIL2"],
            [ el.tail for el in root ])

    def test_comment(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        Comment = self.etree.Comment

        a = Element('a')
        a.append(Comment('foo'))
        self.assertEqual(a[0].tag, Comment)
        self.assertEqual(a[0].text, 'foo')

    # ElementTree < 1.3 adds whitespace around comments
    required_versions_ET['test_comment_text'] = (1,3)
    def test_comment_text(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        Comment = self.etree.Comment
        tostring = self.etree.tostring

        a = Element('a')
        a.append(Comment('foo'))
        self.assertEqual(a[0].text, 'foo')

        self.assertEqual(
            _bytes('<a><!--foo--></a>'),
            tostring(a))

        a[0].text = "TEST"
        self.assertEqual(a[0].text, 'TEST')

        self.assertEqual(
            _bytes('<a><!--TEST--></a>'),
            tostring(a))

    # ElementTree < 1.3 adds whitespace around comments
    required_versions_ET['test_comment_whitespace'] = (1,3)
    def test_comment_whitespace(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        Comment = self.etree.Comment
        tostring = self.etree.tostring

        a = Element('a')
        a.append(Comment(' foo  '))
        self.assertEqual(a[0].text, ' foo  ')
        self.assertEqual(
            _bytes('<a><!-- foo  --></a>'),
            tostring(a))
        
    def test_comment_nonsense(self):
        Comment = self.etree.Comment
        c = Comment('foo')
        self.assertEqual({}, c.attrib)
        self.assertEqual([], list(c.keys()))
        self.assertEqual([], list(c.items()))
        self.assertEqual(None, c.get('hoi'))
        self.assertEqual(0, len(c))
        # should not iterate
        for i in c:
            pass

    def test_pi(self):
        # lxml.etree separates target and text
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        ProcessingInstruction = self.etree.ProcessingInstruction

        a = Element('a')
        a.append(ProcessingInstruction('foo', 'some more text'))
        self.assertEqual(a[0].tag, ProcessingInstruction)
        self.assertXML(_bytes("<a><?foo some more text?></a>"),
                       a)

    def test_processinginstruction(self):
        # lxml.etree separates target and text
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        ProcessingInstruction = self.etree.PI

        a = Element('a')
        a.append(ProcessingInstruction('foo', 'some more text'))
        self.assertEqual(a[0].tag, ProcessingInstruction)
        self.assertXML(_bytes("<a><?foo some more text?></a>"),
                       a)

    def test_pi_nonsense(self):
        ProcessingInstruction = self.etree.ProcessingInstruction
        pi = ProcessingInstruction('foo')
        self.assertEqual({}, pi.attrib)
        self.assertEqual([], list(pi.keys()))
        self.assertEqual([], list(pi.items()))
        self.assertEqual(None, pi.get('hoi'))
        self.assertEqual(0, len(pi))
        # should not iterate
        for i in pi:
            pass

    def test_setitem(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = Element('c')
        a[0] = c
        self.assertEqual(
            c,
            a[0])
        self.assertXML(_bytes('<a><c></c></a>'),
                       a)
        self.assertXML(_bytes('<b></b>'),
                       b)
        
    def test_setitem2(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        for i in range(5):
            b = SubElement(a, 'b%s' % i)
            c = SubElement(b, 'c')
        for i in range(5):
            d = Element('d')
            e = SubElement(d, 'e')
            a[i] = d
        self.assertXML(
            _bytes('<a><d><e></e></d><d><e></e></d><d><e></e></d><d><e></e></d><d><e></e></d></a>'),
            a)
        self.assertXML(_bytes('<c></c>'),
                       c)

    def test_setitem_replace(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        SubElement(a, 'b')
        d = Element('d')
        a[0] = d
        self.assertXML(_bytes('<a><d></d></a>'), a)

    def test_setitem_indexerror(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')

        self.assertRaises(IndexError, operator.setitem, a, 1, Element('c'))

    def test_setitem_tail(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        b.tail = 'B2'
        c = Element('c')
        c.tail = 'C2'

        a[0] = c
        self.assertXML(
            _bytes('<a><c></c>C2</a>'),
            a)

    def test_tag_write(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')

        a.tag = 'c'

        self.assertEqual(
            'c',
            a.tag)

        self.assertXML(
            _bytes('<c><b></b></c>'),
            a)

    def test_tag_reset_ns(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        tostring = self.etree.tostring

        a = Element('{a}a')
        b1 = SubElement(a, '{a}b')
        b2 = SubElement(a, '{b}b')

        self.assertEqual('{a}b',  b1.tag)

        b1.tag = 'c'

        # can't use C14N here!
        self.assertEqual('c', b1.tag)
        self.assertEqual(_bytes('<c'), tostring(b1)[:2])
        self.assertTrue(_bytes('<c') in tostring(a))

    def test_tag_reset_root_ns(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        tostring = self.etree.tostring

        a = Element('{a}a')
        b1 = SubElement(a, '{a}b')
        b2 = SubElement(a, '{b}b')

        a.tag = 'c'

        self.assertEqual(
            'c',
            a.tag)

        # can't use C14N here!
        self.assertEqual('c',  a.tag)
        self.assertEqual(_bytes('<c'), tostring(a)[:2])

    def test_tag_str_subclass(self):
        Element = self.etree.Element

        class strTest(str):
            pass

        a = Element("a")
        a.tag = strTest("TAG")
        self.assertXML(_bytes('<TAG></TAG>'),
                       a)

    def test_delitem(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')

        del a[1]
        self.assertXML(
            _bytes('<a><b></b><d></d></a>'),
            a)

        del a[0]
        self.assertXML(
            _bytes('<a><d></d></a>'),
            a)

        del a[0]
        self.assertXML(
            _bytes('<a></a>'),
            a)
        # move deleted element into other tree afterwards
        other = Element('other')
        other.append(c)
        self.assertXML(
            _bytes('<other><c></c></other>'),
            other)
    
    def test_del_insert(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        bs = SubElement(b, 'bs')
        c = SubElement(a, 'c')
        cs = SubElement(c, 'cs')

        el = a[0]
        self.assertXML(
            _bytes('<a><b><bs></bs></b><c><cs></cs></c></a>'),
            a)
        self.assertXML(_bytes('<b><bs></bs></b>'), b)
        self.assertXML(_bytes('<c><cs></cs></c>'), c)

        del a[0]
        self.assertXML(
            _bytes('<a><c><cs></cs></c></a>'),
            a)
        self.assertXML(_bytes('<b><bs></bs></b>'), b)
        self.assertXML(_bytes('<c><cs></cs></c>'), c)

        a.insert(0, el)
        self.assertXML(
            _bytes('<a><b><bs></bs></b><c><cs></cs></c></a>'),
            a)
        self.assertXML(_bytes('<b><bs></bs></b>'), b)
        self.assertXML(_bytes('<c><cs></cs></c>'), c)

    def test_del_setitem(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        bs = SubElement(b, 'bs')
        c = SubElement(a, 'c')
        cs = SubElement(c, 'cs')

        el = a[0]
        del a[0]
        a[0] = el
        self.assertXML(
            _bytes('<a><b><bs></bs></b></a>'),
            a)
        self.assertXML(_bytes('<b><bs></bs></b>'), b)
        self.assertXML(_bytes('<c><cs></cs></c>'), c)

    def test_del_setslice(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        bs = SubElement(b, 'bs')
        c = SubElement(a, 'c')
        cs = SubElement(c, 'cs')

        el = a[0]
        del a[0]
        a[0:0] = [el]
        self.assertXML(
            _bytes('<a><b><bs></bs></b><c><cs></cs></c></a>'),
            a)
        self.assertXML(_bytes('<b><bs></bs></b>'), b)
        self.assertXML(_bytes('<c><cs></cs></c>'), c)

    def test_replace_slice_tail(self):
        XML = self.etree.XML
        a = XML(_bytes('<a><b></b>B2<c></c>C2</a>'))
        b, c = a

        a[:] = []

        self.assertEqual("B2", b.tail)
        self.assertEqual("C2", c.tail)

    def test_merge_namespaced_subtree_as_slice(self):
        XML = self.etree.XML
        root = XML(_bytes(
            '<foo><bar xmlns:baz="http://huhu"><puh><baz:bump1 /><baz:bump2 /></puh></bar></foo>'))
        root[:] = root.findall('.//puh') # delete bar from hierarchy

        # previously, this lost a namespace declaration on bump2
        result = self.etree.tostring(root)
        foo = self.etree.fromstring(result)

        self.assertEqual('puh', foo[0].tag)
        self.assertEqual('{http://huhu}bump1', foo[0][0].tag)
        self.assertEqual('{http://huhu}bump2', foo[0][1].tag)

    def test_delitem_tail(self):
        ElementTree = self.etree.ElementTree
        f = BytesIO('<a><b></b>B2<c></c>C2</a>')
        doc = ElementTree(file=f)
        a = doc.getroot()
        del a[0]
        self.assertXML(
            _bytes('<a><c></c>C2</a>'),
            a)
        
    def test_clear(self):
        Element = self.etree.Element
     
        a = Element('a')
        a.text = 'foo'
        a.tail = 'bar'
        a.set('hoi', 'dag')
        a.clear()
        self.assertEqual(None, a.text)
        self.assertEqual(None, a.tail)
        self.assertEqual(None, a.get('hoi'))
        self.assertEqual('a', a.tag)

    def test_clear_sub(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        a.text = 'foo'
        a.tail = 'bar'
        a.set('hoi', 'dag')
        b = SubElement(a, 'b')
        c = SubElement(b, 'c')
        a.clear()
        self.assertEqual(None, a.text)
        self.assertEqual(None, a.tail)
        self.assertEqual(None, a.get('hoi'))
        self.assertEqual('a', a.tag)
        self.assertEqual(0, len(a))
        self.assertXML(_bytes('<a></a>'),
                       a)
        self.assertXML(_bytes('<b><c></c></b>'),
                       b)
    
    def test_clear_tail(self):
        ElementTree = self.etree.ElementTree
        f = BytesIO('<a><b></b>B2<c></c>C2</a>')
        doc = ElementTree(file=f)
        a = doc.getroot()
        a.clear()
        self.assertXML(
            _bytes('<a></a>'),
            a)

    def test_insert(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = Element('d')
        a.insert(0, d)

        self.assertEqual(
            d,
            a[0])

        self.assertXML(
            _bytes('<a><d></d><b></b><c></c></a>'),
            a)

        e = Element('e')
        a.insert(2, e)
        self.assertEqual(
            e,
            a[2])
        self.assertXML(
            _bytes('<a><d></d><b></b><e></e><c></c></a>'),
            a)

    def test_insert_beyond_index(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = Element('c')

        a.insert(2, c)
        self.assertEqual(
            c,
            a[1])
        self.assertXML(
            _bytes('<a><b></b><c></c></a>'),
            a)

    def test_insert_negative(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')

        d = Element('d')
        a.insert(-1, d)
        self.assertEqual(
            d,
            a[-2])
        self.assertXML(
            _bytes('<a><b></b><d></d><c></c></a>'),
            a)

    def test_insert_tail(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')

        c = Element('c')
        c.tail = 'C2'

        a.insert(0, c)
        self.assertXML(
            _bytes('<a><c></c>C2<b></b></a>'),
            a)
        
    def test_remove(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')

        a.remove(b)
        self.assertEqual(
            c,
            a[0])
        self.assertXML(
            _bytes('<a><c></c></a>'),
            a)
        
    def test_remove_ns(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('{http://test}a')
        b = SubElement(a, '{http://test}b')
        c = SubElement(a, '{http://test}c')

        a.remove(b)
        self.assertXML(
            _bytes('<ns0:a xmlns:ns0="http://test"><ns0:c></ns0:c></ns0:a>'),
            a)
        self.assertXML(
            _bytes('<ns0:b xmlns:ns0="http://test"></ns0:b>'),
            b)

    def test_remove_nonexisting(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = Element('d')
        self.assertRaises(
            ValueError, a.remove, d)

    def test_remove_tail(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        b.tail = 'b2'
        a.remove(b)
        self.assertXML(
            _bytes('<a></a>'),
            a)
        self.assertEqual('b2', b.tail)

    def _test_getchildren(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        e = SubElement(c, 'e')
        self.assertXML(
            _bytes('<a><b><d></d></b><c><e></e></c></a>'),
            a)
        self.assertEqual(
            [b, c],
            a.getchildren())
        self.assertEqual(
            [d],
            b.getchildren())
        self.assertEqual(
            [],
            d.getchildren())

    def test_makeelement(self):
        Element = self.etree.Element

        a = Element('a')
        b = a.makeelement('c', {'hoi':'dag'})
        self.assertXML(
            _bytes('<c hoi="dag"></c>'),
            b)

    required_versions_ET['test_iter'] = (1,3)
    def test_iter(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        e = SubElement(c, 'e')

        self.assertEqual(
            [a, b, d, c, e],
            list(a.iter()))
        self.assertEqual(
            [d],
            list(d.iter()))

    def test_getiterator(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        e = SubElement(c, 'e')

        self.assertEqual(
            [a, b, d, c, e],
            list(a.getiterator()))
        self.assertEqual(
            [d],
            list(d.getiterator()))

    def test_getiterator_empty(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        e = SubElement(c, 'e')

        self.assertEqual(
            [],
            list(a.getiterator('none')))
        self.assertEqual(
            [],
            list(e.getiterator('none')))
        self.assertEqual(
            [e],
            list(e.getiterator()))

    def test_getiterator_filter(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        e = SubElement(c, 'e')

        self.assertEqual(
            [a],
            list(a.getiterator('a')))
        a2 = SubElement(e, 'a')
        self.assertEqual(
            [a, a2],
            list(a.getiterator('a')))
        self.assertEqual(
            [a2],
            list(c.getiterator('a')))

    def test_getiterator_filter_all(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        e = SubElement(c, 'e')

        self.assertEqual(
            [a, b, d, c, e],
            list(a.getiterator('*')))

    def test_getiterator_filter_comment(self):
        Element = self.etree.Element
        Comment = self.etree.Comment
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        comment_b = Comment("TEST-b")
        b.append(comment_b)

        self.assertEqual(
            [comment_b],
            list(a.getiterator(Comment)))

        comment_a = Comment("TEST-a")
        a.append(comment_a)

        self.assertEqual(
            [comment_b, comment_a],
            list(a.getiterator(Comment)))

        self.assertEqual(
            [comment_b],
            list(b.getiterator(Comment)))

    def test_getiterator_filter_pi(self):
        Element = self.etree.Element
        PI = self.etree.ProcessingInstruction
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        pi_b = PI("TEST-b")
        b.append(pi_b)

        self.assertEqual(
            [pi_b],
            list(a.getiterator(PI)))

        pi_a = PI("TEST-a")
        a.append(pi_a)

        self.assertEqual(
            [pi_b, pi_a],
            list(a.getiterator(PI)))

        self.assertEqual(
            [pi_b],
            list(b.getiterator(PI)))

    def test_getiterator_with_text(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        a.text = 'a'
        b = SubElement(a, 'b')
        b.text = 'b'
        b.tail = 'b1'
        c = SubElement(a, 'c')
        c.text = 'c'
        c.tail = 'c1'
        d = SubElement(b, 'd')
        c.text = 'd'
        c.tail = 'd1'
        e = SubElement(c, 'e')
        e.text = 'e'
        e.tail = 'e1'

        self.assertEqual(
            [a, b, d, c, e],
            list(a.getiterator()))
        #self.assertEqual(
        #    [d],
        #    list(d.getiterator()))

    def test_getiterator_filter_with_text(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        a.text = 'a'
        b = SubElement(a, 'b')
        b.text = 'b'
        b.tail = 'b1'
        c = SubElement(a, 'c')
        c.text = 'c'
        c.tail = 'c1'
        d = SubElement(b, 'd')
        c.text = 'd'
        c.tail = 'd1'
        e = SubElement(c, 'e')
        e.text = 'e'
        e.tail = 'e1'

        self.assertEqual(
            [a],
            list(a.getiterator('a')))
        a2 = SubElement(e, 'a')
        self.assertEqual(
            [a, a2],
            list(a.getiterator('a')))   
        self.assertEqual(
            [a2],
            list(e.getiterator('a')))

    def test_getslice(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')

        self.assertEqual(
            [b, c],
            a[0:2])
        self.assertEqual(
            [b, c, d],
            a[:])
        self.assertEqual(
            [b, c, d],
            a[:10])
        self.assertEqual(
            [b],
            a[0:1])
        self.assertEqual(
            [],
            a[10:12])

    def test_getslice_negative(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')

        self.assertEqual(
            [d],
            a[-1:])
        self.assertEqual(
            [c, d],
            a[-2:])
        self.assertEqual(
            [c],
            a[-2:-1])
        self.assertEqual(
            [b, c],
            a[-3:-1])
        self.assertEqual(
            [b, c],
            a[-3:2])

    def test_getslice_step(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')
        e = SubElement(a, 'e')

        self.assertEqual(
            [e,d,c,b],
            a[::-1])
        self.assertEqual(
            [b,d],
            a[::2])
        self.assertEqual(
            [e,c],
            a[::-2])
        self.assertEqual(
            [d,c],
            a[-2:0:-1])
        self.assertEqual(
            [e],
            a[:1:-2])

    def test_getslice_text(self):
        ElementTree = self.etree.ElementTree
        
        f = BytesIO('<a><b>B</b>B1<c>C</c>C1</a>')
        doc = ElementTree(file=f)
        a = doc.getroot()
        b = a[0]
        c = a[1]
        self.assertEqual(
            [b, c],
            a[:])
        self.assertEqual(
            [b],
            a[0:1])
        self.assertEqual(
            [c],
            a[1:])

    def test_comment_getitem_getslice(self):
        Element = self.etree.Element
        Comment = self.etree.Comment
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        foo = Comment('foo')
        a.append(foo)
        c = SubElement(a, 'c')
        self.assertEqual(
            [b, foo, c],
            a[:])
        self.assertEqual(
            foo,
            a[1])
        a[1] = new = Element('new')
        self.assertEqual(
            new,
            a[1])
        self.assertXML(
            _bytes('<a><b></b><new></new><c></c></a>'),
            a)
        
    def test_delslice(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')
        e = SubElement(a, 'e')

        del a[1:3]
        self.assertEqual(
            [b, e],
            list(a))

    def test_delslice_negative1(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')
        e = SubElement(a, 'e')

        del a[1:-1]
        self.assertEqual(
            [b, e],
            list(a))

    def test_delslice_negative2(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')
        e = SubElement(a, 'e')

        del a[-3:-1]
        self.assertEqual(
            [b, e],
            list(a))

    def test_delslice_step(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')
        e = SubElement(a, 'e')

        del a[1::2]
        self.assertEqual(
            [b, d],
            list(a))

    def test_delslice_step_negative(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')
        e = SubElement(a, 'e')

        del a[::-1]
        self.assertEqual(
            [],
            list(a))

    def test_delslice_step_negative2(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')
        e = SubElement(a, 'e')

        del a[::-2]
        self.assertEqual(
            [b, d],
            list(a))

    def test_delslice_child_tail(self):
        ElementTree = self.etree.ElementTree
        f = BytesIO('<a><b></b>B2<c></c>C2<d></d>D2<e></e>E2</a>')
        doc = ElementTree(file=f)
        a = doc.getroot()
        del a[1:3]
        self.assertXML(
            _bytes('<a><b></b>B2<e></e>E2</a>'),
            a)

    def test_delslice_tail(self):
        XML = self.etree.XML
        a = XML(_bytes('<a><b></b>B2<c></c>C2</a>'))
        b, c = a

        del a[:]

        self.assertEqual("B2", b.tail)
        self.assertEqual("C2", c.tail)

    def test_delslice_memory(self):
        # this could trigger a crash
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(b, 'c')
        del b # no more reference to b
        del a[:]
        self.assertEqual('c', c.tag)
        
    def test_setslice(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')

        e = Element('e')
        f = Element('f')
        g = Element('g')

        s = [e, f, g]
        a[1:2] = s
        self.assertEqual(
            [b, e, f, g, d],
            list(a))

    def test_setslice_all(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')

        e = Element('e')
        f = Element('f')
        g = Element('g')

        s = [e, f, g]
        a[:] = s
        self.assertEqual(
            [e, f, g],
            list(a))

    def test_setslice_all_empty(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')

        e = Element('e')
        f = Element('f')
        g = Element('g')

        s = [e, f, g]
        a[:] = s
        self.assertEqual(
            [e, f, g],
            list(a))

    def test_setslice_all_replace(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')

        s = [b, c, d]
        a[:] = s
        self.assertEqual(
            [b, c, d],
            list(a))
        
    def test_setslice_all_replace_reversed(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')

        s = [d, c, b]
        a[:] = s
        self.assertEqual(
            [d, c, b],
            list(a))

    def test_setslice_all_replace_reversed_ns1(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('{ns}a')
        b = SubElement(a, '{ns}b', {'{ns1}a1': 'test'})
        c = SubElement(a, '{ns}c', {'{ns2}a2': 'test'})
        d = SubElement(a, '{ns}d', {'{ns3}a3': 'test'})

        s = [d, c, b]
        a[:] = s
        self.assertEqual(
            [d, c, b],
            list(a))
        self.assertEqual(
            ['{ns}d', '{ns}c', '{ns}b'],
            [ child.tag for child in a ])

        self.assertEqual(
            [['{ns3}a3'], ['{ns2}a2'], ['{ns1}a1']],
            [ list(child.attrib.keys()) for child in a ])

    def test_setslice_all_replace_reversed_ns2(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('{ns}a')
        b = SubElement(a, '{ns1}b', {'{ns}a1': 'test'})
        c = SubElement(a, '{ns2}c', {'{ns}a2': 'test'})
        d = SubElement(a, '{ns3}d', {'{ns}a3': 'test'})

        s = [d, c, b]
        a[:] = s
        self.assertEqual(
            [d, c, b],
            list(a))
        self.assertEqual(
            ['{ns3}d', '{ns2}c', '{ns1}b'],
            [ child.tag for child in a ])

        self.assertEqual(
            [['{ns}a3'], ['{ns}a2'], ['{ns}a1']],
            [ list(child.attrib.keys()) for child in a ])

    def test_setslice_end(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')

        e = Element('e')
        f = Element('f')
        g = Element('g')
        h = Element('h')

        s = [e, f]
        a[99:] = s
        self.assertEqual(
            [b, c, e, f],
            list(a))

        s = [g, h]
        a[:0] = s
        self.assertEqual(
            [g, h, b, c, e, f],
            list(a))

    def test_setslice_end_exact(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')

        e = Element('e')
        f = Element('f')
        g = Element('g')

        s = [e, f, g]
        a[3:] = s
        self.assertEqual(
            [b, c, d, e, f, g],
            list(a))

    def test_setslice_single(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')

        e = Element('e')
        f = Element('f')

        s = [e]
        a[0:1] = s
        self.assertEqual(
            [e, c],
            list(a))

        s = [f]
        a[1:2] = s
        self.assertEqual(
            [e, f],
            list(a))

    def test_setslice_tail(self):
        ElementTree = self.etree.ElementTree
        Element = self.etree.Element
        f = BytesIO('<a><b></b>B2<c></c>C2<d></d>D2<e></e>E2</a>')
        doc = ElementTree(file=f)
        a = doc.getroot()
        x = Element('x')
        y = Element('y')
        z = Element('z')
        x.tail = 'X2'
        y.tail = 'Y2'
        z.tail = 'Z2'
        a[1:3] = [x, y, z]
        self.assertXML(
            _bytes('<a><b></b>B2<x></x>X2<y></y>Y2<z></z>Z2<e></e>E2</a>'),
            a)

    def test_setslice_negative(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')

        x = Element('x')
        y = Element('y')

        a[1:-1] = [x, y]
        self.assertEqual(
            [b, x, y, d],
            list(a))

    def test_setslice_negative2(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')

        x = Element('x')
        y = Element('y')

        a[1:-2] = [x, y]
        self.assertEqual(
            [b, x, y, c, d],
            list(a))

    def test_setslice_empty(self):
        Element = self.etree.Element

        a = Element('a')

        b = Element('b')
        c = Element('c')

        a[:] = [b, c]
        self.assertEqual(
            [b, c],
            list(a))

    def test_tail_elementtree_root(self):
        Element = self.etree.Element
        ElementTree = self.etree.ElementTree

        a = Element('a')
        a.tail = 'A2'
        t = ElementTree(element=a)
        self.assertEqual('A2',
                          a.tail)

    def test_elementtree_getiterator(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        ElementTree = self.etree.ElementTree
        
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        e = SubElement(c, 'e')
        t = ElementTree(element=a)
        
        self.assertEqual(
            [a, b, d, c, e],
            list(t.getiterator()))

    def test_elementtree_getiterator_filter(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        ElementTree = self.etree.ElementTree
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        e = SubElement(c, 'e')
        t = ElementTree(element=a)
        
        self.assertEqual(
            [a],
            list(t.getiterator('a')))
        a2 = SubElement(e, 'a')
        self.assertEqual(
            [a, a2],
            list(t.getiterator('a')))

    def test_ns_access(self):
        ElementTree = self.etree.ElementTree
        ns = 'http://xml.infrae.com/1'
        f = BytesIO('<x:a xmlns:x="%s"><x:b></x:b></x:a>' % ns)
        t = ElementTree(file=f)
        a = t.getroot()
        self.assertEqual('{%s}a' % ns,
                          a.tag)
        self.assertEqual('{%s}b' % ns,
                          a[0].tag)

    def test_ns_access2(self):
        ElementTree = self.etree.ElementTree
        ns = 'http://xml.infrae.com/1'
        ns2 = 'http://xml.infrae.com/2'
        f = BytesIO('<x:a xmlns:x="%s" xmlns:y="%s"><x:b></x:b><y:b></y:b></x:a>' % (ns, ns2))
        t = ElementTree(file=f)
        a = t.getroot()
        self.assertEqual('{%s}a' % ns,
                          a.tag)
        self.assertEqual('{%s}b' % ns,
                          a[0].tag)
        self.assertEqual('{%s}b' % ns2,
                          a[1].tag)

    def test_ns_setting(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        ns = 'http://xml.infrae.com/1'
        ns2 = 'http://xml.infrae.com/2'
        a = Element('{%s}a' % ns)
        b = SubElement(a, '{%s}b' % ns2)
        c = SubElement(a, '{%s}c' % ns)
        self.assertEqual('{%s}a' % ns,
                          a.tag)
        self.assertEqual('{%s}b' % ns2,
                          b.tag)
        self.assertEqual('{%s}c' % ns,
                          c.tag)
        self.assertEqual('{%s}a' % ns,
                          a.tag)
        self.assertEqual('{%s}b' % ns2,
                          b.tag)
        self.assertEqual('{%s}c' % ns,
                          c.tag)

    def test_ns_tag_parse(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        ElementTree = self.etree.ElementTree

        ns = 'http://xml.infrae.com/1'
        ns2 = 'http://xml.infrae.com/2'
        f = BytesIO('<a xmlns="%s" xmlns:x="%s"><x:b></x:b><b></b></a>' % (ns, ns2))
        t = ElementTree(file=f)

        a = t.getroot()
        self.assertEqual('{%s}a' % ns,
                          a.tag)
        self.assertEqual('{%s}b' % ns2,
                          a[0].tag)
        self.assertEqual('{%s}b' % ns,
                          a[1].tag)

    def test_ns_attr(self):
        Element = self.etree.Element
        ns = 'http://xml.infrae.com/1'
        ns2 = 'http://xml.infrae.com/2'
        a = Element('a')
        a.set('{%s}foo' % ns, 'Foo')
        a.set('{%s}bar' % ns2, 'Bar')
        self.assertEqual(
            'Foo',
            a.get('{%s}foo' % ns))
        self.assertEqual(
            'Bar',
            a.get('{%s}bar' % ns2))
        try:
            self.assertXML(
                _bytes('<a xmlns:ns0="%s" xmlns:ns1="%s" ns0:foo="Foo" ns1:bar="Bar"></a>' % (ns, ns2)),
                a)
        except AssertionError:
            self.assertXML(
                _bytes('<a xmlns:ns0="%s" xmlns:ns1="%s" ns1:foo="Foo" ns0:bar="Bar"></a>' % (ns2, ns)),
                a)

    def test_ns_move(self):
        Element = self.etree.Element
        one = self.etree.fromstring(
            _bytes('<foo><bar xmlns:ns="http://a.b.c"><ns:baz/></bar></foo>'))
        baz = one[0][0]

        two = Element('root')
        two.append(baz)
        # removing the originating document could cause a crash/error before
        # as namespace is not moved along with it
        del one, baz
        self.assertEqual('{http://a.b.c}baz', two[0].tag)

    def test_ns_decl_tostring(self):
        tostring = self.etree.tostring
        root = self.etree.XML(
            _bytes('<foo><bar xmlns:ns="http://a.b.c"><ns:baz/></bar></foo>'))
        baz = root[0][0]

        nsdecl = re.findall(_bytes("xmlns(?::[a-z0-9]+)?=[\"']([^\"']+)[\"']"),
                            tostring(baz))
        self.assertEqual([_bytes("http://a.b.c")], nsdecl)

    def test_ns_decl_tostring_default(self):
        tostring = self.etree.tostring
        root = self.etree.XML(
            _bytes('<foo><bar xmlns="http://a.b.c"><baz/></bar></foo>'))
        baz = root[0][0]

        nsdecl = re.findall(_bytes("xmlns(?::[a-z0-9]+)?=[\"']([^\"']+)[\"']"),
                            tostring(baz))
        self.assertEqual([_bytes("http://a.b.c")], nsdecl)
        
    def test_ns_decl_tostring_root(self):
        tostring = self.etree.tostring
        root = self.etree.XML(
            _bytes('<foo xmlns:ns="http://a.b.c"><bar><ns:baz/></bar></foo>'))
        baz = root[0][0]

        nsdecl = re.findall(_bytes("xmlns(?::[a-z0-9]+)?=[\"']([^\"']+)[\"']"),
                            tostring(baz))

        self.assertEqual([_bytes("http://a.b.c")], nsdecl)
        
    def test_ns_decl_tostring_element(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        root = Element("foo")
        bar = SubElement(root, "{http://a.b.c}bar")
        baz = SubElement(bar, "{http://a.b.c}baz")

        nsdecl = re.findall(_bytes("xmlns(?::[a-z0-9]+)?=[\"']([^\"']+)[\"']"),
                            self.etree.tostring(baz))

        self.assertEqual([_bytes("http://a.b.c")], nsdecl)

    def test_attribute_xmlns_move(self):
        Element = self.etree.Element

        root = Element('element')

        subelement = Element('subelement',
                             {"{http://www.w3.org/XML/1998/namespace}id": "foo"})
        self.assertEqual(1, len(subelement.attrib))
        self.assertEqual(
            "foo",
            subelement.get("{http://www.w3.org/XML/1998/namespace}id"))

        root.append(subelement)
        self.assertEqual(1, len(subelement.attrib))
        self.assertEqual(
            list({"{http://www.w3.org/XML/1998/namespace}id" : "foo"}.items()),
            list(subelement.attrib.items()))
        self.assertEqual(
            "foo",
            subelement.get("{http://www.w3.org/XML/1998/namespace}id"))

    def test_namespaces_after_serialize(self):
        parse = self.etree.parse
        tostring = self.etree.tostring

        ns_href = "http://a.b.c"
        one = parse(
            BytesIO('<foo><bar xmlns:ns="%s"><ns:baz/></bar></foo>' % ns_href))
        baz = one.getroot()[0][0]

        parsed = parse(BytesIO( tostring(baz) )).getroot()
        self.assertEqual('{%s}baz' % ns_href, parsed.tag)

    def test_attribute_namespace_roundtrip(self):
        fromstring = self.etree.fromstring
        tostring = self.etree.tostring

        ns_href = "http://a.b.c"
        xml = _bytes('<root xmlns="%s" xmlns:x="%s"><el x:a="test" /></root>' % (
                ns_href,ns_href))
        root = fromstring(xml)
        self.assertEqual('test', root[0].get('{%s}a' % ns_href))

        xml2 = tostring(root)
        self.assertTrue(_bytes(':a=') in xml2, xml2)

        root2 = fromstring(xml2)
        self.assertEqual('test', root2[0].get('{%s}a' % ns_href))

    def test_attribute_namespace_roundtrip_replaced(self):
        fromstring = self.etree.fromstring
        tostring = self.etree.tostring

        ns_href = "http://a.b.c"
        xml = _bytes('<root xmlns="%s" xmlns:x="%s"><el x:a="test" /></root>' % (
                ns_href,ns_href))
        root = fromstring(xml)
        self.assertEqual('test', root[0].get('{%s}a' % ns_href))

        root[0].set('{%s}a' % ns_href, 'TEST')

        xml2 = tostring(root)
        self.assertTrue(_bytes(':a=') in xml2, xml2)

        root2 = fromstring(xml2)
        self.assertEqual('TEST', root2[0].get('{%s}a' % ns_href))

    required_versions_ET['test_register_namespace'] = (1,3)
    def test_register_namespace(self):
        # ET 1.3+
        Element = self.etree.Element
        prefix = 'TESTPREFIX'
        namespace = 'http://seriously.unknown/namespace/URI'

        el = Element('{%s}test' % namespace)
        self.assertEqual(_bytes('<ns0:test xmlns:ns0="%s"></ns0:test>' % namespace),
            self._writeElement(el))

        self.etree.register_namespace(prefix, namespace)
        el = Element('{%s}test' % namespace)
        self.assertEqual(_bytes('<%s:test xmlns:%s="%s"></%s:test>' % (
            prefix, prefix, namespace, prefix)),
            self._writeElement(el))

        self.assertRaises(ValueError, self.etree.register_namespace, 'ns25', namespace)

    def test_tostring(self):
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        
        self.assertEqual(_bytes('<a><b></b><c></c></a>'),
                          canonicalize(tostring(a)))

    def test_tostring_element(self):
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(c, 'd')
        self.assertEqual(_bytes('<b></b>'),
                          canonicalize(tostring(b)))
        self.assertEqual(_bytes('<c><d></d></c>'),
                          canonicalize(tostring(c)))
        
    def test_tostring_element_tail(self):
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(c, 'd')
        b.tail = 'Foo'

        self.assertTrue(tostring(b) == _bytes('<b/>Foo') or
                     tostring(b) == _bytes('<b />Foo'))

    required_versions_ET['test_tostring_method_html'] = (1,3)
    def test_tostring_method_html(self):
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        html = Element('html')
        body = SubElement(html, 'body')
        p = SubElement(body, 'p')
        p.text = "html"
        SubElement(p, 'br').tail = "test"

        self.assertEqual(_bytes('<html><body><p>html<br>test</p></body></html>'),
                          tostring(html, method="html"))

    required_versions_ET['test_tostring_method_text'] = (1,3)
    def test_tostring_method_text(self):
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        a.text = "A"
        a.tail = "tail"
        b = SubElement(a, 'b')
        b.text = "B"
        b.tail = "TAIL"
        c = SubElement(a, 'c')
        c.text = "C"
        
        self.assertEqual(_bytes('ABTAILCtail'),
                          tostring(a, method="text"))

    def test_iterparse(self):
        iterparse = self.etree.iterparse
        f = BytesIO('<a><b></b><c/></a>')

        iterator = iterparse(f)
        self.assertEqual(None,
                          iterator.root)
        events = list(iterator)
        root = iterator.root
        self.assertEqual(
            [('end', root[0]), ('end', root[1]), ('end', root)],
            events)

    def test_iterparse_file(self):
        iterparse = self.etree.iterparse
        iterator = iterparse(fileInTestDir("test.xml"))
        self.assertEqual(None,
                          iterator.root)
        events = list(iterator)
        root = iterator.root
        self.assertEqual(
            [('end', root[0]), ('end', root)],
            events)

    def test_iterparse_start(self):
        iterparse = self.etree.iterparse
        f = BytesIO('<a><b></b><c/></a>')

        iterator = iterparse(f, events=('start',))
        events = list(iterator)
        root = iterator.root
        self.assertEqual(
            [('start', root), ('start', root[0]), ('start', root[1])],
            events)

    def test_iterparse_start_end(self):
        iterparse = self.etree.iterparse
        f = BytesIO('<a><b></b><c/></a>')

        iterator = iterparse(f, events=('start','end'))
        events = list(iterator)
        root = iterator.root
        self.assertEqual(
            [('start', root), ('start', root[0]), ('end', root[0]),
             ('start', root[1]), ('end', root[1]), ('end', root)],
            events)

    def test_iterparse_clear(self):
        iterparse = self.etree.iterparse
        f = BytesIO('<a><b></b><c/></a>')

        iterator = iterparse(f)
        for event, elem in iterator:
            elem.clear()

        root = iterator.root
        self.assertEqual(0,
                          len(root))

    def test_iterparse_large(self):
        iterparse = self.etree.iterparse
        CHILD_COUNT = 12345
        f = BytesIO('<a>%s</a>' % ('<b>test</b>'*CHILD_COUNT))

        i = 0
        for key in iterparse(f):
            event, element = key
            i += 1
        self.assertEqual(i, CHILD_COUNT + 1)

    def test_iterparse_attrib_ns(self):
        iterparse = self.etree.iterparse
        f = BytesIO('<a xmlns="http://ns1/"><b><c xmlns="http://ns2/"/></b></a>')

        attr_name = '{http://testns/}bla'
        events = []
        iterator = iterparse(f, events=('start','end','start-ns','end-ns'))
        for event, elem in iterator:
            events.append(event)
            if event == 'start':
                if elem.tag != '{http://ns1/}a':
                    elem.set(attr_name, 'value')

        self.assertEqual(
            ['start-ns', 'start', 'start', 'start-ns', 'start',
             'end', 'end-ns', 'end', 'end', 'end-ns'],
            events)

        root = iterator.root
        self.assertEqual(
            None,
            root.get(attr_name))
        self.assertEqual(
            'value',
            root[0].get(attr_name))

    def test_iterparse_getiterator(self):
        iterparse = self.etree.iterparse
        f = BytesIO('<a><b><d/></b><c/></a>')

        counts = []
        for event, elem in iterparse(f):
            counts.append(len(list(elem.getiterator())))
        self.assertEqual(
            [1,2,1,4],
            counts)

    def test_iterparse_move_elements(self):
        iterparse = self.etree.iterparse
        f = BytesIO('<a><b><d/></b><c/></a>')

        for event, node in etree.iterparse(f): pass

        root = etree.Element('new_root', {})
        root[:] = node[:]

        self.assertEqual(
            ['b', 'c'],
            [ el.tag for el in root ])

    def test_iterparse_cdata(self):
        tostring = self.etree.tostring
        f = BytesIO('<root><![CDATA[test]]></root>')
        context = self.etree.iterparse(f)
        content = [ el.text for event,el in context ]

        self.assertEqual(['test'], content)
        self.assertEqual(_bytes('<root>test</root>'),
                          tostring(context.root))

    def test_parse_file(self):
        parse = self.etree.parse
        # from file
        tree = parse(fileInTestDir('test.xml'))
        self.assertXML(
            _bytes('<a><b></b></a>'),
            tree.getroot())

    def test_parse_file_nonexistent(self):
        parse = self.etree.parse
        self.assertRaises(IOError, parse, fileInTestDir('notthere.xml'))  

    def test_parse_error_none(self):
        parse = self.etree.parse
        self.assertRaises(TypeError, parse, None)

    required_versions_ET['test_parse_error'] = (1,3)
    def test_parse_error(self):
        # ET < 1.3 raises ExpatError
        parse = self.etree.parse
        f = BytesIO('<a><b></c></b></a>')
        self.assertRaises(SyntaxError, parse, f)
        f.close()

    required_versions_ET['test_parse_error_from_file'] = (1,3)
    def test_parse_error_from_file(self):
        parse = self.etree.parse
        # from file
        f = open(fileInTestDir('test_broken.xml'), 'rb')
        self.assertRaises(SyntaxError, parse, f)
        f.close()

    def test_parse_file_object(self):
        parse = self.etree.parse
        # from file object
        f = open(fileInTestDir('test.xml'), 'rb')
        tree = parse(f)
        f.close()
        self.assertXML(
            _bytes('<a><b></b></a>'),
            tree.getroot())

    def test_parse_stringio(self):
        parse = self.etree.parse
        f = BytesIO('<a><b></b></a>')
        tree = parse(f)
        f.close()
        self.assertXML(
            _bytes('<a><b></b></a>'),
            tree.getroot()
           )

    def test_parse_cdata(self):
        tostring = self.etree.tostring
        root = self.etree.XML(_bytes('<root><![CDATA[test]]></root>'))

        self.assertEqual('test', root.text)
        self.assertEqual(_bytes('<root>test</root>'),
                          tostring(root))

    def test_parse_with_encoding(self):
        # this can fail in libxml2 <= 2.6.22
        parse = self.etree.parse
        tree = parse(BytesIO('<?xml version="1.0" encoding="ascii"?><html/>'))
        self.assertXML(_bytes('<html></html>'),
                       tree.getroot())

    def test_encoding(self):
        Element = self.etree.Element

        a = Element('a')
        a.text = _str('Søk på nettet')
        self.assertXML(
            _str('<a>Søk på nettet</a>').encode('UTF-8'),
            a, 'utf-8')

    def test_encoding_exact(self):
        ElementTree = self.etree.ElementTree
        Element = self.etree.Element

        a = Element('a')
        a.text = _str('Søk på nettet')
        
        f = BytesIO()
        tree = ElementTree(element=a)
        tree.write(f, encoding='utf-8')
        self.assertEqual(_str('<a>Søk på nettet</a>').encode('UTF-8'),
                          f.getvalue().replace(_bytes('\n'),_bytes('')))

    def test_parse_file_encoding(self):
        parse = self.etree.parse
        # from file
        tree = parse(fileInTestDir('test-string.xml'))
        self.assertXML(
            _str('<a>Søk på nettet</a>').encode('UTF-8'),
            tree.getroot(), 'UTF-8')

    def test_parse_file_object_encoding(self):
        parse = self.etree.parse
        # from file object
        f = open(fileInTestDir('test-string.xml'), 'rb')
        tree = parse(f)
        f.close()
        self.assertXML(
            _str('<a>Søk på nettet</a>').encode('UTF-8'),
            tree.getroot(), 'UTF-8')

    def test_encoding_8bit_latin1(self):
        ElementTree = self.etree.ElementTree
        Element = self.etree.Element

        a = Element('a')
        a.text = _str('Søk på nettet')

        f = BytesIO()
        tree = ElementTree(element=a)
        tree.write(f, encoding='iso-8859-1')
        result = f.getvalue()
        declaration = _bytes("<?xml version=\'1.0\' encoding=\'iso-8859-1\'?>")
        self.assertEncodingDeclaration(result, _bytes('iso-8859-1'))
        result = result.split(_bytes('?>'), 1)[-1].replace(_bytes('\n'),_bytes(''))
        self.assertEqual(_str('<a>Søk på nettet</a>').encode('iso-8859-1'),
                          result)

    required_versions_ET['test_parse_encoding_8bit_explicit'] = (1,3)
    def test_parse_encoding_8bit_explicit(self):
        XMLParser = self.XMLParser

        text = _str('Søk på nettet')
        xml_latin1 = (_str('<a>%s</a>') % text).encode('iso-8859-1')

        self.assertRaises(self.etree.ParseError,
                          self.etree.parse,
                          BytesIO(xml_latin1))

        tree = self.etree.parse(BytesIO(xml_latin1),
                                XMLParser(encoding="iso-8859-1"))
        a = tree.getroot()
        self.assertEqual(a.text, text)

    required_versions_ET['test_parse_encoding_8bit_override'] = (1,3)
    def test_parse_encoding_8bit_override(self):
        XMLParser = self.XMLParser

        text = _str('Søk på nettet')
        wrong_declaration = _str("<?xml version='1.0' encoding='UTF-8'?>")
        xml_latin1 = (_str('%s<a>%s</a>') % (wrong_declaration, text)
                      ).encode('iso-8859-1')

        self.assertRaises(self.etree.ParseError,
                          self.etree.parse,
                          BytesIO(xml_latin1))

        tree = self.etree.parse(BytesIO(xml_latin1),
                                XMLParser(encoding="iso-8859-1"))
        a = tree.getroot()
        self.assertEqual(a.text, text)

    def _test_wrong_unicode_encoding(self):
        # raise error on wrong encoding declaration in unicode strings
        XML = self.etree.XML
        test_utf = (_str('<?xml version="1.0" encoding="iso-8859-1"?>') +
                    _str('<a>Søk på nettet</a>'))
        self.assertRaises(SyntaxError, XML, test_utf)

    def test_encoding_write_default_encoding(self):
        ElementTree = self.etree.ElementTree
        Element = self.etree.Element

        a = Element('a')
        a.text = _str('Søk på nettet')
        
        f = BytesIO()
        tree = ElementTree(element=a)
        tree.write(f)
        data = f.getvalue().replace(_bytes('\n'),_bytes(''))
        self.assertEqual(
            _str('<a>Søk på nettet</a>').encode('ASCII', 'xmlcharrefreplace'),
            data)

    def test_encoding_tostring(self):
        Element = self.etree.Element
        tostring = self.etree.tostring

        a = Element('a')
        a.text = _str('Søk på nettet')
        self.assertEqual(_str('<a>Søk på nettet</a>').encode('UTF-8'),
                         tostring(a, encoding='utf-8'))

    def test_encoding_tostring_unknown(self):
        Element = self.etree.Element
        tostring = self.etree.tostring
        
        a = Element('a')
        a.text = _str('Søk på nettet')
        self.assertRaises(LookupError, tostring, a,
                          encoding='Invalid Encoding')

    def test_encoding_tostring_sub(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        tostring = self.etree.tostring

        a = Element('a')
        b = SubElement(a, 'b')
        b.text = _str('Søk på nettet')
        self.assertEqual(_str('<b>Søk på nettet</b>').encode('UTF-8'),
                         tostring(b, encoding='utf-8'))

    def test_encoding_tostring_sub_tail(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        tostring = self.etree.tostring

        a = Element('a')
        b = SubElement(a, 'b')
        b.text = _str('Søk på nettet')
        b.tail = _str('Søk')
        self.assertEqual(_str('<b>Søk på nettet</b>Søk').encode('UTF-8'),
                         tostring(b, encoding='utf-8'))
        
    def test_encoding_tostring_default_encoding(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        tostring = self.etree.tostring

        a = Element('a')
        a.text = _str('Søk på nettet')

        expected = _bytes('<a>S&#248;k p&#229; nettet</a>')
        self.assertEqual(
            expected,
            tostring(a))

    def test_encoding_sub_tostring_default_encoding(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        tostring = self.etree.tostring

        a = Element('a')
        b = SubElement(a, 'b')
        b.text = _str('Søk på nettet')

        expected = _bytes('<b>S&#248;k p&#229; nettet</b>')
        self.assertEqual(
            expected,
            tostring(b))

    def test_encoding_8bit_xml(self):
        utext = _str('Søk på nettet')
        uxml = _str('<p>%s</p>') % utext
        prologue = _bytes('<?xml version="1.0" encoding="iso-8859-1" ?>')
        isoxml = prologue + uxml.encode('iso-8859-1')
        tree = self.etree.XML(isoxml)
        self.assertEqual(utext, tree.text)

    def test_encoding_utf8_bom(self):
        utext = _str('Søk på nettet')
        uxml = (_str('<?xml version="1.0" encoding="UTF-8"?>') +
                _str('<p>%s</p>') % utext)
        bom = _bytes('\\xEF\\xBB\\xBF').decode("unicode_escape").encode("latin1")
        xml = bom + uxml.encode("utf-8")
        tree = etree.XML(xml)
        self.assertEqual(utext, tree.text)

    def test_encoding_8bit_parse_stringio(self):
        utext = _str('Søk på nettet')
        uxml = _str('<p>%s</p>') % utext
        prologue = _bytes('<?xml version="1.0" encoding="iso-8859-1" ?>')
        isoxml = prologue + uxml.encode('iso-8859-1')
        el = self.etree.parse(BytesIO(isoxml)).getroot()
        self.assertEqual(utext, el.text)

    def test_deepcopy_elementtree(self):
        Element = self.etree.Element
        ElementTree = self.etree.ElementTree

        a = Element('a')
        a.text = "Foo"
        atree = ElementTree(a)

        btree = copy.deepcopy(atree)
        self.assertEqual("Foo", atree.getroot().text)
        self.assertEqual("Foo", btree.getroot().text)
        self.assertFalse(btree is atree)
        self.assertFalse(btree.getroot() is atree.getroot())

    def test_deepcopy(self):
        Element = self.etree.Element
        
        a = Element('a')
        a.text = 'Foo'

        b = copy.deepcopy(a)
        self.assertEqual('Foo', b.text)
        
        b.text = 'Bar'
        self.assertEqual('Bar', b.text)
        self.assertEqual('Foo', a.text)

        del a
        self.assertEqual('Bar', b.text)

    def test_deepcopy_tail(self):
        Element = self.etree.Element
        
        a = Element('a')
        a.tail = 'Foo'

        b = copy.deepcopy(a)
        self.assertEqual('Foo', b.tail)
        
        b.tail = 'Bar'
        self.assertEqual('Bar', b.tail)
        self.assertEqual('Foo', a.tail)

        del a
        self.assertEqual('Bar', b.tail)

    def test_deepcopy_subelement(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        root = Element('root')
        a = SubElement(root, 'a')
        a.text = 'FooText'
        a.tail = 'FooTail'

        b = copy.deepcopy(a)
        self.assertEqual('FooText', b.text)
        self.assertEqual('FooTail', b.tail)
        
        b.text = 'BarText'
        b.tail = 'BarTail'
        self.assertEqual('BarTail', b.tail)
        self.assertEqual('FooTail', a.tail)
        self.assertEqual('BarText', b.text)
        self.assertEqual('FooText', a.text)

        del a
        self.assertEqual('BarTail', b.tail)
        self.assertEqual('BarText', b.text)

    def test_deepcopy_namespaces(self):
        root = self.etree.XML(_bytes('''<doc xmlns="dns" xmlns:t="tns">
        <parent><node t:foo="bar" /></parent>
        </doc>'''))
        self.assertEqual(
            root[0][0].get('{tns}foo'),
            copy.deepcopy(root[0])[0].get('{tns}foo') )
        self.assertEqual(
            root[0][0].get('{tns}foo'),
            copy.deepcopy(root[0][0]).get('{tns}foo') )
        
    def test_deepcopy_append(self):
        # previously caused a crash
        Element = self.etree.Element
        tostring = self.etree.tostring
        
        a = Element('a')
        b = copy.deepcopy(a)
        a.append( Element('C') )
        b.append( Element('X') )

        self.assertEqual(_bytes('<a><C/></a>'),
                          tostring(a).replace(_bytes(' '), _bytes('')))
        self.assertEqual(_bytes('<a><X/></a>'),
                          tostring(b).replace(_bytes(' '), _bytes('')))

    def test_deepcopy_comment(self):
        # previously caused a crash
        # not supported by ET < 1.3!
        Comment = self.etree.Comment
        
        a = Comment("ONE")
        b = copy.deepcopy(a)
        b.text = "ANOTHER"

        self.assertEqual('ONE',     a.text)
        self.assertEqual('ANOTHER', b.text)

    def test_shallowcopy(self):
        Element = self.etree.Element
        
        a = Element('a')
        a.text = 'Foo'

        b = copy.copy(a)
        self.assertEqual('Foo', b.text)
        
        b.text = 'Bar'
        self.assertEqual('Bar', b.text)
        self.assertEqual('Foo', a.text)
        # XXX ElementTree will share nodes, but lxml.etree won't..

    def test_shallowcopy_elementtree(self):
        Element = self.etree.Element
        ElementTree = self.etree.ElementTree
        
        a = Element('a')
        a.text = 'Foo'
        atree = ElementTree(a)

        btree = copy.copy(atree)
        self.assertFalse(btree is atree)
        self.assertTrue(btree.getroot() is atree.getroot())
        self.assertEqual('Foo', atree.getroot().text)

    def _test_element_boolean(self):
        # deprecated as of ET 1.3/lxml 2.0
        etree = self.etree
        e = etree.Element('foo')
        self.assertEqual(False, bool(e))
        etree.SubElement(e, 'bar')
        self.assertEqual(True, bool(e))
        e = etree.Element('foo')
        e.text = 'hey'
        self.assertEqual(False, bool(e))
        e = etree.Element('foo')
        e.tail = 'bar'
        self.assertEqual(False, bool(e))
        e = etree.Element('foo')
        e.set('bar', 'Bar')
        self.assertEqual(False, bool(e))

    def test_multiple_elementrees(self):
        etree = self.etree

        a = etree.Element('a')
        b = etree.SubElement(a, 'b')

        t = etree.ElementTree(a)
        self.assertEqual(self._rootstring(t), _bytes('<a><b/></a>'))

        t1 = etree.ElementTree(a)
        self.assertEqual(self._rootstring(t1), _bytes('<a><b/></a>'))
        self.assertEqual(self._rootstring(t),  _bytes('<a><b/></a>'))

        t2 = etree.ElementTree(b)
        self.assertEqual(self._rootstring(t2), _bytes('<b/>'))
        self.assertEqual(self._rootstring(t1), _bytes('<a><b/></a>'))
        self.assertEqual(self._rootstring(t),  _bytes('<a><b/></a>'))

    def test_qname(self):
        etree = self.etree
        qname = etree.QName('myns', 'a')
        a1 = etree.Element(qname)
        a2 = etree.SubElement(a1, qname)
        self.assertEqual(a1.tag, "{myns}a")
        self.assertEqual(a2.tag, "{myns}a")

    def test_qname_cmp(self):
        etree = self.etree
        qname1 = etree.QName('myns', 'a')
        qname2 = etree.QName('myns', 'a')
        self.assertEqual(qname1, "{myns}a")
        self.assertEqual("{myns}a", qname2)
        self.assertEqual(qname1, qname1)
        self.assertEqual(qname1, qname2)

    def test_qname_attribute_getset(self):
        etree = self.etree
        qname = etree.QName('myns', 'a')

        a = etree.Element(qname)
        a.set(qname, "value")

        self.assertEqual(a.get(qname), "value")
        self.assertEqual(a.get("{myns}a"), "value")

    def test_qname_attrib(self):
        etree = self.etree
        qname = etree.QName('myns', 'a')

        a = etree.Element(qname)
        a.attrib[qname] = "value"

        self.assertEqual(a.attrib[qname], "value")
        self.assertEqual(a.attrib.get(qname), "value")

        self.assertEqual(a.attrib["{myns}a"], "value")
        self.assertEqual(a.attrib.get("{myns}a"), "value")

    def test_qname_attribute_resolve(self):
        etree = self.etree
        qname = etree.QName('http://myns', 'a')
        a = etree.Element(qname)
        a.set(qname, qname)

        self.assertXML(
            _bytes('<ns0:a xmlns:ns0="http://myns" ns0:a="ns0:a"></ns0:a>'),
            a)

    def test_qname_attribute_resolve_new(self):
        etree = self.etree
        qname = etree.QName('http://myns', 'a')
        a = etree.Element('a')
        a.set('a', qname)

        self.assertXML(
            _bytes('<a xmlns:ns0="http://myns" a="ns0:a"></a>'),
            a)

    def test_qname_attrib_resolve(self):
        etree = self.etree
        qname = etree.QName('http://myns', 'a')
        a = etree.Element(qname)
        a.attrib[qname] = qname

        self.assertXML(
            _bytes('<ns0:a xmlns:ns0="http://myns" ns0:a="ns0:a"></ns0:a>'),
            a)

    def test_parser_version(self):
        etree = self.etree
        parser = etree.XMLParser()
        if hasattr(parser, "version"):
            # ElementTree 1.3+, cET
            self.assertTrue(re.match("[^ ]+ [0-9.]+", parser.version))

    # feed parser interface

    def test_feed_parser_bytes(self):
        parser = self.XMLParser()

        parser.feed(_bytes('<?xml version='))
        parser.feed(_bytes('"1.0"?><ro'))
        parser.feed(_bytes('ot><'))
        parser.feed(_bytes('a test="works"/'))
        parser.feed(_bytes('></root'))
        parser.feed(_bytes('>'))

        root = parser.close()

        self.assertEqual(root.tag, "root")
        self.assertEqual(root[0].tag, "a")
        self.assertEqual(root[0].get("test"), "works")

    def test_feed_parser_unicode(self):
        parser = self.XMLParser()

        parser.feed(_str('<ro'))
        parser.feed(_str('ot><'))
        parser.feed(_str('a test="works"/'))
        parser.feed(_str('></root'))
        parser.feed(_str('>'))

        root = parser.close()

        self.assertEqual(root.tag, "root")
        self.assertEqual(root[0].tag, "a")
        self.assertEqual(root[0].get("test"), "works")

    required_versions_ET['test_feed_parser_error_close_empty'] = (1,3)
    def test_feed_parser_error_close_empty(self):
        ParseError = self.etree.ParseError
        parser = self.XMLParser()
        self.assertRaises(ParseError, parser.close)

    required_versions_ET['test_feed_parser_error_close_incomplete'] = (1,3)
    def test_feed_parser_error_close_incomplete(self):
        ParseError = self.etree.ParseError
        parser = self.XMLParser()

        parser.feed('<?xml version=')
        parser.feed('"1.0"?><ro')

        self.assertRaises(ParseError, parser.close)

    required_versions_ET['test_feed_parser_error_broken'] = (1,3)
    def test_feed_parser_error_broken(self):
        ParseError = self.etree.ParseError
        parser = self.XMLParser()

        parser.feed('<?xml version=')
        parser.feed('"1.0"?><ro')
        try:
            parser.feed('<><><><><><><')
        except ParseError:
            # can raise, but not required before close()
            pass

        self.assertRaises(ParseError, parser.close)

    required_versions_ET['test_feed_parser_error_position'] = (1,3)
    def test_feed_parser_error_position(self):
        ParseError = self.etree.ParseError
        parser = self.XMLParser()
        try:
            parser.close()
        except ParseError:
            e = sys.exc_info()[1]
            self.assertNotEqual(None, e.code)
            self.assertNotEqual(0, e.code)
            self.assertTrue(isinstance(e.position, tuple))
            self.assertTrue(e.position >= (0, 0))

    # parser target interface

    required_versions_ET['test_parser_target_property'] = (1,3)
    def test_parser_target_property(self):
        class Target(object):
            pass

        target = Target()
        parser = self.XMLParser(target=target)

        self.assertEqual(target, parser.target)

    def test_parser_target_tag(self):
        assertEqual = self.assertEqual
        assertFalse  = self.assertFalse

        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append("start")
                assertFalse(attrib)
                assertEqual("TAG", tag)
            def end(self, tag):
                events.append("end")
                assertEqual("TAG", tag)
            def close(self):
                return "DONE"

        parser = self.XMLParser(target=Target())

        parser.feed("<TAG/>")
        done = parser.close()

        self.assertEqual("DONE", done)
        self.assertEqual(["start", "end"], events)

    def test_parser_target_error_in_start(self):
        assertEqual = self.assertEqual

        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append("start")
                assertEqual("TAG", tag)
                raise ValueError("TEST")
            def end(self, tag):
                events.append("end")
                assertEqual("TAG", tag)
            def close(self):
                return "DONE"

        parser = self.XMLParser(target=Target())

        try:
            parser.feed("<TAG/>")
        except ValueError:
            self.assertTrue('TEST' in str(sys.exc_info()[1]))
        else:
            self.assertTrue(False)
        if 'lxml' in self.etree.__name__:
            self.assertEqual(["start"], events)
        else:
            # cElementTree calls end() as well
            self.assertTrue("start" in events)

    def test_parser_target_error_in_end(self):
        assertEqual = self.assertEqual

        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append("start")
                assertEqual("TAG", tag)
            def end(self, tag):
                events.append("end")
                assertEqual("TAG", tag)
                raise ValueError("TEST")
            def close(self):
                return "DONE"

        parser = self.XMLParser(target=Target())

        try:
            parser.feed("<TAG/>")
        except ValueError:
            self.assertTrue('TEST' in str(sys.exc_info()[1]))
        else:
            self.assertTrue(False)
        self.assertEqual(["start", "end"], events)

    def test_parser_target_error_in_close(self):
        assertEqual = self.assertEqual

        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append("start")
                assertEqual("TAG", tag)
            def end(self, tag):
                events.append("end")
                assertEqual("TAG", tag)
            def close(self):
                raise ValueError("TEST")

        parser = self.XMLParser(target=Target())

        try:
            parser.feed("<TAG/>")
            parser.close()
        except ValueError:
            self.assertTrue('TEST' in str(sys.exc_info()[1]))
        else:
            self.assertTrue(False)
        self.assertEqual(["start", "end"], events)

    def test_parser_target_error_in_start_and_close(self):
        assertEqual = self.assertEqual

        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append("start")
                assertEqual("TAG", tag)
                raise IndexError("TEST-IE")
            def end(self, tag):
                events.append("end")
                assertEqual("TAG", tag)
            def close(self):
                raise ValueError("TEST-VE")

        parser = self.XMLParser(target=Target())

        try:
            parser.feed("<TAG/>")
            parser.close()
        except IndexError:
            if 'lxml' in self.etree.__name__:
                # we try not to swallow the initial exception in Py2
                self.assertTrue(sys.version_info[0] < 3)
            self.assertTrue('TEST-IE' in str(sys.exc_info()[1]))
        except ValueError:
            if 'lxml' in self.etree.__name__:
                self.assertTrue(sys.version_info[0] >= 3)
            self.assertTrue('TEST-VE' in str(sys.exc_info()[1]))
        else:
            self.assertTrue(False)

        if 'lxml' in self.etree.__name__:
            self.assertEqual(["start"], events)
        else:
            # cElementTree calls end() as well
            self.assertTrue("start" in events)

    def test_elementtree_parser_target(self):
        assertEqual = self.assertEqual
        assertFalse  = self.assertFalse
        Element = self.etree.Element

        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append("start")
                assertFalse(attrib)
                assertEqual("TAG", tag)
            def end(self, tag):
                events.append("end")
                assertEqual("TAG", tag)
            def close(self):
                return Element("DONE")

        parser = self.XMLParser(target=Target())
        tree = self.etree.ElementTree()
        tree.parse(BytesIO("<TAG/>"), parser=parser)

        self.assertEqual("DONE", tree.getroot().tag)
        self.assertEqual(["start", "end"], events)

    def test_parser_target_attrib(self):
        assertEqual = self.assertEqual

        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append("start-" + tag)
                for name, value in attrib.items():
                    assertEqual(tag + name, value)
            def end(self, tag):
                events.append("end-" + tag)
            def close(self):
                return "DONE"

        parser = self.XMLParser(target=Target())

        parser.feed('<root a="roota" b="rootb"><sub c="subc"/></root>')
        done = parser.close()

        self.assertEqual("DONE", done)
        self.assertEqual(["start-root", "start-sub", "end-sub", "end-root"],
                          events)

    def test_parser_target_data(self):
        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append("start-" + tag)
            def end(self, tag):
                events.append("end-" + tag)
            def data(self, data):
                events.append("data-" + data)
            def close(self):
                return "DONE"

        parser = self.XMLParser(target=Target())

        parser.feed('<root>A<sub/>B</root>')
        done = parser.close()

        self.assertEqual("DONE", done)
        self.assertEqual(["start-root", "data-A", "start-sub",
                           "end-sub", "data-B", "end-root"],
                          events)

    def test_parser_target_entity(self):
        events = []
        class Target(object):
            def __init__(self):
                self._data = []
            def _flush_data(self):
                if self._data:
                    events.append("data-" + ''.join(self._data))
                    del self._data[:]
            def start(self, tag, attrib):
                self._flush_data()
                events.append("start-" + tag)
            def end(self, tag):
                self._flush_data()
                events.append("end-" + tag)
            def data(self, data):
                self._data.append(data)
            def close(self):
                self._flush_data()
                return "DONE"

        parser = self.XMLParser(target=Target())

        dtd = '''
            <!DOCTYPE root [
            <!ELEMENT root (sub*)>
            <!ELEMENT sub (#PCDATA)>
            <!ENTITY ent "an entity">
        ]>
        '''
        parser.feed(dtd+'<root><sub/><sub>this is &ent;</sub><sub/></root>')
        done = parser.close()

        self.assertEqual("DONE", done)
        self.assertEqual(["start-root", "start-sub", "end-sub", "start-sub",
                           "data-this is an entity",
                           "end-sub", "start-sub", "end-sub", "end-root"],
                          events)

    required_versions_ET['test_parser_target_entity_unknown'] = (1,3)
    def test_parser_target_entity_unknown(self):
        events = []
        class Target(object):
            def __init__(self):
                self._data = []
            def _flush_data(self):
                if self._data:
                    events.append("data-" + ''.join(self._data))
                    del self._data[:]
            def start(self, tag, attrib):
                self._flush_data()
                events.append("start-" + tag)
            def end(self, tag):
                self._flush_data()
                events.append("end-" + tag)
            def data(self, data):
                self._data.append(data)
            def close(self):
                self._flush_data()
                return "DONE"

        parser = self.XMLParser(target=Target())

        def feed():
            parser.feed('<root><sub/><sub>some &ent;</sub><sub/></root>')
            parser.close()

        self.assertRaises(self.etree.ParseError, feed)

    def test_treebuilder(self):
        builder = self.etree.TreeBuilder()
        el = builder.start("root", {'a':'A', 'b':'B'})
        self.assertEqual("root", el.tag)
        self.assertEqual({'a':'A', 'b':'B'}, el.attrib)
        builder.data("ROOTTEXT")
        el = builder.start("child", {'x':'X', 'y':'Y'})
        self.assertEqual("child", el.tag)
        self.assertEqual({'x':'X', 'y':'Y'}, el.attrib)
        builder.data("CHILDTEXT")
        el = builder.end("child")
        self.assertEqual("child", el.tag)
        self.assertEqual({'x':'X', 'y':'Y'}, el.attrib)
        self.assertEqual("CHILDTEXT", el.text)
        self.assertEqual(None, el.tail)
        builder.data("CHILDTAIL")
        root = builder.end("root")

        self.assertEqual("root", root.tag)
        self.assertEqual("ROOTTEXT", root.text)
        self.assertEqual("CHILDTEXT", root[0].text)
        self.assertEqual("CHILDTAIL", root[0].tail)

    def test_treebuilder_target(self):
        parser = self.XMLParser(target=self.etree.TreeBuilder())
        parser.feed('<root>ROOTTEXT<child>CHILDTEXT</child>CHILDTAIL</root>')
        root = parser.close()

        self.assertEqual("root", root.tag)
        self.assertEqual("ROOTTEXT", root.text)
        self.assertEqual("CHILDTEXT", root[0].text)
        self.assertEqual("CHILDTAIL", root[0].tail)

    # helper methods

    def _writeElement(self, element, encoding='us-ascii'):
        """Write out element for comparison.
        """
        data = self.etree.tostring(element, encoding=encoding)
        return canonicalize(data)

    def _writeElementFile(self, element, encoding='us-ascii'):
        """Write out element for comparison, using real file.
        """
        ElementTree = self.etree.ElementTree
        handle, filename = tempfile.mkstemp()
        try:
            f = open(filename, 'wb')
            tree = ElementTree(element=element)
            tree.write(f, encoding=encoding)
            f.close()
            f = open(filename, 'rb')
            data = f.read()
            f.close()
        finally:
            os.close(handle)
            os.remove(filename)
        return canonicalize(data)

    def assertXML(self, expected, element, encoding='us-ascii'):
        """Writes element out and checks whether it is expected.

        Does this two ways; once using BytesIO, once using a real file.
        """
        if isinstance(expected, unicode):
            expected = expected.encode(encoding)
        self.assertEqual(expected, self._writeElement(element, encoding))
        self.assertEqual(expected, self._writeElementFile(element, encoding))

    def assertEncodingDeclaration(self, result, encoding):
        "Checks if the result XML byte string specifies the encoding."
        enc_re = r"<\?xml[^>]+ encoding=[\"']([^\"']+)[\"']"
        if isinstance(result, str):
            has_encoding = re.compile(enc_re).match
        else:
            has_encoding = re.compile(_bytes(enc_re)).match
        self.assertTrue(has_encoding(result))
        result_encoding = has_encoding(result).group(1)
        self.assertEqual(result_encoding.upper(), encoding.upper())
        
    def _rootstring(self, tree):
        return self.etree.tostring(tree.getroot()).replace(
            _bytes(' '), _bytes('')).replace(_bytes('\n'), _bytes(''))

    def _check_element_tree(self, tree):
        self._check_element(tree.getroot())
        
    def _check_element(self, element):
        self.assertTrue(hasattr(element, 'tag'))
        self.assertTrue(hasattr(element, 'attrib'))
        self.assertTrue(hasattr(element, 'text'))
        self.assertTrue(hasattr(element, 'tail'))
        self._check_string(element.tag)
        self._check_mapping(element.attrib)
        if element.text != None:
            self._check_string(element.text)
        if element.tail != None:
            self._check_string(element.tail)
        
    def _check_string(self, string):
        len(string)
        for char in string:
            self.assertEqual(1, len(char))
        new_string = string + ""
        new_string = string + " "
        string[:0]

    def _check_mapping(self, mapping):
        len(mapping)
        keys = mapping.keys()
        values = mapping.values()
        items = mapping.items()
        for key in keys:
            item = mapping[key]
        mapping["key"] = "value"
        self.assertEqual("value", mapping["key"])


class _XMLPullParserTest(unittest.TestCase):
    etree = None

    def _feed(self, parser, data, chunk_size=None):
        if chunk_size is None:
            parser.feed(data)
        else:
            for i in range(0, len(data), chunk_size):
                parser.feed(data[i:i+chunk_size])

    def _close_and_return_root(self, parser):
        if 'ElementTree' in self.etree.__name__:
            # ElementTree's API is a bit unwieldy in Py3.4
            root = parser._close_and_return_root()
        else:
            root = parser.close()
        return root

    def assert_event_tags(self, parser, expected):
        events = parser.read_events()
        self.assertEqual([(action, elem.tag) for action, elem in events],
                         expected)

    def test_simple_xml(self):
        for chunk_size in (None, 1, 5):
            #with self.subTest(chunk_size=chunk_size):
                parser = self.etree.XMLPullParser()
                self.assert_event_tags(parser, [])
                self._feed(parser, "<!-- comment -->\n", chunk_size)
                self.assert_event_tags(parser, [])
                self._feed(parser,
                           "<root>\n  <element key='value'>text</element",
                           chunk_size)
                self.assert_event_tags(parser, [])
                self._feed(parser, ">\n", chunk_size)
                self.assert_event_tags(parser, [('end', 'element')])
                self._feed(parser, "<element>text</element>tail\n", chunk_size)
                self._feed(parser, "<empty-element/>\n", chunk_size)
                self.assert_event_tags(parser, [
                    ('end', 'element'),
                    ('end', 'empty-element'),
                    ])
                self._feed(parser, "</root>\n", chunk_size)
                self.assert_event_tags(parser, [('end', 'root')])
                root = self._close_and_return_root(parser)
                self.assertEqual(root.tag, 'root')

    def test_feed_while_iterating(self):
        parser = self.etree.XMLPullParser()
        it = parser.read_events()
        self._feed(parser, "<root>\n  <element key='value'>text</element>\n")
        action, elem = next(it)
        self.assertEqual((action, elem.tag), ('end', 'element'))
        self._feed(parser, "</root>\n")
        action, elem = next(it)
        self.assertEqual((action, elem.tag), ('end', 'root'))
        try:
            next(it)
        except StopIteration:
            self.assertTrue(True)
        else:
            self.assertTrue(False)

    def test_simple_xml_with_ns(self):
        parser = self.etree.XMLPullParser()
        self.assert_event_tags(parser, [])
        self._feed(parser, "<!-- comment -->\n")
        self.assert_event_tags(parser, [])
        self._feed(parser, "<root xmlns='namespace'>\n")
        self.assert_event_tags(parser, [])
        self._feed(parser, "<element key='value'>text</element")
        self.assert_event_tags(parser, [])
        self._feed(parser, ">\n")
        self.assert_event_tags(parser, [('end', '{namespace}element')])
        self._feed(parser, "<element>text</element>tail\n")
        self._feed(parser, "<empty-element/>\n")
        self.assert_event_tags(parser, [
            ('end', '{namespace}element'),
            ('end', '{namespace}empty-element'),
            ])
        self._feed(parser, "</root>\n")
        self.assert_event_tags(parser, [('end', '{namespace}root')])
        root = self._close_and_return_root(parser)
        self.assertEqual(root.tag, '{namespace}root')

    def test_ns_events(self):
        parser = self.etree.XMLPullParser(events=('start-ns', 'end-ns'))
        self._feed(parser, "<!-- comment -->\n")
        self._feed(parser, "<root xmlns='namespace'>\n")
        self.assertEqual(
            list(parser.read_events()),
            [('start-ns', ('', 'namespace'))])
        self._feed(parser, "<element key='value'>text</element")
        self._feed(parser, ">\n")
        self._feed(parser, "<element>text</element>tail\n")
        self._feed(parser, "<empty-element/>\n")
        self._feed(parser, "</root>\n")
        self.assertEqual(list(parser.read_events()), [('end-ns', None)])
        parser.close()

    def test_events(self):
        parser = self.etree.XMLPullParser(events=())
        self._feed(parser, "<root/>\n")
        self.assert_event_tags(parser, [])

        parser = self.etree.XMLPullParser(events=('start', 'end'))
        self._feed(parser, "<!-- comment -->\n")
        self.assert_event_tags(parser, [])
        self._feed(parser, "<root>\n")
        self.assert_event_tags(parser, [('start', 'root')])
        self._feed(parser, "<element key='value'>text</element")
        self.assert_event_tags(parser, [('start', 'element')])
        self._feed(parser, ">\n")
        self.assert_event_tags(parser, [('end', 'element')])
        self._feed(parser,
                   "<element xmlns='foo'>text<empty-element/></element>tail\n")
        self.assert_event_tags(parser, [
            ('start', '{foo}element'),
            ('start', '{foo}empty-element'),
            ('end', '{foo}empty-element'),
            ('end', '{foo}element'),
            ])
        self._feed(parser, "</root>")
        root = self._close_and_return_root(parser)
        self.assert_event_tags(parser, [('end', 'root')])
        self.assertEqual(root.tag, 'root')

        parser = self.etree.XMLPullParser(events=('start',))
        self._feed(parser, "<!-- comment -->\n")
        self.assert_event_tags(parser, [])
        self._feed(parser, "<root>\n")
        self.assert_event_tags(parser, [('start', 'root')])
        self._feed(parser, "<element key='value'>text</element")
        self.assert_event_tags(parser, [('start', 'element')])
        self._feed(parser, ">\n")
        self.assert_event_tags(parser, [])
        self._feed(parser,
                   "<element xmlns='foo'>text<empty-element/></element>tail\n")
        self.assert_event_tags(parser, [
            ('start', '{foo}element'),
            ('start', '{foo}empty-element'),
            ])
        self._feed(parser, "</root>")
        root = self._close_and_return_root(parser)
        self.assertEqual(root.tag, 'root')

    def test_events_sequence(self):
        # Test that events can be some sequence that's not just a tuple or list
        eventset = set(['end', 'start'])
        parser = self.etree.XMLPullParser(events=eventset)
        self._feed(parser, "<foo>bar</foo>")
        self.assert_event_tags(parser, [('start', 'foo'), ('end', 'foo')])

        class DummyIter:
            def __init__(self):
                self.events = iter(['start', 'end', 'start-ns'])
            def __iter__(self):
                return self
            def __next__(self):
                return next(self.events)
            next = __next__

        parser = self.etree.XMLPullParser(events=DummyIter())
        self._feed(parser, "<foo>bar</foo>")
        self.assert_event_tags(parser, [('start', 'foo'), ('end', 'foo')])

    def test_unknown_event(self):
        try:
            self.etree.XMLPullParser(events=('start', 'end', 'bogus'))
        except ValueError:
            self.assertTrue(True)
        else:
            self.assertTrue(False)


if etree:
    class ETreeTestCase(_ETreeTestCaseBase):
        etree = etree

    class ETreePullTestCase(_XMLPullParserTest):
        etree = etree


if ElementTree:
    class ElementTreeTestCase(_ETreeTestCaseBase):
        etree = ElementTree

        @classmethod
        def setUpClass(cls):
            import warnings
            # ElementTree warns about getiterator() in recent Pythons
            warnings.filterwarnings(
                'ignore',
                r'This method will be removed.*\.iter\(\).*instead',
                PendingDeprecationWarning)

    filter_by_version(
        ElementTreeTestCase,
        ElementTreeTestCase.required_versions_ET, ET_VERSION)

    if hasattr(ElementTree, 'XMLPullParser'):
        class ElementTreePullTestCase(_XMLPullParserTest):
            etree = ElementTree
    else:
        ElementTreePullTestCase = None


if cElementTree:
    class CElementTreeTestCase(_ETreeTestCaseBase):
        etree = cElementTree

    filter_by_version(
        CElementTreeTestCase,
        CElementTreeTestCase.required_versions_cET, CET_VERSION)


def test_suite():
    suite = unittest.TestSuite()
    if etree:
        suite.addTests([unittest.makeSuite(ETreeTestCase)])
        suite.addTests([unittest.makeSuite(ETreePullTestCase)])
    if ElementTree:
        suite.addTests([unittest.makeSuite(ElementTreeTestCase)])
        if ElementTreePullTestCase:
            suite.addTests([unittest.makeSuite(ElementTreePullTestCase)])
    if cElementTree:
        suite.addTests([unittest.makeSuite(CElementTreeTestCase)])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
