# -*- coding: utf-8 -*-

"""
Test cases related to XPath evaluation and the XPath class
"""

import unittest, sys, os.path

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

from common_imports import etree, HelperTestCase, _bytes, BytesIO
from common_imports import doctest, make_doctest

class ETreeXPathTestCase(HelperTestCase):
    """XPath tests etree"""

    def test_xpath_boolean(self):
        tree = self.parse('<a><b></b><b></b></a>')
        self.assert_(tree.xpath('boolean(/a/b)'))
        self.assert_(not tree.xpath('boolean(/a/c)'))

    def test_xpath_number(self):
        tree = self.parse('<a>1</a>')
        self.assertEquals(1.,
                          tree.xpath('number(/a)'))
        tree = self.parse('<a>A</a>')
        actual = str(tree.xpath('number(/a)'))
        expected = ['nan', '1.#qnan', 'nanq']
        if not actual.lower() in expected:
            self.fail('Expected a NAN value, got %s' % actual)
        
    def test_xpath_string(self):
        tree = self.parse('<a>Foo</a>')
        self.assertEquals('Foo',
                          tree.xpath('string(/a/text())'))

    def test_xpath_document_root(self):
        tree = self.parse('<a><b/></a>')
        self.assertEquals([],
                          tree.xpath('/'))

    def test_xpath_namespace(self):
        tree = self.parse('<a xmlns="test" xmlns:p="myURI"/>')
        self.assert_((None, "test") in tree.xpath('namespace::*'))
        self.assert_(('p', 'myURI') in tree.xpath('namespace::*'))

    def test_xpath_namespace_empty(self):
        tree = self.parse('<a/>')
        self.assertEquals([('xml', 'http://www.w3.org/XML/1998/namespace')],
                          tree.xpath('namespace::*'))

    def test_xpath_list_elements(self):
        tree = self.parse('<a><b>Foo</b><b>Bar</b></a>')
        root = tree.getroot()
        self.assertEquals([root[0], root[1]],
                          tree.xpath('/a/b'))

    def test_xpath_list_nothing(self):
        tree = self.parse('<a><b/></a>')
        self.assertEquals([],
                          tree.xpath('/a/c'))
        # this seems to pass a different code path, also should return nothing
        self.assertEquals([],
                          tree.xpath('/a/c/text()'))
    
    def test_xpath_list_text(self):
        tree = self.parse('<a><b>Foo</b><b>Bar</b></a>')
        root = tree.getroot()
        self.assertEquals(['Foo', 'Bar'],
                          tree.xpath('/a/b/text()'))

    def test_xpath_list_text_parent(self):
        tree = self.parse('<a><b>FooBar</b><b>BarFoo</b></a>')
        root = tree.getroot()
        self.assertEquals(['FooBar', 'BarFoo'],
                          tree.xpath('/a/b/text()'))
        self.assertEquals([root[0], root[1]],
                          [r.getparent() for r in tree.xpath('/a/b/text()')])

    def test_xpath_list_text_parent_no_smart_strings(self):
        tree = self.parse('<a><b>FooBar</b><b>BarFoo</b></a>')
        root = tree.getroot()
        self.assertEquals(['FooBar', 'BarFoo'],
                          tree.xpath('/a/b/text()', smart_strings=True))
        self.assertEquals([root[0], root[1]],
                          [r.getparent() for r in
                           tree.xpath('/a/b/text()', smart_strings=True)])
        self.assertEquals([None, None],
                          [r.attrname for r in
                           tree.xpath('/a/b/text()', smart_strings=True)])

        self.assertEquals(['FooBar', 'BarFoo'],
                          tree.xpath('/a/b/text()', smart_strings=False))
        self.assertEquals([False, False],
                          [hasattr(r, 'getparent') for r in
                           tree.xpath('/a/b/text()', smart_strings=False)])
        self.assertEquals([None, None],
                          [r.attrname for r in
                           tree.xpath('/a/b/text()', smart_strings=True)])

    def test_xpath_list_unicode_text_parent(self):
        xml = _bytes('<a><b>FooBar\\u0680\\u3120</b><b>BarFoo\\u0680\\u3120</b></a>').decode("unicode_escape")
        tree = self.parse(xml.encode('utf-8'))
        root = tree.getroot()
        self.assertEquals([_bytes('FooBar\\u0680\\u3120').decode("unicode_escape"),
                           _bytes('BarFoo\\u0680\\u3120').decode("unicode_escape")],
                          tree.xpath('/a/b/text()'))
        self.assertEquals([root[0], root[1]],
                          [r.getparent() for r in tree.xpath('/a/b/text()')])

    def test_xpath_list_attribute(self):
        tree = self.parse('<a b="B" c="C"/>')
        self.assertEquals(['B'],
                          tree.xpath('/a/@b'))

    def test_xpath_list_attribute_parent(self):
        tree = self.parse('<a b="BaSdFgHjKl" c="CqWeRtZuI"/>')
        results = tree.xpath('/a/@c')
        self.assertEquals(1, len(results))
        self.assertEquals('CqWeRtZuI', results[0])
        self.assertEquals(tree.getroot().tag, results[0].getparent().tag)

    def test_xpath_list_attribute_parent_no_smart_strings(self):
        tree = self.parse('<a b="BaSdFgHjKl" c="CqWeRtZuI"/>')

        results = tree.xpath('/a/@c', smart_strings=True)
        self.assertEquals(1, len(results))
        self.assertEquals('CqWeRtZuI', results[0])
        self.assertEquals('c', results[0].attrname)
        self.assertEquals(tree.getroot().tag, results[0].getparent().tag)

        results = tree.xpath('/a/@c', smart_strings=False)
        self.assertEquals(1, len(results))
        self.assertEquals('CqWeRtZuI', results[0])
        self.assertEquals(False, hasattr(results[0], 'getparent'))
        self.assertEquals(False, hasattr(results[0], 'attrname'))

    def test_xpath_text_from_other_document(self):
        xml_data = '''
        <table>
                <item xml:id="k1"><value>v1</value></item>
                <item xml:id="k2"><value>v2</value></item>
        </table>
        '''

        def lookup(dummy, id):
            return etree.XML(xml_data).xpath('id(%r)' % id)
        functions = {(None, 'lookup') : lookup}

        root = etree.XML('<dummy/>')
        values = root.xpath("lookup('k1')/value/text()",
                           extensions=functions)
        self.assertEquals(['v1'], values)
        self.assertEquals('value', values[0].getparent().tag)

    def test_xpath_list_comment(self):
        tree = self.parse('<a><!-- Foo --></a>')
        self.assertEquals(['<!-- Foo -->'],
                          list(map(repr, tree.xpath('/a/node()'))))

    def test_rel_xpath_boolean(self):
        root = etree.XML('<a><b><c/></b></a>')
        el = root[0]
        self.assert_(el.xpath('boolean(c)'))
        self.assert_(not el.xpath('boolean(d)'))

    def test_rel_xpath_list_elements(self):
        tree = self.parse('<a><c><b>Foo</b><b>Bar</b></c><c><b>Hey</b></c></a>')
        root = tree.getroot()
        c = root[0]
        self.assertEquals([c[0], c[1]],
                          c.xpath('b'))
        self.assertEquals([c[0], c[1], root[1][0]],
                          c.xpath('//b'))

    def test_xpath_ns(self):
        tree = self.parse('<a xmlns="uri:a"><b></b></a>')
        root = tree.getroot()
        self.assertEquals(
            [root[0]],
            tree.xpath('//foo:b', namespaces={'foo': 'uri:a'}))
        self.assertEquals(
            [],
            tree.xpath('//foo:b', namespaces={'foo': 'uri:c'}))
        self.assertEquals(
            [root[0]],
            root.xpath('//baz:b', namespaces={'baz': 'uri:a'}))

    def test_xpath_ns_none(self):
        tree = self.parse('<a xmlns="uri:a"><b></b></a>')
        root = tree.getroot()
        self.assertRaises(
            TypeError,
            root.xpath, '//b', namespaces={None: 'uri:a'})

    def test_xpath_ns_empty(self):
        tree = self.parse('<a xmlns="uri:a"><b></b></a>')
        root = tree.getroot()
        self.assertRaises(
            TypeError,
            root.xpath, '//b', namespaces={'': 'uri:a'})

    def test_xpath_error(self):
        tree = self.parse('<a/>')
        self.assertRaises(etree.XPathEvalError, tree.xpath, '\\fad')

    def test_xpath_class_error(self):
        self.assertRaises(SyntaxError, etree.XPath, '\\fad')
        self.assertRaises(etree.XPathSyntaxError, etree.XPath, '\\fad')

    def test_xpath_prefix_error(self):
        tree = self.parse('<a/>')
        self.assertRaises(etree.XPathEvalError, tree.xpath, '/fa:d')

    def test_xpath_class_prefix_error(self):
        tree = self.parse('<a/>')
        xpath = etree.XPath("/fa:d")
        self.assertRaises(etree.XPathEvalError, xpath, tree)

    def test_elementtree_getpath(self):
        a  = etree.Element("a")
        b  = etree.SubElement(a, "b")
        c  = etree.SubElement(a, "c")
        d1 = etree.SubElement(c, "d")
        d2 = etree.SubElement(c, "d")

        tree = etree.ElementTree(a)
        self.assertEqual('/a/c/d',
                         tree.getpath(d2)[:6])
        self.assertEqual([d2],
                         tree.xpath(tree.getpath(d2)))

    def test_elementtree_getpath_partial(self):
        a  = etree.Element("a")
        b  = etree.SubElement(a, "b")
        c  = etree.SubElement(a, "c")
        d1 = etree.SubElement(c, "d")
        d2 = etree.SubElement(c, "d")

        tree = etree.ElementTree(c)
        self.assertEqual('/c/d',
                         tree.getpath(d2)[:4])
        self.assertEqual([d2],
                         tree.xpath(tree.getpath(d2)))

    def test_xpath_evaluator(self):
        tree = self.parse('<a><b><c></c></b></a>')
        e = etree.XPathEvaluator(tree)
        root = tree.getroot()
        self.assertEquals(
            [root],
            e('//a'))

    def test_xpath_evaluator_tree(self):
        tree = self.parse('<a><b><c></c></b></a>')
        child_tree = etree.ElementTree(tree.getroot()[0])
        e = etree.XPathEvaluator(child_tree)
        self.assertEquals(
            [],
            e('a'))
        root = child_tree.getroot()
        self.assertEquals(
            [root[0]],
            e('c'))

    def test_xpath_evaluator_tree_absolute(self):
        tree = self.parse('<a><b><c></c></b></a>')
        child_tree = etree.ElementTree(tree.getroot()[0])
        e = etree.XPathEvaluator(child_tree)
        self.assertEquals(
            [],
            e('/a'))
        root = child_tree.getroot()
        self.assertEquals(
            [root],
            e('/b'))
        self.assertEquals(
            [],
            e('/c'))

    def test_xpath_evaluator_element(self):
        tree = self.parse('<a><b><c></c></b></a>')
        root = tree.getroot()
        e = etree.XPathEvaluator(root[0])
        self.assertEquals(
            [root[0][0]],
            e('c'))
        
    def test_xpath_extensions(self):
        def foo(evaluator, a):
            return 'hello %s' % a
        extension = {(None, 'foo'): foo}
        tree = self.parse('<a><b></b></a>')
        e = etree.XPathEvaluator(tree, extensions=[extension])
        self.assertEquals(
            "hello you", e("foo('you')"))

    def test_xpath_extensions_wrong_args(self):
        def foo(evaluator, a, b):
            return "hello %s and %s" % (a, b)
        extension = {(None, 'foo'): foo}
        tree = self.parse('<a><b></b></a>')
        e = etree.XPathEvaluator(tree, extensions=[extension])
        self.assertRaises(TypeError, e, "foo('you')")

    def test_xpath_extensions_error(self):
        def foo(evaluator, a):
            return 1/0
        extension = {(None, 'foo'): foo}
        tree = self.parse('<a/>')
        e = etree.XPathEvaluator(tree, extensions=[extension])
        self.assertRaises(ZeroDivisionError, e, "foo('test')")

    def test_xpath_extensions_nodes(self):
        def f(evaluator, arg):
            r = etree.Element('results')
            b = etree.SubElement(r, 'result')
            b.text = 'Hoi'
            b = etree.SubElement(r, 'result')
            b.text = 'Dag'
            return r

        x = self.parse('<a/>')
        e = etree.XPathEvaluator(x, extensions=[{(None, 'foo'): f}])
        r = e("foo('World')/result")
        self.assertEquals(2, len(r))
        self.assertEquals('Hoi', r[0].text)
        self.assertEquals('Dag', r[1].text)

    def test_xpath_extensions_nodes_append(self):
        def f(evaluator, nodes):
            r = etree.SubElement(nodes[0], 'results')
            b = etree.SubElement(r, 'result')
            b.text = 'Hoi'
            b = etree.SubElement(r, 'result')
            b.text = 'Dag'
            return r

        x = self.parse('<a/>')
        e = etree.XPathEvaluator(x, extensions=[{(None, 'foo'): f}])
        r = e("foo(/*)/result")
        self.assertEquals(2, len(r))
        self.assertEquals('Hoi', r[0].text)
        self.assertEquals('Dag', r[1].text)

    def test_xpath_extensions_nodes_append2(self):
        def f(evaluator, nodes):
            r = etree.Element('results')
            b = etree.SubElement(r, 'result')
            b.text = 'Hoi'
            b = etree.SubElement(r, 'result')
            b.text = 'Dag'
            r.append(nodes[0])
            return r

        x = self.parse('<result>Honk</result>')
        e = etree.XPathEvaluator(x, extensions=[{(None, 'foo'): f}])
        r = e("foo(/*)/result")
        self.assertEquals(3, len(r))
        self.assertEquals('Hoi',  r[0].text)
        self.assertEquals('Dag',  r[1].text)
        self.assertEquals('Honk', r[2].text)

    def test_xpath_context_node(self):
        tree = self.parse('<root><a/><b><c/></b></root>')

        check_call = []
        def check_context(ctxt, nodes):
            self.assertEquals(len(nodes), 1)
            check_call.append(nodes[0].tag)
            self.assertEquals(ctxt.context_node, nodes[0])
            return True

        find = etree.XPath("//*[p:foo(.)]",
                           namespaces={'p' : 'ns'},
                           extensions=[{('ns', 'foo') : check_context}])
        find(tree)

        check_call.sort()
        self.assertEquals(check_call, ["a", "b", "c", "root"])

    def test_xpath_eval_context_propagation(self):
        tree = self.parse('<root><a/><b><c/></b></root>')

        check_call = {}
        def check_context(ctxt, nodes):
            self.assertEquals(len(nodes), 1)
            tag = nodes[0].tag
            # empty during the "b" call, a "b" during the "c" call
            check_call[tag] = ctxt.eval_context.get("b")
            ctxt.eval_context[tag] = tag
            return True

        find = etree.XPath("//b[p:foo(.)]/c[p:foo(.)]",
                           namespaces={'p' : 'ns'},
                           extensions=[{('ns', 'foo') : check_context}])
        result = find(tree)

        self.assertEquals(result, [tree.getroot()[1][0]])
        self.assertEquals(check_call, {'b':None, 'c':'b'})

    def test_xpath_eval_context_clear(self):
        tree = self.parse('<root><a/><b><c/></b></root>')

        check_call = {}
        def check_context(ctxt):
            check_call["done"] = True
            # context must be empty for each new evaluation
            self.assertEquals(len(ctxt.eval_context), 0)
            ctxt.eval_context["test"] = True
            return True

        find = etree.XPath("//b[p:foo()]",
                           namespaces={'p' : 'ns'},
                           extensions=[{('ns', 'foo') : check_context}])
        result = find(tree)

        self.assertEquals(result, [tree.getroot()[1]])
        self.assertEquals(check_call["done"], True)

        check_call.clear()
        find = etree.XPath("//b[p:foo()]",
                           namespaces={'p' : 'ns'},
                           extensions=[{('ns', 'foo') : check_context}])
        result = find(tree)

        self.assertEquals(result, [tree.getroot()[1]])
        self.assertEquals(check_call["done"], True)

    def test_xpath_variables(self):
        x = self.parse('<a attr="true"/>')
        e = etree.XPathEvaluator(x)

        expr = "/a[@attr=$aval]"
        r = e(expr, aval=1)
        self.assertEquals(0, len(r))

        r = e(expr, aval="true")
        self.assertEquals(1, len(r))
        self.assertEquals("true", r[0].get('attr'))

        r = e(expr, aval=True)
        self.assertEquals(1, len(r))
        self.assertEquals("true", r[0].get('attr'))

    def test_xpath_variables_nodeset(self):
        x = self.parse('<a attr="true"/>')
        e = etree.XPathEvaluator(x)

        element = etree.Element("test-el")
        etree.SubElement(element, "test-sub")
        expr = "$value"
        r = e(expr, value=element)
        self.assertEquals(1, len(r))
        self.assertEquals(element.tag, r[0].tag)
        self.assertEquals(element[0].tag, r[0][0].tag)

    def test_xpath_extensions_mix(self):
        x = self.parse('<a attr="true"><test/></a>')

        class LocalException(Exception):
            pass

        def foo(evaluator, a, varval):
            etree.Element("DUMMY")
            if varval == 0:
                raise LocalException
            elif varval == 1:
                return ()
            elif varval == 2:
                return None
            elif varval == 3:
                return a[0][0]
            a = a[0]
            if a.get("attr") == str(varval):
                return a
            else:
                return etree.Element("NODE")

        extension = {(None, 'foo'): foo}
        e = etree.XPathEvaluator(x, extensions=[extension])
        del x

        self.assertRaises(LocalException, e, "foo(., 0)")
        self.assertRaises(LocalException, e, "foo(., $value)", value=0)

        r = e("foo(., $value)", value=1)
        self.assertEqual(len(r), 0)

        r = e("foo(.,  1)")
        self.assertEqual(len(r), 0)

        r = e("foo(., $value)", value=2)
        self.assertEqual(len(r), 0)

        r = e("foo(., $value)", value=3)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].tag, "test")

        r = e("foo(., $value)", value="false")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].tag, "NODE")

        r = e("foo(., 'false')")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].tag, "NODE")

        r = e("foo(., 'true')")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].tag, "a")
        self.assertEqual(r[0][0].tag, "test")

        r = e("foo(., $value)", value="true")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].tag, "a")

        self.assertRaises(LocalException, e, "foo(., 0)")
        self.assertRaises(LocalException, e, "foo(., $value)", value=0)


