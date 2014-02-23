import sys
import unittest

from lxml.tests.common_imports import HelperTestCase
from lxml.doctestcompare import LXMLOutputChecker, PARSE_HTML, PARSE_XML


class DummyInput:
    def __init__(self, **kw):
        for name, value in kw.items():
            setattr(self, name, value)


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
            want_doc, got_doc, html, options).lstrip()

    def assert_diff(self, want, got, diff, html=False):
        self.assertEqual(self.compare(want, got, html), diff)

    def assert_nodiff(self, want, got, html=False):
        self.assert_diff(want, got, None, html=html)

    def test_attributes(self):
        self.assert_diff(
            '<p title="expected">Expected</p>',
            '<p title="actual">Actual</p>',
            '<p title="expected (got: actual)">Expected (got: Actual)</p>\n')


def test_suite():
    suite = unittest.TestSuite()
    if sys.version_info >= (2,4):
        suite.addTests([unittest.makeSuite(DoctestCompareTest)])
    return suite


if __name__ == '__main__':
    unittest.main()
