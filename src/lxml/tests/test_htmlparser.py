# -*- coding: UTF-8 -*-

"""
HTML parser test cases for etree
"""

import unittest
import tempfile

from common_imports import StringIO, etree, fileInTestDir, SillyFileLike, HelperTestCase

class HtmlParserTestCaseBase(HelperTestCase):
    """HTML parser test cases
    """
    etree = etree

    html_str = "<html><head><title>test</title></head><body><h1>page title</h1></body></html>"
    broken_html_str = "<html><head><title>test<body><h1>page title</body></html>"

    def tearDown(self):
        self.etree.set_default_parser()

    def test_module_HTML(self):
        element = self.etree.HTML(self.html_str)
        self.assertEqual(self.etree.tostring(element),
                         self.html_str)

    def test_module_parse_html_error(self):
        parser = self.etree.HTMLParser(recover=False)
        parse = self.etree.parse
        f = StringIO("<html></body>")
        self.assertRaises(self.etree.XMLSyntaxError,
                          parse, f, parser)

    def test_module_HTML_broken(self):
        element = self.etree.HTML(self.broken_html_str)
        self.assertEqual(self.etree.tostring(element),
                         self.html_str)

    def test_module_HTML_access(self):
        element = self.etree.HTML(self.html_str)
        element = element[0][0]
        self.assertEqual(element.tag, 'title')

    def test_module_parse_html(self):
        parser = self.etree.HTMLParser()
        filename = tempfile.mktemp(suffix=".html")
        open(filename, 'wb').write(self.html_str)
        f = open(filename, 'r')
        tree = self.etree.parse(f, parser)
        self.assertEqual(self.etree.tostring(tree.getroot()), self.html_str)

    def test_html_file_error(self):
        parser = self.etree.HTMLParser()
        parse = self.etree.parse
        self.assertRaises(IOError,
                          parse, "__some_hopefully_nonexisting_file__.html",
                          parser)

    def test_default_parser_HTML_broken(self):
        self.assertRaises(self.etree.XMLSyntaxError,
                          self.etree.parse, StringIO(self.broken_html_str))

        self.etree.set_default_parser( self.etree.HTMLParser() )

        tree = self.etree.parse(StringIO(self.broken_html_str))
        self.assertEqual(self.etree.tostring(tree.getroot()),
                         self.html_str)

        self.etree.set_default_parser()

        self.assertRaises(self.etree.XMLSyntaxError,
                          self.etree.parse, StringIO(self.broken_html_str))

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(HtmlParserTestCaseBase)])
    return suite

if __name__ == '__main__':
    unittest.main()
