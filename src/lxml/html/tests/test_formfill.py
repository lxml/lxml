import unittest
from lxml.tests.common_imports import make_doctest

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([make_doctest('test_formfill.txt')])
    return suite
