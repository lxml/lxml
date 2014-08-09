# -*- coding: utf-8 -*-

"""
Test cases related to XSLT processing
"""

import unittest, copy, sys, os.path

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

is_python3 = sys.version_info[0] >= 3

try:
    unicode
except NameError: # Python 3
    unicode = str

try:
    basestring
except NameError: # Python 3
    basestring = str

from common_imports import etree, BytesIO, HelperTestCase, fileInTestDir
from common_imports import doctest, _bytes, _str, make_doctest, skipif

class ETreeXSLTTestCase(HelperTestCase):
    """XSLT tests etree"""
        
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
        res = st(tree)
        self.assertEqual('''\
<?xml version="1.0"?>
<foo>B</foo>
''',
                          str(res))

    def test_xslt_elementtree_error(self):
        self.assertRaises(ValueError, etree.XSLT, etree.ElementTree())

    def test_xslt_input_none(self):
        self.assertRaises(TypeError, etree.XSLT, None)

    if False and etree.LIBXSLT_VERSION >= (1,1,15):
        # earlier versions generate no error
        if etree.LIBXSLT_VERSION > (1,1,17):
            def test_xslt_invalid_stylesheet(self):
                style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:stylesheet />
</xsl:stylesheet>''')

                self.assertRaises(
                    etree.XSLTParseError, etree.XSLT, style)
        
    def test_xslt_copy(self):
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="*" />
  <xsl:template match="/">
    <foo><xsl:value-of select="/a/b/text()" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        transform = etree.XSLT(style)
        res = transform(tree)
        self.assertEqual('''\
<?xml version="1.0"?>
<foo>B</foo>
''',
                          str(res))

        transform_copy = copy.deepcopy(transform)
        res = transform_copy(tree)
        self.assertEqual('''\
<?xml version="1.0"?>
<foo>B</foo>
''',
                          str(res))

        transform = etree.XSLT(style)
        res = transform(tree)
        self.assertEqual('''\
<?xml version="1.0"?>
<foo>B</foo>
''',
                          str(res))

    def test_xslt_utf8(self):
        tree = self.parse(_bytes('<a><b>\\uF8D2</b><c>\\uF8D2</c></a>'
                                 ).decode("unicode_escape"))
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output encoding="UTF-8"/>
  <xsl:template match="/">
    <foo><xsl:value-of select="/a/b/text()" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = st(tree)
        expected = _bytes('''\
<?xml version="1.0" encoding="UTF-8"?>
<foo>\\uF8D2</foo>
''').decode("unicode_escape")
        if is_python3:
            self.assertEqual(expected,
                              str(bytes(res), 'UTF-8'))
        else:
            self.assertEqual(expected,
                              unicode(str(res), 'UTF-8'))

    def test_xslt_encoding(self):
        tree = self.parse(_bytes('<a><b>\\uF8D2</b><c>\\uF8D2</c></a>'
                                 ).decode("unicode_escape"))
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output encoding="UTF-16"/>
  <xsl:template match="/">
    <foo><xsl:value-of select="/a/b/text()" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = st(tree)
        expected = _bytes('''\
<?xml version="1.0" encoding="UTF-16"?>
<foo>\\uF8D2</foo>
''').decode("unicode_escape")
        if is_python3:
            self.assertEqual(expected,
                              str(bytes(res), 'UTF-16'))
        else:
            self.assertEqual(expected,
                              unicode(str(res), 'UTF-16'))

    def test_xslt_encoding_override(self):
        tree = self.parse(_bytes('<a><b>\\uF8D2</b><c>\\uF8D2</c></a>'
                                 ).decode("unicode_escape"))
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output encoding="UTF-8"/>
  <xsl:template match="/">
    <foo><xsl:value-of select="/a/b/text()" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = st(tree)
        expected = _bytes("""\
<?xml version='1.0' encoding='UTF-16'?>\
<foo>\\uF8D2</foo>""").decode("unicode_escape")

        f = BytesIO()
        res.write(f, encoding='UTF-16')
        if is_python3:
            result = str(f.getvalue(), 'UTF-16').replace('\n', '')
        else:
            result = unicode(str(f.getvalue()), 'UTF-16').replace('\n', '')
        self.assertEqual(expected, result)

    def test_xslt_unicode(self):
        tree = self.parse(_bytes('<a><b>\\uF8D2</b><c>\\uF8D2</c></a>'
                                 ).decode("unicode_escape"))
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output encoding="UTF-16"/>
  <xsl:template match="/">
    <foo><xsl:value-of select="/a/b/text()" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = st(tree)
        expected = _bytes('''\
<?xml version="1.0"?>
<foo>\\uF8D2</foo>
''').decode("unicode_escape")
        self.assertEqual(expected,
                          unicode(res))

    def test_xslt_unicode_standalone(self):
        tree = self.parse(_bytes('<a><b>\\uF8D2</b><c>\\uF8D2</c></a>'
        ).decode("unicode_escape"))
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output encoding="UTF-16" standalone="no"/>
  <xsl:template match="/">
    <foo><xsl:value-of select="/a/b/text()" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = st(tree)
        expected = _bytes('''\
<?xml version="1.0" standalone="no"?>
<foo>\\uF8D2</foo>
''').decode("unicode_escape")
        self.assertEqual(expected,
                         unicode(res))

    def test_xslt_input(self):
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
        res = st(tree, bar="'Bar'")
        self.assertEqual('''\