class ETreeXPathClassTestCase(HelperTestCase):
    "Tests for the XPath class"
    def test_xpath_compile_doc(self):
        x = self.parse('<a attr="true"/>')

        expr = etree.XPath("/a[@attr != 'true']")
        r = expr(x)
        self.assertEquals(0, len(r))

        expr = etree.XPath("/a[@attr = 'true']")
        r = expr(x)
        self.assertEquals(1, len(r))

        expr = etree.XPath( expr.path )
        r = expr(x)
        self.assertEquals(1, len(r))

    def test_xpath_compile_element(self):
        x = self.parse('<a><b/><c/></a>')
        root = x.getroot()

        expr = etree.XPath("./b")
        r = expr(root)
        self.assertEquals(1, len(r))
        self.assertEquals('b', r[0].tag)

        expr = etree.XPath("./*")
        r = expr(root)
        self.assertEquals(2, len(r))

    def test_xpath_compile_vars(self):
        x = self.parse('<a attr="true"/>')

        expr = etree.XPath("/a[@attr=$aval]")
        r = expr(x, aval=False)
        self.assertEquals(0, len(r))

        r = expr(x, aval=True)
        self.assertEquals(1, len(r))

    def test_xpath_compile_error(self):
        self.assertRaises(SyntaxError, etree.XPath, '\\fad')

    def test_xpath_elementtree_error(self):
        self.assertRaises(ValueError, etree.XPath('*'), etree.ElementTree())


