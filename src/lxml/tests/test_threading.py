# -*- coding: utf-8 -*-

"""
Tests for thread usage in lxml.etree.
"""

import unittest, threading

from common_imports import etree, HelperTestCase, StringIO

class ThreadingTestCase(HelperTestCase):
    """Threading tests"""
    etree = etree

    def _run_thread(self, func):
        thread = threading.Thread(target=func)
        thread.start()
        thread.join()

    def test_subtree_copy_thread(self):
        tostring = self.etree.tostring
        XML = self.etree.XML
        xml = "<root><threadtag/></root>"
        main_root = XML("<root/>")

        def run_thread():
            thread_root = XML(xml)
            main_root.append(thread_root[0])
            del thread_root

        self._run_thread(run_thread)
        self.assertEquals(xml, tostring(main_root))

    def test_main_xslt_in_thread(self):
        XML = self.etree.XML
        style = XML('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="*">
    <foo><xsl:copy><xsl:value-of select="/a/b/text()" /></xsl:copy></foo>
  </xsl:template>
</xsl:stylesheet>''')
        st = etree.XSLT(style)

        result = []

        def run_thread():
            root = XML('<a><b>B</b><c>C</c></a>')
            result.append( st(root) )

        self._run_thread(run_thread)
        self.assertEquals('''\
<?xml version="1.0"?>
<foo><a>B</a></foo>
''',
                          str(result[0]))

    def test_thread_xslt(self):
        XML = self.etree.XML
        tostring = self.etree.tostring
        root = XML('<a><b>B</b><c>C</c></a>')

        def run_thread():
            style = XML('''\
    <xsl:stylesheet version="1.0"
        xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
      <xsl:template match="*">
        <foo><xsl:copy><xsl:value-of select="/a/b/text()" /></xsl:copy></foo>
      </xsl:template>
    </xsl:stylesheet>''')
            st = etree.XSLT(style)
            root.append( st(root).getroot() )

        self._run_thread(run_thread)
        self.assertEquals('<a><b>B</b><c>C</c><foo><a>B</a></foo></a>',
                          tostring(root))

    def test_thread_mix(self):
        XML = self.etree.XML
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        tostring = self.etree.tostring
        xml = '<a><b>B</b><c xmlns="test">C</c></a>'
        root = XML(xml)
        fragment = XML("<other><tags/></other>")

        result = self.etree.Element("{myns}root", att = "someval")

        def run_XML():
            thread_root = XML(xml)
            result.append(thread_root[0])
            result.append(thread_root[-1])

        def run_parse():
            thread_root = self.etree.parse(StringIO(xml)).getroot()
            result.append(thread_root[0])
            result.append(thread_root[-1])

        def run_move_main():
            result.append(fragment[0])

        def run_build():
            result.append(
                Element("{myns}foo", attrib={'{test}attr':'val'}))
            SubElement(result, "{otherns}tasty")

        def run_xslt():
            style = XML('''\
    <xsl:stylesheet version="1.0"
        xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
      <xsl:template match="*">
        <foo><xsl:copy><xsl:value-of select="/a/b/text()" /></xsl:copy></foo>
      </xsl:template>
    </xsl:stylesheet>''')
            st = etree.XSLT(style)
            result.append( st(root).getroot()[0] )

        for test in (run_XML, run_parse, run_move_main, run_xslt):
            tostring(result)
            self._run_thread(test)

        self.assertEquals(
            '<ns0:root xmlns:ns0="myns" att="someval"><b>B</b><c xmlns="test">C</c><b>B</b><c xmlns="test">C</c><tags/><a>B</a></ns0:root>',
            tostring(result))

        def strip_first():
            root = Element("newroot")
            root.append(result[0])

        while len(result):
            self._run_thread(strip_first)

        self.assertEquals(
            '<ns0:root xmlns:ns0="myns" att="someval"/>',
            tostring(result))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ThreadingTestCase)])
    return suite

if __name__ == '__main__':
    print 'to test use test.py %s' % __file__
