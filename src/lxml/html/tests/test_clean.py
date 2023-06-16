import base64
import gzip
import io
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

    def test_sneaky_noscript_in_style(self):
        # This gets parsed as <noscript> -> <style>"...</noscript>..."</style>
        # thus passing the </noscript> through into the output.
        html = '<noscript><style><a title="</noscript><img src=x onerror=alert(1)>">'
        s = lxml.html.fragment_fromstring(html)

        self.assertEqual(
            b'<noscript><style>/* deleted */</style></noscript>',
            lxml.html.tostring(clean_html(s)))

    def test_sneaky_js_in_math_style(self):
        # This gets parsed as <math> -> <style>"..."</style>
        # thus passing any tag/script/whatever content through into the output.
        html = '<math><style><img src=x onerror=alert(1)></style></math>'
        s = lxml.html.fragment_fromstring(html)

        self.assertEqual(
            b'<math><style>/* deleted */</style></math>',
            lxml.html.tostring(clean_html(s)))

    def test_sneaky_import_in_style(self):
        # Prevent "@@importimport" -> "@import" replacement etc.
        style_codes = [
            "@@importimport(extstyle.css)",
            "@ @  import import(extstyle.css)",
            "@ @ importimport(extstyle.css)",
            "@@  import import(extstyle.css)",
            "@ @import import(extstyle.css)",
            "@@importimport()",
            "@@importimport()  ()",
            "@/* ... */import()",
            "@im/* ... */port()",
            "@ @import/* ... */import()",
            "@    /* ... */      import()",
        ]
        for style_code in style_codes:
            html = '<style>%s</style>' % style_code
            s = lxml.html.fragment_fromstring(html)

            cleaned = lxml.html.tostring(clean_html(s))
            self.assertEqual(
                b'<style>/* deleted */</style>',
                cleaned,
                "%s  ->  %s" % (style_code, cleaned))

    def test_sneaky_schemes_in_style(self):
        style_codes = [
            "javasjavascript:cript:",
            "javascriptjavascript::",
            "javascriptjavascript:: :",
            "vbjavascript:cript:",
        ]
        for style_code in style_codes:
            html = '<style>%s</style>' % style_code
            s = lxml.html.fragment_fromstring(html)

            cleaned = lxml.html.tostring(clean_html(s))
            self.assertEqual(
                b'<style>/* deleted */</style>',
                cleaned,
                "%s  ->  %s" % (style_code, cleaned))

    def test_sneaky_urls_in_style(self):
        style_codes = [
            "url(data:image/svg+xml;base64,...)",
            "url(javasjavascript:cript:)",
            "url(javasjavascript:cript: ::)",
            "url(vbjavascript:cript:)",
            "url(vbjavascript:cript: :)",
        ]
        for style_code in style_codes:
            html = '<style>%s</style>' % style_code
            s = lxml.html.fragment_fromstring(html)

            cleaned = lxml.html.tostring(clean_html(s))
            self.assertEqual(
                b'<style>url()</style>',
                cleaned,
                "%s  ->  %s" % (style_code, cleaned))

    def test_svg_data_links(self):
        # Remove SVG images with potentially insecure content.
        svg = b'<svg onload="alert(123)" />'
        gzout = io.BytesIO()
        f = gzip.GzipFile(fileobj=gzout, mode='wb')
        f.write(svg)
        f.close()
        svgz = gzout.getvalue()
        svg_b64 = base64.b64encode(svg).decode('ASCII')
        svgz_b64 = base64.b64encode(svgz).decode('ASCII')
        urls = [
            "data:image/svg+xml;base64," + svg_b64,
            "data:image/svg+xml-compressed;base64," + svgz_b64,
        ]
        for url in urls:
            html = '<img src="%s">' % url
            s = lxml.html.fragment_fromstring(html)

            cleaned = lxml.html.tostring(clean_html(s))
            self.assertEqual(
                b'<img src="">',
                cleaned,
                "%s  ->  %s" % (url, cleaned))

    def test_image_data_links(self):
        data = b'123'
        data_b64 = base64.b64encode(data).decode('ASCII')
        urls = [
            "data:image/jpeg;base64," + data_b64,
            "data:image/apng;base64," + data_b64,
            "data:image/png;base64," + data_b64,
            "data:image/gif;base64," + data_b64,
            "data:image/webp;base64," + data_b64,
            "data:image/bmp;base64," + data_b64,
            "data:image/tiff;base64," + data_b64,
            "data:image/x-icon;base64," + data_b64,
        ]
        for url in urls:
            html = '<img src="%s">' % url
            s = lxml.html.fragment_fromstring(html)

            cleaned = lxml.html.tostring(clean_html(s))
            self.assertEqual(
                html.encode("UTF-8"),
                cleaned,
                "%s  ->  %s" % (url, cleaned))

    def test_image_data_links_in_style(self):
        data = b'123'
        data_b64 = base64.b64encode(data).decode('ASCII')
        urls = [
            "data:image/jpeg;base64," + data_b64,
            "data:image/apng;base64," + data_b64,
            "data:image/png;base64," + data_b64,
            "data:image/gif;base64," + data_b64,
            "data:image/webp;base64," + data_b64,
            "data:image/bmp;base64," + data_b64,
            "data:image/tiff;base64," + data_b64,
            "data:image/x-icon;base64," + data_b64,
        ]
        for url in urls:
            html = '<style> url(%s) </style>' % url
            s = lxml.html.fragment_fromstring(html)

            cleaned = lxml.html.tostring(clean_html(s))
            self.assertEqual(
                html.encode("UTF-8"),
                cleaned,
                "%s  ->  %s" % (url, cleaned))

    def test_formaction_attribute_in_button_input(self):
        # The formaction attribute overrides the form's action and should be
        # treated as a malicious link attribute
        html = ('<form id="test"><input type="submit" formaction="javascript:alert(1)"></form>'
        '<button form="test" formaction="javascript:alert(1)">X</button>')
        expected = ('<div><form id="test"><input type="submit" formaction=""></form>'
        '<button form="test" formaction="">X</button></div>')
        cleaner = Cleaner(
            forms=False,
            safe_attrs_only=False,
        )
        self.assertEqual(
            expected,
            cleaner.clean_html(html))

    def test_host_whitelist_valid(self):
        # Frame with valid hostname in src is allowed.
        html = '<div><iframe src="https://example.com/page"></div>'
        expected = '<div><iframe src="https://example.com/page"></iframe></div>'
        cleaner = Cleaner(frames=False, host_whitelist=["example.com"])
        self.assertEqual(expected, cleaner.clean_html(html))

    def test_host_whitelist_invalid(self):
        html = '<div><iframe src="https://evil.com/page"></div>'
        expected = '<div></div>'
        cleaner = Cleaner(frames=False, host_whitelist=["example.com"])
        self.assertEqual(expected, cleaner.clean_html(html))

    def test_host_whitelist_sneaky_userinfo(self):
        # Regression test: Don't be fooled by hostname and colon in userinfo.
        html = '<div><iframe src="https://example.com:@evil.com/page"></div>'
        expected = '<div></div>'
        cleaner = Cleaner(frames=False, host_whitelist=["example.com"])
        self.assertEqual(expected, cleaner.clean_html(html))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([make_doctest('test_clean.txt')])
    suite.addTests([make_doctest('test_clean_embed.txt')])
    suite.addTests(unittest.makeSuite(CleanerTest))
    return suite
