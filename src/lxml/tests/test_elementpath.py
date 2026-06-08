"""
Tests for the ElementPath implementation.
"""

import sys
import unittest
from copy import deepcopy
from .common_imports import etree, HelperTestCase

ET = etree  # compatibility with CPython tests.

SAMPLE_XML = """\
<body>
  <tag class='a'>text</tag>
  <tag class='b' />
  <section>
    <tag class='b' id='inner'>subtext</tag>
  </section>
</body>
"""

SAMPLE_SECTION = """\
<section>
  <tag class='b' id='inner'>subtext</tag>
  <nexttag />
  <nextsection>
    <tag />
  </nextsection>
</section>
"""

SAMPLE_XML_NS = """
<body xmlns="http://effbot.org/ns">
  <tag>text</tag>
  <tag />
  <section>
    <tag>subtext</tag>
  </section>
</body>
"""

SAMPLE_XML_NS_ELEMS = """
<root>
<h:table xmlns:h="hello">
  <h:tr>
    <h:td>Apples</h:td>
    <h:td>Bananas</h:td>
  </h:tr>
</h:table>

<f:table xmlns:f="foo">
  <f:name>African Coffee Table</f:name>
  <f:width>80</f:width>
  <f:length>120</f:length>
</f:table>
</root>
"""


def summarize(elem):
    return elem.tag

def summarize_list(seq):
    return list(map(summarize, seq))

def normalize_crlf(tree):
    for elem in tree.getiterator():
        if elem.text: elem.text = elem.text.replace("\r\n", "\n")
        if elem.tail: elem.tail = elem.tail.replace("\r\n", "\n")


