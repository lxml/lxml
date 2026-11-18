import doctest
import time
import unittest

import lxml.html


class IterlinksComplexityTest(unittest.TestCase):
    # These inputs took minutes to process with the previous, quadratic regular expressions.
    n = 100000

    def assertFast(self, html):
        doc = lxml.html.fromstring(html)
        t = time.perf_counter()
        links = list(doc.iterlinks())
        self.assertLess(time.perf_counter() - t, 10)
        return [link for el, attr, link, pos in links]

    def test_meta_refresh_without_semicolon(self):
        content = 'a' * self.n
        links = self.assertFast(
            '<html><head><meta http-equiv="refresh" content="%s"></head></html>' % content)
        self.assertEqual([content], links)

    def test_meta_refresh_with_newline(self):
        content = ';' * self.n + '&#10;x'
        links = self.assertFast(
            '<html><head><meta http-equiv="refresh" content="%s"></head></html>' % content)
        self.assertEqual([';' * (self.n - 1) + '\nx'], links)

    def test_unterminated_css_url_in_style_element(self):
        links = self.assertFast(
            '<html><head><style>%s</style></head></html>' % ('url(' * (self.n // 4)))
        self.assertEqual([], links)

    def test_unterminated_css_url_in_style_attribute(self):
        links = self.assertFast('<p style="%s">x</p>' % ("url('" * (self.n // 5)))
        self.assertEqual([], links)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(IterlinksComplexityTest)])
    suite.addTests([doctest.DocFileSuite('test_rewritelinks.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
