# -*- coding: utf-8 -*-

"""
Tests for the ElementTree API

Only test cases that apply equally well to etree and ElementTree
belong here. Note that there is a second test module called test_io.py
for IO related test cases.
"""

import unittest, doctest
import os, re, tempfile, copy, operator, gc

from common_imports import StringIO, etree, ElementTree, cElementTree
from common_imports import fileInTestDir, canonicalize, HelperTestCase

if cElementTree is not None:
    if tuple([int(n) for n in
              getattr(cElementTree, "VERSION", "0.0").split(".")]) <= (1,0,7):
        cElementTree = None

try:
    reversed
except NameError:
    # Python 2.3
    def reversed(seq):
        seq = list(seq)[::-1]
        return seq

class ETreeTestCaseBase(HelperTestCase):
    etree = None

    def test_element(self):
        for i in range(10):
            e = self.etree.Element('foo')
            self.assertEquals(e.tag, 'foo')
            self.assertEquals(e.text, None)
            self.assertEquals(e.tail, None)

    def test_simple(self):
        Element = self.etree.Element
        
        root = Element('root')
        root.append(Element('one'))
        root.append(Element('two'))
        root.append(Element('three'))
        self.assertEquals(3, len(root))
        self.assertEquals('one', root[0].tag)
        self.assertEquals('two', root[1].tag)
        self.assertEquals('three', root[2].tag)
        self.assertRaises(IndexError, operator.getitem, root, 3)

    def test_subelement(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        root = Element('root')
        SubElement(root, 'one')
        SubElement(root, 'two')
        SubElement(root, 'three')
        self.assertEquals(3, len(root))
        self.assertEquals('one', root[0].tag)
        self.assertEquals('two', root[1].tag)
        self.assertEquals('three', root[2].tag)
        
    def test_element_contains(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        root1 = Element('root')
        SubElement(root1, 'one')
        self.assert_(root1[0] in root1)

        root2 = Element('root')
        SubElement(root2, 'two')
        SubElement(root2, 'three')
        self.assert_(root2[0] in root2)
        self.assert_(root2[1] in root2)

        self.assertFalse(root1[0] in root2)
        self.assertFalse(root2[0] in root1)
        self.assertFalse(None in root2)

    def test_element_indexing_with_text(self):
        ElementTree = self.etree.ElementTree
        
        f = StringIO('<doc>Test<one>One</one></doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals(1, len(root))
        self.assertEquals('one', root[0].tag)
        self.assertRaises(IndexError, operator.getitem, root, 1)
        
    def test_element_indexing_with_text2(self):
        ElementTree = self.etree.ElementTree
        
        f = StringIO('<doc><one>One</one><two>Two</two>hm<three>Three</three></doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals(3, len(root))
        self.assertEquals('one', root[0].tag)
        self.assertEquals('two', root[1].tag)
        self.assertEquals('three', root[2].tag)

    def test_element_indexing_only_text(self):
        ElementTree = self.etree.ElementTree
        
        f = StringIO('<doc>Test</doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals(0, len(root))

    def test_element_indexing_negative(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')
        self.assertEquals(d, a[-1])
        self.assertEquals(c, a[-2])
        self.assertEquals(b, a[-3])
        self.assertRaises(IndexError, operator.getitem, a, -4)
        a[-1] = e = Element('e')
        self.assertEquals(e, a[-1])
        del a[-1]
        self.assertEquals(2, len(a))
        
    def test_elementtree(self):
        ElementTree = self.etree.ElementTree
        
        f = StringIO('<doc><one>One</one><two>Two</two></doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals(2, len(root))
        self.assertEquals('one', root[0].tag)
        self.assertEquals('two', root[1].tag)

    def test_text(self):
        ElementTree = self.etree.ElementTree
        
        f = StringIO('<doc>This is a text</doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals('This is a text', root.text)

    def test_text_empty(self):
        ElementTree = self.etree.ElementTree
        
        f = StringIO('<doc></doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals(None, root.text)

    def test_text_other(self):
        ElementTree = self.etree.ElementTree
        
        f = StringIO('<doc><one>One</one></doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals(None, root.text)
        self.assertEquals('One', root[0].text)

    def test_text_escape_in(self):
        ElementTree = self.etree.ElementTree

        f = StringIO('<doc>This is &gt; than a text</doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals('This is > than a text', root.text)

    def test_text_escape_out(self):
        Element = self.etree.Element

        a = Element("a")
        a.text = "<>&"
        self.assertXML('<a>&lt;&gt;&amp;</a>',
                       a)

    def test_text_escape_tostring(self):
        tostring = self.etree.tostring
        Element  = self.etree.Element

        a = Element("a")
        a.text = "<>&"
        self.assertEquals('<a>&lt;&gt;&amp;</a>',
                         tostring(a))

    def test_text_str_subclass(self):
        Element = self.etree.Element

        class strTest(str):
            pass

        a = Element("a")
        a.text = strTest("text")
        self.assertXML('<a>text</a>',
                       a)

    def test_tail(self):
        ElementTree = self.etree.ElementTree
        
        f = StringIO('<doc>This is <i>mixed</i> content.</doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals(1, len(root))
        self.assertEquals('This is ', root.text)
        self.assertEquals(None, root.tail)
        self.assertEquals('mixed', root[0].text)
        self.assertEquals(' content.', root[0].tail)

    def test_tail_str_subclass(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        class strTest(str):
            pass

        a = Element("a")
        SubElement(a, "t").tail = strTest("tail")
        self.assertXML('<a><t></t>tail</a>',
                       a)

    def _test_del_tail(self):
        # this is discouraged for ET compat, should not be tested...
        XML = self.etree.XML
        
        root = XML('<doc>This is <i>mixed</i> content.</doc>')
        self.assertEquals(1, len(root))
        self.assertEquals('This is ', root.text)
        self.assertEquals(None, root.tail)
        self.assertEquals('mixed', root[0].text)
        self.assertEquals(' content.', root[0].tail)

        del root[0].tail

        self.assertEquals(1, len(root))
        self.assertEquals('This is ', root.text)
        self.assertEquals(None, root.tail)
        self.assertEquals('mixed', root[0].text)
        self.assertEquals(None, root[0].tail)

        root[0].tail = "TAIL"

        self.assertEquals(1, len(root))
        self.assertEquals('This is ', root.text)
        self.assertEquals(None, root.tail)
        self.assertEquals('mixed', root[0].text)
        self.assertEquals('TAIL', root[0].tail)

    def test_ElementTree(self):
        Element = self.etree.Element
        ElementTree = self.etree.ElementTree
        
        el = Element('hoi')
        doc = ElementTree(el)
        root = doc.getroot()
        self.assertEquals(None, root.text)
        self.assertEquals('hoi', root.tag)

    def test_attributes(self):
        ElementTree = self.etree.ElementTree
        
        f = StringIO('<doc one="One" two="Two"/>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals('One', root.attrib['one'])
        self.assertEquals('Two', root.attrib['two'])
        self.assertRaises(KeyError, operator.getitem, root.attrib, 'three')

    def test_attributes2(self):
        ElementTree = self.etree.ElementTree
        
        f = StringIO('<doc one="One" two="Two"/>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals('One', root.attrib.get('one'))
        self.assertEquals('Two', root.attrib.get('two'))
        self.assertEquals(None, root.attrib.get('three'))
        self.assertEquals('foo', root.attrib.get('three', 'foo'))

    def test_attributes3(self):
        ElementTree = self.etree.ElementTree
        
        f = StringIO('<doc one="One" two="Two"/>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals('One', root.get('one'))
        self.assertEquals('Two', root.get('two'))
        self.assertEquals(None, root.get('three'))
        self.assertEquals('foo', root.get('three', 'foo'))

    def test_attrib_clear(self):
        XML = self.etree.XML
        
        root = XML('<doc one="One" two="Two"/>')
        self.assertEquals('One', root.get('one'))
        self.assertEquals('Two', root.get('two'))
        root.attrib.clear()
        self.assertEquals(None, root.get('one'))
        self.assertEquals(None, root.get('two'))

    def test_attrib_set_clear(self):
        Element = self.etree.Element
        
        root = Element("root", one="One")
        root.set("two", "Two")
        self.assertEquals('One', root.get('one'))
        self.assertEquals('Two', root.get('two'))
        root.attrib.clear()
        self.assertEquals(None, root.get('one'))
        self.assertEquals(None, root.get('two'))

    def test_attrib_ns_clear(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        attribNS = '{http://foo/bar}x'

        parent = Element('parent')
        parent.set(attribNS, 'a')
        child = SubElement(parent, 'child')
        child.set(attribNS, 'b')

        self.assertEquals('a', parent.get(attribNS))
        self.assertEquals('b', child.get(attribNS))

        parent.clear()
        self.assertEquals(None, parent.get(attribNS))
        self.assertEquals('b', child.get(attribNS))

    def test_attribute_update_dict(self):
        XML = self.etree.XML
        
        root = XML('<doc alpha="Alpha" beta="Beta"/>')
        items = root.attrib.items()
        items.sort()
        self.assertEquals(
            [('alpha', 'Alpha'), ('beta', 'Beta')],
            items)

        root.attrib.update({'alpha' : 'test', 'gamma' : 'Gamma'})

        items = root.attrib.items()
        items.sort()
        self.assertEquals(
            [('alpha', 'test'), ('beta', 'Beta'), ('gamma', 'Gamma')],
            items)

    def test_attribute_update_sequence(self):
        XML = self.etree.XML
        
        root = XML('<doc alpha="Alpha" beta="Beta"/>')
        items = root.attrib.items()
        items.sort()
        self.assertEquals(
            [('alpha', 'Alpha'), ('beta', 'Beta')],
            items)

        root.attrib.update({'alpha' : 'test', 'gamma' : 'Gamma'}.items())

        items = root.attrib.items()
        items.sort()
        self.assertEquals(
            [('alpha', 'test'), ('beta', 'Beta'), ('gamma', 'Gamma')],
            items)

    def test_attribute_update_iter(self):
        XML = self.etree.XML
        
        root = XML('<doc alpha="Alpha" beta="Beta"/>')
        items = root.attrib.items()
        items.sort()
        self.assertEquals(
            [('alpha', 'Alpha'), ('beta', 'Beta')],
            items)

        root.attrib.update({'alpha' : 'test', 'gamma' : 'Gamma'}.iteritems())

        items = root.attrib.items()
        items.sort()
        self.assertEquals(
            [('alpha', 'test'), ('beta', 'Beta'), ('gamma', 'Gamma')],
            items)

    def test_attribute_keys(self):
        XML = self.etree.XML
        
        root = XML('<doc alpha="Alpha" beta="Beta" gamma="Gamma"/>')
        keys = root.attrib.keys()
        keys.sort()
        self.assertEquals(['alpha', 'beta', 'gamma'], keys)

    def test_attribute_keys2(self):
        XML = self.etree.XML
        
        root = XML('<doc alpha="Alpha" beta="Beta" gamma="Gamma"/>')
        keys = root.keys()
        keys.sort()
        self.assertEquals(['alpha', 'beta', 'gamma'], keys)

    def test_attribute_items2(self):
        XML = self.etree.XML
        
        root = XML('<doc alpha="Alpha" beta="Beta" gamma="Gamma"/>')
        items = root.items()
        items.sort()
        self.assertEquals(
            [('alpha','Alpha'), ('beta','Beta'), ('gamma','Gamma')],
            items)

    def test_attribute_keys_ns(self):
        XML = self.etree.XML

        root = XML('<foo bar="Bar" xmlns:ns="http://ns.codespeak.net/test" ns:baz="Baz" />')
        keys = root.keys()
        keys.sort()
        self.assertEquals(['bar', '{http://ns.codespeak.net/test}baz'],
                          keys)
        
    def test_attribute_values(self):
        XML = self.etree.XML
        
        root = XML('<doc alpha="Alpha" beta="Beta" gamma="Gamma"/>')
        values = root.attrib.values()
        values.sort()
        self.assertEquals(['Alpha', 'Beta', 'Gamma'], values)

    def test_attribute_values_ns(self):
        XML = self.etree.XML
        
        root = XML('<foo bar="Bar" xmlns:ns="http://ns.codespeak.net/test" ns:baz="Baz" />')
        values = root.attrib.values()
        values.sort()
        self.assertEquals(
            ['Bar', 'Baz'], values)
        
    def test_attribute_items(self):
        XML = self.etree.XML
        
        root = XML('<doc alpha="Alpha" beta="Beta" gamma="Gamma"/>')
        items = root.attrib.items()
        items.sort()
        self.assertEquals([
            ('alpha', 'Alpha'),
            ('beta', 'Beta'),
            ('gamma', 'Gamma'),
            ], 
            items)

    def test_attribute_items_ns(self):
        XML = self.etree.XML
        
        root = XML('<foo bar="Bar" xmlns:ns="http://ns.codespeak.net/test" ns:baz="Baz" />')
        items = root.attrib.items()
        items.sort()
        self.assertEquals(
            [('bar', 'Bar'), ('{http://ns.codespeak.net/test}baz', 'Baz')],
            items)

    def test_attribute_str(self):
        XML = self.etree.XML

        expected = "{'{http://ns.codespeak.net/test}baz': 'Baz', 'bar': 'Bar'}"
        alternative = "{'bar': 'Bar', '{http://ns.codespeak.net/test}baz': 'Baz'}"
        
        root = XML('<foo bar="Bar" xmlns:ns="http://ns.codespeak.net/test" ns:baz="Baz" />')
        try:
            self.assertEquals(expected, str(root.attrib))
        except AssertionError:
            self.assertEquals(alternative, str(root.attrib))

    def test_attribute_has_key(self):
        XML = self.etree.XML

        root = XML('<foo bar="Bar" xmlns:ns="http://ns.codespeak.net/test" ns:baz="Baz" />')
        self.assertEquals(
            True, root.attrib.has_key('bar'))
        self.assertEquals(
            False, root.attrib.has_key('baz'))
        self.assertEquals(
            False, root.attrib.has_key('hah'))
        self.assertEquals(
            True,
            root.attrib.has_key('{http://ns.codespeak.net/test}baz'))

    def test_attribute_contains(self):
        XML = self.etree.XML

        root = XML('<foo bar="Bar" xmlns:ns="http://ns.codespeak.net/test" ns:baz="Baz" />')
        self.assertEquals(
            True, 'bar' in root.attrib)
        self.assertEquals(
            False, 'baz' in root.attrib)
        self.assertEquals(
            False, 'hah' in root.attrib)
        self.assertEquals(
            True,
            '{http://ns.codespeak.net/test}baz' in root.attrib)

    def test_attribute_set(self):
        Element = self.etree.Element

        root = Element("root")
        root.set("attr", "TEST")
        self.assertEquals("TEST", root.get("attr"))

    def test_XML(self):
        XML = self.etree.XML
        
        root = XML('<doc>This is a text.</doc>')
        self.assertEquals(0, len(root))
        self.assertEquals('This is a text.', root.text)

    def test_XMLID(self):
        XMLID = self.etree.XMLID
        XML   = self.etree.XML
        xml_text = '''
        <document>
          <h1 id="chapter1">...</h1>
          <p id="note1" class="note">...</p>
          <p>Regular paragraph.</p>
          <p xml:id="xmlid">XML:ID paragraph.</p>
          <p id="warn1" class="warning">...</p>
        </document>
        '''

        root, dic = XMLID(xml_text)
        root2 = XML(xml_text)
        self.assertEquals(self._writeElement(root),
                          self._writeElement(root2))
        expected = {
            "chapter1" : root[0],
            "note1"    : root[1],
            "warn1"    : root[4]
            }
        self.assertEquals(dic, expected)

    def test_fromstring(self):
        fromstring = self.etree.fromstring

        root = fromstring('<doc>This is a text.</doc>')
        self.assertEquals(0, len(root))
        self.assertEquals('This is a text.', root.text)

    def test_fromstringlist(self):
        fromstringlist = self.etree.fromstringlist

        root = fromstringlist(["<do", "c>T", "hi", "s is",
                               " a text.<", "/doc", ">"])
        self.assertEquals(0, len(root))
        self.assertEquals('This is a text.', root.text)

    def test_fromstringlist_characters(self):
        fromstringlist = self.etree.fromstringlist

        root = fromstringlist(list('<doc>This is a text.</doc>'))
        self.assertEquals(0, len(root))
        self.assertEquals('This is a text.', root.text)

    def test_fromstringlist_single(self):
        fromstringlist = self.etree.fromstringlist

        root = fromstringlist(['<doc>This is a text.</doc>'])
        self.assertEquals(0, len(root))
        self.assertEquals('This is a text.', root.text)

    def test_iselement(self):
        iselement = self.etree.iselement
        Element = self.etree.Element
        ElementTree = self.etree.ElementTree
        XML = self.etree.XML
        Comment = self.etree.Comment
        ProcessingInstruction = self.etree.ProcessingInstruction
        
        el = Element('hoi')
        self.assert_(iselement(el))

        el2 = XML('<foo/>')
        self.assert_(iselement(el2))

        tree = ElementTree(element=Element('dag'))
        self.assert_(not iselement(tree))
        self.assert_(iselement(tree.getroot()))

        c = Comment('test')
        self.assert_(iselement(c))

        p = ProcessingInstruction("test", "some text")
        self.assert_(iselement(p))
        
    def test_iteration(self):
        XML = self.etree.XML
        
        root = XML('<doc><one/><two>Two</two>Hm<three/></doc>')
        result = []
        for el in root:
            result.append(el.tag)
        self.assertEquals(['one', 'two', 'three'], result)

    def test_iteration_empty(self):
        XML = self.etree.XML
        
        root = XML('<doc></doc>')
        result = []
        for el in root:
            result.append(el.tag)
        self.assertEquals([], result)

    def test_iteration_text_only(self):
        XML = self.etree.XML
        
        root = XML('<doc>Text</doc>')
        result = []
        for el in root:
            result.append(el.tag)
        self.assertEquals([], result)

    def test_iteration_crash(self):
        # this would cause a crash in the past
        fromstring = self.etree.fromstring
        root = etree.fromstring('<html><p></p>x</html>')
        for elem in root:
            elem.tail = ''

    def test_iteration_reversed(self):
        XML = self.etree.XML
        root = XML('<doc><one/><two>Two</two>Hm<three/></doc>')
        result = []
        for el in reversed(root):
            result.append(el.tag)
        self.assertEquals(['three', 'two', 'one'], result)

    def test_iteration_subelement(self):
        XML = self.etree.XML

        root = XML('<doc><one/><two>Two</two>Hm<three/></doc>')
        result = []
        add = True
        for el in root:
            result.append(el.tag)
            if add:
                self.etree.SubElement(root, 'four')
                add = False
        self.assertEquals(['one', 'two', 'three', 'four'], result)

    def test_iteration_del_child(self):
        XML = self.etree.XML

        root = XML('<doc><one/><two>Two</two>Hm<three/></doc>')
        result = []
        for el in root:
            result.append(el.tag)
            del root[-1]
        self.assertEquals(['one', 'two'], result)

    def test_iteration_double(self):
        XML = self.etree.XML

        root = XML('<doc><one/><two/></doc>')
        result = []
        for el0 in root:
            result.append(el0.tag)
            for el1 in root:
                result.append(el1.tag)
        self.assertEquals(['one','one', 'two', 'two', 'one', 'two'], result)

    def test_attribute_iterator(self):
        XML = self.etree.XML
        
        root = XML('<doc alpha="Alpha" beta="Beta" gamma="Gamma" />')
        result = []
        for key in root.attrib:
            result.append(key)
        result.sort()
        self.assertEquals(['alpha', 'beta', 'gamma'], result)

    def test_findall(self):
        XML = self.etree.XML
        root = XML('<a><b><c/></b><b/><c><b/></c></a>')
        self.assertEquals(len(list(root.findall("c"))), 1)
        self.assertEquals(len(list(root.findall(".//c"))), 2)
        self.assertEquals(len(list(root.findall(".//b"))), 3)
        self.assertEquals(len(list(root.findall(".//b"))[0]), 1)
        self.assertEquals(len(list(root.findall(".//b"))[1]), 0)
        self.assertEquals(len(list(root.findall(".//b"))[2]), 0)

    def test_findall_ns(self):
        XML = self.etree.XML
        root = XML('<a xmlns:x="X" xmlns:y="Y"><x:b><c/></x:b><b/><c><x:b/><b/></c><b/></a>')
        self.assertEquals(len(list(root.findall(".//{X}b"))), 2)
        self.assertEquals(len(list(root.findall(".//b"))), 3)
        self.assertEquals(len(list(root.findall("b"))), 2)

    def test_element_with_attributes_keywords(self):
        Element = self.etree.Element
        
        el = Element('tag', foo='Foo', bar='Bar')
        self.assertEquals('Foo', el.attrib['foo'])
        self.assertEquals('Bar', el.attrib['bar'])

    def test_element_with_attributes(self):
        Element = self.etree.Element
        
        el = Element('tag', {'foo':'Foo', 'bar':'Bar'})
        self.assertEquals('Foo', el.attrib['foo'])
        self.assertEquals('Bar', el.attrib['bar'])

    def test_element_with_attributes_ns(self):
        Element = self.etree.Element

        el = Element('tag', {'{ns1}foo':'Foo', '{ns2}bar':'Bar'})
        self.assertEquals('Foo', el.attrib['{ns1}foo'])
        self.assertEquals('Bar', el.attrib['{ns2}bar'])

    def test_subelement_with_attributes(self):
        Element =  self.etree.Element
        SubElement = self.etree.SubElement
        
        el = Element('tag')
        SubElement(el, 'foo', {'foo':'Foo'}, baz="Baz")
        self.assertEquals("Baz", el[0].attrib['baz'])
        self.assertEquals('Foo', el[0].attrib['foo'])

    def test_subelement_with_attributes_ns(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        el = Element('tag')
        SubElement(el, 'foo', {'{ns1}foo':'Foo', '{ns2}bar':'Bar'})
        self.assertEquals('Foo', el[0].attrib['{ns1}foo'])
        self.assertEquals('Bar', el[0].attrib['{ns2}bar'])
        
    def test_write(self):
        ElementTree = self.etree.ElementTree
        XML = self.etree.XML

        for i in range(10):
            f = StringIO() 
            root = XML('<doc%s>This is a test.</doc%s>' % (i, i))
            tree = ElementTree(element=root)
            tree.write(f)
            data = f.getvalue()
            self.assertEquals(
                '<doc%s>This is a test.</doc%s>' % (i, i),
                canonicalize(data))

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
        f = StringIO() 
        tree.write(f, method="html")
        data = f.getvalue().replace('\n','')

        self.assertEquals('<html><body><p>html<br>test</p></body></html>',
                          data)

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
        f = StringIO() 
        tree.write(f, method="text")
        data = f.getvalue()

        self.assertEquals('ABTAILCtail',
                          data)
        
    def test_write_fail(self):
        ElementTree = self.etree.ElementTree
        XML = self.etree.XML

        tree = ElementTree( XML('<doc>This is a test.</doc>') )
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
            self.assertEquals(value, 'value')
            
    # from doctest; for some reason this caused crashes too
    def test_write_ElementTreeDoctest(self):
        Element = self.etree.Element
        ElementTree = self.etree.ElementTree
        
        f = StringIO()
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
        self.assertEquals(
            'baz2-modified',
            el[1][0].text)

    def test_set_text(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        a.text = 'hoi'
        self.assertEquals(
            'hoi',
            a.text)
        self.assertEquals(
            'b',
            a[0].tag)

    def test_set_text2(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        a.text = 'hoi'
        b = SubElement(a ,'b')
        self.assertEquals(
            'hoi',
            a.text)
        self.assertEquals(
            'b',
            a[0].tag)

    def test_set_text_none(self):
        Element = self.etree.Element

        a = Element('a')

        a.text = 'foo'
        a.text = None

        self.assertEquals(
            None,
            a.text)
        self.assertXML('<a></a>', a)
        
    def test_set_text_empty(self):
        Element = self.etree.Element

        a = Element('a')
        self.assertEquals(None, a.text)

        a.text = ''
        self.assertEquals('', a.text)
        self.assertXML('<a></a>', a)
        
    def test_tail1(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        a.tail = 'dag'
        self.assertEquals('dag',
                          a.tail)
        b = SubElement(a, 'b')
        b.tail = 'hoi'
        self.assertEquals('hoi',
                          b.tail)
        self.assertEquals('dag',
                          a.tail)

    def test_tail_append(self):
        Element = self.etree.Element
        
        a = Element('a')
        b = Element('b')
        b.tail = 'b_tail'
        a.append(b)
        self.assertEquals('b_tail',
                          b.tail)

    def test_tail_set_twice(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        b.tail = 'foo'
        b.tail = 'bar'
        self.assertEquals('bar',
                          b.tail)
        self.assertXML('<a><b></b>bar</a>', a)
        
    def test_tail_set_none(self):
        Element = self.etree.Element
        a = Element('a')
        a.tail = 'foo'
        a.tail = None
        self.assertEquals(
            None,
            a.tail)
        self.assertXML('<a></a>', a)

    def test_comment(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        Comment = self.etree.Comment

        a = Element('a')
        a.append(Comment('foo'))
        self.assertEquals(a[0].tag, Comment)
        self.assertEquals(a[0].text, 'foo')

    def test_comment_text(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        Comment = self.etree.Comment

        a = Element('a')
        a.append(Comment('foo'))
        self.assertEquals(a[0].text, 'foo')

        a[0].text = "TEST"
        self.assertEquals(a[0].text, 'TEST')
        
    def test_comment_whitespace(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        Comment = self.etree.Comment

        a = Element('a')
        a.append(Comment(' foo  '))
        self.assertEquals(a[0].text, ' foo  ')
        
    def test_comment_nonsense(self):
        Comment = self.etree.Comment
        c = Comment('foo')
        self.assertEquals({}, c.attrib)
        self.assertEquals([], c.keys())
        self.assertEquals([], c.items())
        self.assertEquals(None, c.get('hoi'))
        self.assertEquals(0, len(c))
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
        self.assertEquals(a[0].tag, ProcessingInstruction)
        self.assertXML("<a><?foo some more text?></a>",
                       a)

    def test_processinginstruction(self):
        # lxml.etree separates target and text
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        ProcessingInstruction = self.etree.PI

        a = Element('a')
        a.append(ProcessingInstruction('foo', 'some more text'))
        self.assertEquals(a[0].tag, ProcessingInstruction)
        self.assertXML("<a><?foo some more text?></a>",
                       a)

    def test_pi_nonsense(self):
        ProcessingInstruction = self.etree.ProcessingInstruction
        pi = ProcessingInstruction('foo')
        self.assertEquals({}, pi.attrib)
        self.assertEquals([], pi.keys())
        self.assertEquals([], pi.items())
        self.assertEquals(None, pi.get('hoi'))
        self.assertEquals(0, len(pi))
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
        self.assertEquals(
            c,
            a[0])
        self.assertXML('<a><c></c></a>',
                       a)
        self.assertXML('<b></b>',
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
            '<a><d><e></e></d><d><e></e></d><d><e></e></d><d><e></e></d><d><e></e></d></a>',
            a)
        self.assertXML('<c></c>',
                       c)

    def test_setitem_replace(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        SubElement(a, 'b')
        d = Element('d')
        a[0] = d
        self.assertXML('<a><d></d></a>', a)

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
            '<a><c></c>C2</a>',
            a)

    def test_tag_write(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')

        a.tag = 'c'

        self.assertEquals(
            'c',
            a.tag)

        self.assertXML(
            '<c><b></b></c>',
            a)

    def test_tag_reset_ns(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        tostring = self.etree.tostring

        a = Element('{a}a')
        b1 = SubElement(a, '{a}b')
        b2 = SubElement(a, '{b}b')

        self.assertEquals('{a}b',  b1.tag)

        b1.tag = 'c'

        # can't use C14N here!
        self.assertEquals('c', b1.tag)
        self.assertEquals('<c', tostring(b1)[:2])
        self.assert_('<c' in tostring(a))

    def test_tag_reset_root_ns(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        tostring = self.etree.tostring

        a = Element('{a}a')
        b1 = SubElement(a, '{a}b')
        b2 = SubElement(a, '{b}b')

        a.tag = 'c'

        self.assertEquals(
            'c',
            a.tag)

        # can't use C14N here!
        self.assertEquals('c',  a.tag)
        self.assertEquals('<c', tostring(a)[:2])

    def test_tag_str_subclass(self):
        Element = self.etree.Element

        class strTest(str):
            pass

        a = Element("a")
        a.tag = strTest("TAG")
        self.assertXML('<TAG></TAG>',
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
            '<a><b></b><d></d></a>',
            a)

        del a[0]
        self.assertXML(
            '<a><d></d></a>',
            a)

        del a[0]
        self.assertXML(
            '<a></a>',
            a)
        # move deleted element into other tree afterwards
        other = Element('other')
        other.append(c)
        self.assertXML(
            '<other><c></c></other>',
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
            '<a><b><bs></bs></b><c><cs></cs></c></a>',
            a)
        self.assertXML('<b><bs></bs></b>', b)
        self.assertXML('<c><cs></cs></c>', c)

        del a[0]
        self.assertXML(
            '<a><c><cs></cs></c></a>',
            a)
        self.assertXML('<b><bs></bs></b>', b)
        self.assertXML('<c><cs></cs></c>', c)

        a.insert(0, el)
        self.assertXML(
            '<a><b><bs></bs></b><c><cs></cs></c></a>',
            a)
        self.assertXML('<b><bs></bs></b>', b)
        self.assertXML('<c><cs></cs></c>', c)

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
            '<a><b><bs></bs></b></a>',
            a)
        self.assertXML('<b><bs></bs></b>', b)
        self.assertXML('<c><cs></cs></c>', c)

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
            '<a><b><bs></bs></b><c><cs></cs></c></a>',
            a)
        self.assertXML('<b><bs></bs></b>', b)
        self.assertXML('<c><cs></cs></c>', c)

    def test_replace_slice_tail(self):
        XML = self.etree.XML
        a = XML('<a><b></b>B2<c></c>C2</a>')
        b, c = a

        a[:] = []

        self.assertEquals("B2", b.tail)
        self.assertEquals("C2", c.tail)

    def test_delitem_tail(self):
        ElementTree = self.etree.ElementTree
        f = StringIO('<a><b></b>B2<c></c>C2</a>')
        doc = ElementTree(file=f)
        a = doc.getroot()
        del a[0]
        self.assertXML(
            '<a><c></c>C2</a>',
            a)
        
    def test_clear(self):
        Element = self.etree.Element
     
        a = Element('a')
        a.text = 'foo'
        a.tail = 'bar'
        a.set('hoi', 'dag')
        a.clear()
        self.assertEquals(None, a.text)
        self.assertEquals(None, a.tail)
        self.assertEquals(None, a.get('hoi'))
        self.assertEquals('a', a.tag)

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
        self.assertEquals(None, a.text)
        self.assertEquals(None, a.tail)
        self.assertEquals(None, a.get('hoi'))
        self.assertEquals('a', a.tag)
        self.assertEquals(0, len(a))
        self.assertXML('<a></a>',
                       a)
        self.assertXML('<b><c></c></b>',
                       b)
    
    def test_clear_tail(self):
        ElementTree = self.etree.ElementTree
        f = StringIO('<a><b></b>B2<c></c>C2</a>')
        doc = ElementTree(file=f)
        a = doc.getroot()
        a.clear()
        self.assertXML(
            '<a></a>',
            a)

    def test_insert(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = Element('d')
        a.insert(0, d)

        self.assertEquals(
            d,
            a[0])

        self.assertXML(
            '<a><d></d><b></b><c></c></a>',
            a)

        e = Element('e')
        a.insert(2, e)
        self.assertEquals(
            e,
            a[2])
        self.assertXML(
            '<a><d></d><b></b><e></e><c></c></a>',
            a)

    def test_insert_beyond_index(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = Element('c')

        a.insert(2, c)
        self.assertEquals(
            c,
            a[1])
        self.assertXML(
            '<a><b></b><c></c></a>',
            a)

    def test_insert_negative(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')

        d = Element('d')
        a.insert(-1, d)
        self.assertEquals(
            d,
            a[-2])
        self.assertXML(
            '<a><b></b><d></d><c></c></a>',
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
            '<a><c></c>C2<b></b></a>',
            a)
        
    def test_remove(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')

        a.remove(b)
        self.assertEquals(
            c,
            a[0])
        self.assertXML(
            '<a><c></c></a>',
            a)
        
    def test_remove_ns(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('{http://test}a')
        b = SubElement(a, '{http://test}b')
        c = SubElement(a, '{http://test}c')

        a.remove(b)
        self.assertXML(
            '<ns0:a xmlns:ns0="http://test"><ns0:c></ns0:c></ns0:a>',
            a)
        self.assertXML(
            '<ns0:b xmlns:ns0="http://test"></ns0:b>',
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
            '<a></a>',
            a)
        self.assertEquals('b2', b.tail)

    def _test_getchildren(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        e = SubElement(c, 'e')
        self.assertXML(
            '<a><b><d></d></b><c><e></e></c></a>',
            a)
        self.assertEquals(
            [b, c],
            a.getchildren())
        self.assertEquals(
            [d],
            b.getchildren())
        self.assertEquals(
            [],
            d.getchildren())

    def test_makeelement(self):
        Element = self.etree.Element

        a = Element('a')
        b = a.makeelement('c', {'hoi':'dag'})
        self.assertXML(
            '<c hoi="dag"></c>',
            b)

    def test_iter(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        e = SubElement(c, 'e')

        self.assertEquals(
            [a, b, d, c, e],
            list(a.iter()))
        self.assertEquals(
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

        self.assertEquals(
            [a, b, d, c, e],
            list(a.getiterator()))
        self.assertEquals(
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

        self.assertEquals(
            [],
            list(a.getiterator('none')))
        self.assertEquals(
            [],
            list(e.getiterator('none')))
        self.assertEquals(
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

        self.assertEquals(
            [a],
            list(a.getiterator('a')))
        a2 = SubElement(e, 'a')
        self.assertEquals(
            [a, a2],
            list(a.getiterator('a')))
        self.assertEquals(
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

        self.assertEquals(
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

        self.assertEquals(
            [comment_b],
            list(a.getiterator(Comment)))

        comment_a = Comment("TEST-a")
        a.append(comment_a)

        self.assertEquals(
            [comment_b, comment_a],
            list(a.getiterator(Comment)))

        self.assertEquals(
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

        self.assertEquals(
            [pi_b],
            list(a.getiterator(PI)))

        pi_a = PI("TEST-a")
        a.append(pi_a)

        self.assertEquals(
            [pi_b, pi_a],
            list(a.getiterator(PI)))

        self.assertEquals(
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

        self.assertEquals(
            [a, b, d, c, e],
            list(a.getiterator()))
        #self.assertEquals(
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

        self.assertEquals(
            [a],
            list(a.getiterator('a')))
        a2 = SubElement(e, 'a')
        self.assertEquals(
            [a, a2],
            list(a.getiterator('a')))   
        self.assertEquals(
            [a2],
            list(e.getiterator('a')))

    def test_attribute_manipulation(self):
        Element = self.etree.Element

        a = Element('a')
        a.attrib['foo'] = 'Foo'
        a.attrib['bar'] = 'Bar'
        self.assertEquals('Foo', a.attrib['foo'])
        del a.attrib['foo']
        self.assertRaises(KeyError, operator.getitem, a.attrib, 'foo')

    def test_getslice(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')

        self.assertEquals(
            [b, c],
            a[0:2])
        self.assertEquals(
            [b, c, d],
            a[:])
        self.assertEquals(
            [b, c, d],
            a[:10])
        self.assertEquals(
            [b],
            a[0:1])
        self.assertEquals(
            [],
            a[10:12])

    def test_getslice_negative(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')

        self.assertEquals(
            [d],
            a[-1:])
        self.assertEquals(
            [c, d],
            a[-2:])
        self.assertEquals(
            [c],
            a[-2:-1])
        self.assertEquals(
            [b, c],
            a[-3:-1])
        self.assertEquals(
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

        self.assertEquals(
            [e,d,c,b],
            a[::-1])
        self.assertEquals(
            [b,d],
            a[::2])
        self.assertEquals(
            [e,c],
            a[::-2])
        self.assertEquals(
            [d,c],
            a[-2:0:-1])
        self.assertEquals(
            [e],
            a[:1:-2])

    def test_getslice_text(self):
        ElementTree = self.etree.ElementTree
        
        f = StringIO('<a><b>B</b>B1<c>C</c>C1</a>')
        doc = ElementTree(file=f)
        a = doc.getroot()
        b = a[0]
        c = a[1]
        self.assertEquals(
            [b, c],
            a[:])
        self.assertEquals(
            [b],
            a[0:1])
        self.assertEquals(
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
        self.assertEquals(
            [b, foo, c],
            a[:])
        self.assertEquals(
            foo,
            a[1])
        a[1] = new = Element('new')
        self.assertEquals(
            new,
            a[1])
        self.assertXML(
            '<a><b></b><new></new><c></c></a>',
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
        self.assertEquals(
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
        self.assertEquals(
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
        self.assertEquals(
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
        self.assertEquals(
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
        self.assertEquals(
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
        self.assertEquals(
            [b, d],
            list(a))

    def test_delslice_child_tail(self):
        ElementTree = self.etree.ElementTree
        f = StringIO('<a><b></b>B2<c></c>C2<d></d>D2<e></e>E2</a>')
        doc = ElementTree(file=f)
        a = doc.getroot()
        del a[1:3]
        self.assertXML(
            '<a><b></b>B2<e></e>E2</a>',
            a)

    def test_delslice_tail(self):
        XML = self.etree.XML
        a = XML('<a><b></b>B2<c></c>C2</a>')
        b, c = a

        del a[:]

        self.assertEquals("B2", b.tail)
        self.assertEquals("C2", c.tail)

    def test_delslice_memory(self):
        # this could trigger a crash
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(b, 'c')
        del b # no more reference to b
        del a[:]
        self.assertEquals('c', c.tag)
        
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
        self.assertEquals(
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
        self.assertEquals(
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
        self.assertEquals(
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
        self.assertEquals(
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
        self.assertEquals(
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
        self.assertEquals(
            [d, c, b],
            list(a))
        self.assertEquals(
            ['{ns}d', '{ns}c', '{ns}b'],
            [ child.tag for child in a ])

        self.assertEquals(
            [['{ns3}a3'], ['{ns2}a2'], ['{ns1}a1']],
            [ child.attrib.keys() for child in a ])

    def test_setslice_all_replace_reversed_ns2(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('{ns}a')
        b = SubElement(a, '{ns1}b', {'{ns}a1': 'test'})
        c = SubElement(a, '{ns2}c', {'{ns}a2': 'test'})
        d = SubElement(a, '{ns3}d', {'{ns}a3': 'test'})

        s = [d, c, b]
        a[:] = s
        self.assertEquals(
            [d, c, b],
            list(a))
        self.assertEquals(
            ['{ns3}d', '{ns2}c', '{ns1}b'],
            [ child.tag for child in a ])

        self.assertEquals(
            [['{ns}a3'], ['{ns}a2'], ['{ns}a1']],
            [ child.attrib.keys() for child in a ])

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
        self.assertEquals(
            [a, b, e, f],
            list(a))

        s = [g, h]
        a[:0] = s
        self.assertEquals(
            [g, h, a, b, e, f],
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
        self.assertEquals(
            [e, c],
            list(a))

        s = [f]
        a[1:2] = s
        self.assertEquals(
            [e, f],
            list(a))

    def test_setslice_tail(self):
        ElementTree = self.etree.ElementTree
        Element = self.etree.Element
        f = StringIO('<a><b></b>B2<c></c>C2<d></d>D2<e></e>E2</a>')
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
            '<a><b></b>B2<x></x>X2<y></y>Y2<z></z>Z2<e></e>E2</a>',
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
        self.assertEquals(
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
        self.assertEquals(
            [b, x, y, c, d],
            list(a))

    def test_setslice_end(self):
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
        self.assertEquals(
            [b, c, d, e, f, g],
            list(a))
        
    def test_setslice_empty(self):
        Element = self.etree.Element

        a = Element('a')

        b = Element('b')
        c = Element('c')

        a[:] = [b, c]
        self.assertEquals(
            [b, c],
            list(a))

    def test_tail_elementtree_root(self):
        Element = self.etree.Element
        ElementTree = self.etree.ElementTree

        a = Element('a')
        a.tail = 'A2'
        t = ElementTree(element=a)
        self.assertEquals('A2',
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
        
        self.assertEquals(
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
        
        self.assertEquals(
            [a],
            list(t.getiterator('a')))
        a2 = SubElement(e, 'a')
        self.assertEquals(
            [a, a2],
            list(t.getiterator('a')))

    def test_ns_access(self):
        ElementTree = self.etree.ElementTree
        ns = 'http://xml.infrae.com/1'
        f = StringIO('<x:a xmlns:x="%s"><x:b></x:b></x:a>' % ns)
        t = ElementTree(file=f)
        a = t.getroot()
        self.assertEquals('{%s}a' % ns,
                          a.tag)
        self.assertEquals('{%s}b' % ns,
                          a[0].tag)

    def test_ns_access2(self):
        ElementTree = self.etree.ElementTree
        ns = 'http://xml.infrae.com/1'
        ns2 = 'http://xml.infrae.com/2'
        f = StringIO('<x:a xmlns:x="%s" xmlns:y="%s"><x:b></x:b><y:b></y:b></x:a>' % (ns, ns2))
        t = ElementTree(file=f)
        a = t.getroot()
        self.assertEquals('{%s}a' % ns,
                          a.tag)
        self.assertEquals('{%s}b' % ns,
                          a[0].tag)
        self.assertEquals('{%s}b' % ns2,
                          a[1].tag)

    def test_ns_setting(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        ns = 'http://xml.infrae.com/1'
        ns2 = 'http://xml.infrae.com/2'
        a = Element('{%s}a' % ns)
        b = SubElement(a, '{%s}b' % ns2)
        c = SubElement(a, '{%s}c' % ns)
        self.assertEquals('{%s}a' % ns,
                          a.tag)
        self.assertEquals('{%s}b' % ns2,
                          b.tag)
        self.assertEquals('{%s}c' % ns,
                          c.tag)
        self.assertEquals('{%s}a' % ns,
                          a.tag)
        self.assertEquals('{%s}b' % ns2,
                          b.tag)
        self.assertEquals('{%s}c' % ns,
                          c.tag)

    def test_ns_tag_parse(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        ElementTree = self.etree.ElementTree

        ns = 'http://xml.infrae.com/1'
        ns2 = 'http://xml.infrae.com/2'
        f = StringIO('<a xmlns="%s" xmlns:x="%s"><x:b></x:b><b></b></a>' % (ns, ns2))
        t = ElementTree(file=f)

        a = t.getroot()
        self.assertEquals('{%s}a' % ns,
                          a.tag)
        self.assertEquals('{%s}b' % ns2,
                          a[0].tag)
        self.assertEquals('{%s}b' % ns,
                          a[1].tag)

    def test_ns_attr(self):
        Element = self.etree.Element
        ns = 'http://xml.infrae.com/1'
        ns2 = 'http://xml.infrae.com/2'
        a = Element('a')
        a.set('{%s}foo' % ns, 'Foo')
        a.set('{%s}bar' % ns2, 'Bar')
        self.assertEquals(
            'Foo',
            a.get('{%s}foo' % ns))
        self.assertEquals(
            'Bar',
            a.get('{%s}bar' % ns2))
        try:
            self.assertXML(
                '<a xmlns:ns0="%s" xmlns:ns1="%s" ns0:foo="Foo" ns1:bar="Bar"></a>' % (ns, ns2),
                a)
        except AssertionError:
            self.assertXML(
                '<a xmlns:ns0="%s" xmlns:ns1="%s" ns1:foo="Foo" ns0:bar="Bar"></a>' % (ns2, ns),
                a)

    def test_ns_move(self):
        Element = self.etree.Element
        ElementTree = self.etree.ElementTree
        
        one = self.etree.parse(
            StringIO('<foo><bar xmlns:ns="http://a.b.c"><ns:baz/></bar></foo>'))
        baz = one.getroot()[0][0]

        two = ElementTree(Element('root'))
        two.getroot().append(baz)
        # removing the originating document could cause a crash/error before
        # as namespace is not moved along with it
        del one
        self.assertEquals('{http://a.b.c}baz', baz.tag)

    def test_ns_decl_tostring(self):
        tostring = self.etree.tostring
        root = self.etree.XML(
            '<foo><bar xmlns:ns="http://a.b.c"><ns:baz/></bar></foo>')
        baz = root[0][0]

        nsdecl = re.findall("xmlns(?::[a-z0-9]+)?=[\"']([^\"']+)[\"']",
                            tostring(baz))
        self.assertEquals(["http://a.b.c"], nsdecl)

    def test_ns_decl_tostring_default(self):
        tostring = self.etree.tostring
        root = self.etree.XML(
            '<foo><bar xmlns="http://a.b.c"><baz/></bar></foo>')
        baz = root[0][0]

        nsdecl = re.findall("xmlns(?::[a-z0-9]+)?=[\"']([^\"']+)[\"']",
                            tostring(baz))
        self.assertEquals(["http://a.b.c"], nsdecl)
        
    def test_ns_decl_tostring_root(self):
        tostring = self.etree.tostring
        root = self.etree.XML(
            '<foo xmlns:ns="http://a.b.c"><bar><ns:baz/></bar></foo>')
        baz = root[0][0]

        nsdecl = re.findall("xmlns(?::[a-z0-9]+)?=[\"']([^\"']+)[\"']",
                            tostring(baz))

        self.assertEquals(["http://a.b.c"], nsdecl)
        
    def test_ns_decl_tostring_element(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        root = Element("foo")
        bar = SubElement(root, "{http://a.b.c}bar")
        baz = SubElement(bar, "{http://a.b.c}baz")

        nsdecl = re.findall("xmlns(?::[a-z0-9]+)?=[\"']([^\"']+)[\"']",
                            self.etree.tostring(baz))

        self.assertEquals(["http://a.b.c"], nsdecl)

    def test_attribute_xmlns_move(self):
        Element = self.etree.Element

        root = Element('element')

        subelement = Element('subelement',
                             {"{http://www.w3.org/XML/1998/namespace}id": "foo"})
        self.assertEquals(1, len(subelement.attrib))
        self.assertEquals(
            "foo",
            subelement.get("{http://www.w3.org/XML/1998/namespace}id"))

        root.append(subelement)
        self.assertEquals(1, len(subelement.attrib))
        self.assertEquals(
            {"{http://www.w3.org/XML/1998/namespace}id" : "foo"}.items(),
            subelement.attrib.items())
        self.assertEquals(
            "foo",
            subelement.get("{http://www.w3.org/XML/1998/namespace}id"))

    def test_tostring(self):
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        
        self.assertEquals('<a><b></b><c></c></a>',
                          canonicalize(tostring(a)))

    def test_tostring_element(self):
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(c, 'd')
        self.assertEquals('<b></b>',
                          canonicalize(tostring(b)))
        self.assertEquals('<c><d></d></c>',
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

        self.assert_(tostring(b) == '<b/>Foo' or
                     tostring(b) == '<b />Foo')

    def test_tostring_method_html(self):
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        html = Element('html')
        body = SubElement(html, 'body')
        p = SubElement(body, 'p')
        p.text = "html"
        SubElement(p, 'br').tail = "test"

        self.assertEquals('<html><body><p>html<br>test</p></body></html>',
                          tostring(html, method="html"))

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
        
        self.assertEquals('ABTAILCtail',
                          tostring(a, method="text"))

    def test_iterparse(self):
        iterparse = self.etree.iterparse
        f = StringIO('<a><b></b><c/></a>')

        iterator = iterparse(f)
        self.assertEquals(None,
                          iterator.root)
        events = list(iterator)
        root = iterator.root
        self.assertEquals(
            [('end', root[0]), ('end', root[1]), ('end', root)],
            events)

    def test_iterparse_file(self):
        iterparse = self.etree.iterparse
        iterator = iterparse(fileInTestDir("test.xml"))
        self.assertEquals(None,
                          iterator.root)
        events = list(iterator)
        root = iterator.root
        self.assertEquals(
            [('end', root[0]), ('end', root)],
            events)

    def test_iterparse_start(self):
        iterparse = self.etree.iterparse
        f = StringIO('<a><b></b><c/></a>')

        iterator = iterparse(f, events=('start',))
        events = list(iterator)
        root = iterator.root
        self.assertEquals(
            [('start', root), ('start', root[0]), ('start', root[1])],
            events)

    def test_iterparse_start_end(self):
        iterparse = self.etree.iterparse
        f = StringIO('<a><b></b><c/></a>')

        iterator = iterparse(f, events=('start','end'))
        events = list(iterator)
        root = iterator.root
        self.assertEquals(
            [('start', root), ('start', root[0]), ('end', root[0]),
             ('start', root[1]), ('end', root[1]), ('end', root)],
            events)

    def test_iterparse_clear(self):
        iterparse = self.etree.iterparse
        f = StringIO('<a><b></b><c/></a>')

        iterator = iterparse(f)
        for event, elem in iterator:
            elem.clear()

        root = iterator.root
        self.assertEquals(0,
                          len(root))

    def test_iterparse_large(self):
        iterparse = self.etree.iterparse
        CHILD_COUNT = 12345
        f = StringIO('<a>%s</a>' % ('<b>test</b>'*CHILD_COUNT))

        i = 0
        for key in iterparse(f):
            event, element = key
            i += 1
        self.assertEquals(i, CHILD_COUNT + 1)

    def test_iterparse_attrib_ns(self):
        iterparse = self.etree.iterparse
        f = StringIO('<a xmlns="ns1"><b><c xmlns="ns2"/></b></a>')

        attr_name = '{testns}bla'
        events = []
        iterator = iterparse(f, events=('start','end','start-ns','end-ns'))
        for event, elem in iterator:
            events.append(event)
            if event == 'start':
                if elem.tag != '{ns1}a':
                    elem.set(attr_name, 'value')

        self.assertEquals(
            ['start-ns', 'start', 'start', 'start-ns', 'start',
             'end', 'end-ns', 'end', 'end', 'end-ns'],
            events)

        root = iterator.root
        self.assertEquals(
            None,
            root.get(attr_name))
        self.assertEquals(
            'value',
            root[0].get(attr_name))

    def test_iterparse_getiterator(self):
        iterparse = self.etree.iterparse
        f = StringIO('<a><b><d/></b><c/></a>')

        counts = []
        for event, elem in iterparse(f):
            counts.append(len(list(elem.getiterator())))
        self.assertEquals(
            [1,2,1,4],
            counts)

    def test_parse_file(self):
        parse = self.etree.parse
        # from file
        tree = parse(fileInTestDir('test.xml'))
        self.assertXML(
            '<a><b></b></a>',
            tree.getroot())

    def test_parse_file_nonexistent(self):
        parse = self.etree.parse
        self.assertRaises(IOError, parse, fileInTestDir('notthere.xml'))  

    def test_parse_file_object(self):
        parse = self.etree.parse
        # from file object
        f = open(fileInTestDir('test.xml'), 'r')
        tree = parse(f)
        f.close()
        self.assertXML(
            '<a><b></b></a>',
            tree.getroot())

    def test_parse_stringio(self):
        parse = self.etree.parse
        # from StringIO
        f = StringIO('<a><b></b></a>')
        tree = parse(f)
        f.close()
        self.assertXML(
            '<a><b></b></a>',
            tree.getroot()
           )

    def test_parse_with_encoding(self):
        # this can fail in libxml2 <= 2.6.22
        parse = self.etree.parse
        tree = parse(StringIO('<?xml version="1.0" encoding="ascii"?><html/>'))
        self.assertXML('<html></html>',
                       tree.getroot())

    def test_encoding(self):
        Element = self.etree.Element

        a = Element('a')
        a.text = u'Søk på nettet'
        self.assertXML(
            u'<a>Søk på nettet</a>'.encode('UTF-8'),
            a, 'utf-8')

    def test_encoding_exact(self):
        ElementTree = self.etree.ElementTree
        Element = self.etree.Element

        a = Element('a')
        a.text = u'Søk på nettet'
        
        f = StringIO()
        tree = ElementTree(element=a)
        tree.write(f, encoding='utf-8')
        self.assertEquals(u'<a>Søk på nettet</a>'.encode('UTF-8'),
                          f.getvalue().replace('\n',''))

    def test_parse_file_encoding(self):
        parse = self.etree.parse
        # from file
        tree = parse(fileInTestDir('test-string.xml'))
        self.assertXML(
            u'<a>Søk på nettet</a>'.encode('UTF-8'),
            tree.getroot(), 'UTF-8')

    def test_parse_file_object_encoding(self):
        parse = self.etree.parse
        # from file object
        f = open(fileInTestDir('test-string.xml'), 'r')
        tree = parse(f)
        f.close()
        self.assertXML(
            u'<a>Søk på nettet</a>'.encode('UTF-8'),
            tree.getroot(), 'UTF-8')

    def test_encoding_8bit_latin1(self):
        ElementTree = self.etree.ElementTree
        Element = self.etree.Element

        a = Element('a')
        a.text = u'Søk på nettet'

        f = StringIO()
        tree = ElementTree(element=a)
        tree.write(f, encoding='iso-8859-1')
        result = f.getvalue()
        declaration = "<?xml version=\'1.0\' encoding=\'iso-8859-1\'?>"
        self.assertEncodingDeclaration(result,'iso-8859-1')
        result = result.split('?>', 1)[-1].replace('\n','')
        self.assertEquals(u'<a>Søk på nettet</a>'.encode('iso-8859-1'),
                          result)

    def test_parse_encoding_8bit_explicit(self):
        XMLParser = self.etree.XMLParser

        text = u'Søk på nettet'
        xml_latin1 = (u'<a>%s</a>' % text).encode('iso-8859-1')

        self.assertRaises(self.etree.ParseError,
                          self.etree.parse,
                          StringIO(xml_latin1))

        tree = self.etree.parse(StringIO(xml_latin1),
                                XMLParser(encoding="iso-8859-1"))
        a = tree.getroot()
        self.assertEquals(a.text, text)

    def test_parse_encoding_8bit_override(self):
        XMLParser = self.etree.XMLParser

        text = u'Søk på nettet'
        wrong_declaration = "<?xml version='1.0' encoding='UTF-8'?>"
        xml_latin1 = (u'%s<a>%s</a>' % (wrong_declaration, text)
                      ).encode('iso-8859-1')

        self.assertRaises(self.etree.ParseError,
                          self.etree.parse,
                          StringIO(xml_latin1))

        tree = self.etree.parse(StringIO(xml_latin1),
                                XMLParser(encoding="iso-8859-1"))
        a = tree.getroot()
        self.assertEquals(a.text, text)

    def _test_wrong_unicode_encoding(self):
        # raise error on wrong encoding declaration in unicode strings
        XML = self.etree.XML
        test_utf = (u'<?xml version="1.0" encoding="iso-8859-1"?>' + \
                                        u'<a>Søk på nettet</a>')
        self.assertRaises(SyntaxError, XML, test_utf)

    def test_encoding_write_default_encoding(self):
        ElementTree = self.etree.ElementTree
        Element = self.etree.Element

        a = Element('a')
        a.text = u'Søk på nettet'
        
        f = StringIO()
        tree = ElementTree(element=a)
        tree.write(f)
        data = f.getvalue().replace('\n','')
        self.assertEquals(
            u'<a>Søk på nettet</a>'.encode('ASCII', 'xmlcharrefreplace'),
            data)

    def test_encoding_tostring(self):
        Element = self.etree.Element
        tostring = self.etree.tostring

        a = Element('a')
        a.text = u'Søk på nettet'
        self.assertEquals(u'<a>Søk på nettet</a>'.encode('UTF-8'),
                         tostring(a, encoding='utf-8'))

    def test_encoding_tostring_unknown(self):
        Element = self.etree.Element
        tostring = self.etree.tostring
        
        a = Element('a')
        a.text = u'Søk på nettet'
        self.assertRaises(LookupError, tostring, a,
                          encoding='Invalid Encoding')

    def test_encoding_tostring_sub(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        tostring = self.etree.tostring

        a = Element('a')
        b = SubElement(a, 'b')
        b.text = u'Søk på nettet'
        self.assertEquals(u'<b>Søk på nettet</b>'.encode('UTF-8'),
                         tostring(b, encoding='utf-8'))

    def test_encoding_tostring_sub_tail(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        tostring = self.etree.tostring

        a = Element('a')
        b = SubElement(a, 'b')
        b.text = u'Søk på nettet'
        b.tail = u'Søk'
        self.assertEquals(u'<b>Søk på nettet</b>Søk'.encode('UTF-8'),
                         tostring(b, encoding='utf-8'))
        
    def test_encoding_tostring_default_encoding(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        tostring = self.etree.tostring

        a = Element('a')
        a.text = u'Søk på nettet'

        expected = '<a>S&#248;k p&#229; nettet</a>'
        self.assertEquals(
            expected,
            tostring(a))

    def test_encoding_sub_tostring_default_encoding(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        tostring = self.etree.tostring

        a = Element('a')
        b = SubElement(a, 'b')
        b.text = u'Søk på nettet'

        expected = '<b>S&#248;k p&#229; nettet</b>'
        self.assertEquals(
            expected,
            tostring(b))

    def test_encoding_8bit_xml(self):
        utext = u'Søk på nettet'
        uxml = u'<p>%s</p>' % utext
        prologue = '<?xml version="1.0" encoding="iso-8859-1" ?>'
        isoxml = prologue + uxml.encode('iso-8859-1')
        tree = self.etree.XML(isoxml)
        self.assertEquals(utext, tree.text)

    def test_encoding_utf8_bom(self):
        utext = u'Søk på nettet'
        uxml = u'<?xml version="1.0" encoding="UTF-8"?>' + \
               u'<p>%s</p>' % utext
        bom = '\xEF\xBB\xBF'
        xml = bom + uxml.encode("utf-8")
        tree = etree.XML(xml)
        self.assertEquals(utext, tree.text)

    def test_encoding_8bit_parse_stringio(self):
        utext = u'Søk på nettet'
        uxml = u'<p>%s</p>' % utext
        prologue = '<?xml version="1.0" encoding="iso-8859-1" ?>'
        isoxml = prologue + uxml.encode('iso-8859-1')
        el = self.etree.parse(StringIO(isoxml)).getroot()
        self.assertEquals(utext, el.text)

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
        self.assertEquals('Foo', b.text)
        
        b.text = 'Bar'
        self.assertEquals('Bar', b.text)
        self.assertEquals('Foo', a.text)

        del a
        self.assertEquals('Bar', b.text)

    def test_deepcopy_tail(self):
        Element = self.etree.Element
        
        a = Element('a')
        a.tail = 'Foo'

        b = copy.deepcopy(a)
        self.assertEquals('Foo', b.tail)
        
        b.tail = 'Bar'
        self.assertEquals('Bar', b.tail)
        self.assertEquals('Foo', a.tail)

        del a
        self.assertEquals('Bar', b.tail)

    def test_deepcopy_subelement(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        root = Element('root')
        a = SubElement(root, 'a')
        a.text = 'FooText'
        a.tail = 'FooTail'

        b = copy.deepcopy(a)
        self.assertEquals('FooText', b.text)
        self.assertEquals('FooTail', b.tail)
        
        b.text = 'BarText'
        b.tail = 'BarTail'
        self.assertEquals('BarTail', b.tail)
        self.assertEquals('FooTail', a.tail)
        self.assertEquals('BarText', b.text)
        self.assertEquals('FooText', a.text)

        del a
        self.assertEquals('BarTail', b.tail)
        self.assertEquals('BarText', b.text)

    def test_deepcopy_namespaces(self):
        root = self.etree.XML('''<doc xmlns="dns" xmlns:t="tns">
        <parent><node t:foo="bar" /></parent>
        </doc>''')
        self.assertEquals(
            root[0][0].get('{tns}foo'),
            copy.deepcopy(root[0])[0].get('{tns}foo') )
        self.assertEquals(
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

        self.assertEquals('<a><C/></a>',
                          tostring(a).replace(' ', ''))
        self.assertEquals('<a><X/></a>',
                          tostring(b).replace(' ', ''))

    def test_shallowcopy(self):
        Element = self.etree.Element
        
        a = Element('a')
        a.text = 'Foo'

        b = copy.copy(a)
        self.assertEquals('Foo', b.text)
        
        b.text = 'Bar'
        self.assertEquals('Bar', b.text)
        self.assertEquals('Foo', a.text)
        # XXX ElementTree will share nodes, but lxml.etree won't..

    def test_shallowcopy_elementtree(self):
        Element = self.etree.Element
        ElementTree = self.etree.ElementTree
        
        a = Element('a')
        a.text = 'Foo'
        atree = ElementTree(a)

        btree = copy.copy(atree)
        self.assertFalse(btree is atree)
        self.assert_(btree.getroot() is atree.getroot())
        self.assertEquals('Foo', atree.getroot().text)

    def _test_element_boolean(self):
        # deprecated as of ET 1.3/lxml 2.0
        etree = self.etree
        e = etree.Element('foo')
        self.assertEquals(False, bool(e))
        etree.SubElement(e, 'bar')
        self.assertEquals(True, bool(e))
        e = etree.Element('foo')
        e.text = 'hey'
        self.assertEquals(False, bool(e))
        e = etree.Element('foo')
        e.tail = 'bar'
        self.assertEquals(False, bool(e))
        e = etree.Element('foo')
        e.set('bar', 'Bar')
        self.assertEquals(False, bool(e))

    def test_multiple_elementrees(self):
        etree = self.etree

        a = etree.Element('a')
        b = etree.SubElement(a, 'b')

        t = etree.ElementTree(a)
        self.assertEquals(self._rootstring(t), '<a><b/></a>')

        t1 = etree.ElementTree(a)
        self.assertEquals(self._rootstring(t1), '<a><b/></a>')
        self.assertEquals(self._rootstring(t),  '<a><b/></a>')

        t2 = etree.ElementTree(b)
        self.assertEquals(self._rootstring(t2), '<b/>')
        self.assertEquals(self._rootstring(t1), '<a><b/></a>')
        self.assertEquals(self._rootstring(t),  '<a><b/></a>')

    def test_qname(self):
        etree = self.etree
        qname = etree.QName('myns', 'a')
        a1 = etree.Element(qname)
        a2 = etree.SubElement(a1, qname)
        self.assertEquals(a1.tag, "{myns}a")
        self.assertEquals(a2.tag, "{myns}a")

    def test_qname_cmp(self):
        etree = self.etree
        qname1 = etree.QName('myns', 'a')
        qname2 = etree.QName('myns', 'a')
        self.assertEquals(qname1, "{myns}a")
        self.assertEquals("{myns}a", qname2)
        self.assertEquals(qname1, qname1)
        self.assertEquals(qname1, qname2)

    def test_qname_attribute_getset(self):
        etree = self.etree
        qname = etree.QName('myns', 'a')

        a = etree.Element(qname)
        a.set(qname, "value")

        self.assertEquals(a.get(qname), "value")
        self.assertEquals(a.get("{myns}a"), "value")

    def test_qname_attrib(self):
        etree = self.etree
        qname = etree.QName('myns', 'a')

        a = etree.Element(qname)
        a.attrib[qname] = "value"

        self.assertEquals(a.attrib[qname], "value")
        self.assertEquals(a.attrib.get(qname), "value")

        self.assertEquals(a.attrib["{myns}a"], "value")
        self.assertEquals(a.attrib.get("{myns}a"), "value")

    def test_qname_attribute_resolve(self):
        etree = self.etree
        qname = etree.QName('http://myns', 'a')
        a = etree.Element(qname)
        a.set(qname, qname)

        self.assertXML(
            '<ns0:a xmlns:ns0="http://myns" ns0:a="ns0:a"></ns0:a>',
            a)

    def test_qname_attribute_resolve_new(self):
        etree = self.etree
        qname = etree.QName('http://myns', 'a')
        a = etree.Element('a')
        a.set('a', qname)

        self.assertXML(
            '<a xmlns:ns0="http://myns" a="ns0:a"></a>',
            a)

    def test_qname_attrib_resolve(self):
        etree = self.etree
        qname = etree.QName('http://myns', 'a')
        a = etree.Element(qname)
        a.attrib[qname] = qname

        self.assertXML(
            '<ns0:a xmlns:ns0="http://myns" ns0:a="ns0:a"></ns0:a>',
            a)

    def test_parser_version(self):
        etree = self.etree
        parser = etree.XMLParser()
        if hasattr(parser, "version"):
            # ElementTree 1.3+, cET
            self.assert_(re.match("[^ ]+ [0-9.]+", parser.version))

    # feed parser interface

    def test_feed_parser(self):
        parser = self.etree.XMLParser()

        parser.feed('<?xml version=')
        parser.feed('"1.0"?><ro')
        parser.feed('ot><')
        parser.feed('a test="works"/')
        parser.feed('></root')
        parser.feed('>')

        root = parser.close()

        self.assertEquals(root.tag, "root")
        self.assertEquals(root[0].tag, "a")
        self.assertEquals(root[0].get("test"), "works")

    def test_feed_parser_error_close_empty(self):
        ParseError = self.etree.ParseError
        parser = self.etree.XMLParser()
        self.assertRaises(ParseError, parser.close)

    def test_feed_parser_error_close_incomplete(self):
        ParseError = self.etree.ParseError
        parser = self.etree.XMLParser()

        parser.feed('<?xml version=')
        parser.feed('"1.0"?><ro')

        self.assertRaises(ParseError, parser.close)

    def test_feed_parser_error_broken(self):
        ParseError = self.etree.ParseError
        parser = self.etree.XMLParser()

        parser.feed('<?xml version=')
        parser.feed('"1.0"?><ro')
        try:
            parser.feed('<><><><><><><')
        except ParseError:
            # can raise, but not required before close()
            pass

        self.assertRaises(ParseError, parser.close)

    def test_feed_parser_error_position(self):
        ParseError = self.etree.ParseError
        parser = self.etree.XMLParser()
        try:
            parser.close()
        except ParseError, e:
            self.assertNotEquals(None, e.code)
            self.assertNotEquals(0, e.code)
            self.assert_(isinstance(e.position, tuple))
            self.assert_(e.position >= (0, 0))

    # parser target interface

    def test_parser_target_tag(self):
        assertEquals = self.assertEquals
        assertFalse  = self.assertFalse

        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append("start")
                assertFalse(attrib)
                assertEquals("TAG", tag)
            def end(self, tag):
                events.append("end")
                assertEquals("TAG", tag)
            def close(self):
                return "DONE"

        parser = self.etree.XMLParser(target=Target())

        parser.feed("<TAG/>")
        done = parser.close()

        self.assertEquals("DONE", done)
        self.assertEquals(["start", "end"], events)

    def test_parser_target_attrib(self):
        assertEquals = self.assertEquals

        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append("start-" + tag)
                for name, value in attrib.iteritems():
                    assertEquals(tag + name, value)
            def end(self, tag):
                events.append("end-" + tag)
            def close(self):
                return "DONE"

        parser = self.etree.XMLParser(target=Target())

        parser.feed('<root a="roota" b="rootb"><sub c="subc"/></root>')
        done = parser.close()

        self.assertEquals("DONE", done)
        self.assertEquals(["start-root", "start-sub", "end-sub", "end-root"],
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

        parser = self.etree.XMLParser(target=Target())

        parser.feed('<root>A<sub/>B</root>')
        done = parser.close()

        self.assertEquals("DONE", done)
        self.assertEquals(["start-root", "data-A", "start-sub",
                           "end-sub", "data-B", "end-root"],
                          events)

    def test_treebuilder(self):
        builder = self.etree.TreeBuilder()
        el = builder.start("root", {'a':'A', 'b':'B'})
        self.assertEquals("root", el.tag)
        self.assertEquals({'a':'A', 'b':'B'}, el.attrib)
        builder.data("ROOTTEXT")
        el = builder.start("child", {'x':'X', 'y':'Y'})
        self.assertEquals("child", el.tag)
        self.assertEquals({'x':'X', 'y':'Y'}, el.attrib)
        builder.data("CHILDTEXT")
        el = builder.end("child")
        self.assertEquals("child", el.tag)
        self.assertEquals({'x':'X', 'y':'Y'}, el.attrib)
        self.assertEquals("CHILDTEXT", el.text)
        self.assertEquals(None, el.tail)
        builder.data("CHILDTAIL")
        root = builder.end("root")

        self.assertEquals("root", root.tag)
        self.assertEquals("ROOTTEXT", root.text)
        self.assertEquals("CHILDTEXT", root[0].text)
        self.assertEquals("CHILDTAIL", root[0].tail)

    def test_treebuilder_target(self):
        parser = self.etree.XMLParser(target=self.etree.TreeBuilder())
        parser.feed('<root>ROOTTEXT<child>CHILDTEXT</child>CHILDTAIL</root>')
        root = parser.close()

        self.assertEquals("root", root.tag)
        self.assertEquals("ROOTTEXT", root.text)
        self.assertEquals("CHILDTEXT", root[0].text)
        self.assertEquals("CHILDTAIL", root[0].tail)

    # helper methods

    def _writeElement(self, element, encoding='us-ascii'):
        """Write out element for comparison.
        """
        data = self.etree.tostring(element, encoding=encoding)
        if encoding != 'us-ascii':
            data = unicode(data, encoding)
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
        if encoding != 'us-ascii':
            data = unicode(data, encoding)
        return canonicalize(data)

    def assertXML(self, expected, element, encoding='us-ascii'):
        """Writes element out and checks whether it is expected.

        Does this two ways; once using StringIO, once using a real file.
        """
        self.assertEquals(expected, self._writeElement(element, encoding))
        self.assertEquals(expected, self._writeElementFile(element, encoding))

    def assertEncodingDeclaration(self, result, encoding):
        "Checks if the result XML byte string specifies the encoding."
        has_encoding = re.compile(r"<\?xml[^>]+ encoding=[\"']([^\"']+)[\"']").match
        self.assert_(has_encoding(result))
        result_encoding = has_encoding(result).group(1)
        self.assertEquals(result_encoding.upper(), encoding.upper())
        
    def _rootstring(self, tree):
        return self.etree.tostring(tree.getroot()).replace(' ', '').replace('\n', '')

    def _check_element_tree(self, tree):
        self._check_element(tree.getroot())
        
    def _check_element(self, element):
        self.assert_(hasattr(element, 'tag'))
        self.assert_(hasattr(element, 'attrib'))
        self.assert_(hasattr(element, 'text'))
        self.assert_(hasattr(element, 'tail'))
        self._check_string(element.tag)
        self._check_mapping(element.attrib)
        if element.text != None:
            self._check_string(element.text)
        if element.tail != None:
            self._check_string(element.tail)
        
    def _check_string(self, string):
        len(string)
        for char in string:
            self.assertEquals(1, len(char))
        new_string = string + ""
        new_string = string + " "
        string[:0]

    def _check_mapping(self, mapping):
        len(mapping)
        keys = mapping.keys()
        items = mapping.items()
        for key in keys:
            item = mapping[key]
        mapping["key"] = "value"
        self.assertEquals("value", mapping["key"])


if etree:
    class ETreeTestCase(ETreeTestCaseBase):
        etree = etree

if ElementTree:
    class ElementTreeTestCase(ETreeTestCaseBase):
        etree = ElementTree

if cElementTree:
    class CElementTreeTestCase(ETreeTestCaseBase):
        etree = cElementTree

def test_suite():
    suite = unittest.TestSuite()
    if etree:
        suite.addTests([unittest.makeSuite(ETreeTestCase)])
    if ElementTree:
        suite.addTests([unittest.makeSuite(ElementTreeTestCase)])
    if cElementTree:
        suite.addTests([unittest.makeSuite(CElementTreeTestCase)])
    return suite

if __name__ == '__main__':
    print 'to test use test.py %s' % __file__
