"""
Tests for thread usage in lxml.etree.
"""


import re
import sys
import unittest
import threading
import warnings
from queue import Queue, Empty

from .common_imports import etree, HelperTestCase, BytesIO, IS_FT_PYTHON, IS_PYPY, needs_feature


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

    @unittest.skipIf(IS_FT_PYTHON, "in freethreading Python")
    def test_freethreading_not_enabled(self):
        self.assertFalse(getattr(etree, '_freethreading_enabled', False))

    @unittest.skipIf(not IS_FT_PYTHON, "not in freethreading Python")
    def test_freethreading_enabled(self):
        self.assertTrue(getattr(etree, '_freethreading_enabled', False))

    def test_subtree_copy_thread(self):
        tostring = self.etree.tostring
        XML = self.etree.XML
        xml = b"<root><threadtag/></root>"
        main_root = XML(b"<root/>")

        def run_thread():
            thread_root = XML(xml)
            main_root.append(thread_root[0])
            del thread_root

        self._run_thread(run_thread)
        self.assertEqual(xml, tostring(main_root))

    def test_concurrent_parser_feed(self):
        parser = self.etree.XMLParser()
        parser.feed("<root>")

        def feed_chunk():
            parser.feed("<node>text</node>")

        self._run_threads(15, feed_chunk)

        parser.feed("</root>")

        root = parser.close()
        self.assertEqual(len(root), 15)
        self.assertListEqual(['node'] * 15, [child.tag for child in root])

    def test_main_xslt_in_thread(self):
        XML = self.etree.XML
        style = XML(b'''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="*">
    <foo><xsl:copy><xsl:value-of select="/a/b/text()" /></xsl:copy></foo>
  </xsl:template>
</xsl:stylesheet>''')
        st = etree.XSLT(style)

        result = []

        def run_thread():
            root = XML(b'<a><b>B</b><c>C</c></a>')
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
        root = XML(b'<a><b>B</b><c>C</c></a>')

        def run_thread():
            style = XML(b'''\
    <xsl:stylesheet version="1.0"
        xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
      <xsl:template match="*">
        <foo><xsl:copy><xsl:value-of select="/a/b/text()" /></xsl:copy></foo>
      </xsl:template>
    </xsl:stylesheet>''')
            st = etree.XSLT(style)
            root.append( st(root).getroot() )

        self._run_thread(run_thread)
        self.assertEqual(b'<a><b>B</b><c>C</c><foo><a>B</a></foo></a>',
                          tostring(root))

    def test_thread_xslt_serialisation(self):
        XML = self.etree.XML
        tostring = self.etree.tostring
        root = XML(b'<a><b>B</b><c>C</c></a>')

        style = XML(b'''\
    <xsl:stylesheet version="1.0"
        xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
      <xsl:template match="b|c">
        <foo><xsl:value-of select="text()" /></foo>
      </xsl:template>
      <xsl:template match="*"><xsl:copy><xsl:apply-templates /></xsl:copy></xsl:template>
    </xsl:stylesheet>''')
        st = etree.XSLT(style)

        result = st(root)
        self.assertEqual(type(result).__name__, "_XSLTResultTree")

        def serialise():
            for i in range(10):
                s = str(result)
                self.assertEqual('<?xml version="1.0"?>\n<a><foo>B</foo><foo>C</foo></a>\n', s)
                b = bytes(result)
                self.assertEqual(b'<?xml version="1.0"?>\n<a><foo>B</foo><foo>C</foo></a>\n', b)
                m = memoryview(result)
                ba = bytearray(m)
                self.assertEqual(bytearray(b'<?xml version="1.0"?>\n<a><foo>B</foo><foo>C</foo></a>\n'), ba)
                mb = bytes(m)
                m = None
                self.assertEqual(b'<?xml version="1.0"?>\n<a><foo>B</foo><foo>C</foo></a>\n', mb)

        self._run_threads(15, serialise)

    def test_thread_xslt_parsing_error_log(self):
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:template match="tag" />
    <!-- extend time for parsing + transform -->
