import unittest, sys
from lxml.tests.common_imports import make_doctest, doctest
import lxml.html

def test_suite():
    suite = unittest.TestSuite()
    if sys.version_info >= (2,4):
        suite.addTests([make_doctest('test_basic.txt')])
    suite.addTests([doctest.DocTestSuite(lxml.html)])
    return suite

if __name__ == '__main__':
    unittest.main()
