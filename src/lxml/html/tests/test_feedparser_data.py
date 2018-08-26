import os
import re
try:
    from rfc822 import Message
except ImportError:
    # Python 3
    from email import message_from_file as Message
import unittest
from lxml.tests.common_imports import doctest
from lxml.doctestcompare import LHTMLOutputChecker

from lxml.html.clean import clean, Cleaner

feed_dirs = [
    os.path.join(os.path.dirname(__file__), 'feedparser-data'),
    os.path.join(os.path.dirname(__file__), 'hackers-org-data'),
    ]
bar_re = re.compile(r"-----+")

class DummyInput:
    def __init__(self, **kw):
        for name, value in kw.items():
            setattr(self, name, value)

class FeedTestCase(unittest.TestCase):

    def __init__(self, filename):
        self.filename = filename
        unittest.TestCase.__init__(self)

    def parse(self):
        f = open(self.filename, 'r')
        headers = Message(f)
        c = f.read()
        f.close()
        if not c.strip():
            c = headers.get_payload()
        if not headers.keys():
            raise Exception(
                "File %s has no headers" % self.filename)
        self.description = headers['Description']
        self.expect = headers.get('Expect', '')
        self.ignore = headers.get('Ignore')
        self.options = [
            o.strip() for o in headers.get('Options', '').split(',')
            if o.strip()]
        parts = bar_re.split(c)
        self.input = parts[0].rstrip() + '\n'
        if parts[1:]:
            self.expect = parts[1].rstrip() + '\n'
        else:
            self.expect = None

    def runTest(self):
        self.parse()
        if self.ignore:
            # We've marked this test to be ignored.
            return
        kw = {}
        for name in self.options:
            if name.startswith('-'):
                kw[name[1:]] = False
            else:
                kw[name] = True
        if kw.get('clean', True):
            transformed = Cleaner(**kw).clean_html(self.input)
        else:
            transformed = self.input
        assert self.expect is not None, (
            "No expected output in %s" % self.filename)
        checker = LHTMLOutputChecker()
        if not checker.check_output(self.expect, transformed, 0):
            result = checker.output_difference(
                DummyInput(want=self.expect), transformed, 0)
            #result += '\noptions: %s %r' % (', '.join(self.options), kw)
            #result += repr(transformed)
            raise Exception("\n"+result)

    def shortDescription(self):
        return self.filename

def test_suite():
    suite = unittest.TestSuite()
    for dir in feed_dirs:
        for fn in os.listdir(dir):
            fn = os.path.join(dir, fn)
            if fn.endswith('.data'):
                case = FeedTestCase(fn)
                suite.addTests([case])
                # This is my lazy way of stopping on first error:
                try:
                    case.runTest()
                except:
                    break
    return suite
