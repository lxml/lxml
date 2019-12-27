# -*- coding: utf-8 -*-
from __future__ import absolute_import

import unittest

# These tests check that error handling in the Pyrex code is
# complete.
# It is likely that if there are errors, instead of failing the code
# will simply crash.

import sys, gc, os.path
from lxml import etree

from .common_imports import HelperTestCase


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
        getrefcount = sys.getrefcount

        # must disable tracing as it could change the refcounts
        trace_func = sys.gettrace()
        try:
            sys.settrace(None)
            gc.collect()

            count = getrefcount(None)

            l = [Element('name'), Element('name')]
            l.append(l)

            del l
            gc.collect()
            count = getrefcount(None) - count

            self.assertEqual(count, 0)
        finally:
            sys.settrace(trace_func)

    def test_xmlsyntaxerror_has_info(self):
        broken_xml_name = 'test_broken.xml'
        broken_xml_path = os.path.join(os.path.dirname(__file__), broken_xml_name)
        fail_msg = 'test_broken.xml should raise an etree.XMLSyntaxError'
        try:
            etree.parse(broken_xml_path)
        except etree.XMLSyntaxError as e:
            # invariant
            self.assertEqual(e.position, (e.lineno, e.offset + 1), 'position and lineno/offset out of sync')
            # SyntaxError info derived from file & contents
            self.assertTrue(e.filename.endswith(broken_xml_name), 'filename must be preserved')
            self.assertEqual(e.lineno, 1)
            self.assertEqual(e.offset, 10)
        except Exception as e:
            self.fail('{0}, not {1}'.format(fail_msg, type(e)))
        else:
            self.fail('test_broken.xml should raise an etree.XMLSyntaxError')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ErrorTestCase)])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
