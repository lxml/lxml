from lxml.tests.test_etree import HelperTestCase
import unittest
from lxml import etree

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
        self.assertEquals('nan', str(tree.xpath('number(/a)')))
        
    def test_xpath_string(self):
        tree = self.parse('<a>Foo</a>')
        self.assertEquals('Foo',
                          tree.xpath('string(/a/text())'))

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
                          tree.xpath('/a/node()'))

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

    def test_xpath_error(self):
        tree = self.parse('<a/>')
        self.assertRaises(SyntaxError, tree.xpath, '\\fad')

    def test_xpath_evaluator(self):
        tree = self.parse('<a><b><c></c></b></a>')
        e = etree.XPathEvaluator(tree)
        root = tree.getroot()
        self.assertEquals(
            [root],
            e.evaluate('//a'))

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
        e = etree.XPathEvaluator(tree, None, [extension])
        self.assertRaises(TypeError, e.evaluate, "foo('you')")

    def test_xpath_extensions_error(self):
        def foo(evaluator, a):
            return 1/0
        extension = {(None, 'foo'): foo}
        tree = self.parse('<a/>')
        e = etree.XPathEvaluator(tree, None, [extension])
        self.assertRaises(ZeroDivisionError, e.evaluate, "foo('test')")

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeXPathTestCase)])    
    return suite

if __name__ == '__main__':
    unittest.main()
