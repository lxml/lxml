import unittest

from lxml.etree import Element, ElementTree, SubElement, XML
from StringIO import StringIO
import os, shutil, tempfile

class ETreeTestCase(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self._temp_dir)

    def getTestFilePath(self, name):
        return os.path.join(self._temp_dir, name)
    
    def test_element(self):
        for i in range(10):
            e = Element('foo')

    def test_tree(self):

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
        if depth == 0:
            return
        for i in range(children):
            new_element = Element('element_%s_%s' % (depth, i))
            self.buildNodes(new_element, children, depth - 1)
            element.append(new_element)

    def test_simple(self):
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
        root = Element('root')
        SubElement(root, 'one')
        SubElement(root, 'two')
        SubElement(root, 'three')
        self.assertEquals(3, len(root))
        self.assertEquals('one', root[0].tag)
        self.assertEquals('two', root[1].tag)
        self.assertEquals('three', root[2].tag)
        
    def test_element_indexing_with_text(self):
        f = StringIO('<doc>Test<one>One</one></doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals(1, len(root))
        self.assertEquals('one', root[0].tag)
        self.assertRaises(IndexError, root.__getitem__, 1)
        
    def test_element_indexing_with_text2(self):
        f = StringIO('<doc><one>One</one><two>Two</two>hm<three>Three</three></doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals(3, len(root))
        self.assertEquals('one', root[0].tag)
        self.assertEquals('two', root[1].tag)
        self.assertEquals('three', root[2].tag)

    def test_element_indexing_only_text(self):
        f = StringIO('<doc>Test</doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals(0, len(root))

    def test_elementtree(self):
        f = StringIO('<doc><one>One</one><two>Two</two></doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals(2, len(root))
        self.assertEquals('one', root[0].tag)
        self.assertEquals('two', root[1].tag)

    def test_text(self):
        f = StringIO('<doc>This is a text</doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals('This is a text', root.text)

    def test_text_empty(self):
        f = StringIO('<doc></doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals(None, root.text)

    def test_text_other(self):
        f = StringIO('<doc><one>One</one></doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals(None, root.text)
        self.assertEquals('One', root[0].text)

    def test_tail(self):
        f = StringIO('<doc>This is <i>mixed</i> content.</doc>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals(1, len(root))
        self.assertEquals('This is ', root.text)
        self.assertEquals(None, root.tail)
        self.assertEquals('mixed', root[0].text)
        self.assertEquals(' content.', root[0].tail)

    def test_ElementTree(self):
        el = Element('hoi')
        doc = ElementTree(el)
        root = doc.getroot()
        self.assertEquals(None, root.text)
        self.assertEquals('hoi', root.tag)

    def test_attributes(self):
        f = StringIO('<doc one="One" two="Two"/>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals('One', root.attrib['one'])
        self.assertEquals('Two', root.attrib['two'])
        self.assertRaises(KeyError, root.attrib.__getitem__, 'three')  

    def test_attributes2(self):
        f = StringIO('<doc one="One" two="Two"/>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals('One', root.attrib.get('one'))
        self.assertEquals('Two', root.attrib.get('two'))
        self.assertEquals(None, root.attrib.get('three'))
        self.assertEquals('foo', root.attrib.get('three', 'foo'))

    def test_attributes3(self):
        f = StringIO('<doc one="One" two="Two"/>')
        doc = ElementTree(file=f)
        root = doc.getroot()
        self.assertEquals('One', root.get('one'))
        self.assertEquals('Two', root.get('two'))
        self.assertEquals(None, root.get('three'))
        self.assertEquals('foo', root.get('three', 'foo'))

    def test_attribute_keys(self):
        root = XML('<doc alpha="Alpha" beta="Beta" gamma="Gamma"/>')
        keys = root.attrib.keys()
        keys.sort()
        self.assertEquals(['alpha', 'beta', 'gamma'], keys)

    def test_attribute_keys2(self):
        root = XML('<doc alpha="Alpha" beta="Beta" gamma="Gamma"/>')
        keys = root.keys()
        keys.sort()
        self.assertEquals(['alpha', 'beta', 'gamma'], keys)

    def test_attribute_values(self):
        root = XML('<doc alpha="Alpha" beta="Beta" gamma="Gamma"/>')
        values = root.attrib.values()
        values.sort()
        self.assertEquals(['Alpha', 'Beta', 'Gamma'], values)

    def test_attribute_items(self):
        root = XML('<doc alpha="Alpha" beta="Beta" gamma="Gamma"/>')
        items = root.attrib.items()
        items.sort()
        self.assertEquals([
            ('alpha', 'Alpha'),
            ('beta', 'Beta'),
            ('gamma', 'Gamma'),
            ], 
            items)

    def test_XML(self):
        root = XML('<doc>This is a text.</doc>')
        self.assertEquals(0, len(root))
        self.assertEquals('This is a text.', root.text)

    def test_iteration(self):
        root = XML('<doc><one/><two>Two</two>Hm<three/></doc>')
        result = []
        for el in root:
            result.append(el.tag)
        self.assertEquals(['one', 'two', 'three'], result)

    def test_iteration2(self):
        root = XML('<doc></doc>')
        result = []
        for el in root:
            result.append(el.tag)
        self.assertEquals([], result)

    def test_iteration3(self):
        root = XML('<doc>Text</doc>')
        result = []
        for el in root:
            result.append(el.tag)
        self.assertEquals([], result)
        
    def test_attribute_iterator(self):
        root = XML('<doc alpha="Alpha" beta="Beta" gamma="Gamma" />')
        result = []
        for key in root.attrib:
            result.append(key)
        result.sort()
        self.assertEquals(['alpha', 'beta', 'gamma'], result)


    def test_element_with_attributes(self):
        el = Element('tag', {'foo':'Foo', 'bar':'Bar'})
        self.assertEquals('Foo', el.attrib['foo'])
        self.assertEquals('Bar', el.attrib['bar'])

    def test_subelement_with_attributes(self):
        el = Element('tag')
        SubElement(el, 'foo', baz="Baz")
        self.assertEquals("Baz", el[0].attrib['baz'])
        
    # could trigger a crash in the past
    def test_write(self):
        for i in range(10):
            f = StringIO() 
            root = XML('<doc%s>This is a test.</doc%s>' % (i, i))
            tree = ElementTree(element=root)
            tree.write(f)
            data = f.getvalue()
            self.assertEquals(
                '<?xml version="1.0"?>\n<doc%s>This is a test.</doc%s>\n' % (i, i),
                data)

    # this could trigger a crash, apparently because the document
    # reference was prematurely garbage collected
    def test_crash(self):
        element = Element('tag')
        for i in range(10):
            element.attrib['key'] = 'value'
            value = element.attrib['key']
            self.assertEquals(value, 'value')
            
    # from doctest; for some reason this caused crashes too
    def test_write_ElementTreeDoctest(self):
        f = StringIO()
        for i in range(10):
            element = Element('tag%s' % i)
            self._check_element(element)
            tree = ElementTree(element)
            tree.write(f)
            self._check_element_tree(tree)

##     def test_subelement_reference(self):
##         el = Element('foo')
##         el2 = SubElement(el, 'bar')
##         el3 = SubElement(el2, 'baz')

##         al = Element('foo2')
##         al2 = SubElement(al, 'bar2')
##         al3 = SubElement(al2, 'baz2')

##         # now move al2 into el
##         el.append(al2)

##         # now change al3 directly
##         al3.text = 'baz2-modified'

##         # it should have changed through this route too
##         self.assertEquals(
##             'baz2-modified',
##             el[1][0].text)
        
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

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeTestCase)])
    return suite

if __name__ == '__main__':
    unittest.main()
