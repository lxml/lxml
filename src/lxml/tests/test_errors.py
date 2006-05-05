# -*- coding: utf-8 -*-
import unittest, doctest

# These tests check that error handling in the Pyrex code is
# complete.
# It is likely that if there are errors, instead of failing the code
# will simply crash.

from lxml import etree

class ErrorTestCase(unittest.TestCase):
    etree = etree

    def test_bad_element(self):
        # attrib argument of Element() should be a dictionary, so if
        # we pass a string we should get an error.
        self.assertRaises(AttributeError, self.etree.Element, 'a', 'b')

    def test_empty_parse(self):
        self.assertRaises(etree.XMLSyntaxError, etree.fromstring, '')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ErrorTestCase)])
    return suite

if __name__ == '__main__':
    unittest.main()
