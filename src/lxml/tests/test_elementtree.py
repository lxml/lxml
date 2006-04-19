# -*- coding: UTF-8 -*-

"""
Tests for the ElementTree API

Only test cases that apply equally well to etree and ElementTree
belong here. Note that there is a second test module called test_io.py
for IO related test cases.
"""

import unittest, doctest
import os, shutil, tempfile, copy

from common_imports import StringIO, etree, ElementTree, HelperTestCase, fileInTestDir, canonicalize

class ETreeTestCaseBase(unittest.TestCase):
    etree = None
    
    def setUp(self):
        self._temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self._temp_dir)

    def getTestFilePath(self, name):
        return os.path.join(self._temp_dir, name)
    
    def test_element(self):
        for i in range(10):
            e = self.etree.Element('foo')

    def test_tree(self):
        Element = self.etree.Element
        ElementTree = self.etree.ElementTree
    
        element = Element('top')
        tree = ElementTree(element)
        self.buildNodes(element, 10, 3)
        f = open(self.getTestFilePath('testdump.xml'), 'w')
        tree.write(f, 'UTF-8')
        f.close()
        f = open(self.getTestFilePath('testdump.xml'), 'r')
        tree = ElementTree(file=f)
        f.close()
        f = open(self.getTestFilePath('testdump2.xml'), 'w')
        tree.write(f, 'UTF-8')
        f.close()
        f = open(self.getTestFilePath('testdump.xml'), 'r')
        data1 = f.read()
        f.close()
        f = open(self.getTestFilePath('testdump2.xml'), 'r')
        data2 = f.read()
        f.close()
        self.assertEquals(data1, data2)
        
    def buildNodes(self, element, children, depth):
        Element = self.etree.Element
        
        if depth == 0:
            return
        for i in range(children):
            new_element = Element('element_%s_%s' % (depth, i))
            self.buildNodes(new_element, children, depth - 1)
            element.append(new_element)

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
        self.assertRaises(IndexError, root.__getitem__, 3)

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
        
    def test_element_indexing_with_text(self):
        ElementTree = self.etree.ElementTree
        
        f = StringIO('<doc>Test<one>One</one></doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals(1, len(root))
        self.assertEquals('one', root[0].tag)
        self.assertRaises(IndexError, root.__getitem__, 1)
        
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
        self.assertRaises(IndexError, a.__getitem__, -4)
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
        self.assertRaises(KeyError, root.attrib.__getitem__, 'three')  

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
        
        root = XML('<foo bar="Bar" xmlns:ns="http://ns.codespeak.net/test" ns:baz="Baz" />')
        # XXX hope this is not dependent on unpredictable attribute order
        self.assertEquals(
            "{'{http://ns.codespeak.net/test}baz': 'Baz', 'bar': 'Bar'}",
            str(root.attrib))

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
            "warn1"    : root[3]
            }
        self.assertEquals(dic, expected)

    def test_fromstring(self):
        fromstring = self.etree.fromstring

        root = fromstring('<doc>This is a text.</doc>')
        self.assertEquals(0, len(root))
        self.assertEquals('This is a text.', root.text)

    def test_iselement(self):
        iselement = self.etree.iselement
        Element = self.etree.Element
        ElementTree = self.etree.ElementTree
        XML = self.etree.XML
        Comment = self.etree.Comment
        
        el = Element('hoi')
        self.assert_(iselement(el))

        el2 = XML('<foo/>')
        self.assert_(iselement(el2))

        tree = ElementTree(element=Element('dag'))
        self.assert_(not iselement(tree))
        self.assert_(iselement(tree.getroot()))

        c = Comment('test')
        self.assert_(iselement(c))
        
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

        try:
            reversed(())
        except NameError:
            # before Python 2.4
            return

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

    def test_element_with_attributes(self):
        Element = self.etree.Element
        
        el = Element('tag', {'foo':'Foo', 'bar':'Bar'})
        self.assertEquals('Foo', el.attrib['foo'])
        self.assertEquals('Bar', el.attrib['bar'])

    def test_subelement_with_attributes(self):
        Element =  self.etree.Element
        SubElement = self.etree.SubElement
        
        el = Element('tag')
        SubElement(el, 'foo', baz="Baz")
        self.assertEquals("Baz", el[0].attrib['baz'])
        
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
        self.assertXML(
            '<a><!-- foo --></a>',
            a)
        
    def test_comment_whitespace(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        Comment = self.etree.Comment

        a = Element('a')
        a.append(Comment(' foo  '))
        self.assertXML(
            '<a><!--  foo   --></a>',
            a)
        
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
        
    def test_setitem_indexerror(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')

        self.assertRaises(IndexError, a.__setitem__, 1, Element('c'))

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
        
    def test_getchildren(self):
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
            list(e.getiterator('a'))) 

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
        self.assertRaises(KeyError, a.attrib.__getitem__, 'foo')

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

    def test_delslice_tail(self):
        ElementTree = self.etree.ElementTree
        f = StringIO('<a><b></b>B2<c></c>C2<d></d>D2<e></e>E2</a>')
        doc = ElementTree(file=f)
        a = doc.getroot()
        del a[1:3]
        self.assertXML(
            '<a><b></b>B2<e></e>E2</a>',
            a)

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
        self.assertXML(
            '<a xmlns:ns0="%s" xmlns:ns1="%s" ns0:foo="Foo" ns1:bar="Bar"></a>' % (ns, ns2),
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

    def test_tostring_none(self):
        tostring = self.etree.tostring
        self.assertRaises(AssertionError, self.etree.tostring, None)
        
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
        
    def test_encoding(self):
        ElementTree = self.etree.ElementTree
        Element = self.etree.Element

        a = Element('a')
        a.text = u'Søk på nettet'
        self.assertXML(
            u'<a>Søk på nettet</a>'.encode('UTF-8'),
            a)

    def test_encoding2(self):
        ElementTree = self.etree.ElementTree
        Element = self.etree.Element

        a = Element('a')
        a.text = u'Søk på nettet'
        self.assertXML(
            u'<a>Søk på nettet</a>'.encode('UTF-8'),
            a, 'UTF-8')
        
    def test_encoding3(self):
        ElementTree = self.etree.ElementTree
        Element = self.etree.Element

        a = Element('a')
        a.text = u'Søk på nettet'
        
        f = StringIO()
        tree = ElementTree(element=a)
        tree.write(f, 'UTF-8')
        data = f.getvalue()

        # XXX prologue generation seems to be inconsistent between libraries..
        xml = u'<a>Søk på nettet</a>'.encode('UTF-8')
        prologue = u'<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n'.encode('UTF-8')
        self.assert_(data in [xml, prologue + xml])

##     # ignore wrong (left-over?) encoding declaration in unicode strings
##     def _test_wrong_unicode_encoding(self):
##         XML = self.etree.XML

##         test_utf = u'<?xml version=\'1.0\' encoding=\'iso-8859-1\'?><a>Søk på nettet</a>'
##         parsed = XML(test_utf)
##         self.assertXML(
##             u'<a>Søk på nettet</a>'.encode('UTF-8'),
##             parsed, 'UTF-8')
        
    def test_encoding_default_encoding(self):
        ElementTree = self.etree.ElementTree
        Element = self.etree.Element

        a = Element('a')
        a.text = u'Søk på nettet'
        
        f = StringIO()
        tree = ElementTree(element=a)
        tree.write(f)
        data = f.getvalue()
        self.assertEquals(
            '<a>S&#248;k p&#229; nettet</a>',
            data)

    def test_encoding_tostring(self):
        Element = self.etree.Element
        tostring = self.etree.tostring

        # XXX prologue generation seems to be inconsistent between libraries..
        xml = u'<a>Søk på nettet</a>'.encode('UTF-8')
        prologue = u'<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n'.encode('UTF-8')
        
        a = Element('a')
        a.text = u'Søk på nettet'
        self.assert_(tostring(a, 'UTF-8') in [xml, prologue + xml])
        
    def test_encoding_tostring_sub(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        tostring = self.etree.tostring

        a = Element('a')
        b = SubElement(a, 'b')
        b.text = u'Søk på nettet'

        # XXX prologue generation seems to be inconsistent between libraries..
        xml = u'<b>Søk på nettet</b>'.encode('UTF-8')
        prologue = u'<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n'.encode('UTF-8')
        self.assert_(tostring(b, 'UTF-8') in [xml, prologue + xml])

    def test_encoding_tostring_sub_tail(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        tostring = self.etree.tostring

        a = Element('a')
        b = SubElement(a, 'b')
        b.text = u'Søk på nettet'
        b.tail = u'Søk'
        xml = u'<b>Søk på nettet</b>Søk'.encode('UTF-8')
        prologue = u'<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n'.encode('UTF-8')
        self.assert_(tostring(b, 'UTF-8') in [xml, prologue + xml])
        
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

        # the same, just hex versus decimal
        expected = '<b>S&#248;k p&#229; nettet</b>'
        expected2 = '<b>S&#xF8;k p&#xE5; nettet</b>'
        self.assert_(tostring(b) in [expected, expected2])

    def test_deepcopy(self):
        Element = self.etree.Element
        
        a = Element('a')
        a.text = 'Foo'

        b = copy.deepcopy(a)
        self.assertEquals('Foo', b.text)
        
        b.text = 'Bar'
        self.assertEquals('Bar', b.text)
        self.assertEquals('Foo', a.text)

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
        
    def test_element_boolean(self):
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

    def _writeElement(self, element, encoding='us-ascii'):
        """Write out element for comparison.
        """
        ElementTree = self.etree.ElementTree
        f = StringIO()
        tree = ElementTree(element=element)
        tree.write(f, encoding)
        data = f.getvalue()
        return canonicalize(data)

    def _writeElementFile(self, element, encoding='us-ascii'):
        """Write out element for comparison, using real file.
        """
        ElementTree = self.etree.ElementTree
        handle, filename = tempfile.mkstemp()
        f = open(filename, 'wb')
        tree = ElementTree(element=element)
        tree.write(f, encoding)
        f.close()
        f = open(filename, 'rb')
        data = f.read()
        f.close()
        os.close(handle)
        os.remove(filename)
        return canonicalize(data)

    def assertXML(self, expected, element, encoding='us-ascii'):
        """Writes element out and checks whether it is expected.

        Does this two ways; once using StringIO, once using a real file.
        """
        self.assertEquals(expected, self._writeElement(element, encoding))
        self.assertEquals(expected, self._writeElementFile(element, encoding))
        
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


class ETreeTestCase(ETreeTestCaseBase):
    etree = etree

if ElementTree:
    class ElementTreeTestCase(ETreeTestCaseBase):
        etree = ElementTree

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeTestCase)])
    if ElementTree:
        suite.addTests([unittest.makeSuite(ElementTreeTestCase)])
    suite.addTests(
        [doctest.DocFileSuite('../../../doc/api.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