class EtreeElementPathTestCase(HelperTestCase):
    etree = etree
    from lxml import _elementpath

    _empty_namespaces = None

    def test_cache(self):
        self._elementpath._cache.clear()
        el = self.etree.XML(b'<a><b><c/><c/></b></a>')
        self.assertFalse(self._elementpath._cache)

        self.assertTrue(el.findall('b/c'))
        self.assertEqual(1, len(self._elementpath._cache))
        self.assertTrue(el.findall('b/c'))
        self.assertEqual(1, len(self._elementpath._cache))
        self.assertFalse(el.findall('xxx'))
        self.assertEqual(2, len(self._elementpath._cache))
        self.assertFalse(el.findall('xxx'))
        self.assertEqual(2, len(self._elementpath._cache))
        self.assertTrue(el.findall('b/c'))
        self.assertEqual(2, len(self._elementpath._cache))

    def _assert_tokens(self, tokens, path, namespaces=None):
        if namespaces is None:
            namespaces = self._empty_namespaces
        self.assertEqual(tokens, list(self._elementpath.xpath_tokenizer(path, namespaces)))

    def test_tokenizer(self):
        assert_tokens = self._assert_tokens
        assert_tokens(
            [('/', '')],
            '/',
        )
        assert_tokens(
            [('.', ''), ('/', ''), ('', 'a'), ('/', ''), ('', 'b'), ('/', ''), ('', 'c')],
            './a/b/c',
        )
        assert_tokens(
            [('/', ''), ('', 'a'), ('/', ''), ('', 'b'), ('/', ''), ('', 'c')],
            '/a/b/c',
        )
        assert_tokens(
            [('/', ''), ('', '{nsx}a'), ('/', ''), ('', '{nsy}b'), ('/', ''), ('', 'c')],
            '/x:a/y:b/c',
            {'x': 'nsx', 'y': 'nsy'},
        )
        assert_tokens(
            [('/', ''), ('', '{nsx}a'), ('/', ''), ('', '{nsy}b'), ('/', ''), ('', '{nsnone}c')],
            '/x:a/y:b/c',
            {'x': 'nsx', 'y': 'nsy', None: 'nsnone'},
        )

    def test_tokenizer_predicates(self):
        assert_tokens = self._assert_tokens
        assert_tokens(
            [('', 'a'), ('[', ''), ('', 'b'), (']', '')],
            'a[b]',
        )
        assert_tokens(
            [('', 'a'), ('[', ''), ('', 'b'), ('=', ''), ('"abc"', ''), (']', '')],
            'a[b="abc"]',
        )
        assert_tokens(
            [('', 'a'), ('[', ''), ('.', ''), ('', ''), ('=', ''), ('', ''), ('"abc"', ''), (']', '')],
            'a[. = "abc"]',
        )

    def test_tokenizer_index(self):
        assert_tokens = self._assert_tokens
        assert_tokens(
            [('/', ''), ('', 'a'), ('/', ''), ('', 'b'), ('/', ''), ('', 'c'), ('[', ''), ('', '1'), (']', '')],
            '/a/b/c[1]',
        )
        assert_tokens(
            [('/', ''), ('', '{nsnone}a'), ('/', ''), ('', '{nsnone}b'), ('/', ''), ('', '{nsnone}c'), ('[', ''), ('', '1'), (']', '')],
            '/a/b/c[1]',
            namespaces={None:'nsnone'},
        )
        assert_tokens(
            [('/', ''), ('', '{nsnone}a'), ('/', ''), ('', '{nsnone}b'), ('[', ''), ('', '2'), (']', ''), ('/', ''), ('', '{nsnone}c'), ('[', ''), ('', '1'), (']', '')],
            '/a/b[2]/c[1]',
            namespaces={None:'nsnone'},
        )
        assert_tokens(
            [('/', ''), ('', '{nsnone}a'), ('/', ''), ('', '{nsnone}b'), ('[', ''), ('', '100'), (']', '')],
            '/a/b[100]',
            namespaces={None:'nsnone'}
        )

    def test_xpath_tokenizer(self):
        # Test the XPath tokenizer.  Copied from CPython's "test_xml_etree.py"
        ElementPath = self._elementpath

        def check(p, expected, namespaces=self._empty_namespaces):
            self.assertEqual([op or tag
                              for op, tag in ElementPath.xpath_tokenizer(p, namespaces)],
                             expected)

        # tests from the xml specification
        check("*", ['*'])
        check("text()", ['text', '()'])
        check("@name", ['@', 'name'])
        check("@*", ['@', '*'])
        check("para[1]", ['para', '[', '1', ']'])
        check("para[last()]", ['para', '[', 'last', '()', ']'])
        check("*/para", ['*', '/', 'para'])
        check("/doc/chapter[5]/section[2]",
              ['/', 'doc', '/', 'chapter', '[', '5', ']',
               '/', 'section', '[', '2', ']'])
        check("chapter//para", ['chapter', '//', 'para'])
        check("//para", ['//', 'para'])
        check("//olist/item", ['//', 'olist', '/', 'item'])
        check(".", ['.'])
        check(".//para", ['.', '//', 'para'])
        check("..", ['..'])
        check("../@lang", ['..', '/', '@', 'lang'])
        check("chapter[title]", ['chapter', '[', 'title', ']'])
        check("employee[@secretary and @assistant]", ['employee',
              '[', '@', 'secretary', '', 'and', '', '@', 'assistant', ']'])

        # additional tests
        check("@{ns}attr", ['@', '{ns}attr'])
        check("{http://spam}egg", ['{http://spam}egg'])
        check("./spam.egg", ['.', '/', 'spam.egg'])
        check(".//{http://spam}egg", ['.', '//', '{http://spam}egg'])

        # wildcard tags
        check("{ns}*", ['{ns}*'])
        check("{}*", ['{}*'])
        check("{*}tag", ['{*}tag'])
        check("{*}*", ['{*}*'])
        check(".//{*}tag", ['.', '//', '{*}tag'])

        # namespace prefix resolution
        check("./xsd:type", ['.', '/', '{http://www.w3.org/2001/XMLSchema}type'],
              {'xsd': 'http://www.w3.org/2001/XMLSchema'})
        check("type", ['{http://www.w3.org/2001/XMLSchema}type'],
              {'': 'http://www.w3.org/2001/XMLSchema'})
        check("@xsd:type", ['@', '{http://www.w3.org/2001/XMLSchema}type'],
              {'xsd': 'http://www.w3.org/2001/XMLSchema'})
        check("@type", ['@', 'type'],
              {'': 'http://www.w3.org/2001/XMLSchema'})
        check("@{*}type", ['@', '{*}type'],
              {'': 'http://www.w3.org/2001/XMLSchema'})
        check("@{ns}attr", ['@', '{ns}attr'],
              {'': 'http://www.w3.org/2001/XMLSchema',
               'ns': 'http://www.w3.org/2001/XMLSchema'})

        if self.etree is etree:
            check("/doc/section[2]",
                ['/', '{http://www.w3.org/2001/XMLSchema}doc', '/', '{http://www.w3.org/2001/XMLSchema}section', '[', '2', ']'],
                {"":"http://www.w3.org/2001/XMLSchema"}
            )
            check("/doc/section[2]",
                ['/', '{http://www.w3.org/2001/XMLSchema}doc', '/', '{http://www.w3.org/2001/XMLSchema}section', '[', '2', ']'],
                {None:"http://www.w3.org/2001/XMLSchema"}
            )
            check("/ns:doc/ns:section[2]",
                ['/', '{http://www.w3.org/2001/XMLSchema}doc', '/', '{http://www.w3.org/2001/XMLSchema}section', '[', '2', ']'],
                {"ns":"http://www.w3.org/2001/XMLSchema"}
            )

    def test_find(self):
        """
        Test find methods (including xpath syntax).
        Originally copied from 'selftest.py'.
        """
        elem = etree.XML("""
        <body>
          <tag class='a'>text</tag>
          <tag class='b' />
          <section>
            <tag class='b' id='inner'>subtext</tag>
          </section>
        </body>
        """)

        self.assertEqual(elem.find("tag").tag,
                         'tag')
        self.assertEqual(etree.ElementTree(elem).find("tag").tag,
                         'tag')
        self.assertEqual(elem.find("section/tag").tag,
                         'tag')
        self.assertEqual(etree.ElementTree(elem).find("section/tag").tag,
                         'tag')

        self.assertEqual(elem.findtext("tag"),
                         'text')
        self.assertEqual(elem.findtext("tog"),
                         None)
        self.assertEqual(elem.findtext("tog", "default"),
                         'default')
        self.assertEqual(etree.ElementTree(elem).findtext("tag"),
                         'text')
        self.assertEqual(elem.findtext("section/tag"),
                         'subtext')
        self.assertEqual(etree.ElementTree(elem).findtext("section/tag"),
                         'subtext')

        self.assertEqual(summarize_list(elem.findall("tag")),
                         ['tag', 'tag'])
        self.assertEqual(summarize_list(elem.findall("*")),
                         ['tag', 'tag', 'section'])
        self.assertEqual(summarize_list(elem.findall(".//tag")),
                         ['tag', 'tag', 'tag'])
        self.assertEqual(summarize_list(elem.findall("section/tag")),
                         ['tag'])
        self.assertEqual(summarize_list(elem.findall("section//tag")),
                         ['tag'])

        self.assertEqual(summarize_list(elem.findall("section/*")),
                         ['tag'])
        self.assertEqual(summarize_list(elem.findall("section//*")),
                         ['tag'])
        self.assertEqual(summarize_list(elem.findall("section/.//*")),
                         ['tag'])
        self.assertEqual(summarize_list(elem.findall("*/*")),
                         ['tag'])
        self.assertEqual(summarize_list(elem.findall("*//*")),
                         ['tag'])
        self.assertEqual(summarize_list(elem.findall("*/tag")),
                         ['tag'])
        self.assertEqual(summarize_list(elem.findall("*/./tag")),
                         ['tag'])
        self.assertEqual(summarize_list(elem.findall("./tag")),
                         ['tag', 'tag'])
        self.assertEqual(summarize_list(elem.findall(".//tag")),
                         ['tag', 'tag', 'tag'])
        self.assertEqual(summarize_list(elem.findall("././tag")),
                         ['tag', 'tag'])

        self.assertEqual(summarize_list(elem.findall(".//tag[@class]")),
                         ['tag', 'tag', 'tag'])
        self.assertEqual(summarize_list(elem.findall(".//tag[ @class]")),
                         ['tag', 'tag', 'tag'])
        self.assertEqual(summarize_list(elem.findall(".//tag[@class ]")),
                         ['tag', 'tag', 'tag'])
        self.assertEqual(summarize_list(elem.findall(".//tag[  @class  ]")),
                         ['tag', 'tag', 'tag'])
        self.assertEqual(summarize_list(elem.findall(".//tag[@class='a']")),
                         ['tag'])
        self.assertEqual(summarize_list(elem.findall('.//tag[@class="a"]')),
                         ['tag'])
        self.assertEqual(summarize_list(elem.findall(".//tag[@class='b']")),
                         ['tag', 'tag'])
        self.assertEqual(summarize_list(elem.findall('.//tag[@class="b"]')),
                         ['tag', 'tag'])
        self.assertEqual(summarize_list(elem.findall('.//tag[@class = "b"]')),
                         ['tag', 'tag'])
        self.assertEqual(summarize_list(elem.findall(".//tag[@id]")),
                         ['tag'])
        self.assertEqual(summarize_list(elem.findall(".//tag[@class][@id]")),
                         ['tag'])
        self.assertEqual(summarize_list(elem.findall(".//section[tag]")),
                         ['section'])
        self.assertEqual(summarize_list(elem.findall(".//section[element]")),
                         [])

        self.assertEqual(summarize_list(elem.findall(".//section[tag='subtext']")),
                         ['section'])
        self.assertEqual(summarize_list(elem.findall(".//section[tag ='subtext']")),
                         ['section'])
        self.assertEqual(summarize_list(elem.findall(".//section[tag= 'subtext']")),
                         ['section'])
        self.assertEqual(summarize_list(elem.findall(".//section[tag = 'subtext']")),
                         ['section'])
        self.assertEqual(summarize_list(elem.findall(".//section[  tag   =   'subtext'  ]")),
                         ['section'])
        self.assertEqual(summarize_list(elem.findall(".//tag[.='subtext']")),
                         ['tag'])
        self.assertEqual(summarize_list(elem.findall(".//tag[. ='subtext']")),
                         ['tag'])
        self.assertEqual(summarize_list(elem.findall('.//tag[.= "subtext"]')),
                         ['tag'])
        self.assertEqual(summarize_list(elem.findall(".//tag[. = 'subtext']")),
                         ['tag'])
        self.assertEqual(summarize_list(elem.findall(".//tag[. = 'subtext ']")),
                         [])
        self.assertEqual(summarize_list(elem.findall(".//tag[.= ' subtext']")),
                         [])

        self.assertEqual(summarize_list(elem.findall("../tag")),
                         [])
        self.assertEqual(summarize_list(elem.findall("section/../tag")),
                         ['tag', 'tag'])
        self.assertEqual(summarize_list(etree.ElementTree(elem).findall("./tag")),
                         ['tag', 'tag'])

        self.assertEqual(summarize_list(etree.ElementTree(elem).findall("/tag")),
                         ['tag', 'tag'])
        # This would be correct:
        if False:
            self.assertEqual(summarize_list(etree.ElementTree(elem).findall("/body")),
                            ['body'])

        # duplicate section => 2x tag matches
        elem[1] = deepcopy(elem[2])
        self.assertEqual(summarize_list(elem.findall(".//section[tag = 'subtext']")),
                         ['section', 'section'])
        self.assertEqual(summarize_list(elem.findall(".//tag[. = 'subtext']")),
                         ['tag', 'tag'])
        self.assertEqual(summarize_list(elem.findall(".//tag[@class][@id]")),
                         ['tag', 'tag'])

    def test_find_warning(self):
        etree = self.etree
        elem = etree.XML("""
        <body>
          <tag class='a'>text</tag>
          <tag class='b' />
          <section>
            <tag class='b' id='inner'>subtext</tag>
          </section>
        </body>
        """)

        # FIXME: ET's Path module handles this case incorrectly; this gives
        # a warning in 1.3, and the behaviour will be modified in the future.
        self.assertWarnsRegex(
            FutureWarning, ".*If you rely on the current behaviour, change it to './tag'",
            etree.ElementTree(elem).findall, "/tag")
        self.assertWarnsRegex(
            FutureWarning, ".*If you rely on the current behaviour, change it to './tag'",
            etree.ElementTree(elem).findtext, "/tag")
        self.assertWarnsRegex(
            FutureWarning, ".*If you rely on the current behaviour, change it to './tag'",
            etree.ElementTree(elem).find, "/tag")
        self.assertWarnsRegex(
            FutureWarning, ".*If you rely on the current behaviour, change it to './tag'",
            etree.ElementTree(elem).iterfind, "/tag")


