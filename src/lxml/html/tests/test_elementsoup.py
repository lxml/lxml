import unittest
from lxml.tests.common_imports import doctest

try:
    import BeautifulSoup
    BS_INSTALLED = True
except:
    BS_INSTALLED = False


def test_suite():
    suite = unittest.TestSuite()
    if BS_INSTALLED:
        suite.addTests([doctest.DocFileSuite('../../../../doc/elementsoup.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
