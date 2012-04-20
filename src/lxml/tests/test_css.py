import unittest

import lxml.etree
import lxml.html
import lxml.cssselect

from lxml.tests.common_imports import doctest, HelperTestCase


HTML = '''
<div>
  <a href="foo">link</a>
  <a>anchor</a>
</div>
'''


class CSSTestCase(HelperTestCase):

    def test_xml(self):
        self._run(lxml.etree.fromstring(HTML), is_html=False)

    def test_html(self):
        # HTML elements default to the HTML translator.
        self._run(lxml.html.document_fromstring(HTML), is_html=True)

    def _run(self, document, is_html):
        div, = document.xpath('//div')

        def count(selector, expected_count, **kwargs):
            result = div.cssselect(selector, **kwargs)
            self.assertEqual(len(result), expected_count)

        count('div', 1)
        count('a', 2)
        count('em', 0)
        if is_html:
            # Element names are case-insensitive in HTML
            count('DIV', 1)
            # ... but not in XHTML
            count('DIV', 0, translator='xhtml')
        else:
            # Element names are case-sensitive in XML
            count('DIV', 0)

        # :contains() is case-insensitive in lxml
        count(':contains("link")', 2)  # div, a
        count(':contains("LInk")', 2)
        # ... but not in upstream cssselect
        import cssselect
        count(':contains("link")', 2, translator=cssselect.HTMLTranslator())
        count(':contains("LInk")', 0, translator=cssselect.HTMLTranslator())


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests(doctest.DocTestSuite(lxml.cssselect))
    suite.addTests([unittest.makeSuite(CSSTestCase)])
    return suite
