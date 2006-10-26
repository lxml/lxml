import sys, copy
from itertools import *
from StringIO import StringIO

from lxml import etree, objectify

parser = etree.XMLParser(remove_blank_text=True)
lookup = etree.ElementNamespaceClassLookup(objectify.ObjectifyElementClassLookup())
parser.setElementClassLookup(lookup)

import benchbase
from benchbase import with_attributes, with_text, onlylib, serialized

############################################################
# Benchmarks
############################################################

class BenchMark(benchbase.BenchMarkBase):
    def __init__(self, lib):
        benchbase.BenchMarkBase.__init__(self, lib, parser)

    def bench_attributes(self, root):
        "1 2 4"
        for i in repeat(None, 3000):
            root.zzzzz

    def bench_attributes_deep(self, root):
        "1 2 4"
        for i in repeat(None, 3000):
            root.zzzzz['{cdefg}z00000']

    def bench_attributes_deep_cached(self, root):
        "1 2 4"
        cache1 = root.zzzzz
        cache2 = cache1['{cdefg}z00000']
        for i in repeat(None, 3000):
            root.zzzzz['{cdefg}z00000']

    def bench_objectpath(self, root):
        "1 2 4"
        path = objectify.ObjectPath(".zzzzz")
        for i in repeat(None, 3000):
            path(root)

    def bench_objectpath_deep(self, root):
        "1 2 4"
        path = objectify.ObjectPath(".zzzzz.{cdefg}z00000")
        for i in repeat(None, 3000):
            path(root)

    def bench_objectpath_deep_cached(self, root):
        "1 2 4"
        cache1 = root.zzzzz
        cache2 = cache1['{cdefg}z00000']
        path = objectify.ObjectPath(".zzzzz.{cdefg}z00000")
        for i in repeat(None, 3000):
            path(root)

if __name__ == '__main__':
    benchbase.main(BenchMark)
