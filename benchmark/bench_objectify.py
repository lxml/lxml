import sys, copy
from itertools import *
from StringIO import StringIO

import benchbase
from benchbase import (with_attributes, with_text, onlylib,
                       serialized, children, nochange)

############################################################
# Benchmarks
############################################################

class BenchMark(benchbase.TreeBenchMark):
    repeat100  = range(100)
    repeat1000 = range(1000)
    repeat3000 = range(3000)

    def __init__(self, lib):
        from lxml import etree, objectify
        self.objectify = objectify
        parser = etree.XMLParser(remove_blank_text=True)
        lookup = objectify.ObjectifyElementClassLookup()
        parser.setElementClassLookup(lookup)
        super(BenchMark, self).__init__(etree, parser)

    @nochange
    def bench_attribute(self, root):
        "1 2 4"
        for i in self.repeat3000:
            root.zzzzz

    def bench_attribute_assign_int(self, root):
        "1 2 4"
        for i in self.repeat3000:
            root.XYZ = 5

    def bench_attribute_assign_string(self, root):
        "1 2 4"
        for i in self.repeat3000:
            root.XYZ = "5"

    @nochange
    def bench_attribute_cached(self, root):
        "1 2 4"
        cache = root.zzzzz
        for i in self.repeat3000:
            root.zzzzz

    @nochange
    def bench_attributes_deep(self, root):
        "1 2 4"
        for i in self.repeat3000:
            root.zzzzz['{cdefg}a00001']

    @nochange
    def bench_attributes_deep_cached(self, root):
        "1 2 4"
        cache1 = root.zzzzz
        cache2 = cache1['{cdefg}a00001']
        for i in self.repeat3000:
            root.zzzzz['{cdefg}a00001']

    @nochange
    def bench_objectpath(self, root):
        "1 2 4"
        path = self.objectify.ObjectPath(".zzzzz")
        for i in self.repeat3000:
            path(root)

    @nochange
    def bench_objectpath_deep(self, root):
        "1 2 4"
        path = self.objectify.ObjectPath(".zzzzz.{cdefg}a00001")
        for i in self.repeat3000:
            path(root)

    @nochange
    def bench_objectpath_deep_cached(self, root):
        "1 2 4"
        cache1 = root.zzzzz
        cache2 = cache1['{cdefg}a00001']
        path = self.objectify.ObjectPath(".zzzzz.{cdefg}a00001")
        for i in self.repeat3000:
            path(root)

    @with_text(text=True, utext=True, no_text=True)
    def bench_annotate(self, root):
        self.objectify.annotate(root)

    @nochange
    def bench_descendantpaths(self, root):
        root.descendantpaths()

    @nochange
    @with_text(text=True)
    def bench_type_inference(self, root):
        "1 2 4"
        el = root.aaaaa
        for i in self.repeat1000:
            el.getchildren()

    @nochange
    @with_text(text=True)
    def bench_type_inference_annotated(self, root):
        "1 2 4"
        el = root.aaaaa
        self.objectify.annotate(el)
        for i in self.repeat1000:
            el.getchildren()

    @nochange
    @children
    def bench_elementmaker(self, children):
        E = self.objectify.E
        for child in children:
            root = E.this(
                "test",
                E.will(
                    E.do("nothing"),
                    E.special,
                    )
                )

if __name__ == '__main__':
    benchbase.main(BenchMark)