class ETreeXPathExsltTestCase(HelperTestCase):
    "Tests for the EXSLT support in XPath (requires libxslt 1.1.25+)"

    NSMAP = dict(
        date = "http://exslt.org/dates-and-times",
        math = "http://exslt.org/math",
        set  = "http://exslt.org/sets",
        str  = "http://exslt.org/strings",
        )

    def test_xpath_exslt_functions_date(self):
        tree = self.parse('<a><b>2009-11-12</b><b>2008-12-11</b></a>')

        match_dates = tree.xpath('//b[date:year(string()) = 2009]',
                                 namespaces=self.NSMAP)
        self.assertTrue(match_dates, str(match_dates))
        self.assertEquals(len(match_dates), 1, str(match_dates))
        self.assertEquals(match_dates[0].text, '2009-11-12')

    def test_xpath_exslt_functions_strings(self):
        tree = self.parse('<a><b>2009-11-12</b><b>2008-12-11</b></a>')

        match_date = tree.xpath('str:replace(//b[1], "-", "*")',
                                namespaces=self.NSMAP)
        self.assertTrue(match_date, str(match_date))
        self.assertEquals(match_date, '2009*11*12')


class ETreeETXPathClassTestCase(HelperTestCase):
    "Tests for the ETXPath class"
    def test_xpath_compile_ns(self):
        x = self.parse('<a><b xmlns="nsa"/><b xmlns="nsb"/></a>')

        expr = etree.ETXPath("/a/{nsa}b")
        r = expr(x)
        self.assertEquals(1, len(r))
        self.assertEquals('{nsa}b', r[0].tag)

        expr = etree.ETXPath("/a/{nsb}b")
        r = expr(x)
        self.assertEquals(1, len(r))
        self.assertEquals('{nsb}b', r[0].tag)

    # disabled this test as non-ASCII characters in namespace URIs are
    # not acceptable
    def _test_xpath_compile_unicode(self):
        x = self.parse(_bytes('<a><b xmlns="http://nsa/\\uf8d2"/><b xmlns="http://nsb/\\uf8d1"/></a>'
                              ).decode("unicode_escape"))

        expr = etree.ETXPath(_bytes("/a/{http://nsa/\\uf8d2}b").decode("unicode_escape"))
        r = expr(x)
        self.assertEquals(1, len(r))
        self.assertEquals(_bytes('{http://nsa/\\uf8d2}b').decode("unicode_escape"), r[0].tag)

        expr = etree.ETXPath(_bytes("/a/{http://nsb/\\uf8d1}b").decode("unicode_escape"))
        r = expr(x)
        self.assertEquals(1, len(r))
        self.assertEquals(_bytes('{http://nsb/\\uf8d1}b').decode("unicode_escape"), r[0].tag)

