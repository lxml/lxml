import unittest
from lxml.tests.common_imports import make_doctest, doctest

from lxml.html import diff

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([make_doctest('test_diff.txt'),
                    doctest.DocTestSuite(diff)])
    return suite

if __name__ == '__main__':
    unittest.main()
