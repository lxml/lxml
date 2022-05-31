# -*- coding: utf-8 -*-

"""
HTML parser test cases for etree
"""

from __future__ import absolute_import

import unittest
import tempfile, os, os.path, sys

from .common_imports import etree, html, BytesIO, fileInTestDir, _bytes, _str
from .common_imports import SillyFileLike, HelperTestCase, write_to_file, needs_libxml

try:
    unicode
except NameError:
    unicode = str


class HtmlParserTestCase(HelperTestCase):
    """HTML parser test cases
    """
    etree = etree

    html_str = _bytes("<html><head><title>test</title></head><body><h1>page title</h1></body></html>")
    html_str_pretty = _bytes("""\
<html>
<head><title>test</title></head>
<body><h1>page title</h1></body>
</html>
""")
    broken_html_str = _bytes("<html><head><title>test"
                             "<body><h1>page title</h3></p></html>")
    uhtml_str = _bytes(
        "<html><head><title>test Ã¡</title></head>"
        "<body><h1>page Ã¡ title</h1></body></html>").decode('utf8')

    def tearDown(self):
        super(HtmlParserTestCase, self).tearDown()
        self.etree.set_default_parser()

    def test_module_HTML(self):
        element = self.etree.HTML(self.html_str)
        self.assertEqual(self.etree.tostring(element, method="html"),
                         self.html_str)

    def test_module_HTML_unicode(self):
        element = self.etree.HTML(self.uhtml_str)
        self.assertEqual(
            self.etree.tostring(element, method="html", encoding='unicode'),
            self.uhtml_str)
        self.assertEqual(element.findtext('.//h1'),
                         _bytes("page Ã¡ title").decode('utf8'))

    @needs_libxml(2, 9, 5)  # not sure, at least 2.9.4 fails
    def test_wide_unicode_html(self):
        if sys.maxunicode < 1114111:
            return  # skip test
        element = self.etree.HTML(_bytes(
            '<html><body><p>\\U00026007</p></body></html>'
        ).decode('unicode_escape'))
        p_text = element.findtext('.//p')
        self.assertEqual(1, len(p_text))
        self.assertEqual(_bytes('\\U00026007').decode('unicode_escape'),
                         p_text)

    def test_html_ids(self):
        parser = self.etree.HTMLParser(recover=False)
        fromstring = self.etree.fromstring
        html = fromstring('''
            <html><body id="bodyID"><p id="pID"></p></body></html>
        ''', parser=parser)
        self.assertEqual(len(html.xpath('//p[@id="pID"]')), 1)
        self.assertEqual(len(html.findall('.//p[@id="pID"]')), 1)

    def test_html_ids_no_collect_ids(self):
        parser = self.etree.HTMLParser(recover=False, collect_ids=False)
        fromstring = self.etree.fromstring
        html = fromstring('''
            <html><body id="bodyID"><p id="pID"></p></body></html>
        ''', parser=parser)
        self.assertEqual(len(html.xpath('//p[@id="pID"]')), 1)
        self.assertEqual(len(html.findall('.//p[@id="pID"]')), 1)

    def test_module_HTML_pretty_print(self):
        element = self.etree.HTML(self.html_str)
        self.assertEqual(self.etree.tostring(element, method="html", pretty_print=True),
                         self.html_str_pretty)

    def test_module_parse_html_error(self):
        parser = self.etree.HTMLParser(recover=False)
        parse = self.etree.parse
        f = BytesIO("<html></body>")
        self.assertRaises(self.etree.XMLSyntaxError,
                          parse, f, parser)

    def test_html_element_name_empty(self):
        parser = self.etree.HTMLParser()
        Element = parser.makeelement

        el = Element('name')
        self.assertRaises(ValueError, Element, '{}')
        self.assertRaises(ValueError, setattr, el, 'tag', '{}')

        self.assertRaises(ValueError, Element, '{test}')
        self.assertRaises(ValueError, setattr, el, 'tag', '{test}')

    def test_html_element_name_colon(self):
        parser = self.etree.HTMLParser()
        Element = parser.makeelement

        pname = Element('p:name')
        self.assertEqual(pname.tag, 'p:name')

        pname = Element('{test}p:name')
        self.assertEqual(pname.tag, '{test}p:name')

        pname = Element('name')
        pname.tag = 'p:name'
        self.assertEqual(pname.tag, 'p:name')

    def test_html_element_name_quote(self):
        parser = self.etree.HTMLParser()
        Element = parser.makeelement

        self.assertRaises(ValueError, Element, 'p"name')
        self.assertRaises(ValueError, Element, "na'me")
        self.assertRaises(ValueError, Element, '{test}"name')
        self.assertRaises(ValueError, Element, "{test}name'")

        el = Element('name')
        self.assertRaises(ValueError, setattr, el, 'tag', "pname'")
        self.assertRaises(ValueError, setattr, el, 'tag', '"pname')
        self.assertEqual(el.tag, "name")

    def test_html_element_name_space(self):
        parser = self.etree.HTMLParser()
        Element = parser.makeelement

        self.assertRaises(ValueError, Element, ' name ')
        self.assertRaises(ValueError, Element, 'na me')
        self.assertRaises(ValueError, Element, '{test} name')

        el = Element('name')
        self.assertRaises(ValueError, setattr, el, 'tag', ' name ')
        self.assertEqual(el.tag, "name")

    def test_html_subelement_name_empty(self):
        parser = self.etree.HTMLParser()
        Element = parser.makeelement

        SubElement = self.etree.SubElement

        el = Element('name')
        self.assertRaises(ValueError, SubElement, el, '{}')
        self.assertRaises(ValueError, SubElement, el, '{test}')

    def test_html_subelement_name_colon(self):
        parser = self.etree.HTMLParser()
        Element = parser.makeelement
        SubElement = self.etree.SubElement

        el = Element('name')
        pname = SubElement(el, 'p:name')
        self.assertEqual(pname.tag, 'p:name')

        pname = SubElement(el, '{test}p:name')
        self.assertEqual(pname.tag, '{test}p:name')

    def test_html_subelement_name_quote(self):
        parser = self.etree.HTMLParser()
        Element = parser.makeelement
        SubElement = self.etree.SubElement

        el = Element('name')
        self.assertRaises(ValueError, SubElement, el, "name'")
        self.assertRaises(ValueError, SubElement, el, 'na"me')
        self.assertRaises(ValueError, SubElement, el, "{test}na'me")
        self.assertRaises(ValueError, SubElement, el, '{test}"name')

    def test_html_subelement_name_space(self):
        parser = self.etree.HTMLParser()
        Element = parser.makeelement
        SubElement = self.etree.SubElement

        el = Element('name')
        self.assertRaises(ValueError, SubElement, el, ' name ')
        self.assertRaises(ValueError, SubElement, el, 'na me')
        self.assertRaises(ValueError, SubElement, el, '{test} name')

    def test_module_parse_html_norecover(self):
        parser = self.etree.HTMLParser(recover=False)
        parse = self.etree.parse
        f = BytesIO(self.broken_html_str)
        self.assertRaises(self.etree.XMLSyntaxError,
                          parse, f, parser)

    def test_module_parse_html_default_doctype(self):
        parser = self.etree.HTMLParser(default_doctype=False)
        d = html.fromstring('<!DOCTYPE html><h1>S</h1></html>', parser=parser)
        self.assertEqual(d.getroottree().docinfo.doctype, '<!DOCTYPE html>')

        d = html.fromstring('<html><h1>S</h1></html>', parser=parser)
        self.assertEqual(d.getroottree().docinfo.doctype, '')

    def test_parse_encoding_8bit_explicit(self):
        text = _str('Søk på nettet')
        html_latin1 = (_str('<p>%s</p>') % text).encode('iso-8859-1')

        tree = self.etree.parse(
            BytesIO(html_latin1),
            self.etree.HTMLParser(encoding="iso-8859-1"))
        p = tree.find("//p")
        self.assertEqual(p.text, text)

    def test_parse_encoding_8bit_override(self):
        text = _str('Søk på nettet')
        wrong_head = _str('''
        <head>
          <meta http-equiv="Content-Type"
                content="text/html; charset=UTF-8" />
        </head>''')
        html_latin1 = (_str('<html>%s<body><p>%s</p></body></html>') % (wrong_head,
                                                                        text)
                      ).encode('iso-8859-1')

        self.assertRaises(self.etree.ParseError,
                          self.etree.parse,
                          BytesIO(html_latin1))

        tree = self.etree.parse(
            BytesIO(html_latin1),
            self.etree.HTMLParser(encoding="iso-8859-1"))
        p = tree.find("//p")
        self.assertEqual(p.text, text)

    def test_module_HTML_broken(self):
        element = self.etree.HTML(self.broken_html_str)
        self.assertEqual(self.etree.tostring(element, method="html"),
                         self.html_str)

    def test_module_HTML_cdata(self):
        # by default, libxml2 generates CDATA nodes for <script> content
        html = _bytes('<html><head><style>foo</style></head></html>')
        element = self.etree.HTML(html)
        self.assertEqual(element[0][0].text, "foo")

    def test_module_HTML_access(self):
        element = self.etree.HTML(self.html_str)
        self.assertEqual(element[0][0].tag, 'title')

    def test_module_parse_html(self):
        parser = self.etree.HTMLParser()
        filename = tempfile.mktemp(suffix=".html")
        write_to_file(filename, self.html_str, 'wb')
        try:
            with open(filename, 'rb') as f:
                tree = self.etree.parse(f, parser)
            self.assertEqual(self.etree.tostring(tree.getroot(), method="html"),
                             self.html_str)
        finally:
            os.remove(filename)

    def test_module_parse_html_filelike(self):
        parser = self.etree.HTMLParser()
        f = SillyFileLike(self.html_str)
        tree = self.etree.parse(f, parser)
        html = self.etree.tostring(tree.getroot(),
                                   method="html", encoding='UTF-8')
        self.assertEqual(html, self.html_str)

