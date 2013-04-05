import sys, re, string, time, copy, gc
from itertools import *
import time

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO

try:
    izip
except NameError:
    izip = zip  # Py3

def exec_(code, glob):
    if sys.version_info[0] >= 3:
        exec(code, glob)
    else:
        exec("exec code in glob")


TREE_FACTOR = 1 # increase tree size with '-l / '-L' cmd option

_TEXT  = "some ASCII text" * TREE_FACTOR
_UTEXT = u"some klingon: \F8D2" * TREE_FACTOR
_ATTRIBUTES = {
    '{attr}test1' : _TEXT,
    '{attr}test2' : _TEXT,
    'bla1'        : _TEXT,
    'bla2'        : _TEXT,
    'bla3'        : _TEXT
    }


def initArgs(argv):
    global TREE_FACTOR
    try:
        argv.remove('-l')
        # use large trees
        TREE_FACTOR *= 2
    except ValueError:
        pass

    try:
        argv.remove('-L')
        # use LARGE trees
        TREE_FACTOR *= 2
    except ValueError:
        pass

############################################################
# benchmark decorators
############################################################

def with_attributes(*use_attributes):
    "Decorator for benchmarks that use attributes"
    vmap = {False : 0, True : 1}
    values = [ vmap[bool(v)] for v in use_attributes ]
    def set_value(function):
        try:
            function.ATTRIBUTES.update(values)
        except AttributeError:
            function.ATTRIBUTES = set(values)
        return function
    return set_value

def with_text(no_text=False, text=False, utext=False):
    "Decorator for benchmarks that use text"
    values = []
    if no_text:
        values.append(0)
    if text:
        values.append(1)
    if utext:
        values.append(2)
    def set_value(function):
        try:
            function.TEXT.add(values)
        except AttributeError:
            function.TEXT = set(values)
        return function
    return set_value

def onlylib(*libs):
    "Decorator to restrict benchmarks to specific libraries"
    def set_libs(function):
        if libs:
            function.LIBS = libs
        return function
    return set_libs

def serialized(function):
    "Decorator for benchmarks that require serialized XML data"
    function.STRING = True
    return function

def children(function):
    "Decorator for benchmarks that require a list of root children"
    function.CHILDREN = True
    return function

def nochange(function):
    "Decorator for benchmarks that do not change the XML tree"
    function.NO_CHANGE = True
    return function

############################################################
# benchmark baseclass
############################################################

class SkippedTest(Exception):
    pass

