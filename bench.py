import sys, string, time, copy, gc
from itertools import *

class BenchMarkBase(object):
    atoz = string.ascii_lowercase

    def __init__(self, etree):
        self.etree = etree
        self.lib_name = etree.__name__.split('.')[-1]

        self.setup_times = times = []
        for tree in self._all_trees():
            setup = getattr(self, '_setup_tree%d' % tree)
            root, t = setup()
            times.append(t)
            setattr(self, '__root%d' % tree, root)
            def set_property(root):
                setattr(self, '_root%d' % tree,
                        lambda : copy.deepcopy(root))
            set_property(root)

    def setup(self, trees=()):
        if not trees:
            trees = self._all_trees()

        for tree in trees:
            set_property( getattr(self, '__root%d' % tree) )

    def _all_trees(self):
        all_trees = []
        for name in dir(self):
            if name.startswith('_setup_tree'):
                all_trees.append(int(name[11:]))
        return all_trees

    def _setup_tree1(self):
        "tree with 26 2nd level and 520 3rd level children"
        atoz = self.atoz
        SubElement = self.etree.SubElement
        current_time = time.time
        t = current_time()
        root = self.etree.Element('{a}root')
        for ch1 in atoz:
            el = SubElement(root, "{b}"+ch1)
            for ch2 in atoz:
                for i in range(20):
                    SubElement(el, "{c}%s%03d" % (ch2, i))
        t = current_time() - t
        return (root, t)

    def _setup_tree2(self):
        "tree with 520 2nd level and 26 3rd level children"
        atoz = self.atoz
        SubElement = self.etree.SubElement
        current_time = time.time
        t = current_time()
        root = self.etree.Element('{x}root')
        for ch1 in atoz:
            for i in range(20):
                el = SubElement(root, "{y}%s%03d" % (ch1, i))
                for ch2 in atoz:
                    SubElement(el, "{z}"+ch2)
        t = current_time() - t
        return (root, t)

    def _setup_tree3(self):
        "tree of depth 8 with 3 children per node"
        SubElement = self.etree.SubElement
        current_time = time.time
        t = current_time()
        root = self.etree.Element('{x}root')
        children = [root]
        for i in range(7):
            tag_no = count().next
            children = [ SubElement(c, "{y}z%d" % i)
                         for i,c in enumerate(chain(children, children, children)) ]
        t = current_time() - t
        return (root, t)

    def _setup_tree4(self):
        "small tree with 26 2nd level and 2 3rd level children"
        atoz = self.atoz
        SubElement = self.etree.SubElement
        current_time = time.time
        t = current_time()
        root = self.etree.Element('{x}root')
        children = [root]
        for ch1 in atoz:
            el = SubElement(root, "{b}"+ch1)
            SubElement(el, "{c}a")
            SubElement(el, "{c}b")
        t = current_time() - t
        return (root, t)

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
                    arg_count = method.func_code.co_argcount - 1
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
# Benchmarks
############################################################

class BenchMark(BenchMarkBase):
    def bench_append_from_document(self, root1, root2):
        # == "1,2 2,3 1,3 3,1 3,2 2,1" # trees 1 and 2, or 2 and 3, or ...
        for el in root2:
            root1.append(el)

    def bench_insert_from_document(self, root1, root2):
        for el in root2:
            root1.insert(len(root1)/2, el)

    def bench_rotate_children(self, root):
        # == "1 2 3" # runs on any single tree independently
        for i in range(100):
            el = root[0]
            del root[0]
            root.append(el)

    def bench_reorder(self, root):
        for i in range(1,len(root)/2):
            el = root[0]
            del root[0]
            root[-i:-i] = [ el ]

    def bench_reorder_slice(self, root):
        for i in range(1,len(root)/2):
            els = root[0:1]
            del root[0]
            root[-i:-i] = els

    def bench_clear(self, root):
        root.clear()

    def bench_create_subelements(self, root):
        SubElement = self.etree.SubElement
        for child in root:
            SubElement(child, '{test}test')

    def bench_append_elements(self, root):
        Element = self.etree.Element
        for child in root:
            el = Element('{test}test')
            child.append(el)

    def bench_replace_children(self, root):
        Element = self.etree.Element
        for child in root:
            el = Element('{test}test')
            child[:] = [el]

    def bench_remove_children(self, root):
        for child in root:
            root.remove(child)

    def bench_remove_children_reversed(self, root):
        for child in reversed(root[:]):
            root.remove(child)

    def bench_set_attributes(self, root):
        for child in root:
            child.set('a', 'bla')

    def bench_setget_attributes(self, root):
        for child in root:
            child.set('a', 'bla')
        for child in root:
            child.get('a')

    def bench_getchildren(self, root):
        for child in root:
            child.getchildren()

############################################################
# Main program
############################################################

if __name__ == '__main__':
    if len(sys.argv) > 1:
        try:
            sys.argv.remove('-i')
            sys.path.insert(0, 'src')
        except ValueError:
            pass

    from lxml import etree
    _etrees = [etree]

    if len(sys.argv) > 1:
        try:
            sys.argv.remove('-a')
        except ValueError:
            pass
        else:
            try:
                from elementtree import ElementTree as ET
                _etrees.append(ET)
            except ImportError:
                pass

            try:
                import cElementTree as cET
                _etrees.append(cET)
            except ImportError:
                pass

    print "Preparing test suites and trees ..."

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

    import time
    def run_bench(suite, method_name, tree_set):
        current_time = time.time
        call_repeat = range(10)

        call = getattr(suite, method_name)
        tree_builders = [ getattr(suite, '_root%d' % tree)
                          for tree in tree_set ]

        times = []
        for i in range(3):
            gc.collect()
            gc.disable()
            t = 0
            for i in call_repeat:
                args = [ build() for build in tree_builders ]
                t_one_call = current_time()
                call(*args)
                t += current_time() - t_one_call
            t = 1000.0 * t / len(call_repeat)
            times.append(t)
            gc.enable()
        return times


    print "Running benchmark on", ', '.join(b.lib_name
                                            for b in benchmark_suites)
    print

    print "Setup times for trees in seconds:"
    for b in benchmark_suites:
        print "%-12s : " % b.lib_name, ', '.join("%9.4f" % t
                                                 for t in b.setup_times)
    print

    for bench_calls in izip(*benchmarks):
        for lib, config in enumerate(izip(benchmark_suites, bench_calls)):
            bench, (bench_name, tree_set) = config

            print "%-12s %-25s (T%-6s)" % (bench.lib_name, bench_name[6:],
                                           ',T'.join(imap(str, tree_set))[:6]),
            sys.stdout.flush()

            result = run_bench(bench, bench_name, tree_set)

            for t in result:
                print "%9.4f" % t,
            print "msec/pass, best: %9.4f" % min(result)

        if len(benchmark_suites) > 1:
            print # empty line between different benchmarks
