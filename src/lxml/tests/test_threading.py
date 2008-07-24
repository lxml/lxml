# -*- coding: utf-8 -*-

"""
Tests for thread usage in lxml.etree.
"""

import unittest, threading, sys, os.path

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

from common_imports import etree, HelperTestCase, BytesIO, _bytes

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
        xml = _bytes("<root><threadtag/></root>")
        main_root = XML(_bytes("<root/>"))

        def run_thread():
            thread_root = XML(xml)
            main_root.append(thread_root[0])
            del thread_root

        self._run_thread(run_thread)
        self.assertEquals(xml, tostring(main_root))

    def test_main_xslt_in_thread(self):
        XML = self.etree.XML
        style = XML(_bytes('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="*">
    <foo><xsl:copy><xsl:value-of select="/a/b/text()" /></xsl:copy></foo>
  </xsl:template>
</xsl:stylesheet>'''))
        st = etree.XSLT(style)

        result = []

        def run_thread():
            root = XML(_bytes('<a><b>B</b><c>C</c></a>'))
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
        root = XML(_bytes('<a><b>B</b><c>C</c></a>'))

        def run_thread():
            style = XML(_bytes('''\
    <xsl:stylesheet version="1.0"
        xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
      <xsl:template match="*">
        <foo><xsl:copy><xsl:value-of select="/a/b/text()" /></xsl:copy></foo>
      </xsl:template>
    </xsl:stylesheet>'''))
            st = etree.XSLT(style)
            root.append( st(root).getroot() )

        self._run_thread(run_thread)
        self.assertEquals(_bytes('<a><b>B</b><c>C</c><foo><a>B</a></foo></a>'),
                          tostring(root))

    def test_thread_create_xslt(self):
        XML = self.etree.XML
        tostring = self.etree.tostring
        root = XML(_bytes('<a><b>B</b><c>C</c></a>'))

        stylesheets = []

        def run_thread():
            style = XML(_bytes('''\
    <xsl:stylesheet
        xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
        version="1.0">
      <xsl:output method="xml" />
      <xsl:template match="/">
         <div id="test">
           <xsl:apply-templates/>
         </div>
      </xsl:template>
    </xsl:stylesheet>'''))
            stylesheets.append( etree.XSLT(style) )

        self._run_thread(run_thread)

        st = stylesheets[0]
        result = tostring( st(root) )

        self.assertEquals(_bytes('<div id="test">BC</div>'),
                          result)

    def test_thread_mix(self):
        XML = self.etree.XML
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        tostring = self.etree.tostring
        xml = _bytes('<a><b>B</b><c xmlns="test">C</c></a>')
        root = XML(xml)
        fragment = XML(_bytes("<other><tags/></other>"))

        result = self.etree.Element("{myns}root", att = "someval")

        def run_XML():
            thread_root = XML(xml)
            result.append(thread_root[0])
            result.append(thread_root[-1])

        def run_parse():
            thread_root = self.etree.parse(BytesIO(xml)).getroot()
            result.append(thread_root[0])
            result.append(thread_root[-1])

        def run_move_main():
            result.append(fragment[0])

        def run_build():
            result.append(
                Element("{myns}foo", attrib={'{test}attr':'val'}))
            SubElement(result, "{otherns}tasty")

        def run_xslt():
            style = XML(_bytes('''\
    <xsl:stylesheet version="1.0"
        xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
      <xsl:template match="*">
        <foo><xsl:copy><xsl:value-of select="/a/b/text()" /></xsl:copy></foo>
      </xsl:template>
    </xsl:stylesheet>'''))
            st = etree.XSLT(style)
            result.append( st(root).getroot()[0] )

        for test in (run_XML, run_parse, run_move_main, run_xslt):
            tostring(result)
            self._run_thread(test)

        self.assertEquals(
            _bytes('<ns0:root xmlns:ns0="myns" att="someval"><b>B</b><c xmlns="test">C</c><b>B</b><c xmlns="test">C</c><tags/><a>B</a></ns0:root>'),
            tostring(result))

        def strip_first():
            root = Element("newroot")
            root.append(result[0])

        while len(result):
            self._run_thread(strip_first)

        self.assertEquals(
            _bytes('<ns0:root xmlns:ns0="myns" att="someval"/>'),
            tostring(result))

    def test_concurrent_proxies(self):
        XML = self.etree.XML
        root = XML(_bytes('<root><a>A</a><b xmlns="test">B</b><c/></root>'))
        child_count = len(root)
        def testrun():
            for i in range(10000):
                el = root[i%child_count]
                del el
        threads = [ threading.Thread(target=testrun)
                    for _ in range(10) ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    def test_concurrent_class_lookup(self):
        XML = self.etree.XML

        class TestElement(etree.ElementBase):
            pass

        class MyLookup(etree.CustomElementClassLookup):
            repeat = range(100)
            def lookup(self, t, d, ns, name):
                count = 0
                for i in self.repeat:
                    # allow other threads to run
                    count += 1
                return TestElement

        parser = self.etree.XMLParser()
        parser.set_element_class_lookup(MyLookup())

        root = XML(_bytes('<root><a>A</a><b xmlns="test">B</b><c/></root>'),
                   parser)

        child_count = len(root)
        def testrun():
            for i in range(1000):
                el = root[i%child_count]
                del el
        threads = [ threading.Thread(target=testrun)
                    for _ in range(10) ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ThreadingTestCase)])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