SAMPLE_XML = etree.parse(BytesIO("""
<body>
  <tag>text</tag>
  <section>
    <tag>subtext</tag>
  </section>
  <tag />
  <tag />
</body>
"""))

def tag(elem):
    return elem.tag

def tag_or_value(elem):
    return getattr(elem, 'tag', elem)

def stringTest(ctxt, s1):
    return "Hello "+s1

def stringListTest(ctxt, s1):
    return ["Hello "] + list(s1) +  ["!"]
    
def floatTest(ctxt, f1):
    return f1+4

def booleanTest(ctxt, b1):
    return not b1
    
def setTest(ctxt, st1):
    return st1[0]
    
def setTest2(ctxt, st1):
    return st1[0:2]

def argsTest1(ctxt, s, f, b, st):
    return ", ".join(map(str, (s, f, b, list(map(tag, st)))))

def argsTest2(ctxt, st1, st2):
    st1.extend(st2)
    return st1

def resultTypesTest(ctxt):
    return [None,None]

def resultTypesTest2(ctxt):
    return resultTypesTest
    
uri = "http://www.example.com/"

extension = {(None, 'stringTest'): stringTest,
             (None, 'stringListTest'): stringListTest,
             (None, 'floatTest'): floatTest,
             (None, 'booleanTest'): booleanTest,
             (None, 'setTest'): setTest,
             (None, 'setTest2'): setTest2,
             (None, 'argsTest1'): argsTest1,
             (None, 'argsTest2'): argsTest2,
             (None, 'resultTypesTest'): resultTypesTest,
             (None, 'resultTypesTest2'): resultTypesTest2,}