''' + '\n'.join(f'<xsl:template match="tag{i:x}" />' for i in range(200)) + '''
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

        last_log = None
        for log in error_logs:
            self.assertTrue(len(log))
            if last_log is not None:
                self.assertEqual(len(last_log), len(log))
            self.assertTrue(len(log) >= 2, len(log))
            for error in log:
                self.assertIn(':ERROR:XSLT:', str(error), str(error))
            self.assertTrue(any('UnExpectedElement' in str(error) for error in log), log)
            last_log = log

        self.assertEqual(16, len(error_logs))

    def test_thread_xslt_apply_error_log(self):
        tree = self.parse('<tagFF/>')
        style = self.parse('''\
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:template name="tag0">
        <xsl:message terminate="yes">FAIL</xsl:message>
    </xsl:template>
    <!-- extend time for parsing + transform -->
''' + '\n'.join(f'<xsl:template match="tag{i:X}" name="tag{i:x}"> <xsl:call-template name="tag{i-1:x}" /> </xsl:template>'
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
                self.assertIn(':ERROR:XSLT:', str(error))
            last_log = log

    def test_thread_xslt_attr_replace(self):
        # this is the only case in XSLT where the result tree can be
        # modified in-place
        XML = self.etree.XML
        tostring = self.etree.tostring
        style = self.etree.XSLT(XML(b'''\
    <xsl:stylesheet version="1.0"
        xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
      <xsl:template match="*">
        <root class="abc">
          <xsl:copy-of select="@class" />
          <xsl:attribute name="class">xyz</xsl:attribute>
        </root>
      </xsl:template>
    </xsl:stylesheet>'''))

        result = []
        def run_thread():
            root = XML(b'<ROOT class="ABC" />')
            result.append( style(root).getroot() )

        self._run_thread(run_thread)
        self.assertEqual(b'<root class="xyz"/>',
                          tostring(result[0]))

    def test_thread_xslt_extension_waits_for_thread(self):
        # An extension function that waits for stylesheets to be parsed and applied
        # in another thread, e.g. in a thread pool.
        XML = self.etree.XML
        style = b'''\
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="text"/>
  <xsl:template match="/">inner-<xsl:value-of select="name(*)"/></xsl:template>
</xsl:stylesheet>'''
        inner = self.etree.XSLT(XML(style))
        threads = []
        inner_results = []

        def transform_in_thread(context):
            done = threading.Event()

            def run_thread():
                # Parse in this thread: transformations with extension functions lock
                # all documents of the parser of their input document for writing.
                try:
                    inner_results.append(str(inner(XML('<b/>'))))
                    inner_results.append(str(self.etree.XSLT(XML(style))(XML('<c/>'))))
                finally:
                    done.set()

            thread = threading.Thread(target=run_thread)
            threads.append(thread)
            thread.start()
            # The time limit only bounds the time it takes to fail.
            return 'done' if done.wait(60) else 'deadlock'

        transform = self.etree.XSLT(XML(b'''\
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:test="testns">
  <xsl:output method="text"/>
  <xsl:template match="/"><xsl:value-of select="test:transform-in-thread()"/></xsl:template>
</xsl:stylesheet>'''), extensions={('testns', 'transform-in-thread'): transform_in_thread})

        try:
            result = str(transform(XML('<a/>')))
        finally:
            for thread in threads:
                thread.join()
        self.assertEqual('done', result)
        self.assertEqual(['inner-b', 'inner-c'], inner_results)

    def test_thread_xslt_shared_new_names(self):
        # Concurrent runs of one stylesheet that copy names which the stylesheet does not contain.
        XML = self.etree.XML
        identity = self.etree.XSLT(XML(b'''\
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="@*|node()">
    <xsl:copy><xsl:apply-templates select="@*|node()"/></xsl:copy>
  </xsl:template>
</xsl:stylesheet>'''))

        def run_thread():
            thread_id = threading.get_ident()
            for i in range(50):
                names = [f"t{thread_id}i{i}n{k}" for k in range(20)]
                result = identity(XML(
                    '<r>' + ''.join(f'<{name} {name}="v"/>' for name in names) + '</r>'))
                self.assertEqual(names, [el.tag for el in result.getroot()])
                self.assertEqual(names, [el.keys()[0] for el in result.getroot()])

        self._run_threads(8, run_thread)

    def test_thread_create_xslt(self):
        XML = self.etree.XML
        tostring = self.etree.tostring
        root = XML(b'<a><b>B</b><c>C</c></a>')

        stylesheets = []

        def run_thread():
            style = XML(b'''\
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
            stylesheets.append( etree.XSLT(style) )

        self._run_thread(run_thread)

        st = stylesheets[0]
        result = tostring( st(root) )

        self.assertEqual(b'<div id="test">BC</div>',
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

    def _run_while_thread_paused(self, call_in_thread, exception_types, while_paused,
                                 pause_at_error=1):
        # Runs call_in_thread() in a thread, pauses that thread when it reports its
        # 'pause_at_error'-th error, and runs while_paused() in this thread in the meantime.
        # Returns the exception of the call in the thread and the result of while_paused().
        error_reported = threading.Event()
        resume = threading.Event()
        reported = []

        class PauseAtError(self.etree.PyErrorLog):
            # As global error log of the thread, this receives each error before
            # the error log of the called object receives it.
            def receive(self, log_entry):
                reported.append(log_entry)
                if len(reported) == pause_at_error:
                    error_reported.set()
                    resume.wait()

        thread_exceptions = []

        def run_in_thread():
            self.etree.use_global_python_log(PauseAtError())
            try:
                call_in_thread()
            except exception_types as exc:
                thread_exceptions.append(exc)
            finally:
                error_reported.set()

        thread = threading.Thread(target=run_in_thread)
        thread.start()
        try:
            error_reported.wait()
            result = while_paused()
        finally:
            resume.set()
            thread.join()

        self.assertGreaterEqual(len(reported), pause_at_error)
        self.assertEqual(1, len(thread_exceptions))
        return thread_exceptions[0], result

    def _call_while_other_thread_reports(self, call, exception_types):
        # Runs call('in_thread') in a thread, pauses that thread when it reports
        # its first error, and runs call('in_main') in this thread in the meantime.
        # Returns the exceptions of both calls (thread first).
        def call_in_main():
            try:
                call('in_main')
            except exception_types as exc:
                return exc
            return None

        return self._run_while_thread_paused(
            lambda: call('in_thread'), exception_types, call_in_main)

    def _assert_while_other_thread_reports(self, validator, assert_method):
        # Calls 'assert_method' of the validator for invalid documents (see above).
        return self._call_while_other_thread_reports(
            lambda name: getattr(validator, assert_method)(self.etree.XML(f'<{name}/>')),
            (self.etree.DocumentInvalid, AssertionError))

    def _assert_own_validation_errors(self, validator):
        thread_error, main_error = self._assert_while_other_thread_reports(
            validator, 'assertValid')

        for error, own, other in [(thread_error, 'in_thread', 'in_main'),
                                  (main_error, 'in_main', 'in_thread')]:
            self.assertIsInstance(error, self.etree.DocumentInvalid)
            self.assertIn(own, str(error))
            self.assertNotIn(other, str(error))
            messages = [entry.message for entry in error.error_log]
            self.assertTrue(messages)
            for message in messages:
                self.assertIn(own, message)

        # The validation in the thread finished last.
        self.assertEqual(
            [entry.message for entry in thread_error.error_log],
            [entry.message for entry in validator.error_log])

    def test_thread_xmlschema_error_log(self):
        self._assert_own_validation_errors(self.etree.XMLSchema(self.etree.XML(
            '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
            '<xs:element name="a"/></xs:schema>')))

    def test_thread_xmlschema_subclass_error_log(self):
        class XMLSchemaSubclass(self.etree.XMLSchema):
            def __call__(self, etree):
                return super().__call__(etree)

        self._assert_own_validation_errors(XMLSchemaSubclass(self.etree.XML(
            '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
            '<xs:element name="a"/></xs:schema>')))

    def test_thread_xmlschema_assert_(self):
        schema = self.etree.XMLSchema(self.etree.XML(
            '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
            '<xs:element name="a"/></xs:schema>'))
        thread_error, main_error = self._assert_while_other_thread_reports(
            schema, 'assert_')

        self.assertIsInstance(thread_error, AssertionError)
        self.assertIn('in_thread', str(thread_error))
        self.assertNotIn('in_main', str(thread_error))
        self.assertIsInstance(main_error, AssertionError)
        self.assertIn('in_main', str(main_error))
        self.assertNotIn('in_thread', str(main_error))

    def test_thread_relaxng_error_log(self):
        self._assert_own_validation_errors(self.etree.RelaxNG(self.etree.XML(
            '<element name="a" xmlns="http://relaxng.org/ns/structure/1.0">'
            '<empty/></element>')))

    def test_thread_dtd_error_log(self):
        self._assert_own_validation_errors(
            self.etree.DTD(BytesIO(b'<!ELEMENT a EMPTY>')))

    @needs_feature("schematron")
    def test_thread_schematron_error_log(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', DeprecationWarning)
            schematron = self.etree.Schematron(self.etree.XML(
                '<schema xmlns="http://purl.oclc.org/dsdl/schematron"><pattern name="p">'
                '<rule context="/*"><assert test="false()">invalid <name/></assert></rule>'
                '</pattern></schema>'))
        self._assert_own_validation_errors(schematron)

    def test_thread_isoschematron_error_log(self):
        from lxml import isoschematron
        self._assert_own_validation_errors(isoschematron.Schematron(self.etree.XML(
            '<schema xmlns="http://purl.oclc.org/dsdl/schematron"><pattern>'
            '<rule context="/*"><assert test="false()">invalid <value-of select="name()"/></assert></rule>'
            '</pattern></schema>')))

    def test_thread_xslt_error_log(self):
        transform = self.etree.XSLT(self.etree.XML('''\
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/*">
    <xsl:message>processing <xsl:value-of select="name()"/></xsl:message>
    <xsl:message terminate="yes">failed <xsl:value-of select="name()"/></xsl:message>
  </xsl:template>
</xsl:stylesheet>'''))

        def messages(error_log):
            return [entry.message for entry in error_log]

        self.assertRaises(self.etree.XSLTApplyError, transform, self.etree.XML('<in_main/>'))
        self.assertEqual(['processing in_main', 'failed in_main'], messages(transform.error_log))

        # While a transformation runs in another thread, 'error_log' shows the last
        # finished one.
        thread_error, messages_while_running = self._run_while_thread_paused(
            lambda: transform(self.etree.XML('<in_thread/>')),
            self.etree.XSLTApplyError,
            lambda: messages(transform.error_log),
            pause_at_error=2)
        self.assertEqual(['processing in_main', 'failed in_main'], messages_while_running)

        self.assertEqual('failed in_thread', str(thread_error))
        self.assertEqual(['processing in_thread', 'failed in_thread'], messages(thread_error.error_log))
        self.assertEqual(['processing in_thread', 'failed in_thread'], messages(transform.error_log))

    def test_thread_xinclude_error_log(self):
        xinclude = self.etree.XInclude()
        thread_error, main_error = self._call_while_other_thread_reports(
            lambda name: xinclude(self.etree.XML(
                '<doc xmlns:xi="http://www.w3.org/2001/XInclude">'
                f'<xi:include href="lxml-test-missing-{name}.xml"/></doc>')),
            self.etree.XIncludeError)

        for error, own, other in [(thread_error, 'in_thread', 'in_main'),
                                  (main_error, 'in_main', 'in_thread')]:
            self.assertIsInstance(error, self.etree.XIncludeError)
            self.assertIn(own, str(error))
            self.assertNotIn(other, str(error))
            messages = [entry.message for entry in error.error_log]
            self.assertTrue(any(own in message for message in messages), messages)
            self.assertFalse(any(other in message for message in messages), messages)

        # The XInclude processing in the thread finished last.
        self.assertEqual(
            [entry.message for entry in thread_error.error_log],
            [entry.message for entry in xinclude.error_log])

    def test_thread_mix(self):
        XML = self.etree.XML
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        tostring = self.etree.tostring
        xml = b'<a><b>B</b><c xmlns="test">C</c></a>'
        root = XML(xml)
        fragment = XML(b"<other><tags/></other>")

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
            style = XML(b'''\
    <xsl:stylesheet version="1.0"
        xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
      <xsl:template match="*">
        <xsl:copy><foo><xsl:value-of select="/a/b/text()" /></foo></xsl:copy>
      </xsl:template>
    </xsl:stylesheet>''')
            st = etree.XSLT(style)
            result.append( st(root).getroot() )

        for test in (run_XML, run_parse, run_move_main, run_xslt, run_build):
            tostring(result)
            self._run_thread(test)

        self.assertEqual(
            b'<ns0:root xmlns:ns0="myns" att="someval"><b>B</b>'
                   b'<c xmlns="test">C</c><b>B</b><c xmlns="test">C</c><tags/>'
                   b'<a><foo>B</foo></a>'
                   b'<ns0:foo xmlns:ns1="test" ns1:attr="val"/>'
                   b'<ns1:tasty xmlns:ns1="otherns"/></ns0:root>',
            tostring(result))

        def strip_first():
            root = Element("newroot")
            root.append(result[0])

        while len(result):
            self._run_thread(strip_first)

        self.assertEqual(
            b'<ns0:root xmlns:ns0="myns" att="someval"/>',
            tostring(result))

    def test_concurrent_attribute_names_in_dicts(self):
        SubElement = self.etree.SubElement
        names = list('abcdefghijklmnop')
        runs_per_name = range(20)
        result_matches = re.compile(
            br'<thread_root>'
            br'(?:<[a-p]{5} thread_attr_[a-p]="value" thread_attr2_[a-p]="value2"\s?/>)+'
            br'</thread_root>').match

        def testrun():
            for _ in range(3):
                root = self.etree.Element('thread_root')
                for name in names:
                    tag_name = name * 5
                    new = [
                        SubElement(root, tag_name, {'thread_attr_' + name: 'value'})
                        for _ in runs_per_name
                    ]
                    for el in new:
                        el.set('thread_attr2_' + name, 'value2')
                s = etree.tostring(root)
                self.assertTrue(result_matches(s))

        # first, run only in sub-threads
        self._run_threads(10, testrun)

        # then, additionally include the main thread (and its parent dict)
        self._run_threads(10, testrun, main_func=testrun)

    @unittest.skipIf(IS_PYPY, "currently crashes PyPy")
    def test_concurrent_proxies(self):
        XML = self.etree.XML
        root = XML(b'<root><a>A</a><b xmlns="test">B</b><c/></root>')
        child_count = len(root)
        def testrun():
            for i in range(10000):
                el = root[i % child_count]
                del el
        self._run_threads(10, testrun)

    def test_concurrent_class_lookup(self):
        XML = self.etree.XML

        class TestElement(etree.ElementBase):
            pass

        class MyLookup(etree.CustomElementClassLookup):
            repeat = range(100)
            _TestElement = TestElement

            def lookup(self, t, d, ns, name):
                count = 0
                for i in self.repeat:
                    # allow other threads to run
                    count += i
                return self._TestElement if count > 1 else self._TestElement

        parser = self.etree.XMLParser()
        parser.set_element_class_lookup(MyLookup())

        root = XML(b'<root><a>A</a><b xmlns="test">B</b><c/></root>',
                   parser)

        child_count = len(root)
        def testrun():
            for i in range(1000):
                el = root[i % child_count]
                del el
        self._run_threads(10, testrun)


class ThreadPipelineTestCase(HelperTestCase):
    """Threading tests based on a thread worker pipeline.
    """
    etree = etree
    item_count = 40

    class Worker(threading.Thread):
        _print_lock = threading.Lock()
        _DEBUG = False

        def __init__(self, in_queue, in_count, **kwargs):
            threading.Thread.__init__(self)
            self.in_queue = in_queue
            self.in_count = in_count
            self.out_queue = Queue(in_count)
            self._print_counter = 0
            self.__dict__.update(kwargs)

        def _debug_print(self, s):
            if not self._DEBUG:
                return
            with self._print_lock:
                self._print_counter += 1
                print(f"{s}[{self._print_counter}]")

        def run(self):
            get, put = self.in_queue.get, self.out_queue.put
            handle = self.handle
            i = 0
            try:
                for i in range(self.in_count):
                    put(handle(get(timeout=10)))
            except Empty:
                self._debug_print(f"failed({type(self).__name__})")
                raise RuntimeError(f"timeout after {i} items in thread {type(self).__name__}")

            self._debug_print(f"done({type(self).__name__})")

        def handle(self, data):
            raise NotImplementedError()

    class ParseWorker(Worker):
        def handle(self, xml, _fromstring=etree.fromstring):
            self._debug_print("parse")
            return _fromstring(xml)

    class RotateWorker(Worker):
        def handle(self, element):
            self._debug_print("rotate")
            first = element[0]
            element[:] = element[1:]
            element.append(first)
            return element

    class ReverseWorker(Worker):
        def handle(self, element):
            self._debug_print("reverse")
            element[:] = element[::-1]
            return element

    class ParseAndExtendWorker(Worker):
        def handle(self, element, _fromstring=etree.fromstring):
            self._debug_print("parseandextend")
            element.extend(_fromstring(self.xml))
            return element

    class ParseAndInjectWorker(Worker):
        def handle(self, element, _fromstring=etree.fromstring):
            self._debug_print("parseandinject")
            root = _fromstring(self.xml)
            root.extend(element)
            return root

    class Validate(Worker):
        def handle(self, element):
            self._debug_print("validate")
            element.getroottree().docinfo.internalDTD.assertValid(element)
            return element

    class SerialiseWorker(Worker):
        def handle(self, element):
            self._debug_print("serialise")
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
        start.daemon = True
        for worker_class in classes[1:]:
            last = worker_class(last.out_queue, item_count, **kwargs)
            last.daemon = True
            last.start()
        return in_queue, start, last

    @unittest.skipIf(IS_PYPY, "currently crashes PyPy")
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
        put = in_queue.put
        for _ in range(item_count):
            put(xml)

        # start the first thread and thus everything
        start.start()
        # make sure the last thread has terminated
        last.join(60)  # time out after x seconds
        self.assertEqual(item_count, last.out_queue.qsize())
        # read the results
        get = last.out_queue.get
        results = [get(timeout=10) for _ in range(item_count)]

        comparison = results[0]
        for i, result in enumerate(results[1:]):
            self.assertEqual(comparison, result)

    @unittest.skipIf(IS_PYPY, "currently crashes PyPy")
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
        put = in_queue.put
        for _ in range(item_count):
            put(XML(xml))

        # start the first thread and thus everything
        start.start()
        # make sure the last thread has terminated
        last.join(60)  # time out after x seconds
        self.assertEqual(item_count, last.out_queue.qsize())
        # read the results
        get = last.out_queue.get
        results = [get(timeout=10) for _ in range(item_count)]

        comparison = results[0]
        for i, result in enumerate(results[1:]):
            self.assertEqual(comparison, result)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(ThreadingTestCase)])
    suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(ThreadPipelineTestCase)])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
