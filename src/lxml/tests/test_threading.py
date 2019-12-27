# -*- coding: utf-8 -*-

"""
Tests for thread usage in lxml.etree.
"""

from __future__ import absolute_import

import re
import sys
import unittest
import threading

from .common_imports import etree, HelperTestCase, BytesIO, _bytes

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

    def _run_threads(self, count, func, main_func=None):
        sync = threading.Event()
        lock = threading.Lock()
        counter = dict(started=0, finished=0, failed=0)

        def sync_start(func):
            with lock:
                started = counter['started'] + 1
                counter['started'] = started
            if started < count + (main_func is not None):
                sync.wait(4)  # wait until the other threads have started up
                assert sync.is_set()
            sync.set()  # all waiting => go!
            try:
                func()
            except:
                with lock:
                    counter['failed'] += 1
                raise
            else:
                with lock:
                    counter['finished'] += 1

        threads = [threading.Thread(target=sync_start, args=(func,)) for _ in range(count)]
        for thread in threads:
            thread.start()
        if main_func is not None:
            sync_start(main_func)
        for thread in threads:
            thread.join()

        self.assertEqual(0, counter['failed'])
        self.assertEqual(counter['finished'], counter['started'])

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

    def test_thread_xslt_parsing_error_log(self):
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:template match="tag" />
    <!-- extend time for parsing + transform -->
''' + '\n'.join('<xsl:template match="tag%x" />' % i for i in range(200)) + '''
    <xsl:UnExpectedElement />
</xsl:stylesheet>''')
        self.assertRaises(etree.XSLTParseError,
                          etree.XSLT, style)

        error_logs = []

        def run_thread():
            try:
                etree.XSLT(style)
            except etree.XSLTParseError as e:
                error_logs.append(e.error_log)
            else:
                self.assertFalse(True, "XSLT parsing should have failed but didn't")

        self._run_threads(16, run_thread)

        self.assertEqual(16, len(error_logs))
        last_log = None
        for log in error_logs:
            self.assertTrue(len(log))
            if last_log is not None:
                self.assertEqual(len(last_log), len(log))
            self.assertTrue(len(log) >= 2, len(log))
            for error in log:
                self.assertTrue(':ERROR:XSLT:' in str(error), str(error))
            self.assertTrue(any('UnExpectedElement' in str(error) for error in log), log)
            last_log = log

    def test_thread_xslt_apply_error_log(self):
        tree = self.parse('<tagFF/>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:template name="tag0">
        <xsl:message terminate="yes">FAIL</xsl:message>
    </xsl:template>
    <!-- extend time for parsing + transform -->
''' + '\n'.join('<xsl:template match="tag%X" name="tag%x"> <xsl:call-template name="tag%x" /> </xsl:template>' % (i, i, i-1)
                for i in range(1, 256)) + '''
</xsl:stylesheet>''')
        self.assertRaises(etree.XSLTApplyError,
                          etree.XSLT(style), tree)

        error_logs = []

        def run_thread():
            transform = etree.XSLT(style)
            try:
                transform(tree)
            except etree.XSLTApplyError:
                error_logs.append(transform.error_log)
            else:
                self.assertFalse(True, "XSLT parsing should have failed but didn't")

        self._run_threads(16, run_thread)

        self.assertEqual(16, len(error_logs))
        last_log = None
        for log in error_logs:
            self.assertTrue(len(log))
            if last_log is not None:
                self.assertEqual(len(last_log), len(log))
            self.assertEqual(1, len(log))
            for error in log:
                self.assertTrue(':ERROR:XSLT:' in str(error))
            last_log = log

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

    def test_concurrent_attribute_names_in_dicts(self):
        SubElement = self.etree.SubElement
        names = list('abcdefghijklmnop')
        runs_per_name = range(50)
        result_matches = re.compile(
            br'<thread_root>'
            br'(?:<[a-p]{5} thread_attr_[a-p]="value" thread_attr2_[a-p]="value2"\s?/>)+'
            br'</thread_root>').match

        def testrun():
            for _ in range(3):
                root = self.etree.Element('thread_root')
                for name in names:
                    tag_name = name * 5
                    new = []
                    for _ in runs_per_name:
                        el = SubElement(root, tag_name, {'thread_attr_' + name: 'value'})
                        new.append(el)
                    for el in new:
                        el.set('thread_attr2_' + name, 'value2')
                s = etree.tostring(root)
                self.assertTrue(result_matches(s))

        # first, run only in sub-threads
        self._run_threads(10, testrun)

        # then, additionally include the main thread (and its parent dict)
        self._run_threads(10, testrun, main_func=testrun)

    def test_concurrent_proxies(self):
        XML = self.etree.XML
        root = XML(_bytes('<root><a>A</a><b xmlns="test">B</b><c/></root>'))
        child_count = len(root)
        def testrun():
            for i in range(10000):
                el = root[i%child_count]
                del el
        self._run_threads(10, testrun)

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
        self._run_threads(10, testrun)