class TreeBenchMark(object):
    atoz = string.ascii_lowercase
    repeat100  = range(100)
    repeat500  = range(500)
    repeat1000 = range(1000)

    _LIB_NAME_MAP = {
        'etree'        : 'lxe',
        'ElementTree'  : 'ET',
        'cElementTree' : 'cET'
        }

    SEARCH_TAG = "{cdefg}a00001"

    def __init__(self, etree, etree_parser=None):
        self.etree = etree
        libname = etree.__name__.split('.')[-1]
        self.lib_name = self._LIB_NAME_MAP.get(libname, libname)

        if libname == 'etree':
            deepcopy = copy.deepcopy
            def set_property(root, fname):
                xml = self._serialize_tree(root)
                if etree_parser is not None:
                    setattr(self, fname, lambda : etree.XML(xml, etree_parser))
                else:
                    setattr(self, fname, lambda : deepcopy(root))
                setattr(self, fname + '_xml', lambda : xml)
                setattr(self, fname + '_children', lambda : root[:])
        else:
            def set_property(root, fname):
                setattr(self, fname, self.et_make_clone_factory(root))
                xml = self._serialize_tree(root)
                setattr(self, fname + '_xml', lambda : xml)
                setattr(self, fname + '_children', lambda : root[:])

        attribute_list = list(enumerate( [{}, _ATTRIBUTES] ))
        text_list = list(enumerate( [None, _TEXT, _UTEXT] ))
        build_name = self._tree_builder_name

        self.setup_times = []
        for tree in self._all_trees():
            times = []
            self.setup_times.append(times)
            setup = getattr(self, '_setup_tree%d' % tree)
            for an, attributes in attribute_list:
                for tn, text in text_list:
                    root, t = setup(text, attributes)
                    times.append(t)
                    set_property(root, build_name(tree, tn, an))

    def _tree_builder_name(self, tree, tn, an):
        return '_root%d_T%d_A%d' % (tree, tn, an)

    def tree_builder(self, tree, tn, an, serial, children):
        name = self._tree_builder_name(tree, tn, an)
        if serial:
            name += '_xml'
        elif children:
            name += '_children'
        return getattr(self, name)

    def _serialize_tree(self, root):
        return self.etree.tostring(root, encoding='UTF-8')

    def et_make_clone_factory(self, elem):
        def generate_elem(append, elem, level):
            var = "e" + str(level)
            arg = repr(elem.tag)
            if elem.attrib:
                arg += ", **%r" % elem.attrib
            if level == 1:
                append(" e1 = Element(%s)" % arg)
            else:
                append(" %s = SubElement(e%d, %s)" % (var, level-1, arg))
            if elem.text:
                append(" %s.text = %r" % (var, elem.text))
            if elem.tail:
                append(" %s.tail = %r" % (var, elem.tail))
            for e in elem:
                generate_elem(append, e, level+1)
        # generate code for a function that creates a tree
        output = ["def element_factory():"]
        generate_elem(output.append, elem, 1)
        output.append(" return e1")
        # setup global function namespace
        namespace = {
            "Element"    : self.etree.Element,
            "SubElement" : self.etree.SubElement
            }

        # create function object
        exec_("\n".join(output), namespace)
        return namespace["element_factory"]

    def _all_trees(self):
        all_trees = []
        for name in dir(self):
            if name.startswith('_setup_tree'):
                all_trees.append(int(name[11:]))
        return all_trees

    def _setup_tree1(self, text, attributes):
        "tree with 26 2nd level and 520 * TREE_FACTOR 3rd level children"
        atoz = self.atoz
        SubElement = self.etree.SubElement
        current_time = time.time
        t = current_time()
        root = self.etree.Element('{abc}rootnode')
        for ch1 in atoz:
            el = SubElement(root, "{abc}"+ch1*5, attributes)
            el.text = text
            for ch2 in atoz:
                tag = "{cdefg}%s00001" % ch2
                for i in range(20 * TREE_FACTOR):
                    SubElement(el, tag).tail = text
        t = current_time() - t
        return (root, t)

    def _setup_tree2(self, text, attributes):
        "tree with 520 * TREE_FACTOR 2nd level and 26 3rd level children"
        atoz = self.atoz
        SubElement = self.etree.SubElement
        current_time = time.time
        t = current_time()
        root = self.etree.Element('{abc}rootnode')
        for ch1 in atoz:
            for i in range(20 * TREE_FACTOR):
                el = SubElement(root, "{abc}"+ch1*5, attributes)
                el.text = text
                for ch2 in atoz:
                    SubElement(el, "{cdefg}%s00001" % ch2).tail = text
        t = current_time() - t
        return (root, t)

    def _setup_tree3(self, text, attributes):
        "tree of depth 8 + TREE_FACTOR with 3 children per node"
        SubElement = self.etree.SubElement
        current_time = time.time
        t = current_time()
        root = self.etree.Element('{abc}rootnode')
        children = [root]
        for i in range(6 + TREE_FACTOR):
            children = [ SubElement(c, "{cdefg}a%05d" % (i%8), attributes)
                         for i,c in enumerate(chain(children, children, children)) ]
        for child in children:
            child.text = text
            child.tail = text
        t = current_time() - t
        return (root, t)

    def _setup_tree4(self, text, attributes):
        "small tree with 26 2nd level and 2 3rd level children"
        SubElement = self.etree.SubElement
        current_time = time.time
        t = current_time()
        root = self.etree.Element('{abc}rootnode')
        for ch1 in self.atoz:
            el = SubElement(root, "{abc}"+ch1*5, attributes)
            el.text = text
            SubElement(el, "{cdefg}a00001", attributes).tail = text
            SubElement(el, "{cdefg}z00000", attributes).tail = text
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
            if hasattr(method, 'LIBS') and self.lib_name not in method.LIBS:
                method_call = None
            else:
                method_call = method
            if method.__doc__:
                tree_sets = method.__doc__.split()
            else:
                tree_sets = ()
            if tree_sets:
                tree_tuples = [list(map(int, tree_set.split(',')))
                               for tree_set in tree_sets]
            else:
                try:
                    arg_count = method.func_code.co_argcount - 1
                except AttributeError:
                    try:
                        arg_count = method.__code__.co_argcount - 1
                    except AttributeError:
                        arg_count = 1
                tree_tuples = self._permutations(all_trees, arg_count)

            serialized = getattr(method, 'STRING',   False)
            children   = getattr(method, 'CHILDREN', False)
            no_change  = getattr(method, 'NO_CHANGE', False)

            for tree_tuple in tree_tuples:
                for tn in sorted(getattr(method, 'TEXT', (0,))):
                    for an in sorted(getattr(method, 'ATTRIBUTES', (0,))):
                        benchmarks.append((name, method_call, tree_tuple,
                                           tn, an, serialized, children,
                                           no_change))

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
# Prepare and run benchmark suites
############################################################

def buildSuites(benchmark_class, etrees, selected):
    benchmark_suites = list(map(benchmark_class, etrees))

    # sorted by name and tree tuple
    benchmarks = [ sorted(b.benchmarks()) for b in benchmark_suites ]

    selected = [ re.compile(r).search for r in selected ]

    if selected:
        benchmarks = [ [ b for b in bs
                         if [ match for match in selected
                              if match(b[0]) ] ]
                       for bs in benchmarks ]

    return (benchmark_suites, benchmarks)

def build_treeset_name(trees, tn, an, serialized, children):
    text = {0:'-', 1:'S', 2:'U'}[tn]
    attr = {0:'-', 1:'A'}[an]
    ser  = {True:'X', False:'T'}[serialized]
    chd  = {True:'C', False:'R'}[children]
    return "%s%s%s%s T%s" % (text, attr, ser, chd, ',T'.join(map(str, trees))[:6])

