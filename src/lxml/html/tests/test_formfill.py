import doctest
import unittest

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([doctest.DocFileSuite('test_formfill.txt')])
    return suite
