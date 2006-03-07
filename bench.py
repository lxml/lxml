import sys, timeit
from itertools import *

from lxml import etree

def atoz():
    return iter('abcdefghijklmnopqrstuvwxyz')

class BenchMark(object):
    ALL_TREES = (1,2)
    def setup(self, trees=ALL_TREES):
        if 1 in trees:
            root = etree.Element('{a}root')
            for ch1 in atoz():
                el = etree.SubElement(root, "{b}"+ch1)
                for ch2 in atoz():
                    for i in range(100):
                        etree.SubElement(el, "{c}%s%03d" % (ch2, i))

            self.root1 = root
            self.tree1 = etree.ElementTree(root)

        if 2 in trees:
            root = etree.Element('{x}root')
            for ch1 in atoz():
                for i in range(100):
                    el = etree.SubElement(root, "{y}%s%03d" % (ch1, i))
                    for ch2 in atoz():
                        etree.SubElement(el, "{z}"+ch2)

            self.root2 = root
            self.tree2 = etree.ElementTree(root)

    def benchmarks(self):
        """Returns a list of all benchmarks.

        A benchmark is a tuple containing a method name and a list of tree
        numbers.  Trees are prepared by the setup function.
        """
        benchmarks = []
        for name in dir(self):
            if not name.startswith('bench_'):
                continue
            method = getattr(self, name)
            tree_sets = method.__doc__.split()
            if tree_sets:
                for tree_set in tree_sets:
                    benchmarks.append((name, sorted(imap(int, tree_set.split(',')))))
            else:
                for tree in bench.ALL_TREES:
                    benchmarks.append((name, [tree]))
        return benchmarks


class LxmlBenchMark(BenchMark):
    def bench_append_from_document(self, tree1, root1, tree2, root2):
        "1,2" # needs trees 1 and 2
        for el in root2:
            root1.append(root2[0])

    def bench_rotate_children(self, tree, root):
        "1 2" # runs on tree 1 or 2 independently
        for i in range(100):
            root[-1] = root[0]

    def bench_reorder(self, tree, root):
        "1 2"
        for i in range(len(root)/2):
            root[-i] = root[0]


if __name__ == '__main__':
    bench = LxmlBenchMark()
    benchmarks = bench.benchmarks()

    if len(sys.argv) > 1:
        selected = [ "bench_%s" % name for name in sys.argv[1:] ]
        benchmarks = [ b for b in benchmarks if b[0] in selected ]

    benchmarks.sort() # by name

    for bench_name, tree_set in benchmarks:
        bench_args  = ', '.join("bench.tree%d, bench.root%d" % (tree, tree)
                                for tree in tree_set)

        timer = timeit.Timer(
            "bench.%s(%s)" % (bench_name, bench_args),
            "from __main__ import bench ; bench.setup(%s)" % str(tuple(tree_set))
            )

        print "%-25s (T%-6s)" % (bench_name[6:], ',T'.join(imap(str, tree_set))[:6]),
        sys.stdout.flush()

        result = timer.repeat(4, 1000)[1:] # run benchmark, but ignore first run

        for t in result:
            print "%8.4f" % t,
        print "msec/pass, avg: %8.4f" % (sum(result) / 3)
