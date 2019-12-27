
from __future__ import absolute_import

import unittest

from lxml import etree
from .common_imports import HelperTestCase
from lxml.doctestcompare import LXMLOutputChecker, PARSE_HTML, PARSE_XML


class DummyInput:
    def __init__(self, **kw):
        for name, value in kw.items():
            setattr(self, name, value)


def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


class DoctestCompareTest(HelperTestCase):
    _checker = LXMLOutputChecker()

    def compare(self, want, got, html=False):
        if html:
            options = PARSE_HTML
        else:
            options = PARSE_XML

        parse = self._checker.get_parser(want, got, options)
        want_doc = parse(want)
        got_doc = parse(got)
        return self._checker.collect_diff(
            want_doc, got_doc, html, indent=0).lstrip()

    def assert_diff(self, want, got, diff, html=False):
        self.assertEqual(self.compare(want, got, html), diff)

    def assert_nodiff(self, want, got, html=False):
        root = etree.fromstring(want)
        root.tail = '\n'
        indent(root)
        diff = etree.tostring(
            root, encoding='unicode', method=html and 'html' or 'xml')
        self.assert_diff(want, got, diff, html=html)

    def test_equal_input(self):
        self.assert_nodiff(
            '<p title="expected">Expected</p>',
            '<p title="expected">Expected</p>')

    def test_differing_tags(self):
        self.assert_diff(
            '<p title="expected">Expected</p>',
            '<b title="expected">Expected</b>',
            '<p (got: b) title="expected">Expected</p (got: b)>\n')

    def test_tags_upper_lower_case(self):
        self.assert_diff(
            '<p title="expected">Expected</p>',
            '<P title="expected">Expected</P>',
            '<p (got: P) title="expected">Expected</p (got: P)>\n')

    def test_tags_upper_lower_case_html(self):
        self.assert_nodiff(
            '<html><body><p title="expected">Expected</p></body></html>',
            '<HTML><BODY><P title="expected">Expected</P></BODY></HTML>',
            html=True)

    def test_differing_attributes(self):
        self.assert_diff(
            '<p title="expected">Expected</p>',
            '<p title="actual">Actual</p>',
            '<p title="expected (got: actual)">Expected (got: Actual)</p>\n')

    def test_extra_children(self):
        # https://bugs.launchpad.net/lxml/+bug/1238503
        self.assert_diff(
            '<p><span>One</span></p>',
            '<p><span>One</span><b>Two</b><em>Three</em></p>',
            '<p>\n'
            '  <span>One</span>\n'
            '  +<b>Two</b>\n'
            '  +<em>Three</em>\n'
            '</p>\n')

    def test_missing_children(self):
        self.assert_diff(
            '<p><span>One</span><b>Two</b><em>Three</em></p>',
            '<p><span>One</span></p>',
            '<p>\n'
            '  <span>One</span>\n'
            '  -<b>Two</b>\n'
            '  -<em>Three</em>\n'
            '</p>\n')

    def test_extra_attributes(self):
        self.assert_diff(
            '<p><span class="foo">Text</span></p>',
            '<p><span class="foo" id="bar">Text</span></p>',
            '<p>\n'
            '  <span class="foo" +id="bar">Text</span>\n'
            '</p>\n')

    def test_missing_attributes(self):
        self.assert_diff(
            '<p><span class="foo" id="bar">Text</span></p>',
            '<p><span class="foo">Text</span></p>',
            '<p>\n'
            '  <span class="foo" -id="bar">Text</span>\n'
            '</p>\n')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(DoctestCompareTest)])
    return suite


if __name__ == '__main__':
    unittest.main()
