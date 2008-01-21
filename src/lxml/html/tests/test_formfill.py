import unittest, sys
from lxml.tests.common_imports import doctest

def test_suite():
    suite = unittest.TestSuite()
    if sys.version_info >= (2,4):
        suite.addTests([doctest.DocFileSuite('test_formfill.txt')])
    return suite
