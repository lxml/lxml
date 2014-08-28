# -*- coding: utf-8 -*-

"""
Tests specific to the extended etree API

Tests that apply to the general ElementTree API should go into
test_elementtree
"""

import os.path
import unittest
import copy
import sys
import re
import gc
import operator
import tempfile
import zlib
import gzip

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

from common_imports import etree, StringIO, BytesIO, HelperTestCase
from common_imports import fileInTestDir, fileUrlInTestDir, read_file, path2url
from common_imports import SillyFileLike, LargeFileLikeUnicode, doctest, make_doctest
from common_imports import canonicalize, sorted, _str, _bytes

print("")
print("TESTED VERSION: %s" % etree.__version__)
print("    Python:           " + repr(sys.version_info))
print("    lxml.etree:       " + repr(etree.LXML_VERSION))
print("    libxml used:      " + repr(etree.LIBXML_VERSION))
print("    libxml compiled:  " + repr(etree.LIBXML_COMPILED_VERSION))
print("    libxslt used:     " + repr(etree.LIBXSLT_VERSION))
print("    libxslt compiled: " + repr(etree.LIBXSLT_COMPILED_VERSION))
print("")

try:
    _unicode = unicode
except NameError:
    # Python 3
    _unicode = str

class ETreeOnlyTestCase(HelperTestCase):
    """Tests only for etree, not ElementTree"""
    etree = etree

    def test_version(self):
        self.assertTrue(isinstance(etree.__version__, _unicode))
        self.assertTrue(isinstance(etree.LXML_VERSION, tuple))
        self.assertEqual(len(etree.LXML_VERSION), 4)
        self.assertTrue(isinstance(etree.LXML_VERSION[0], int))
        self.assertTrue(isinstance(etree.LXML_VERSION[1], int))
        self.assertTrue(isinstance(etree.LXML_VERSION[2], int))
        self.assertTrue(isinstance(etree.LXML_VERSION[3], int))
        self.assertTrue(etree.__version__.startswith(
            str(etree.LXML_VERSION[0])))

    def test_c_api(self):
        if hasattr(self.etree, '__pyx_capi__'):
            # newer Pyrex compatible C-API
            self.assertTrue(isinstance(self.etree.__pyx_capi__, dict))
            self.assertTrue(len(self.etree.__pyx_capi__) > 0)
        else:
            # older C-API mechanism
            self.assertTrue(hasattr(self.etree, '_import_c_api'))

    def test_element_names(self):
        Element = self.etree.Element
        el = Element('name')
        self.assertEqual(el.tag, 'name')
        el = Element('{}name')
        self.assertEqual(el.tag, 'name')

    def test_element_name_empty(self):
        Element = self.etree.Element
        el = Element('name')
        self.assertRaises(ValueError, Element, '{}')
        self.assertRaises(ValueError, setattr, el, 'tag', '{}')

        self.assertRaises(ValueError, Element, '{test}')
        self.assertRaises(ValueError, setattr, el, 'tag', '{test}')

    def test_element_name_colon(self):
        Element = self.etree.Element
        self.assertRaises(ValueError, Element, 'p:name')
        self.assertRaises(ValueError, Element, '{test}p:name')

        el = Element('name')
        self.assertRaises(ValueError, setattr, el, 'tag', 'p:name')

    def test_element_name_quote(self):
        Element = self.etree.Element
        self.assertRaises(ValueError, Element, "p'name")
        self.assertRaises(ValueError, Element, 'p"name')

        self.assertRaises(ValueError, Element, "{test}p'name")
        self.assertRaises(ValueError, Element, '{test}p"name')

        el = Element('name')
        self.assertRaises(ValueError, setattr, el, 'tag', "p'name")
        self.assertRaises(ValueError, setattr, el, 'tag', 'p"name')

    def test_element_name_space(self):
        Element = self.etree.Element
        self.assertRaises(ValueError, Element, ' name ')
        self.assertRaises(ValueError, Element, 'na me')
        self.assertRaises(ValueError, Element, '{test} name')

        el = Element('name')
        self.assertRaises(ValueError, setattr, el, 'tag', ' name ')

    def test_subelement_name_empty(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        el = Element('name')
        self.assertRaises(ValueError, SubElement, el, '{}')
        self.assertRaises(ValueError, SubElement, el, '{test}')

    def test_subelement_name_colon(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        el = Element('name')
        self.assertRaises(ValueError, SubElement, el, 'p:name')
        self.assertRaises(ValueError, SubElement, el, '{test}p:name')

    def test_subelement_name_quote(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        el = Element('name')
        self.assertRaises(ValueError, SubElement, el, "p'name")
        self.assertRaises(ValueError, SubElement, el, "{test}p'name")

        self.assertRaises(ValueError, SubElement, el, 'p"name')
        self.assertRaises(ValueError, SubElement, el, '{test}p"name')

    def test_subelement_name_space(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        el = Element('name')
        self.assertRaises(ValueError, SubElement, el, ' name ')
        self.assertRaises(ValueError, SubElement, el, 'na me')
        self.assertRaises(ValueError, SubElement, el, '{test} name')

    def test_subelement_attribute_invalid(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        el = Element('name')
        self.assertRaises(ValueError, SubElement, el, 'name', {'a b c' : 'abc'})
        self.assertRaises(ValueError, SubElement, el, 'name', {'a' : 'a\0\n'})
        self.assertEqual(0, len(el))

    def test_qname_empty(self):
        QName = self.etree.QName
        self.assertRaises(ValueError, QName, '')
        self.assertRaises(ValueError, QName, 'test', '')

    def test_qname_colon(self):
        QName = self.etree.QName
        self.assertRaises(ValueError, QName, 'p:name')
        self.assertRaises(ValueError, QName, 'test', 'p:name')

    def test_qname_space(self):
        QName = self.etree.QName
        self.assertRaises(ValueError, QName, ' name ')
        self.assertRaises(ValueError, QName, 'na me')
        self.assertRaises(ValueError, QName, 'test', ' name')

    def test_qname_namespace_localname(self):
        # ET doesn't have namespace/localname properties on QNames
        QName = self.etree.QName
        namespace, localname = 'http://myns', 'a'
        qname = QName(namespace, localname)
        self.assertEqual(namespace, qname.namespace)
        self.assertEqual(localname, qname.localname)

    def test_qname_element(self):
        # ET doesn't have namespace/localname properties on QNames
        QName = self.etree.QName
        qname1 = QName('http://myns', 'a')
        a = self.etree.Element(qname1, nsmap={'p' : 'http://myns'})

        qname2 = QName(a)
        self.assertEqual(a.tag, qname1.text)
        self.assertEqual(qname1.text, qname2.text)
        self.assertEqual(qname1, qname2)

    def test_qname_text_resolve(self):
        # ET doesn't resove QNames as text values
        etree = self.etree
        qname = etree.QName('http://myns', 'a')
        a = etree.Element(qname, nsmap={'p' : 'http://myns'})
        a.text = qname

        self.assertEqual("p:a", a.text)

    def test_nsmap_prefix_invalid(self):
        etree = self.etree
        self.assertRaises(ValueError,
                          etree.Element, "root", nsmap={'"' : 'testns'})
        self.assertRaises(ValueError,
                          etree.Element, "root", nsmap={'&' : 'testns'})
        self.assertRaises(ValueError,
                          etree.Element, "root", nsmap={'a:b' : 'testns'})

    def test_attribute_has_key(self):
        # ET in Py 3.x has no "attrib.has_key()" method
        XML = self.etree.XML

        root = XML(_bytes('<foo bar="Bar" xmlns:ns="http://ns.codespeak.net/test" ns:baz="Baz" />'))
        self.assertEqual(
            True, root.attrib.has_key('bar'))
        self.assertEqual(
            False, root.attrib.has_key('baz'))
        self.assertEqual(
            False, root.attrib.has_key('hah'))
        self.assertEqual(
            True,
            root.attrib.has_key('{http://ns.codespeak.net/test}baz'))

    def test_attribute_set(self):
        Element = self.etree.Element
        root = Element("root")
        root.set("attr", "TEST")
        self.assertEqual("TEST", root.get("attr"))

    def test_attrib_and_keywords(self):
        Element = self.etree.Element

        root = Element("root")
        root.set("attr", "TEST")
        self.assertEqual("TEST", root.attrib["attr"])

        root2 = Element("root2", root.attrib, attr2='TOAST')
        self.assertEqual("TEST", root2.attrib["attr"])
        self.assertEqual("TOAST", root2.attrib["attr2"])
        self.assertEqual(None, root.attrib.get("attr2"))

    def test_attrib_order(self):
        Element = self.etree.Element

        keys = ["attr%d" % i for i in range(10)]
        values = ["TEST-%d" % i for i in range(10)]
        items = list(zip(keys, values))

        root = Element("root")
        for key, value in items:
            root.set(key, value)
        self.assertEqual(keys, root.attrib.keys())
        self.assertEqual(values, root.attrib.values())

        root2 = Element("root2", root.attrib,
                        attr_99='TOAST-1', attr_98='TOAST-2')
        self.assertEqual(['attr_98', 'attr_99'] + keys,
                         root2.attrib.keys())
        self.assertEqual(['TOAST-2', 'TOAST-1'] + values,
                         root2.attrib.values())

        self.assertEqual(keys, root.attrib.keys())
        self.assertEqual(values, root.attrib.values())

    def test_attribute_set_invalid(self):
        # ElementTree accepts arbitrary attribute values
        # lxml.etree allows only strings
        Element = self.etree.Element
        root = Element("root")
        self.assertRaises(TypeError, root.set, "newattr", 5)
        self.assertRaises(TypeError, root.set, "newattr", None)

    def test_strip_attributes(self):
        XML = self.etree.XML
        xml = _bytes('<test a="5" b="10" c="20"><x a="4" b="2"/></test>')

        root = XML(xml)
        self.etree.strip_attributes(root, 'a')
        self.assertEqual(_bytes('<test b="10" c="20"><x b="2"></x></test>'),
                          self._writeElement(root))

        root = XML(xml)
        self.etree.strip_attributes(root, 'b', 'c')
        self.assertEqual(_bytes('<test a="5"><x a="4"></x></test>'),
                          self._writeElement(root))

    def test_strip_attributes_ns(self):
        XML = self.etree.XML
        xml = _bytes('<test xmlns:n="http://test/ns" a="6" b="10" c="20" n:a="5"><x a="4" n:b="2"/></test>')

        root = XML(xml)
        self.etree.strip_attributes(root, 'a')
        self.assertEqual(
            _bytes('<test xmlns:n="http://test/ns" b="10" c="20" n:a="5"><x n:b="2"></x></test>'),
            self._writeElement(root))

        root = XML(xml)
        self.etree.strip_attributes(root, '{http://test/ns}a', 'c')
        self.assertEqual(
            _bytes('<test xmlns:n="http://test/ns" a="6" b="10"><x a="4" n:b="2"></x></test>'),
            self._writeElement(root))

        root = XML(xml)
        self.etree.strip_attributes(root, '{http://test/ns}*')
        self.assertEqual(
            _bytes('<test xmlns:n="http://test/ns" a="6" b="10" c="20"><x a="4"></x></test>'),
            self._writeElement(root))

    def test_strip_elements(self):
        XML = self.etree.XML
        xml = _bytes('<test><a><b><c/></b></a><x><a><b/><c/></a></x></test>')

        root = XML(xml)
        self.etree.strip_elements(root, 'a')
        self.assertEqual(_bytes('<test><x></x></test>'),
                          self._writeElement(root))

        root = XML(xml)
        self.etree.strip_elements(root, 'b', 'c', 'X', 'Y', 'Z')
        self.assertEqual(_bytes('<test><a></a><x><a></a></x></test>'),
                          self._writeElement(root))

        root = XML(xml)
        self.etree.strip_elements(root, 'c')
        self.assertEqual(_bytes('<test><a><b></b></a><x><a><b></b></a></x></test>'),
                          self._writeElement(root))

    def test_strip_elements_ns(self):
        XML = self.etree.XML
        xml = _bytes('<test>TEST<n:a xmlns:n="urn:a">A<b>B<c xmlns="urn:c"/>C</b>BT</n:a>AT<x>X<a>A<b xmlns="urn:a"/>BT<c xmlns="urn:x"/>CT</a>AT</x>XT</test>')

        root = XML(xml)
        self.etree.strip_elements(root, 'a')
        self.assertEqual(_bytes('<test>TEST<n:a xmlns:n="urn:a">A<b>B<c xmlns="urn:c"></c>C</b>BT</n:a>AT<x>X</x>XT</test>'),
                          self._writeElement(root))

        root = XML(xml)
        self.etree.strip_elements(root, '{urn:a}b', 'c')
        self.assertEqual(_bytes('<test>TEST<n:a xmlns:n="urn:a">A<b>B<c xmlns="urn:c"></c>C</b>BT</n:a>AT<x>X<a>A<c xmlns="urn:x"></c>CT</a>AT</x>XT</test>'),
                          self._writeElement(root))

        root = XML(xml)
        self.etree.strip_elements(root, '{urn:a}*', 'c')
        self.assertEqual(_bytes('<test>TEST<x>X<a>A<c xmlns="urn:x"></c>CT</a>AT</x>XT</test>'),
                          self._writeElement(root))

        root = XML(xml)
        self.etree.strip_elements(root, '{urn:a}*', 'c', with_tail=False)
        self.assertEqual(_bytes('<test>TESTAT<x>X<a>ABT<c xmlns="urn:x"></c>CT</a>AT</x>XT</test>'),
                          self._writeElement(root))

    def test_strip_tags(self):
        XML = self.etree.XML
        xml = _bytes('<test>TEST<a>A<b>B<c/>CT</b>BT</a>AT<x>X<a>A<b/>BT<c/>CT</a>AT</x>XT</test>')

        root = XML(xml)
        self.etree.strip_tags(root, 'a')
        self.assertEqual(_bytes('<test>TESTA<b>B<c></c>CT</b>BTAT<x>XA<b></b>BT<c></c>CTAT</x>XT</test>'),
                          self._writeElement(root))

        root = XML(xml)
        self.etree.strip_tags(root, 'b', 'c', 'X', 'Y', 'Z')
        self.assertEqual(_bytes('<test>TEST<a>ABCTBT</a>AT<x>X<a>ABTCT</a>AT</x>XT</test>'),
                          self._writeElement(root))

        root = XML(xml)
        self.etree.strip_tags(root, 'c')
        self.assertEqual(_bytes('<test>TEST<a>A<b>BCT</b>BT</a>AT<x>X<a>A<b></b>BTCT</a>AT</x>XT</test>'),
                          self._writeElement(root))

    def test_strip_tags_pi_comment(self):
        XML = self.etree.XML
        PI = self.etree.ProcessingInstruction
        Comment = self.etree.Comment
        xml = _bytes('<!--comment1-->\n<?PI1?>\n<test>TEST<!--comment2-->XT<?PI2?></test>\n<!--comment3-->\n<?PI1?>')

        root = XML(xml)
        self.etree.strip_tags(root, PI)
        self.assertEqual(_bytes('<!--comment1-->\n<?PI1?>\n<test>TEST<!--comment2-->XT</test>\n<!--comment3-->\n<?PI1?>'),
                          self._writeElement(root))

        root = XML(xml)
        self.etree.strip_tags(root, Comment)
        self.assertEqual(_bytes('<!--comment1-->\n<?PI1?>\n<test>TESTXT<?PI2?></test>\n<!--comment3-->\n<?PI1?>'),
                          self._writeElement(root))

        root = XML(xml)
        self.etree.strip_tags(root, PI, Comment)
        self.assertEqual(_bytes('<!--comment1-->\n<?PI1?>\n<test>TESTXT</test>\n<!--comment3-->\n<?PI1?>'),
                          self._writeElement(root))

        root = XML(xml)
        self.etree.strip_tags(root, Comment, PI)
        self.assertEqual(_bytes('<!--comment1-->\n<?PI1?>\n<test>TESTXT</test>\n<!--comment3-->\n<?PI1?>'),
                          self._writeElement(root))

    def test_strip_tags_pi_comment_all(self):
        XML = self.etree.XML
        ElementTree = self.etree.ElementTree
        PI = self.etree.ProcessingInstruction
        Comment = self.etree.Comment
        xml = _bytes('<!--comment1-->\n<?PI1?>\n<test>TEST<!--comment2-->XT<?PI2?></test>\n<!--comment3-->\n<?PI1?>')

        root = XML(xml)
        self.etree.strip_tags(ElementTree(root), PI)
        self.assertEqual(_bytes('<!--comment1-->\n<test>TEST<!--comment2-->XT</test>\n<!--comment3-->'),
                          self._writeElement(root))

        root = XML(xml)
        self.etree.strip_tags(ElementTree(root), Comment)
        self.assertEqual(_bytes('<?PI1?>\n<test>TESTXT<?PI2?></test>\n<?PI1?>'),
                          self._writeElement(root))

        root = XML(xml)
        self.etree.strip_tags(ElementTree(root), PI, Comment)
        self.assertEqual(_bytes('<test>TESTXT</test>'),
                          self._writeElement(root))

        root = XML(xml)
        self.etree.strip_tags(ElementTree(root), Comment, PI)
        self.assertEqual(_bytes('<test>TESTXT</test>'),
                          self._writeElement(root))

    def test_strip_tags_doc_style(self):
        XML = self.etree.XML
        xml = _bytes('''
        <div>
            <div>
                I like <strong>sheep</strong>.
                <br/>
                I like lots of <strong>sheep</strong>.
                <br/>
                Click <a href="http://www.sheep.com">here</a>
                 for <a href="http://www.sheep.com">those</a> sheep.
                <br/>
            </div>
        </div>
        '''.strip())

        root = XML(xml)
        self.etree.strip_tags(root, 'a')
        self.assertEqual(re.sub(_bytes('</?a[^>]*>'), _bytes(''), xml).replace(_bytes('<br/>'), _bytes('<br></br>')),
                          self._writeElement(root))

        root = XML(xml)
        self.etree.strip_tags(root, 'a', 'br')
        self.assertEqual(re.sub(_bytes('</?a[^>]*>'), _bytes(''),
                                 re.sub(_bytes('<br[^>]*>'), _bytes(''), xml)),
                          self._writeElement(root))

    def test_strip_tags_ns(self):
        XML = self.etree.XML
        xml = _bytes('<test>TEST<n:a xmlns:n="urn:a">A<b>B<c xmlns="urn:c"/>CT</b>BT</n:a>AT<x>X<a>A<b xmlns="urn:a"/>BT<c xmlns="urn:x"/>CT</a>AT</x>XT</test>')

        root = XML(xml)
        self.etree.strip_tags(root, 'a')
        self.assertEqual(_bytes('<test>TEST<n:a xmlns:n="urn:a">A<b>B<c xmlns="urn:c"></c>CT</b>BT</n:a>AT<x>XA<b xmlns="urn:a"></b>BT<c xmlns="urn:x"></c>CTAT</x>XT</test>'),
                          self._writeElement(root))

        root = XML(xml)
        self.etree.strip_tags(root, '{urn:a}b', 'c')
        self.assertEqual(_bytes('<test>TEST<n:a xmlns:n="urn:a">A<b>B<c xmlns="urn:c"></c>CT</b>BT</n:a>AT<x>X<a>ABT<c xmlns="urn:x"></c>CT</a>AT</x>XT</test>'),
                          self._writeElement(root))

        root = XML(xml)
        self.etree.strip_tags(root, '{urn:a}*', 'c')
        self.assertEqual(_bytes('<test>TESTA<b>B<c xmlns="urn:c"></c>CT</b>BTAT<x>X<a>ABT<c xmlns="urn:x"></c>CT</a>AT</x>XT</test>'),
                          self._writeElement(root))

    def test_strip_tags_and_remove(self):
        # previously crashed
        HTML = self.etree.HTML
        root = HTML(_bytes('<div><h1>title</h1> <b>foo</b> <p>boo</p></div>'))[0][0]
        self.assertEqual(_bytes('<div><h1>title</h1> <b>foo</b> <p>boo</p></div>'),
                          self.etree.tostring(root))
        self.etree.strip_tags(root, 'b')
        self.assertEqual(_bytes('<div><h1>title</h1> foo <p>boo</p></div>'),
                          self.etree.tostring(root))
        root.remove(root[0])
        self.assertEqual(_bytes('<div><p>boo</p></div>'),
                          self.etree.tostring(root))

    def test_pi(self):
        # lxml.etree separates target and text
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        ProcessingInstruction = self.etree.ProcessingInstruction

        a = Element('a')
        a.append(ProcessingInstruction('foo', 'some more text'))
        self.assertEqual(a[0].target, 'foo')
        self.assertEqual(a[0].text, 'some more text')

    def test_pi_parse(self):
        XML = self.etree.XML
        root = XML(_bytes("<test><?mypi my test ?></test>"))
        self.assertEqual(root[0].target, "mypi")
        self.assertEqual(root[0].text, "my test ")

    def test_pi_pseudo_attributes_get(self):
        XML = self.etree.XML
        root = XML(_bytes("<test><?mypi my='1' test=\" abc \" quotes=\"' '\" only names ?></test>"))
        self.assertEqual(root[0].target, "mypi")
        self.assertEqual(root[0].get('my'), "1")
        self.assertEqual(root[0].get('test'), " abc ")
        self.assertEqual(root[0].get('quotes'), "' '")
        self.assertEqual(root[0].get('only'), None)
        self.assertEqual(root[0].get('names'), None)
        self.assertEqual(root[0].get('nope'), None)

    def test_pi_pseudo_attributes_attrib(self):
        XML = self.etree.XML
        root = XML(_bytes("<test><?mypi my='1' test=\" abc \" quotes=\"' '\" only names ?></test>"))
        self.assertEqual(root[0].target, "mypi")
        self.assertEqual(root[0].attrib['my'], "1")
        self.assertEqual(root[0].attrib['test'], " abc ")
        self.assertEqual(root[0].attrib['quotes'], "' '")
        self.assertRaises(KeyError, root[0].attrib.__getitem__, 'only')
        self.assertRaises(KeyError, root[0].attrib.__getitem__, 'names')
        self.assertRaises(KeyError, root[0].attrib.__getitem__, 'nope')

    def test_deepcopy_pi(self):
        # previously caused a crash
        ProcessingInstruction = self.etree.ProcessingInstruction
        
        a = ProcessingInstruction("PI", "ONE")
        b = copy.deepcopy(a)
        b.text = "ANOTHER"

        self.assertEqual('ONE',     a.text)
        self.assertEqual('ANOTHER', b.text)

    def test_deepcopy_elementtree_pi(self):
        XML = self.etree.XML
        tostring = self.etree.tostring
        root = XML(_bytes("<?mypi my test ?><test/><!--comment -->"))
        tree1 = self.etree.ElementTree(root)
        self.assertEqual(_bytes("<?mypi my test ?><test/><!--comment -->"),
                          tostring(tree1))

        tree2 = copy.deepcopy(tree1)
        self.assertEqual(_bytes("<?mypi my test ?><test/><!--comment -->"),
                          tostring(tree2))

        root2 = copy.deepcopy(tree1.getroot())
        self.assertEqual(_bytes("<test/>"),
                          tostring(root2))

    def test_deepcopy_elementtree_dtd(self):
        XML = self.etree.XML
        tostring = self.etree.tostring
        xml = _bytes('<!DOCTYPE test [\n<!ENTITY entity "tasty">\n]>\n<test/>')
        root = XML(xml)
        tree1 = self.etree.ElementTree(root)
        self.assertEqual(xml, tostring(tree1))

        tree2 = copy.deepcopy(tree1)
        self.assertEqual(xml, tostring(tree2))

        root2 = copy.deepcopy(tree1.getroot())
        self.assertEqual(_bytes("<test/>"),
                          tostring(root2))

    def test_attribute_set(self):
        # ElementTree accepts arbitrary attribute values
        # lxml.etree allows only strings
        Element = self.etree.Element

        root = Element("root")
        root.set("attr", "TEST")
        self.assertEqual("TEST", root.get("attr"))
        self.assertRaises(TypeError, root.set, "newattr", 5)

    def test_parse_remove_comments(self):
        fromstring = self.etree.fromstring
        tostring = self.etree.tostring
        XMLParser = self.etree.XMLParser

        xml = _bytes('<a><!--A--><b><!-- B --><c/></b><!--C--></a>')
        parser = XMLParser(remove_comments=True)
        root = fromstring(xml, parser)
        self.assertEqual(
            _bytes('<a><b><c/></b></a>'),
            tostring(root))

    def test_parse_remove_pis(self):
        parse = self.etree.parse
        tostring = self.etree.tostring
        XMLParser = self.etree.XMLParser

        xml = _bytes('<?test?><a><?A?><b><?B?><c/></b><?C?></a><?tail?>')

        f = BytesIO(xml)
        tree = parse(f)
        self.assertEqual(
            xml,
            tostring(tree))

        parser = XMLParser(remove_pis=True)
        tree = parse(f, parser)
        self.assertEqual(
            _bytes('<a><b><c/></b></a>'),
            tostring(tree))

    def test_parse_parser_type_error(self):
        # ET raises IOError only
        parse = self.etree.parse
        self.assertRaises(TypeError, parse, 'notthere.xml', object())

    def test_iterparse_tree_comments(self):
        # ET removes comments
        iterparse = self.etree.iterparse
        tostring = self.etree.tostring

        f = BytesIO('<a><!--A--><b><!-- B --><c/></b><!--C--></a>')
        events = list(iterparse(f))
        root = events[-1][1]
        self.assertEqual(3, len(events))
        self.assertEqual(
            _bytes('<a><!--A--><b><!-- B --><c/></b><!--C--></a>'),
            tostring(root))

    def test_iterparse_comments(self):
        # ET removes comments
        iterparse = self.etree.iterparse
        tostring = self.etree.tostring

        def name(event, el):
            if event == 'comment':
                return el.text
            else:
                return el.tag

        f = BytesIO('<a><!--A--><b><!-- B --><c/></b><!--C--></a>')
        events = list(iterparse(f, events=('end', 'comment')))
        root = events[-1][1]
        self.assertEqual(6, len(events))
        self.assertEqual(['A', ' B ', 'c', 'b', 'C', 'a'],
                          [ name(*item) for item in events ])
        self.assertEqual(
            _bytes('<a><!--A--><b><!-- B --><c/></b><!--C--></a>'),
            tostring(root))

    def test_iterparse_pis(self):
        # ET removes pis
        iterparse = self.etree.iterparse
        tostring = self.etree.tostring
        ElementTree = self.etree.ElementTree

        def name(event, el):
            if event == 'pi':
                return (el.target, el.text)
            else:
                return el.tag

        f = BytesIO('<?pia a?><a><?pib b?><b><?pic c?><c/></b><?pid d?></a><?pie e?>')
        events = list(iterparse(f, events=('end', 'pi')))
        root = events[-2][1]
        self.assertEqual(8, len(events))
        self.assertEqual([('pia','a'), ('pib','b'), ('pic','c'), 'c', 'b',
                           ('pid','d'), 'a', ('pie','e')],
                          [ name(*item) for item in events ])
        self.assertEqual(
            _bytes('<?pia a?><a><?pib b?><b><?pic c?><c/></b><?pid d?></a><?pie e?>'),
            tostring(ElementTree(root)))

    def test_iterparse_remove_comments(self):
        iterparse = self.etree.iterparse
        tostring = self.etree.tostring

        f = BytesIO('<a><!--A--><b><!-- B --><c/></b><!--C--></a>')
        events = list(iterparse(f, remove_comments=True,
                                events=('end', 'comment')))
        root = events[-1][1]
        self.assertEqual(3, len(events))
        self.assertEqual(['c', 'b', 'a'],
                          [ el.tag for (event, el) in events ])
        self.assertEqual(
            _bytes('<a><b><c/></b></a>'),
            tostring(root))

    def test_iterparse_broken(self):
        iterparse = self.etree.iterparse
        f = BytesIO('<a><b><c/></a>')
        # ET raises ExpatError, lxml raises XMLSyntaxError
        self.assertRaises(self.etree.XMLSyntaxError, list, iterparse(f))

    def test_iterparse_broken_recover(self):
        iterparse = self.etree.iterparse
        f = BytesIO('<a><b><c/></a>')
        it = iterparse(f, events=('start', 'end'), recover=True)
        events = [(ev, el.tag) for ev, el in it]
        root = it.root
        self.assertTrue(root is not None)

        self.assertEqual(1, events.count(('start', 'a')))
        self.assertEqual(1, events.count(('end', 'a')))

        self.assertEqual(1, events.count(('start', 'b')))
        self.assertEqual(1, events.count(('end', 'b')))

        self.assertEqual(1, events.count(('start', 'c')))
        self.assertEqual(1, events.count(('end', 'c')))

    def test_iterparse_broken_multi_recover(self):
        iterparse = self.etree.iterparse
        f = BytesIO('<a><b><c/></d><b><c/></a></b>')
        it = iterparse(f, events=('start', 'end'), recover=True)
        events = [(ev, el.tag) for ev, el in it]
        root = it.root
        self.assertTrue(root is not None)

        self.assertEqual(1, events.count(('start', 'a')))
        self.assertEqual(1, events.count(('end', 'a')))

        self.assertEqual(2, events.count(('start', 'b')))
        self.assertEqual(2, events.count(('end', 'b')))

        self.assertEqual(2, events.count(('start', 'c')))
        self.assertEqual(2, events.count(('end', 'c')))

    def test_iterparse_strip(self):
        iterparse = self.etree.iterparse
        f = BytesIO("""
               <a>  \n \n  <b> b test </b>  \n

               \n\t <c> \n </c> </a>  \n """)
        iterator = iterparse(f, remove_blank_text=True)
        text = [ (element.text, element.tail)
                 for event, element in iterator ]
        self.assertEqual(
            [(" b test ", None), (" \n ", None), (None, None)],
            text)

    def test_iterparse_tag(self):
        iterparse = self.etree.iterparse
        f = BytesIO('<a><b><d/></b><c/></a>')

        iterator = iterparse(f, tag="b", events=('start', 'end'))
        events = list(iterator)
        root = iterator.root
        self.assertEqual(
            [('start', root[0]), ('end', root[0])],
            events)

    def test_iterparse_tag_all(self):
        iterparse = self.etree.iterparse
        f = BytesIO('<a><b><d/></b><c/></a>')

        iterator = iterparse(f, tag="*", events=('start', 'end'))
        events = list(iterator)
        self.assertEqual(
            8,
            len(events))

    def test_iterparse_tag_ns(self):
        iterparse = self.etree.iterparse
        f = BytesIO('<a xmlns="urn:test:1"><b><d/></b><c/></a>')

        iterator = iterparse(f, tag="{urn:test:1}b", events=('start', 'end'))
        events = list(iterator)
        root = iterator.root
        self.assertEqual(
            [('start', root[0]), ('end', root[0])],
            events)

    def test_iterparse_tag_ns_empty(self):
        iterparse = self.etree.iterparse
        f = BytesIO('<a><b><d/></b><c/></a>')
        iterator = iterparse(f, tag="{}b", events=('start', 'end'))
        events = list(iterator)
        root = iterator.root
        self.assertEqual(
            [('start', root[0]), ('end', root[0])],
            events)

        f = BytesIO('<a xmlns="urn:test:1"><b><d/></b><c/></a>')
        iterator = iterparse(f, tag="{}b", events=('start', 'end'))
        events = list(iterator)
        root = iterator.root
        self.assertEqual([], events)

    def test_iterparse_tag_ns_all(self):
        iterparse = self.etree.iterparse
        f = BytesIO('<a xmlns="urn:test:1"><b><d/></b><c/></a>')
        iterator = iterparse(f, tag="{urn:test:1}*", events=('start', 'end'))
        events = list(iterator)
        self.assertEqual(8, len(events))

    def test_iterparse_tag_ns_empty_all(self):
        iterparse = self.etree.iterparse
        f = BytesIO('<a xmlns="urn:test:1"><b><d/></b><c/></a>')
        iterator = iterparse(f, tag="{}*", events=('start', 'end'))
        events = list(iterator)
        self.assertEqual([], events)

        f = BytesIO('<a><b><d/></b><c/></a>')
        iterator = iterparse(f, tag="{}*", events=('start', 'end'))
        events = list(iterator)
        self.assertEqual(8, len(events))

    def test_iterparse_encoding_error(self):
        text = _str('Søk på nettet')
        wrong_declaration = "<?xml version='1.0' encoding='UTF-8'?>"
        xml_latin1 = (_str('%s<a>%s</a>') % (wrong_declaration, text)
                      ).encode('iso-8859-1')

        self.assertRaises(self.etree.ParseError,
                          list, self.etree.iterparse(BytesIO(xml_latin1)))

    def test_iterparse_encoding_8bit_override(self):
        text = _str('Søk på nettet', encoding="UTF-8")
        wrong_declaration = "<?xml version='1.0' encoding='UTF-8'?>"
        xml_latin1 = (_str('%s<a>%s</a>') % (wrong_declaration, text)
                      ).encode('iso-8859-1')

        iterator = self.etree.iterparse(BytesIO(xml_latin1),
                                        encoding="iso-8859-1")
        self.assertEqual(1, len(list(iterator)))

        a = iterator.root
        self.assertEqual(a.text, text)

    def test_iterparse_keep_cdata(self):
        tostring = self.etree.tostring
        f = BytesIO('<root><![CDATA[test]]></root>')
        context = self.etree.iterparse(f, strip_cdata=False)
        content = [ el.text for event,el in context ]

        self.assertEqual(['test'], content)
        self.assertEqual(_bytes('<root><![CDATA[test]]></root>'),
                          tostring(context.root))

    def test_parser_encoding_unknown(self):
        self.assertRaises(
            LookupError, self.etree.XMLParser, encoding="hopefully unknown")

    def test_parser_encoding(self):
        self.etree.XMLParser(encoding="ascii")
        self.etree.XMLParser(encoding="utf-8")
        self.etree.XMLParser(encoding="iso-8859-1")

    def test_feed_parser_recover(self):
        parser = self.etree.XMLParser(recover=True)

        parser.feed('<?xml version=')
        parser.feed('"1.0"?><ro')
        parser.feed('ot><')
        parser.feed('a test="works"')
        parser.feed('><othertag/></root') # <a> not closed!
        parser.feed('>')

        root = parser.close()

        self.assertEqual(root.tag, "root")
        self.assertEqual(len(root), 1)
        self.assertEqual(root[0].tag, "a")
        self.assertEqual(root[0].get("test"), "works")
        self.assertEqual(len(root[0]), 1)
        self.assertEqual(root[0][0].tag, "othertag")
        # FIXME: would be nice to get some errors logged ...
        #self.assertTrue(len(parser.error_log) > 0, "error log is empty")

    def test_elementtree_parser_target_type_error(self):
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
                return "DONE" # no Element!

        parser = self.etree.XMLParser(target=Target())
        tree = self.etree.ElementTree()

        self.assertRaises(TypeError,
                          tree.parse, BytesIO("<TAG/>"), parser=parser)
        self.assertEqual(["start", "end"], events)

    def test_parser_target_feed_exception(self):
        # ET doesn't call .close() on errors
        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append("start-" + tag)
            def end(self, tag):
                events.append("end-" + tag)
                if tag == 'a':
                    raise ValueError("dead and gone")
            def data(self, data):
                events.append("data-" + data)
            def close(self):
                events.append("close")
                return "DONE"

        parser = self.etree.XMLParser(target=Target())

        try:
            parser.feed(_bytes('<root>A<a>ca</a>B</root>'))
            done = parser.close()
            self.fail("error expected, but parsing succeeded")
        except ValueError:
            done = 'value error received as expected'

        self.assertEqual(["start-root", "data-A", "start-a",
                           "data-ca", "end-a", "close"],
                          events)

    def test_parser_target_fromstring_exception(self):
        # ET doesn't call .close() on errors
        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append("start-" + tag)
            def end(self, tag):
                events.append("end-" + tag)
                if tag == 'a':
                    raise ValueError("dead and gone")
            def data(self, data):
                events.append("data-" + data)
            def close(self):
                events.append("close")
                return "DONE"

        parser = self.etree.XMLParser(target=Target())

        try:
            done = self.etree.fromstring(_bytes('<root>A<a>ca</a>B</root>'),
                                         parser=parser)
            self.fail("error expected, but parsing succeeded")
        except ValueError:
            done = 'value error received as expected'

        self.assertEqual(["start-root", "data-A", "start-a",
                           "data-ca", "end-a", "close"],
                          events)

    def test_parser_target_comment(self):
        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append("start-" + tag)
            def end(self, tag):
                events.append("end-" + tag)
            def data(self, data):
                events.append("data-" + data)
            def comment(self, text):
                events.append("comment-" + text)
            def close(self):
                return "DONE"

        parser = self.etree.XMLParser(target=Target())

        parser.feed(_bytes('<!--a--><root>A<!--b--><sub/><!--c-->B</root><!--d-->'))
        done = parser.close()

        self.assertEqual("DONE", done)
        self.assertEqual(["comment-a", "start-root", "data-A", "comment-b",
                           "start-sub", "end-sub", "comment-c", "data-B",
                           "end-root", "comment-d"],
                          events)

    def test_parser_target_pi(self):
        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append("start-" + tag)
            def end(self, tag):
                events.append("end-" + tag)
            def data(self, data):
                events.append("data-" + data)
            def pi(self, target, data):
                events.append("pi-" + target + "-" + data)
            def close(self):
                return "DONE"

        parser = self.etree.XMLParser(target=Target())

        parser.feed(_bytes('<?test a?><root>A<?test b?>B</root><?test c?>'))
        done = parser.close()

        self.assertEqual("DONE", done)
        self.assertEqual(["pi-test-a", "start-root", "data-A", "pi-test-b",
                           "data-B", "end-root", "pi-test-c"],
                          events)

    def test_parser_target_cdata(self):
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

        parser = self.etree.XMLParser(target=Target(),
                                      strip_cdata=False)

        parser.feed(_bytes('<root>A<a><![CDATA[ca]]></a>B</root>'))
        done = parser.close()

        self.assertEqual("DONE", done)
        self.assertEqual(["start-root", "data-A", "start-a",
                           "data-ca", "end-a", "data-B", "end-root"],
                          events)

    def test_parser_target_recover(self):
        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append("start-" + tag)
            def end(self, tag):
                events.append("end-" + tag)
            def data(self, data):
                events.append("data-" + data)
            def close(self):
                events.append("close")
                return "DONE"

        parser = self.etree.XMLParser(target=Target(),
                                      recover=True)

        parser.feed(_bytes('<root>A<a>ca</a>B</not-root>'))
        done = parser.close()

        self.assertEqual("DONE", done)
        self.assertEqual(["start-root", "data-A", "start-a",
                           "data-ca", "end-a", "data-B",
                           "end-root", "close"],
                          events)

    def test_iterwalk_tag(self):
        iterwalk = self.etree.iterwalk
        root = self.etree.XML(_bytes('<a><b><d/></b><c/></a>'))

        iterator = iterwalk(root, tag="b", events=('start', 'end'))
        events = list(iterator)
        self.assertEqual(
            [('start', root[0]), ('end', root[0])],
            events)

    def test_iterwalk_tag_all(self):
        iterwalk = self.etree.iterwalk
        root = self.etree.XML(_bytes('<a><b><d/></b><c/></a>'))

        iterator = iterwalk(root, tag="*", events=('start', 'end'))
        events = list(iterator)
        self.assertEqual(
            8,
            len(events))

    def test_iterwalk(self):
        iterwalk = self.etree.iterwalk
        root = self.etree.XML(_bytes('<a><b></b><c/></a>'))

        events = list(iterwalk(root))
        self.assertEqual(
            [('end', root[0]), ('end', root[1]), ('end', root)],
            events)

    def test_iterwalk_start(self):
        iterwalk = self.etree.iterwalk
        root = self.etree.XML(_bytes('<a><b></b><c/></a>'))

        iterator = iterwalk(root, events=('start',))
        events = list(iterator)
        self.assertEqual(
            [('start', root), ('start', root[0]), ('start', root[1])],
            events)

    def test_iterwalk_start_end(self):
        iterwalk = self.etree.iterwalk
        root = self.etree.XML(_bytes('<a><b></b><c/></a>'))

        iterator = iterwalk(root, events=('start','end'))
        events = list(iterator)
        self.assertEqual(
            [('start', root), ('start', root[0]), ('end', root[0]),
             ('start', root[1]), ('end', root[1]), ('end', root)],
            events)

    def test_iterwalk_clear(self):
        iterwalk = self.etree.iterwalk
        root = self.etree.XML(_bytes('<a><b></b><c/></a>'))

        iterator = iterwalk(root)
        for event, elem in iterator:
            elem.clear()

        self.assertEqual(0,
                          len(root))

    def test_iterwalk_attrib_ns(self):
        iterwalk = self.etree.iterwalk
        root = self.etree.XML(_bytes('<a xmlns="ns1"><b><c xmlns="ns2"/></b></a>'))

        attr_name = '{testns}bla'
        events = []
        iterator = iterwalk(root, events=('start','end','start-ns','end-ns'))
        for event, elem in iterator:
            events.append(event)
            if event == 'start':
                if elem.tag != '{ns1}a':
                    elem.set(attr_name, 'value')

        self.assertEqual(
            ['start-ns', 'start', 'start', 'start-ns', 'start',
             'end', 'end-ns', 'end', 'end', 'end-ns'],
            events)

        self.assertEqual(
            None,
            root.get(attr_name))
        self.assertEqual(
            'value',
            root[0].get(attr_name))

    def test_iterwalk_getiterator(self):
        iterwalk = self.etree.iterwalk
        root = self.etree.XML(_bytes('<a><b><d/></b><c/></a>'))

        counts = []
        for event, elem in iterwalk(root):
            counts.append(len(list(elem.getiterator())))
        self.assertEqual(
            [1,2,1,4],
            counts)

    def test_resolve_string_dtd(self):
        parse = self.etree.parse
        parser = self.etree.XMLParser(dtd_validation=True)
        assertEqual = self.assertEqual
        test_url = _str("__nosuch.dtd")

        class MyResolver(self.etree.Resolver):
            def resolve(self, url, id, context):
                assertEqual(url, test_url)
                return self.resolve_string(
                    _str('''<!ENTITY myentity "%s">
                        <!ELEMENT doc ANY>''') % url, context)

        parser.resolvers.add(MyResolver())

        xml = _str('<!DOCTYPE doc SYSTEM "%s"><doc>&myentity;</doc>') % test_url
        tree = parse(StringIO(xml), parser)
        root = tree.getroot()
        self.assertEqual(root.text, test_url)

    def test_resolve_bytes_dtd(self):
        parse = self.etree.parse
        parser = self.etree.XMLParser(dtd_validation=True)
        assertEqual = self.assertEqual
        test_url = _str("__nosuch.dtd")

        class MyResolver(self.etree.Resolver):
            def resolve(self, url, id, context):
                assertEqual(url, test_url)
                return self.resolve_string(
                    (_str('''<!ENTITY myentity "%s">
                             <!ELEMENT doc ANY>''') % url).encode('utf-8'),
                    context)

        parser.resolvers.add(MyResolver())

        xml = _str('<!DOCTYPE doc SYSTEM "%s"><doc>&myentity;</doc>') % test_url
        tree = parse(StringIO(xml), parser)
        root = tree.getroot()
        self.assertEqual(root.text, test_url)

    def test_resolve_filelike_dtd(self):
        parse = self.etree.parse
        parser = self.etree.XMLParser(dtd_validation=True)
        assertEqual = self.assertEqual
        test_url = _str("__nosuch.dtd")

        class MyResolver(self.etree.Resolver):
            def resolve(self, url, id, context):
                assertEqual(url, test_url)
                return self.resolve_file(
                    SillyFileLike(
                        _str('''<!ENTITY myentity "%s">
                        <!ELEMENT doc ANY>''') % url), context)

        parser.resolvers.add(MyResolver())

        xml = _str('<!DOCTYPE doc SYSTEM "%s"><doc>&myentity;</doc>') % test_url
        tree = parse(StringIO(xml), parser)
        root = tree.getroot()
        self.assertEqual(root.text, test_url)

    def test_resolve_filename_dtd(self):
        parse = self.etree.parse
        parser = self.etree.XMLParser(attribute_defaults=True)
        assertEqual = self.assertEqual
        test_url = _str("__nosuch.dtd")

        class MyResolver(self.etree.Resolver):
            def resolve(self, url, id, context):
                assertEqual(url, test_url)
                return self.resolve_filename(
                    fileInTestDir('test.dtd'), context)

        parser.resolvers.add(MyResolver())

        xml = _str('<!DOCTYPE a SYSTEM "%s"><a><b/></a>') % test_url
        tree = parse(StringIO(xml), parser)
        root = tree.getroot()
        self.assertEqual(
            root.attrib,    {'default': 'valueA'})
        self.assertEqual(
            root[0].attrib, {'default': 'valueB'})

    def test_resolve_filename_dtd_relative(self):
        parse = self.etree.parse
        parser = self.etree.XMLParser(attribute_defaults=True)
        assertEqual = self.assertEqual
        test_url = _str("__nosuch.dtd")

        class MyResolver(self.etree.Resolver):
            def resolve(self, url, id, context):
                assertEqual(url, fileUrlInTestDir(test_url))
                return self.resolve_filename(
                    fileUrlInTestDir('test.dtd'), context)

        parser.resolvers.add(MyResolver())

        xml = _str('<!DOCTYPE a SYSTEM "%s"><a><b/></a>') % test_url
        tree = parse(StringIO(xml), parser,
                     base_url=fileUrlInTestDir('__test.xml'))
        root = tree.getroot()
        self.assertEqual(
            root.attrib,    {'default': 'valueA'})
        self.assertEqual(
            root[0].attrib, {'default': 'valueB'})

    def test_resolve_file_dtd(self):
        parse = self.etree.parse
        parser = self.etree.XMLParser(attribute_defaults=True)
        assertEqual = self.assertEqual
        test_url = _str("__nosuch.dtd")

        class MyResolver(self.etree.Resolver):
            def resolve(self, url, id, context):
                assertEqual(url, test_url)
                return self.resolve_file(
                    open(fileInTestDir('test.dtd'), 'rb'), context)

        parser.resolvers.add(MyResolver())

        xml = _str('<!DOCTYPE a SYSTEM "%s"><a><b/></a>') % test_url
        tree = parse(StringIO(xml), parser)
        root = tree.getroot()
        self.assertEqual(
            root.attrib,    {'default': 'valueA'})
        self.assertEqual(
            root[0].attrib, {'default': 'valueB'})

    def test_resolve_empty(self):
        parse = self.etree.parse
        parser = self.etree.XMLParser(load_dtd=True)
        assertEqual = self.assertEqual
        test_url = _str("__nosuch.dtd")

        class check(object):
            resolved = False

        class MyResolver(self.etree.Resolver):
            def resolve(self, url, id, context):
                assertEqual(url, test_url)
                check.resolved = True
                return self.resolve_empty(context)

        parser.resolvers.add(MyResolver())

        xml = _str('<!DOCTYPE doc SYSTEM "%s"><doc>&myentity;</doc>') % test_url
        self.assertRaises(etree.XMLSyntaxError, parse, StringIO(xml), parser)
        self.assertTrue(check.resolved)

    def test_resolve_error(self):
        parse = self.etree.parse
        parser = self.etree.XMLParser(dtd_validation=True)

        class _LocalException(Exception):
            pass

        class MyResolver(self.etree.Resolver):
            def resolve(self, url, id, context):
                raise _LocalException

        parser.resolvers.add(MyResolver())

        xml = '<!DOCTYPE doc SYSTEM "test"><doc>&myentity;</doc>'
        self.assertRaises(_LocalException, parse, BytesIO(xml), parser)

    if etree.LIBXML_VERSION > (2,6,20):
        def test_entity_parse(self):
            parse = self.etree.parse
            tostring = self.etree.tostring
            parser = self.etree.XMLParser(resolve_entities=False)
            Entity = self.etree.Entity

            xml = _bytes('<!DOCTYPE doc SYSTEM "test"><doc>&myentity;</doc>')
            tree = parse(BytesIO(xml), parser)
            root = tree.getroot()
            self.assertEqual(root[0].tag, Entity)
            self.assertEqual(root[0].text, "&myentity;")
            self.assertEqual(root[0].tail, None)
            self.assertEqual(root[0].name, "myentity")

            self.assertEqual(_bytes('<doc>&myentity;</doc>'),
                              tostring(root))

        def test_entity_restructure(self):
            xml = _bytes('''<!DOCTYPE root [ <!ENTITY nbsp "&#160;"> ]>
                <root>
                  <child1/>
                  <child2/>
                  <child3>&nbsp;</child3>
                </root>''')

            parser = self.etree.XMLParser(resolve_entities=False)
            root = etree.fromstring(xml, parser)
            self.assertEqual([ el.tag for el in root ],
                              ['child1', 'child2', 'child3'])

            root[0] = root[-1]
            self.assertEqual([ el.tag for el in root ],
                              ['child3', 'child2'])
            self.assertEqual(root[0][0].text, '&nbsp;')
            self.assertEqual(root[0][0].name, 'nbsp')

    def test_entity_append(self):
        Entity = self.etree.Entity
        Element = self.etree.Element
        tostring = self.etree.tostring

        root = Element("root")
        root.append( Entity("test") )

        self.assertEqual(root[0].tag, Entity)
        self.assertEqual(root[0].text, "&test;")
        self.assertEqual(root[0].tail, None)
        self.assertEqual(root[0].name, "test")

        self.assertEqual(_bytes('<root>&test;</root>'),
                          tostring(root))

    def test_entity_values(self):
        Entity = self.etree.Entity
        self.assertEqual(Entity("test").text, '&test;')
        self.assertEqual(Entity("#17683").text, '&#17683;')
        self.assertEqual(Entity("#x1768").text, '&#x1768;')
        self.assertEqual(Entity("#x98AF").text, '&#x98AF;')

    def test_entity_error(self):
        Entity = self.etree.Entity
        self.assertRaises(ValueError, Entity, 'a b c')
        self.assertRaises(ValueError, Entity, 'a,b')
        self.assertRaises(ValueError, Entity, 'a\0b')
        self.assertRaises(ValueError, Entity, '#abc')
        self.assertRaises(ValueError, Entity, '#xxyz')

    def test_cdata(self):
        CDATA = self.etree.CDATA
        Element = self.etree.Element
        tostring = self.etree.tostring

        root = Element("root")
        root.text = CDATA('test')

        self.assertEqual('test',
                          root.text)
        self.assertEqual(_bytes('<root><![CDATA[test]]></root>'),
                          tostring(root))

    def test_cdata_type(self):
        CDATA = self.etree.CDATA
        Element = self.etree.Element
        root = Element("root")

        root.text = CDATA("test")
        self.assertEqual('test', root.text)

        root.text = CDATA(_str("test"))
        self.assertEqual('test', root.text)

        self.assertRaises(TypeError, CDATA, 1)

    def test_cdata_errors(self):
        CDATA = self.etree.CDATA
        Element = self.etree.Element

        root = Element("root")
        cdata = CDATA('test')
        
        self.assertRaises(TypeError,
                          setattr, root, 'tail', cdata)
        self.assertRaises(TypeError,
                          root.set, 'attr', cdata)
        self.assertRaises(TypeError,
                          operator.setitem, root.attrib, 'attr', cdata)

    def test_cdata_parser(self):
        tostring = self.etree.tostring
        parser = self.etree.XMLParser(strip_cdata=False)
        root = self.etree.XML(_bytes('<root><![CDATA[test]]></root>'), parser)

        self.assertEqual('test', root.text)
        self.assertEqual(_bytes('<root><![CDATA[test]]></root>'),
                          tostring(root))

    def test_cdata_xpath(self):
        tostring = self.etree.tostring
        parser = self.etree.XMLParser(strip_cdata=False)
        root = self.etree.XML(_bytes('<root><![CDATA[test]]></root>'), parser)
        self.assertEqual(_bytes('<root><![CDATA[test]]></root>'),
                          tostring(root))

        self.assertEqual(['test'], root.xpath('//text()'))

    # TypeError in etree, AssertionError in ElementTree;
    def test_setitem_assert(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        
        self.assertRaises(TypeError,
                          a.__setitem__, 0, 'foo')

    def test_append_error(self):
        Element = self.etree.Element
        root = Element('root')
        # raises AssertionError in ElementTree
        self.assertRaises(TypeError, root.append, None)
        self.assertRaises(TypeError, root.extend, [None])
        self.assertRaises(TypeError, root.extend, [Element('one'), None])
        self.assertEqual('one', root[0].tag)

    def test_append_recursive_error(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        root = Element('root')
        self.assertRaises(ValueError, root.append, root)
        child = SubElement(root, 'child')
        self.assertRaises(ValueError, child.append, root)
        child2 = SubElement(child, 'child2')
        self.assertRaises(ValueError, child2.append, root)
        self.assertRaises(ValueError, child2.append, child)
        self.assertEqual('child2', root[0][0].tag)

    def test_addnext(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        root = Element('root')
        SubElement(root, 'a')
        SubElement(root, 'b')

        self.assertEqual(['a', 'b'],
                          [c.tag for c in root])
        root[1].addnext(root[0])
        self.assertEqual(['b', 'a'],
                          [c.tag for c in root])

    def test_addprevious(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        root = Element('root')
        SubElement(root, 'a')
        SubElement(root, 'b')

        self.assertEqual(['a', 'b'],
                          [c.tag for c in root])
        root[0].addprevious(root[1])
        self.assertEqual(['b', 'a'],
                          [c.tag for c in root])

    def test_addnext_cycle(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        root = Element('root')
        a = SubElement(root, 'a')
        b = SubElement(a, 'b')
        # appending parent as sibling is forbidden
        self.assertRaises(ValueError, b.addnext, a)
        self.assertEqual(['a'], [c.tag for c in root])
        self.assertEqual(['b'], [c.tag for c in a])

    def test_addprevious_cycle(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        root = Element('root')
        a = SubElement(root, 'a')
        b = SubElement(a, 'b')
        # appending parent as sibling is forbidden
        self.assertRaises(ValueError, b.addprevious, a)
        self.assertEqual(['a'], [c.tag for c in root])
        self.assertEqual(['b'], [c.tag for c in a])

    def test_addnext_cycle_long(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        root = Element('root')
        a = SubElement(root, 'a')
        b = SubElement(a, 'b')
        c = SubElement(b, 'c')
        # appending parent as sibling is forbidden
        self.assertRaises(ValueError, c.addnext, a)

    def test_addprevious_cycle_long(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        root = Element('root')
        a = SubElement(root, 'a')
        b = SubElement(a, 'b')
        c = SubElement(b, 'c')
        # appending parent as sibling is forbidden
        self.assertRaises(ValueError, c.addprevious, a)

    def test_addprevious_noops(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        root = Element('root')
        a = SubElement(root, 'a')
        b = SubElement(root, 'b')
        a.addprevious(a)
        self.assertEqual('a', root[0].tag)
        self.assertEqual('b', root[1].tag)
        b.addprevious(b)
        self.assertEqual('a', root[0].tag)
        self.assertEqual('b', root[1].tag)
        b.addprevious(a)
        self.assertEqual('a', root[0].tag)
        self.assertEqual('b', root[1].tag)

    def test_addnext_noops(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        root = Element('root')
        a = SubElement(root, 'a')
        b = SubElement(root, 'b')
        a.addnext(a)
        self.assertEqual('a', root[0].tag)
        self.assertEqual('b', root[1].tag)
        b.addnext(b)
        self.assertEqual('a', root[0].tag)
        self.assertEqual('b', root[1].tag)
        a.addnext(b)
        self.assertEqual('a', root[0].tag)
        self.assertEqual('b', root[1].tag)

    def test_addnext_root(self):
        Element = self.etree.Element
        a = Element('a')
        b = Element('b')
        self.assertRaises(TypeError, a.addnext, b)

    def test_addprevious_pi(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        PI = self.etree.PI
        root = Element('root')
        SubElement(root, 'a')
        pi = PI('TARGET', 'TEXT')
        pi.tail = "TAIL"

        self.assertEqual(_bytes('<root><a></a></root>'),
                          self._writeElement(root))
        root[0].addprevious(pi)
        self.assertEqual(_bytes('<root><?TARGET TEXT?>TAIL<a></a></root>'),
                          self._writeElement(root))

    def test_addprevious_root_pi(self):
        Element = self.etree.Element
        PI = self.etree.PI
        root = Element('root')
        pi = PI('TARGET', 'TEXT')
        pi.tail = "TAIL"

        self.assertEqual(_bytes('<root></root>'),
                          self._writeElement(root))
        root.addprevious(pi)
        self.assertEqual(_bytes('<?TARGET TEXT?>\n<root></root>'),
                          self._writeElement(root))

    def test_addnext_pi(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        PI = self.etree.PI
        root = Element('root')
        SubElement(root, 'a')
        pi = PI('TARGET', 'TEXT')
        pi.tail = "TAIL"

        self.assertEqual(_bytes('<root><a></a></root>'),
                          self._writeElement(root))
        root[0].addnext(pi)
        self.assertEqual(_bytes('<root><a></a><?TARGET TEXT?>TAIL</root>'),
                          self._writeElement(root))

    def test_addnext_root_pi(self):
        Element = self.etree.Element
        PI = self.etree.PI
        root = Element('root')
        pi = PI('TARGET', 'TEXT')
        pi.tail = "TAIL"

        self.assertEqual(_bytes('<root></root>'),
                          self._writeElement(root))
        root.addnext(pi)
        self.assertEqual(_bytes('<root></root>\n<?TARGET TEXT?>'),
                          self._writeElement(root))

    def test_addnext_comment(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        Comment = self.etree.Comment
        root = Element('root')
        SubElement(root, 'a')
        comment = Comment('TEXT ')
        comment.tail = "TAIL"

        self.assertEqual(_bytes('<root><a></a></root>'),
                          self._writeElement(root))
        root[0].addnext(comment)
        self.assertEqual(_bytes('<root><a></a><!--TEXT -->TAIL</root>'),
                          self._writeElement(root))

    def test_addnext_root_comment(self):
        Element = self.etree.Element
        Comment = self.etree.Comment
        root = Element('root')
        comment = Comment('TEXT ')
        comment.tail = "TAIL"

        self.assertEqual(_bytes('<root></root>'),
                          self._writeElement(root))
        root.addnext(comment)
        self.assertEqual(_bytes('<root></root>\n<!--TEXT -->'),
                          self._writeElement(root))

    def test_addprevious_comment(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        Comment = self.etree.Comment
        root = Element('root')
        SubElement(root, 'a')
        comment = Comment('TEXT ')
        comment.tail = "TAIL"

        self.assertEqual(_bytes('<root><a></a></root>'),
                          self._writeElement(root))
        root[0].addprevious(comment)
        self.assertEqual(_bytes('<root><!--TEXT -->TAIL<a></a></root>'),
                          self._writeElement(root))

    def test_addprevious_root_comment(self):
        Element = self.etree.Element
        Comment = self.etree.Comment
        root = Element('root')
        comment = Comment('TEXT ')
        comment.tail = "TAIL"

        self.assertEqual(_bytes('<root></root>'),
                          self._writeElement(root))
        root.addprevious(comment)
        self.assertEqual(_bytes('<!--TEXT -->\n<root></root>'),
                          self._writeElement(root))

    # ET's Elements have items() and key(), but not values()
    def test_attribute_values(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc alpha="Alpha" beta="Beta" gamma="Gamma"/>'))
        values = root.values()
        values.sort()
        self.assertEqual(['Alpha', 'Beta', 'Gamma'], values)

    # gives error in ElementTree
    def test_comment_empty(self):
        Element = self.etree.Element
        Comment = self.etree.Comment

        a = Element('a')
        a.append(Comment())
        self.assertEqual(
            _bytes('<a><!----></a>'),
            self._writeElement(a))

    # ElementTree ignores comments
    def test_comment_parse_empty(self):
        ElementTree = self.etree.ElementTree
        tostring = self.etree.tostring

        xml = _bytes('<a><b/><!----><c/></a>')
        f = BytesIO(xml)
        doc = ElementTree(file=f)
        a = doc.getroot()
        self.assertEqual(
            '',
            a[1].text)
        self.assertEqual(
            xml,
            tostring(a))

    # ElementTree ignores comments
    def test_comment_no_proxy_yet(self):
        ElementTree = self.etree.ElementTree
        
        f = BytesIO('<a><b></b><!-- hoi --><c></c></a>')
        doc = ElementTree(file=f)
        a = doc.getroot()
        self.assertEqual(
            ' hoi ',
            a[1].text)

    # does not raise an exception in ElementTree
    def test_comment_immutable(self):
        Element = self.etree.Element
        Comment = self.etree.Comment

        c = Comment()
        el = Element('myel')

        self.assertRaises(TypeError, c.append, el)
        self.assertRaises(TypeError, c.insert, 0, el)
        self.assertRaises(TypeError, c.set, "myattr", "test")

    def test_comment_immutable_attrib(self):
        c = self.etree.Comment()
        self.assertEqual(0, len(c.attrib))

        self.assertFalse(c.attrib.__contains__('nope'))
        self.assertFalse('nope' in c.attrib)
        self.assertFalse('nope' in c.attrib.keys())
        self.assertFalse('nope' in c.attrib.values())
        self.assertFalse(('nope', 'huhu') in c.attrib.items())

        self.assertEqual([], list(c.attrib))
        self.assertEqual([], list(c.attrib.keys()))
        self.assertEqual([], list(c.attrib.items()))
        self.assertEqual([], list(c.attrib.values()))
        self.assertEqual([], list(c.attrib.iterkeys()))
        self.assertEqual([], list(c.attrib.iteritems()))
        self.assertEqual([], list(c.attrib.itervalues()))

        self.assertEqual('HUHU', c.attrib.pop('nope', 'HUHU'))
        self.assertRaises(KeyError, c.attrib.pop, 'nope')

        self.assertRaises(KeyError, c.attrib.__getitem__, 'only')
        self.assertRaises(KeyError, c.attrib.__getitem__, 'names')
        self.assertRaises(KeyError, c.attrib.__getitem__, 'nope')
        self.assertRaises(KeyError, c.attrib.__setitem__, 'nope', 'yep')
        self.assertRaises(KeyError, c.attrib.__delitem__, 'nope')

    # test passing 'None' to dump()
    def test_dump_none(self):
        self.assertRaises(TypeError, self.etree.dump, None)

    def test_prefix(self):
        ElementTree = self.etree.ElementTree
        
        f = BytesIO('<a xmlns:foo="http://www.infrae.com/ns/1"><foo:b/></a>')
        doc = ElementTree(file=f)
        a = doc.getroot()
        self.assertEqual(
            None,
            a.prefix)
        self.assertEqual(
            'foo',
            a[0].prefix)

    def test_prefix_default_ns(self):
        ElementTree = self.etree.ElementTree
        
        f = BytesIO('<a xmlns="http://www.infrae.com/ns/1"><b/></a>')
        doc = ElementTree(file=f)
        a = doc.getroot()
        self.assertEqual(
            None,
            a.prefix)
        self.assertEqual(
            None,
            a[0].prefix)

    def test_getparent(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        self.assertEqual(
            None,
            a.getparent())
        self.assertEqual(
            a,
            b.getparent())
        self.assertEqual(
            b.getparent(),
            c.getparent())
        self.assertEqual(
            b,
            d.getparent())

    def test_iterchildren(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc><one/><two>Two</two>Hm<three/></doc>'))
        result = []
        for el in root.iterchildren():
            result.append(el.tag)
        self.assertEqual(['one', 'two', 'three'], result)

    def test_iterchildren_reversed(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc><one/><two>Two</two>Hm<three/></doc>'))
        result = []
        for el in root.iterchildren(reversed=True):
            result.append(el.tag)
        self.assertEqual(['three', 'two', 'one'], result)

    def test_iterchildren_tag(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc><one/><two>Two</two>Hm<two>Bla</two></doc>'))
        result = []
        for el in root.iterchildren(tag='two'):
            result.append(el.text)
        self.assertEqual(['Two', 'Bla'], result)

    def test_iterchildren_tag_posarg(self):
        XML = self.etree.XML

        root = XML(_bytes('<doc><one/><two>Two</two>Hm<two>Bla</two></doc>'))
        result = []
        for el in root.iterchildren('two'):
            result.append(el.text)
        self.assertEqual(['Two', 'Bla'], result)

    def test_iterchildren_tag_reversed(self):
        XML = self.etree.XML
        
        root = XML(_bytes('<doc><one/><two>Two</two>Hm<two>Bla</two></doc>'))
        result = []
        for el in root.iterchildren(reversed=True, tag='two'):
            result.append(el.text)
        self.assertEqual(['Bla', 'Two'], result)

    def test_iterchildren_tag_multiple(self):
        XML = self.etree.XML

        root = XML(_bytes('<doc><one/><two>Two</two>Hm<two>Bla</two><three/></doc>'))
        result = []
        for el in root.iterchildren(tag=['two', 'three']):
            result.append(el.text)
        self.assertEqual(['Two', 'Bla', None], result)

    def test_iterchildren_tag_multiple_posarg(self):
        XML = self.etree.XML

        root = XML(_bytes('<doc><one/><two>Two</two>Hm<two>Bla</two><three/></doc>'))
        result = []
        for el in root.iterchildren('two', 'three'):
            result.append(el.text)
        self.assertEqual(['Two', 'Bla', None], result)

    def test_iterchildren_tag_multiple_reversed(self):
        XML = self.etree.XML

        root = XML(_bytes('<doc><one/><two>Two</two>Hm<two>Bla</two><three/></doc>'))
        result = []
        for el in root.iterchildren(reversed=True, tag=['two', 'three']):
            result.append(el.text)
        self.assertEqual([None, 'Bla', 'Two'], result)

    def test_iterancestors(self):
        Element    = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        self.assertEqual(
            [],
            list(a.iterancestors()))
        self.assertEqual(
            [a],
            list(b.iterancestors()))
        self.assertEqual(
            [a],
            list(c.iterancestors()))
        self.assertEqual(
            [b, a],
            list(d.iterancestors()))

    def test_iterancestors_tag(self):
        Element    = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        self.assertEqual(
            [a],
            list(d.iterancestors('a')))
        self.assertEqual(
            [a],
            list(d.iterancestors(tag='a')))

        self.assertEqual(
            [b, a],
            list(d.iterancestors('*')))
        self.assertEqual(
            [b, a],
            list(d.iterancestors(tag='*')))

    def test_iterancestors_tag_multiple(self):
        Element    = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        self.assertEqual(
            [b, a],
            list(d.iterancestors(tag=('a', 'b'))))
        self.assertEqual(
            [b, a],
            list(d.iterancestors('a', 'b')))

        self.assertEqual(
            [],
            list(d.iterancestors(tag=('w', 'x', 'y', 'z'))))
        self.assertEqual(
            [],
            list(d.iterancestors('w', 'x', 'y', 'z')))

        self.assertEqual(
            [],
            list(d.iterancestors(tag=('d', 'x'))))
        self.assertEqual(
            [],
            list(d.iterancestors('d', 'x')))

        self.assertEqual(
            [b, a],
            list(d.iterancestors(tag=('b', '*'))))
        self.assertEqual(
            [b, a],
            list(d.iterancestors('b', '*')))

        self.assertEqual(
            [b],
            list(d.iterancestors(tag=('b', 'c'))))
        self.assertEqual(
            [b],
            list(d.iterancestors('b', 'c')))

    def test_iterdescendants(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        e = SubElement(c, 'e')

        self.assertEqual(
            [b, d, c, e],
            list(a.iterdescendants()))
        self.assertEqual(
            [],
            list(d.iterdescendants()))

    def test_iterdescendants_tag(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        e = SubElement(c, 'e')

        self.assertEqual(
            [],
            list(a.iterdescendants('a')))
        self.assertEqual(
            [],
            list(a.iterdescendants(tag='a')))

        a2 = SubElement(e, 'a')
        self.assertEqual(
            [a2],
            list(a.iterdescendants('a')))

        self.assertEqual(
            [a2],
            list(c.iterdescendants('a')))
        self.assertEqual(
            [a2],
            list(c.iterdescendants(tag='a')))

    def test_iterdescendants_tag_multiple(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        e = SubElement(c, 'e')

        self.assertEqual(
            [b, e],
            list(a.iterdescendants(tag=('a', 'b', 'e'))))
        self.assertEqual(
            [b, e],
            list(a.iterdescendants('a', 'b', 'e')))

        a2 = SubElement(e, 'a')
        self.assertEqual(
            [b, a2],
            list(a.iterdescendants(tag=('a', 'b'))))
        self.assertEqual(
            [b, a2],
            list(a.iterdescendants('a', 'b')))

        self.assertEqual(
            [],
            list(c.iterdescendants(tag=('x', 'y', 'z'))))
        self.assertEqual(
            [],
            list(c.iterdescendants('x', 'y', 'z')))

        self.assertEqual(
            [b, d, c, e, a2],
            list(a.iterdescendants(tag=('x', 'y', 'z', '*'))))
        self.assertEqual(
            [b, d, c, e, a2],
            list(a.iterdescendants('x', 'y', 'z', '*')))

    def test_getroottree(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        self.assertEqual(
            a,
            a.getroottree().getroot())
        self.assertEqual(
            a,
            b.getroottree().getroot())
        self.assertEqual(
            a,
            d.getroottree().getroot())

    def test_getnext(self):
        Element    = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        self.assertEqual(
            None,
            a.getnext())
        self.assertEqual(
            c,
            b.getnext())
        self.assertEqual(
            None,
            c.getnext())

    def test_getprevious(self):
        Element    = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        self.assertEqual(
            None,
            a.getprevious())
        self.assertEqual(
            b,
            c.getprevious())
        self.assertEqual(
            None,
            b.getprevious())

    def test_itersiblings(self):
        Element    = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        self.assertEqual(
            [],
            list(a.itersiblings()))
        self.assertEqual(
            [c],
            list(b.itersiblings()))
        self.assertEqual(
            [],
            list(c.itersiblings()))
        self.assertEqual(
            [b],
            list(c.itersiblings(preceding=True)))
        self.assertEqual(
            [],
            list(b.itersiblings(preceding=True)))

    def test_itersiblings_tag(self):
        Element    = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        self.assertEqual(
            [],
            list(a.itersiblings(tag='XXX')))
        self.assertEqual(
            [c],
            list(b.itersiblings(tag='c')))
        self.assertEqual(
            [c],
            list(b.itersiblings(tag='*')))
        self.assertEqual(
            [b],
            list(c.itersiblings(preceding=True, tag='b')))
        self.assertEqual(
            [],
            list(c.itersiblings(preceding=True, tag='c')))

    def test_itersiblings_tag_multiple(self):
        Element    = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        e = SubElement(a, 'e')
        self.assertEqual(
            [],
            list(a.itersiblings(tag=('XXX', 'YYY'))))
        self.assertEqual(
            [c, e],
            list(b.itersiblings(tag=('c', 'd', 'e'))))
        self.assertEqual(
            [b],
            list(c.itersiblings(preceding=True, tag=('b', 'b', 'c', 'd'))))
        self.assertEqual(
            [c, b],
            list(e.itersiblings(preceding=True, tag=('c', '*'))))

    def test_parseid(self):
        parseid = self.etree.parseid
        XML     = self.etree.XML
        xml_text = _bytes('''
        <!DOCTYPE document [
        <!ELEMENT document (h1,p)*>
        <!ELEMENT h1 (#PCDATA)>
        <!ATTLIST h1 myid ID #REQUIRED>
        <!ELEMENT p  (#PCDATA)>
        <!ATTLIST p  someid ID #REQUIRED>
        ]>
        <document>
          <h1 myid="chapter1">...</h1>
          <p id="note1" class="note">...</p>
          <p>Regular paragraph.</p>
          <p xml:id="xmlid">XML:ID paragraph.</p>
          <p someid="warn1" class="warning">...</p>
        </document>
        ''')

        tree, dic = parseid(BytesIO(xml_text))
        root = tree.getroot()
        root2 = XML(xml_text)
        self.assertEqual(self._writeElement(root),
                          self._writeElement(root2))
        expected = {
            "chapter1" : root[0],
            "xmlid"    : root[3],
            "warn1"    : root[4]
            }
        self.assertTrue("chapter1" in dic)
        self.assertTrue("warn1" in dic)
        self.assertTrue("xmlid" in dic)
        self._checkIDDict(dic, expected)

    def test_XMLDTDID(self):
        XMLDTDID = self.etree.XMLDTDID
        XML      = self.etree.XML
        xml_text = _bytes('''
        <!DOCTYPE document [
        <!ELEMENT document (h1,p)*>
        <!ELEMENT h1 (#PCDATA)>
        <!ATTLIST h1 myid ID #REQUIRED>
        <!ELEMENT p  (#PCDATA)>
        <!ATTLIST p  someid ID #REQUIRED>
        ]>
        <document>
          <h1 myid="chapter1">...</h1>
          <p id="note1" class="note">...</p>
          <p>Regular paragraph.</p>
          <p xml:id="xmlid">XML:ID paragraph.</p>
          <p someid="warn1" class="warning">...</p>
        </document>
        ''')

        root, dic = XMLDTDID(xml_text)
        root2 = XML(xml_text)
        self.assertEqual(self._writeElement(root),
                          self._writeElement(root2))
        expected = {
            "chapter1" : root[0],
            "xmlid"    : root[3],
            "warn1"    : root[4]
            }
        self.assertTrue("chapter1" in dic)
        self.assertTrue("warn1" in dic)
        self.assertTrue("xmlid" in dic)
        self._checkIDDict(dic, expected)

    def test_XMLDTDID_empty(self):
        XMLDTDID = self.etree.XMLDTDID
        XML      = self.etree.XML
        xml_text = _bytes('''
        <document>
          <h1 myid="chapter1">...</h1>
          <p id="note1" class="note">...</p>
          <p>Regular paragraph.</p>
          <p someid="warn1" class="warning">...</p>
        </document>
        ''')

        root, dic = XMLDTDID(xml_text)
        root2 = XML(xml_text)
        self.assertEqual(self._writeElement(root),
                          self._writeElement(root2))
        expected = {}
        self._checkIDDict(dic, expected)

    def _checkIDDict(self, dic, expected):
        self.assertEqual(len(dic),
                          len(expected))
        self.assertEqual(sorted(dic.items()),
                          sorted(expected.items()))
        if sys.version_info < (3,):
            self.assertEqual(sorted(dic.iteritems()),
                              sorted(expected.iteritems()))
        self.assertEqual(sorted(dic.keys()),
                          sorted(expected.keys()))
        if sys.version_info < (3,):
            self.assertEqual(sorted(dic.iterkeys()),
                              sorted(expected.iterkeys()))
        if sys.version_info < (3,):
            self.assertEqual(sorted(dic.values()),
                              sorted(expected.values()))
            self.assertEqual(sorted(dic.itervalues()),
                              sorted(expected.itervalues()))

    def test_namespaces(self):
        etree = self.etree

        r = {'foo': 'http://ns.infrae.com/foo'}
        e = etree.Element('{http://ns.infrae.com/foo}bar', nsmap=r)
        self.assertEqual(
            'foo',
            e.prefix)
        self.assertEqual(
            _bytes('<foo:bar xmlns:foo="http://ns.infrae.com/foo"></foo:bar>'),
            self._writeElement(e))
        
    def test_namespaces_default(self):
        etree = self.etree

        r = {None: 'http://ns.infrae.com/foo'}
        e = etree.Element('{http://ns.infrae.com/foo}bar', nsmap=r)
        self.assertEqual(
            None,
            e.prefix)
        self.assertEqual(
            '{http://ns.infrae.com/foo}bar',
            e.tag)
        self.assertEqual(
            _bytes('<bar xmlns="http://ns.infrae.com/foo"></bar>'),
            self._writeElement(e))

    def test_namespaces_default_and_attr(self):
        etree = self.etree

        r = {None: 'http://ns.infrae.com/foo',
             'hoi': 'http://ns.infrae.com/hoi'}
        e = etree.Element('{http://ns.infrae.com/foo}bar', nsmap=r)
        e.set('{http://ns.infrae.com/hoi}test', 'value')
        self.assertEqual(
            _bytes('<bar xmlns="http://ns.infrae.com/foo" xmlns:hoi="http://ns.infrae.com/hoi" hoi:test="value"></bar>'),
            self._writeElement(e))

    def test_attribute_keeps_namespace_prefix_on_merge(self):
        etree = self.etree

        root = etree.Element('{http://test/ns}root',
                             nsmap={None: 'http://test/ns'})
        sub = etree.Element('{http://test/ns}sub',
                            nsmap={'test': 'http://test/ns'})

        sub.attrib['{http://test/ns}attr'] = 'value'
        self.assertEqual(sub.attrib['{http://test/ns}attr'], 'value')
        self.assertEqual(
            _bytes('<test:sub xmlns:test="http://test/ns" test:attr="value"/>'),
            etree.tostring(sub))

        root.append(sub)
        self.assertEqual(
            _bytes('<root xmlns="http://test/ns">'
                   '<sub xmlns:test="http://test/ns" test:attr="value"/>'
                   '</root>'),
            etree.tostring(root))

    def test_attribute_keeps_namespace_prefix_on_merge_with_nons(self):
        etree = self.etree

        root = etree.Element('root')
        sub = etree.Element('{http://test/ns}sub',
                            nsmap={'test': 'http://test/ns'})

        sub.attrib['{http://test/ns}attr'] = 'value'
        self.assertEqual(sub.attrib['{http://test/ns}attr'], 'value')
        self.assertEqual(
            _bytes('<test:sub xmlns:test="http://test/ns" test:attr="value"/>'),
            etree.tostring(sub))

        root.append(sub)
        self.assertEqual(
            _bytes('<root>'
                   '<test:sub xmlns:test="http://test/ns" test:attr="value"/>'
                   '</root>'),
            etree.tostring(root))

    def test_attribute_gets_namespace_prefix_on_merge_with_nons(self):
        etree = self.etree

        root = etree.Element('root')
        sub = etree.Element('{http://test/ns}sub',
                            nsmap={None: 'http://test/ns'})

        sub.attrib['{http://test/ns}attr'] = 'value'
        self.assertEqual(sub.attrib['{http://test/ns}attr'], 'value')
        self.assertEqual(
            _bytes('<sub xmlns="http://test/ns" '
                   'xmlns:ns0="http://test/ns" ns0:attr="value"/>'),
            etree.tostring(sub))

        root.append(sub)
        self.assertEqual(
            _bytes('<root>'
                   '<sub xmlns="http://test/ns"'
                   ' xmlns:ns0="http://test/ns" ns0:attr="value"/>'
                   '</root>'),
            etree.tostring(root))

    def test_attribute_gets_namespace_prefix_on_merge(self):
        etree = self.etree

        root = etree.Element('{http://test/ns}root',
                             nsmap={'test': 'http://test/ns',
                                    None: 'http://test/ns'})
        sub = etree.Element('{http://test/ns}sub',
                            nsmap={None: 'http://test/ns'})

        sub.attrib['{http://test/ns}attr'] = 'value'
        self.assertEqual(sub.attrib['{http://test/ns}attr'], 'value')
        self.assertEqual(
            _bytes('<sub xmlns="http://test/ns" '
                   'xmlns:ns0="http://test/ns" ns0:attr="value"/>'),
            etree.tostring(sub))

        root.append(sub)
        self.assertEqual(
            _bytes('<test:root xmlns:test="http://test/ns" xmlns="http://test/ns">'
                   '<test:sub test:attr="value"/>'
                   '</test:root>'),
            etree.tostring(root))

    def test_namespaces_elementtree(self):
        etree = self.etree
        r = {None: 'http://ns.infrae.com/foo',
             'hoi': 'http://ns.infrae.com/hoi'} 
        e = etree.Element('{http://ns.infrae.com/foo}z', nsmap=r)
        tree = etree.ElementTree(element=e)
        etree.SubElement(e, '{http://ns.infrae.com/hoi}x')
        self.assertEqual(
            _bytes('<z xmlns="http://ns.infrae.com/foo" xmlns:hoi="http://ns.infrae.com/hoi"><hoi:x></hoi:x></z>'),
            self._writeElement(e))

    def test_namespaces_default_copy_element(self):
        etree = self.etree

        r = {None: 'http://ns.infrae.com/foo'}
        e1 = etree.Element('{http://ns.infrae.com/foo}bar', nsmap=r)
        e2 = etree.Element('{http://ns.infrae.com/foo}bar', nsmap=r)

        e1.append(e2)

        self.assertEqual(
            None,
            e1.prefix)
        self.assertEqual(
            None,
            e1[0].prefix)
        self.assertEqual(
            '{http://ns.infrae.com/foo}bar',
            e1.tag)
        self.assertEqual(
            '{http://ns.infrae.com/foo}bar',
            e1[0].tag)

    def test_namespaces_copy_element(self):
        etree = self.etree

        r = {None: 'http://ns.infrae.com/BAR'}
        e1 = etree.Element('{http://ns.infrae.com/BAR}bar', nsmap=r)
        e2 = etree.Element('{http://ns.infrae.com/foo}bar', nsmap=r)

        e1.append(e2)

        self.assertEqual(
            None,
            e1.prefix)
        self.assertNotEqual(
            None,
            e2.prefix)
        self.assertEqual(
            '{http://ns.infrae.com/BAR}bar',
            e1.tag)
        self.assertEqual(
            '{http://ns.infrae.com/foo}bar',
            e2.tag)

    def test_namespaces_reuse_after_move(self):
        ns_href = "http://a.b.c"
        one = self.etree.fromstring(
            _bytes('<foo><bar xmlns:ns="%s"><ns:baz/></bar></foo>' % ns_href))
        baz = one[0][0]

        two = self.etree.fromstring(
            _bytes('<root xmlns:ns="%s"/>' % ns_href))
        two.append(baz)
        del one # make sure the source document is deallocated

        self.assertEqual('{%s}baz' % ns_href, baz.tag)
        self.assertEqual(
            _bytes('<root xmlns:ns="%s"><ns:baz/></root>' % ns_href),
            self.etree.tostring(two))

    def test_namespace_cleanup(self):
        xml = _bytes('<foo xmlns="F" xmlns:x="x"><bar xmlns:ns="NS" xmlns:b="b" xmlns="B"><ns:baz/></bar></foo>')
        root = self.etree.fromstring(xml)
        self.assertEqual(xml,
                          self.etree.tostring(root))
        self.etree.cleanup_namespaces(root)
        self.assertEqual(
            _bytes('<foo xmlns="F"><bar xmlns:ns="NS" xmlns="B"><ns:baz/></bar></foo>'),
            self.etree.tostring(root))

    def test_element_nsmap(self):
        etree = self.etree

        r = {None: 'http://ns.infrae.com/foo',
             'hoi': 'http://ns.infrae.com/hoi'}
        e = etree.Element('{http://ns.infrae.com/foo}bar', nsmap=r)
        self.assertEqual(
            r,
            e.nsmap)

    def test_subelement_nsmap(self):
        etree = self.etree

        re = {None: 'http://ns.infrae.com/foo',
             'hoi': 'http://ns.infrae.com/hoi'}
        e = etree.Element('{http://ns.infrae.com/foo}bar', nsmap=re)

        rs = {None: 'http://ns.infrae.com/honk',
             'top': 'http://ns.infrae.com/top'}
        s = etree.SubElement(e, '{http://ns.infrae.com/honk}bar', nsmap=rs)

        r = re.copy()
        r.update(rs)
        self.assertEqual(re, e.nsmap)
        self.assertEqual(r,  s.nsmap)

    def test_html_prefix_nsmap(self):
        etree = self.etree
        el = etree.HTML('<hha:page-description>aa</hha:page-description>').find('.//page-description')
        self.assertEqual({'hha': None}, el.nsmap)

    def test_getiterator_filter_multiple(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        e = SubElement(c, 'e')
        f = SubElement(c, 'f')

        self.assertEqual(
            [a, b],
               list(a.getiterator('a', 'b')))
        self.assertEqual(
            [],
              list(a.getiterator('x', 'y')))
        self.assertEqual(
            [a, f],
              list(a.getiterator('f', 'a')))
        self.assertEqual(
            [c, e, f],
               list(c.getiterator('c', '*', 'a')))
        self.assertEqual(
            [],
                  list(a.getiterator( (), () )))

    def test_getiterator_filter_multiple_tuple(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        e = SubElement(c, 'e')
        f = SubElement(c, 'f')

        self.assertEqual(
            [a, b],
                  list(a.getiterator( ('a', 'b') )))
        self.assertEqual(
            [],
              list(a.getiterator( ('x', 'y') )))
        self.assertEqual(
            [a, f],
                  list(a.getiterator( ('f', 'a') )))
        self.assertEqual(
            [c, e, f],
                     list(c.getiterator( ('c', '*', 'a') )))
        self.assertEqual(
            [],
              list(a.getiterator( () )))

    def test_getiterator_filter_namespace(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('{a}a')
        b = SubElement(a, '{a}b')
        c = SubElement(a, '{a}c')
        d = SubElement(b, '{b}d')
        e = SubElement(c, '{a}e')
        f = SubElement(c, '{b}f')
        g = SubElement(c, 'g')

        self.assertEqual(
            [a],
            list(a.getiterator('{a}a')))
        self.assertEqual(
            [],
            list(a.getiterator('{b}a')))
        self.assertEqual(
            [],
            list(a.getiterator('a')))
        self.assertEqual(
            [a,b,d,c,e,f,g],
            list(a.getiterator('*')))
        self.assertEqual(
            [f],
            list(c.getiterator('{b}*')))
        self.assertEqual(
            [d, f],
            list(a.getiterator('{b}*')))
        self.assertEqual(
            [g],
            list(a.getiterator('g')))
        self.assertEqual(
            [g],
            list(a.getiterator('{}g')))
        self.assertEqual(
            [g],
            list(a.getiterator('{}*')))

    def test_getiterator_filter_local_name(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('{a}a')
        b = SubElement(a, '{nsA}b')
        c = SubElement(b, '{nsB}b')
        d = SubElement(a, 'b')
        e = SubElement(a, '{nsA}e')
        f = SubElement(e, '{nsB}e')
        g = SubElement(e, 'e')

        self.assertEqual(
            [b, c, d],
            list(a.getiterator('{*}b')))
        self.assertEqual(
            [e, f, g],
            list(a.getiterator('{*}e')))
        self.assertEqual(
            [a, b, c, d, e, f, g],
            list(a.getiterator('{*}*')))

    def test_getiterator_filter_entities(self):
        Element = self.etree.Element
        Entity = self.etree.Entity
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        entity_b = Entity("TEST-b")
        b.append(entity_b)

        self.assertEqual(
            [entity_b],
            list(a.getiterator(Entity)))

        entity_a = Entity("TEST-a")
        a.append(entity_a)

        self.assertEqual(
            [entity_b, entity_a],
            list(a.getiterator(Entity)))

        self.assertEqual(
            [entity_b],
            list(b.getiterator(Entity)))

    def test_getiterator_filter_element(self):
        Element = self.etree.Element
        Comment = self.etree.Comment
        PI = self.etree.PI
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        a.append(Comment("test"))
        a.append(PI("pi", "content"))
        c = SubElement(a, 'c')

        self.assertEqual(
            [a, b, c],
            list(a.getiterator(Element)))

    def test_getiterator_filter_all_comment_pi(self):
        # ElementTree iterates over everything here
        Element = self.etree.Element
        Comment = self.etree.Comment
        PI = self.etree.PI
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        a.append(Comment("test"))
        a.append(PI("pi", "content"))
        c = SubElement(a, 'c')

        self.assertEqual(
            [a, b, c],
            list(a.getiterator('*')))

    def test_elementtree_find_qname(self):
        XML = self.etree.XML
        ElementTree = self.etree.ElementTree
        QName = self.etree.QName
        tree = ElementTree(XML(_bytes('<a><b><c/></b><b/><c><b/></c></a>')))
        self.assertEqual(tree.find(QName("c")), tree.getroot()[2])

    def test_elementtree_findall_qname(self):
        XML = self.etree.XML
        ElementTree = self.etree.ElementTree
        QName = self.etree.QName
        tree = ElementTree(XML(_bytes('<a><b><c/></b><b/><c><b/></c></a>')))
        self.assertEqual(len(list(tree.findall(QName("c")))), 1)

    def test_elementtree_findall_ns_qname(self):
        XML = self.etree.XML
        ElementTree = self.etree.ElementTree
        QName = self.etree.QName
        tree = ElementTree(XML(
                _bytes('<a xmlns:x="X" xmlns:y="Y"><x:b><c/></x:b><b/><c><x:b/><b/></c><b/></a>')))
        self.assertEqual(len(list(tree.findall(QName("b")))), 2)
        self.assertEqual(len(list(tree.findall(QName("X", "b")))), 1)

    def test_findall_ns(self):
        XML = self.etree.XML
        root = XML(_bytes('<a xmlns:x="X" xmlns:y="Y"><x:b><c/></x:b><b/><c><x:b/><b/></c><b/></a>'))
        self.assertEqual(len(root.findall(".//{X}b")), 2)
        self.assertEqual(len(root.findall(".//{X}*")), 2)
        self.assertEqual(len(root.findall(".//b")), 3)

    def test_findall_different_nsmaps(self):
        XML = self.etree.XML
        root = XML(_bytes('<a xmlns:x="X" xmlns:y="Y"><x:b><c/></x:b><b/><c><x:b/><b/></c><y:b/></a>'))
        nsmap = {'xx': 'X'}
        self.assertEqual(len(root.findall(".//xx:b", namespaces=nsmap)), 2)
        self.assertEqual(len(root.findall(".//xx:*", namespaces=nsmap)), 2)
        self.assertEqual(len(root.findall(".//b", namespaces=nsmap)), 2)
        nsmap = {'xx': 'Y'}
        self.assertEqual(len(root.findall(".//xx:b", namespaces=nsmap)), 1)
        self.assertEqual(len(root.findall(".//xx:*", namespaces=nsmap)), 1)
        self.assertEqual(len(root.findall(".//b", namespaces=nsmap)), 2)

    def test_findall_different_nsmaps(self):
        XML = self.etree.XML
        root = XML(_bytes('<a xmlns:x="X" xmlns:y="Y"><x:b><c/></x:b><b/><c><x:b/><b/></c><y:b/></a>'))
        nsmap = {'xx': 'X'}
        self.assertEqual(len(root.findall(".//xx:b", namespaces=nsmap)), 2)
        self.assertEqual(len(root.findall(".//xx:*", namespaces=nsmap)), 2)
        self.assertEqual(len(root.findall(".//b", namespaces=nsmap)), 2)
        nsmap = {'xx': 'Y'}
        self.assertEqual(len(root.findall(".//xx:b", namespaces=nsmap)), 1)
        self.assertEqual(len(root.findall(".//xx:*", namespaces=nsmap)), 1)
        self.assertEqual(len(root.findall(".//b", namespaces=nsmap)), 2)

    def test_findall_syntax_error(self):
        XML = self.etree.XML
        root = XML(_bytes('<a><b><c/></b><b/><c><b/><b/></c><b/></a>'))
        self.assertRaises(SyntaxError, root.findall, '')
        self.assertRaises(SyntaxError, root.findall, '//')  # absolute path on Element
        self.assertRaises(SyntaxError, root.findall, './//')

    def test_index(self):
        etree = self.etree
        e = etree.Element('foo')
        for i in range(10):
            etree.SubElement(e, 'a%s' % i)
        for i in range(10):
            self.assertEqual(
                i,
                e.index(e[i]))
        self.assertEqual(
            3, e.index(e[3], 3))
        self.assertRaises(
            ValueError, e.index, e[3], 4)
        self.assertRaises(
            ValueError, e.index, e[3], 0, 2)
        self.assertRaises(
            ValueError, e.index, e[8], 0, -3)
        self.assertRaises(
            ValueError, e.index, e[8], -5, -3)
        self.assertEqual(
            8, e.index(e[8], 0, -1))
        self.assertEqual(
            8, e.index(e[8], -12, -1))
        self.assertEqual(
            0, e.index(e[0], -12, -1))

    def test_replace(self):
        etree = self.etree
        e = etree.Element('foo')
        for i in range(10):
            el = etree.SubElement(e, 'a%s' % i)
            el.text = "text%d" % i
            el.tail = "tail%d" % i

        child0 = e[0]
        child1 = e[1]
        child2 = e[2]

        e.replace(e[0], e[1])
        self.assertEqual(
            9, len(e))
        self.assertEqual(
            child1, e[0])
        self.assertEqual(
            child1.text, "text1")
        self.assertEqual(
            child1.tail, "tail1")
        self.assertEqual(
            child0.tail, "tail0")
        self.assertEqual(
            child2, e[1])

        e.replace(e[-1], e[0])
        self.assertEqual(
            child1, e[-1])
        self.assertEqual(
            child1.text, "text1")
        self.assertEqual(
            child1.tail, "tail1")
        self.assertEqual(
            child2, e[0])

    def test_replace_new(self):
        etree = self.etree
        e = etree.Element('foo')
        for i in range(10):
            etree.SubElement(e, 'a%s' % i)

        new_element = etree.Element("test")
        new_element.text = "TESTTEXT"
        new_element.tail = "TESTTAIL"
        child1 = e[1]
        e.replace(e[0], new_element)
        self.assertEqual(
            new_element, e[0])
        self.assertEqual(
            "TESTTEXT",
            e[0].text)
        self.assertEqual(
            "TESTTAIL",
            e[0].tail)
        self.assertEqual(
            child1, e[1])

    def test_setslice_all_empty_reversed(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')

        e = Element('e')
        f = Element('f')
        g = Element('g')

        s = [e, f, g]
        a[::-1] = s
        self.assertEqual(
            [g, f, e],
            list(a))

    def test_setslice_step(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')
        e = SubElement(a, 'e')

        x = Element('x')
        y = Element('y')

        a[1::2] = [x, y]
        self.assertEqual(
            [b, x, d, y],
            list(a))

    def test_setslice_step_negative(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')
        e = SubElement(a, 'e')

        x = Element('x')
        y = Element('y')

        a[1::-1] = [x, y]
        self.assertEqual(
            [y, x, d, e],
            list(a))

    def test_setslice_step_negative2(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')
        e = SubElement(a, 'e')

        x = Element('x')
        y = Element('y')

        a[::-2] = [x, y]
        self.assertEqual(
            [b, y, d, x],
            list(a))

    def test_setslice_step_overrun(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        try:
            slice
        except NameError:
            print("slice() not found")
            return

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(a, 'd')
        e = SubElement(a, 'e')

        x = Element('x')
        y = Element('y')
        z = Element('z')

        self.assertRaises(
            ValueError,
            operator.setitem, a, slice(1,None,2), [x, y, z])

        self.assertEqual(
            [b, c, d, e],
            list(a))

    def test_sourceline_XML(self):
        XML = self.etree.XML
        root = XML(_bytes('''<?xml version="1.0"?>
        <root><test>

        <bla/></test>
        </root>
        '''))

        self.assertEqual(
            [2, 2, 4],
            [ el.sourceline for el in root.getiterator() ])

    def test_large_sourceline_XML(self):
        XML = self.etree.XML
        root = XML(_bytes(
            '<?xml version="1.0"?>\n'
            '<root>' + '\n' * 65536 +
            '<p>' + '\n' * 65536 + '</p>\n' +
            '<br/>\n'
            '</root>'))

        if self.etree.LIBXML_VERSION >= (2, 9):
            expected = [2, 131074, 131076]
        else:
            expected = [2, 65535, 65535]

        self.assertEqual(expected, [el.sourceline for el in root.iter()])

    def test_sourceline_parse(self):
        parse = self.etree.parse
        tree = parse(fileInTestDir('include/test_xinclude.xml'))

        self.assertEqual(
            [1, 2, 3],
            [ el.sourceline for el in tree.getiterator() ])

    def test_sourceline_iterparse_end(self):
        iterparse = self.etree.iterparse
        lines = [ el.sourceline for (event, el) in 
                  iterparse(fileInTestDir('include/test_xinclude.xml')) ]

        self.assertEqual(
            [2, 3, 1],
            lines)

    def test_sourceline_iterparse_start(self):
        iterparse = self.etree.iterparse
        lines = [ el.sourceline for (event, el) in 
                  iterparse(fileInTestDir('include/test_xinclude.xml'),
                            events=("start",)) ]

        self.assertEqual(
            [1, 2, 3],
            lines)

    def test_sourceline_element(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        el = Element("test")
        self.assertEqual(None, el.sourceline)

        child = SubElement(el, "test")
        self.assertEqual(None, el.sourceline)
        self.assertEqual(None, child.sourceline)

    def test_XML_base_url_docinfo(self):
        etree = self.etree
        root = etree.XML(_bytes("<root/>"), base_url="http://no/such/url")
        docinfo = root.getroottree().docinfo
        self.assertEqual(docinfo.URL, "http://no/such/url")

    def test_XML_set_base_url_docinfo(self):
        etree = self.etree
        root = etree.XML(_bytes("<root/>"), base_url="http://no/such/url")
        docinfo = root.getroottree().docinfo
        self.assertEqual(docinfo.URL, "http://no/such/url")
        docinfo.URL = "https://secret/url"
        self.assertEqual(docinfo.URL, "https://secret/url")

    def test_parse_stringio_base_url(self):
        etree = self.etree
        tree = etree.parse(BytesIO("<root/>"), base_url="http://no/such/url")
        docinfo = tree.docinfo
        self.assertEqual(docinfo.URL, "http://no/such/url")

    def test_parse_base_url_docinfo(self):
        etree = self.etree
        tree = etree.parse(fileInTestDir('include/test_xinclude.xml'),
                           base_url="http://no/such/url")
        docinfo = tree.docinfo
        self.assertEqual(docinfo.URL, "http://no/such/url")

    def test_HTML_base_url_docinfo(self):
        etree = self.etree
        root = etree.HTML(_bytes("<html/>"), base_url="http://no/such/url")
        docinfo = root.getroottree().docinfo
        self.assertEqual(docinfo.URL, "http://no/such/url")

    def test_docinfo_public(self):
        etree = self.etree
        xml_header = '<?xml version="1.0" encoding="ascii"?>'
        pub_id = "-//W3C//DTD XHTML 1.0 Transitional//EN"
        sys_id = "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"
        doctype_string = '<!DOCTYPE html PUBLIC "%s" "%s">' % (pub_id, sys_id)

        xml = _bytes(xml_header + doctype_string + '<html><body></body></html>')

        tree = etree.parse(BytesIO(xml))
        docinfo = tree.docinfo
        self.assertEqual(docinfo.encoding,    "ascii")
        self.assertEqual(docinfo.xml_version, "1.0")
        self.assertEqual(docinfo.public_id,   pub_id)
        self.assertEqual(docinfo.system_url,  sys_id)
        self.assertEqual(docinfo.root_name,   'html')
        self.assertEqual(docinfo.doctype, doctype_string)

    def test_docinfo_system(self):
        etree = self.etree
        xml_header = '<?xml version="1.0" encoding="UTF-8"?>'
        sys_id = "some.dtd"
        doctype_string = '<!DOCTYPE html SYSTEM "%s">' % sys_id
        xml = _bytes(xml_header + doctype_string + '<html><body></body></html>')

        tree = etree.parse(BytesIO(xml))
        docinfo = tree.docinfo
        self.assertEqual(docinfo.encoding,    "UTF-8")
        self.assertEqual(docinfo.xml_version, "1.0")
        self.assertEqual(docinfo.public_id,   None)
        self.assertEqual(docinfo.system_url,  sys_id)
        self.assertEqual(docinfo.root_name,   'html')
        self.assertEqual(docinfo.doctype, doctype_string)

    def test_docinfo_empty(self):
        etree = self.etree
        xml = _bytes('<html><body></body></html>')
        tree = etree.parse(BytesIO(xml))
        docinfo = tree.docinfo
        self.assertEqual(docinfo.encoding,    "UTF-8")
        self.assertEqual(docinfo.xml_version, "1.0")
        self.assertEqual(docinfo.public_id,   None)
        self.assertEqual(docinfo.system_url,  None)
        self.assertEqual(docinfo.root_name,   'html')
        self.assertEqual(docinfo.doctype, '')

    def test_docinfo_name_only(self):
        etree = self.etree
        xml = _bytes('<!DOCTYPE root><root></root>')
        tree = etree.parse(BytesIO(xml))
        docinfo = tree.docinfo
        self.assertEqual(docinfo.encoding,    "UTF-8")
        self.assertEqual(docinfo.xml_version, "1.0")
        self.assertEqual(docinfo.public_id,   None)
        self.assertEqual(docinfo.system_url,  None)
        self.assertEqual(docinfo.root_name,   'root')
        self.assertEqual(docinfo.doctype, '<!DOCTYPE root>')

    def test_doctype_name_only_roundtrip(self):
        etree = self.etree
        xml = _bytes('<!DOCTYPE root>\n<root/>')
        tree = etree.parse(BytesIO(xml))
        self.assertEqual(xml, etree.tostring(tree))

    def test_doctype_output_override(self):
        etree = self.etree
        pub_id = "-//W3C//DTD XHTML 1.0 Transitional//EN"
        sys_id = "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"
        doctype_string = _bytes('<!DOCTYPE html PUBLIC "%s" "%s">' % (pub_id, sys_id))

        xml = _bytes('<!DOCTYPE root>\n<root/>')
        tree = etree.parse(BytesIO(xml))
        self.assertEqual(xml.replace(_bytes('<!DOCTYPE root>'), doctype_string),
                          etree.tostring(tree, doctype=doctype_string))

    def test_xml_base(self):
        etree = self.etree
        root = etree.XML(_bytes("<root/>"), base_url="http://no/such/url")
        self.assertEqual(root.base, "http://no/such/url")
        self.assertEqual(
            root.get('{http://www.w3.org/XML/1998/namespace}base'), None)
        root.base = "https://secret/url"
        self.assertEqual(root.base, "https://secret/url")
        self.assertEqual(
            root.get('{http://www.w3.org/XML/1998/namespace}base'),
            "https://secret/url")

    def test_xml_base_attribute(self):
        etree = self.etree
        root = etree.XML(_bytes("<root/>"), base_url="http://no/such/url")
        self.assertEqual(root.base, "http://no/such/url")
        self.assertEqual(
            root.get('{http://www.w3.org/XML/1998/namespace}base'), None)
        root.set('{http://www.w3.org/XML/1998/namespace}base',
                 "https://secret/url")
        self.assertEqual(root.base, "https://secret/url")
        self.assertEqual(
            root.get('{http://www.w3.org/XML/1998/namespace}base'),
            "https://secret/url")

    def test_html_base(self):
        etree = self.etree
        root = etree.HTML(_bytes("<html><body></body></html>"),
                          base_url="http://no/such/url")
        self.assertEqual(root.base, "http://no/such/url")

    def test_html_base_tag(self):
        etree = self.etree
        root = etree.HTML(_bytes('<html><head><base href="http://no/such/url"></head></html>'))
        self.assertEqual(root.base, "http://no/such/url")

    def test_parse_fileobject_unicode(self):
        # parse from a file object that returns unicode strings
        f = LargeFileLikeUnicode()
        tree = self.etree.parse(f)
        root = tree.getroot()
        self.assertTrue(root.tag.endswith('root'))

    def test_dtd_io(self):
        # check that DTDs that go in also go back out
        xml = _bytes('''\
        <!DOCTYPE test SYSTEM "test.dtd" [
          <!ENTITY entity "tasty">
          <!ELEMENT test (a)>
          <!ELEMENT a (#PCDATA)>
        ]>
        <test><a>test-test</a></test>\
        ''')
        tree = self.etree.parse(BytesIO(xml))
        self.assertEqual(self.etree.tostring(tree).replace(_bytes(" "), _bytes("")),
                         xml.replace(_bytes(" "), _bytes("")))

    def test_byte_zero(self):
        Element = self.etree.Element

        a = Element('a')
        self.assertRaises(ValueError, setattr, a, "text", 'ha\0ho')
        self.assertRaises(ValueError, setattr, a, "tail", 'ha\0ho')

        self.assertRaises(ValueError, Element, 'ha\0ho')

    def test_unicode_byte_zero(self):
        Element = self.etree.Element

        a = Element('a')
        self.assertRaises(ValueError, setattr, a, "text",
                          _str('ha\0ho'))
        self.assertRaises(ValueError, setattr, a, "tail",
                          _str('ha\0ho'))

        self.assertRaises(ValueError, Element,
                          _str('ha\0ho'))

    def test_byte_invalid(self):
        Element = self.etree.Element

        a = Element('a')
        self.assertRaises(ValueError, setattr, a, "text", 'ha\x07ho')
        self.assertRaises(ValueError, setattr, a, "text", 'ha\x02ho')

        self.assertRaises(ValueError, setattr, a, "tail", 'ha\x07ho')
        self.assertRaises(ValueError, setattr, a, "tail", 'ha\x02ho')

        self.assertRaises(ValueError, Element, 'ha\x07ho')
        self.assertRaises(ValueError, Element, 'ha\x02ho')

    def test_unicode_byte_invalid(self):
        Element = self.etree.Element

        a = Element('a')
        self.assertRaises(ValueError, setattr, a, "text",
                          _str('ha\x07ho'))
        self.assertRaises(ValueError, setattr, a, "text",
                          _str('ha\x02ho'))

        self.assertRaises(ValueError, setattr, a, "tail",
                          _str('ha\x07ho'))
        self.assertRaises(ValueError, setattr, a, "tail",
                          _str('ha\x02ho'))

        self.assertRaises(ValueError, Element,
                          _str('ha\x07ho'))
        self.assertRaises(ValueError, Element,
                          _str('ha\x02ho'))

    def test_unicode_byte_invalid_sequence(self):
        Element = self.etree.Element

        a = Element('a')
        self.assertRaises(ValueError, setattr, a, "text",
                          _str('ha\u1234\x07ho'))
        self.assertRaises(ValueError, setattr, a, "text",
                          _str('ha\u1234\x02ho'))

        self.assertRaises(ValueError, setattr, a, "tail",
                          _str('ha\u1234\x07ho'))
        self.assertRaises(ValueError, setattr, a, "tail",
                          _str('ha\u1234\x02ho'))

        self.assertRaises(ValueError, Element,
                          _str('ha\u1234\x07ho'))
        self.assertRaises(ValueError, Element,
                          _str('ha\u1234\x02ho'))

    def test_encoding_tostring_utf16(self):
        # ElementTree fails to serialize this
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')

        result = tostring(a, encoding='UTF-16')
        self.assertEqual(_bytes('<a><b></b><c></c></a>'),
                          canonicalize(result))

    def test_tostring_none(self):
        # ElementTree raises an AssertionError here
        tostring = self.etree.tostring
        self.assertRaises(TypeError, self.etree.tostring, None)

    def test_tostring_pretty(self):
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')

        result = tostring(a)
        self.assertEqual(result, _bytes("<a><b/><c/></a>"))

        result = tostring(a, pretty_print=False)
        self.assertEqual(result, _bytes("<a><b/><c/></a>"))

        result = tostring(a, pretty_print=True)
        self.assertEqual(result, _bytes("<a>\n  <b/>\n  <c/>\n</a>\n"))

    def test_tostring_with_tail(self):
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        a.tail = "aTAIL"
        b = SubElement(a, 'b')
        b.tail = "bTAIL"
        c = SubElement(a, 'c')

        result = tostring(a)
        self.assertEqual(result, _bytes("<a><b/>bTAIL<c/></a>aTAIL"))

        result = tostring(a, with_tail=False)
        self.assertEqual(result, _bytes("<a><b/>bTAIL<c/></a>"))

        result = tostring(a, with_tail=True)
        self.assertEqual(result, _bytes("<a><b/>bTAIL<c/></a>aTAIL"))

    def test_tostring_method_html_with_tail(self):
        tostring = self.etree.tostring
        html = self.etree.fromstring(
            '<html><body>'
            '<div><p>Some text<i>\r\n</i></p></div>\r\n'
            '</body></html>',
            parser=self.etree.HTMLParser())
        self.assertEqual(html.tag, 'html')
        div = html.find('.//div')
        self.assertEqual(div.tail, '\r\n')
        result = tostring(div, method='html')
        self.assertEqual(
            result,
            _bytes("<div><p>Some text<i>\r\n</i></p></div>\r\n"))
        result = tostring(div, method='html', with_tail=True)
        self.assertEqual(
            result,
            _bytes("<div><p>Some text<i>\r\n</i></p></div>\r\n"))
        result = tostring(div, method='html', with_tail=False)
        self.assertEqual(
            result,
            _bytes("<div><p>Some text<i>\r\n</i></p></div>"))

    def test_standalone(self):
        tostring = self.etree.tostring
        XML = self.etree.XML
        ElementTree = self.etree.ElementTree
        Element = self.etree.Element

        tree = Element("root").getroottree()
        self.assertEqual(None, tree.docinfo.standalone)

        tree = XML(_bytes("<root/>")).getroottree()
        self.assertEqual(None, tree.docinfo.standalone)

        tree = XML(_bytes(
            "<?xml version='1.0' encoding='ASCII' standalone='yes'?>\n<root/>"
            )).getroottree()
        self.assertEqual(True, tree.docinfo.standalone)

        tree = XML(_bytes(
            "<?xml version='1.0' encoding='ASCII' standalone='no'?>\n<root/>"
            )).getroottree()
        self.assertEqual(False, tree.docinfo.standalone)

    def test_tostring_standalone(self):
        tostring = self.etree.tostring
        XML = self.etree.XML
        ElementTree = self.etree.ElementTree

        root = XML(_bytes("<root/>"))

        tree = ElementTree(root)
        self.assertEqual(None, tree.docinfo.standalone)

        result = tostring(root, xml_declaration=True, encoding="ASCII")
        self.assertEqual(result, _bytes(
            "<?xml version='1.0' encoding='ASCII'?>\n<root/>"))

        result = tostring(root, xml_declaration=True, encoding="ASCII",
                          standalone=True)
        self.assertEqual(result, _bytes(
            "<?xml version='1.0' encoding='ASCII' standalone='yes'?>\n<root/>"))

        tree = ElementTree(XML(result))
        self.assertEqual(True, tree.docinfo.standalone)

        result = tostring(root, xml_declaration=True, encoding="ASCII",
                          standalone=False)
        self.assertEqual(result, _bytes(
            "<?xml version='1.0' encoding='ASCII' standalone='no'?>\n<root/>"))

        tree = ElementTree(XML(result))
        self.assertEqual(False, tree.docinfo.standalone)

    def test_tostring_standalone_in_out(self):
        tostring = self.etree.tostring
        XML = self.etree.XML
        ElementTree = self.etree.ElementTree

        root = XML(_bytes(
            "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>\n<root/>"))

        tree = ElementTree(root)
        self.assertEqual(True, tree.docinfo.standalone)

        result = tostring(root, xml_declaration=True, encoding="ASCII")
        self.assertEqual(result, _bytes(
            "<?xml version='1.0' encoding='ASCII'?>\n<root/>"))

        result = tostring(root, xml_declaration=True, encoding="ASCII",
                          standalone=True)
        self.assertEqual(result, _bytes(
            "<?xml version='1.0' encoding='ASCII' standalone='yes'?>\n<root/>"))

    def test_tostring_method_text_encoding(self):
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        a.text = "A"
        a.tail = "tail"
        b = SubElement(a, 'b')
        b.text = "B"
        b.tail = _str("Søk på nettet")
        c = SubElement(a, 'c')
        c.text = "C"

        result = tostring(a, method="text", encoding="UTF-16")

        self.assertEqual(_str('ABSøk på nettetCtail').encode("UTF-16"),
                          result)

    def test_tostring_method_text_unicode(self):
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        a.text = _str('Søk på nettetA')
        a.tail = "tail"
        b = SubElement(a, 'b')
        b.text = "B"
        b.tail = _str('Søk på nettetB')
        c = SubElement(a, 'c')
        c.text = "C"
        
        self.assertRaises(UnicodeEncodeError,
                          tostring, a, method="text")
        
        self.assertEqual(
            _str('Søk på nettetABSøk på nettetBCtail').encode('utf-8'),
            tostring(a, encoding="UTF-8", method="text"))

    def test_tounicode(self):
        tounicode = self.etree.tounicode
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        
        self.assertTrue(isinstance(tounicode(a), _unicode))
        self.assertEqual(_bytes('<a><b></b><c></c></a>'),
                          canonicalize(tounicode(a)))

    def test_tounicode_element(self):
        tounicode = self.etree.tounicode
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(c, 'd')
        self.assertTrue(isinstance(tounicode(b), _unicode))
        self.assertTrue(isinstance(tounicode(c), _unicode))
        self.assertEqual(_bytes('<b></b>'),
                          canonicalize(tounicode(b)))
        self.assertEqual(_bytes('<c><d></d></c>'),
                          canonicalize(tounicode(c)))

    def test_tounicode_none(self):
        tounicode = self.etree.tounicode
        self.assertRaises(TypeError, self.etree.tounicode, None)

    def test_tounicode_element_tail(self):
        tounicode = self.etree.tounicode
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(c, 'd')
        b.tail = 'Foo'

        self.assertTrue(isinstance(tounicode(b), _unicode))
        self.assertTrue(tounicode(b) == '<b/>Foo' or
                     tounicode(b) == '<b />Foo')

    def test_tounicode_pretty(self):
        tounicode = self.etree.tounicode
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')

        result = tounicode(a)
        self.assertEqual(result, "<a><b/><c/></a>")

        result = tounicode(a, pretty_print=False)
        self.assertEqual(result, "<a><b/><c/></a>")

        result = tounicode(a, pretty_print=True)
        self.assertEqual(result, "<a>\n  <b/>\n  <c/>\n</a>\n")

    def test_tostring_unicode(self):
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        
        self.assertTrue(isinstance(tostring(a, encoding=_unicode), _unicode))
        self.assertEqual(_bytes('<a><b></b><c></c></a>'),
                          canonicalize(tostring(a, encoding=_unicode)))

    def test_tostring_unicode_element(self):
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(c, 'd')
        self.assertTrue(isinstance(tostring(b, encoding=_unicode), _unicode))
        self.assertTrue(isinstance(tostring(c, encoding=_unicode), _unicode))
        self.assertEqual(_bytes('<b></b>'),
                          canonicalize(tostring(b, encoding=_unicode)))
        self.assertEqual(_bytes('<c><d></d></c>'),
                          canonicalize(tostring(c, encoding=_unicode)))

    def test_tostring_unicode_none(self):
        tostring = self.etree.tostring
        self.assertRaises(TypeError, self.etree.tostring,
                          None, encoding=_unicode)

    def test_tostring_unicode_element_tail(self):
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(c, 'd')
        b.tail = 'Foo'

        self.assertTrue(isinstance(tostring(b, encoding=_unicode), _unicode))
        self.assertTrue(tostring(b, encoding=_unicode) == '<b/>Foo' or
                     tostring(b, encoding=_unicode) == '<b />Foo')

    def test_tostring_unicode_pretty(self):
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')

        result = tostring(a, encoding=_unicode)
        self.assertEqual(result, "<a><b/><c/></a>")

        result = tostring(a, encoding=_unicode, pretty_print=False)
        self.assertEqual(result, "<a><b/><c/></a>")

        result = tostring(a, encoding=_unicode, pretty_print=True)
        self.assertEqual(result, "<a>\n  <b/>\n  <c/>\n</a>\n")

    def test_pypy_proxy_collect(self):
        root = etree.Element('parent')
        etree.SubElement(root, 'child')

        self.assertEqual(len(root), 1)
        self.assertEqual(root[0].tag, 'child')

        # in PyPy, GC used to kill the Python proxy instance without cleanup
        gc.collect()
        self.assertEqual(len(root), 1)
        self.assertEqual(root[0].tag, 'child')

    def test_element_refcycle(self):
        class SubEl(etree.ElementBase):
            pass

        el1 = SubEl()
        el2 = SubEl()
        self.assertEqual('SubEl', el1.tag)
        self.assertEqual('SubEl', el2.tag)
        el1.other = el2
        el2.other = el1

        del el1, el2
        gc.collect()
        # not really testing anything here, but it shouldn't crash

    def test_proxy_collect_siblings(self):
        root = etree.Element('parent')
        c1 = etree.SubElement(root, 'child1')
        c2 = etree.SubElement(root, 'child2')

        root.remove(c1)
        root.remove(c2)
        c1.addnext(c2)
        del c1
        # trigger deallocation attempt of c1
        c2.getprevious()
        # make sure it wasn't deallocated
        self.assertEqual('child1', c2.getprevious().tag)

    def test_proxy_collect_siblings_text(self):
        root = etree.Element('parent')
        c1 = etree.SubElement(root, 'child1')
        c2 = etree.SubElement(root, 'child2')

        root.remove(c1)
        root.remove(c2)
        c1.addnext(c2)
        c1.tail = 'abc'
        c2.tail = 'xyz'
        del c1
        # trigger deallocation attempt of c1
        c2.getprevious()
        # make sure it wasn't deallocated
        self.assertEqual('child1', c2.getprevious().tag)
        self.assertEqual('abc', c2.getprevious().tail)

    # helper methods

    def _writeElement(self, element, encoding='us-ascii', compression=0):
        """Write out element for comparison.
        """
        ElementTree = self.etree.ElementTree
        f = BytesIO()
        tree = ElementTree(element=element)
        tree.write(f, encoding=encoding, compression=compression)
        data = f.getvalue()
        if compression:
            data = zlib.decompress(data)
        return canonicalize(data)


class _XIncludeTestCase(HelperTestCase):
    def test_xinclude_text(self):
        filename = fileInTestDir('test_broken.xml')
        root = etree.XML(_bytes('''\
        <doc xmlns:xi="http://www.w3.org/2001/XInclude">
          <xi:include href="%s" parse="text"/>
        </doc>
        ''' % path2url(filename)))
        old_text = root.text
        content = read_file(filename)
        old_tail = root[0].tail

        self.include( etree.ElementTree(root) )
        self.assertEqual(old_text + content + old_tail,
                          root.text)

    def test_xinclude(self):
        tree = etree.parse(fileInTestDir('include/test_xinclude.xml'))
        self.assertNotEqual(
            'a',
            tree.getroot()[1].tag)
        # process xincludes
        self.include( tree )
        # check whether we find it replaced with included data
        self.assertEqual(
            'a',
            tree.getroot()[1].tag)

    def test_xinclude_resolver(self):
        class res(etree.Resolver):
            include_text = read_file(fileInTestDir('test.xml'))
            called = {}
            def resolve(self, url, id, context):
                if url.endswith(".dtd"):
                    self.called["dtd"] = True
                    return self.resolve_filename(
                        fileInTestDir('test.dtd'), context)
                elif url.endswith("test_xinclude.xml"):
                    self.called["input"] = True
                    return None # delegate to default resolver
                else:
                    self.called["include"] = True
                    return self.resolve_string(self.include_text, context)

        res_instance = res()
        parser = etree.XMLParser(load_dtd = True)
        parser.resolvers.add(res_instance)

        tree = etree.parse(fileInTestDir('include/test_xinclude.xml'),
                           parser = parser)

        self.include(tree)

        called = list(res_instance.called.items())
        called.sort()
        self.assertEqual(
            [("dtd", True), ("include", True), ("input", True)],
            called)


class ETreeXIncludeTestCase(_XIncludeTestCase):
    def include(self, tree):
        tree.xinclude()


class ElementIncludeTestCase(_XIncludeTestCase):
    from lxml import ElementInclude
    def include(self, tree):
        self.ElementInclude.include(tree.getroot())


class ETreeC14NTestCase(HelperTestCase):
    def test_c14n(self):
        tree = self.parse(_bytes('<a><b/></a>'))
        f = BytesIO()
        tree.write_c14n(f)
        s = f.getvalue()
        self.assertEqual(_bytes('<a><b></b></a>'),
                          s)

    def test_c14n_gzip(self):
        tree = self.parse(_bytes('<a>'+'<b/>'*200+'</a>'))
        f = BytesIO()
        tree.write_c14n(f, compression=9)
        gzfile = gzip.GzipFile(fileobj=BytesIO(f.getvalue()))
        try:
            s = gzfile.read()
        finally:
            gzfile.close()
        self.assertEqual(_bytes('<a>'+'<b></b>'*200+'</a>'),
                          s)

    def test_c14n_file(self):
        tree = self.parse(_bytes('<a><b/></a>'))
        handle, filename = tempfile.mkstemp()
        try:
            tree.write_c14n(filename)
            data = read_file(filename, 'rb')
        finally:
            os.close(handle)
            os.remove(filename)
        self.assertEqual(_bytes('<a><b></b></a>'),
                          data)

    def test_c14n_file_gzip(self):
        tree = self.parse(_bytes('<a>'+'<b/>'*200+'</a>'))
        handle, filename = tempfile.mkstemp()
        try:
            tree.write_c14n(filename, compression=9)
            f = gzip.open(filename, 'rb')
            try:
                data = f.read()
            finally:
                f.close()
        finally:
            os.close(handle)
            os.remove(filename)
        self.assertEqual(_bytes('<a>'+'<b></b>'*200+'</a>'),
                          data)

    def test_c14n_with_comments(self):
        tree = self.parse(_bytes('<!--hi--><a><!--ho--><b/></a><!--hu-->'))
        f = BytesIO()
        tree.write_c14n(f)
        s = f.getvalue()
        self.assertEqual(_bytes('<!--hi-->\n<a><!--ho--><b></b></a>\n<!--hu-->'),
                          s)
        f = BytesIO()
        tree.write_c14n(f, with_comments=True)
        s = f.getvalue()
        self.assertEqual(_bytes('<!--hi-->\n<a><!--ho--><b></b></a>\n<!--hu-->'),
                          s)
        f = BytesIO()
        tree.write_c14n(f, with_comments=False)
        s = f.getvalue()
        self.assertEqual(_bytes('<a><b></b></a>'),
                          s)

    def test_c14n_tostring_with_comments(self):
        tree = self.parse(_bytes('<!--hi--><a><!--ho--><b/></a><!--hu-->'))
        s = etree.tostring(tree, method='c14n')
        self.assertEqual(_bytes('<!--hi-->\n<a><!--ho--><b></b></a>\n<!--hu-->'),
                          s)
        s = etree.tostring(tree, method='c14n', with_comments=True)
        self.assertEqual(_bytes('<!--hi-->\n<a><!--ho--><b></b></a>\n<!--hu-->'),
                          s)
        s = etree.tostring(tree, method='c14n', with_comments=False)
        self.assertEqual(_bytes('<a><b></b></a>'),
                          s)

    def test_c14n_element_tostring_with_comments(self):
        tree = self.parse(_bytes('<!--hi--><a><!--ho--><b/></a><!--hu-->'))
        s = etree.tostring(tree.getroot(), method='c14n')
        self.assertEqual(_bytes('<a><!--ho--><b></b></a>'),
                          s)
        s = etree.tostring(tree.getroot(), method='c14n', with_comments=True)
        self.assertEqual(_bytes('<a><!--ho--><b></b></a>'),
                          s)
        s = etree.tostring(tree.getroot(), method='c14n', with_comments=False)
        self.assertEqual(_bytes('<a><b></b></a>'),
                          s)

    def test_c14n_exclusive(self):
        tree = self.parse(_bytes(
                '<a xmlns="http://abc" xmlns:y="http://bcd" xmlns:z="http://cde"><z:b/></a>'))
        f = BytesIO()
        tree.write_c14n(f)
        s = f.getvalue()
        self.assertEqual(_bytes('<a xmlns="http://abc" xmlns:y="http://bcd" xmlns:z="http://cde"><z:b></z:b></a>'),
                          s)
        f = BytesIO()
        tree.write_c14n(f, exclusive=False)
        s = f.getvalue()
        self.assertEqual(_bytes('<a xmlns="http://abc" xmlns:y="http://bcd" xmlns:z="http://cde"><z:b></z:b></a>'),
                          s)
        f = BytesIO()
        tree.write_c14n(f, exclusive=True)
        s = f.getvalue()
        self.assertEqual(_bytes('<a xmlns="http://abc"><z:b xmlns:z="http://cde"></z:b></a>'),
                          s)

        f = BytesIO()
        tree.write_c14n(f, exclusive=True, inclusive_ns_prefixes=['z'])
        s = f.getvalue()
        self.assertEqual(_bytes('<a xmlns="http://abc" xmlns:z="http://cde"><z:b></z:b></a>'),
                          s)

    def test_c14n_tostring_exclusive(self):
        tree = self.parse(_bytes(
                '<a xmlns="http://abc" xmlns:y="http://bcd" xmlns:z="http://cde"><z:b/></a>'))
        s = etree.tostring(tree, method='c14n')
        self.assertEqual(_bytes('<a xmlns="http://abc" xmlns:y="http://bcd" xmlns:z="http://cde"><z:b></z:b></a>'),
                          s)
        s = etree.tostring(tree, method='c14n', exclusive=False)
        self.assertEqual(_bytes('<a xmlns="http://abc" xmlns:y="http://bcd" xmlns:z="http://cde"><z:b></z:b></a>'),
                          s)
        s = etree.tostring(tree, method='c14n', exclusive=True)
        self.assertEqual(_bytes('<a xmlns="http://abc"><z:b xmlns:z="http://cde"></z:b></a>'),
                          s)

        s = etree.tostring(tree, method='c14n', exclusive=True, inclusive_ns_prefixes=['y'])
        self.assertEqual(_bytes('<a xmlns="http://abc" xmlns:y="http://bcd"><z:b xmlns:z="http://cde"></z:b></a>'),
                          s)

    def test_c14n_element_tostring_exclusive(self):
        tree = self.parse(_bytes(
                '<a xmlns="http://abc" xmlns:y="http://bcd" xmlns:z="http://cde"><z:b/></a>'))
        s = etree.tostring(tree.getroot(), method='c14n')
        self.assertEqual(_bytes('<a xmlns="http://abc" xmlns:y="http://bcd" xmlns:z="http://cde"><z:b></z:b></a>'),
                          s)
        s = etree.tostring(tree.getroot(), method='c14n', exclusive=False)
        self.assertEqual(_bytes('<a xmlns="http://abc" xmlns:y="http://bcd" xmlns:z="http://cde"><z:b></z:b></a>'),
                          s)
        s = etree.tostring(tree.getroot(), method='c14n', exclusive=True)
        self.assertEqual(_bytes('<a xmlns="http://abc"><z:b xmlns:z="http://cde"></z:b></a>'),
                          s)

        s = etree.tostring(tree.getroot()[0], method='c14n', exclusive=False)
        self.assertEqual(_bytes('<z:b xmlns="http://abc" xmlns:y="http://bcd" xmlns:z="http://cde"></z:b>'),
                          s)
        s = etree.tostring(tree.getroot()[0], method='c14n', exclusive=True)
        self.assertEqual(_bytes('<z:b xmlns:z="http://cde"></z:b>'),
                          s)

        s = etree.tostring(tree.getroot()[0], method='c14n', exclusive=True, inclusive_ns_prefixes=['y'])
        self.assertEqual(_bytes('<z:b xmlns:y="http://bcd" xmlns:z="http://cde"></z:b>'),
                          s)

    def test_c14n_tostring_inclusive_ns_prefixes(self):
        """ Regression test to fix memory allocation issues (use 3+ inclusive NS spaces)"""
        tree = self.parse(_bytes(
                '<a xmlns:x="http://abc" xmlns:y="http://bcd" xmlns:z="http://cde"><z:b/></a>'))

        s = etree.tostring(tree, method='c14n', exclusive=True, inclusive_ns_prefixes=['x', 'y', 'z'])
        self.assertEqual(_bytes('<a xmlns:x="http://abc" xmlns:y="http://bcd" xmlns:z="http://cde"><z:b></z:b></a>'),
                          s)


class ETreeWriteTestCase(HelperTestCase):
    def test_write(self):
        tree = self.parse(_bytes('<a><b/></a>'))
        f = BytesIO()
        tree.write(f)
        s = f.getvalue()
        self.assertEqual(_bytes('<a><b/></a>'),
                          s)

    def test_write_gzip(self):
        tree = self.parse(_bytes('<a>'+'<b/>'*200+'</a>'))
        f = BytesIO()
        tree.write(f, compression=9)
        gzfile = gzip.GzipFile(fileobj=BytesIO(f.getvalue()))
        try:
            s = gzfile.read()
        finally:
            gzfile.close()
        self.assertEqual(_bytes('<a>'+'<b/>'*200+'</a>'),
                          s)

    def test_write_gzip_level(self):
        tree = self.parse(_bytes('<a>'+'<b/>'*200+'</a>'))
        f = BytesIO()
        tree.write(f, compression=0)
        s0 = f.getvalue()

        f = BytesIO()
        tree.write(f)
        self.assertEqual(f.getvalue(), s0)

        f = BytesIO()
        tree.write(f, compression=1)
        s = f.getvalue()
        self.assertTrue(len(s) <= len(s0))
        gzfile = gzip.GzipFile(fileobj=BytesIO(s))
        try:
            s1 = gzfile.read()
        finally:
            gzfile.close()

        f = BytesIO()
        tree.write(f, compression=9)
        s = f.getvalue()
        self.assertTrue(len(s) <= len(s0))
        gzfile = gzip.GzipFile(fileobj=BytesIO(s))
        try:
            s9 = gzfile.read()
        finally:
            gzfile.close()

        self.assertEqual(_bytes('<a>'+'<b/>'*200+'</a>'),
                          s0)
        self.assertEqual(_bytes('<a>'+'<b/>'*200+'</a>'),
                          s1)
        self.assertEqual(_bytes('<a>'+'<b/>'*200+'</a>'),
                          s9)

    def test_write_file(self):
        tree = self.parse(_bytes('<a><b/></a>'))
        handle, filename = tempfile.mkstemp()
        try:
            tree.write(filename)
            data = read_file(filename, 'rb')
        finally:
            os.close(handle)
            os.remove(filename)
        self.assertEqual(_bytes('<a><b/></a>'),
                          data)

    def test_write_file_gzip(self):
        tree = self.parse(_bytes('<a>'+'<b/>'*200+'</a>'))
        handle, filename = tempfile.mkstemp()
        try:
            tree.write(filename, compression=9)
            f = gzip.open(filename, 'rb')
            try:
                data = f.read()
            finally:
                f.close()
        finally:
            os.close(handle)
            os.remove(filename)
        self.assertEqual(_bytes('<a>'+'<b/>'*200+'</a>'),
                          data)

    def test_write_file_gzip_parse(self):
        tree = self.parse(_bytes('<a>'+'<b/>'*200+'</a>'))
        handle, filename = tempfile.mkstemp()
        try:
            tree.write(filename, compression=9)
            data = etree.tostring(etree.parse(filename))
        finally:
            os.close(handle)
            os.remove(filename)
        self.assertEqual(_bytes('<a>'+'<b/>'*200+'</a>'),
                          data)

    def test_write_file_gzipfile_parse(self):
        tree = self.parse(_bytes('<a>'+'<b/>'*200+'</a>'))
        handle, filename = tempfile.mkstemp()
        try:
            tree.write(filename, compression=9)
            data = etree.tostring(etree.parse(
                gzip.GzipFile(filename)))
        finally:
            os.close(handle)
            os.remove(filename)
        self.assertEqual(_bytes('<a>'+'<b/>'*200+'</a>'),
                          data)

class ETreeErrorLogTest(HelperTestCase):
    etree = etree

    def test_parse_error_logging(self):
        parse = self.etree.parse
        f = BytesIO('<a><b></c></b></a>')
        self.etree.clear_error_log()
        try:
            parse(f)
            logs = None
        except SyntaxError:
            e = sys.exc_info()[1]
            logs = e.error_log
        f.close()
        self.assertTrue([ log for log in logs
                       if 'mismatch' in log.message ])
        self.assertTrue([ log for log in logs
                       if 'PARSER'   in log.domain_name])
        self.assertTrue([ log for log in logs
                       if 'ERR_TAG_NAME_MISMATCH' in log.type_name ])
        self.assertTrue([ log for log in logs
                       if 1 == log.line ])
        self.assertTrue([ log for log in logs
                       if 15 == log.column ])

    def _test_python_error_logging(self):
        """This can't really be tested as long as there isn't a way to
        reset the logging setup ...
        """
        parse = self.etree.parse

        messages = []
        class Logger(self.etree.PyErrorLog):
            def log(self, entry, message, *args):
                messages.append(message)

        self.etree.use_global_python_log(Logger())
        f = BytesIO('<a><b></c></b></a>')
        try:
            parse(f)
        except SyntaxError:
            pass
        f.close()

        self.assertTrue([ message for message in messages
                       if 'mismatch' in message ])
        self.assertTrue([ message for message in messages
                       if ':PARSER:'   in message])
        self.assertTrue([ message for message in messages
                       if ':ERR_TAG_NAME_MISMATCH:' in message ])
        self.assertTrue([ message for message in messages
                       if ':1:15:' in message ])


class XMLPullParserTest(unittest.TestCase):
    etree = etree

    def assert_event_tags(self, events, expected):
        self.assertEqual([(action, elem.tag) for action, elem in events],
                         expected)

    def test_pull_from_simple_target(self):
        class Target(object):
            def start(self, tag, attrib):
                return 'start(%s)' % tag
            def end(self, tag):
                return 'end(%s)' % tag
            def close(self):
                return 'close()'

        parser = self.etree.XMLPullParser(target=Target())
        events = parser.read_events()

        parser.feed('<root><element>')
        self.assertFalse(list(events))
        self.assertFalse(list(events))
        parser.feed('</element><child>')
        self.assertEqual([('end', 'end(element)')], list(events))
        parser.feed('</child>')
        self.assertEqual([('end', 'end(child)')], list(events))
        parser.feed('</root>')
        self.assertEqual([('end', 'end(root)')], list(events))
        self.assertFalse(list(events))
        self.assertEqual('close()', parser.close())

    def test_pull_from_simple_target_start_end(self):
        class Target(object):
            def start(self, tag, attrib):
                return 'start(%s)' % tag
            def end(self, tag):
                return 'end(%s)' % tag
            def close(self):
                return 'close()'

        parser = self.etree.XMLPullParser(
            ['start', 'end'], target=Target())
        events = parser.read_events()

        parser.feed('<root><element>')
        self.assertEqual(
            [('start', 'start(root)'), ('start', 'start(element)')],
            list(events))
        self.assertFalse(list(events))
        parser.feed('</element><child>')
        self.assertEqual(
            [('end', 'end(element)'), ('start', 'start(child)')],
            list(events))
        parser.feed('</child>')
        self.assertEqual(
            [('end', 'end(child)')],
            list(events))
        parser.feed('</root>')
        self.assertEqual(
            [('end', 'end(root)')],
            list(events))
        self.assertFalse(list(events))
        self.assertEqual('close()', parser.close())

    def test_pull_from_tree_builder(self):
        parser = self.etree.XMLPullParser(
            ['start', 'end'], target=etree.TreeBuilder())
        events = parser.read_events()

        parser.feed('<root><element>')
        self.assert_event_tags(
            events, [('start', 'root'), ('start', 'element')])
        self.assertFalse(list(events))
        parser.feed('</element><child>')
        self.assert_event_tags(
            events, [('end', 'element'), ('start', 'child')])
        parser.feed('</child>')
        self.assert_event_tags(
            events, [('end', 'child')])
        parser.feed('</root>')
        self.assert_event_tags(
            events, [('end', 'root')])
        self.assertFalse(list(events))
        root = parser.close()
        self.assertEqual('root', root.tag)

    def test_pull_from_tree_builder_subclass(self):
        class Target(etree.TreeBuilder):
            def end(self, tag):
                el = super(Target, self).end(tag)
                el.tag += '-huhu'
                return el

        parser = self.etree.XMLPullParser(
            ['start', 'end'], target=Target())
        events = parser.read_events()

        parser.feed('<root><element>')
        self.assert_event_tags(
            events, [('start', 'root'), ('start', 'element')])
        self.assertFalse(list(events))
        parser.feed('</element><child>')
        self.assert_event_tags(
            events, [('end', 'element-huhu'), ('start', 'child')])
        parser.feed('</child>')
        self.assert_event_tags(
            events, [('end', 'child-huhu')])
        parser.feed('</root>')
        self.assert_event_tags(
            events, [('end', 'root-huhu')])
        self.assertFalse(list(events))
        root = parser.close()
        self.assertEqual('root-huhu', root.tag)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeOnlyTestCase)])
    suite.addTests([unittest.makeSuite(ETreeXIncludeTestCase)])
    suite.addTests([unittest.makeSuite(ElementIncludeTestCase)])
    suite.addTests([unittest.makeSuite(ETreeC14NTestCase)])
    suite.addTests([unittest.makeSuite(ETreeWriteTestCase)])
    suite.addTests([unittest.makeSuite(ETreeErrorLogTest)])
    suite.addTests([unittest.makeSuite(XMLPullParserTest)])
    suite.addTests(doctest.DocTestSuite(etree))
    suite.addTests(
        [make_doctest('../../../doc/tutorial.txt')])
    if sys.version_info >= (2,6):
        # now requires the 'with' statement
        suite.addTests(
            [make_doctest('../../../doc/api.txt')])
    suite.addTests(
        [make_doctest('../../../doc/FAQ.txt')])
    suite.addTests(
        [make_doctest('../../../doc/parsing.txt')])
    suite.addTests(
        [make_doctest('../../../doc/resolvers.txt')])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