def printSetupTimes(benchmark_suites):
    print("Setup times for trees in seconds:")
    for b in benchmark_suites:
        sys.stdout.write("%-3s:     " % b.lib_name)
        for an in (0,1):
            for tn in (0,1,2):
                sys.stdout.write('  %s   ' %
                    build_treeset_name((), tn, an, False, False)[:2])
        print('')
        for i, tree_times in enumerate(b.setup_times):
            print("     T%d: %s" % (i+1, ' '.join("%6.4f" % t for t in tree_times)))
    print('')

def runBench(suite, method_name, method_call, tree_set, tn, an,
             serial, children, no_change):
    if method_call is None:
        raise SkippedTest

    current_time = time.time
    call_repeat = range(10)

    tree_builders = [ suite.tree_builder(tree, tn, an, serial, children)
                      for tree in tree_set ]

    rebuild_trees = not no_change and not serial

    args = tuple([ build() for build in tree_builders ])
    method_call(*args) # run once to skip setup overhead

    times = []
    for i in range(3):
        gc.collect()
        gc.disable()
        t = -1
        for i in call_repeat:
            if rebuild_trees:
                args = [ build() for build in tree_builders ]
            t_one_call = current_time()
            method_call(*args)
            t_one_call = current_time() - t_one_call
            if t < 0:
                t = t_one_call
            else:
                t = min(t, t_one_call)
        times.append(1000.0 * t)
        gc.enable()
        if rebuild_trees:
            args = ()
    args = ()
    gc.collect()
    return times


def runBenchmarks(benchmark_suites, benchmarks):
    for bench_calls in izip(*benchmarks):
        for lib, (bench, benchmark_setup) in enumerate(izip(benchmark_suites, bench_calls)):
            bench_name = benchmark_setup[0]
            tree_set_name = build_treeset_name(*benchmark_setup[-6:-1])
            sys.stdout.write("%-3s: %-28s (%-10s) " % (
                bench.lib_name, bench_name[6:34], tree_set_name))
            sys.stdout.flush()

            try:
                result = runBench(bench, *benchmark_setup)
            except SkippedTest:
                print("skipped")
            except KeyboardInterrupt:
                print("interrupted by user")
                sys.exit(1)
            except Exception:
                exc_type, exc_value = sys.exc_info()[:2]
                print("failed: %s: %s" % (exc_type.__name__, exc_value))
                exc_type = exc_value = None
            else:
                print("%9.4f msec/pass, best of (%s)" % (
                      min(result), ' '.join("%9.4f" % t for t in result)))

        if len(benchmark_suites) > 1:
            print('')  # empty line between different benchmarks

############################################################
# Main program
############################################################

def main(benchmark_class):
    import_lxml = True
    callgrind_zero = False
    if len(sys.argv) > 1:
        try:
            sys.argv.remove('-i')
            # run benchmark 'inplace'
            sys.path.insert(0, 'src')
        except ValueError:
            pass

        try:
            sys.argv.remove('-nolxml')
            # run without lxml
            import_lxml = False
        except ValueError:
            pass

        try:
            sys.argv.remove('-z')
            # reset callgrind after tree setup
            callgrind_zero = True
        except ValueError:
            pass

        initArgs(sys.argv)

    _etrees = []
    if import_lxml:
        from lxml import etree
        _etrees.append(etree)

        try:
            sys.argv.remove('-fel')
        except ValueError:
            pass
        else:
            # use fast element creation in lxml.etree
            etree.set_element_class_lookup(
                etree.ElementDefaultClassLookup())

    if len(sys.argv) > 1:
        if '-a' in sys.argv or '-c' in sys.argv:
            # 'all' or 'C-implementations' ?
            try:
                sys.argv.remove('-c')
            except ValueError:
                pass
            try:
                import cElementTree as cET
                _etrees.append(cET)
            except ImportError:
                try:
                    import xml.etree.cElementTree as cET
                    _etrees.append(cET)
                except ImportError:
                    pass

        try:
            # 'all' ?
            sys.argv.remove('-a')
        except ValueError:
            pass
        else:
            try:
                from elementtree import ElementTree as ET
                _etrees.append(ET)
            except ImportError:
                try:
                    from xml.etree import ElementTree as ET
                    _etrees.append(ET)
                except ImportError:
                    pass

    if not _etrees:
        print("No library to test. Exiting.")
        sys.exit(1)

    print("Preparing test suites and trees ...")
    selected = set( sys.argv[1:] )
    benchmark_suites, benchmarks = \
                      buildSuites(benchmark_class, _etrees, selected)

    print("Running benchmark on", ', '.join(b.lib_name
                                            for b in benchmark_suites))
    print('')

    printSetupTimes(benchmark_suites)

    if callgrind_zero:
        cmd = open("callgrind.cmd", 'w')
        cmd.write('+Instrumentation\n')
        cmd.write('Zero\n')
        cmd.close()

    runBenchmarks(benchmark_suites, benchmarks)
