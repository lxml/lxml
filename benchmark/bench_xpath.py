import sys, copy
from itertools import *
from StringIO import StringIO

import benchbase
from benchbase import with_attributes, with_text, onlylib, serialized, children

############################################################
# Benchmarks
############################################################

class XPathBenchMark(benchbase.BenchMarkBase):
    @onlylib('lxe')
    @children
    def bench_xpath_class(self, children):
        xpath = self.etree.XPath("./*[0]")
        for child in children:
            xpath(child)

    @onlylib('lxe')
    @children
    def bench_xpath_class_repeat(self, children):
        for child in children:
            xpath = self.etree.XPath("./*[0]")
            xpath(child)

    @onlylib('lxe')
    def bench_xpath_element(self, root):
        xpath = self.etree.XPathElementEvaluator(root)
        for child in root:
            xpath.evaluate("./*[0]")

    @onlylib('lxe')
    @children
    def bench_xpath_method(self, children):
        for child in children:
            child.xpath("./*[0]")

    @onlylib('lxe')
    @children
    def bench_xpath_old_extensions(self, children):
        def return_child(_, elements):
            if elements:
                return elements[0][0]
            else:
                return ()
        extensions = {("test", "child") : return_child}
        xpath = self.etree.XPath("t:child(.)", namespaces={"test":"t"},
                                 extensions=extensions)
        for child in children:
            xpath(child)

    @onlylib('lxe')
    @children
    def bench_xpath_extensions(self, children):
        def return_child(_, elements):
            if elements:
                return elements[0][0]
            else:
                return ()
        self.etree.FunctionNamespace("testns")["t"] = return_child

        try:
            xpath = self.etree.XPath("test:t(.)", {"test":"testns"})
            for child in children:
                xpath(child)
        finally:
            del self.etree.FunctionNamespace("testns")["t"]

if __name__ == '__main__':
    benchbase.main(XPathBenchMark)
