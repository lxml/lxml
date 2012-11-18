import unittest

import lxml.html

from lxml.tests.common_imports import doctest, HelperTestCase, skipif

try:
    import cssselect
except ImportError:
    cssselect = None


HTML = '''
<div>
  <a href="foo">link</a>
  <a>anchor</a>
</div>
'''


class CSSTestCase(HelperTestCase):

    pytestmark = skipif('cssselect is None')

    def test_cssselect(self):
        div, = lxml.html.fromstring(HTML).xpath('//div')

        def count(selector, expected_count, **kwargs):
            result = div.cssselect(selector, **kwargs)
            self.assertEqual(len(result), expected_count)

        count('div', 1)
        count('a', 2)
        count('em', 0)
        # Element names are case-insensitive in HTML
        count('DIV', 1)
        # ... but not in XHTML or XML
        count('DIV', 0, translator='xhtml')
        count('DIV', 0, translator='xml')

        # :contains() is case-insensitive in lxml
        count(':contains("link")', 2)  # div, a
        count(':contains("LInk")', 2)
        # Whatever the document language
        count(':contains("LInk")', 2, translator='xhtml')
        count(':contains("LInk")', 2, translator='xml')
        # ... but not in upstream cssselect
        import cssselect
        count(':contains("link")', 2, translator=cssselect.HTMLTranslator())
        count(':contains("LInk")', 0, translator=cssselect.HTMLTranslator())


def test_suite():
    suite = unittest.TestSuite()
    try:
        import cssselect
    except ImportError:
        # no 'cssselect' installed
        print("Skipping tests in lxml.cssselect - external cssselect package is not installed")
        return suite

    import lxml.cssselect
    suite.addTests(doctest.DocTestSuite(lxml.cssselect))
    suite.addTests([unittest.makeSuite(CSSTestCase)])
    return suite
