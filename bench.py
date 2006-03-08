import sys, string, timeit
from itertools import *

from lxml import etree

_etrees = [etree]

### cannot test these in all cases anyway (different semantics)
##
## try:
##     from elementtree import ElementTree as ET
##     _etrees.append(ET)
## except:
##     ET = None

## try:
##     import cElementTree as cET
##     _etrees.append(cET)
## except:
##     cET = None


class BenchMarkBase(object):
    atoz = string.ascii_lowercase

    def __init__(self, etree):
        self.etree = etree
        self.lib_name = etree.__name__.split('.')[-1]

    def setup(self, trees=()):
        if not trees:
            trees = self._all_trees()

        for tree in trees:
            setup = getattr(self, '_setup_tree%d' % tree)
            root = setup()
            setattr(self, '_root%d' % tree, root)
            setattr(self, '_tree%d' % tree, self.etree.ElementTree(root))

    def _all_trees(self):
        all_trees = []
        for name in dir(self):
            if name.startswith('_setup_tree'):
                all_trees.append(int(name[11:]))
        return all_trees

    def _setup_tree1(self):
        "tree with some 2nd level and loads of 3rd level children"
        root = self.etree.Element('{a}root')
        atoz = self.atoz
        SubElement = self.etree.SubElement
        for ch1 in atoz:
            el = SubElement(root, "{b}"+ch1)
            for ch2 in atoz:
                for i in range(100):
                    SubElement(el, "{c}%s%03d" % (ch2, i))
        return root

    def _setup_tree2(self):
        "tree with loads of 2nd level and fewer 3rd level children"
        root = self.etree.Element('{x}root')
        atoz = self.atoz
        SubElement = self.etree.SubElement
        for ch1 in atoz:
            for i in range(100):
                el = SubElement(root, "{y}%s%03d" % (ch1, i))
                for ch2 in atoz:
                    SubElement(el, "{z}"+ch2)
        return root

    def _setup_tree3(self):
        "deep tree with constant number of children per node"
        root = self.etree.Element('{x}root')
        SubElement = self.etree.SubElement
        tags = self._tags
        children = [root]
        for i in range(10):
            children = list(imap(SubElement, children*3, tags()))
        return root

    def _tags(ns='y'):
        for i in count():
            yield "{%s}z%d" % (ns,i)

    def cleanup(self):
        for name in dir(self):
            if name.startswith('_root') or name.startswith('_tree'):
                delattr(self, name)

    def benchmarks(self):
        """Returns a list of all benchmarks.

        A benchmark is a tuple containing a method name and a list of tree
        numbers.  Trees are prepared by the setup function.
        """
        all_trees = self._all_trees()
        benchmarks = []
        for name in dir(self):
            if not name.startswith('bench_'):
                continue
            method = getattr(self, name)
            if method.__doc__:
                tree_sets = method.__doc__.split()
            else:
                tree_sets = ()
            if tree_sets:
                for tree_set in tree_sets:
                    benchmarks.append((name, map(int, tree_set.split(','))))
            else:
                try:
                    function = getattr(method, 'im_func', method)
                    arg_count = method.func_code.co_argcount / 2
                except AttributeError:
                    arg_count = 1
                for trees in self._permutations(all_trees, arg_count):
                    benchmarks.append((name, trees))
        return benchmarks

    def _permutations(self, seq, count):
        def _permutations(prefix, remainder, count):
            if count == 0:
                return [ prefix[:] ]
            count -= 1
            perms = []
            prefix.append(None)
            for pos, el in enumerate(remainder):
                new_remainder = remainder[:pos] + remainder[pos+1:]
                prefix[-1] = el
                perms.extend( _permutations(prefix, new_remainder, count) )
            prefix.pop()
            return perms
        return _permutations([], seq, count)


############################################################
# Benchmarks:
############################################################

class BenchMark(BenchMarkBase):
    def bench_append_from_document(self, tree1, root1, tree2, root2):
        # == "1,2 2,3 1,3 3,1 3,2 2,1" # trees 1 and 2, or 2 and 3, or ...
        for el in root2:
            root1.append(root2[0])

    def bench_insert_from_document(self, tree1, root1, tree2, root2):
        for el in root2:
            root1.insert(len(root1)/2, root2[0])

    def bench_rotate_children(self, tree, root):
        # == "1 2 3" # runs on any single tree independently
        for i in range(100):
            root.append(root[0])

    def bench_reorder(self, tree, root):
        for i in range(1,len(root)/2):
            root[-i:-i] = [ root[0] ]

    def bench_clear(self, tree, root):
        root.clear()


if __name__ == '__main__':
    benchmark_suites = map(BenchMark, _etrees)

    # sorted by name and tree tuple
    benchmarks = [ sorted(b.benchmarks()) for b in benchmark_suites ]

    if len(sys.argv) > 1:
        selected = []
        for name in sys.argv[1:]:
            if not name.startswith('bench_'):
                name = 'bench_' + name
            selected.append(name)
        benchmarks = [ [ b for b in bs if b[0] in selected ]
                       for bs in benchmarks ]

    for bench_calls in izip(*benchmarks):
        for lib, config in enumerate(izip(bench_calls, benchmark_suites)):
            (bench_name, tree_set), bench = config

            bench_args  = ', '.join("bench._tree%d, bench._root%d" % (tree, tree)
                                    for tree in tree_set)

            timer = timeit.Timer(
                "bench.%s(%s)" % (bench_name, bench_args),
                "from __main__ import bench ; bench.setup(%s) ; gc.enable()" % \
                    str(tuple(tree_set))
                )

            print "%-12s %-25s (T%-6s)" % (bench.lib_name, bench_name[6:],
                                           ',T'.join(imap(str, tree_set))[:6]),
            sys.stdout.flush()

            result = timer.repeat(3, 50)

            bench.cleanup()

            for t in result:
                print "%8.4f" % t,
            print "msec/pass, best: %8.4f" % min(result)

        if len(benchmark_suites) > 1:
            print # empty line between different benchmarks
