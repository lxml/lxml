# -*- coding: utf-8 -*-
from __future__ import absolute_import

import unittest
import sys

from .common_imports import StringIO, etree, HelperTestCase, _str, _bytes, _chr, needs_libxml

try:
    unicode
except NameError:
    unicode = str

ascii_uni = _bytes('a').decode('utf8')

klingon = _bytes("\\uF8D2").decode("unicode_escape") # not valid for XML names

invalid_tag = _bytes("test").decode('utf8') + klingon

uni = _bytes('\\xc3\\u0680\\u3120').decode("unicode_escape") # some non-ASCII characters

uxml = _bytes("<test><title>test \\xc3\\xa1\\u3120</title><h1>page \\xc3\\xa1\\u3120 title</h1></test>"
              ).decode("unicode_escape")


class UnicodeTestCase(HelperTestCase):
    def test__str(self):
        # test the testing framework, namely _str from common_imports
        self.assertEqual(_str('\x10'), _str('\u0010'))
        self.assertEqual(_str('\x10'), _str('\U00000010'))
        self.assertEqual(_str('\u1234'), _str('\U00001234'))

    def test_unicode_xml(self):
        tree = etree.XML('<p>%s</p>' % uni)
        self.assertEqual(uni, tree.text)

    @needs_libxml(2, 9, 5)  # not sure, at least 2.9.4 fails
    def test_wide_unicode_xml(self):
        if sys.maxunicode < 1114111:
            return  # skip test
        tree = etree.XML(_bytes('<p>\\U00026007</p>').decode('unicode_escape'))
        self.assertEqual(1, len(tree.text))
        self.assertEqual(_bytes('\\U00026007').decode('unicode_escape'),
                         tree.text)

    def test_unicode_xml_broken(self):
        uxml = ('<?xml version="1.0" encoding="UTF-8"?>' +
                '<p>%s</p>' % uni)
        self.assertRaises(ValueError, etree.XML, uxml)

    def test_unicode_tag(self):
        el = etree.Element(uni)
        self.assertEqual(uni, el.tag)

    def test_unicode_tag_invalid(self):
        # sadly, Klingon is not well-formed
        self.assertRaises(ValueError, etree.Element, invalid_tag)

    def test_unicode_nstag(self):
        tag = "{http://abc/}%s" % uni
        el = etree.Element(tag)
        self.assertEqual(tag, el.tag)

    def test_unicode_ns_invalid(self):
        # namespace URIs must conform to RFC 3986
        tag = "{http://%s/}abc" % uni
        self.assertRaises(ValueError, etree.Element, tag)

    def test_unicode_nstag_invalid(self):
        # sadly, Klingon is not well-formed
        tag = "{http://abc/}%s" % invalid_tag
        self.assertRaises(ValueError, etree.Element, tag)

    def test_unicode_qname(self):
        qname = etree.QName(uni, uni)
        tag = "{%s}%s" % (uni, uni)
        self.assertEqual(qname.text, tag)
        self.assertEqual(unicode(qname), tag)

    def test_unicode_qname_invalid(self):
        self.assertRaises(ValueError, etree.QName, invalid_tag)

    def test_unicode_attr(self):
        el = etree.Element('foo', {'bar': uni})
        self.assertEqual(uni, el.attrib['bar'])

    def test_unicode_comment(self):
        el = etree.Comment(uni)
        self.assertEqual(uni, el.text)

    def test_unicode_repr1(self):
        x = etree.Element(_str('å'))
        # must not raise UnicodeEncodeError
        repr(x)

    def test_unicode_repr2(self):
        x = etree.Comment(_str('ö'))
        repr(x)

    def test_unicode_repr3(self):
        x = etree.ProcessingInstruction(_str('Å'), _str('\u0131'))
        repr(x)

    def test_unicode_repr4(self):
        x = etree.Entity(_str('ä'))
        repr(x)

    def test_unicode_text(self):
        e = etree.Element('e')

        def settext(text):
            e.text = text

        self.assertRaises(ValueError, settext, _str('ab\ufffe'))
        self.assertRaises(ValueError, settext, _str('ö\ffff'))
        self.assertRaises(ValueError, settext, _str('\u0123\ud800'))
        self.assertRaises(ValueError, settext, _str('x\ud8ff'))
        self.assertRaises(ValueError, settext, _str('\U00010000\udfff'))
        self.assertRaises(ValueError, settext, _str('abd\x00def'))
        # should not Raise
        settext(_str('\ud7ff\ue000\U00010000\U0010FFFFäöas'))

        for char_val in range(0xD800, 0xDFFF+1):
            self.assertRaises(ValueError, settext, 'abc' + _chr(char_val))
            self.assertRaises(ValueError, settext, _chr(char_val))
            self.assertRaises(ValueError, settext, _chr(char_val) + 'abc')

        self.assertRaises(ValueError, settext, _bytes('\xe4'))
        self.assertRaises(ValueError, settext, _bytes('\x80'))
        self.assertRaises(ValueError, settext, _bytes('\xff'))
        self.assertRaises(ValueError, settext, _bytes('\x08'))
        self.assertRaises(ValueError, settext, _bytes('\x19'))
        self.assertRaises(ValueError, settext, _bytes('\x20\x00'))
        # should not Raise
        settext(_bytes('\x09\x0A\x0D\x20\x60\x7f'))

    def test_uniname(self):
        Element = etree.Element
        def el(name):
            return Element(name)

        self.assertRaises(ValueError, el, ':')
        self.assertRaises(ValueError, el, '0a')
        self.assertRaises(ValueError, el, _str('\u203f'))
        # should not Raise
        el(_str('\u0132'))



    def test_unicode_parse_stringio(self):
        el = etree.parse(StringIO('<p>%s</p>' % uni)).getroot()
        self.assertEqual(uni, el.text)