class ThreadPipelineTestCase(HelperTestCase):
    """Threading tests based on a thread worker pipeline.
    """
    etree = etree
    item_count = 40

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

        def handle(self, data):
            raise NotImplementedError()

    class ParseWorker(Worker):
        def handle(self, xml, _fromstring=etree.fromstring):
            return _fromstring(xml)

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
        def handle(self, element, _fromstring=etree.fromstring):
            element.extend(_fromstring(self.xml))
            return element

    class ParseAndInjectWorker(Worker):
        def handle(self, element, _fromstring=etree.fromstring):
            root = _fromstring(self.xml)
            root.extend(element)
            return root

    class Validate(Worker):
        def handle(self, element):
            element.getroottree().docinfo.internalDTD.assertValid(element)
            return element

    class SerialiseWorker(Worker):
        def handle(self, element):
            return etree.tostring(element)

    xml = (b'''\
<!DOCTYPE threadtest [
    <!ELEMENT threadtest (thread-tag1,thread-tag2)+>
    <!ATTLIST threadtest
        version    CDATA  "1.0"
    >
    <!ELEMENT thread-tag1 EMPTY>
    <!ELEMENT thread-tag2 (div)>
    <!ELEMENT div (threaded)>
    <!ATTLIST div
        huhu  CDATA  #IMPLIED
    >
    <!ELEMENT threaded EMPTY>
    <!ATTLIST threaded
        host  CDATA  #REQUIRED
    >
]>
<threadtest version="123">
''' + (b'''
  <thread-tag1 />
  <thread-tag2>
    <div huhu="true">
       <threaded host="here" />
    </div>
  </thread-tag2>
''') * 20 + b'''
</threadtest>''')

    def _build_pipeline(self, item_count, *classes, **kwargs):
        in_queue = Queue(item_count)
        start = last = classes[0](in_queue, item_count, **kwargs)
        start.setDaemon(True)
        for worker_class in classes[1:]:
            last = worker_class(last.out_queue, item_count, **kwargs)
            last.setDaemon(True)
            last.start()
        return in_queue, start, last

    def test_thread_pipeline_thread_parse(self):
        item_count = self.item_count
        xml = self.xml.replace(b'thread', b'THREAD')  # use fresh tag names

        # build and start the pipeline
        in_queue, start, last = self._build_pipeline(
            item_count,
            self.ParseWorker,
            self.RotateWorker,
            self.ReverseWorker,
            self.ParseAndExtendWorker,
            self.Validate,
            self.ParseAndInjectWorker,
            self.SerialiseWorker,
            xml=xml)

        # fill the queue
        put = start.in_queue.put
        for _ in range(item_count):
            put(xml)

        # start the first thread and thus everything
        start.start()
        # make sure the last thread has terminated
        last.join(60)  # time out after 60 seconds
        self.assertEqual(item_count, last.out_queue.qsize())
        # read the results
        get = last.out_queue.get
        results = [get() for _ in range(item_count)]

        comparison = results[0]
        for i, result in enumerate(results[1:]):
            self.assertEqual(comparison, result)

    def test_thread_pipeline_global_parse(self):
        item_count = self.item_count
        xml = self.xml.replace(b'thread', b'GLOBAL')  # use fresh tag names
        XML = self.etree.XML
        # build and start the pipeline
        in_queue, start, last = self._build_pipeline(
            item_count,
            self.RotateWorker,
            self.ReverseWorker,
            self.ParseAndExtendWorker,
            self.Validate,
            self.SerialiseWorker,
            xml=xml)

        # fill the queue
        put = start.in_queue.put
        for _ in range(item_count):
            put(XML(xml))

        # start the first thread and thus everything
        start.start()
        # make sure the last thread has terminated
        last.join(60)  # time out after 90 seconds
        self.assertEqual(item_count, last.out_queue.qsize())
        # read the results
        get = last.out_queue.get
        results = [get() for _ in range(item_count)]

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
