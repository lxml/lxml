import doctest
import unittest

from lxml.html import diff

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([doctest.DocFileSuite('test_diff.txt'),
                    doctest.DocTestSuite(diff)])
    return suite

if __name__ == '__main__':
    unittest.main()
