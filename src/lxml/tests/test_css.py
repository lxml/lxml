import unittest, sys
from lxml.tests.common_imports import doctest, make_doctest, HelperTestCase
from lxml import html
from lxml import cssselect
import os

doc_fn = os.path.join(os.path.dirname(__file__),
                      'css_shakespear.html')

try:
    basestring = __builtins__['basestring']
except (NameError, KeyError):
    basestring = (str, bytes)

# Data borrowed from http://mootools.net/slickspeed/

class CSSTestCase(HelperTestCase):
    
    selectors = [
        ## Changed from original; probably because I'm only searching the body
        #('*', 252),
        ('*', 246),
        ('div:only-child', 22), # ?
        ## Changed from original, because the original doesn't make sense.
        ## There really aren't that many occurrances of 'celia'
        #('div:contains(CELIA)', 243),
        ('div:contains(CELIA)', 30),
        ('div:nth-child(even)', 106),
        ('div:nth-child(2n)', 106),
        ('div:nth-child(odd)', 137),
        ('div:nth-child(2n+1)', 137),
        ('div:nth-child(n)', 243),
        ('div:last-child', 53),
        ('div:first-child', 51),
        ('div > div', 242),
        ('div + div', 190),
        ('div ~ div', 190),
        ('body', 1),
        ('body div', 243),
        ('div', 243),
        ('div div', 242),
        ('div div div', 241),
        ('div, div, div', 243),
        ('div, a, span', 243),
        ('.dialog', 51),
        ('div.dialog', 51),
        ('div .dialog', 51),
        ('div.character, div.dialog', 99),
        ('div.direction.dialog', 0),
        ('div.dialog.direction', 0),
        ('div.dialog.scene', 1),
        ('div.scene.scene', 1),
        ('div.scene .scene', 0),
        ('div.direction .dialog ', 0),
        ('div .dialog .direction', 4),
        ('div.dialog .dialog .direction', 4),
        ('#speech5', 1),
        ('div#speech5', 1),
        ('div #speech5', 1),
        ('div.scene div.dialog', 49),
        ('div#scene1 div.dialog div', 142),
        ('#scene1 #speech1', 1),
        ('div[class]', 103),
        ('div[class=dialog]', 50),
        ('div[class^=dia]', 51),
        ('div[class$=log]', 50),
        ('div[class*=sce]', 1),
        ('div[class|=dialog]', 50), # ? Seems right
        ('div[class!=madeup]', 243), # ? Seems right
        ('div[class~=dialog]', 51), # ? Seems right
        ]

    def __init__(self, index):
        self.index = index
        super(HelperTestCase, self).__init__()

    def all(cls):
        for i in range(len(cls.selectors)):
            yield cls(i)
    all = classmethod(all)

    def runTest(self):
        f = open(doc_fn, 'rb')
        c = f.read()
        f.close()
        doc = html.document_fromstring(c)
        body = doc.xpath('//body')[0]
        bad = []
        selector, count = self.selectors[self.index]
        xpath = cssselect.css_to_xpath(cssselect.parse(selector))
        try:
            results = body.xpath(xpath)
        except Exception:
            e = sys.exc_info()[1]
            e.args = ("%s for xpath %r" % (e, xpath))
            raise
        found = {}
        for item in results:
            if item in found:
                assert 0, (
                    "Element shows up multiple times: %r" % item)
            found[item] = None
        if isinstance(results, basestring):
            assert 0, (
                "Got string result (%r), not element, for xpath %r"
                % (results[:20], str(xpath)))
        if len(results) != count:
            #if self.shortDescription() == 'div.character, div.dialog':
            #    import pdb; pdb.set_trace()
            assert 0, (
                "Did not get expected results (%s) instead %s for xpath %r"
                % (count, len(results), str(xpath)))

    def shortDescription(self):
        return self.selectors[self.index][0]

def unique(s):
    found = {}
    result = []
    for item in s:
        if item in found:
            continue
        found[item] = None
        result.append(s)
    return result
        
def test_suite():
    suite = unittest.TestSuite()
    if sys.version_info >= (2,4):
        suite.addTests([make_doctest('test_css_select.txt')])
    suite.addTests([make_doctest('test_css.txt')])
    suite.addTests(doctest.DocTestSuite(cssselect))
    suite.addTests(list(CSSTestCase.all()))
    return suite
