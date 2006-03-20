# -*- coding: UTF-8 -*-

"""
Tests specific to the extended etree API

Tests that apply to the general ElementTree API should go into
test_elementtree
"""


import unittest, doctest

from StringIO import StringIO

from common_imports import etree, HelperTestCase, fileInTestDir, canonicalize

class ETreeOnlyTestCase(HelperTestCase):
    """Tests only for etree, not ElementTree"""
    etree = etree
    
    def test_parse_error(self):
        parse = self.etree.parse
        # from StringIO
        f = StringIO('<a><b></c></b></a>')
        self.assertRaises(SyntaxError, parse, f)
        f.close()

    def test_parse_error_logging(self):
        parse = self.etree.parse
        # from StringIO
        f = StringIO('<a><b></c></b></a>')
        self.etree.clearErrorLog()
        try:
            parse(f)
            logs = None
        except SyntaxError, e:
            logs = e.error_log
        f.close()
        self.assert_([ log for log in logs
                       if 'mismatch' in log.message ])
        self.assert_([ log for log in logs
                       if 'PARSER'   in log.domain_name])
        self.assert_([ log for log in logs
                       if 'TAG_NAME_MISMATCH' in log.type_name ])

    def test_parse_error_from_file(self):
        parse = self.etree.parse
        # from file
        f = open(fileInTestDir('test_broken.xml'), 'r')
        self.assertRaises(SyntaxError, parse, f)
        f.close()
        
    # TypeError in etree, AssertionError in ElementTree;
    def test_setitem_assert(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        
        self.assertRaises(TypeError,
                          a.__setitem__, 0, 'foo')
        
    # gives error in ElementTree
    def test_comment_empty(self):
        Element = self.etree.Element
        Comment = self.etree.Comment

        a = Element('a')
        a.append(Comment())
        self.assertEquals(
            '<a><!--  --></a>',
            self._writeElement(a))

    # ignores Comment in ElementTree
    def test_comment_no_proxy_yet(self):
        ElementTree = self.etree.ElementTree
        
        f = StringIO('<a><b></b><!-- hoi --><c></c></a>')
        doc = ElementTree(file=f)
        a = doc.getroot()
        self.assertEquals(
            ' hoi ',
            a[1].text)

    # test weird dictionary interaction leading to segfault previously
    def test_weird_dict_interaction(self):
        root = self.etree.Element('root')
        add = self.etree.ElementTree(file=StringIO('<foo>Foo</foo>'))
        root.append(self.etree.Element('baz'))

    # test passing 'None' to dump
    def test_dump_none(self):
        self.assertRaises(AssertionError, etree.dump, None)

    def test_prefix(self):
        ElementTree = self.etree.ElementTree
        
        f = StringIO('<a xmlns:foo="http://www.infrae.com/ns/1"><foo:b/></a>')
        doc = ElementTree(file=f)
        a = doc.getroot()
        self.assertEquals(
            None,
            a.prefix)
        self.assertEquals(
            'foo',
            a[0].prefix)

    def test_prefix_default_ns(self):
        ElementTree = self.etree.ElementTree
        
        f = StringIO('<a xmlns="http://www.infrae.com/ns/1"><b/></a>')
        doc = ElementTree(file=f)
        a = doc.getroot()
        self.assertEquals(
            None,
            a.prefix)
        self.assertEquals(
            None,
            a[0].prefix)

    def test_getparent(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        self.assertEquals(
            None,
            a.getparent())
        self.assertEquals(
            a,
            b.getparent())
        self.assertEquals(
            b.getparent(),
            c.getparent())
        self.assertEquals(
            b,
            d.getparent())

    def test_namespaces(self):
        etree = self.etree

        r = {'foo': 'http://ns.infrae.com/foo'}
        e = etree.Element('{http://ns.infrae.com/foo}bar', nsmap=r)
        self.assertEquals(
            'foo',
            e.prefix)
        self.assertEquals(
            '<foo:bar xmlns:foo="http://ns.infrae.com/foo"></foo:bar>',
            self._writeElement(e))
        
    def test_namespaces_default(self):
        etree = self.etree

        r = {None: 'http://ns.infrae.com/foo'}
        e = etree.Element('{http://ns.infrae.com/foo}bar', nsmap=r)
        self.assertEquals(
            None,
            e.prefix)
        self.assertEquals(
            '{http://ns.infrae.com/foo}bar',
            e.tag)
        self.assertEquals(
            '<bar xmlns="http://ns.infrae.com/foo"></bar>',
            self._writeElement(e))

    def test_namespaces_default_and_attr(self):
        etree = self.etree

        r = {None: 'http://ns.infrae.com/foo',
             'hoi': 'http://ns.infrae.com/hoi'}
        e = etree.Element('{http://ns.infrae.com/foo}bar', nsmap=r)
        e.set('{http://ns.infrae.com/hoi}test', 'value')
        self.assertEquals(
            '<bar xmlns="http://ns.infrae.com/foo" xmlns:hoi="http://ns.infrae.com/hoi" hoi:test="value"></bar>',
            self._writeElement(e))

    def test_namespaces_elementtree(self):
        etree = self.etree
        r = {None: 'http://ns.infrae.com/foo',
             'hoi': 'http://ns.infrae.com/hoi'} 
        e = etree.Element('{http://ns.infrae.com/foo}z', nsmap=r)
        tree = etree.ElementTree(element=e)
        etree.SubElement(e, '{http://ns.infrae.com/hoi}x')
        self.assertEquals(
            '<z xmlns="http://ns.infrae.com/foo" xmlns:hoi="http://ns.infrae.com/hoi"><hoi:x></hoi:x></z>',
            self._writeElement(e))

    def test_index(self):
        etree = self.etree
        e = etree.Element('foo')
        for i in range(10):
            etree.SubElement(e, 'a%s' % i)
        for i in range(10):
            self.assertEquals(
                i,
                e.index(e[i]))
        self.assertEquals(
            3, e.index(e[3], 3))
        self.assertRaises(
            ValueError, e.index, e[3], 4)
        self.assertRaises(
            ValueError, e.index, e[3], 0, 2)
        self.assertRaises(
            ValueError, e.index, e[8], 0, -3)
        self.assertRaises(
            ValueError, e.index, e[8], -5, -3)
        self.assertEquals(
            8, e.index(e[8], 0, -1))
        self.assertEquals(
            8, e.index(e[8], -12, -1))
        self.assertEquals(
            0, e.index(e[0], -12, -1))
        
    def _writeElement(self, element, encoding='us-ascii'):
        """Write out element for comparison.
        """
        ElementTree = self.etree.ElementTree
        f = StringIO()
        tree = ElementTree(element=element)
        tree.write(f, encoding)
        data = f.getvalue()
        return canonicalize(data)


class ETreeXIncludeTestCase(HelperTestCase):
    def test_xinclude(self):
        tree = etree.parse(fileInTestDir('test_xinclude.xml'))
        # process xincludes
        tree.xinclude()
        # check whether we find it replaced with included data
        self.assertEquals(
            'a',
            tree.getroot()[1].tag)
        
class ETreeC14NTestCase(HelperTestCase):
    def test_c14n(self):
        tree = self.parse('<a><b/></a>')
        f = StringIO()
        tree.write_c14n(f)
        s = f.getvalue()
        self.assertEquals('<a><b></b></a>',
                          s)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeOnlyTestCase)])
    suite.addTests([unittest.makeSuite(ETreeXIncludeTestCase)])
    suite.addTests([unittest.makeSuite(ETreeC14NTestCase)])
    suite.addTests(
        [doctest.DocFileSuite('../../../doc/api.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
