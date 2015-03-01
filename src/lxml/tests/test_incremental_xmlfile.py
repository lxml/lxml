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

from common_imports import etree, BytesIO, HelperTestCase, skipIf

class _XmlFileTestCaseBase(HelperTestCase):
    _file = None  # to be set by specific subtypes below

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
        self.assertTrue(tree is not None)
        self.assertEqual(100, len(tree.getroot()))
        self.assertEqual(set(['test']), set(el.tag for el in tree.getroot()))

    def test_namespace_nsmap(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('{nsURI}test', nsmap={'x': 'nsURI'}):
                pass
        self.assertXml('<x:test xmlns:x="nsURI"></x:test>')

    def test_namespace_nested_nsmap(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('test', nsmap={'x': 'nsURI'}):
                with xf.element('{nsURI}toast'):
                    pass
        self.assertXml('<test xmlns:x="nsURI"><x:toast></x:toast></test>')

    def test_anonymous_namespace(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('{nsURI}test'):
                pass
        self.assertXml('<ns0:test xmlns:ns0="nsURI"></ns0:test>')

    def test_namespace_nested_anonymous(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('test'):
                with xf.element('{nsURI}toast'):
                    pass
        self.assertXml('<test><ns0:toast xmlns:ns0="nsURI"></ns0:toast></test>')

    def test_default_namespace(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('{nsURI}test', nsmap={None: 'nsURI'}):
                pass
        self.assertXml('<test xmlns="nsURI"></test>')

    def test_nested_default_namespace(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('{nsURI}test', nsmap={None: 'nsURI'}):
                with xf.element('{nsURI}toast'):
                    pass
        self.assertXml('<test xmlns="nsURI"><toast></toast></test>')

    def test_nested_default_namespace_and_other(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('{nsURI}test', nsmap={None: 'nsURI', 'p': 'ns2'}):
                with xf.element('{nsURI}toast'):
                    pass
                with xf.element('{ns2}toast'):
                    pass
        self.assertXml(
            '<test xmlns="nsURI" xmlns:p="ns2"><toast></toast><p:toast></p:toast></test>')

    def test_pi(self):
        with etree.xmlfile(self._file) as xf:
            xf.write(etree.ProcessingInstruction('pypi'))
            with xf.element('test'):
                pass
        self.assertXml('<?pypi ?><test></test>')

    def test_comment(self):
        with etree.xmlfile(self._file) as xf:
            xf.write(etree.Comment('a comment'))
            with xf.element('test'):
                pass
        self.assertXml('<!--a comment--><test></test>')

    def test_attribute(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('test', attrib={'k': 'v'}):
                pass
        self.assertXml('<test k="v"></test>')

    def test_escaping(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('test'):
                xf.write('Comments: <!-- text -->\n')
                xf.write('Entities: &amp;')
        self.assertXml(
            '<test>Comments: &lt;!-- text --&gt;\nEntities: &amp;amp;</test>')

    def test_encoding(self):
        with etree.xmlfile(self._file, encoding='utf16') as xf:
            with xf.element('test'):
                xf.write('toast')
        self.assertXml('<test>toast</test>', encoding='utf16')

    def test_buffering(self):
        with etree.xmlfile(self._file, buffered=False) as xf:
            with xf.element('test'):
                self.assertXml("<test>")
                xf.write('toast')
                self.assertXml("<test>toast")
                with xf.element('taste'):
                    self.assertXml("<test>toast<taste>")
                    xf.write('some', etree.Element("more"), "toast")
                    self.assertXml("<test>toast<taste>some<more/>toast")
                self.assertXml("<test>toast<taste>some<more/>toast</taste>")
                xf.write('end')
                self.assertXml("<test>toast<taste>some<more/>toast</taste>end")
            self.assertXml("<test>toast<taste>some<more/>toast</taste>end</test>")
        self.assertXml("<test>toast<taste>some<more/>toast</taste>end</test>")

    def test_flush(self):
        with etree.xmlfile(self._file, buffered=True) as xf:
            with xf.element('test'):
                self.assertXml("")
                xf.write('toast')
                self.assertXml("")
                with xf.element('taste'):
                    self.assertXml("")
                    xf.flush()
                    self.assertXml("<test>toast<taste>")
                self.assertXml("<test>toast<taste>")
            self.assertXml("<test>toast<taste>")
        self.assertXml("<test>toast<taste></taste></test>")

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

    def test_closing_out_of_order_in_error_case(self):
        cm_exit = None
        try:
            with etree.xmlfile(self._file) as xf:
                x = xf.element('test')
                cm_exit = x.__exit__
                x.__enter__()
                raise ValueError('123')
        except ValueError:
            self.assertTrue(cm_exit)
            try:
                cm_exit(ValueError, ValueError("huhu"), None)
            except etree.LxmlSyntaxError:
                self.assertTrue(True)
            else:
                self.assertTrue(False)
        else:
            self.assertTrue(False)

    def _read_file(self):
        pos = self._file.tell()
        self._file.seek(0)
        try:
            return self._file.read()
        finally:
            self._file.seek(pos)

    def _parse_file(self):
        pos = self._file.tell()
        self._file.seek(0)
        try:
            return etree.parse(self._file)
        finally:
            self._file.seek(pos)

    def tearDown(self):
        if self._file is not None:
            self._file.close()

    def assertXml(self, expected, encoding='utf8'):
        self.assertEqual(self._read_file().decode(encoding), expected)


class BytesIOXmlFileTestCase(_XmlFileTestCaseBase):
    def setUp(self):
        self._file = BytesIO()

    def test_filelike_close(self):
        with etree.xmlfile(self._file, close=True) as xf:
            with xf.element('test'):
                pass
        self.assertRaises(ValueError, self._file.getvalue)


class TempXmlFileTestCase(_XmlFileTestCaseBase):
    def setUp(self):
        self._file = tempfile.TemporaryFile()


class TempPathXmlFileTestCase(_XmlFileTestCaseBase):
    def setUp(self):
        self._tmpfile = tempfile.NamedTemporaryFile()
        self._file = self._tmpfile.name

    def tearDown(self):
        try:
            self._tmpfile.close()
        finally:
            if os.path.exists(self._tmpfile.name):
                os.unlink(self._tmpfile.name)

    def _read_file(self):
        self._tmpfile.seek(0)
        return self._tmpfile.read()

    def _parse_file(self):
        self._tmpfile.seek(0)
        return etree.parse(self._tmpfile)

    @skipIf(True, "temp file behaviour is too platform specific here")
    def test_buffering(self):
        pass

    @skipIf(True, "temp file behaviour is too platform specific here")
    def test_flush(self):
        pass


class SimpleFileLikeXmlFileTestCase(_XmlFileTestCaseBase):
    class SimpleFileLike(object):
        def __init__(self, target):
            self._target = target
            self.write = target.write
            self.tell = target.tell
            self.seek = target.seek
            self.closed = False

        def close(self):
            assert not self.closed
            self.closed = True
            self._target.close()

    def setUp(self):
        self._target = BytesIO()
        self._file = self.SimpleFileLike(self._target)

    def _read_file(self):
        return self._target.getvalue()

    def _parse_file(self):
        pos = self._file.tell()
        self._target.seek(0)
        try:
            return etree.parse(self._target)
        finally:
            self._target.seek(pos)

    def test_filelike_not_closing(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('test'):
                pass
        self.assertFalse(self._file.closed)

    def test_filelike_close(self):
        with etree.xmlfile(self._file, close=True) as xf:
            with xf.element('test'):
                pass
        self.assertTrue(self._file.closed)
        self._file = None  # prevent closing in tearDown()


class HtmlFileTestCase(_XmlFileTestCaseBase):
    def setUp(self):
        self._file = BytesIO()

    def test_void_elements(self):
        # http://www.w3.org/TR/html5/syntax.html#elements-0
        void_elements = set([
            "area", "base", "br", "col", "embed", "hr", "img",
            "input", "keygen", "link", "meta", "param",
            "source", "track", "wbr"
        ])

        # FIXME: These don't get serialized as void elements.
        void_elements.difference_update([
            'area', 'embed', 'keygen', 'source', 'track', 'wbr'
        ])

        for tag in sorted(void_elements):
            with etree.htmlfile(self._file) as xf:
                xf.write(etree.Element(tag))
            self.assertXml('<%s>' % tag)
            self._file = BytesIO()

    def test_write_declaration(self):
        with etree.htmlfile(self._file) as xf:
            try:
                xf.write_declaration()
            except etree.LxmlSyntaxError:
                self.assertTrue(True)
            else:
                self.assertTrue(False)
            xf.write(etree.Element('html'))

    def test_write_namespaced_element(self):
        with etree.htmlfile(self._file) as xf:
            xf.write(etree.Element('{some_ns}some_tag'))
        self.assertXml('<ns0:some_tag xmlns:ns0="some_ns"></ns0:some_tag>')

    def test_open_namespaced_element(self):
        with etree.htmlfile(self._file) as xf:
            with xf.element("{some_ns}some_tag"):
                pass
        self.assertXml('<ns0:some_tag xmlns:ns0="some_ns"></ns0:some_tag>')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(BytesIOXmlFileTestCase),
                    unittest.makeSuite(TempXmlFileTestCase),
                    unittest.makeSuite(TempPathXmlFileTestCase),
                    unittest.makeSuite(SimpleFileLikeXmlFileTestCase),
                    unittest.makeSuite(HtmlFileTestCase),
                    ])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
