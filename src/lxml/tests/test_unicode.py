# -*- coding: utf-8 -*-
import unittest, doctest

from common_imports import StringIO, etree, SillyFileLike, HelperTestCase

ascii_uni = u'a'

klingon = u"\uF8D2" # not valid for XML names

invalid_tag = "test" + klingon

uni = u'Ã\u0680\u3120' # some non-ASCII characters

uxml = u"<test><title>test Ã¡\u3120</title><h1>page Ã¡\u3120 title</h1></test>"

class UnicodeTestCase(HelperTestCase):
    def test_unicode_xml(self):
        tree = etree.XML(u'<p>%s</p>' % uni)
        self.assertEquals(uni, tree.text)

    def test_unicode_xml_broken(self):
        uxml = u'<?xml version="1.0" encoding="UTF-8"?>' + \
               u'<p>%s</p>' % uni
        self.assertRaises(ValueError, etree.XML, uxml)

    def test_unicode_tag(self):
        el = etree.Element(uni)
        self.assertEquals(uni, el.tag)

    def test_unicode_tag_invalid(self):
        # sadly, Klingon is not well-formed
        self.assertRaises(ValueError, etree.Element, invalid_tag)

    def test_unicode_nstag(self):
        tag = u"{%s}%s" % (uni, uni)
        el = etree.Element(tag)
        self.assertEquals(tag, el.tag)

    def test_unicode_nstag_invalid(self):
        # sadly, Klingon is not well-formed
        tag = u"{%s}%s" % (uni, invalid_tag)
        self.assertRaises(ValueError, etree.Element, tag)

    def test_unicode_qname(self):
        qname = etree.QName(uni, uni)
        tag = u"{%s}%s" % (uni, uni)
        self.assertEquals(qname.text, tag)
        self.assertEquals(unicode(qname), tag)

    def test_unicode_qname_invalid(self):
        self.assertRaises(ValueError, etree.QName, invalid_tag)

    def test_unicode_attr(self):
        el = etree.Element('foo', {'bar': uni})
        self.assertEquals(uni, el.attrib['bar'])

    def test_unicode_comment(self):
        el = etree.Comment(uni)
        self.assertEquals(uni, el.text)

    def test_unicode_parse_stringio(self):
        el = etree.parse(StringIO(u'<p>%s</p>' % uni)).getroot()
        self.assertEquals(uni, el.text)

##     def test_parse_fileobject_unicode(self):
##         # parse unicode from unamed file object (not support by ElementTree)
##         f = SillyFileLike(uxml)
##         root = etree.parse(f).getroot()
##         self.assertEquals(unicode(etree.tostring(root, 'UTF-8'), 'UTF-8'),
##                           uxml)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(UnicodeTestCase)])
    return suite
