# -*- coding: utf-8 -*-

"""
Tests for the incremental XML serialisation API.

Tests require Python 2.5 or later.
"""

from __future__ import with_statement

import unittest
import tempfile, os, sys

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

from common_imports import etree, _bytes, BytesIO
from common_imports import HelperTestCase

class _XmlFileTestCaseBase(HelperTestCase):
    def test_element(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('test'):
                pass
        self.assertXml('<test></test>')

    def test_element_write_text(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('test'):
                xf.write('toast')
        self.assertXml('<test>toast</test>')

    def test_element_nested(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('test'):
                with xf.element('toast'):
                    with xf.element('taste'):
                        xf.write('conTent')
        self.assertXml('<test><toast><taste>conTent</taste></toast></test>')

    def test_element_nested_with_text(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('test'):
                xf.write('con')
                with xf.element('toast'):
                    xf.write('tent')
                    with xf.element('taste'):
                        xf.write('inside')
                    xf.write('tnet')
                xf.write('noc')
        self.assertXml('<test>con<toast>tent<taste>inside</taste>'
                       'tnet</toast>noc</test>')

    def test_write_Element(self):
        with etree.xmlfile(self._file) as xf:
            xf.write(etree.Element('test'))
        self.assertXml('<test/>')

    def test_write_Element_repeatedly(self):
        element = etree.Element('test')
        with etree.xmlfile(self._file) as xf:
            with xf.element('test'):
                for i in range(100):
                    xf.write(element)

        tree = self._parse_file()
        self.assertIsNotNone(tree)
        self.assertEqual(100, len(tree.getroot()))
        self.assertEqual(set(['test']), set(el.tag for el in tree.getroot()))

    def test_pi(self):
        with etree.xmlfile(self._file) as xf:
            xf.write(etree.ProcessingInstruction('pypi'))
            with xf.element('test'):
                pass
        self.assertXml('<?pypi ?><test></test>')

    def test_encoding(self):
        with etree.xmlfile(self._file, encoding='utf16') as xf:
            with xf.element('test'):
                xf.write('toast')
        self.assertXml('<test>toast</test>', encoding='utf16')

    def test_failure_preceding_text(self):
        try:
            with etree.xmlfile(self._file) as xf:
                xf.write('toast')
        except etree.LxmlSyntaxError:
            self.assertTrue(True)
        else:
            self.assertTrue(False)

    def test_failure_trailing_text(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('test'):
                pass
            try:
                xf.write('toast')
            except etree.LxmlSyntaxError:
                self.assertTrue(True)
            else:
                self.assertTrue(False)

    def test_failure_trailing_Element(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('test'):
                pass
            try:
                xf.write(etree.Element('test'))
            except etree.LxmlSyntaxError:
                self.assertTrue(True)
            else:
                self.assertTrue(False)

    def _read_file(self):
        self._file.seek(0)
        return self._file.read()

    def _parse_file(self):
        self._file.seek(0)
        return etree.parse(self._file)

    def tearDown(self):
        self._file.close()

    def assertXml(self, expected, encoding='utf8'):
        self.assertEqual(self._read_file().decode(encoding), expected)


class BytesIOXmlFileTestCase(_XmlFileTestCaseBase):
    def setUp(self):
        self._file = BytesIO()

class TempXmlFileTestCase(_XmlFileTestCaseBase):
    def setUp(self):
        self._file = tempfile.NamedTemporaryFile()


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(BytesIOXmlFileTestCase),
                    unittest.makeSuite(TempXmlFileTestCase),
                    ])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
