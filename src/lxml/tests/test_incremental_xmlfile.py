# -*- coding: utf-8 -*-

"""
Tests for the incremental XML serialisation API.
"""

from __future__ import absolute_import

import io
import os
import sys
import unittest
import textwrap
import tempfile

from lxml.etree import LxmlSyntaxError

from .common_imports import etree, BytesIO, HelperTestCase, skipIf, _str


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

    def test_element_write_empty(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('test'):
                xf.write(None)
                xf.write('')
                xf.write('')
                xf.write(None)
        self.assertXml('<test></test>')

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
        self.assertEqual({'test'}, {el.tag for el in tree.getroot()})

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

    def test_attribute_extra(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('test', attrib={'k': 'v'}, n='N'):
                pass
        self.assertXml('<test k="v" n="N"></test>')

    def test_attribute_extra_duplicate(self):
        with etree.xmlfile(self._file) as xf:
            with xf.element('test', attrib={'k': 'v'}, k='V'):
                pass
        self.assertXml('<test k="V"></test>')

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

    def test_non_io_exception_continues_closing(self):
        try:
            with etree.xmlfile(self._file) as xf:
                with xf.element('root'):
                    with xf.element('test'):
                        xf.write("BEFORE")
                        raise TypeError("FAIL!")
                    xf.write("AFTER")
        except TypeError as exc:
            self.assertTrue("FAIL" in str(exc), exc)
        else:
            self.assertTrue(False, "exception not propagated")
        self.assertXml("<root><test>BEFORE</test></root>")

    def test_generator_close_continues_closing(self):
        def gen():
            with etree.xmlfile(self._file) as xf:
                with xf.element('root'):
                    while True:
                        content = (yield)
                        with xf.element('entry'):
                            xf.write(content)

        g = gen()
        next(g)
        g.send('A')
        g.send('B')
        g.send('C')
        g.close()
        self.assertXml("<root><entry>A</entry><entry>B</entry><entry>C</entry></root>")

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


@skipIf(sys.platform.startswith("win"), "Can't reopen temporary files on Windows")
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

    def test_write_fails(self):
        class WriteError(Exception):
            pass

        class Writer(object):
            def __init__(self, trigger):
                self._trigger = trigger
                self._failed = False

            def write(self, data):
                assert not self._failed, "write() called again after failure"
                if self._trigger in data:
                    self._failed = True
                    raise WriteError("FAILED: " + self._trigger.decode('utf8'))

        for trigger in ['text', 'root', 'tag', 'noflush']:
            try:
                with etree.xmlfile(Writer(trigger.encode('utf8')), encoding='utf8') as xf:
                    with xf.element('root'):
                        xf.flush()
                        with xf.element('tag'):
                            xf.write('text')
                            xf.flush()
                            xf.write('noflush')
                        xf.flush()
                    xf.flush()
            except WriteError as exc:
                self.assertTrue('FAILED: ' + trigger in str(exc))
            else:
                self.assertTrue(False, "exception not raised for '%s'" % trigger)


class HtmlFileTestCase(_XmlFileTestCaseBase):
    def setUp(self):
        self._file = BytesIO()

    def test_void_elements(self):
        # http://www.w3.org/TR/html5/syntax.html#elements-0
        void_elements = {
            "area", "base", "br", "col", "embed", "hr", "img", "input",
            "keygen", "link", "meta", "param", "source", "track", "wbr"}

        # FIXME: These don't get serialized as void elements.
        void_elements.difference_update([
            'area', 'embed', 'keygen', 'source', 'track', 'wbr'
        ])

        for tag in sorted(void_elements):
            with etree.htmlfile(self._file) as xf:
                xf.write(etree.Element(tag))
            self.assertXml('<%s>' % tag)
            self._file = BytesIO()

    def test_method_context_manager_misuse(self):
        with etree.htmlfile(self._file) as xf:
            with xf.element('foo'):
                cm = xf.method('xml')
                cm.__enter__()

                self.assertRaises(LxmlSyntaxError, cm.__enter__)

                cm2 = xf.method('xml')
                cm2.__enter__()
                cm2.__exit__(None, None, None)

                self.assertRaises(LxmlSyntaxError, cm2.__exit__, None, None, None)

                cm3 = xf.method('xml')
                cm3.__enter__()
                with xf.method('html'):
                    self.assertRaises(LxmlSyntaxError, cm3.__exit__, None, None, None)

    def test_xml_mode_write_inside_html(self):
        tag = 'foo'
        attrib = {'selected': 'bar'}
        elt = etree.Element(tag, attrib=attrib)

        with etree.htmlfile(self._file) as xf:
            with xf.element("root"):
                xf.write(elt)  # 1

                assert elt.text is None
                xf.write(elt, method='xml')  # 2

                elt.text = ""
                xf.write(elt, method='xml')  # 3

                with xf.element(tag, attrib=attrib, method='xml'):
                    pass # 4

                xf.write(elt)  # 5

                with xf.method('xml'):
                    xf.write(elt)  # 6

        self.assertXml(
            '<root>'
                '<foo selected></foo>'  # 1
                '<foo selected="bar"/>'  # 2
                '<foo selected="bar"></foo>'  # 3
                '<foo selected="bar"></foo>'  # 4
                '<foo selected></foo>'  # 5
                '<foo selected="bar"></foo>'  # 6
            '</root>')
        self._file = BytesIO()

    def test_xml_mode_element_inside_html(self):
        # The htmlfile already outputs in xml mode for .element calls. This
        # test actually illustrates a bug

        with etree.htmlfile(self._file) as xf:
            with xf.element("root"):
                with xf.element('foo', attrib={'selected': 'bar'}):
                    pass

        self.assertXml(
            '<root>'
              # '<foo selected></foo>'  # FIXME: this is the correct output
                                        # in html mode
              '<foo selected="bar"></foo>'
            '</root>')
        self._file = BytesIO()

    def test_attribute_quoting(self):
        with etree.htmlfile(self._file) as xf:
            with xf.element("tagname", attrib={"attr": '"misquoted"'}):
                xf.write("foo")

        self.assertXml('<tagname attr="&quot;misquoted&quot;">foo</tagname>')

    def test_attribute_quoting_unicode(self):
        with etree.htmlfile(self._file) as xf:
            with xf.element("tagname", attrib={"attr": _str('"misquöted\\u3344\\U00013344"')}):
                xf.write("foo")

        self.assertXml('<tagname attr="&quot;misqu&#xF6;ted&#x3344;&#x13344;&quot;">foo</tagname>')

    def test_unescaped_script(self):
        with etree.htmlfile(self._file) as xf:
            elt = etree.Element('script')
            elt.text = "if (a < b);"
            xf.write(elt)
        self.assertXml('<script>if (a < b);</script>')

    def test_unescaped_script_incremental(self):
        with etree.htmlfile(self._file) as xf:
            with xf.element('script'):
                xf.write("if (a < b);")

        self.assertXml('<script>if (a < b);</script>')

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


class AsyncXmlFileTestCase(HelperTestCase):
    def test_async_api(self):
        out = io.BytesIO()
        xf = etree.xmlfile(out)
        scm = xf.__enter__()
        acm = xf.__aenter__()
        list(acm.__await__())  # fake await to avoid destructor warning

        def api_of(obj):
            return sorted(name for name in dir(scm) if not name.startswith('__'))

        a_api = api_of(acm)

        self.assertEqual(api_of(scm), api_of(acm))
        self.assertTrue('write' in a_api)
        self.assertTrue('element' in a_api)
        self.assertTrue('method' in a_api)
        self.assertTrue(len(a_api) > 5)

    def _run_async(self, coro):
        while True:
            try:
                coro.send(None)
            except StopIteration as ex:
                return ex.value

    @skipIf(sys.version_info < (3, 5), "requires support for async-def (Py3.5+)")
    def test_async(self):
        code = textwrap.dedent("""\
        async def test_async_xmlfile(close=True, buffered=True):
            class Writer(object):
                def __init__(self):
                    self._data = []
                    self._all_data = None
                    self._calls = 0

                async def write(self, data):
                    self._calls += 1
                    self._data.append(data)

                async def close(self):
                    assert self._all_data is None
                    assert self._data is not None
                    self._all_data = b''.join(self._data)
                    self._data = None  # make writing fail afterwards

            async def generate(out, close=True, buffered=True):
                async with etree.xmlfile(out, close=close, buffered=buffered) as xf:
                    async with xf.element('root'):
                        await xf.write('root-text')
                        async with xf.method('html'):
                            await xf.write(etree.Element('img', src='http://huhu.org/'))
                        await xf.flush()
                        for i in range(3):
                            async with xf.element('el'):
                                await xf.write('text-%d' % i)

            out = Writer()
            await generate(out, close=close, buffered=buffered)
            if not close:
                await out.close()
            assert out._data is None, out._data
            return out._all_data, out._calls
        """)
        lns = {}
        exec(code, globals(), lns)
        test_async_xmlfile = lns['test_async_xmlfile']

        expected = (
            b'<root>root-text<img src="http://huhu.org/">'
            b'<el>text-0</el><el>text-1</el><el>text-2</el></root>'
        )

        data, calls = self._run_async(test_async_xmlfile(close=True))
        self.assertEqual(expected, data)
        self.assertEqual(2, calls)  # only flush() and close()

        data, calls = self._run_async(test_async_xmlfile(close=False))
        self.assertEqual(expected, data)
        self.assertEqual(2, calls)  # only flush() and close()

        data, unbuffered_calls = self._run_async(test_async_xmlfile(buffered=False))
        self.assertEqual(expected, data)
        self.assertTrue(unbuffered_calls > calls, unbuffered_calls)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([
        unittest.makeSuite(BytesIOXmlFileTestCase),
        unittest.makeSuite(TempXmlFileTestCase),
        unittest.makeSuite(TempPathXmlFileTestCase),
        unittest.makeSuite(SimpleFileLikeXmlFileTestCase),
        unittest.makeSuite(HtmlFileTestCase),
        unittest.makeSuite(AsyncXmlFileTestCase),
    ])
    return suite


if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
