import unittest
from lxml.tests.common_imports import make_doctest

import lxml.html
from lxml.html.clean import Cleaner, clean_html


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

        self.assertEqual(12-5+1, len(list(result.iter())))

    def test_allow_and_remove(self):
        with self.assertRaises(ValueError):
            Cleaner(allow_tags=['a'], remove_unknown_tags=True)

    def test_remove_unknown_tags(self):
        html = """<div><bun>lettuce, tomato, veggie patty</bun></div>"""
        clean_html = """<div>lettuce, tomato, veggie patty</div>"""
        cleaner = Cleaner(remove_unknown_tags=True)
        result = cleaner.clean_html(html)
        self.assertEqual(
            result,
            clean_html,
            msg="Unknown tags not removed. Got: %s" % result,
        )

    def test_safe_attrs_included(self):
        html = """<p><span style="color: #00ffff;">Cyan</span></p>"""

        safe_attrs=set(lxml.html.defs.safe_attrs)
        safe_attrs.add('style')

        cleaner = Cleaner(
            safe_attrs_only=True,
            safe_attrs=safe_attrs)
        result = cleaner.clean_html(html)

        self.assertEqual(html, result)

    def test_safe_attrs_excluded(self):
        html = """<p><span style="color: #00ffff;">Cyan</span></p>"""
        expected = """<p><span>Cyan</span></p>"""

        safe_attrs=set()

        cleaner = Cleaner(
            safe_attrs_only=True,
            safe_attrs=safe_attrs)
        result = cleaner.clean_html(html)

        self.assertEqual(expected, result)

    def test_clean_invalid_root_tag(self):
        # only testing that cleaning with invalid root tags works at all
        s = lxml.html.fromstring('parent <invalid tag>child</another>')
        self.assertEqual('parent child', clean_html(s).text_content())

        s = lxml.html.fromstring('<invalid tag>child</another>')
        self.assertEqual('child', clean_html(s).text_content())

    def test_clean_with_comments(self):
        html = """<p><span style="color: #00ffff;">Cy<!-- xx -->an</span><!-- XXX --></p>"""
        s = lxml.html.fragment_fromstring(html)

        self.assertEqual(
            b'<p><span>Cyan</span></p>',
            lxml.html.tostring(clean_html(s)))
        self.assertEqual(
            '<p><span>Cyan</span></p>',
            clean_html(html))

        cleaner = Cleaner(comments=False)
        result = cleaner.clean_html(s)
        self.assertEqual(
            b'<p><span>Cy<!-- xx -->an</span><!-- XXX --></p>',
            lxml.html.tostring(result))
        self.assertEqual(
            '<p><span>Cy<!-- xx -->an</span><!-- XXX --></p>',
            cleaner.clean_html(html))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([make_doctest('test_clean.txt')])
    suite.addTests([make_doctest('test_clean_embed.txt')])
    suite.addTests(unittest.makeSuite(CleanerTest))
    return suite
