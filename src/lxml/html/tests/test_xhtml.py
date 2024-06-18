import doctest
import unittest

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([doctest.DocFileSuite('test_xhtml.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
