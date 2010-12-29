# -*- coding: utf-8 -*-

"""
HTML parser test cases for etree
"""

import unittest
import tempfile, os, os.path, sys

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

from common_imports import etree, StringIO, BytesIO, fileInTestDir, _bytes, _str
from common_imports import SillyFileLike, HelperTestCase, write_to_file

try:
    unicode = __builtins__["unicode"]
except (NameError, KeyError):
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
    broken_html_str = _bytes("<html><head><title>test<body><h1>page title</h3></p></html>")
    uhtml_str = _str("<html><head><title>test Ã¡\uF8D2</title></head><body><h1>page Ã¡\uF8D2 title</h1></body></html>")

    def tearDown(self):
        super(HtmlParserTestCase, self).tearDown()
        self.etree.set_default_parser()

    def test_module_HTML(self):
        element = self.etree.HTML(self.html_str)
        self.assertEqual(self.etree.tostring(element, method="html"),
                         self.html_str)

    def test_module_HTML_unicode(self):
        element = self.etree.HTML(self.uhtml_str)
        self.assertEqual(unicode(self.etree.tostring(element, method="html",
                                                     encoding='UTF8'), 'UTF8'),
                         unicode(self.uhtml_str.encode('UTF8'), 'UTF8'))

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
        self.assertEquals(pname.tag, 'p:name')

        pname = Element('{test}p:name')
        self.assertEquals(pname.tag, '{test}p:name')

        pname = Element('name')
        pname.tag = 'p:name'
        self.assertEquals(pname.tag, 'p:name')

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
        self.assertEquals(el.tag, "name")

    def test_html_element_name_space(self):
        parser = self.etree.HTMLParser()
        Element = parser.makeelement

        self.assertRaises(ValueError, Element, ' name ')
        self.assertRaises(ValueError, Element, 'na me')
        self.assertRaises(ValueError, Element, '{test} name')

        el = Element('name')
        self.assertRaises(ValueError, setattr, el, 'tag', ' name ')
        self.assertEquals(el.tag, "name")

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
        self.assertEquals(pname.tag, 'p:name')

        pname = SubElement(el, '{test}p:name')
        self.assertEquals(pname.tag, '{test}p:name')

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

    def test_parse_encoding_8bit_explicit(self):
        text = _str('Søk på nettet')
        html_latin1 = (_str('<p>%s</p>') % text).encode('iso-8859-1')

        tree = self.etree.parse(
            BytesIO(html_latin1),
            self.etree.HTMLParser(encoding="iso-8859-1"))
        p = tree.find("//p")
        self.assertEquals(p.text, text)

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
        self.assertEquals(p.text, text)

    def test_module_HTML_broken(self):
        element = self.etree.HTML(self.broken_html_str)
        self.assertEqual(self.etree.tostring(element, method="html"),
                         self.html_str)

    def test_module_HTML_cdata(self):
        # by default, libxml2 generates CDATA nodes for <script> content
        html = _bytes('<html><head><style>foo</style></head></html>')
        element = self.etree.HTML(html)
        self.assertEquals(element[0][0].text, "foo")

    def test_module_HTML_access(self):
        element = self.etree.HTML(self.html_str)
        self.assertEqual(element[0][0].tag, 'title')

    def test_module_parse_html(self):
        parser = self.etree.HTMLParser()
        filename = tempfile.mktemp(suffix=".html")
        write_to_file(filename, self.html_str, 'wb')
        try:
            f = open(filename, 'rb')
            tree = self.etree.parse(f, parser)
            f.close()
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
        self.assertEquals(None, iterator.root)

        events = list(iterator)
        root = iterator.root
        self.assert_(root is not None)
        self.assertEquals(
            [('end', root[0][0]), ('end', root[0]), ('end', root[1][0]),
             ('end', root[1]), ('end', root)],
            events)

    def test_html_iterparse_file(self):
        iterparse = self.etree.iterparse
        iterator = iterparse(fileInTestDir("css_shakespear.html"),
                             html=True)

        self.assertEquals(None, iterator.root)
        events = list(iterator)
        root = iterator.root
        self.assert_(root is not None)
        self.assertEquals(249, len(events))
        self.assertEquals(
            [],
            [ event for (event, element) in events if event != 'end' ])

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(HtmlParserTestCase)])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
