"""
Tests for the ElementPath implementation.
"""

import sys
import unittest
from copy import deepcopy
from .common_imports import etree, HelperTestCase


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
    return suite


if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