class ElementFindTest(unittest.TestCase):
    # Copied from CPython's test_xml_etree.py.

    def test_find_simple(self):
        e = ET.XML(SAMPLE_XML)
        self.assertEqual(e.find('tag').tag, 'tag')
        self.assertEqual(e.find('section/tag').tag, 'tag')
        self.assertEqual(e.find('./tag').tag, 'tag')

        e[2] = ET.XML(SAMPLE_SECTION)
        self.assertEqual(e.find('section/nexttag').tag, 'nexttag')

        self.assertEqual(e.findtext('./tag'), 'text')
        self.assertEqual(e.findtext('section/tag'), 'subtext')

        # section/nexttag is found but has no text
        self.assertEqual(e.findtext('section/nexttag'), '')
        self.assertEqual(e.findtext('section/nexttag', 'default'), '')

        # tog doesn't exist and 'default' kicks in
        self.assertIsNone(e.findtext('tog'))
        self.assertEqual(e.findtext('tog', 'default'), 'default')

        # Issue #16922
        self.assertEqual(ET.XML('<tag><empty /></tag>').findtext('empty'), '')

    def test_find_xpath(self):
        LINEAR_XML = '''
        <body>
            <tag class='a'/>
            <tag class='b'/>
            <tag class='c'/>
            <tag class='d'/>
        </body>'''
        e = ET.XML(LINEAR_XML)

        # Test for numeric indexing and last()
        self.assertEqual(e.find('./tag[1]').attrib['class'], 'a')
        self.assertEqual(e.find('./tag[2]').attrib['class'], 'b')
        self.assertEqual(e.find('./tag[last()]').attrib['class'], 'd')
        self.assertEqual(e.find('./tag[last()-1]').attrib['class'], 'c')
        self.assertEqual(e.find('./tag[last()-2]').attrib['class'], 'b')

        """  # Error message differs in lxml.
        self.assertRaisesRegex(SyntaxError, 'XPath', e.find, './tag[0]')
        self.assertRaisesRegex(SyntaxError, 'XPath', e.find, './tag[-1]')
        self.assertRaisesRegex(SyntaxError, 'XPath', e.find, './tag[last()-0]')
        self.assertRaisesRegex(SyntaxError, 'XPath', e.find, './tag[last()+1]')
        """
        self.assertRaises(SyntaxError, e.find, './tag[0]')
        self.assertRaises(SyntaxError, e.find, './tag[-1]')
        #self.assertRaises(SyntaxError, e.find, './tag[last()-0]')
        #self.assertRaises(SyntaxError, e.find, './tag[last()+1]')

    def test_findall(self):
        e = ET.XML(SAMPLE_XML)
        e[2] = ET.XML(SAMPLE_SECTION)
        self.assertEqual(summarize_list(e.findall('.')), ['body'])
        self.assertEqual(summarize_list(e.findall('tag')), ['tag', 'tag'])
        self.assertEqual(summarize_list(e.findall('tog')), [])
        self.assertEqual(summarize_list(e.findall('tog/foo')), [])
        self.assertEqual(summarize_list(e.findall('*')),
            ['tag', 'tag', 'section'])
        self.assertEqual(summarize_list(e.findall('.//tag')),
            ['tag'] * 4)
        self.assertEqual(summarize_list(e.findall('section/tag')), ['tag'])
        self.assertEqual(summarize_list(e.findall('section//tag')), ['tag'] * 2)
        self.assertEqual(summarize_list(e.findall('section/*')),
            ['tag', 'nexttag', 'nextsection'])
        self.assertEqual(summarize_list(e.findall('section//*')),
            ['tag', 'nexttag', 'nextsection', 'tag'])
        self.assertEqual(summarize_list(e.findall('section/.//*')),
            ['tag', 'nexttag', 'nextsection', 'tag'])
        self.assertEqual(summarize_list(e.findall('*/*')),
            ['tag', 'nexttag', 'nextsection'])
        self.assertEqual(summarize_list(e.findall('*//*')),
            ['tag', 'nexttag', 'nextsection', 'tag'])
        self.assertEqual(summarize_list(e.findall('*/tag')), ['tag'])
        self.assertEqual(summarize_list(e.findall('*/./tag')), ['tag'])
        self.assertEqual(summarize_list(e.findall('./tag')), ['tag'] * 2)
        self.assertEqual(summarize_list(e.findall('././tag')), ['tag'] * 2)

        self.assertEqual(summarize_list(e.findall('.//tag[@class]')),
            ['tag'] * 3)
        self.assertEqual(summarize_list(e.findall('.//tag[@class="a"]')),
            ['tag'])
        self.assertEqual(summarize_list(e.findall('.//tag[@class="b"]')),
            ['tag'] * 2)
        self.assertEqual(summarize_list(e.findall('.//tag[@id]')),
            ['tag'])
        self.assertEqual(summarize_list(e.findall('.//section[tag]')),
            ['section'])
        self.assertEqual(summarize_list(e.findall('.//section[element]')), [])
        self.assertEqual(summarize_list(e.findall('../tag')), [])
        self.assertEqual(summarize_list(e.findall('section/../tag')),
            ['tag'] * 2)
        self.assertEqual(e.findall('section//'), e.findall('section//*'))

        self.assertEqual(summarize_list(e.findall(".//section[tag='subtext']")),
            ['section'])
        self.assertEqual(summarize_list(e.findall(".//section[tag ='subtext']")),
            ['section'])
        self.assertEqual(summarize_list(e.findall(".//section[tag= 'subtext']")),
            ['section'])
        self.assertEqual(summarize_list(e.findall(".//section[tag = 'subtext']")),
            ['section'])
        self.assertEqual(summarize_list(e.findall(".//section[ tag = 'subtext' ]")),
            ['section'])

        self.assertEqual(summarize_list(e.findall(".//tag[.='subtext']")),
                         ['tag'])
        self.assertEqual(summarize_list(e.findall(".//tag[. ='subtext']")),
                         ['tag'])
        self.assertEqual(summarize_list(e.findall('.//tag[.= "subtext"]')),
                         ['tag'])
        self.assertEqual(summarize_list(e.findall('.//tag[ . = "subtext" ]')),
                         ['tag'])
        self.assertEqual(summarize_list(e.findall(".//tag[. = 'subtext']")),
                         ['tag'])
        self.assertEqual(summarize_list(e.findall(".//tag[. = 'subtext ']")),
                         [])
        self.assertEqual(summarize_list(e.findall(".//tag[.= ' subtext']")),
                         [])

        # duplicate section => 2x tag matches
        e[1] = deepcopy(e[2])  # lxml requires deepcopy()
        self.assertEqual(summarize_list(e.findall(".//section[tag = 'subtext']")),
                         ['section', 'section'])
        self.assertEqual(summarize_list(e.findall(".//tag[. = 'subtext']")),
                         ['tag', 'tag'])

    def test_test_find_with_ns(self):
        e = ET.XML(SAMPLE_XML_NS)
        self.assertEqual(summarize_list(e.findall('tag')), [])
        self.assertEqual(
            summarize_list(e.findall("{http://effbot.org/ns}tag")),
            ['{http://effbot.org/ns}tag'] * 2)
        self.assertEqual(
            summarize_list(e.findall(".//{http://effbot.org/ns}tag")),
            ['{http://effbot.org/ns}tag'] * 3)

    def test_findall_different_nsmaps(self):
        root = ET.XML('''
            <a xmlns:x="X" xmlns:y="Y">
                <x:b><c/></x:b>
                <b/>
                <c><x:b/><b/></c><y:b/>
            </a>''')
        nsmap = {'xx': 'X'}
        self.assertEqual(len(root.findall(".//xx:b", namespaces=nsmap)), 2)
        self.assertEqual(len(root.findall(".//b", namespaces=nsmap)), 2)
        nsmap = {'xx': 'Y'}
        self.assertEqual(len(root.findall(".//xx:b", namespaces=nsmap)), 1)
        self.assertEqual(len(root.findall(".//b", namespaces=nsmap)), 2)
        nsmap = {'xx': 'X', '': 'Y'}
        self.assertEqual(len(root.findall(".//xx:b", namespaces=nsmap)), 2)
        self.assertEqual(len(root.findall(".//b", namespaces=nsmap)), 1)

    def test_bad_find(self):
        e = ET.XML(SAMPLE_XML)
        with self.assertRaisesRegex(SyntaxError, 'cannot use absolute path'):
            e.findall('/tag')

    def test_find_through_ElementTree(self):
        e = ET.XML(SAMPLE_XML)
        self.assertEqual(ET.ElementTree(e).find('tag').tag, 'tag')
        self.assertEqual(ET.ElementTree(e).findtext('tag'), 'text')
        self.assertEqual(summarize_list(ET.ElementTree(e).findall('tag')),
            ['tag'] * 2)
        # this produces a warning
        msg = ("This search is broken in 1.3 and earlier, and will be fixed "
               "in a future version.  If you rely on the current behaviour, "
               "change it to '.+'")
        msg = ".*"  # lxml gives a different warning
        with self.assertWarnsRegex(FutureWarning, msg):
            it = ET.ElementTree(e).findall('//tag')
        self.assertEqual(summarize_list(it), ['tag'] * 3)


class ElementTreeElementPathTestCase(EtreeElementPathTestCase):
    import xml.etree.ElementTree as etree
    import xml.etree.ElementPath as _elementpath

    test_cache = unittest.skip("lxml-only")(EtreeElementPathTestCase.test_cache)
    test_tokenizer = unittest.skip("lxml-only")(EtreeElementPathTestCase.test_tokenizer)
    test_tokenizer_index = unittest.skip("lxml-only")(EtreeElementPathTestCase.test_tokenizer_index)


class EtreeElementPathEmptyNamespacesTestCase(EtreeElementPathTestCase):
    _empty_namespaces = {}  # empty dict as opposed to None


class EtreeElementPathNonEmptyNamespacesTestCase(EtreeElementPathTestCase):
    _empty_namespaces = {'unrelated_prefix': 'unrelated_namespace'}  # non-empty but unused dict


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(EtreeElementPathTestCase)])
    suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(ElementTreeElementPathTestCase)])
    suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(EtreeElementPathEmptyNamespacesTestCase)])
    suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(EtreeElementPathNonEmptyNamespacesTestCase)])
    suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(ElementFindTest)])
    return suite


if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