<?xml version="1.0"?>
<foo>Bar</foo>
''',
                          str(res))

    def test_xslt_string_parameters(self):
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <foo><xsl:value-of select="$bar" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = st(tree, bar=etree.XSLT.strparam('''it's me, "Bar"'''))
        self.assertEqual('''\
<?xml version="1.0"?>
<foo>it's me, "Bar"</foo>
''',
                          str(res))

    def test_xslt_parameter_invalid(self):
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:param name="bar"/>
  <xsl:template match="/">
    <foo><xsl:value-of select="$bar" /></foo>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = self.assertRaises(etree.XSLTApplyError,
                                st, tree, bar="<test/>")
        res = self.assertRaises(etree.XSLTApplyError,
                                st, tree, bar="....")

    if etree.LIBXSLT_VERSION < (1,1,18):
        # later versions produce no error
        def test_xslt_parameter_missing(self):
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
        res = st(tree, bar="'Bar'", baz="'Baz'")
        self.assertEqual('''\
<?xml version="1.0"?>
<foo>Bar</foo><foo>Baz</foo>
''',
                          str(res))
        
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
        res = st(tree, bar="/a/b/text()")
        self.assertEqual('''\
<?xml version="1.0"?>
<foo>B</foo>
''',
                          str(res))

    def test_xslt_parameter_xpath_object(self):
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
        res = st(tree, bar=etree.XPath("/a/b/text()"))
        self.assertEqual('''\
<?xml version="1.0"?>
<foo>B</foo>
''',
                          str(res))
        
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
        res = st(tree, bar="'Bar'")
        self.assertEqual('''\
<?xml version="1.0"?>
<foo>Bar</foo>
''',
                          str(res))
        res = st(tree)
        self.assertEqual('''\
<?xml version="1.0"?>
<foo>Default</foo>
''',
                          str(res))
        
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
        self.assertEqual('<html><body>B</body></html>',
                          str(res).strip())

    def test_xslt_include(self):
        tree = etree.parse(fileInTestDir('test1.xslt'))
        st = etree.XSLT(tree)

    def test_xslt_include_from_filelike(self):
        f = open(fileInTestDir('test1.xslt'), 'rb')
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
        result = style(source)

        etree.tostring(result.getroot())
        
        source = self.parse(xml)
        styledoc = self.parse(xslt)
        style = etree.XSLT(styledoc)
        result = style(source)
        
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
        result = transform(source)
        result = transform(source)
        etree.tostring(result.getroot())
        result = transform(source)
        etree.tostring(result.getroot())
        str(result)

        result1 = transform(source)
        result2 = transform(source)
        self.assertEqual(str(result1), str(result2))
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
        result = style(source)
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
        result = style(source)
        self.assertEqual('', str(result))
        self.assertTrue("TEST TEST TEST" in [entry.message
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

        self.assertRaises(etree.XSLTApplyError, style, source)
        self.assertTrue("TEST TEST TEST" in [entry.message
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
        self.assertEqual(
            _bytes('<doc><foo>Bar</foo><foo>Baz</foo></doc>'),
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

        self.assertEqual(self._rootstring(tree),
                          _bytes('<a><b>B</b><c>C</c></a>'))
        result = tree.xslt(style)
        self.assertEqual(self._rootstring(tree),
                          _bytes('<a><b>B</b><c>C</c></a>'))
        self.assertEqual(self._rootstring(result),
                          _bytes('<A><B>B</B><C>C</C></A>'))

        b_tree = etree.ElementTree(tree.getroot()[0])
        self.assertEqual(self._rootstring(b_tree),
                          _bytes('<b>B</b>'))
        result = b_tree.xslt(style)
        self.assertEqual(self._rootstring(tree),
                          _bytes('<a><b>B</b><c>C</c></a>'))
        self.assertEqual(self._rootstring(result),
                          _bytes('<B>B</B>'))

        c_tree = etree.ElementTree(tree.getroot()[1])
        self.assertEqual(self._rootstring(c_tree),
                          _bytes('<c>C</c>'))
        result = c_tree.xslt(style)
        self.assertEqual(self._rootstring(tree),
                          _bytes('<a><b>B</b><c>C</c></a>'))
        self.assertEqual(self._rootstring(result),
                          _bytes('<C>C</C>'))

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
        self.assertEqual(root.tag,
                          'test')
        self.assertEqual(root[0].tag,
                          'test')
        self.assertEqual(root[0].text,
                          'TEXT')
        self.assertEqual(root[0][0].tag,
                          '{http://www.w3.org/1999/XSL/Transform}copy-of')

    def test_xslt_document_parse(self):
        # make sure document('') works from loaded files
        xslt = etree.XSLT(etree.parse(fileInTestDir("test-document.xslt")))
        result = xslt(etree.XML('<a/>'))
        root = result.getroot()
        self.assertEqual(root.tag,
                          'test')
        self.assertEqual(root[0].tag,
                          '{http://www.w3.org/1999/XSL/Transform}stylesheet')

    def test_xslt_document_elementtree(self):
        # make sure document('') works from loaded files
        xslt = etree.XSLT(etree.ElementTree(file=fileInTestDir("test-document.xslt")))
        result = xslt(etree.XML('<a/>'))
        root = result.getroot()
        self.assertEqual(root.tag,
                          'test')
        self.assertEqual(root[0].tag,
                          '{http://www.w3.org/1999/XSL/Transform}stylesheet')

    def test_xslt_document_error(self):
        xslt = etree.XSLT(etree.XML("""\
<xsl:stylesheet version="1.0"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/">
    <test>TEXT<xsl:copy-of select="document('uri:__junkfood__is__evil__')//test"/></test>
  </xsl:template>
</xsl:stylesheet>
"""))
        self.assertRaises(etree.XSLTApplyError, xslt, etree.XML('<a/>'))

    def test_xslt_document_XML_resolver(self):
        # make sure document('') works when custom resolvers are in use
        assertEqual = self.assertEqual
        called = {'count' : 0}
        class TestResolver(etree.Resolver):
            def resolve(self, url, id, context):
                assertEqual(url, 'file://ANYTHING')
                called['count'] += 1
                return self.resolve_string('<CALLED/>', context)

        parser = etree.XMLParser()
        parser.resolvers.add(TestResolver())

        xslt = etree.XSLT(etree.XML(_bytes("""\
<xsl:stylesheet version="1.0"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:l="local">
  <xsl:template match="/">
    <test>
      <xsl:for-each select="document('')//l:data/l:entry">
        <xsl:copy-of select="document('file://ANYTHING')"/>
        <xsl:copy>
          <xsl:attribute name="value">
            <xsl:value-of select="."/>
          </xsl:attribute>
        </xsl:copy>
      </xsl:for-each>
    </test>
  </xsl:template>
  <l:data>
    <l:entry>A</l:entry>
    <l:entry>B</l:entry>
  </l:data>
</xsl:stylesheet>
"""), parser))

        self.assertEqual(called['count'], 0)
        result = xslt(etree.XML('<a/>'))
        self.assertEqual(called['count'], 1)

        root = result.getroot()
        self.assertEqual(root.tag,
                          'test')
        self.assertEqual(len(root), 4)

        self.assertEqual(root[0].tag,
                          'CALLED')
        self.assertEqual(root[1].tag,
                          '{local}entry')
        self.assertEqual(root[1].text,
                          None)
        self.assertEqual(root[1].get("value"),
                          'A')
        self.assertEqual(root[2].tag,
                          'CALLED')
        self.assertEqual(root[3].tag,
                          '{local}entry')
        self.assertEqual(root[3].text,
                          None)
        self.assertEqual(root[3].get("value"),
                          'B')

    def test_xslt_resolver_url_building(self):
        assertEqual = self.assertEqual
        called = {'count' : 0}
        expected_url = None
        class TestResolver(etree.Resolver):
            def resolve(self, url, id, context):
                assertEqual(url, expected_url)
                called['count'] += 1
                return self.resolve_string('<CALLED/>', context)

        stylesheet_xml = _bytes("""\
<xsl:stylesheet version="1.0"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:l="local">
  <xsl:template match="/">
    <xsl:copy-of select="document('test.xml')"/>
  </xsl:template>
</xsl:stylesheet>
""")

        parser = etree.XMLParser()
        parser.resolvers.add(TestResolver())

        # test without base_url => relative path only
        expected_url = 'test.xml'
        xslt = etree.XSLT(etree.XML(stylesheet_xml, parser))

        self.assertEqual(called['count'], 0)
        result = xslt(etree.XML('<a/>'))
        self.assertEqual(called['count'], 1)

        # now the same thing with a stylesheet base URL on the filesystem
        called['count'] = 0
        expected_url = 'MY/BASE/test.xml'  # seems to be the same on Windows
        xslt = etree.XSLT(etree.XML(
            stylesheet_xml, parser,
            base_url=os.path.join('MY', 'BASE', 'FILE')))

        self.assertEqual(called['count'], 0)
        result = xslt(etree.XML('<a/>'))
        self.assertEqual(called['count'], 1)

        # now the same thing with a stylesheet base URL
        called['count'] = 0
        expected_url = 'http://server.com/BASE/DIR/test.xml'
        xslt = etree.XSLT(etree.XML(
            stylesheet_xml, parser,
            base_url='http://server.com/BASE/DIR/FILE'))

        self.assertEqual(called['count'], 0)
        result = xslt(etree.XML('<a/>'))
        self.assertEqual(called['count'], 1)

        # now the same thing with a stylesheet base file:// URL
        called['count'] = 0
        expected_url = 'file://BASE/DIR/test.xml'
        xslt = etree.XSLT(etree.XML(
            stylesheet_xml, parser,
            base_url='file://BASE/DIR/FILE'))

        self.assertEqual(called['count'], 0)
        result = xslt(etree.XML('<a/>'))
        self.assertEqual(called['count'], 1)

    def test_xslt_document_parse_allow(self):
        access_control = etree.XSLTAccessControl(read_file=True)
        xslt = etree.XSLT(etree.parse(fileInTestDir("test-document.xslt")),
                          access_control=access_control)
        result = xslt(etree.XML('<a/>'))
        root = result.getroot()
        self.assertEqual(root.tag,
                         'test')
        self.assertEqual(root[0].tag,
                         '{http://www.w3.org/1999/XSL/Transform}stylesheet')

    def test_xslt_document_parse_deny(self):
        access_control = etree.XSLTAccessControl(read_file=False)
        xslt = etree.XSLT(etree.parse(fileInTestDir("test-document.xslt")),
                          access_control=access_control)
        self.assertRaises(etree.XSLTApplyError, xslt, etree.XML('<a/>'))

    def test_xslt_document_parse_deny_all(self):
        access_control = etree.XSLTAccessControl.DENY_ALL
        xslt = etree.XSLT(etree.parse(fileInTestDir("test-document.xslt")),
                          access_control=access_control)
        self.assertRaises(etree.XSLTApplyError, xslt, etree.XML('<a/>'))

    def test_xslt_access_control_repr(self):
        access_control = etree.XSLTAccessControl.DENY_ALL
        self.assertTrue(repr(access_control).startswith(type(access_control).__name__))
        self.assertEqual(repr(access_control), repr(access_control))
        self.assertNotEqual(repr(etree.XSLTAccessControl.DENY_ALL),
                            repr(etree.XSLTAccessControl.DENY_WRITE))
        self.assertNotEqual(repr(etree.XSLTAccessControl.DENY_ALL),
                            repr(etree.XSLTAccessControl()))

    def test_xslt_move_result(self):
        root = etree.XML(_bytes('''\
        <transform>
          <widget displayType="fieldset"/>
        </transform>'''))

        xslt = etree.XSLT(etree.XML(_bytes('''\
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

        </xsl:stylesheet>''')))

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
        self.assertEqual("{http://www.w3.org/1999/XSL/Transform}stylesheet",
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
        self.assertEqual("{http://www.w3.org/1999/XSL/Transform}stylesheet",
                          style_root.tag)

        st = etree.XSLT(style_root)
        res = st(tree)
        self.assertEqual('''\
<?xml version="1.0"?>
<foo>B</foo>
''',
                          str(res))

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
        self.assertEqual("{http://www.w3.org/1999/XSL/Transform}stylesheet",
                          style_root.tag)

        st = etree.XSLT(style_root)
        res = st(tree)
        self.assertEqual('''\
<?xml version="1.0"?>
<foo>B</foo>
''',
                          str(res))

    def test_xslt_pi_get(self):
        tree = self.parse('''\
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="TEST"?>
<a>
  <b>B</b>
  <c>C</c>
</a>''')

        pi = tree.getroot().getprevious()
        self.assertEqual("TEST", pi.get("href"))

    def test_xslt_pi_get_all(self):
        tree = self.parse('''\
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="TEST"?>
<a>
  <b>B</b>
  <c>C</c>
</a>''')

        pi = tree.getroot().getprevious()
        self.assertEqual("TEST", pi.get("href"))
        self.assertEqual("text/xsl", pi.get("type"))
        self.assertEqual(None, pi.get("motz"))

    def test_xslt_pi_get_all_reversed(self):
        tree = self.parse('''\
<?xml version="1.0"?>
<?xml-stylesheet href="TEST" type="text/xsl"?>
<a>
  <b>B</b>
  <c>C</c>
</a>''')

        pi = tree.getroot().getprevious()
        self.assertEqual("TEST", pi.get("href"))
        self.assertEqual("text/xsl", pi.get("type"))
        self.assertEqual(None, pi.get("motz"))

    def test_xslt_pi_get_unknown(self):
        tree = self.parse('''\
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="TEST"?>
<a>
  <b>B</b>
  <c>C</c>
</a>''')

        pi = tree.getroot().getprevious()
        self.assertEqual(None, pi.get("unknownattribute"))

    def test_xslt_pi_set_replace(self):
        tree = self.parse('''\
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl" href="TEST"?>
<a>
  <b>B</b>
  <c>C</c>
</a>''')

        pi = tree.getroot().getprevious()
        self.assertEqual("TEST", pi.get("href"))

        pi.set("href", "TEST123")
        self.assertEqual("TEST123", pi.get("href"))

    def test_xslt_pi_set_new(self):
        tree = self.parse('''\
<?xml version="1.0"?>
<?xml-stylesheet type="text/xsl"?>
<a>
  <b>B</b>
  <c>C</c>
</a>''')

        pi = tree.getroot().getprevious()
        self.assertEqual(None, pi.get("href"))

        pi.set("href", "TEST")
        self.assertEqual("TEST", pi.get("href"))

class ETreeEXSLTTestCase(HelperTestCase):
    """EXSLT tests"""

    def test_exslt_str(self):
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:str="http://exslt.org/strings"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    exclude-result-prefixes="str xsl">
  <xsl:template match="text()">
    <xsl:value-of select="str:align(string(.), '***', 'center')" />
  </xsl:template>
  <xsl:template match="*">
    <xsl:copy>
      <xsl:apply-templates/>
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>''')

        st = etree.XSLT(style)
        res = st(tree)
        self.assertEqual('''\
<?xml version="1.0"?>
<a><b>*B*</b><c>*C*</c></a>
''',
                          str(res))

    if etree.LIBXSLT_VERSION >= (1,1,21):
        def test_exslt_str_attribute_replace(self):
            tree = self.parse('<a><b>B</b><c>C</c></a>')
            style = self.parse('''\
      <xsl:stylesheet version = "1.0"
          xmlns:xsl='http://www.w3.org/1999/XSL/Transform'
          xmlns:str="http://exslt.org/strings"
          extension-element-prefixes="str">

          <xsl:template match="/">
            <h1 class="{str:replace('abc', 'b', 'x')}">test</h1>
          </xsl:template>

      </xsl:stylesheet>''')

            st = etree.XSLT(style)
            res = st(tree)
            self.assertEqual('''\
<?xml version="1.0"?>
<h1 class="axc">test</h1>
''',
                              str(res))

    def test_exslt_math(self):
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:math="http://exslt.org/math"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    exclude-result-prefixes="math xsl">
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
        self.assertEqual('''\
<?xml version="1.0"?>
<a pi="3.14"><b pi="3">B</b><c pi="3">C</c></a>
''',
                          str(res))

    def test_exslt_regexp_test(self):
        xslt = etree.XSLT(etree.XML(_bytes("""\
<xsl:stylesheet version="1.0"
   xmlns:regexp="http://exslt.org/regular-expressions"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="*">
    <test><xsl:copy-of select="*[regexp:test(string(.), '8.')]"/></test>
  </xsl:template>
</xsl:stylesheet>
""")))
        result = xslt(etree.XML(_bytes('<a><b>123</b><b>098</b><b>987</b></a>')))
        root = result.getroot()
        self.assertEqual(root.tag,
                          'test')
        self.assertEqual(len(root), 1)
        self.assertEqual(root[0].tag,
                          'b')
        self.assertEqual(root[0].text,
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
        result = xslt(etree.XML(_bytes('<a>abdCdEeDed</a>')))
        root = result.getroot()
        self.assertEqual(root.tag,
                          'test')
        self.assertEqual(len(root), 0)
        self.assertEqual(root.text, 'abXXdEeDed-abXXXXeXXd')

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
        result = xslt(etree.XML(_bytes('<a>abdCdEeDed</a>')))
        root = result.getroot()
        self.assertEqual(root.tag,  'test')
        self.assertEqual(len(root), 3)

        self.assertEqual(len(root[0]), 1)
        self.assertEqual(root[0][0].tag, 'match')
        self.assertEqual(root[0][0].text, 'dC')

        self.assertEqual(len(root[1]), 2)
        self.assertEqual(root[1][0].tag, 'match')
        self.assertEqual(root[1][0].text, 'dC')
        self.assertEqual(root[1][1].tag, 'match')
        self.assertEqual(root[1][1].text, 'dE')

        self.assertEqual(len(root[2]), 3)
        self.assertEqual(root[2][0].tag, 'match')
        self.assertEqual(root[2][0].text, 'dC')
        self.assertEqual(root[2][1].tag, 'match')
        self.assertEqual(root[2][1].text, 'dE')
        self.assertEqual(root[2][2].tag, 'match')
        self.assertEqual(root[2][2].text, 'De')

    def test_exslt_regexp_match_groups(self):
        xslt = etree.XSLT(etree.XML(_bytes("""\
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
""")))
        result = xslt(etree.XML(_bytes('<a/>')))
        root = result.getroot()
        self.assertEqual(root.tag,  'test')
        self.assertEqual(len(root), 4)

        self.assertEqual(root[0].text, "123abc567")
        self.assertEqual(root[1].text, "123")
        self.assertEqual(root[2].text, "abc")
        self.assertEqual(root[3].text, "567")

    def test_exslt_regexp_match1(self):
        # taken from http://www.exslt.org/regexp/functions/match/index.html
        xslt = etree.XSLT(etree.XML(_bytes("""\
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
""")))
        result = xslt(etree.XML(_bytes('<a/>')))
        root = result.getroot()
        self.assertEqual(root.tag,  'test')
        self.assertEqual(len(root), 5)

        self.assertEqual(
            root[0].text,
            "http://www.bayes.co.uk/xml/index.xml?/xml/utils/rechecker.xml")
        self.assertEqual(
            root[1].text,
            "http")
        self.assertEqual(
            root[2].text,
            "www.bayes.co.uk")
        self.assertFalse(root[3].text)
        self.assertEqual(
            root[4].text,
            "/xml/index.xml?/xml/utils/rechecker.xml")

    def test_exslt_regexp_match2(self):
        # taken from http://www.exslt.org/regexp/functions/match/index.html
        xslt = etree.XSLT(self.parse("""\
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
        result = xslt(etree.XML(_bytes('<a/>')))
        root = result.getroot()
        self.assertEqual(root.tag,  'test')
        self.assertEqual(len(root), 5)

        self.assertEqual(root[0].text, "This")
        self.assertEqual(root[1].text, "is")
        self.assertEqual(root[2].text, "a")
        self.assertEqual(root[3].text, "test")
        self.assertEqual(root[4].text, "string")

    def _test_exslt_regexp_match3(self):
        # taken from http://www.exslt.org/regexp/functions/match/index.html
        # THIS IS NOT SUPPORTED!
        xslt = etree.XSLT(etree.XML(_bytes("""\
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
""")))
        result = xslt(etree.XML(_bytes('<a/>')))
        root = result.getroot()
        self.assertEqual(root.tag,  'test')
        self.assertEqual(len(root), 4)

        self.assertEqual(root[0].text, "his")
        self.assertEqual(root[1].text, "is")
        self.assertEqual(root[2].text, "a")
        self.assertEqual(root[3].text, "test")

    def _test_exslt_regexp_match4(self):
        # taken from http://www.exslt.org/regexp/functions/match/index.html
        # THIS IS NOT SUPPORTED!
        xslt = etree.XSLT(etree.XML(_bytes("""\
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
""")))
        result = xslt(etree.XML(_bytes('<a/>')))
        root = result.getroot()
        self.assertEqual(root.tag,  'test')
        self.assertEqual(len(root), 4)

        self.assertEqual(root[0].text, "This")
        self.assertEqual(root[1].text, "is")
        self.assertEqual(root[2].text, "a")
        self.assertEqual(root[3].text, "test")


class ETreeXSLTExtFuncTestCase(HelperTestCase):
    """Tests for XPath extension functions in XSLT."""

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
        self.assertEqual(self._rootstring(result),
                          _bytes('<A>X</A>'))

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
        self.assertEqual(self._rootstring(result),
                          _bytes('<A>X</A>'))

    def test_variable_result_tree_fragment(self):
        tree = self.parse('<a><b>B</b><b/></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    exclude-result-prefixes="myns">
  <xsl:template match="a">
    <xsl:variable name="content">
       <xsl:apply-templates/>
    </xsl:variable>
    <A><xsl:value-of select="myns:mytext($content)"/></A>
  </xsl:template>
  <xsl:template match="b"><xsl:copy>BBB</xsl:copy></xsl:template>
</xsl:stylesheet>''')

        def mytext(ctxt, values):
            for value in values:
                self.assertTrue(hasattr(value, 'tag'),
                             "%s is not an Element" % type(value))
                self.assertEqual(value.tag, 'b')
                self.assertEqual(value.text, 'BBB')
            return 'X'.join([el.tag for el in values])

        namespace = etree.FunctionNamespace('testns')
        namespace['mytext'] = mytext

        result = tree.xslt(style)
        self.assertEqual(self._rootstring(result),
                         _bytes('<A>bXb</A>'))

    def test_xpath_on_context_node(self):
        tree = self.parse('<a><b>B<c/>C</b><b/></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    exclude-result-prefixes="myns">
  <xsl:template match="b">
    <A><xsl:value-of select="myns:myext()"/></A>
  </xsl:template>
</xsl:stylesheet>''')

        def extfunc(ctxt):
            text_content = ctxt.context_node.xpath('text()')
            return 'x'.join(text_content)

        namespace = etree.FunctionNamespace('testns')
        namespace['myext'] = extfunc

        result = tree.xslt(style)
        self.assertEqual(self._rootstring(result),
                         _bytes('<A>BxC</A>'))

    def test_xpath_on_foreign_context_node(self):
        # LP ticket 1354652
        class Resolver(etree.Resolver):
            def resolve(self, system_url, public_id, context):
                assert system_url == 'extdoc.xml'
                return self.resolve_string(b'<a><b>B<c/>C</b><b/></a>', context)

        parser = etree.XMLParser()
        parser.resolvers.add(Resolver())

        tree = self.parse(b'<a><b/><b/></a>')
        transform = etree.XSLT(self.parse(b'''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:mypre="testns"
    exclude-result-prefixes="mypre">
  <xsl:template match="b">
    <B><xsl:value-of select="mypre:myext()"/></B>
  </xsl:template>
  <xsl:template match="a">
    <A><xsl:apply-templates select="document('extdoc.xml')//b" /></A>
  </xsl:template>
</xsl:stylesheet>''', parser=parser))

        def extfunc(ctxt):
            text_content = ctxt.context_node.xpath('text()')
            return 'x'.join(text_content)

        namespace = etree.FunctionNamespace('testns')
        namespace['myext'] = extfunc

        result = transform(tree)
        self.assertEqual(self._rootstring(result),
                         _bytes('<A><B>BxC</B><B/></A>'))


class ETreeXSLTExtElementTestCase(HelperTestCase):
    """Tests for extension elements in XSLT."""

    def test_extension_element(self):
        tree = self.parse('<a><b>B</b></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    extension-element-prefixes="myns"
    exclude-result-prefixes="myns">
  <xsl:template match="a">
    <A><myns:myext>b</myns:myext></A>
  </xsl:template>
</xsl:stylesheet>''')

        class MyExt(etree.XSLTExtension):
            def execute(self, context, self_node, input_node, output_parent):
                child = etree.Element(self_node.text)
                child.text = 'X'
                output_parent.append(child)

        extensions = { ('testns', 'myext') : MyExt() }

        result = tree.xslt(style, extensions=extensions)
        self.assertEqual(self._rootstring(result),
                          _bytes('<A><b>X</b></A>'))

    def test_extension_element_doc_context(self):
        tree = self.parse('<a><b>B</b></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    extension-element-prefixes="myns"
    exclude-result-prefixes="myns">
  <xsl:template match="/">
    <A><myns:myext>b</myns:myext></A>
  </xsl:template>
</xsl:stylesheet>''')

        tags = []

        class MyExt(etree.XSLTExtension):
            def execute(self, context, self_node, input_node, output_parent):
                tags.append(input_node.tag)

        extensions = { ('testns', 'myext') : MyExt() }

        result = tree.xslt(style, extensions=extensions)
        self.assertEqual(tags, ['a'])

    def test_extension_element_comment_pi_context(self):
        tree = self.parse('<?test toast?><a><!--a comment--><?another pi?></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    extension-element-prefixes="myns"
    exclude-result-prefixes="myns">
  <xsl:template match="/">
    <ROOT><xsl:apply-templates /></ROOT>
  </xsl:template>
  <xsl:template match="comment()">
    <A><myns:myext>b</myns:myext></A>
  </xsl:template>
  <xsl:template match="processing-instruction()">
    <A><myns:myext>b</myns:myext></A>
  </xsl:template>
</xsl:stylesheet>''')

        text = []

        class MyExt(etree.XSLTExtension):
            def execute(self, context, self_node, input_node, output_parent):
                text.append(input_node.text)

        extensions = { ('testns', 'myext') : MyExt() }

        result = tree.xslt(style, extensions=extensions)
        self.assertEqual(text, ['toast', 'a comment', 'pi'])

    def _test_extension_element_attribute_context(self):
        # currently not supported
        tree = self.parse('<a test="A"><b attr="B"/></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    extension-element-prefixes="myns"
    exclude-result-prefixes="myns">
  <xsl:template match="@test">
    <A><myns:myext>b</myns:myext></A>
  </xsl:template>
  <xsl:template match="@attr">
    <A><myns:myext>b</myns:myext></A>
  </xsl:template>
</xsl:stylesheet>''')

        text = []

        class MyExt(etree.XSLTExtension):
            def execute(self, context, self_node, attr_value, output_parent):
                text.append(attr_value)

        extensions = { ('testns', 'myext') : MyExt() }

        result = tree.xslt(style, extensions=extensions)
        self.assertEqual(text, ['A', 'B'])

    def test_extension_element_content(self):
        tree = self.parse('<a><b>B</b></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    extension-element-prefixes="myns">
  <xsl:template match="a">
    <A><myns:myext><x>X</x><y>Y</y><z/></myns:myext></A>
  </xsl:template>
</xsl:stylesheet>''')

        class MyExt(etree.XSLTExtension):
            def execute(self, context, self_node, input_node, output_parent):
                output_parent.extend(list(self_node)[1:])

        extensions = { ('testns', 'myext') : MyExt() }

        result = tree.xslt(style, extensions=extensions)
        self.assertEqual(self._rootstring(result),
                          _bytes('<A><y>Y</y><z/></A>'))

    def test_extension_element_apply_templates(self):
        tree = self.parse('<a><b>B</b></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    extension-element-prefixes="myns">
  <xsl:template match="a">
    <A><myns:myext><x>X</x><y>Y</y><z/></myns:myext></A>
  </xsl:template>
  <xsl:template match="x" />
  <xsl:template match="z">XYZ</xsl:template>
</xsl:stylesheet>''')

        class MyExt(etree.XSLTExtension):
            def execute(self, context, self_node, input_node, output_parent):
                for child in self_node:
                    for result in self.apply_templates(context, child):
                        if isinstance(result, basestring):
                            el = etree.Element("T")
                            el.text = result
                        else:
                            el = result
                        output_parent.append(el)

        extensions = { ('testns', 'myext') : MyExt() }

        result = tree.xslt(style, extensions=extensions)
        self.assertEqual(self._rootstring(result),
                          _bytes('<A><T>Y</T><T>XYZ</T></A>'))

    def test_extension_element_apply_templates_elements_only(self):
        tree = self.parse('<a><b>B</b></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    extension-element-prefixes="myns">
  <xsl:template match="a">
    <A><myns:myext><x>X</x><y>Y</y><z/></myns:myext></A>
  </xsl:template>
  <xsl:template match="x"><X/></xsl:template>
  <xsl:template match="z">XYZ</xsl:template>
</xsl:stylesheet>''')

        class MyExt(etree.XSLTExtension):
            def execute(self, context, self_node, input_node, output_parent):
                for child in self_node:
                    for result in self.apply_templates(context, child,
                                                       elements_only=True):
                        assert not isinstance(result, basestring)
                        output_parent.append(result)

        extensions = { ('testns', 'myext') : MyExt() }

        result = tree.xslt(style, extensions=extensions)
        self.assertEqual(self._rootstring(result),
                          _bytes('<A><X/></A>'))

    def test_extension_element_apply_templates_remove_blank_text(self):
        tree = self.parse('<a><b>B</b></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    extension-element-prefixes="myns">
  <xsl:template match="a">
    <A><myns:myext><x>X</x><y>Y</y><z/></myns:myext></A>
  </xsl:template>
  <xsl:template match="x"><X/></xsl:template>
  <xsl:template match="y"><xsl:text>   </xsl:text></xsl:template>
  <xsl:template match="z">XYZ</xsl:template>
</xsl:stylesheet>''')

        class MyExt(etree.XSLTExtension):
            def execute(self, context, self_node, input_node, output_parent):
                for child in self_node:
                    for result in self.apply_templates(context, child,
                                                       remove_blank_text=True):
                        if isinstance(result, basestring):
                            assert result.strip()
                            el = etree.Element("T")
                            el.text = result
                        else:
                            el = result
                        output_parent.append(el)

        extensions = { ('testns', 'myext') : MyExt() }

        result = tree.xslt(style, extensions=extensions)
        self.assertEqual(self._rootstring(result),
                          _bytes('<A><X/><T>XYZ</T></A>'))

    def test_extension_element_apply_templates_target_node(self):
        tree = self.parse('<a><b>B</b></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    extension-element-prefixes="myns">
  <xsl:template match="a">
    <A><myns:myext><x>X</x><y>Y</y><z/></myns:myext></A>
  </xsl:template>
  <xsl:template match="x" />
  <xsl:template match="z">XYZ</xsl:template>
</xsl:stylesheet>''')

        class MyExt(etree.XSLTExtension):
            def execute(self, context, self_node, input_node, output_parent):
                for child in self_node:
                    self.apply_templates(context, child, output_parent)

        extensions = { ('testns', 'myext') : MyExt() }

        result = tree.xslt(style, extensions=extensions)
        self.assertEqual(self._rootstring(result),
                          _bytes('<A>YXYZ</A>'))

    def test_extension_element_apply_templates_target_node_doc(self):
        tree = self.parse('<a><b>B</b></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    extension-element-prefixes="myns">
  <xsl:template match="a">
    <myns:myext><x>X</x><y>Y</y><z/></myns:myext>
  </xsl:template>
  <xsl:template match="x"><xsl:processing-instruction name="test">TEST</xsl:processing-instruction></xsl:template>
  <xsl:template match="y"><Y>XYZ</Y></xsl:template>
  <xsl:template match="z"><xsl:comment>TEST</xsl:comment></xsl:template>
</xsl:stylesheet>''')

        class MyExt(etree.XSLTExtension):
            def execute(self, context, self_node, input_node, output_parent):
                for child in self_node:
                    self.apply_templates(context, child, output_parent)

        extensions = { ('testns', 'myext') : MyExt() }

        result = tree.xslt(style, extensions=extensions)
        self.assertEqual(etree.tostring(result),
                          _bytes('<?test TEST?><Y>XYZ</Y><!--TEST-->'))

    def test_extension_element_process_children(self):
        tree = self.parse('<a><b>E</b></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    extension-element-prefixes="myns">
  <xsl:template match="a">
    <xsl:variable name="testvar">yo</xsl:variable>
    <A>
      <myns:myext>
        <xsl:attribute name="attr">
          <xsl:value-of select="$testvar" />
        </xsl:attribute>
        <B>
          <xsl:choose>
            <xsl:when test="1 = 2"><C/></xsl:when>
            <xsl:otherwise><D><xsl:value-of select="b/text()" /></D></xsl:otherwise>
          </xsl:choose>
        </B>
      </myns:myext>
    </A>
  </xsl:template>
</xsl:stylesheet>''')

        class MyExt(etree.XSLTExtension):
            def execute(self, context, self_node, input_node, output_parent):
                el = etree.Element('MY')
                self.process_children(context, el)
                output_parent.append(el)

        extensions = { ('testns', 'myext') : MyExt() }

        result = tree.xslt(style, extensions=extensions)
        self.assertEqual(self._rootstring(result),
                          _bytes('<A><MYattr="yo"><B><D>E</D></B></MY></A>'))

    def test_extension_element_process_children_to_append_only(self):
        tree = self.parse('<a/>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    extension-element-prefixes="myns">
  <xsl:template match="a">
    <myns:myext>
      <A/>
    </myns:myext>
  </xsl:template>
</xsl:stylesheet>''')

        class MyExt(etree.XSLTExtension):
            def execute(self, context, self_node, input_node, output_parent):
                self.process_children(context, output_parent)

        extensions = { ('testns', 'myext') : MyExt() }

        result = tree.xslt(style, extensions=extensions)
        self.assertEqual(self._rootstring(result),
                          _bytes('<A/>'))

    def test_extension_element_process_children_to_read_only_raise(self):
        tree = self.parse('<a/>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    extension-element-prefixes="myns">
  <xsl:template match="a">
    <myns:myext>
      <A/>
    </myns:myext>
  </xsl:template>
</xsl:stylesheet>''')

        class MyExt(etree.XSLTExtension):
            def execute(self, context, self_node, input_node, output_parent):
                self.process_children(context, self_node)

        extensions = { ('testns', 'myext') : MyExt() }

        self.assertRaises(TypeError, tree.xslt, style, extensions=extensions)

    def test_extension_element_process_children_with_subextension_element(self):
        tree = self.parse('<a/>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    extension-element-prefixes="myns">
  <xsl:template match="a">
    <myns:myext>
      <A><myns:myext><B/></myns:myext></A>
    </myns:myext>
  </xsl:template>
</xsl:stylesheet>''')

        class MyExt(etree.XSLTExtension):
            callback_call_counter = 0
            def execute(self, context, self_node, input_node, output_parent):
                self.callback_call_counter += 1
                el = etree.Element('MY', n=str(self.callback_call_counter))
                self.process_children(context, el)
                output_parent.append(el)

        extensions = { ('testns', 'myext') : MyExt() }

        result = tree.xslt(style, extensions=extensions)
        self.assertEqual(self._rootstring(result),
                          _bytes('<MYn="1"><A><MYn="2"><B/></MY></A></MY>'))

    def test_extension_element_raise(self):
        tree = self.parse('<a><b>B</b></a>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:myns="testns"
    extension-element-prefixes="myns"
    exclude-result-prefixes="myns">
  <xsl:template match="a">
    <A><myns:myext>b</myns:myext></A>
  </xsl:template>
</xsl:stylesheet>''')

        class MyError(Exception):
            pass

        class MyExt(etree.XSLTExtension):
            def execute(self, context, self_node, input_node, output_parent):
                raise MyError("expected!")

        extensions = { ('testns', 'myext') : MyExt() }
        self.assertRaises(MyError, tree.xslt, style, extensions=extensions)


class Py3XSLTTestCase(HelperTestCase):
    """XSLT tests for etree under Python 3"""

    pytestmark = skipif('sys.version_info < (3,0)')

    def test_xslt_result_bytes(self):
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
        res = st(tree)
        self.assertEqual(_bytes('''\
<?xml version="1.0"?>
<foo>B</foo>
'''),
                          bytes(res))

    def test_xslt_result_bytearray(self):
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
        res = st(tree)
        self.assertEqual(_bytes('''\
<?xml version="1.0"?>
<foo>B</foo>
'''),
                          bytearray(res))

    def test_xslt_result_memoryview(self):
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
        res = st(tree)
        self.assertEqual(_bytes('''\
<?xml version="1.0"?>
<foo>B</foo>
'''),
                          bytes(memoryview(res)))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeXSLTTestCase)])
    suite.addTests([unittest.makeSuite(ETreeEXSLTTestCase)])
    suite.addTests([unittest.makeSuite(ETreeXSLTExtFuncTestCase)])
    suite.addTests([unittest.makeSuite(ETreeXSLTExtElementTestCase)])
    if is_python3:
        suite.addTests([unittest.makeSuite(Py3XSLTTestCase)])
    suite.addTests(
        [make_doctest('../../../doc/extensions.txt')])
    suite.addTests(
        [make_doctest('../../../doc/xpathxslt.txt')])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
