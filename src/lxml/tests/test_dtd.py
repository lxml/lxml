# -*- coding: utf-8 -*-

"""
Test cases related to DTD parsing and validation
"""

import unittest

from common_imports import etree, StringIO, doctest
from common_imports import HelperTestCase, fileInTestDir

class ETreeDtdTestCase(HelperTestCase):
    def test_dtd(self):
        pass

    def test_dtd_file(self):
        parse = etree.parse
        tree = parse(fileInTestDir("test.xml"))
        root = tree.getroot()

        dtd = etree.DTD(fileInTestDir("test.dtd"))
        self.assert_(dtd.validate(root))

    def test_dtd_stringio(self):
        root = etree.XML("<b/>")
        dtd = etree.DTD(StringIO("<!ELEMENT b EMPTY>"))
        self.assert_(dtd.validate(root))

    def test_dtd_invalid(self):
        root = etree.XML("<b><a/></b>")
        dtd = etree.DTD(StringIO("<!ELEMENT b EMPTY>"))
        self.assertRaises(etree.DocumentInvalid, dtd.assertValid, root)

    def test_dtd_assertValid(self):
        root = etree.XML("<b><a/></b>")
        dtd = etree.DTD(StringIO("<!ELEMENT b (a)><!ELEMENT a EMPTY>"))
        dtd.assertValid(root)

    def test_dtd_broken(self):
        self.assertRaises(etree.DTDParseError, etree.DTD,
                          StringIO("<!ELEMENT b HONKEY>"))

    def test_parse_file_dtd(self):
        parser = etree.XMLParser(attribute_defaults=True)

        tree = etree.parse(fileInTestDir('test.xml'), parser)
        root = tree.getroot()

        self.assertEquals(
            "valueA",
            root.get("default"))
        self.assertEquals(
            "valueB",
            root[0].get("default"))

    def test_iterparse_file_dtd(self):
        iterparse = etree.iterparse
        iterator = iterparse(fileInTestDir("test.xml"), events=("start",),
                             attribute_defaults=True)
        attributes = [ element.get("default")
                       for event, element in iterator ]
        self.assertEquals(
            ["valueA", "valueB"],
            attributes)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeDtdTestCase)])
    suite.addTests(
        [doctest.DocFileSuite('../../../doc/validation.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
