# -*- coding: utf-8 -*-

"""
Test cases related to XSLT processing
"""

import unittest, doctest

from common_imports import etree, StringIO, HelperTestCase, fileInTestDir

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

    def test_xslt_elementtree_error(self):
        self.assertRaises(ValueError, etree.XSLT, etree.ElementTree())

    def test_xslt_utf8(self):
        tree = self.parse(u'<a><b>\uF8D2</b><c>\uF8D2</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output encoding="UTF-8"/>
  <xsl:template match="/">
    <foo><xsl:value-of select="/a/b/text()" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = st.apply(tree)
        expected = u'''\
<?xml version="1.0" encoding="UTF-8"?>
<foo>\uF8D2</foo>
'''
        self.assertEquals(expected,
                          unicode(str(res), 'UTF-8'))

    def test_xslt_encoding(self):
        tree = self.parse(u'<a><b>\uF8D2</b><c>\uF8D2</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output encoding="UTF-16"/>
  <xsl:template match="/">
    <foo><xsl:value-of select="/a/b/text()" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = st.apply(tree)
        expected = u'''\
<?xml version="1.0" encoding="UTF-16"?>
<foo>\uF8D2</foo>
'''
        self.assertEquals(expected,
                          unicode(str(res), 'UTF-16'))

    def test_xslt_encoding_override(self):
        tree = self.parse(u'<a><b>\uF8D2</b><c>\uF8D2</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output encoding="UTF-8"/>
  <xsl:template match="/">
    <foo><xsl:value-of select="/a/b/text()" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = st.apply(tree)
        expected = u"""\
<?xml version='1.0' encoding='UTF-16'?>
<foo>\uF8D2</foo>"""

        f = StringIO()
        res.write(f, 'UTF-16')
        result = unicode(f.getvalue(), 'UTF-16')
        self.assertEquals(expected,
                          result)

    def test_xslt_unicode(self):
        tree = self.parse(u'<a><b>\uF8D2</b><c>\uF8D2</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output encoding="UTF-16"/>
  <xsl:template match="/">
    <foo><xsl:value-of select="/a/b/text()" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = st.apply(tree)
        expected = u'''\
<?xml version="1.0"?>
<foo>\uF8D2</foo>
'''
        self.assertEquals(expected,
                          unicode(res))

    def test_exslt(self):
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:math="http://exslt.org/math"
    xmlns:str="http://exslt.org/strings"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    exclude-result-prefixes="math str xsl">
  <xsl:template match="text()">
    <xsl:value-of select="str:align(string(.), '---', 'center')" />
  </xsl:template>
  <xsl:template match="*">
    <xsl:copy>
      <xsl:attribute name="pi">
        <xsl:value-of select="math:constant('PI', count(*)+2)"/>
      </xsl:attribute>
      <xsl:apply-templates/>
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = st(tree)
        self.assertEquals('''\
<?xml version="1.0"?>
<a pi="3.14"><b pi="3">-B-</b><c pi="3">-C-</c></a>
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
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:foo />
</xsl:stylesheet>''')
        self.assertRaises(etree.XSLTParseError,
                          etree.XSLT, style)

    def test_xslt_parameters(self):
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
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

    def test_xslt_parameter_fail(self):
        # apply() without needed parameter will lead to XSLTApplyError
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <foo><xsl:value-of select="$bar" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
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

    def test_xslt_include(self):
        tree = etree.parse(fileInTestDir('test1.xslt'))
        st = etree.XSLT(tree)

    def test_xslt_include_from_filelike(self):
        f = open(fileInTestDir('test1.xslt'), 'r')
        tree = etree.parse(f)
        f.close()
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
        str(result)

        result1 = transform(source)
        result2 = transform(source)
        self.assertEquals(str(result1), str(result2))
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
        self.assertEqual('', str(result))

    def test_xslt_message(self):
        xml = '<blah/>'
        xslt = '''
        <xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
          <xsl:template match="/">
            <xsl:message>TEST TEST TEST</xsl:message>
          </xsl:template>
        </xsl:stylesheet>
        '''

        source = self.parse(xml)
        styledoc = self.parse(xslt)
        style = etree.XSLT(styledoc)
        result = style.apply(source)
        self.assertEqual('', style.tostring(result))
        self.assertEqual('', str(result))
        self.assert_("TEST TEST TEST" in [entry.message
                                          for entry in style.error_log])

    def test_xslt_message_terminate(self):
        xml = '<blah/>'
        xslt = '''
        <xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
          <xsl:template match="/">
            <xsl:message terminate="yes">TEST TEST TEST</xsl:message>
          </xsl:template>
        </xsl:stylesheet>
        '''

        source = self.parse(xml)
        styledoc = self.parse(xslt)
        style = etree.XSLT(styledoc)
        result = style.apply(source)
        self.assertEqual('', style.tostring(result))
        self.assertEqual('', str(result))
        self.assert_("TEST TEST TEST" in [entry.message
                                          for entry in style.error_log])

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

        result = tree.xslt(style, {('testns', 'mytext') : mytext})
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

    def test_xslt_document_XML(self):
        # make sure document('') works from parsed strings
        xslt = etree.XSLT(etree.XML("""\
<xsl:stylesheet version="1.0"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <test>TEXT<xsl:copy-of select="document('')//test"/></test>
  </xsl:template>
</xsl:stylesheet>
"""))
        result = xslt(etree.XML('<a/>'))
        root = result.getroot()
        self.assertEquals(root.tag,
                          'test')
        self.assertEquals(root[0].tag,
                          'test')
        self.assertEquals(root[0].text,
                          'TEXT')
        self.assertEquals(root[0][0].tag,
                          '{http://www.w3.org/1999/XSL/Transform}copy-of')

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

    def test_xslt_document_error(self):
        # make sure document('') works from parsed strings
        xslt = etree.XSLT(etree.XML("""\
<xsl:stylesheet version="1.0"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <test>TEXT<xsl:copy-of select="document('uri:__junkfood__is__evil__')//test"/></test>
  </xsl:template>
</xsl:stylesheet>
"""))
        self.assertRaises(etree.XSLTApplyError, xslt, etree.XML('<a/>'))

    def test_xslt_move_result(self):
        root = etree.XML('''\
        <transform>
          <widget displayType="fieldset"/>
        </transform>''')

        xslt = etree.XSLT(etree.XML('''\
        <xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
          <xsl:output method="html" indent="no"/>
          <xsl:template match="/">
            <html>
              <xsl:apply-templates/>
            </html>
          </xsl:template>

          <xsl:template match="widget">
            <xsl:element name="{@displayType}"/>
          </xsl:template>

        </xsl:stylesheet>'''))

        result = xslt(root[0])
        root[:] = result.getroot()[:]
        del root # segfaulted before
        
    def test_xslt_pi(self):
        tree = self.parse('''\
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="%s"?>
<a>
  <b>B</b>
  <c>C</c>
</a>''' % fileInTestDir("test1.xslt"))

        style_root = tree.getroot().getprevious().parseXSL().getroot()
        self.assertEquals("{http://www.w3.org/1999/XSL/Transform}stylesheet",
                          style_root.tag)
        
    def test_xslt_pi_embedded_xmlid(self):
        # test xml:id dictionary lookup mechanism
        tree = self.parse('''\
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="#style"?>
<a>
  <b>B</b>
  <c>C</c>
  <xsl:stylesheet version="1.0" xml:id="style"
      xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:template match="*" />
    <xsl:template match="/">
      <foo><xsl:value-of select="/a/b/text()" /></foo>
    </xsl:template>
  </xsl:stylesheet>
</a>''')

        style_root = tree.getroot().getprevious().parseXSL().getroot()
        self.assertEquals("{http://www.w3.org/1999/XSL/Transform}stylesheet",
                          style_root.tag)

        st = etree.XSLT(style_root)
        res = st.apply(tree)
        self.assertEquals('''\
<?xml version="1.0"?>
<foo>B</foo>
''',
                          st.tostring(res))
        
    def test_xslt_pi_embedded_id(self):
        # test XPath lookup mechanism
        tree = self.parse('''\
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="#style"?>
<a>
  <b>B</b>
  <c>C</c>
</a>''')

        style = self.parse('''\
<xsl:stylesheet version="1.0" xml:id="style"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="*" />
  <xsl:template match="/">
    <foo><xsl:value-of select="/a/b/text()" /></foo>
  </xsl:template>
</xsl:stylesheet>
''')

        tree.getroot().append(style.getroot())

        style_root = tree.getroot().getprevious().parseXSL().getroot()
        self.assertEquals("{http://www.w3.org/1999/XSL/Transform}stylesheet",
                          style_root.tag)

        st = etree.XSLT(style_root)
        res = st.apply(tree)
        self.assertEquals('''\
<?xml version="1.0"?>
<foo>B</foo>
''',
                          st.tostring(res))

    def test_exslt_regexp_test(self):
        xslt = etree.XSLT(etree.XML("""\
<xsl:stylesheet version="1.0"
   xmlns:regexp="http://exslt.org/regular-expressions"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="*">
    <test><xsl:copy-of select="*[regexp:test(string(.), '8.')]"/></test>
  </xsl:template>
</xsl:stylesheet>
"""))
        result = xslt(etree.XML('<a><b>123</b><b>098</b><b>987</b></a>'))
        root = result.getroot()
        self.assertEquals(root.tag,
                          'test')
        self.assertEquals(len(root), 1)
        self.assertEquals(root[0].tag,
                          'b')
        self.assertEquals(root[0].text,
                          '987')

    def test_exslt_regexp_replace(self):
        xslt = etree.XSLT(etree.XML("""\
<xsl:stylesheet version="1.0"
   xmlns:regexp="http://exslt.org/regular-expressions"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="*">
    <test>
      <xsl:copy-of select="regexp:replace(string(.), 'd.', '',   'XX')"/>
      <xsl:text>-</xsl:text>
      <xsl:copy-of select="regexp:replace(string(.), 'd.', 'gi', 'XX')"/>
    </test>
  </xsl:template>
</xsl:stylesheet>
"""))
        result = xslt(etree.XML('<a>abdCdEeDed</a>'))
        root = result.getroot()
        self.assertEquals(root.tag,
                          'test')
        self.assertEquals(len(root), 0)
        self.assertEquals(root.text, 'abXXdEeDed-abXXXXeXXd')

    def test_exslt_regexp_match(self):
        xslt = etree.XSLT(etree.XML("""\
<xsl:stylesheet version="1.0"
   xmlns:regexp="http://exslt.org/regular-expressions"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="*">
    <test>
      <test1><xsl:copy-of  select="regexp:match(string(.), 'd.')"/></test1>
      <test2><xsl:copy-of  select="regexp:match(string(.), 'd.', 'g')"/></test2>
      <test2i><xsl:copy-of select="regexp:match(string(.), 'd.', 'gi')"/></test2i>
    </test>
  </xsl:template>
</xsl:stylesheet>
"""))
        result = xslt(etree.XML('<a>abdCdEeDed</a>'))
        root = result.getroot()
        self.assertEquals(root.tag,  'test')
        self.assertEquals(len(root), 3)

        self.assertEquals(len(root[0]), 1)
        self.assertEquals(root[0][0].tag, 'match')
        self.assertEquals(root[0][0].text, 'dC')

        self.assertEquals(len(root[1]), 2)
        self.assertEquals(root[1][0].tag, 'match')
        self.assertEquals(root[1][0].text, 'dC')
        self.assertEquals(root[1][1].tag, 'match')
        self.assertEquals(root[1][1].text, 'dE')

        self.assertEquals(len(root[2]), 3)
        self.assertEquals(root[2][0].tag, 'match')
        self.assertEquals(root[2][0].text, 'dC')
        self.assertEquals(root[2][1].tag, 'match')
        self.assertEquals(root[2][1].text, 'dE')
        self.assertEquals(root[2][2].tag, 'match')
        self.assertEquals(root[2][2].text, 'De')

    def test_exslt_regexp_match_groups(self):
        xslt = etree.XSLT(etree.XML("""\
<xsl:stylesheet version="1.0"
   xmlns:regexp="http://exslt.org/regular-expressions"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <test>
      <xsl:for-each select="regexp:match(
            '123abc567', '([0-9]+)([a-z]+)([0-9]+)' )">
        <test1><xsl:value-of select="."/></test1>
      </xsl:for-each>
    </test>
  </xsl:template>
</xsl:stylesheet>
"""))
        result = xslt(etree.XML('<a/>'))
        root = result.getroot()
        self.assertEquals(root.tag,  'test')
        self.assertEquals(len(root), 4)

        self.assertEquals(root[0].text, "123abc567")
        self.assertEquals(root[1].text, "123")
        self.assertEquals(root[2].text, "abc")
        self.assertEquals(root[3].text, "567")

    def test_exslt_regexp_match1(self):
        # taken from http://www.exslt.org/regexp/functions/match/index.html
        xslt = etree.XSLT(etree.XML("""\
<xsl:stylesheet version="1.0"
   xmlns:regexp="http://exslt.org/regular-expressions"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <test>
      <xsl:for-each select="regexp:match(
            'http://www.bayes.co.uk/xml/index.xml?/xml/utils/rechecker.xml',
            '(\w+):\/\/([^/:]+)(:\d*)?([^# ]*)')">
        <test1><xsl:value-of select="."/></test1>
      </xsl:for-each>
    </test>
  </xsl:template>
</xsl:stylesheet>
"""))
        result = xslt(etree.XML('<a/>'))
        root = result.getroot()
        self.assertEquals(root.tag,  'test')
        self.assertEquals(len(root), 5)

        self.assertEquals(
            root[0].text,
            "http://www.bayes.co.uk/xml/index.xml?/xml/utils/rechecker.xml")
        self.assertEquals(
            root[1].text,
            "http")
        self.assertEquals(
            root[2].text,
            "www.bayes.co.uk")
        self.assertFalse(root[3].text)
        self.assertEquals(
            root[4].text,
            "/xml/index.xml?/xml/utils/rechecker.xml")

    def test_exslt_regexp_match2(self):
        # taken from http://www.exslt.org/regexp/functions/match/index.html
        xslt = etree.XSLT(etree.XML("""\
<xsl:stylesheet version="1.0"
   xmlns:regexp="http://exslt.org/regular-expressions"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <test>
      <xsl:for-each select="regexp:match(
            'This is a test string', '(\w+)', 'g')">
        <test1><xsl:value-of select="."/></test1>
      </xsl:for-each>
    </test>
  </xsl:template>
</xsl:stylesheet>
"""))
        result = xslt(etree.XML('<a/>'))
        root = result.getroot()
        self.assertEquals(root.tag,  'test')
        self.assertEquals(len(root), 5)

        self.assertEquals(root[0].text, "This")
        self.assertEquals(root[1].text, "is")
        self.assertEquals(root[2].text, "a")
        self.assertEquals(root[3].text, "test")
        self.assertEquals(root[4].text, "string")

    def _test_exslt_regexp_match3(self):
        # taken from http://www.exslt.org/regexp/functions/match/index.html
        # THIS IS NOT SUPPORTED!
        xslt = etree.XSLT(etree.XML("""\
<xsl:stylesheet version="1.0"
   xmlns:regexp="http://exslt.org/regular-expressions"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <test>
      <xsl:for-each select="regexp:match(
            'This is a test string', '([a-z])+ ', 'g')">
        <test1><xsl:value-of select="."/></test1>
      </xsl:for-each>
    </test>
  </xsl:template>
</xsl:stylesheet>
"""))
        result = xslt(etree.XML('<a/>'))
        root = result.getroot()
        self.assertEquals(root.tag,  'test')
        self.assertEquals(len(root), 4)

        self.assertEquals(root[0].text, "his")
        self.assertEquals(root[1].text, "is")
        self.assertEquals(root[2].text, "a")
        self.assertEquals(root[3].text, "test")

    def _test_exslt_regexp_match4(self):
        # taken from http://www.exslt.org/regexp/functions/match/index.html
        # THIS IS NOT SUPPORTED!
        xslt = etree.XSLT(etree.XML("""\
<xsl:stylesheet version="1.0"
   xmlns:regexp="http://exslt.org/regular-expressions"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <test>
      <xsl:for-each select="regexp:match(
            'This is a test string', '([a-z])+ ', 'gi')">
        <test1><xsl:value-of select="."/></test1>
      </xsl:for-each>
    </test>
  </xsl:template>
</xsl:stylesheet>
"""))
        result = xslt(etree.XML('<a/>'))
        root = result.getroot()
        self.assertEquals(root.tag,  'test')
        self.assertEquals(len(root), 4)

        self.assertEquals(root[0].text, "This")
        self.assertEquals(root[1].text, "is")
        self.assertEquals(root[2].text, "a")
        self.assertEquals(root[3].text, "test")

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeXSLTTestCase)])
    suite.addTests(
        [doctest.DocFileSuite('../../../doc/extensions.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
