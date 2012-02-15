# -*- coding: utf-8 -*-
import unittest

"""
Tests that ElementMaker works properly.
"""

import sys, os.path
from lxml import etree
from lxml.builder import E

try:
    import cStringIO
    StringIO = cStringIO.StringIO
except ImportError:
    from io import StringIO

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

from common_imports import HelperTestCase

class BuilderTestCase(HelperTestCase):
    etree = etree

    def test_build_from_xpath_result(self):
        elem = etree.parse(StringIO('<root><node>text</node></root>'))
        wrapped = E.b(elem.xpath('string(node)'))
        self.assertEquals(b'<b>text</b>', etree.tostring(wrapped))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(BuilderTestCase)])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