##     def test_parse_fileobject_unicode(self):
##         # parse unicode from unnamed file object (not supported by ElementTree)
##         f = SillyFileLike(uxml)
##         root = etree.parse(f).getroot()
##         self.assertEqual(unicode(etree.tostring(root, 'UTF-8'), 'UTF-8'),
##                           uxml)


class EncodingsTestCase(HelperTestCase):
    def test_illegal_utf8(self):
        data = _bytes('<test>\x80\x80\x80</test>', encoding='iso8859-1')
        self.assertRaises(etree.XMLSyntaxError, etree.fromstring, data)

    def test_illegal_utf8_recover(self):
        data = _bytes('<test>\x80\x80\x80</test>', encoding='iso8859-1')
        parser = etree.XMLParser(recover=True)
        self.assertRaises(etree.XMLSyntaxError, etree.fromstring, data, parser)

    def _test_encoding(self, encoding, xml_encoding_name=None):
        foo = """<?xml version='1.0' encoding='%s'?>\n<tag attrib='123'></tag>""" % (
            xml_encoding_name or encoding)
        root = etree.fromstring(foo.encode(encoding))
        self.assertEqual('tag', root.tag)

        doc_encoding = root.getroottree().docinfo.encoding
        self.assertTrue(
            doc_encoding.lower().rstrip('lbe'),
            (xml_encoding_name or encoding).lower().rstrip('lbe'))

    def test_utf8_fromstring(self):
        self._test_encoding('utf-8')

    def test_utf8sig_fromstring(self):
        self._test_encoding('utf_8_sig', 'utf-8')

    def test_utf16_fromstring(self):
        self._test_encoding('utf-16')

    def test_utf16LE_fromstring(self):
        self._test_encoding('utf-16le', 'utf-16')

    def test_utf16BE_fromstring(self):
        self._test_encoding('utf-16be', 'utf-16')

    def test_utf32_fromstring(self):
        self._test_encoding('utf-32', 'utf-32')

    def test_utf32LE_fromstring(self):
        self._test_encoding('utf-32le', 'utf-32')

    def test_utf32BE_fromstring(self):
        self._test_encoding('utf-32be', 'utf-32')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(UnicodeTestCase)])
    suite.addTests([unittest.makeSuite(EncodingsTestCase)])
    return suite
