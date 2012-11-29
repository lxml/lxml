# -*- coding: utf-8 -*-

"""
Tests for thread usage in lxml.etree.
"""

import unittest, threading, sys, os.path

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

from common_imports import etree, HelperTestCase, BytesIO, _bytes

try:
    from Queue import Queue
except ImportError:
    from queue import Queue # Py3

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
        self.assertEqual(xml, tostring(main_root))

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
        self.assertEqual('''\
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
        self.assertEqual(_bytes('<a><b>B</b><c>C</c><foo><a>B</a></foo></a>'),
                          tostring(root))

    def test_thread_xslt_attr_replace(self):
        # this is the only case in XSLT where the result tree can be
        # modified in-place
        XML = self.etree.XML
        tostring = self.etree.tostring
        style = self.etree.XSLT(XML(_bytes('''\
    <xsl:stylesheet version="1.0"
        xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
      <xsl:template match="*">
        <root class="abc">
          <xsl:copy-of select="@class" />
          <xsl:attribute name="class">xyz</xsl:attribute> 
        </root>
      </xsl:template>
    </xsl:stylesheet>''')))

        result = []
        def run_thread():
            root = XML(_bytes('<ROOT class="ABC" />'))
            result.append( style(root).getroot() )

        self._run_thread(run_thread)
        self.assertEqual(_bytes('<root class="xyz"/>'),
                          tostring(result[0]))

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

        self.assertEqual(_bytes('<div id="test">BC</div>'),
                          result)

    def test_thread_error_log(self):
        XML = self.etree.XML
        ParseError = self.etree.ParseError
        expected_error = [self.etree.ErrorTypes.ERR_TAG_NAME_MISMATCH]
        children = "<a>test</a>" * 100

        def parse_error_test(thread_no):
            tag = "tag%d" % thread_no
            xml = "<%s>%s</%s>" % (tag, children, tag.upper())
            parser = self.etree.XMLParser()
            for _ in range(10):
                errors = None
                try:
                    XML(xml, parser)
                except self.etree.ParseError:
                    e = sys.exc_info()[1]
                    errors = e.error_log.filter_types(expected_error)
                self.assertTrue(errors, "Expected error not found")
                for error in errors:
                    self.assertTrue(
                        tag in error.message and tag.upper() in error.message,
                        "%s and %s not found in '%s'" % (
                        tag, tag.upper(), error.message))

        self.etree.clear_error_log()
        threads = []
        for thread_no in range(1, 10):
            t = threading.Thread(target=parse_error_test,
                                 args=(thread_no,))
            threads.append(t)
            t.start()

        parse_error_test(0)

        for t in threads:
            t.join()

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
        <xsl:copy><foo><xsl:value-of select="/a/b/text()" /></foo></xsl:copy>
      </xsl:template>
    </xsl:stylesheet>'''))
            st = etree.XSLT(style)
            result.append( st(root).getroot() )

        for test in (run_XML, run_parse, run_move_main, run_xslt, run_build):
            tostring(result)
            self._run_thread(test)

        self.assertEqual(
            _bytes('<ns0:root xmlns:ns0="myns" att="someval"><b>B</b>'
                   '<c xmlns="test">C</c><b>B</b><c xmlns="test">C</c><tags/>'
                   '<a><foo>B</foo></a>'
                   '<ns0:foo xmlns:ns1="test" ns1:attr="val"/>'
                   '<ns1:tasty xmlns:ns1="otherns"/></ns0:root>'),
            tostring(result))

        def strip_first():
            root = Element("newroot")
            root.append(result[0])

        while len(result):
            self._run_thread(strip_first)

        self.assertEqual(
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


class ThreadPipelineTestCase(HelperTestCase):
    """Threading tests based on a thread worker pipeline.
    """
    etree = etree
    item_count = 20

    class Worker(threading.Thread):
        def __init__(self, in_queue, in_count, **kwargs):
            threading.Thread.__init__(self)
            self.in_queue = in_queue
            self.in_count = in_count
            self.out_queue = Queue(in_count)
            self.__dict__.update(kwargs)
        def run(self):
            get, put = self.in_queue.get, self.out_queue.put
            handle = self.handle
            for _ in range(self.in_count):
                put(handle(get()))

    class ParseWorker(Worker):
        XML = etree.XML
        def handle(self, xml):
            return self.XML(xml)
    class RotateWorker(Worker):
        def handle(self, element):
            first = element[0]
            element[:] = element[1:]
            element.append(first)
            return element
    class ReverseWorker(Worker):
        def handle(self, element):
            element[:] = element[::-1]
            return element
    class ParseAndExtendWorker(Worker):
        XML = etree.XML
        def handle(self, element):
            element.extend(self.XML(self.xml))
            return element
    class SerialiseWorker(Worker):
        def handle(self, element):
            return etree.tostring(element)

    xml = _bytes('''\
<xsl:stylesheet
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    version="1.0">
  <xsl:output method="xml" />
  <xsl:template match="/">
     <div id="test">
       <xsl:apply-templates/>
     </div>
  </xsl:template>
</xsl:stylesheet>''')

    def _build_pipeline(self, item_count, *classes, **kwargs):
        in_queue = Queue(item_count)
        start = last = classes[0](in_queue, item_count, **kwargs)
        start.setDaemon(True)
        for worker_class in classes[1:]:
            last = worker_class(last.out_queue, item_count, **kwargs)
            last.setDaemon(True)
            last.start()
        return (in_queue, start, last)

    def test_thread_pipeline_thread_parse(self):
        item_count = self.item_count
        # build and start the pipeline
        in_queue, start, last = self._build_pipeline(
            item_count,
            self.ParseWorker,
            self.RotateWorker,
            self.ReverseWorker,
            self.ParseAndExtendWorker,
            self.SerialiseWorker,
            xml = self.xml)

        # fill the queue
        put = start.in_queue.put
        for _ in range(item_count):
            put(self.xml)

        # start the first thread and thus everything
        start.start()
        # make sure the last thread has terminated
        last.join(60) # time out after 60 seconds
        self.assertEqual(item_count, last.out_queue.qsize())
        # read the results
        get = last.out_queue.get
        results = [ get() for _ in range(item_count) ]

        comparison = results[0]
        for i, result in enumerate(results[1:]):
            self.assertEqual(comparison, result)

    def test_thread_pipeline_global_parse(self):
        item_count = self.item_count
        XML = self.etree.XML
        # build and start the pipeline
        in_queue, start, last = self._build_pipeline(
            item_count,
            self.RotateWorker,
            self.ReverseWorker,
            self.ParseAndExtendWorker,
            self.SerialiseWorker,
            xml = self.xml)

        # fill the queue
        put = start.in_queue.put
        for _ in range(item_count):
            put(XML(self.xml))

        # start the first thread and thus everything
        start.start()
        # make sure the last thread has terminated
        last.join(60) # time out after 90 seconds
        self.assertEqual(item_count, last.out_queue.qsize())
        # read the results
        get = last.out_queue.get
        results = [ get() for _ in range(item_count) ]

        comparison = results[0]
        for i, result in enumerate(results[1:]):
            self.assertEqual(comparison, result)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ThreadingTestCase)])
    suite.addTests([unittest.makeSuite(ThreadPipelineTestCase)])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