##     def test_module_parse_html_filelike_unicode(self):
##         parser = self.etree.HTMLParser()
##         f = SillyFileLike(self.uhtml_str)
##         tree = self.etree.parse(f, parser)
##         html = self.etree.tostring(tree.getroot(), encoding='UTF-8')
##         self.assertEqual(unicode(html, 'UTF-8'), self.uhtml_str)

    def test_html_file_error(self):
        parser = self.etree.HTMLParser()
        parse = self.etree.parse
        self.assertRaises(IOError,
                          parse, "__some_hopefully_nonexisting_file__.html",
                          parser)

    def test_default_parser_HTML_broken(self):
        self.assertRaises(self.etree.XMLSyntaxError,
                          self.etree.parse, BytesIO(self.broken_html_str))

        self.etree.set_default_parser( self.etree.HTMLParser() )

        tree = self.etree.parse(BytesIO(self.broken_html_str))
        self.assertEqual(self.etree.tostring(tree.getroot(), method="html"),
                         self.html_str)

        self.etree.set_default_parser()

        self.assertRaises(self.etree.XMLSyntaxError,
                          self.etree.parse, BytesIO(self.broken_html_str))

    def test_html_iterparse(self):
        iterparse = self.etree.iterparse
        f = BytesIO(
            '<html><head><title>TITLE</title><body><p>P</p></body></html>')

        iterator = iterparse(f, html=True)
        self.assertEqual(None, iterator.root)

        events = list(iterator)
        root = iterator.root
        self.assertTrue(root is not None)
        self.assertEqual(
            [('end', root[0][0]), ('end', root[0]), ('end', root[1][0]),
             ('end', root[1]), ('end', root)],
            events)

    def test_html_iterparse_tag(self):
        iterparse = self.etree.iterparse
        f = BytesIO(
            '<html><head><title>TITLE</title><body><p>P</p></body></html>')

        iterator = iterparse(f, html=True, tag=["p", "title"])
        self.assertEqual(None, iterator.root)

        events = list(iterator)
        root = iterator.root
        self.assertTrue(root is not None)
        self.assertEqual(
            [('end', root[0][0]), ('end', root[1][0])],
            events)

    def test_html_iterparse_stop_short(self):
        iterparse = self.etree.iterparse
        f = BytesIO(
            '<html><head><title>TITLE</title><body><p>P</p></body></html>')

        iterator = iterparse(f, html=True)
        self.assertEqual(None, iterator.root)

        event, element = next(iterator)
        self.assertEqual('end', event)
        self.assertEqual('title', element.tag)
        self.assertEqual(None, iterator.root)
        del element

        event, element = next(iterator)
        self.assertEqual('end', event)
        self.assertEqual('head', element.tag)
        self.assertEqual(None, iterator.root)
        del element
        del iterator

    def test_html_iterparse_broken(self):
        iterparse = self.etree.iterparse
        f = BytesIO('<head><title>TEST></head><p>P<br></div>')

        iterator = iterparse(f, html=True)
        self.assertEqual(None, iterator.root)

        events = list(iterator)
        root = iterator.root
        self.assertTrue(root is not None)
        self.assertEqual('html', root.tag)
        self.assertEqual('head', root[0].tag)
        self.assertEqual('body', root[1].tag)
        self.assertEqual('p', root[1][0].tag)
        self.assertEqual('br', root[1][0][0].tag)
        self.assertEqual(
            [('end', root[0][0]), ('end', root[0]), ('end', root[1][0][0]),
             ('end', root[1][0]), ('end', root[1]), ('end', root)],
            events)

    def test_html_iterparse_broken_no_recover(self):
        iterparse = self.etree.iterparse
        f = BytesIO('<p>P<br></div>')
        iterator = iterparse(f, html=True, recover=False)
        self.assertRaises(self.etree.XMLSyntaxError, list, iterator)

    def test_html_iterparse_file(self):
        iterparse = self.etree.iterparse
        iterator = iterparse(fileInTestDir("shakespeare.html"),
                             html=True)

        self.assertEqual(None, iterator.root)
        events = list(iterator)
        root = iterator.root
        self.assertTrue(root is not None)
        self.assertEqual(249, len(events))
        self.assertFalse(
            [event for (event, element) in events if event != 'end'])

    def test_html_iterparse_start(self):
        iterparse = self.etree.iterparse
        f = BytesIO(
            '<html><head><title>TITLE</title><body><p>P</p></body></html>')

        iterator = iterparse(f, html=True, events=('start',))
        self.assertEqual(None, iterator.root)

        events = list(iterator)
        root = iterator.root
        self.assertNotEqual(None, root)
        self.assertEqual(
            [('start', root), ('start', root[0]), ('start', root[0][0]),
                ('start', root[1]), ('start', root[1][0])],
            events)

    def test_html_feed_parser(self):
        parser = self.etree.HTMLParser()
        parser.feed("<html><body></")
        parser.feed("body></html>")
        root = parser.close()

        self.assertEqual('html', root.tag)
        # test that we find all names in the parser dict
        self.assertEqual([root], list(root.iter('html')))
        self.assertEqual([root[0]], list(root.iter('body')))

    def test_html_feed_parser_chunky(self):
        parser = self.etree.HTMLParser()
        parser.feed("<htm")
        parser.feed("l><body")
        parser.feed("><")
        parser.feed("p><")
        parser.feed("strong")
        parser.feed(">some ")
        parser.feed("text</strong></p><")
        parser.feed("/body></html>")
        root = parser.close()

        self.assertEqual('html', root.tag)
        # test that we find all names in the parser dict
        self.assertEqual([root], list(root.iter('html')))
        self.assertEqual([root[0]], list(root.iter('body')))
        self.assertEqual([root[0][0]], list(root.iter('p')))
        self.assertEqual([root[0][0][0]], list(root.iter('strong')))

    def test_html_feed_parser_more_tags(self):
        parser = self.etree.HTMLParser()
        parser.feed('<html><head>')
        parser.feed('<title>TITLE</title><body><p>P</p></body><')
        parser.feed("/html>")
        root = parser.close()

        self.assertEqual('html', root.tag)
        # test that we find all names in the parser dict
        self.assertEqual([root], list(root.iter('html')))
        self.assertEqual([root[0]], list(root.iter('head')))
        self.assertEqual([root[0][0]], list(root.iter('title')))
        self.assertEqual([root[1]], list(root.iter('body')))
        self.assertEqual([root[1][0]], list(root.iter('p')))

    def test_html_parser_target_tag(self):
        assertFalse  = self.assertFalse
        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append(("start", tag))
                assertFalse(attrib)
            def end(self, tag):
                events.append(("end", tag))
            def close(self):
                return "DONE"

        parser = self.etree.HTMLParser(target=Target())

        parser.feed("<html><body></body></html>")
        done = parser.close()

        self.assertEqual("DONE", done)
        self.assertEqual([
            ("start", "html"), ("start", "body"),
            ("end", "body"), ("end", "html")], events)

    def test_html_parser_target_doctype_empty(self):
        assertFalse  = self.assertFalse
        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append(("start", tag))
                assertFalse(attrib)
            def end(self, tag):
                events.append(("end", tag))
            def doctype(self, *args):
                events.append(("doctype", args))
            def close(self):
                return "DONE"

        parser = self.etree.HTMLParser(target=Target())
        parser.feed("<!DOCTYPE><html><body></body></html>")
        done = parser.close()

        self.assertEqual("DONE", done)
        self.assertEqual([
            ("doctype", (None, None, None)),
            ("start", "html"), ("start", "body"),
            ("end", "body"), ("end", "html")], events)

    def test_html_parser_target_doctype_html(self):
        assertFalse  = self.assertFalse
        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append(("start", tag))
                assertFalse(attrib)
            def end(self, tag):
                events.append(("end", tag))
            def doctype(self, *args):
                events.append(("doctype", args))
            def close(self):
                return "DONE"

        parser = self.etree.HTMLParser(target=Target())
        parser.feed("<!DOCTYPE html><html><body></body></html>")
        done = parser.close()

        self.assertEqual("DONE", done)
        self.assertEqual([
            ("doctype", ("html", None, None)),
            ("start", "html"), ("start", "body"),
            ("end", "body"), ("end", "html")], events)

    def test_html_parser_target_doctype_html_full(self):
        assertFalse  = self.assertFalse
        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append(("start", tag))
                assertFalse(attrib)
            def end(self, tag):
                events.append(("end", tag))
            def doctype(self, *args):
                events.append(("doctype", args))
            def close(self):
                return "DONE"

        parser = self.etree.HTMLParser(target=Target())
        parser.feed('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "sys.dtd">'
                    '<html><body></body></html>')
        done = parser.close()

        self.assertEqual("DONE", done)
        self.assertEqual([
            ("doctype", ("html", "-//W3C//DTD HTML 4.01//EN", "sys.dtd")),
            ("start", "html"), ("start", "body"),
            ("end", "body"), ("end", "html")], events)

    def test_html_parser_target_exceptions(self):
        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append(("start", tag))
                raise ValueError("START")
            def end(self, tag):
                events.append(("end", tag))
                raise TypeError("END")
            def close(self):
                return "DONE"

        parser = self.etree.HTMLParser(target=Target())
        try:
            parser.feed('<html><body>')
            parser.feed('</body></html>')
        except ValueError as exc:
            assert "START" in str(exc)
        except TypeError as exc:
            assert "END" in str(exc)
            self.assertTrue(False, "wrong exception raised")
        else:
            self.assertTrue(False, "no exception raised")

        self.assertTrue(("start", "html") in events, events)
        self.assertTrue(("end", "html") not in events, events)

    def test_html_fromstring_target_exceptions(self):
        events = []
        class Target(object):
            def start(self, tag, attrib):
                events.append(("start", tag))
                raise ValueError("START")
            def end(self, tag):
                events.append(("end", tag))
                raise TypeError("END")
            def close(self):
                return "DONE"

        parser = self.etree.HTMLParser(target=Target())
        try:
            self.etree.fromstring('<html><body></body></html>', parser)
        except ValueError as exc:
            assert "START" in str(exc), str(exc)
        except TypeError as exc:
            assert "END" in str(exc), str(exc)
            self.assertTrue(False, "wrong exception raised")
        else:
            self.assertTrue(False, "no exception raised")

        self.assertTrue(("start", "html") in events, events)
        self.assertTrue(("end", "html") not in events, events)

    def test_set_decl_html(self):
        doc = html.Element('html').getroottree()
        doc.docinfo.public_id = "-//W3C//DTD XHTML 1.0 Strict//EN"
        doc.docinfo.system_url = \
            "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd"
        self.assertEqual(doc.docinfo.doctype,
                         '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">')
        self.assertEqual(self.etree.tostring(doc),
                         _bytes('''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"></html>'''))

    def test_html5_doctype(self):
        # document type declaration with neither public if nor system url
        doc = html.Element('html').getroottree()
        doc.docinfo.public_id = None
        doc.docinfo.system_url = None
        self.assertEqual(doc.docinfo.doctype,
                         '<!DOCTYPE html>')
        self.assertTrue(doc.docinfo.public_id is None)
        self.assertEqual(self.etree.tostring(doc),
                         _bytes('<!DOCTYPE html>\n<html/>'))

    def test_ietf_decl(self):
        # legacy declaration with public id, no system url
        doc = html.Element('html').getroottree()
        doc.docinfo.public_id = '-//IETF//DTD HTML//EN'
        doc.docinfo.system_url = None
        self.assertEqual(doc.docinfo.doctype,
                         '<!DOCTYPE html PUBLIC "-//IETF//DTD HTML//EN">')
        self.assertEqual(self.etree.tostring(doc),
                         _bytes('<!DOCTYPE html PUBLIC "-//IETF//DTD HTML//EN">\n<html/>'))

    def test_boolean_attribute(self):
        # ability to serialize boolean attribute by setting value to None
        form = html.Element('form')
        form.set('novalidate', None)
        self.assertEqual(html.tostring(form),
                         _bytes('<form novalidate></form>'))
        form.set('custom')
        self.assertEqual(html.tostring(form),
                         _bytes('<form novalidate custom></form>'))

    def test_boolean_attribute_round_trip(self):
        # ability to pass boolean attributes unmodified
        fragment = '<tag attribute></tag>'
        self.assertEqual(html.tostring(html.fragment_fromstring(fragment)),
                         _bytes(fragment))

    def test_boolean_attribute_xml_adds_empty_string(self):
        # html serialized as xml converts boolean attributes to empty strings
        fragment = '<tag attribute></tag>'
        self.assertEqual(self.etree.tostring(html.fragment_fromstring(fragment)),
                         _bytes('<tag attribute=""/>'))

    def test_xhtml_as_html_as_xml(self):
        # parse XHTML as HTML, serialise as XML
        # See https://bugs.launchpad.net/lxml/+bug/1965070
        xhtml = (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<html xmlns="http://www.w3.org/1999/xhtml"></html>'
        )
        root = html.fromstring(xhtml)
        result = etree.tostring(root)
        self.assertEqual(result, b'<html xmlns="http://www.w3.org/1999/xhtml"/>')

        # Adding an XHTML doctype makes libxml2 add the namespace, which wasn't parsed as such by the HTML parser.
        """
        xhtml = (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
            b'<html xmlns="http://www.w3.org/1999/xhtml"></html>'
        )
        root = html.fromstring(xhtml)
        result = etree.tostring(root)
        self.assertEqual(result, b'<html xmlns="http://www.w3.org/1999/xhtml"/>')
        """


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(HtmlParserTestCase)])
    return suite


if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
