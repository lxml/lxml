import unittest
from lxml.tests.common_imports import doctest

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([doctest.DocFileSuite('test_formfill.txt')])
    return suite
