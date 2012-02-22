#!/usr/bin/env python

import sys
import os.path

def error(message, *args):
    if args:
        message = message % args
    sys.stderr.write('ERROR: %s\n' % message)

try:
    import lxml.etree as et
except ImportError:
    error(sys.exc_info()[1])
    sys.exit(5)

try:
    basestring
except NameError:
    basestring = (str, bytes)

try:
    unicode
except NameError:
    unicode = str

SHORT_DESCRIPTION = "An XPath file finder for XML files."

__doc__ = SHORT_DESCRIPTION + '''

Evaluates an XPath expression against a series of files and prints the
matching subtrees to stdout.

Examples::

  $ cat test.xml
  <root>
    <a num="1234" notnum="1234abc"/>
    <b text="abc"/>
    <c text="aBc"/>
    <d xmlns="http://www.example.org/ns/example" num="2"/>
    <d xmlns="http://www.example.org/ns/example" num="4"/>
  </root>

  # find all leaf elements:
  $ SCRIPT '//*[not(*)]' test.xml
  <a num="1234" notnum="1234abc"/>
  <b text="abc"/>
  <c text="aBc"/>

  # find all elements with attribute values containing "abc" ignoring case:
  $ SCRIPT '//*[@*[contains(py:lower(.), "abc")]]' test.xml
  <a num="1234" notnum="1234abc"/>
  <b text="abc"/>
  <c text="aBc"/>

  # find all numeric attribute values:
  $ SCRIPT '//@*[re:match(., "^[0-9]+$")]' test.xml
  1234

  * find all elements with numeric attribute values:
  $ SCRIPT '//*[@*[re:match(., "^[0-9]+$")]]' test.xml
  <a num="1234" notnum="1234abc"/>

  * find all elements with numeric attribute values in more than one file:
  $ SCRIPT '//*[@*[re:match(., "^[0-9]+$")]]' test.xml test.xml test.xml
  >> test.xml
  <a num="1234" notnum="1234abc"/>
  >> test.xml
  <a num="1234" notnum="1234abc"/>
  >> test.xml
  <a num="1234" notnum="1234abc"/>

  * find XML files that have non-empty root nodes:
  $ SCRIPT -q '*' test.xml test.xml test.xml
  >> test.xml
  >> test.xml
  >> test.xml

  * find out if an XML file has at most depth three:
  $ SCRIPT 'not(/*/*/*)' test.xml
  True

  * find all elements that belong to a specific namespace and have @num=2
  $ SCRIPT --ns e=http://www.example.org/ns/example '//e:*[@num="2"]' test.xml
  <d xmlns="http://www.example.org/ns/example" num="2"/>

By default, all Python builtins and string methods are available as
XPath functions through the ``py`` prefix.  There is also a string
comparison function ``py:within(x, a, b)`` that tests the string x for
being lexicographically within the interval ``a <= x <= b``.
'''.replace('SCRIPT', os.path.basename(sys.argv[0]))

REGEXP_NS = "http://exslt.org/regular-expressions"
PYTHON_BUILTINS_NS = "PYTHON-BUILTINS"

def make_parser(remove_blank_text=True, **kwargs):
    return et.XMLParser(remove_blank_text=remove_blank_text, **kwargs)

def print_result(result, pretty_print, encoding=None, _is_py3=sys.version_info[0] >= 3):
    stdout = sys.stdout
    if not stdout.isatty() and not encoding:
        encoding = 'utf8'
    if et.iselement(result):
        result = et.tostring(result, xml_declaration=False, with_tail=False,
                             pretty_print=pretty_print, encoding=encoding)
        if not pretty_print:
            # pretty printing appends newline, otherwise we do it
            if isinstance(result, unicode):
                result += '\n'
            else:
                result += '\n'.encode('ascii')
    elif isinstance(result, basestring):
        result += '\n'
    else:
        result = '%r\n' % result # '%r' for better number formatting

    if encoding and encoding != 'unicode' and isinstance(result, unicode):
        result = result.encode(encoding)

    if _is_py3 and not isinstance(result, unicode):
        stdout.buffer.write(result)
    else:
        stdout.write(result)

def print_results(results, pretty_print):
    if isinstance(results, list):
        for result in results:
            print_result(result, pretty_print)
    else:
        print_result(results, pretty_print)

def iter_input(input, filename, parser, line_by_line):
    if isinstance(input, basestring):
        with open(input, 'rb') as f:
            for tree in iter_input(f, filename, parser, line_by_line):
                yield tree
    else:
        try:
            if line_by_line:
                for line in input:
                    if line:
                        yield et.ElementTree(et.fromstring(line, parser))
            else:
                yield et.parse(input, parser)
        except IOError:
            e = sys.exc_info()[1]
            error("parsing %r failed: %s: %s",
                  filename, e.__class__.__name__, e)

