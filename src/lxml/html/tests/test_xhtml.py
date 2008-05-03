import unittest, sys
from lxml.tests.common_imports import doctest
import lxml.html

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([doctest.DocFileSuite('test_xhtml.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
