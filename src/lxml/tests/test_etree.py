# -*- coding: utf-8 -*-

"""
Tests specific to the extended etree API

Tests that apply to the general ElementTree API should go into
test_elementtree
"""


import unittest, copy, sys

from common_imports import etree, StringIO, HelperTestCase, fileInTestDir
from common_imports import SillyFileLike, canonicalize, doctest

print
print "TESTED VERSION:"
print "    Python:           ", sys.version_info
print "    lxml.etree:       ", etree.LXML_VERSION
print "    libxml used:      ", etree.LIBXML_VERSION
print "    libxml compiled:  ", etree.LIBXML_COMPILED_VERSION
print "    libxslt used:     ", etree.LIBXSLT_VERSION
print "    libxslt compiled: ", etree.LIBXSLT_COMPILED_VERSION
print

try:
    sorted(())
except NameError:
    # Python 2.3
    def sorted(seq):
        seq = list(seq)
        seq.sort()
        return seq

class ETreeOnlyTestCase(HelperTestCase):
    """Tests only for etree, not ElementTree"""
    etree = etree

    def test_version(self):
        self.assert_(isinstance(etree.__version__, str))
        self.assert_(isinstance(etree.LXML_VERSION, tuple))
        self.assertEqual(len(etree.LXML_VERSION), 4)
        self.assert_(isinstance(etree.LXML_VERSION[0], int))
        self.assert_(isinstance(etree.LXML_VERSION[1], int))
        self.assert_(isinstance(etree.LXML_VERSION[2], int))
        self.assert_(isinstance(etree.LXML_VERSION[3], int))
        self.assert_(etree.__version__.startswith(
            str(etree.LXML_VERSION[0])))

    def test_c_api(self):
        self.assert_(hasattr(self.etree, '_import_c_api'))

    def test_element_names(self):
        Element = self.etree.Element
        
        el = Element('name')
        self.assertEquals(el.tag, 'name')
        el = Element('{}name')
        self.assertEquals(el.tag, 'name')
        self.assertRaises(ValueError, Element, '{test}')
        self.assertRaises(ValueError, setattr, el, 'tag', '{test}')

    def test_attribute_set(self):
        # ElementTree accepts arbitrary attribute values
        # lxml.etree allows only strings
        Element = self.etree.Element

        root = Element("root")
        root.set("attr", "TEST")
        self.assertEquals("TEST", root.get("attr"))
        self.assertRaises(TypeError, root.set, "newattr", 5)

    def test_pi(self):
        # lxml.etree separates target and text
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        ProcessingInstruction = self.etree.ProcessingInstruction

        a = Element('a')
        a.append(ProcessingInstruction('foo', 'some more text'))
        self.assertEquals(a[0].target, 'foo')
        self.assertEquals(a[0].text, 'some more text')

    def test_pi_parse(self):
        XML = self.etree.XML
        root = XML("<test><?mypi my test ?></test>")
        self.assertEquals(root[0].target, "mypi")
        self.assertEquals(root[0].text, "my test ")

    def test_deepcopy_pi(self):
        # previously caused a crash
        ProcessingInstruction = self.etree.ProcessingInstruction
        
        a = ProcessingInstruction("PI", "ONE")
        b = copy.deepcopy(a)
        b.text = "ANOTHER"

        self.assertEquals('ONE',     a.text)
        self.assertEquals('ANOTHER', b.text)

    def test_deepcopy_comment(self):
        # previously caused a crash
        # not supported by ET!
        Comment = self.etree.Comment
        
        a = Comment("ONE")
        b = copy.deepcopy(a)
        b.text = "ANOTHER"

        self.assertEquals('ONE',     a.text)
        self.assertEquals('ANOTHER', b.text)

    def test_attribute_set(self):
        # ElementTree accepts arbitrary attribute values
        # lxml.etree allows only strings
        Element = self.etree.Element

        root = Element("root")
        root.set("attr", "TEST")
        self.assertEquals("TEST", root.get("attr"))
        self.assertRaises(TypeError, root.set, "newattr", 5)

    def test_parse_error(self):
        # ET raises ExpatError
        parse = self.etree.parse
        # from StringIO
        f = StringIO('<a><b></c></b></a>')
        self.assertRaises(SyntaxError, parse, f)
        f.close()

    def test_parse_parser_type_error(self):
        # ET raises IOError only
        parse = self.etree.parse
        self.assertRaises(TypeError, parse, 'notthere.xml', object())

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

    def test_iterparse_broken(self):
        iterparse = self.etree.iterparse
        f = StringIO('<a><b><c/></a>')
        # ET raises ExpatError, lxml raises XMLSyntaxError
        self.assertRaises(self.etree.XMLSyntaxError, list, iterparse(f))

    def test_iterparse_strip(self):
        iterparse = self.etree.iterparse
        f = StringIO("""
               <a>  \n \n  <b> b test </b>  \n

               \n\t <c> \n </c> </a>  \n """)
        iterator = iterparse(f, remove_blank_text=True)
        text = [ (element.text, element.tail)
                 for event, element in iterator ]
        self.assertEquals(
            [(" b test ", None), (" \n ", None), (None, None)],
            text)

    def test_iterparse_tag(self):
        iterparse = self.etree.iterparse
        f = StringIO('<a><b><d/></b><c/></a>')

        iterator = iterparse(f, tag="b", events=('start', 'end'))
        events = list(iterator)
        root = iterator.root
        self.assertEquals(
            [('start', root[0]), ('end', root[0])],
            events)

    def test_iterparse_tag_all(self):
        iterparse = self.etree.iterparse
        f = StringIO('<a><b><d/></b><c/></a>')

        iterator = iterparse(f, tag="*", events=('start', 'end'))
        events = list(iterator)
        self.assertEquals(
            8,
            len(events))

    def test_iterwalk_tag(self):
        iterwalk = self.etree.iterwalk
        root = self.etree.XML('<a><b><d/></b><c/></a>')

        iterator = iterwalk(root, tag="b", events=('start', 'end'))
        events = list(iterator)
        self.assertEquals(
            [('start', root[0]), ('end', root[0])],
            events)

    def test_iterwalk_tag_all(self):
        iterwalk = self.etree.iterwalk
        root = self.etree.XML('<a><b><d/></b><c/></a>')

        iterator = iterwalk(root, tag="*", events=('start', 'end'))
        events = list(iterator)
        self.assertEquals(
            8,
            len(events))

    def test_iterwalk(self):
        iterwalk = self.etree.iterwalk
        root = self.etree.XML('<a><b></b><c/></a>')

        events = list(iterwalk(root))
        self.assertEquals(
            [('end', root[0]), ('end', root[1]), ('end', root)],
            events)

    def test_iterwalk_start(self):
        iterwalk = self.etree.iterwalk
        root = self.etree.XML('<a><b></b><c/></a>')

        iterator = iterwalk(root, events=('start',))
        events = list(iterator)
        self.assertEquals(
            [('start', root), ('start', root[0]), ('start', root[1])],
            events)

    def test_iterwalk_start_end(self):
        iterwalk = self.etree.iterwalk
        root = self.etree.XML('<a><b></b><c/></a>')

        iterator = iterwalk(root, events=('start','end'))
        events = list(iterator)
        self.assertEquals(
            [('start', root), ('start', root[0]), ('end', root[0]),
             ('start', root[1]), ('end', root[1]), ('end', root)],
            events)

    def test_iterwalk_clear(self):
        iterwalk = self.etree.iterwalk
        root = self.etree.XML('<a><b></b><c/></a>')

        iterator = iterwalk(root)
        for event, elem in iterator:
            elem.clear()

        self.assertEquals(0,
                          len(root))

    def test_iterwalk_attrib_ns(self):
        iterwalk = self.etree.iterwalk
        root = self.etree.XML('<a xmlns="ns1"><b><c xmlns="ns2"/></b></a>')

        attr_name = '{testns}bla'
        events = []
        iterator = iterwalk(root, events=('start','end','start-ns','end-ns'))
        for event, elem in iterator:
            events.append(event)
            if event == 'start':
                if elem.tag != '{ns1}a':
                    elem.set(attr_name, 'value')

        self.assertEquals(
            ['start-ns', 'start', 'start', 'start-ns', 'start',
             'end', 'end-ns', 'end', 'end', 'end-ns'],
            events)

        self.assertEquals(
            None,
            root.get(attr_name))
        self.assertEquals(
            'value',
            root[0].get(attr_name))

    def test_iterwalk_getiterator(self):
        iterwalk = self.etree.iterwalk
        root = self.etree.XML('<a><b><d/></b><c/></a>')

        counts = []
        for event, elem in iterwalk(root):
            counts.append(len(list(elem.getiterator())))
        self.assertEquals(
            [1,2,1,4],
            counts)

    def test_resolve_string_dtd(self):
        parse = self.etree.parse
        parser = self.etree.XMLParser(dtd_validation=True)
        assertEqual = self.assertEqual
        test_url = u"__nosuch.dtd"

        class MyResolver(self.etree.Resolver):
            def resolve(self, url, id, context):
                assertEqual(url, test_url)
                return self.resolve_string(
                    u'<!ENTITY myentity "%s">' % url, context)

        parser.resolvers.add(MyResolver())

        xml = u'<!DOCTYPE doc SYSTEM "%s"><doc>&myentity;</doc>' % test_url
        tree = parse(StringIO(xml), parser)
        root = tree.getroot()
        self.assertEquals(root.text, test_url)

    def test_resolve_empty(self):
        parse = self.etree.parse
        parser = self.etree.XMLParser(dtd_validation=True)
        assertEqual = self.assertEqual
        test_url = u"__nosuch.dtd"

        class check(object):
            resolved = False

        class MyResolver(self.etree.Resolver):
            def resolve(self, url, id, context):
                assertEqual(url, test_url)
                check.resolved = True
                return self.resolve_empty(context)

        parser.resolvers.add(MyResolver())

        xml = u'<!DOCTYPE doc SYSTEM "%s"><doc>&myentity;</doc>' % test_url
        tree = parse(StringIO(xml), parser)
        self.assert_(check.resolved)

        root = tree.getroot()
        self.assertEquals(root.text, None)

    def test_resolve_error(self):
        parse = self.etree.parse
        parser = self.etree.XMLParser(dtd_validation=True)
        test_url = u"__nosuch.dtd"

        class _LocalException(Exception):
            pass

        class MyResolver(self.etree.Resolver):
            def resolve(self, url, id, context):
                raise _LocalException

        parser.resolvers.add(MyResolver())

        xml = u'<!DOCTYPE doc SYSTEM "test"><doc>&myentity;</doc>'
        self.assertRaises(_LocalException, parse, StringIO(xml), parser)

    # TypeError in etree, AssertionError in ElementTree;
    def test_setitem_assert(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        
        self.assertRaises(TypeError,
                          a.__setitem__, 0, 'foo')

    def test_append_None(self):
        # raises AssertionError in ElementTree
        Element = self.etree.Element
        self.assertRaises(TypeError, Element('a').append, None)

    # gives error in ElementTree
    def test_comment_empty(self):
        Element = self.etree.Element
        Comment = self.etree.Comment

        a = Element('a')
        a.append(Comment())
        self.assertEquals(
            '<a><!----></a>',
            self._writeElement(a))

    # ElementTree ignores comments
    def test_comment_parse_empty(self):
        ElementTree = self.etree.ElementTree
        tostring = self.etree.tostring

        xml = '<a><b/><!----><c/></a>'
        f = StringIO(xml)
        doc = ElementTree(file=f)
        a = doc.getroot()
        self.assertEquals(
            '',
            a[1].text)
        self.assertEquals(
            xml,
            tostring(a))

    # ElementTree ignores comments
    def test_comment_no_proxy_yet(self):
        ElementTree = self.etree.ElementTree
        
        f = StringIO('<a><b></b><!-- hoi --><c></c></a>')
        doc = ElementTree(file=f)
        a = doc.getroot()
        self.assertEquals(
            ' hoi ',
            a[1].text)

    # ElementTree adds whitespace around comments
    def test_comment_text(self):
        Element  = self.etree.Element
        Comment  = self.etree.Comment
        tostring = self.etree.tostring

        a = Element('a')
        a.append(Comment('foo'))
        self.assertEquals(
            '<a><!--foo--></a>',
            tostring(a))

        a[0].text = "TEST"
        self.assertEquals(
            '<a><!--TEST--></a>',
            tostring(a))

    # ElementTree adds whitespace around comments
    def test_comment_whitespace(self):
        Element = self.etree.Element
        Comment = self.etree.Comment
        tostring = self.etree.tostring

        a = Element('a')
        a.append(Comment(' foo  '))
        self.assertEquals(
            '<a><!-- foo  --></a>',
            tostring(a))

    # does not raise an exception in ElementTree
    def test_comment_immutable(self):
        Element = self.etree.Element
        Comment = self.etree.Comment

        c = Comment()
        el = Element('myel')

        self.assertRaises(TypeError, c.append, el)
        self.assertRaises(TypeError, c.insert, 0, el)
        self.assertRaises(TypeError, c.set, "myattr", "test")

    # test weird dictionary interaction leading to segfault previously
    def test_weird_dict_interaction(self):
        root = self.etree.Element('root')
        add = self.etree.ElementTree(file=StringIO('<foo>Foo</foo>'))
        root.append(self.etree.Element('baz'))

    # test passing 'None' to dump
    def test_dump_none(self):
        self.assertRaises(TypeError, etree.dump, None)

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

    def test_iterchildren(self):
        XML = self.etree.XML
        
        root = XML('<doc><one/><two>Two</two>Hm<three/></doc>')
        result = []
        for el in root.iterchildren():
            result.append(el.tag)
        self.assertEquals(['one', 'two', 'three'], result)

    def test_iterchildren_reversed(self):
        XML = self.etree.XML
        
        root = XML('<doc><one/><two>Two</two>Hm<three/></doc>')
        result = []
        for el in root.iterchildren(reversed=True):
            result.append(el.tag)
        self.assertEquals(['three', 'two', 'one'], result)

    def test_iterchildren_tag(self):
        XML = self.etree.XML
        
        root = XML('<doc><one/><two>Two</two>Hm<two>Bla</two></doc>')
        result = []
        for el in root.iterchildren(tag='two'):
            result.append(el.text)
        self.assertEquals(['Two', 'Bla'], result)

    def test_iterchildren_tag_reversed(self):
        XML = self.etree.XML
        
        root = XML('<doc><one/><two>Two</two>Hm<two>Bla</two></doc>')
        result = []
        for el in root.iterchildren(reversed=True, tag='two'):
            result.append(el.text)
        self.assertEquals(['Bla', 'Two'], result)

    def test_iterancestors(self):
        Element    = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        self.assertEquals(
            [],
            list(a.iterancestors()))
        self.assertEquals(
            [a],
            list(b.iterancestors()))
        self.assertEquals(
            a,
            c.iterancestors().next())
        self.assertEquals(
            [b, a],
            list(d.iterancestors()))

    def test_iterancestors_tag(self):
        Element    = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        self.assertEquals(
            [a],
            list(d.iterancestors(tag='a')))

    def test_iterdescendants(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        e = SubElement(c, 'e')

        self.assertEquals(
            [b, d, c, e],
            list(a.iterdescendants()))
        self.assertEquals(
            [],
            list(d.iterdescendants()))

    def test_iterdescendants_tag(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        e = SubElement(c, 'e')

        self.assertEquals(
            [],
            list(a.iterdescendants('a')))
        a2 = SubElement(e, 'a')
        self.assertEquals(
            [a2],
            list(a.iterdescendants('a')))
        self.assertEquals(
            [a2],
            list(c.iterdescendants('a')))

    def test_getroottree(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        self.assertEquals(
            a,
            a.getroottree().getroot())
        self.assertEquals(
            a,
            b.getroottree().getroot())
        self.assertEquals(
            a,
            d.getroottree().getroot())

    def test_getnext(self):
        Element    = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        self.assertEquals(
            None,
            a.getnext())
        self.assertEquals(
            c,
            b.getnext())
        self.assertEquals(
            None,
            c.getnext())

    def test_getprevious(self):
        Element    = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        self.assertEquals(
            None,
            a.getprevious())
        self.assertEquals(
            b,
            c.getprevious())
        self.assertEquals(
            None,
            b.getprevious())

    def test_itersiblings(self):
        Element    = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        self.assertEquals(
            [],
            list(a.itersiblings()))
        self.assertEquals(
            [c],
            list(b.itersiblings()))
        self.assertEquals(
            c,
            b.itersiblings().next())
        self.assertEquals(
            [],
            list(c.itersiblings()))
        self.assertEquals(
            [b],
            list(c.itersiblings(preceding=True)))
        self.assertEquals(
            [],
            list(b.itersiblings(preceding=True)))

    def test_itersiblings_tag(self):
        Element    = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(b, 'd')
        self.assertEquals(
            [],
            list(a.itersiblings(tag='XXX')))
        self.assertEquals(
            [c],
            list(b.itersiblings(tag='c')))
        self.assertEquals(
            [b],
            list(c.itersiblings(preceding=True, tag='b')))
        self.assertEquals(
            [],
            list(c.itersiblings(preceding=True, tag='c')))

    def test_parseid(self):
        parseid = self.etree.parseid
        XML     = self.etree.XML
        xml_text = '''
        <!DOCTYPE document [
        <!ELEMENT document (h1,p)*>
        <!ELEMENT h1 (#PCDATA)>
        <!ATTLIST h1 myid ID #REQUIRED>
        <!ELEMENT p  (#PCDATA)>
        <!ATTLIST p  someid ID #REQUIRED>
        ]>
        <document>
          <h1 myid="chapter1">...</h1>
          <p id="note1" class="note">...</p>
          <p>Regular paragraph.</p>
          <p xml:id="xmlid">XML:ID paragraph.</p>
          <p someid="warn1" class="warning">...</p>
        </document>
        '''

        tree, dic = parseid(StringIO(xml_text))
        root = tree.getroot()
        root2 = XML(xml_text)
        self.assertEquals(self._writeElement(root),
                          self._writeElement(root2))
        expected = {
            "chapter1" : root[0],
            "xmlid"    : root[3],
            "warn1"    : root[4]
            }
        self.assert_("chapter1" in dic)
        self.assert_("warn1" in dic)
        self.assert_("xmlid" in dic)
        self._checkIDDict(dic, expected)

    def test_XMLDTDID(self):
        XMLDTDID = self.etree.XMLDTDID
        XML      = self.etree.XML
        xml_text = '''
        <!DOCTYPE document [
        <!ELEMENT document (h1,p)*>
        <!ELEMENT h1 (#PCDATA)>
        <!ATTLIST h1 myid ID #REQUIRED>
        <!ELEMENT p  (#PCDATA)>
        <!ATTLIST p  someid ID #REQUIRED>
        ]>
        <document>
          <h1 myid="chapter1">...</h1>
          <p id="note1" class="note">...</p>
          <p>Regular paragraph.</p>
          <p xml:id="xmlid">XML:ID paragraph.</p>
          <p someid="warn1" class="warning">...</p>
        </document>
        '''

        root, dic = XMLDTDID(xml_text)
        root2 = XML(xml_text)
        self.assertEquals(self._writeElement(root),
                          self._writeElement(root2))
        expected = {
            "chapter1" : root[0],
            "xmlid"    : root[3],
            "warn1"    : root[4]
            }
        self.assert_("chapter1" in dic)
        self.assert_("warn1" in dic)
        self.assert_("xmlid" in dic)
        self._checkIDDict(dic, expected)

    def test_XMLDTDID_empty(self):
        XMLDTDID = self.etree.XMLDTDID
        XML      = self.etree.XML
        xml_text = '''
        <document>
          <h1 myid="chapter1">...</h1>
          <p id="note1" class="note">...</p>
          <p>Regular paragraph.</p>
          <p someid="warn1" class="warning">...</p>
        </document>
        '''

        root, dic = XMLDTDID(xml_text)
        root2 = XML(xml_text)
        self.assertEquals(self._writeElement(root),
                          self._writeElement(root2))
        expected = {}
        self._checkIDDict(dic, expected)

    def _checkIDDict(self, dic, expected):
        self.assertEquals(dic, expected)
        self.assertEquals(len(dic),
                          len(expected))
        self.assertEquals(sorted(dic.items()),
                          sorted(expected.items()))
        self.assertEquals(sorted(dic.iteritems()),
                          sorted(expected.iteritems()))
        self.assertEquals(sorted(dic.keys()),
                          sorted(expected.keys()))
        self.assertEquals(sorted(dic.iterkeys()),
                          sorted(expected.iterkeys()))
        self.assertEquals(sorted(dic.values()),
                          sorted(expected.values()))
        self.assertEquals(sorted(dic.itervalues()),
                          sorted(expected.itervalues()))

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

    def test_namespaces_default_copy_element(self):
        etree = self.etree

        r = {None: 'http://ns.infrae.com/foo'}
        e1 = etree.Element('{http://ns.infrae.com/foo}bar', nsmap=r)
        e2 = etree.Element('{http://ns.infrae.com/foo}bar', nsmap=r)

        e1.append(e2)

        self.assertEquals(
            None,
            e1.prefix)
        self.assertEquals(
            None,
            e1[0].prefix)
        self.assertEquals(
            '{http://ns.infrae.com/foo}bar',
            e1.tag)
        self.assertEquals(
            '{http://ns.infrae.com/foo}bar',
            e1[0].tag)

    def test_namespaces_copy_element(self):
        etree = self.etree

        r = {None: 'http://ns.infrae.com/BAR'}
        e1 = etree.Element('{http://ns.infrae.com/BAR}bar', nsmap=r)
        e2 = etree.Element('{http://ns.infrae.com/foo}bar', nsmap=r)

        e1.append(e2)

        self.assertEquals(
            None,
            e1.prefix)
        self.assertNotEquals(
            None,
            e2.prefix)
        self.assertEquals(
            '{http://ns.infrae.com/BAR}bar',
            e1.tag)
        self.assertEquals(
            '{http://ns.infrae.com/foo}bar',
            e2.tag)

    def test_namespaces_reuse_after_move(self):
        ns_href = "http://a.b.c"
        one = self.etree.parse(
            StringIO('<foo><bar xmlns:ns="%s"><ns:baz/></bar></foo>' % ns_href))
        baz = one.getroot()[0][0]

        two = self.etree.parse(
            StringIO('<root xmlns:ns="%s"/>' % ns_href))
        two.getroot().append(baz)
        del one # make sure the source document is deallocated

        self.assertEquals('{%s}baz' % ns_href, baz.tag)
        self.assertEquals(
            '<root xmlns:ns="%s"><ns:baz/></root>' % ns_href,
            self.etree.tostring(two))

    def _test_namespaces_after_serialize(self):
        # FIXME: this currently fails - fix serializer.pxi!
        parse = self.etree.parse
        tostring = self.etree.tostring

        ns_href = "http://a.b.c"
        one = parse(
            StringIO('<foo><bar xmlns:ns="%s"><ns:baz/></bar></foo>' % ns_href))
        baz = one.getroot()[0][0]

        print tostring(baz)
        parsed = parse(StringIO( tostring(baz) )).getroot()

        self.assertEquals('{%s}baz' % ns_href, parsed.tag)

    def test_element_nsmap(self):
        etree = self.etree

        r = {None: 'http://ns.infrae.com/foo',
             'hoi': 'http://ns.infrae.com/hoi'}
        e = etree.Element('{http://ns.infrae.com/foo}bar', nsmap=r)
        self.assertEquals(
            r,
            e.nsmap)

    def test_subelement_nsmap(self):
        etree = self.etree

        re = {None: 'http://ns.infrae.com/foo',
             'hoi': 'http://ns.infrae.com/hoi'}
        e = etree.Element('{http://ns.infrae.com/foo}bar', nsmap=re)

        rs = {None: 'http://ns.infrae.com/honk',
             'top': 'http://ns.infrae.com/top'}
        s = etree.SubElement(e, '{http://ns.infrae.com/honk}bar', nsmap=rs)

        r = re.copy()
        r.update(rs)
        self.assertEquals(
            re,
            e.nsmap)
        self.assertEquals(
            r,
            s.nsmap)

    def test_getiterator_filter_namespace(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('{a}a')
        b = SubElement(a, '{a}b')
        c = SubElement(a, '{a}c')
        d = SubElement(b, '{b}d')
        e = SubElement(c, '{a}e')
        f = SubElement(c, '{b}f')

        self.assertEquals(
            [a],
            list(a.getiterator('{a}a')))
        self.assertEquals(
            [],
            list(a.getiterator('{b}a')))
        self.assertEquals(
            [],
            list(a.getiterator('a')))
        self.assertEquals(
            [f],
            list(c.getiterator('{b}*')))
        self.assertEquals(
            [d, f],
            list(a.getiterator('{b}*')))

    def test_findall_ns(self):
        XML = self.etree.XML
        root = XML('<a xmlns:x="X" xmlns:y="Y"><x:b><c/></x:b><b/><c><x:b/><b/></c><b/></a>')
        self.assertEquals(len(root.findall(".//{X}b")), 2)
        self.assertEquals(len(root.findall(".//{X}*")), 2)
        self.assertEquals(len(root.findall(".//b")), 3)

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

    def test_replace(self):
        etree = self.etree
        e = etree.Element('foo')
        for i in range(10):
            el = etree.SubElement(e, 'a%s' % i)
            el.text = "text%d" % i
            el.tail = "tail%d" % i

        child0 = e[0]
        child1 = e[1]
        child2 = e[2]

        e.replace(e[0], e[1])
        self.assertEquals(
            9, len(e))
        self.assertEquals(
            child1, e[0])
        self.assertEquals(
            child1.text, "text1")
        self.assertEquals(
            child1.tail, "tail1")
        self.assertEquals(
            child0.tail, "tail0")
        self.assertEquals(
            child2, e[1])

        e.replace(e[-1], e[0])
        self.assertEquals(
            child1, e[-1])
        self.assertEquals(
            child1.text, "text1")
        self.assertEquals(
            child1.tail, "tail1")
        self.assertEquals(
            child2, e[0])

    def test_replace_new(self):
        etree = self.etree
        e = etree.Element('foo')
        for i in range(10):
            etree.SubElement(e, 'a%s' % i)

        new_element = etree.Element("test")
        new_element.text = "TESTTEXT"
        new_element.tail = "TESTTAIL"
        child1 = e[1]
        e.replace(e[0], new_element)
        self.assertEquals(
            new_element, e[0])
        self.assertEquals(
            "TESTTEXT",
            e[0].text)
        self.assertEquals(
            "TESTTAIL",
            e[0].tail)
        self.assertEquals(
            child1, e[1])

    def test_extend(self):
        etree = self.etree
        root = etree.Element('foo')
        for i in range(3):
            element = etree.SubElement(root, 'a%s' % i)
            element.text = "text%d" % i
            element.tail = "tail%d" % i

        elements = []
        for i in range(3):
            new_element = etree.Element("test%s" % i)
            new_element.text = "TEXT%s" % i
            new_element.tail = "TAIL%s" % i
            elements.append(new_element)

        root.extend(elements)

        self.assertEquals(
            ["a0", "a1", "a2", "test0", "test1", "test2"],
            [ el.tag for el in root ])
        self.assertEquals(
            ["text0", "text1", "text2", "TEXT0", "TEXT1", "TEXT2"],
            [ el.text for el in root ])
        self.assertEquals(
            ["tail0", "tail1", "tail2", "TAIL0", "TAIL1", "TAIL2"],
            [ el.tail for el in root ])

    def test_sourceline_XML(self):
        XML = self.etree.XML
        root = XML('''<?xml version="1.0"?>
        <root><test>

        <bla/></test>
        </root>
        ''')

        self.assertEquals(
            [2, 2, 4],
            [ el.sourceline for el in root.getiterator() ])

    def test_sourceline_parse(self):
        parse = self.etree.parse
        tree = parse(fileInTestDir('test_xinclude.xml'))

        self.assertEquals(
            [1, 2, 3],
            [ el.sourceline for el in tree.getiterator() ])

    def test_sourceline_element(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        el = Element("test")
        self.assertEquals(None, el.sourceline)

        child = SubElement(el, "test")
        self.assertEquals(None, el.sourceline)
        self.assertEquals(None, child.sourceline)

    def test_docinfo_public(self):
        etree = self.etree
        xml_header = '<?xml version="1.0" encoding="ascii"?>'
        pub_id = "-//W3C//DTD XHTML 1.0 Transitional//EN"
        sys_id = "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"
        doctype_string = '<!DOCTYPE html PUBLIC "%s" "%s">' % (pub_id, sys_id)

        xml = xml_header + doctype_string + '<html><body></body></html>'

        tree = etree.parse(StringIO(xml))
        docinfo = tree.docinfo
        self.assertEquals(docinfo.encoding,    "ascii")
        self.assertEquals(docinfo.xml_version, "1.0")
        self.assertEquals(docinfo.public_id,   pub_id)
        self.assertEquals(docinfo.system_url,  sys_id)
        self.assertEquals(docinfo.root_name,   'html')
        self.assertEquals(docinfo.doctype, doctype_string)

    def test_docinfo_system(self):
        etree = self.etree
        xml_header = '<?xml version="1.0" encoding="UTF-8"?>'
        sys_id = "some.dtd"
        doctype_string = '<!DOCTYPE html SYSTEM "%s">' % sys_id
        xml = xml_header + doctype_string + '<html><body></body></html>'

        tree = etree.parse(StringIO(xml))
        docinfo = tree.docinfo
        self.assertEquals(docinfo.encoding,    "UTF-8")
        self.assertEquals(docinfo.xml_version, "1.0")
        self.assertEquals(docinfo.public_id,   None)
        self.assertEquals(docinfo.system_url,  sys_id)
        self.assertEquals(docinfo.root_name,   'html')
        self.assertEquals(docinfo.doctype, doctype_string)

    def test_docinfo_empty(self):
        etree = self.etree
        xml = '<html><body></body></html>'
        tree = etree.parse(StringIO(xml))
        docinfo = tree.docinfo
        self.assertEquals(docinfo.encoding,    None)
        self.assertEquals(docinfo.xml_version, "1.0")
        self.assertEquals(docinfo.public_id,   None)
        self.assertEquals(docinfo.system_url,  None)
        self.assertEquals(docinfo.root_name,   'html')
        self.assertEquals(docinfo.doctype, '')

    def test_encoding_tostring_utf16(self):
        # ElementTree fails to serialize this
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')

        result = unicode(tostring(a, 'UTF-16'), 'UTF-16')
        self.assertEquals('<a><b></b><c></c></a>',
                          canonicalize(result))

    def test_tostring_none(self):
        # ElementTree raises an AssertionError here
        tostring = self.etree.tostring
        self.assertRaises(TypeError, self.etree.tostring, None)

    def test_tostring_pretty(self):
        tostring = self.etree.tostring
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')

        result = tostring(a)
        self.assertEquals(result, "<a><b/><c/></a>")

        result = tostring(a, pretty_print=False)
        self.assertEquals(result, "<a><b/><c/></a>")

        result = tostring(a, pretty_print=True)
        self.assertEquals(result, "<a>\n  <b/>\n  <c/>\n</a>")

    def test_tounicode(self):
        tounicode = self.etree.tounicode
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        
        self.assert_(isinstance(tounicode(a), unicode))
        self.assertEquals('<a><b></b><c></c></a>',
                          canonicalize(tounicode(a)))

    def test_tounicode_element(self):
        tounicode = self.etree.tounicode
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(c, 'd')
        self.assert_(isinstance(tounicode(b), unicode))
        self.assert_(isinstance(tounicode(c), unicode))
        self.assertEquals('<b></b>',
                          canonicalize(tounicode(b)))
        self.assertEquals('<c><d></d></c>',
                          canonicalize(tounicode(c)))

    def test_tounicode_none(self):
        tounicode = self.etree.tounicode
        self.assertRaises(TypeError, self.etree.tounicode, None)

    def test_tounicode_element_tail(self):
        tounicode = self.etree.tounicode
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        
        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')
        d = SubElement(c, 'd')
        b.tail = 'Foo'

        self.assert_(isinstance(tounicode(b), unicode))
        self.assert_(tounicode(b) == '<b/>Foo' or
                     tounicode(b) == '<b />Foo')

    def test_tounicode_pretty(self):
        tounicode = self.etree.tounicode
        Element = self.etree.Element
        SubElement = self.etree.SubElement

        a = Element('a')
        b = SubElement(a, 'b')
        c = SubElement(a, 'c')

        result = tounicode(a)
        self.assertEquals(result, "<a><b/><c/></a>")

        result = tounicode(a, pretty_print=False)
        self.assertEquals(result, "<a><b/><c/></a>")

        result = tounicode(a, pretty_print=True)
        self.assertEquals(result, "<a>\n  <b/>\n  <c/>\n</a>")

    def _writeElement(self, element, encoding='us-ascii'):
        """Write out element for comparison.
        """
        ElementTree = self.etree.ElementTree
        f = StringIO()
        tree = ElementTree(element=element)
        tree.write(f, encoding)
        data = f.getvalue()
        return canonicalize(data)


class XIncludeTestCase(HelperTestCase):
    def test_xinclude_text(self):
        filename = fileInTestDir('test_broken.xml')
        root = etree.XML('''\
        <doc xmlns:xi="http://www.w3.org/2001/XInclude">
          <xi:include href="%s" parse="text"/>
        </doc>
        ''' % filename)
        old_text = root.text
        content = open(filename).read()
        old_tail = root[0].tail

        self.include( etree.ElementTree(root) )
        self.assertEquals(old_text + content + old_tail,
                          root.text)

class ETreeXIncludeTestCase(XIncludeTestCase):
    def include(self, tree):
        tree.xinclude()

    def test_xinclude(self):
        tree = etree.parse(fileInTestDir('test_xinclude.xml'))
        # process xincludes
        self.include( tree )
        # check whether we find it replaced with included data
        self.assertEquals(
            'a',
            tree.getroot()[1].tag)


class ElementIncludeTestCase(XIncludeTestCase):
    from lxml import ElementInclude
    def include(self, tree):
        self.ElementInclude.include(tree.getroot())


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
    suite.addTests([unittest.makeSuite(ElementIncludeTestCase)])
    suite.addTests([unittest.makeSuite(ETreeC14NTestCase)])
    suite.addTests(
        [doctest.DocFileSuite('../../../doc/api.txt')])
    suite.addTests(
        [doctest.DocFileSuite('../../../doc/parsing.txt')])
    suite.addTests(
        [doctest.DocFileSuite('../../../doc/resolvers.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
