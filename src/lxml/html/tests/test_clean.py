import unittest, sys
from lxml.tests.common_imports import make_doctest
from lxml.etree import LIBXML_VERSION

def test_suite():
    suite = unittest.TestSuite()
    if sys.version_info >= (2,4):
        suite.addTests([make_doctest('test_clean.txt')])
        if LIBXML_VERSION >= (2,6,31):
            suite.addTests([make_doctest('test_clean_embed.txt')])
    return suite
