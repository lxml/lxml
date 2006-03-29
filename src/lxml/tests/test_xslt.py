# -*- coding: UTF-8 -*-

"""
Test cases related to XSLT processing
"""

import unittest, doctest

from common_imports import etree, HelperTestCase, fileInTestDir

class ETreeXSLTTestCase(HelperTestCase):
    """XPath tests etree"""
        
    def test_xslt(self):
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="*" />
  <xsl:template match="/">
    <foo><xsl:value-of select="/a/b/text()" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = st.apply(tree)
        self.assertEquals('''\
<?xml version="1.0"?>
<foo>B</foo>
''',
                          st.tostring(res))
    def test_xslt_input(self):
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="*" />
  <xsl:template match="/">
    <foo><xsl:value-of select="/a/b/text()" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        st = etree.XSLT(style.getroot())
        self.assertRaises(TypeError, etree.XSLT, None)

    def test_xslt_input_partial_doc(self):
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        style = self.parse('''\
<otherroot>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="*" />
  <xsl:template match="/">
    <foo><xsl:value-of select="/a/b/text()" /></foo>
  </xsl:template>
</xsl:stylesheet>
</otherroot>''')

        self.assertRaises(etree.XSLTParseError, etree.XSLT, style)
        root_node = style.getroot()
        self.assertRaises(etree.XSLTParseError, etree.XSLT, root_node)
        st = etree.XSLT(root_node[0])

    def test_xslt_broken(self):
        tree = self.parse('<a/>')
        style = self.parse('''\
<xslt:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:foo />
</xslt:stylesheet>''')
        self.assertRaises(etree.XSLTParseError,
                          etree.XSLT, style)

    def test_xslt_parameters(self):
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="*" />
  <xsl:template match="/">
    <foo><xsl:value-of select="$bar" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = st.apply(tree, bar="'Bar'")
        self.assertEquals('''\
<?xml version="1.0"?>
<foo>Bar</foo>
''',
                          st.tostring(res))
        # apply without needed parameter will lead to XSLTApplyError
        self.assertRaises(etree.XSLTApplyError,
                          st.apply, tree)

    def test_xslt_multiple_parameters(self):
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="*" />
  <xsl:template match="/">
    <foo><xsl:value-of select="$bar" /></foo>
    <foo><xsl:value-of select="$baz" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = st.apply(tree, bar="'Bar'", baz="'Baz'")
        self.assertEquals('''\
<?xml version="1.0"?>
<foo>Bar</foo><foo>Baz</foo>
''',
                          st.tostring(res))
        
    def test_xslt_parameter_xpath(self):
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="*" />
  <xsl:template match="/">
    <foo><xsl:value-of select="$bar" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = st.apply(tree, bar="/a/b/text()")
        self.assertEquals('''\
<?xml version="1.0"?>
<foo>B</foo>
''',
                          st.tostring(res))

        
    def test_xslt_default_parameters(self):
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:param name="bar" select="'Default'" />
  <xsl:template match="*" />
  <xsl:template match="/">
    <foo><xsl:value-of select="$bar" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = st.apply(tree, bar="'Bar'")
        self.assertEquals('''\
<?xml version="1.0"?>
<foo>Bar</foo>
''',
                          st.tostring(res))
        res = st.apply(tree)
        self.assertEquals('''\
<?xml version="1.0"?>
<foo>Default</foo>
''',
                          st.tostring(res))
        
    def test_xslt_html_output(self):
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html"/>
  <xsl:strip-space elements="*"/>
  <xsl:template match="/">
    <html><body><xsl:value-of select="/a/b/text()" /></body></html>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = st(tree)
        self.assertEquals('''<html><body>B</body></html>''',
                          str(res).strip())

    def test_xslt_multiple_files(self):
        tree = etree.parse(fileInTestDir('test1.xslt'))
        st = etree.XSLT(tree)

    def test_xslt_multiple_transforms(self):
        xml = '<a/>'
        xslt = '''\
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
    <xsl:template match="/">
        <response>Some text</response>
    </xsl:template>
</xsl:stylesheet>
'''
        source = self.parse(xml)
        styledoc = self.parse(xslt)
        style = etree.XSLT(styledoc)
        result = style.apply(source)

        etree.tostring(result.getroot())
        
        source = self.parse(xml)
        styledoc = self.parse(xslt)
        style = etree.XSLT(styledoc)
        result = style.apply(source)
        
        etree.tostring(result.getroot())

    def test_xslt_repeat_transform(self):
        xml = '<a/>'
        xslt = '''\
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
    <xsl:template match="/">
        <response>Some text</response>
    </xsl:template>
</xsl:stylesheet>
'''
        source = self.parse(xml)
        styledoc = self.parse(xslt)
        transform = etree.XSLT(styledoc)
        result = transform.apply(source)
        result = transform.apply(source)
        etree.tostring(result.getroot())
        result = transform.apply(source)
        etree.tostring(result.getroot())

        result = transform(source)
        result = transform(source)
        str(result)
        result = transform(source)
        str(result)

    def test_xslt_empty(self):
        # could segfault if result contains "empty document"
        xml = '<blah/>'
        xslt = '''
        <xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
          <xsl:template match="/" />
        </xsl:stylesheet>
        '''

        source = self.parse(xml)
        styledoc = self.parse(xslt)
        style = etree.XSLT(styledoc)
        result = style.apply(source)
        self.assertEqual('', style.tostring(result))

    def test_xslt_shortcut(self):
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="*" />
  <xsl:template match="/">
    <doc>
    <foo><xsl:value-of select="$bar" /></foo>
    <foo><xsl:value-of select="$baz" /></foo>
    </doc>
  </xsl:template>
