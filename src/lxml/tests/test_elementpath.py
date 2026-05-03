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

    _empty_namespaces = None

    def test_find(self):
        """
        Test find methods (including xpath syntax).
        Originally copied from 'selftest.py'.
        """
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
