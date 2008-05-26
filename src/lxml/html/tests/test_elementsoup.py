import unittest, sys
from lxml.tests.common_imports import make_doctest

try:
    import BeautifulSoup
    BS_INSTALLED = True
except ImportError:
    BS_INSTALLED = False


def test_suite():
    suite = unittest.TestSuite()
    if sys.version_info >= (2,4):
        if BS_INSTALLED:
            suite.addTests([make_doctest('../../../../doc/elementsoup.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
