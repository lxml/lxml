import doctest
import sys
import unittest

from lxml.html import fromstring, iterlinks


class TestIterLinks(unittest.TestCase):
    def test_unterminated_css_url_runtime(self):
        # Used to take quadratic time in the number of unterminated 'url('.
        payload = 'url(' * 50000
        doc = fromstring(
            '<div style="%s"><style>%s</style>'
            '<p style="url(/a.png) %s">x</p></div>' % (payload, payload, payload))
        links = [(el.tag, attr, link) for el, attr, link, pos in iterlinks(doc)]
        self.assertEqual(links, [('p', 'style', '/a.png')])

    def test_meta_refresh_without_semicolon_runtime(self):
        # Used to take quadratic time in the length of the 'content' value.
        content = 'a' * 200000
        doc = fromstring(
            '<html><head><meta http-equiv="refresh" content="%s"></head></html>' % content)
        links = [(attr, link) for el, attr, link, pos in iterlinks(doc)]
        self.assertEqual(links, [('content', content)])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([doctest.DocFileSuite('test_rewritelinks.txt')])
    suite.addTest(unittest.TestLoader().loadTestsFromModule(sys.modules[__name__]))
    return suite

if __name__ == '__main__':
    unittest.main()
