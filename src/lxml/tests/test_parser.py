# -*- coding: UTF-8 -*-

"""
Tests specific to the parser API
"""


import unittest, doctest

from StringIO import StringIO
import os, shutil, tempfile, copy
import gzip
import urllib2

from common_imports import etree, HelperTestCase, canonicalize, SillyFileLike

class ETreeParserTestCase(HelperTestCase):
    def test_parse_options(self):
        xml = '<a xmlns="test"><b xmlns="test"/></a>'
        strip_xml = '<a xmlns="test"><b/></a>'

        f = SillyFileLike(xml)
        parser = etree.XMLParser(ns_clean=False)
        root = etree.ElementTree().parse(f, parser)
        self.assertEqual(etree.tostring(root), xml)

        f = SillyFileLike(xml)
        parser = etree.XMLParser(ns_clean=True)
        root = etree.ElementTree().parse(f, parser)
        self.assertEqual(etree.tostring(root), strip_xml)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeParserTestCase)])
#    suite.addTests(
#        [doctest.DocFileSuite('../../../doc/parser.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
