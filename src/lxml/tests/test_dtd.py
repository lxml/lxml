# -*- coding: utf-8 -*-

"""
Test cases related to DTD parsing and validation
"""

import unittest, sys, os.path

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

from common_imports import etree, StringIO, BytesIO, _bytes, doctest
from common_imports import HelperTestCase, fileInTestDir, make_doctest

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
        root = etree.XML(_bytes("<b/>"))
        dtd = etree.DTD(BytesIO("<!ELEMENT b EMPTY>"))
        self.assert_(dtd.validate(root))

    def test_dtd_parse_invalid(self):
        fromstring = etree.fromstring
        parser = etree.XMLParser(dtd_validation=True)
        xml = _bytes('<!DOCTYPE b SYSTEM "%s"><b><a/></b>' % fileInTestDir("test.dtd"))
        self.assertRaises(etree.XMLSyntaxError,
                          fromstring, xml, parser=parser)

    def test_dtd_parse_file_not_found(self):
        fromstring = etree.fromstring
        dtd_filename = fileInTestDir("__nosuch.dtd")
        parser = etree.XMLParser(dtd_validation=True)
        xml = _bytes('<!DOCTYPE b SYSTEM "%s"><b><a/></b>' % dtd_filename)
        self.assertRaises(etree.XMLSyntaxError,
                          fromstring, xml, parser=parser)
        errors = None
        try:
            fromstring(xml, parser=parser)
        except etree.XMLSyntaxError:
            e = sys.exc_info()[1]
            errors = [ entry.message for entry in e.error_log
                       if dtd_filename in entry.message ]
        self.assert_(errors)

    def test_dtd_parse_valid(self):
        parser = etree.XMLParser(dtd_validation=True)
        xml = '<!DOCTYPE a SYSTEM "%s"><a><b/></a>' % fileInTestDir("test.dtd")
        root = etree.fromstring(xml, parser=parser)

    def test_dtd_parse_valid_relative(self):
        parser = etree.XMLParser(dtd_validation=True)
        xml = '<!DOCTYPE a SYSTEM "test.dtd"><a><b/></a>'
        root = etree.fromstring(xml, parser=parser,
                                base_url=fileInTestDir("test.xml"))

    def test_dtd_invalid(self):
        root = etree.XML("<b><a/></b>")
        dtd = etree.DTD(BytesIO("<!ELEMENT b EMPTY>"))
        self.assertRaises(etree.DocumentInvalid, dtd.assertValid, root)

    def test_dtd_assertValid(self):
        root = etree.XML("<b><a/></b>")
        dtd = etree.DTD(BytesIO("<!ELEMENT b (a)><!ELEMENT a EMPTY>"))
        dtd.assertValid(root)

    def test_dtd_internal(self):
        root = etree.XML(_bytes('''
        <!DOCTYPE b SYSTEM "none" [
        <!ELEMENT b (a)>
        <!ELEMENT a EMPTY>
        ]>
        <b><a/></b>
        '''))
        dtd = etree.ElementTree(root).docinfo.internalDTD
        self.assert_(dtd)
        dtd.assertValid(root)

    def test_dtd_internal_invalid(self):
        root = etree.XML(_bytes('''
        <!DOCTYPE b SYSTEM "none" [
        <!ELEMENT b (a)>
        <!ELEMENT a (c)>
        <!ELEMENT c EMPTY>
        ]>
        <b><a/></b>
        '''))
        dtd = etree.ElementTree(root).docinfo.internalDTD
        self.assert_(dtd)
        self.assertFalse(dtd.validate(root))

    def test_dtd_broken(self):
        self.assertRaises(etree.DTDParseError, etree.DTD,
                          BytesIO("<!ELEMENT b HONKEY>"))

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
        [make_doctest('../../../doc/validation.txt')])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
