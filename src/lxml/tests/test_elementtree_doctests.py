# -*- coding: iso-8859-1 -*-
# elementtree selftest program

# this test script uses Python's "doctest" module to check that the
# *test script* works as expected.

# TODO: add more elementtree method tests
# TODO: add xml/html parsing tests
# TODO: etc

import sys, string, StringIO

from lxml import elementtree

def serialize(elem, encoding=None):
    import StringIO
    file = StringIO.StringIO()
    tree = elementtree.ElementTree(elem)
    if encoding:
        tree.write(file, encoding)
    else:
        tree.write(file)
    return file.getvalue()

def summarize(elem):
    return elem.tag

def summarize_list(seq):
    return map(summarize, seq)

def normalize_crlf(tree):
    for elem in tree.getiterator():
        if elem.text: elem.text = string.replace(elem.text, "\r\n", "\n")
        if elem.tail: elem.tail = string.replace(elem.tail, "\r\n", "\n")

SAMPLE_XML = elementtree.XML("""
<body>
  <tag>text</tag>
  <tag />
  <section>
    <tag>subtext</tag>
  </section>
</body>
""")

#
# interface tests

def check_string(string):
    len(string)
    for char in string:
        if len(char) != 1:
            print "expected one-character string, got %r" % char
    new_string = string + ""
    new_string = string + " "
    string[:0]

def check_mapping(mapping):
    len(mapping)
    keys = mapping.keys()
    items = mapping.items()
    for key in keys:
        item = mapping[key]
    mapping["key"] = "value"
    if mapping["key"] != "value":
        print "expected value string, got %r" % mapping["key"]

def check_element(element):
    if not hasattr(element, "tag"):
        print "no tag member"
    if not hasattr(element, "attrib"):
        print "no attrib member"
    if not hasattr(element, "text"):
        print "no text member"
    if not hasattr(element, "tail"):
        print "no tail member"
    check_string(element.tag)
    check_mapping(element.attrib)
    if element.text != None:
        check_string(element.text)
    if element.tail != None:
        check_string(element.tail)

def check_element_tree(tree):
    check_element(tree.getroot())
    
#
# element tree tests

## def interface():
##     """
##     Test element tree interface.

##     >>> element = elementtree.Element("tag")
##     >>> check_element(element)
##     >>> tree = elementtree.ElementTree(element)
##     >>> check_element_tree(tree)
##     """

def foo():
    """
    >>> 1
    1
    """
    
import unittest
from zope.testing.doctestunit import DocTestSuite

def test_suite():
    return unittest.TestSuite((
        DocTestSuite('lxml.tests.test_elementtree_doctests'),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
