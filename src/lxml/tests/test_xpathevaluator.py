# -*- coding: utf-8 -*-

"""
Test cases related to XPath evaluation and the XPath class
"""

import unittest, doctest
from StringIO import StringIO

from common_imports import etree, HelperTestCase

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
        expected = ['nan', '1.#qnan']
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

    def test_xpath_list_attribute(self):
        tree = self.parse('<a b="B" c="C"/>')
        self.assertEquals(['B'],
                          tree.xpath('/a/@b'))

    def test_xpath_list_comment(self):
        tree = self.parse('<a><!-- Foo --></a>')
        self.assertEquals(['<!-- Foo -->'],
                          map(repr, tree.xpath('/a/node()')))

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
            tree.xpath('//foo:b', {'foo': 'uri:a'}))
        self.assertEquals(
            [],
            tree.xpath('//foo:b', {'foo': 'uri:c'}))
        self.assertEquals(
            [root[0]],
            root.xpath('//baz:b', {'baz': 'uri:a'}))

    def test_xpath_ns_none(self):
        tree = self.parse('<a xmlns="uri:a"><b></b></a>')
        root = tree.getroot()
        self.assertRaises(
            TypeError,
            root.xpath, '//b', {None: 'uri:a'})

    def test_xpath_error(self):
        tree = self.parse('<a/>')
        self.assertRaises(SyntaxError, tree.xpath, '\\fad')

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
            e.evaluate('//a'))

    def test_xpath_evaluator_tree(self):
        tree = self.parse('<a><b><c></c></b></a>')
        child_tree = etree.ElementTree(tree.getroot()[0])
        e = etree.XPathEvaluator(child_tree)
        self.assertEquals(
            [],
            e.evaluate('a'))
        root = child_tree.getroot()
        self.assertEquals(
            [root[0]],
            e.evaluate('c'))

    def test_xpath_evaluator_element(self):
        tree = self.parse('<a><b><c></c></b></a>')
        root = tree.getroot()
        e = etree.XPathEvaluator(root[0])
        self.assertEquals(
            [root[0][0]],
            e.evaluate('c'))
        
    def test_xpath_extensions(self):
        def foo(evaluator, a):
            return 'hello %s' % a
        extension = {(None, 'foo'): foo}
        tree = self.parse('<a><b></b></a>')
        e = etree.XPathEvaluator(tree, None, [extension])
        self.assertEquals(
            "hello you", e.evaluate("foo('you')"))

    def test_xpath_extensions_wrong_args(self):
        def foo(evaluator, a, b):
            return "hello %s and %s" % (a, b)
        extension = {(None, 'foo'): foo}
        tree = self.parse('<a><b></b></a>')
        e = etree.XPathEvaluator(tree, extensions=[extension])
        self.assertRaises(TypeError, e.evaluate, "foo('you')")

    def test_xpath_extensions_error(self):
        def foo(evaluator, a):
            return 1/0
        extension = {(None, 'foo'): foo}
        tree = self.parse('<a/>')
        e = etree.XPathEvaluator(tree, None, [extension])
        self.assertRaises(ZeroDivisionError, e.evaluate, "foo('test')")

    def test_xpath_extensions_nodes(self):
        def f(evaluator, arg):
            r = etree.Element('results')
            b = etree.SubElement(r, 'result')
            b.text = 'Hoi'
            b = etree.SubElement(r, 'result')
            b.text = 'Dag'
            return r

        x = self.parse('<a/>')
        e = etree.XPathEvaluator(x, None, [{(None, 'foo'): f}])
        r = e.evaluate("foo('World')/result")
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
        e = etree.XPathEvaluator(x, None, [{(None, 'foo'): f}])
        r = e.evaluate("foo(/*)/result")
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
        e = etree.XPathEvaluator(x, None, [{(None, 'foo'): f}])
        r = e.evaluate("foo(/*)/result")
        self.assertEquals(3, len(r))
        self.assertEquals('Hoi',  r[0].text)
        self.assertEquals('Dag',  r[1].text)
        self.assertEquals('Honk', r[2].text)

    def test_xpath_variables(self):
        x = self.parse('<a attr="true"/>')
        e = etree.XPathEvaluator(x)

        expr = "/a[@attr=$aval]"
        r = e.evaluate(expr, aval=1)
        self.assertEquals(0, len(r))

        r = e.evaluate(expr, aval="true")
        self.assertEquals(1, len(r))
        self.assertEquals("true", r[0].get('attr'))

        r = e.evaluate(expr, aval=True)
        self.assertEquals(1, len(r))
        self.assertEquals("true", r[0].get('attr'))

    def test_xpath_variables_nodeset(self):
        x = self.parse('<a attr="true"/>')
        e = etree.XPathEvaluator(x)

        element = etree.Element("test-el")
        etree.SubElement(element, "test-sub")
        expr = "$value"
        r = e.evaluate(expr, value=element)
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

        self.assertRaises(LocalException, e.evaluate, "foo(., 0)")
        self.assertRaises(LocalException, e.evaluate, "foo(., $value)", value=0)

        r = e.evaluate("foo(., $value)", value=1)
        self.assertEqual(len(r), 0)

        r = e.evaluate("foo(.,  1)")
        self.assertEqual(len(r), 0)

        r = e.evaluate("foo(., $value)", value=2)
        self.assertEqual(len(r), 0)

        r = e.evaluate("foo(., $value)", value=3)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].tag, "test")

        r = e.evaluate("foo(., $value)", value="false")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].tag, "NODE")

        r = e.evaluate("foo(., 'false')")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].tag, "NODE")

        r = e.evaluate("foo(., 'true')")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].tag, "a")
        self.assertEqual(r[0][0].tag, "test")

        r = e.evaluate("foo(., $value)", value="true")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].tag, "a")

        self.assertRaises(LocalException, e.evaluate, "foo(., 0)")
        self.assertRaises(LocalException, e.evaluate, "foo(., $value)", value=0)


