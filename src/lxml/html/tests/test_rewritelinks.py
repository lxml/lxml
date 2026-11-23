import doctest
import sys
import unittest
from lxml import html


class TestRewriteLinks(unittest.TestCase):
    def test_rewrite_links_style_text_many_urls(self):
        css = 'a{background:url(img/%d.png)} @import "sheet%d.css";\n'
        count = 50
        doc = html.fromstring(
            '<html><head><style>%s</style></head><body></body></html>'
            % ''.join(css % (n, n) for n in range(count)))
        doc.make_links_absolute('http://example.com/base/')
        self.assertEqual(
            doc.find('.//style').text,
            ''.join(
                css.replace('img/', 'http://example.com/base/img/')
                   .replace('"sheet', '"http://example.com/base/sheet') % (n, n)
                for n in range(count)))

    def test_rewrite_links_style_text_unchanged_and_changed(self):
        doc = html.fromstring(
            '<html><head><style>a{b:url(keep)} c{d:url(x)} e{f:url(keep)} g{h:url(y)}'
            '</style></head></html>')
        doc.rewrite_links(
            lambda link: link if link == 'keep' else 'LONG-' + link,
            resolve_base_href=False)
        self.assertEqual(
            doc.find('.//style').text,
            'a{b:url(keep)} c{d:url(LONG-x)} e{f:url(keep)} g{h:url(LONG-y)}')

    def test_rewrite_links_style_attribute_many_urls(self):
        doc = html.fromstring(
            '<div style="a:url(1.png);b:url(\'2.png\');c:url(&quot;3.png&quot;)"></div>')
        doc.rewrite_links(lambda link: 'http://h/' + link, resolve_base_href=False)
        self.assertEqual(
            doc.get('style'),
            'a:url(http://h/1.png);b:url(\'http://h/2.png\');c:url("http://h/3.png")')

    def test_rewrite_links_none_removes_style_text_and_attribute(self):
        doc = html.fromstring(
            '<html><head><style>a{b:url(x)} c{d:url(y)}</style></head>'
            '<body><div style="a:url(x);b:url(y)" id="d"><a href="z">t</a></div></body></html>')
        doc.rewrite_links(
            lambda link: None if link == 'y' else link + '2',
            resolve_base_href=False)
        self.assertEqual(doc.find('.//style').text, '')
        div = doc.find('.//div')
        self.assertNotIn('style', div.attrib)
        self.assertEqual(div.get('id'), 'd')
        self.assertEqual(div[0].get('href'), 'z2')

    def test_rewrite_links_style_text_and_attribute_in_one_pass(self):
        doc = html.fromstring(
            '<html><head><style style="a:url(1);b:url(2)">c{d:url(3)} e{f:url(4)}'
            '</style></head></html>')
        doc.rewrite_links(lambda link: 'N' + link + 'N', resolve_base_href=False)
        style = doc.find('.//style')
        self.assertEqual(style.text, 'c{d:url(N3N)} e{f:url(N4N)}')
        self.assertEqual(style.get('style'), 'a:url(N1N);b:url(N2N)')

    def test_rewrite_links_none_after_replacement_in_same_value(self):
        # Links of one value are reported last to first, so the removal of
        # the first link happens after the later ones were replaced.
        doc = html.fromstring(
            '<html><head><style>a{b:url(x)} c{d:url(y)}</style></head>'
            '<body><div style="a:url(x);b:url(y)"></div></body></html>')
        doc.rewrite_links(
            lambda link: None if link == 'x' else link + '2',
            resolve_base_href=False)
        self.assertEqual(doc.find('.//style').text, '')
        self.assertNotIn('style', doc.find('.//div').attrib)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([doctest.DocFileSuite('test_rewritelinks.txt')])
    suite.addTest(unittest.TestLoader().loadTestsFromModule(sys.modules[__name__]))
    return suite

if __name__ == '__main__':
    unittest.main()
