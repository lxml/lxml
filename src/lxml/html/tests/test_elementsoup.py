import unittest, sys
from lxml.tests.common_imports import make_doctest, HelperTestCase

try:
    import lxml.html.soupparser
    BS_INSTALLED = True
except ImportError:
    if 'bs4' in sys.modules or 'BeautifulSoup' in sys.modules:
        raise  # seems we managed to import BS but not soupparser
    BS_INSTALLED = False

from lxml.html import tostring


if BS_INSTALLED:
    class SoupParserTestCase(HelperTestCase):
        soupparser = lxml.html.soupparser

        def test_broken_attribute(self):
            html = """\
              <html><head></head><body>
                <form><input type='text' disabled size='10'></form>
              </body></html>
            """
            root = self.soupparser.fromstring(html)
            self.assertTrue(root.find('.//input').get('disabled') is not None)

        def test_empty(self):
            tree = self.soupparser.fromstring('')
            res = b'''<html></html>'''
            self.assertEqual(tostring(tree), res)

        def test_text(self):
            tree = self.soupparser.fromstring('huhu')
            res = b'''<html>huhu</html>'''
            self.assertEqual(tostring(tree), res)

        def test_body(self):
            html = '''<body><p>test</p></body>'''
            res = b'''<html><body><p>test</p></body></html>'''
            tree = self.soupparser.fromstring(html)
            self.assertEqual(tostring(tree), res)

        def test_head_body(self):
            # HTML tag missing, parser should fix that
            html = '<head><title>test</title></head><body><p>test</p></body>'
            res = b'<html><head><title>test</title></head><body><p>test</p></body></html>'
            tree = self.soupparser.fromstring(html)
            self.assertEqual(tostring(tree), res)

        def test_wrap_html(self):
            # <head> outside <html>, parser should fix that
            html = '<head><title>title</test></head><html><body/></html>'
            res = b'<html><head><title>title</title></head><body></body></html>'
            tree = self.soupparser.fromstring(html)
            self.assertEqual(tostring(tree), res)

        def test_comment_hyphen(self):
            # These are really invalid XML as per specification
            # https://www.w3.org/TR/REC-xml/#sec-comments
            html = b'<html><!-- comment -- with double-hyphen --></html>'
            tree = self.soupparser.fromstring(html)
            self.assertEqual(tostring(tree), html)

            html = b'<html><!-- comment ends with hyphen ---></html>'
            tree = self.soupparser.fromstring(html)
            self.assertEqual(tostring(tree), html)

        def test_comment_pi(self):
            html = '''<!-- comment -->
<?test asdf?>
<head><title>test</title></head><body><p>test</p></body>
<!-- another comment -->'''
            res = b'''<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN" "http://www.w3.org/TR/REC-html40/loose.dtd">
<!-- comment --><?test asdf?><html><head><title>test</title></head><body><p>test</p></body></html><!-- another comment -->'''
            tree = self.soupparser.fromstring(html).getroottree()
            self.assertEqual(tostring(tree, method='html'), res)

        def test_doctype1(self):
            # Test document type declaration, comments and PI's
            # outside the root
            html = \
'''<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<!--another comment--><html><head><title>My first HTML document</title></head><body><p>Hello world!</p></body></html><?foo bar>'''

            res = \
b'''<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<!--another comment--><html><head><title>My first HTML document</title></head><body><p>Hello world!</p></body></html><?foo bar?>'''

            tree = self.soupparser.fromstring(html).getroottree()
            self.assertEqual(tree.docinfo.public_id, "-//W3C//DTD HTML 4.01//EN")
            self.assertEqual(tostring(tree), res)

        def test_doctype2(self):
            # Test document type declaration, comments and PI's
            # outside the root
            html = \
'''<!DOCTYPE html PUBLIC "-//IETF//DTD HTML//EN">
<!--another comment--><html><head><title>My first HTML document</title></head><body><p>Hello world!</p></body></html><?foo bar?>'''

            res = \
b'''<!DOCTYPE html PUBLIC "-//IETF//DTD HTML//EN">
<!--another comment--><html><head><title>My first HTML document</title></head><body><p>Hello world!</p></body></html><?foo bar?>'''

            tree = self.soupparser.fromstring(html).getroottree()
            self.assertEqual(tree.docinfo.public_id, "-//IETF//DTD HTML//EN")
            self.assertEqual(tostring(tree), res)

        def test_doctype_html5(self):
            # html 5 doctype declaration
            html = b'<!DOCTYPE html>\n<html lang="en"></html>'

            tree = self.soupparser.fromstring(html).getroottree()
            self.assertTrue(tree.docinfo.public_id is None)
            self.assertEqual(tostring(tree), html)


def test_suite():
    suite = unittest.TestSuite()
    if BS_INSTALLED:
        suite.addTests([unittest.makeSuite(SoupParserTestCase)])
        if sys.version_info[0] < 3:
            suite.addTests([make_doctest('../../../../doc/elementsoup.txt')])
    return suite


if __name__ == '__main__':
    unittest.main()
