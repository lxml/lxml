import unittest
from lxml.elementtree import Element, SubElement, ElementTree, XML
from StringIO import StringIO

class ElementTreeTestCase(unittest.TestCase):
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

    def test_XML(self):
        root = XML('<doc>This is a text.</doc>')
        self.assertEquals(0, len(root))
        self.assertEquals('This is a text.', root.text)

    def test_ElementTree(self):
        el = Element('hoi')
        doc = ElementTree(el)
        root = doc.getroot()
        self.assertEquals(None, root.text)
        self.assertEquals('hoi', root.tag)
       
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

    def test_attribute_iterator(self):
        root = XML('<doc alpha="Alpha" beta="Beta" gamma="Gamma" />')
        result = []
        for key in root.attrib:
            result.append(key)
        result.sort()
        self.assertEquals(['alpha', 'beta', 'gamma'], result)
        
    def test_attribute_set(self):
        root = XML('<doc/>')
        root.attrib['foo'] = 'Foo'
        self.assertEquals(
            'Foo', root.attrib['foo'])
        
    def test_attribute_items(self):
        root = XML('<doc alpha="Alpha" beta="Beta" gamma="Gamma"/>')
        items = root.items()
        items.sort()
        self.assertEquals([
            ('alpha', 'Alpha'),
            ('beta', 'Beta'),
            ('gamma', 'Gamma'),
            ], 
            items)

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

# crashes..
    def test_write(self):
        for i in range(1000):
            #print "start of test write", i
            f = StringIO()
            #print "create new element"
            root = XML('<doc%s>This is a test.</doc%s>' % (i, i))
            #print "stuff into tree"
            tree = ElementTree(element=root)
            #print "write tree"
            tree.write(f)
            #print "getting value of tree"
            data = f.getvalue()
            self.assertEquals(
                '<?xml version="1.0"?>\n<doc%s>This is a test.</doc%s>\n' % (i, i),
                data)
            #print "done"

    # this could trigger a crash, apparently because the document
    # reference was prematurely garbage collected
    def test_crash(self):
        element = Element('tag')
        for i in range(10):
            element.attrib['key'] = 'value'
            value = element.attrib['key']
            self.assertEquals(value, 'value')
            
    # from doctest; for some reason this fails after
    # test_write is executed; the ElementTree(element) factory causes
    # some form of hanging/segfault behavior when check element
    def test_write2_ElementTreeDoctest(self):
        f = StringIO()
        for i in range(100):
            #print "create element", i
            element = Element('tag%s' % i)
            #print "check element", i
            self._check_element(element)
            #print "create tree", i
            tree = ElementTree(element)
            tree.write(f)
            #print "check tree", i
            self._check_element_tree(tree)
            #print "done", i
            
    def _check_element_tree(self, tree):
        self._check_element(tree.getroot())
        
    def _check_element(self, element):
        #print "checking attrs"
        self.assert_(hasattr(element, 'tag'))
        self.assert_(hasattr(element, 'attrib'))
        self.assert_(hasattr(element, 'text'))
        self.assert_(hasattr(element, 'tail'))
        #print "checking tag string"
        self._check_string(element.tag)
        #print "checking mapping"
        self._check_mapping(element.attrib)
        #print "checking text"
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
    suite.addTests([unittest.makeSuite(ElementTreeTestCase)])
    return suite

if __name__ == '__main__':
    unittest.main()
    
