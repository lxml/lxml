import unittest, sys
from lxml.tests.common_imports import make_doctest, HelperTestCase

try:
    import BeautifulSoup
    BS_INSTALLED = True
except ImportError:
    BS_INSTALLED = False

if BS_INSTALLED:
    class SoupParserTestCase(HelperTestCase):
        from lxml.html import soupparser

        def test_broken_attribute(self):
            html = """\
              <html><head></head><body>
                <form><input type='text' disabled size='10'></form>
              </body></html>
            """
            root = self.soupparser.fromstring(html)
            self.assert_(root.find('.//input').get('disabled') is not None)


def test_suite():
    suite = unittest.TestSuite()
    if sys.version_info >= (2,4):
        if BS_INSTALLED:
            suite.addTests([unittest.makeSuite(SoupParserTestCase)])
            suite.addTests([make_doctest('../../../../doc/elementsoup.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
