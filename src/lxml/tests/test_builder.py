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
        class StringSubclass(str): pass
        wrapped = E.b(StringSubclass('Hello'))
        self.assertEqual(_bytes('<b>Hello</b>'), etree.tostring(wrapped))

    def test_unknown_type_raises(self):
        class UnknownType(object):
            pass
        self.assertRaises(TypeError, E.b, UnknownType())

    def test_cdata(self):
        wrapped = E.b(etree.CDATA('Hello'))
        self.assertEqual(_bytes('<b><![CDATA[Hello]]></b>'), etree.tostring(wrapped))

    def test_cdata_solo(self):
        self.assertRaises(ValueError, E.b, 'Hello', etree.CDATA('World'))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(BuilderTestCase)])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
