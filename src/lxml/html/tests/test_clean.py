import unittest, sys
from lxml.tests.common_imports import make_doctest
from lxml.etree import LIBXML_VERSION

import lxml.html
from lxml.html.clean import Cleaner

class CleanerTest(unittest.TestCase):
    def test_allow_tags(self):
        html = """
            <html>
            <head>
            </head>
            <body>
            <p>some text</p>
            <table>
            <tr>
            <td>hello</td><td>world</td>
            </tr>
            <tr>
            <td>hello</td><td>world</td>
            </tr>
            </table>
            <img>
            </body>
            </html>
            """

        html_root = lxml.html.document_fromstring(html)
        cleaner = Cleaner(
            remove_unknown_tags = False,
            allow_tags = ['table', 'tr', 'td'])
        result = cleaner.clean_html(html_root)

        self.assertEquals(12-5+1, len(list(result.iter())))

def test_suite():
    suite = unittest.TestSuite()
    if sys.version_info >= (2,4):
        suite.addTests([make_doctest('test_clean.txt')])
        if LIBXML_VERSION >= (2,6,31):
            suite.addTests([make_doctest('test_clean_embed.txt')])
    suite.addTests(unittest.makeSuite(CleanerTest))
    return suite
