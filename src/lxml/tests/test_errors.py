# -*- coding: utf-8 -*-
import unittest, doctest

# These tests check that error handling in the Pyrex code is
# complete.
# It is likely that if there are errors, instead of failing the code
# will simply crash.

import sys, gc, os.path
from lxml import etree

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

from common_imports import HelperTestCase

class ErrorTestCase(HelperTestCase):
    etree = etree

    def test_bad_element(self):
        # attrib argument of Element() should be a dictionary, so if
        # we pass a string we should get an error.
        self.assertRaises(TypeError, self.etree.Element, 'a', 'b')

    def test_empty_parse(self):
        self.assertRaises(etree.XMLSyntaxError, etree.fromstring, '')

    def test_element_cyclic_gc_none(self):
        # test if cyclic reference can crash etree
        Element = self.etree.Element
        gc.collect()

        count = sys.getrefcount(None)

        l = [Element('name'), Element('name')]
        l.append(l)

        del l
        gc.collect()

        self.assertEqual(sys.getrefcount(None), count)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ErrorTestCase)])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