def find_in_file(f, xpath, print_name=True, xinclude=False, pretty_print=True, line_by_line=False,
                 encoding=None, verbose=True):
    try:
        filename = f.name
    except AttributeError:
        filename = f

    xml_parser = et.XMLParser(encoding=encoding)

    try:
        if not callable(xpath):
            xpath = et.XPath(xpath)

        found = False
        for tree in iter_input(f, filename, xml_parser, line_by_line):
            try:
                if xinclude:
                    tree.xinclude()
            except IOError:
                e = sys.exc_info()[1]
                error("XInclude for %r failed: %s: %s",
                      filename, e.__class__.__name__, e)

            results = xpath(tree)
            if results is not None and results != []:
                found = True
                if verbose:
                    print_results(results, pretty_print)

        if not found:
            return False
        if not verbose and print_name:
            print(filename)
        return True
    except Exception:
        e = sys.exc_info()[1]
        error("%r: %s: %s",
              filename, e.__class__.__name__, e)
        return False

def register_builtins():
    ns = et.FunctionNamespace(PYTHON_BUILTINS_NS)
    tostring = et.tostring

    def make_string(s):
        if isinstance(s, list):
            if not s:
                return ''
            s = s[0]
        if not isinstance(s, unicode):
            if et.iselement(s):
                s = tostring(s, method="text", encoding='unicode')
            else:
                s = unicode(s)
        return s

    def wrap_builtin(b):
        def wrapped_builtin(_, *args):
            return b(*args)
        return wrapped_builtin

    for (name, builtin) in vars(__builtins__).items():
        if callable(builtin):
            if not name.startswith('_') and name == name.lower():
                ns[name] = wrap_builtin(builtin)

    def wrap_str_method(b):
        def wrapped_method(_, *args):
            args = tuple(map(make_string, args))
            return b(*args)
        return wrapped_method

    for (name, method) in vars(unicode).items():
        if callable(method):
            if not name.startswith('_'):
                ns[name] = wrap_str_method(method)

    def within(_, s, a, b):
        return make_string(a) <= make_string(s) <= make_string(b)
    ns["within"] = within


def parse_options():
    from optparse import OptionParser

    usage = "usage: %prog [options] XPATH [FILE ...]"

    parser = OptionParser(
        usage       = usage,
        version     = "%prog using lxml.etree " + et.__version__,
        description = SHORT_DESCRIPTION)
    parser.add_option("-H", "--long-help",
                      action="store_true", dest="long_help", default=False,
                      help="a longer help text including usage examples")
    parser.add_option("-i", "--xinclude",
                      action="store_true", dest="xinclude", default=False,
                      help="run XInclude on the file before XPath")
    parser.add_option("--no-python", 
                      action="store_false", dest="python", default=True,
                      help="disable Python builtins and functions (prefix 'py')")
    parser.add_option("--no-regexp", 
                      action="store_false", dest="regexp", default=True,
                      help="disable regular expressions (prefix 're')")
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose", default=True,
                      help="don't print status messages to stdout")
    parser.add_option("-t", "--root-tag",
                      dest="root_tag", metavar="TAG",
                      help="surround output with <TAG>...</TAG> to produce a well-formed XML document")
    parser.add_option("-p", "--plain",
                      action="store_false", dest="pretty_print", default=True,
                      help="do not pretty-print the output")
    parser.add_option("-l", "--lines",
                      action="store_true", dest="line_by_line", default=False,
                      help="parse each line of input separately (e.g. grep output)")
    parser.add_option("-e", "--encoding",
                      dest="encoding",
                      help="use a specific encoding for parsing (may be required with --lines)")
    parser.add_option("-N", "--ns", metavar="PREFIX=NS",
                      action="append", dest="namespaces", default=[],
                      help="add a namespace declaration")

    options, args = parser.parse_args()

    if options.long_help:
        parser.print_help()
        print(__doc__[__doc__.find('\n\n')+1:])
        sys.exit(0)

    if len(args) < 1:
        parser.error("first argument must be an XPath expression")

    return options, args


def main(options, args):
    namespaces = {}
    if options.regexp:
        namespaces["re"] = REGEXP_NS
    if options.python:
        register_builtins()
        namespaces["py"] = PYTHON_BUILTINS_NS

    for ns in options.namespaces:
        prefix, NS = ns.split("=", 1)
        namespaces[prefix.strip()] = NS.strip()

    xpath = et.XPath(args[0], namespaces=namespaces)
    files = args[1:] or [sys.stdin]

    if options.root_tag and options.verbose:
        print('<%s>' % options.root_tag)

    found = False
    print_name = len(files) > 1 and not options.root_tag
    for input in files:
        found |= find_in_file(
            input, xpath,
            print_name=print_name,
            xinclude=options.xinclude,
            pretty_print=options.pretty_print,
            line_by_line=options.line_by_line,
            encoding=options.encoding,
            verbose=options.verbose,
        )

    if options.root_tag and options.verbose:
        print('</%s>' % options.root_tag)

    return found

if __name__ == "__main__":
    try:
        options, args = parse_options()
        found = main(options, args)
        if found:
            sys.exit(0)
        else:
            sys.exit(1)
    except et.XPathSyntaxError:
        error(sys.exc_info()[1])
        sys.exit(4)
    except KeyboardInterrupt:
        pass