def xpath():
    """
    Test xpath extension functions.
    
    >>> root = SAMPLE_XML
    >>> e = etree.XPathEvaluator(root, extensions=[extension])
    >>> e("stringTest('you')")
    'Hello you'
    >>> e(_bytes("stringTest('\\\\xe9lan')").decode("unicode_escape"))
    u'Hello \\xe9lan'
    >>> e("stringTest('you','there')")
    Traceback (most recent call last):
    ...
    TypeError: stringTest() takes exactly 2 arguments (3 given)
    >>> e("floatTest(2)")
    6.0
    >>> e("booleanTest(true())")
    False
    >>> list(map(tag, e("setTest(/body/tag)")))
    ['tag']
    >>> list(map(tag, e("setTest2(/body/*)")))
    ['tag', 'section']
    >>> list(map(tag_or_value, e("stringListTest(/body/tag)")))
    ['Hello ', 'tag', 'tag', 'tag', '!']
    >>> e("argsTest1('a',1.5,true(),/body/tag)")
    "a, 1.5, True, ['tag', 'tag', 'tag']"
    >>> list(map(tag, e("argsTest2(/body/tag, /body/section)")))
    ['tag', 'section', 'tag', 'tag']
    >>> e("resultTypesTest()")
    Traceback (most recent call last):
    ...
    XPathResultError: This is not a supported node-set result: None
    >>> try:
    ...     e("resultTypesTest2()")
    ... except etree.XPathResultError:
    ...     print("Got error")
    Got error
    """

if sys.version_info[0] >= 3:
    xpath.__doc__ = xpath.__doc__.replace(" u'", " '")
    xpath.__doc__ = xpath.__doc__.replace(" XPathResultError",
                                          " lxml.etree.XPathResultError")
    xpath.__doc__ = xpath.__doc__.replace(" exactly 2 arguments",
                                          " exactly 2 positional arguments")

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeXPathTestCase)])
    suite.addTests([unittest.makeSuite(ETreeXPathClassTestCase)])
    if etree.LIBXSLT_COMPILED_VERSION >= (1,1,25):
        suite.addTests([unittest.makeSuite(ETreeXPathExsltTestCase)])
    suite.addTests([unittest.makeSuite(ETreeETXPathClassTestCase)])
    suite.addTests([doctest.DocTestSuite()])
    suite.addTests(
        [make_doctest('../../../doc/xpathxslt.txt')])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