class ETreeXPathClassTestCase(HelperTestCase):
    "Tests for the XPath class"
    def test_xpath_compile_doc(self):
        x = self.parse('<a attr="true"/>')

        expr = etree.XPath("/a[@attr != 'true']")
        r = expr.evaluate(x)
        self.assertEquals(0, len(r))

        expr = etree.XPath("/a[@attr = 'true']")
        r = expr.evaluate(x)
        self.assertEquals(1, len(r))

        expr = etree.XPath( expr.path )
        r = expr.evaluate(x)
        self.assertEquals(1, len(r))

    def test_xpath_compile_element(self):
        x = self.parse('<a><b/><c/></a>')
        root = x.getroot()

        expr = etree.XPath("./b")
        r = expr.evaluate(root)
        self.assertEquals(1, len(r))
        self.assertEquals('b', r[0].tag)

        expr = etree.XPath("./*")
        r = expr.evaluate(root)
        self.assertEquals(2, len(r))

    def test_xpath_compile_vars(self):
        x = self.parse('<a attr="true"/>')

        expr = etree.XPath("/a[@attr=$aval]")
        r = expr.evaluate(x, aval=False)
        self.assertEquals(0, len(r))

        r = expr.evaluate(x, aval=True)
        self.assertEquals(1, len(r))

    def test_xpath_compile_error(self):
        self.assertRaises(SyntaxError, etree.XPath, '\\fad')

    def test_xpath_elementtree_error(self):
        self.assertRaises(ValueError, etree.XPath('*'), etree.ElementTree())

class ETreeETXPathClassTestCase(HelperTestCase):
    "Tests for the ETXPath class"
    def test_xpath_compile_ns(self):
        x = self.parse('<a><b xmlns="nsa"/><b xmlns="nsb"/></a>')

        expr = etree.ETXPath("/a/{nsa}b")
        r = expr.evaluate(x)
        self.assertEquals(1, len(r))
        self.assertEquals('{nsa}b', r[0].tag)

        expr = etree.ETXPath("/a/{nsb}b")
        r = expr.evaluate(x)
        self.assertEquals(1, len(r))
        self.assertEquals('{nsb}b', r[0].tag)

    def test_xpath_compile_unicode(self):
        x = self.parse(u'<a><b xmlns="nsa\uf8d2"/><b xmlns="nsb\uf8d1"/></a>')

        expr = etree.ETXPath(u"/a/{nsa\uf8d2}b")
        r = expr.evaluate(x)
        self.assertEquals(1, len(r))
        self.assertEquals(u'{nsa\uf8d2}b', r[0].tag)

        expr = etree.ETXPath(u"/a/{nsb\uf8d1}b")
        r = expr.evaluate(x)
        self.assertEquals(1, len(r))
        self.assertEquals(u'{nsb\uf8d1}b', r[0].tag)

SAMPLE_XML = etree.parse(StringIO("""
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

def stringTest(ctxt, s1):
    return "Hello "+s1
    
def floatTest(ctxt, f1):
    return f1+4

def booleanTest(ctxt, b1):
    return not b1
    
def setTest(ctxt, st1):
    return st1[0]
    
def setTest2(ctxt, st1):
    return st1[0:2]

def argsTest1(ctxt, s, f, b, st):
    return ", ".join(map(str, (s, f, b, map(tag, st))))

def argsTest2(ctxt, st1, st2):
    st1.extend(st2)
    return st1

def resultTypesTest(ctxt):
    return ["x","y"]

def resultTypesTest2(ctxt):
    return resultTypesTest
    
uri = "http://www.example.com/"

extension = {(None, 'stringTest'): stringTest,
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
    >>> e = etree.XPathEvaluator(root, None, [extension])
    >>> e.evaluate("stringTest('you')")
    'Hello you'
    >>> e.evaluate(u"stringTest('\xe9lan')")
    u'Hello \\xe9lan'
    >>> e.evaluate("stringTest('you','there')")
    Traceback (most recent call last):
    ...
    TypeError: stringTest() takes exactly 2 arguments (3 given)
    >>> e.evaluate("floatTest(2)")
    6.0
    >>> e.evaluate("booleanTest(true())")
    False
    >>> map(tag, e.evaluate("setTest(/body/tag)"))
    ['tag']
    >>> map(tag, e.evaluate("setTest2(/body/*)"))
    ['tag', 'section']
    >>> e.evaluate("argsTest1('a',1.5,true(),/body/tag)")
    "a, 1.5, True, ['tag', 'tag', 'tag']"
    >>> map(tag, e.evaluate("argsTest2(/body/tag, /body/section)"))
    ['tag', 'section', 'tag', 'tag']
    >>> e.evaluate("resultTypesTest()")
    Traceback (most recent call last):
    ...
    XPathResultError: This is not a node: x
    >>> try:
    ...     e.evaluate("resultTypesTest2()")
    ... except etree.XPathResultError:
    ...     print "Got error"
    Got error
    """
   
def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeXPathTestCase)])
    suite.addTests([unittest.makeSuite(ETreeXPathClassTestCase)])
    suite.addTests([unittest.makeSuite(ETreeETXPathClassTestCase)])
    suite.addTests([doctest.DocTestSuite()])
    suite.addTests(
        [doctest.DocFileSuite('../../../doc/xpathxslt.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
