import unittest
from lxml.tests.common_imports import make_doctest

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([make_doctest('test_rewritelinks.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
