# -*- coding: utf-8 -*-

"""
Test cases related to DTD parsing and validation
"""

import unittest, sys, os.path

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir)  # needed for Py3

from common_imports import etree, BytesIO, _bytes
from common_imports import HelperTestCase, make_doctest, skipIf
from common_imports import fileInTestDir, fileUrlInTestDir


class ETreeDtdTestCase(HelperTestCase):
    def test_dtd(self):
        pass

    def test_dtd_file(self):
        parse = etree.parse
        tree = parse(fileInTestDir("test.xml"))
        root = tree.getroot()

        dtd = etree.DTD(fileInTestDir("test.dtd"))
        self.assertTrue(dtd.validate(root))

    def test_dtd_stringio(self):
        root = etree.XML(_bytes("<b/>"))
        dtd = etree.DTD(BytesIO("<!ELEMENT b EMPTY>"))
        self.assertTrue(dtd.validate(root))

    def test_dtd_parse_invalid(self):
        fromstring = etree.fromstring
        parser = etree.XMLParser(dtd_validation=True)
        xml = _bytes('<!DOCTYPE b SYSTEM "%s"><b><a/></b>' %
                     fileInTestDir("test.dtd"))
        self.assertRaises(etree.XMLSyntaxError,
                          fromstring, xml, parser=parser)

    def test_dtd_parse_file_not_found(self):
        fromstring = etree.fromstring
        dtd_filename = fileUrlInTestDir("__nosuch.dtd")
        parser = etree.XMLParser(dtd_validation=True)
        xml = _bytes('<!DOCTYPE b SYSTEM "%s"><b><a/></b>' % dtd_filename)
        self.assertRaises(etree.XMLSyntaxError,
                          fromstring, xml, parser=parser)
        errors = None
        try:
            fromstring(xml, parser=parser)
        except etree.XMLSyntaxError:
            e = sys.exc_info()[1]
            self.assertTrue(e.error_log)
            self.assertTrue(parser.error_log)
            errors = [entry.message for entry in e.error_log
                      if dtd_filename in entry.message]
        self.assertTrue(errors)

    def test_dtd_parse_valid(self):
        parser = etree.XMLParser(dtd_validation=True)
        xml = ('<!DOCTYPE a SYSTEM "%s"><a><b/></a>' %
               fileUrlInTestDir("test.dtd"))
        root = etree.fromstring(xml, parser=parser)

    def test_dtd_parse_valid_file_url(self):
        parser = etree.XMLParser(dtd_validation=True)
        xml = ('<!DOCTYPE a SYSTEM "%s"><a><b/></a>' %
               fileUrlInTestDir("test.dtd"))
        root = etree.fromstring(xml, parser=parser)

    def test_dtd_parse_valid_relative(self):
        parser = etree.XMLParser(dtd_validation=True)
        xml = '<!DOCTYPE a SYSTEM "test.dtd"><a><b/></a>'
        root = etree.fromstring(
            xml, parser=parser, base_url=fileUrlInTestDir("test.xml"))

    def test_dtd_parse_valid_relative_file_url(self):
        parser = etree.XMLParser(dtd_validation=True)
        xml = '<!DOCTYPE a SYSTEM "test.dtd"><a><b/></a>'
        root = etree.fromstring(
            xml, parser=parser, base_url=fileUrlInTestDir("test.xml"))

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
        self.assertTrue(dtd)
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
        self.assertTrue(dtd)
        self.assertFalse(dtd.validate(root))

    def test_dtd_invalid_duplicate_id(self):
        root = etree.XML(_bytes('''
        <a><b id="id1"/><b id="id2"/><b id="id1"/></a>
        '''))
        dtd = etree.DTD(BytesIO(_bytes("""
        <!ELEMENT a (b*)>
        <!ATTLIST b
            id ID #REQUIRED
        >
        <!ELEMENT b EMPTY>
        """)))
        self.assertFalse(dtd.validate(root))
        self.assertTrue(dtd.error_log)
        self.assertTrue([error for error in dtd.error_log
                         if 'id1' in error.message])

    def test_dtd_api_internal(self):
        root = etree.XML(_bytes('''
        <!DOCTYPE b SYSTEM "none" [
        <!ATTLIST a
          attr1 (x | y | z) "z"
          attr2 CDATA #FIXED "X"
        >
        <!ELEMENT b (a)>
        <!ELEMENT a EMPTY>
        ]>
        <b><a/></b>
        '''))
        dtd = etree.ElementTree(root).docinfo.internalDTD
        self.assertTrue(dtd)
        dtd.assertValid(root)

        seen = []
        for el in dtd.iterelements():
            if el.name == 'a':
                self.assertEqual(2, len(el.attributes()))
                for attr in el.iterattributes():
                    if attr.name == 'attr1':
                        self.assertEqual('enumeration', attr.type)
                        self.assertEqual('none', attr.default)
                        self.assertEqual('z', attr.default_value)
                        values = attr.values()
                        values.sort()
                        self.assertEqual(['x', 'y', 'z'], values)
                    else:
                        self.assertEqual('attr2', attr.name)
                        self.assertEqual('cdata', attr.type)
                        self.assertEqual('fixed', attr.default)
                        self.assertEqual('X', attr.default_value)
            else:
                self.assertEqual('b', el.name)
                self.assertEqual(0, len(el.attributes()))
            seen.append(el.name)
        seen.sort()
        self.assertEqual(['a', 'b'], seen)
        self.assertEqual(2, len(dtd.elements()))

    def test_internal_dtds(self):
        for el_count in range(2, 5):
            for attr_count in range(4):
                root = etree.XML(_bytes('''
                <!DOCTYPE el0 SYSTEM "none" [
                ''' + ''.join(['''
                <!ATTLIST el%d
                  attr%d (x | y | z) "z"
                >
                ''' % (e, a) for a in range(attr_count) for e in range(el_count)
                ]) + ''.join(['''
                <!ELEMENT el%d EMPTY>
                ''' % e for e in range(1, el_count)
                ]) + '''
                ''' + '<!ELEMENT el0 (%s)>' % '|'.join([
                    'el%d' % e for e in range(1, el_count)]) + '''
                ]>
                <el0><el1 %s /></el0>
                ''' % ' '.join(['attr%d="x"' % a for a in range(attr_count)])))
                dtd = etree.ElementTree(root).docinfo.internalDTD
                self.assertTrue(dtd)
                dtd.assertValid(root)

                e = -1
                for e, el in enumerate(dtd.iterelements()):
                    self.assertEqual(attr_count, len(el.attributes()))
                    a = -1
                    for a, attr in enumerate(el.iterattributes()):
                        self.assertEqual('enumeration', attr.type)
                        self.assertEqual('none', attr.default)
                        self.assertEqual('z', attr.default_value)
                        values = sorted(attr.values())
                        self.assertEqual(['x', 'y', 'z'], values)
                    self.assertEqual(attr_count - 1, a)
                self.assertEqual(el_count - 1, e)
                self.assertEqual(el_count, len(dtd.elements()))

    def test_dtd_broken(self):
        self.assertRaises(etree.DTDParseError, etree.DTD,
                          BytesIO("<!ELEMENT b HONKEY>"))

    def test_parse_file_dtd(self):
        parser = etree.XMLParser(attribute_defaults=True)

        tree = etree.parse(fileInTestDir('test.xml'), parser)
        root = tree.getroot()

        self.assertEqual(
            "valueA",
            root.get("default"))
        self.assertEqual(
            "valueB",
            root[0].get("default"))

    @skipIf(etree.LIBXML_VERSION == (2, 9, 0),
            "DTD loading is broken for incremental parsing in libxml2 2.9.0")
    def test_iterparse_file_dtd_start(self):
        iterparse = etree.iterparse
        iterator = iterparse(fileInTestDir("test.xml"), events=('start',),
                             attribute_defaults=True)
        attributes = [ element.get("default")
                       for event, element in iterator ]
        self.assertEqual(
            ["valueA", "valueB"],
            attributes)

    @skipIf(etree.LIBXML_VERSION == (2, 9, 0),
            "DTD loading is broken for incremental parsing in libxml2 2.9.0")
    def test_iterparse_file_dtd_end(self):
        iterparse = etree.iterparse
        iterator = iterparse(fileInTestDir("test.xml"), events=('end',),
                             attribute_defaults=True)
        attributes = [ element.get("default")
                       for event, element in iterator ]
        self.assertEqual(
            ["valueB", "valueA"],
            attributes)

    def test_dtd_attrs(self):
        dtd = etree.DTD(fileUrlInTestDir("test.dtd"))

        # Test DTD.system_url attribute
        self.assertTrue(dtd.system_url.endswith("test.dtd"))

        # Test elements and their attributes
        a = dtd.elements()[0]
        self.assertEqual(a.name, "a")
        self.assertEqual(a.type, "element")
        self.assertEqual(a.content.name, "b")
        self.assertEqual(a.content.type, "element")
        self.assertEqual(a.content.occur, "once")

        aattr = a.attributes()[0]
        self.assertEqual(aattr.name, "default")
        self.assertEqual(aattr.type, "enumeration")
        self.assertEqual(aattr.values(), ["valueA", "valueB"])
        self.assertEqual(aattr.default_value, "valueA")

        b = dtd.elements()[1]
        self.assertEqual(b.name, "b")
        self.assertEqual(b.type, "empty")
        self.assertEqual(b.content, None)

        # Test entities and their attributes
        c = dtd.entities()[0]
        self.assertEqual(c.name, "c")
        self.assertEqual(c.orig, "&#42;")
        self.assertEqual(c.content, "*")

        # Test DTD.name attribute
        root = etree.XML(_bytes('''
        <!DOCTYPE a SYSTEM "none" [
        <!ELEMENT a EMPTY>
        ]>
        <a/>
        '''))
        dtd = etree.ElementTree(root).docinfo.internalDTD
        self.assertEqual(dtd.name, "a")

        # Test DTD.name and DTD.systemID attributes
        parser = etree.XMLParser(dtd_validation=True)
        xml = '<!DOCTYPE a SYSTEM "test.dtd"><a><b/></a>'
        root = etree.fromstring(xml, parser=parser,
                                base_url=fileUrlInTestDir("test.xml"))

        dtd = root.getroottree().docinfo.internalDTD
        self.assertEqual(dtd.name, "a")
        self.assertEqual(dtd.system_url, "test.dtd")

    def test_declaration_escape_quote_pid(self):
        # Standard allows quotes in systemliteral, but in that case
        # systemliteral must be escaped with hyphens, not quotes.
        # See http://www.w3.org/TR/REC-xml/#sec-prolog-dtd.
        root = etree.XML('''<!DOCTYPE a PUBLIC 'foo' '"'><a/>''')
        doc = root.getroottree()
        self.assertEqual(doc.docinfo.doctype,
                         u'''<!DOCTYPE a PUBLIC "foo" '"'>''')
        self.assertEqual(etree.tostring(doc),
                         '''<!DOCTYPE a PUBLIC "foo" '"'>\n<a/>''')

    def test_declaration_escape_quote_withoutpid(self):
        root = etree.XML('''<!DOCTYPE a SYSTEM '"'><a/>''')
        doc = root.getroottree()
        self.assertEqual(doc.docinfo.doctype, u'''<!DOCTYPE a SYSTEM '"'>''')
        self.assertEqual(etree.tostring(doc),
                         '''<!DOCTYPE a SYSTEM '"'>\n<a/>''')

    def test_declaration_escape_hyphen(self):
        root = etree.XML('''<!DOCTYPE a SYSTEM "'"><a/>''')
        doc = root.getroottree()
        self.assertEqual(doc.docinfo.doctype, u'''<!DOCTYPE a SYSTEM "'">''')
        self.assertEqual(etree.tostring(doc),
                         '''<!DOCTYPE a SYSTEM "'">\n<a/>''')

    def test_ietf_decl(self):
        html = u'<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">\n' \
            u'<html></html>'
        root = etree.HTML(html)
        doc = root.getroottree()
        self.assertEqual(doc.docinfo.doctype,
                         u'<!DOCTYPE html PUBLIC "-//IETF//DTD HTML//EN">')
        self.assertEqual(etree.tostring(doc, method='html'), html)

    def test_set_decl_public(self):
        doc = etree.Element('test').getroottree()
        doc.setdoctype('bar', 'baz')
        self.assertEqual(doc.docinfo.doctype,
                         u'<!DOCTYPE test PUBLIC "bar" "baz">')
        self.assertEqual(etree.tostring(doc),
                         u'<!DOCTYPE test PUBLIC "bar" "baz">\n<test/>')

    def test_set_decl_system(self):
        doc = etree.Element('test').getroottree()
        doc.setdoctype(None, 'baz')
        self.assertEqual(doc.docinfo.doctype,
                         u'<!DOCTYPE test SYSTEM "baz">')
        self.assertEqual(etree.tostring(doc),
                         u'<!DOCTYPE test SYSTEM "baz">\n<test/>')

    def test_invalid_decl_1(self):
        doc = etree.Element('test').getroottree()
        with self.assertRaises(ValueError):
            doc.setdoctype(u'\xe4', 'a')

    def test_invalid_decl_2(self):
        doc = etree.Element('test').getroottree()
        with self.assertRaises(ValueError):
            doc.setdoctype(u'a', '\'"')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeDtdTestCase)])
    suite.addTests(
        [make_doctest('../../../doc/validation.txt')])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
