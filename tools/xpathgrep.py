#!/usr/bin/env python

import lxml.etree as et
import sys, os.path, optparse, itertools

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

'''.replace('SCRIPT', os.path.basename(sys.argv[0]))

REGEXP_NS = "http://exslt.org/regular-expressions"
PYTHON_BUILTINS_NS = "PYTHON-BUILTINS"

parser = et.XMLParser(remove_blank_text=True)

def print_results(results):
    if isinstance(results, basestring) or isinstance(results, bool):
        print results
        return

    for result in results:
        if isinstance(result, basestring) or isinstance(result, bool):
            print result
        else:
            print et.tostring(
                result,
                xml_declaration=False,
                pretty_print=True)

def find_in_file(f, xpath, print_name=True, xinclude=False):
    if hasattr(f, 'name'):
        filename = f.name
    else:
        filename = f

    try:
        try:
            tree = et.parse(f, parser)
        except IOError, e:
            print >> sys.stderr, "ERR: parsing %r failed: %s: %s" % (
                filename, e.__class__.__name__, e)
            return False

        try:
            if xinclude:
                tree.xinclude()
        except IOError, e:
            print >> sys.stderr, "ERR: XInclude for %r failed: %s: %s" % (
                filename, e.__class__.__name__, e)
            return False

        if not callable(xpath):
            xpath = et.XPath(xpath)

        results = xpath(tree)
        if results == []:
            return False
        if print_name:
            print ">> %s" % f
        if options.verbose:
            print_results(results)
        return True
    except Exception, e:
        print >> sys.stderr, "ERR: %r: %s: %s" % (
            filename, e.__class__.__name__, e)
        return False

def register_builtins():
    ns = et.FunctionNamespace(PYTHON_BUILTINS_NS)
    for (name, builtin) in vars(__builtins__).iteritems():
        if callable(builtin):
            if not name.startswith('_') and name == name.lower():
                ns[name] = builtin

    str_xpath = et.XPath("string()")
    def lower(_, s):
        if isinstance(s, list):
            if not s:
                return ''
            s = s[0]
        if not isinstance(s, basestring):
            if isinstance(s, bool):
                s = str(s)
            else:
                s = str_xpath(s)
        return s.lower()
    def upper(_, s):
        if isinstance(s, list):
            if not s:
                return ''
            s = s[0]
        if not isinstance(s, basestring):
            if isinstance(s, bool):
                s = str(s)
            else:
                s = str_xpath(s)
        return s.upper()

    ns["lower"] = lower
    ns["upper"] = upper


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
                      help="disable Python builtins (prefix 'py')")
    parser.add_option("--no-regexp", 
                      action="store_false", dest="regexp", default=True,
                      help="disable regular expressions (prefix 're')")
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose", default=True,
                      help="don't print status messages to stdout")

    options, args = parser.parse_args()

    if options.long_help:
        parser.print_help()
        print __doc__[__doc__.find('\n\n')+1:]
        sys.exit(0)

    if len(args) < 1:
        parser.error("first argument must be an XPath expression")

    return options, args


if __name__ == "__main__":
    options, args = parse_options()

    namespaces = {}
    if options.regexp:
        namespaces["re"] = REGEXP_NS
    if options.python:
        register_builtins()
        namespaces["py"] = PYTHON_BUILTINS_NS

    xpath = et.XPath(args[0], namespaces)

    found = False
    if len(args) == 1:
        found = find_in_file(
            sys.stdin, xpath, print_name, options.xinclude)
    else:
        print_name = len(args) > 2
        for filename in itertools.islice(args, 1, None):
            found |= find_in_file(
                filename, xpath, print_name, options.xinclude)

    if found:
        sys.exit(0)
    else:
        sys.exit(1)
