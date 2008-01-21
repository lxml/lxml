import unittest, sys
from lxml.tests.common_imports import doctest

from lxml.html import diff

def test_suite():
    suite = unittest.TestSuite()
    if sys.version_info >= (2,4):
        suite.addTests([doctest.DocFileSuite('test_diff.txt'),
                        doctest.DocTestSuite(diff)])
    return suite

if __name__ == '__main__':
    unittest.main()
