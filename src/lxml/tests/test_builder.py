# -*- coding: utf-8 -*-
import unittest

"""
Tests that ElementMaker works properly.
"""

import sys, os.path
from lxml import etree
from lxml.builder import E

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

from common_imports import HelperTestCase, BytesIO, _bytes

class BuilderTestCase(HelperTestCase):
    etree = etree

    def test_build_from_xpath_result(self):
        elem = etree.parse(BytesIO('<root><node>text</node></root>'))
        wrapped = E.b(elem.xpath('string(node)'))
        self.assertEquals(_bytes('<b>text</b>'), etree.tostring(wrapped))

    def test_unknown_type_raises(self):
        class UnknownType(object):
            pass
        self.assertRaises(TypeError, E.b, UnknownType())

    def test_build_from_list(self):
        wrapped = E.b([E.p(), "text"], E.i())
        self.assertEquals(_bytes('<b><p/>text<i/></b>'),
                          etree.tostring(wrapped))

    def test_destructive_list_build_raises(self):
        # If we try to build from an XPath result, it will implicitly
        # move that result out of its original location.  We want to
        # make users explicitly move or copy the elements, so we raise
        # an exception on an attempt to build from elements with
        # parents.
        elem = etree.parse(BytesIO('<root><node>text</node></root>'))
        self.assertRaises(ValueError, E.b, elem.xpath('node'))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(BuilderTestCase)])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