</xsl:stylesheet>''')

        result = tree.xslt(style, bar="'Bar'", baz="'Baz'")
        self.assertEquals(
            '<doc><foo>Bar</foo><foo>Baz</foo></doc>',
            etree.tostring(result.getroot()))
        
    def test_multiple_elementrees(self):
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="a"><A><xsl:apply-templates/></A></xsl:template>
  <xsl:template match="b"><B><xsl:apply-templates/></B></xsl:template>
  <xsl:template match="c"><C><xsl:apply-templates/></C></xsl:template>
</xsl:stylesheet>''')

        self.assertEquals(self._rootstring(tree),
                          '<a><b>B</b><c>C</c></a>')
        result = tree.xslt(style)
        self.assertEquals(self._rootstring(tree),
                          '<a><b>B</b><c>C</c></a>')
        self.assertEquals(self._rootstring(result),
                          '<A><B>B</B><C>C</C></A>')

        b_tree = etree.ElementTree(tree.getroot()[0])
        self.assertEquals(self._rootstring(b_tree),
                          '<b>B</b>')
        result = b_tree.xslt(style)
        self.assertEquals(self._rootstring(tree),
                          '<a><b>B</b><c>C</c></a>')
        self.assertEquals(self._rootstring(result),
                          '<B>B</B>')

        c_tree = etree.ElementTree(tree.getroot()[1])
        self.assertEquals(self._rootstring(c_tree),
                          '<c>C</c>')
        result = c_tree.xslt(style)
        self.assertEquals(self._rootstring(tree),
                          '<a><b>B</b><c>C</c></a>')
        self.assertEquals(self._rootstring(result),
                          '<C>C</C>')

    def test_extensions1(self):
        tree = self.parse('<a><b>B</b></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    exclude-result-prefixes="myns">
  <xsl:template match="a"><A><xsl:value-of select="myns:mytext(b)"/></A></xsl:template>
</xsl:stylesheet>''')

        def mytext(ctxt, values):
            return 'X' * len(values)

        result = tree.xslt(style, {'testns' : {'mytext' : mytext}})
        self.assertEquals(self._rootstring(result),
                          '<A>X</A>')

    def test_extensions2(self):
        tree = self.parse('<a><b>B</b></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    exclude-result-prefixes="myns">
  <xsl:template match="a"><A><xsl:value-of select="myns:mytext(b)"/></A></xsl:template>
</xsl:stylesheet>''')

        def mytext(ctxt, values):
            return 'X' * len(values)

        namespace = etree.FunctionNamespace('testns')
        namespace['mytext'] = mytext

        result = tree.xslt(style)
        self.assertEquals(self._rootstring(result),
                          '<A>X</A>')

    def test_xslt_document_parse(self):
        # make sure document('') works from loaded files
        xslt = etree.XSLT(etree.parse(fileInTestDir("test-document.xslt")))
        result = xslt(etree.XML('<a/>'))
        root = result.getroot()
        self.assertEquals(root.tag,
                          'test')
        self.assertEquals(root[0].tag,
                          '{http://www.w3.org/1999/XSL/Transform}stylesheet')

    def test_xslt_document_elementtree(self):
        # make sure document('') works from loaded files
        xslt = etree.XSLT(etree.ElementTree(file=fileInTestDir("test-document.xslt")))
        result = xslt(etree.XML('<a/>'))
        root = result.getroot()
        self.assertEquals(root.tag,
                          'test')
        self.assertEquals(root[0].tag,
                          '{http://www.w3.org/1999/XSL/Transform}stylesheet')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeXSLTTestCase)])
    suite.addTests(
        [doctest.DocFileSuite('../../../doc/extensions.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
