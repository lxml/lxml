import unittest
from lxml.tests.common_imports import doctest

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([doctest.DocFileSuite('test_basic.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
