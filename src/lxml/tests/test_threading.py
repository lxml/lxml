"""
Tests for thread usage in lxml.etree.
"""


import re
import sys
import unittest
import threading
from queue import Queue, Empty

from .common_imports import etree, HelperTestCase, BytesIO, IS_FT_PYTHON, IS_PYPY


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

    def test_thread_xslt_extension_waits_for_reader(self):
        # An extension function that waits for another thread that reads a document of the
        # parser of the input document (here: the default parser of this thread).
        XML = self.etree.XML
        other = XML('<other><child/></other>')
        threads = []

        def read_in_thread(context):
            result = []
            thread = threading.Thread(target=lambda: result.append(other[0].tag))
            threads.append(thread)
            thread.start()
            # The time limit only bounds the time it takes to fail.
            thread.join(60)
            return result[0] if result else 'deadlock'

        transform = self.etree.XSLT(XML(b'''\
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:test="testns">
  <xsl:output method="text"/>
  <xsl:template match="/"><xsl:value-of select="test:read-in-thread()"/></xsl:template>
</xsl:stylesheet>'''), extensions={('testns', 'read-in-thread'): read_in_thread})

        try:
            result = str(transform(XML('<a/>')))
        finally:
            for thread in threads:
                thread.join()
        self.assertEqual('child', result)

    def test_thread_xslt_extension_element_waits_for_reader(self):
        # Like an extension function, an extension element waits for another thread that reads
        # a document of the parser of the input document.
        etree = self.etree
        other = etree.XML('<other><child/></other>')
        threads = []

        class ReadInThread(etree.XSLTExtension):
            def execute(self, context, self_node, input_node, output_parent):
                result = []
                thread = threading.Thread(target=lambda: result.append(other[0].tag))
                threads.append(thread)
                thread.start()
                # The time limit only bounds the time it takes to fail.
                thread.join(60)
                output_parent.append(etree.Element(result[0] if result else 'deadlock'))

        transform = etree.XSLT(etree.XML(b'''\
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:test="testns" extension-element-prefixes="test">
  <xsl:template match="/"><out><test:read-in-thread/></out></xsl:template>
</xsl:stylesheet>'''), extensions={('testns', 'read-in-thread'): ReadInThread()})

        try:
            result = transform(etree.XML('<a/>'))
        finally:
            for thread in threads:
                thread.join()
        self.assertEqual(['child'], [el.tag for el in result.getroot()])

    def test_thread_xslt_resolver_waits_for_reader(self):
        # A resolver that waits for another thread that reads a document of the parser of the
        # input document.
        etree = self.etree
        other = etree.XML('<other><child/></other>')
        threads = []

        class ReadInThread(etree.Resolver):
            def resolve(self, url, pubid, context):
                result = []
                thread = threading.Thread(target=lambda: result.append(other[0].tag))
                threads.append(thread)
                thread.start()
                # The time limit only bounds the time it takes to fail.
                thread.join(60)
                return self.resolve_string(f'<{result[0] if result else "deadlock"}/>', context)

        parser = etree.XMLParser()
        parser.resolvers.add(ReadInThread())
        transform = etree.XSLT(etree.XML(b'''\
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="text"/>
  <xsl:template match="/"><xsl:value-of select="name(document('doc.xml')/*)"/></xsl:template>
</xsl:stylesheet>''', parser))

        try:
            result = str(transform(etree.XML('<a/>')))
        finally:
            for thread in threads:
                thread.join()
        self.assertEqual('child', result)

    def test_thread_xslt_extension_waits_for_relaxng_validations(self):
        # An extension function that waits for other threads that validate the input document
        # with RelaxNG at the same time, which must not change the ids of generate-id() that
        # libxslt keeps in the nodes of the input document.
        etree = self.etree
        root = etree.XML('<r>' + '<a><b/></a>' * 500 + '</r>')
        relaxng = etree.RelaxNG(etree.XML('''\
<element name="r" xmlns="http://relaxng.org/ns/structure/1.0">
  <zeroOrMore><element name="a"><element name="b"><empty/></element></element></zeroOrMore>
</element>'''))
        thread_count = 4
        threads = []

        def validate_in_threads(context):
            start = threading.Barrier(thread_count)
            results = []

            def validate():
                start.wait(60)
                results.append(all([relaxng.validate(root) for _ in range(20)]))

            validators = [threading.Thread(target=validate) for _ in range(thread_count)]
            threads.extend(validators)
            for thread in validators:
                thread.start()
            for thread in validators:
                # The time limit only bounds the time it takes to fail.
                thread.join(60)
            return str(results == [True] * thread_count)

        transform = etree.XSLT(etree.XML(b'''\
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:test="testns">
  <xsl:template match="/">
    <out>
      <xsl:for-each select="//*"><id><xsl:value-of select="generate-id()"/></id></xsl:for-each>
      <valid><xsl:value-of select="test:validate-in-threads()"/></valid>
      <xsl:for-each select="//*"><id><xsl:value-of select="generate-id()"/></id></xsl:for-each>
    </out>
  </xsl:template>
</xsl:stylesheet>'''), extensions={('testns', 'validate-in-threads'): validate_in_threads})

        try:
            # (Races between the validations show up more reliably in several runs.)
            for _ in range(5):
                result = transform(root).getroot()
                self.assertEqual('True', result.findtext('valid'))
                ids = [id_element.text for id_element in result.iterfind('id')]
                self.assertEqual(1001, len(set(ids[:1001])))
                self.assertEqual(ids[:1001], ids[1001:])
        finally:
            for thread in threads:
                thread.join()

    def test_thread_xslt_extensions_concurrent_readers(self):
        # Transformations with extension functions let other threads read their input documents
        # while the extension functions run, but not while libxslt changes the input documents
        # (it unlinks the DOCTYPE, numbers the elements for sorting nodes in document order and
        # keeps the ids of generate-id() in the nodes).
        XML = self.etree.XML
        tostring = self.etree.tostring
        style = self.etree.XSLT(XML(b'''\
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:test="testns">
  <xsl:template match="/">
    <out><xsl:value-of select="test:count(//b | //a)"/>
      <xsl:for-each select="//a"><id><xsl:value-of select="generate-id()"/></id></xsl:for-each>
    </out>
  </xsl:template>
</xsl:stylesheet>'''), extensions={('testns', 'count'): lambda context, nodes: len(nodes)})

        def make_doc():
            return self.etree.ElementTree(XML(
                '<?pi x?><!DOCTYPE r [<!ELEMENT r ANY>]><r>' + '<a><b/></a>' * 10 + '</r>'))

        transformed = make_doc()
        style(transformed)
        serialised = {tostring(make_doc()), tostring(transformed)}
        docs = [make_doc() for _ in range(10)]
        done = threading.Event()

        def read():
            while not done.is_set():
                for doc in docs:
                    self.assertEqual(['a', 'b'] * 10, [el.tag for el in doc.xpath('//b | //a')])
                    self.assertIn(tostring(doc), serialised)

        def transform():
            try:
                for _ in range(5):
                    for doc in docs:
                        out = style(doc).getroot()
                        self.assertEqual('20', out.text)
                        self.assertEqual(10, len({id_element.text for id_element in out}))
            finally:
                done.set()

        self._run_threads(4, read, main_func=transform)

    def _run_xslt_modifying_with_writers(self, make_stylesheet):
        # Transformations whose Python extensions modify a document of the parser of their input
        # documents while other threads keep waiting to modify it.
        XML = self.etree.XML
        other = XML('<other n="0"/>')
        docs = [XML('<a/>') for _ in range(20)]  # same parser (and lock) as 'other'
        done = threading.Event()

        def modify():
            other.set('n', str(int(other.get('n')) + 1))

        style = make_stylesheet(modify)

        def write():
            while not done.is_set():
                other.set('w', 'x')

        def transform():
            try:
                for doc in docs:
                    self.assertEqual('out', style(doc).getroot().tag)
            finally:
                done.set()

        self._run_threads(2, write, main_func=transform)
        self.assertEqual('20', other.get('n'))

    def test_thread_xslt_extension_element_modifies_with_writers(self):
        etree = self.etree

        def make_stylesheet(modify):
            class Modify(etree.XSLTExtension):
                def execute(self, context, self_node, input_node, output_parent):
                    modify()

            return etree.XSLT(etree.XML(b'''\
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:ext="testns" extension-element-prefixes="ext">
  <xsl:template match="/"><out><ext:modify/></out></xsl:template>
</xsl:stylesheet>'''), regexp=False, extensions={('testns', 'modify'): Modify()})

        self._run_xslt_modifying_with_writers(make_stylesheet)

    def test_thread_xslt_global_function_modifies_with_writers(self):
        etree = self.etree
        namespace = etree.FunctionNamespace('testns-global-modify')

        def make_stylesheet(modify):
            namespace['modify'] = lambda context: modify() or 'ok'
            return etree.XSLT(etree.XML(b'''\
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:g="testns-global-modify">
  <xsl:template match="/"><out><xsl:value-of select="g:modify()"/></out></xsl:template>
</xsl:stylesheet>'''), regexp=False)

        try:
            self._run_xslt_modifying_with_writers(make_stylesheet)
        finally:
            del namespace['modify']

    def test_thread_xslt_extension_with_waiting_writer(self):
        # Another thread starts to wait for the lock of the input's parser while an extension
        # function runs.  Its wait must let the extension function return, also where lxml
        # does not release the GIL around calls into libxml2 and libxslt (PyPy).
        XML = self.etree.XML
        other = XML('<other/>')  # same parser (and lock) as the input document
        writer_started = threading.Event()
        threads = []

        def write():
            writer_started.set()
            other.set('written', 'yes')  # waits for the transformation

        def start_writer(context):
            thread = threading.Thread(target=write)
            threads.append(thread)
            thread.start()
            writer_started.wait()
            return 'ok'

        transform = self.etree.XSLT(XML(b'''\
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:test="testns">
  <xsl:output method="text"/>
  <xsl:template match="/"><xsl:value-of select="test:start-writer()"/></xsl:template>
</xsl:stylesheet>'''), extensions={('testns', 'start-writer'): start_writer})

        try:
            result = str(transform(XML('<a/>')))
        finally:
            for thread in threads:
                thread.join()
        self.assertEqual('ok', result)
        self.assertEqual('yes', other.get('written'))

    def test_thread_xpath_extension_with_waiting_reader(self):
        # Same for a thread that starts to wait for the document while an XPath extension
        # function runs, which holds the write lock of the document.
        root = self.etree.XML('<root><child/></root>')
        reader_started = threading.Event()
        threads = []
        result = []

        def read():
            reader_started.set()
            result.append(root[0].tag)  # waits for the XPath evaluation

        def start_reader(context):
            thread = threading.Thread(target=read)
            threads.append(thread)
            thread.start()
            reader_started.wait()
            return 'ok'

        try:
            self.assertEqual('ok', root.xpath(
                'test:start-reader()', namespaces={'test': 'testns'},
                extensions={('testns', 'start-reader'): start_reader}))
        finally:
            for thread in threads:
                thread.join()
        self.assertEqual(['child'], result)

    def test_thread_write_after_xpath_extension_with_waiting_readers(self):
        # Two threads start to wait for the document while an XPath extension function runs.
        # The evaluating thread modifies the document right afterwards, before both readers
        # could continue, and waits for them, which must let them run (PyPy).
        root = self.etree.XML('<root><child/></root>')
        readers_started = [threading.Event() for _ in range(2)]
        threads = []
        result = []

        def read(started):
            started.set()
            result.append(root[0].tag)  # waits for the XPath evaluation

        def start_readers(context):
            for started in readers_started:
                thread = threading.Thread(target=read, args=(started,))
                threads.append(thread)
                thread.start()
            for started in readers_started:
                started.wait()
            return 'ok'

        try:
            self.assertEqual('ok', root.xpath(
                'test:start-readers()', namespaces={'test': 'testns'},
                extensions={('testns', 'start-readers'): start_readers}))
            root.set('written', 'yes')
        finally:
            for thread in threads:
                thread.join()
        self.assertEqual(['child', 'child'], result)
        self.assertEqual('yes', root.get('written'))

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

    def _validate_concurrently_with_ids(self, validator):
        # Threads validate one document, which adds its ID attributes to the ID table of
        # the document and its IDREFs to the IDREF table, while other threads look up IDs.
        root = self.etree.XML('<r>' + ''.join(
            f'<e id="i{k}" ref="i{(k + 1) % 50}"/>' for k in range(50)) + '</r>')
        elements = list(root)
        thread_count = 8
        start = threading.Barrier(thread_count)
        results = []

        def validate():
            start.wait()
            results.append(all([validator.validate(root) for _ in range(30)]))

        def look_up_ids():
            start.wait()
            # The IDs are only known after the first validation.
            results.append(all([root.xpath(f"id('i{k % 50}')") in ([], [elements[k % 50]])
                                for k in range(300)]))

        threads = [threading.Thread(target=validate if i % 2 else look_up_ids)
                   for i in range(thread_count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual([True] * thread_count, results)

    def test_concurrent_xmlschema_with_ids(self):
        self._validate_concurrently_with_ids(self.etree.XMLSchema(self.etree.XML('''\
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="r"><xs:complexType><xs:sequence>
    <xs:element name="e" maxOccurs="unbounded"><xs:complexType>
      <xs:attribute name="id" type="xs:ID"/><xs:attribute name="ref" type="xs:IDREF"/>
    </xs:complexType></xs:element>
  </xs:sequence></xs:complexType></xs:element>
</xs:schema>''')))

    def test_concurrent_relaxng_with_ids(self):
        self._validate_concurrently_with_ids(self.etree.RelaxNG(self.etree.XML('''\
<element name="r" xmlns="http://relaxng.org/ns/structure/1.0"
         datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
  <oneOrMore><element name="e">
    <attribute name="id"><data type="ID"/></attribute>
    <attribute name="ref"><data type="IDREF"/></attribute>
  </element></oneOrMore>
</element>''')))

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
