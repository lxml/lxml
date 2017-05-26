# -*- coding: utf-8 -*-

"""
Tests for the ElementPath implementation.
"""

from __future__ import absolute_import

import unittest
from .common_imports import etree, HelperTestCase


class EtreeElementPathTestCase(HelperTestCase):
    etree = etree
    from lxml import _elementpath

    def test_cache(self):
        self._elementpath._cache.clear()
        el = self.etree.XML(b'<a><b><c/><c/></b></a>')
        self.assertFalse(self._elementpath._cache)

        self.assertTrue(el.findall('b/c'))
        self.assertEqual(1, len(self._elementpath._cache))
        self.assertTrue(el.findall('b/c'))
        self.assertEqual(1, len(self._elementpath._cache))
        self.assertFalse(el.findall('xxx'))
        self.assertEqual(2, len(self._elementpath._cache))
        self.assertFalse(el.findall('xxx'))
        self.assertEqual(2, len(self._elementpath._cache))
        self.assertTrue(el.findall('b/c'))
        self.assertEqual(2, len(self._elementpath._cache))

    def test_tokenizer(self):
        def assert_tokens(tokens, path, namespaces=None):
            self.assertEqual(tokens, list(self._elementpath.xpath_tokenizer(path, namespaces)))

        assert_tokens(
            [('/', '')],
            '/',
        )
        assert_tokens(
            [('.', ''), ('/', ''), ('', 'a'), ('/', ''), ('', 'b'), ('/', ''), ('', 'c')],
            './a/b/c',
        )
        assert_tokens(
            [('/', ''), ('', 'a'), ('/', ''), ('', 'b'), ('/', ''), ('', 'c')],
            '/a/b/c',
        )
        assert_tokens(
            [('/', ''), ('', '{nsx}a'), ('/', ''), ('', '{nsy}b'), ('/', ''), ('', 'c')],
            '/x:a/y:b/c',
            {'x': 'nsx', 'y': 'nsy'},
        )
        assert_tokens(
            [('/', ''), ('', '{nsx}a'), ('/', ''), ('', '{nsy}b'), ('/', ''), ('', '{nsnone}c')],
            '/x:a/y:b/c',
            {'x': 'nsx', 'y': 'nsy', None: 'nsnone'},
        )


#class ElementTreeElementPathTestCase(EtreeElementPathTestCase):
#    import xml.etree.ElementTree as etree
#    import xml.etree.ElementPath as _elementpath


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(EtreeElementPathTestCase)])
    #suite.addTests([unittest.makeSuite(ElementTreeElementPathTestCase)])
    return suite


if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
