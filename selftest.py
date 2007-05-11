# $Id: selftest.py 2193 2004-12-05 18:03:00Z fredrik $
# -*- coding: iso-8859-1 -*-
# elementtree selftest program

# this test script uses Python's "doctest" module to check that the
# *test script* works as expected.

# TODO: add more elementtree method tests
# TODO: add xml/html parsing tests
# TODO: etc

import re, sys, string, StringIO

from lxml import etree as ElementTree
from lxml import _elementpath as ElementPath
from lxml import ElementInclude

#from elementtree import ElementTree
#from elementtree import ElementPath
#from elementtree import ElementInclude
#from elementtree import HTMLTreeBuilder
#from elementtree import SimpleXMLWriter

def fix_compatibility(xml_data):
    xml_data = re.sub('\s*xmlns:[a-z0-9]+="http://www.w3.org/2001/XInclude"', '', xml_data)
    return xml_data

def serialize(elem, encoding=None):
    import StringIO
    file = StringIO.StringIO()
    tree = ElementTree.ElementTree(elem)
    if encoding:
        tree.write(file, encoding)
    else:
        tree.write(file)
    return fix_compatibility( file.getvalue() )

def summarize(elem):
    return elem.tag

def summarize_list(seq):
    return map(summarize, seq)

def normalize_crlf(tree):
    for elem in tree.getiterator():
        if elem.text: elem.text = string.replace(elem.text, "\r\n", "\n")
        if elem.tail: elem.tail = string.replace(elem.tail, "\r\n", "\n")

SAMPLE_XML = ElementTree.XML("""
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

def check_string_or_none(value):
    if value is None:
        return
    return check_string(value)

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
    check_string_or_none(element.text)
    check_string_or_none(element.tail)
    for elem in element:
        check_element(elem)

def check_element_tree(tree):
    check_element(tree.getroot())

# --------------------------------------------------------------------
# element tree tests

## def sanity():
##     """
##     >>> from elementtree.ElementTree import *
##     >>> from elementtree.ElementInclude import *
##     >>> from elementtree.ElementPath import *
##     >>> from elementtree.HTMLTreeBuilder import *
##     >>> from elementtree.SimpleXMLTreeBuilder import *
##     >>> from elementtree.SimpleXMLWriter import *
##     >>> from elementtree.TidyHTMLTreeBuilder import *
##     >>> from elementtree.TidyTools import *
##     >>> from elementtree.XMLTreeBuilder import *
##     """

def interface():
    """
    Test element tree interface.

    >>> element = ElementTree.Element("tag")
    >>> check_element(element)
    >>> tree = ElementTree.ElementTree(element)
    >>> check_element_tree(tree)
    """

## def simplefind():
##     """
##     Test find methods using the elementpath fallback.

##     >>> CurrentElementPath = ElementTree.ElementPath
##     >>> ElementTree.ElementPath = ElementTree._SimpleElementPath()
##     >>> elem = SAMPLE_XML
##     >>> elem.find("tag").tag
##     'tag'
##     >>> ElementTree.ElementTree(elem).find("tag").tag
##     'tag'
##     >>> elem.findtext("tag")
##     'text'
##     >>> elem.findtext("tog")
##     >>> elem.findtext("tog", "default")
##     'default'
##     >>> ElementTree.ElementTree(elem).findtext("tag")
##     'text'
##     >>> summarize_list(elem.findall("tag"))
##     ['tag', 'tag']
##     >>> summarize_list(elem.findall(".//tag"))
##     ['tag', 'tag', 'tag']

##     Path syntax doesn't work in this case.

##     >>> elem.find("section/tag")
##     >>> elem.findtext("section/tag")
##     >>> elem.findall("section/tag")
##     []

##     >>> ElementTree.ElementPath = CurrentElementPath
##     """

def find():
    """
    Test find methods (including xpath syntax).

    >>> elem = SAMPLE_XML
    >>> elem.find("tag").tag
    'tag'
    >>> ElementTree.ElementTree(elem).find("tag").tag
    'tag'
    >>> elem.find("section/tag").tag
    'tag'
    >>> ElementTree.ElementTree(elem).find("section/tag").tag
    'tag'
    >>> elem.findtext("tag")
    'text'
    >>> elem.findtext("tog")
    >>> elem.findtext("tog", "default")
    'default'
    >>> ElementTree.ElementTree(elem).findtext("tag")
    'text'
    >>> elem.findtext("section/tag")
    'subtext'
    >>> ElementTree.ElementTree(elem).findtext("section/tag")
    'subtext'
    >>> summarize_list(elem.findall("tag"))
    ['tag', 'tag']
    >>> summarize_list(elem.findall("*"))
    ['tag', 'tag', 'section']
    >>> summarize_list(elem.findall(".//tag"))
    ['tag', 'tag', 'tag']
    >>> summarize_list(elem.findall("section/tag"))
    ['tag']
    >>> summarize_list(elem.findall("section//tag"))
    ['tag']
    >>> summarize_list(elem.findall("section/*"))
    ['tag']
    >>> summarize_list(elem.findall("section//*"))
    ['tag']
    >>> summarize_list(elem.findall("section/.//*"))
    ['tag']
    >>> summarize_list(elem.findall("*/*"))
    ['tag']
    >>> summarize_list(elem.findall("*//*"))
    ['tag']
    >>> summarize_list(elem.findall("*/tag"))
    ['tag']
    >>> summarize_list(elem.findall("*/./tag"))
    ['tag']
    >>> summarize_list(elem.findall("./tag"))
    ['tag', 'tag']
    >>> summarize_list(elem.findall(".//tag"))
    ['tag', 'tag', 'tag']
    >>> summarize_list(elem.findall("././tag"))
    ['tag', 'tag']
    >>> summarize_list(ElementTree.ElementTree(elem).findall("/tag"))
    ['tag', 'tag']
    >>> summarize_list(ElementTree.ElementTree(elem).findall("./tag"))
    ['tag', 'tag']
    """

def bad_find():
    """
    Check bad or unsupported path expressions.

    >>> elem = SAMPLE_XML
    >>> elem.findall("/tag")
    Traceback (most recent call last):
    SyntaxError: cannot use absolute path on element
    >>> elem.findall("../tag")
    Traceback (most recent call last):
    SyntaxError: unsupported path syntax (..)
    >>> elem.findall("section//")
    Traceback (most recent call last):
    SyntaxError: path cannot end with //
    >>> elem.findall("tag[tag]")
    Traceback (most recent call last):
    SyntaxError: expected path separator ([)
    """

def parsefile():
    """
    Test parsing from file.

    >>> tree = ElementTree.parse("samples/simple.xml")
    >>> normalize_crlf(tree)
    >>> tree.write(sys.stdout)
    <root>
       <element key="value">text</element>
       <element>text</element>tail
       <empty-element/>
    </root>
    >>> tree = ElementTree.parse("samples/simple-ns.xml")
    >>> normalize_crlf(tree)
    >>> tree.write(sys.stdout)
    <root xmlns="namespace">
       <element key="value">text</element>
       <element>text</element>tail
       <empty-element/>
    </root>
    """

## def parsehtml():
##     """
##     Test HTML parsing.

##     >>> p = HTMLTreeBuilder.TreeBuilder()
##     >>> p.feed("<p><p>spam<b>egg</b></p>")
##     >>> serialize(p.close())
##     '<p>spam<b>egg</b></p>'
##     """

def parseliteral():
    r"""
    >>> element = ElementTree.XML("<html><body>text</body></html>")
    >>> ElementTree.ElementTree(element).write(sys.stdout)
    <html><body>text</body></html>
    >>> element = ElementTree.fromstring("<html><body>text</body></html>")
    >>> ElementTree.ElementTree(element).write(sys.stdout)
    <html><body>text</body></html>
    >>> print ElementTree.tostring(element)
    <html><body>text</body></html>

# looks different in lxml
#    >>> print ElementTree.tostring(element, "ascii")
#    <?xml version='1.0' encoding='ascii'?>
#    <html><body>text</body></html>

    >>> _, ids = ElementTree.XMLID("<html><body>text</body></html>")
    >>> len(ids)
    0
    >>> _, ids = ElementTree.XMLID("<html><body id='body'>text</body></html>")
    >>> len(ids)
    1
    >>> ids["body"].tag
    'body'
    """

## def simpleparsefile():
##     """
##     Test the xmllib-based parser.

##     >>> from elementtree import SimpleXMLTreeBuilder
##     >>> parser = SimpleXMLTreeBuilder.TreeBuilder()
##     >>> tree = ElementTree.parse("samples/simple.xml", parser)
##     >>> normalize_crlf(tree)
##     >>> tree.write(sys.stdout)
##     <root>
##        <element key="value">text</element>
##        <element>text</element>tail
##        <empty-element />
##     </root>
##     """

def iterparse():
    """
    Test iterparse interface.

    >>> iterparse = ElementTree.iterparse

    >>> context = iterparse("samples/simple.xml")
    >>> for action, elem in context:
    ...   print action, elem.tag
    end element
    end element
    end empty-element
    end root
    >>> context.root.tag
    'root'

    >>> context = iterparse("samples/simple-ns.xml")
    >>> for action, elem in context:
    ...   print action, elem.tag
    end {namespace}element
    end {namespace}element
    end {namespace}empty-element
    end {namespace}root

    >>> events = ()
    >>> context = iterparse("samples/simple.xml", events)
    >>> for action, elem in context:
    ...   print action, elem.tag

    >>> events = ()
    >>> context = iterparse("samples/simple.xml", events=events)
    >>> for action, elem in context:
    ...   print action, elem.tag

    >>> events = ("start", "end")
    >>> context = iterparse("samples/simple.xml", events)
    >>> for action, elem in context:
    ...   print action, elem.tag
    start root
    start element
    end element
    start element
    end element
    start empty-element
    end empty-element
    end root

    >>> events = ("start", "end", "start-ns", "end-ns")
    >>> context = iterparse("samples/simple-ns.xml", events)
    >>> for action, elem in context:
    ...   if action in ("start", "end"):
    ...     print action, elem.tag
    ...   else:
    ...     print action, elem
    start-ns ('', 'namespace')
    start {namespace}root
    start {namespace}element
    end {namespace}element
    start {namespace}element
    end {namespace}element
    start {namespace}empty-element
    end {namespace}empty-element
    end {namespace}root
    end-ns None

    """

## def fancyparsefile():
##     """
##     Test the "fancy" parser.

##     Sanity check.
##     >>> from elementtree import XMLTreeBuilder
##     >>> parser = XMLTreeBuilder.FancyTreeBuilder()
##     >>> tree = ElementTree.parse("samples/simple.xml", parser)
##     >>> normalize_crlf(tree)
##     >>> tree.write(sys.stdout)
##     <root>
##        <element key="value">text</element>
##        <element>text</element>tail
##        <empty-element />
##     </root>

##     Callback check.
##     >>> class MyFancyParser(XMLTreeBuilder.FancyTreeBuilder):
##     ...     def start(self, elem):
##     ...         print "START", elem.tag
##     ...     def end(self, elem):
##     ...         print "END", elem.tag
##     >>> parser = MyFancyParser()
##     >>> tree = ElementTree.parse("samples/simple.xml", parser)
##     START root
##     START element
##     END element
##     START element
##     END element
##     START empty-element
##     END empty-element
##     END root
##     """

def writefile():
    """
    >>> elem = ElementTree.Element("tag")
    >>> elem.text = "text"
    >>> serialize(elem)
    '<tag>text</tag>'
    >>> ElementTree.SubElement(elem, "subtag").text = "subtext"
    >>> serialize(elem)
    '<tag>text<subtag>subtext</subtag></tag>'
    """

def writestring():
    """
    >>> elem = ElementTree.XML("<html><body>text</body></html>")
    >>> ElementTree.tostring(elem)
    '<html><body>text</body></html>'
    >>> elem = ElementTree.fromstring("<html><body>text</body></html>")
    >>> ElementTree.tostring(elem)
    '<html><body>text</body></html>'
    """

## def encoding():
##     r"""
##     Test encoding issues.

##     >>> elem = ElementTree.Element("tag")
##     >>> elem.text = u"abc"
##     >>> serialize(elem)
##     '<tag>abc</tag>'
##     >>> serialize(elem, "utf-8")
##     '<tag>abc</tag>'
##     >>> serialize(elem, "us-ascii")
##     '<tag>abc</tag>'
##     >>> serialize(elem, "iso-8859-1")
##     "<?xml version='1.0' encoding='iso-8859-1'?>\n<tag>abc</tag>"

##     >>> elem.text = "<&\"\'>"
##     >>> serialize(elem)
##     '<tag>&lt;&amp;"\'&gt;</tag>'
##     >>> serialize(elem, "utf-8")
##     '<tag>&lt;&amp;"\'&gt;</tag>'
##     >>> serialize(elem, "us-ascii") # cdata characters
##     '<tag>&lt;&amp;"\'&gt;</tag>'
##     >>> serialize(elem, "iso-8859-1")
##     '<?xml version=\'1.0\' encoding=\'iso-8859-1\'?>\n<tag>&lt;&amp;"\'&gt;</tag>'

##     >>> elem.attrib["key"] = "<&\"\'>"
##     >>> elem.text = None
##     >>> serialize(elem)
##     '<tag key="&lt;&amp;&quot;&apos;&gt;" />'
##     >>> serialize(elem, "utf-8")
##     '<tag key="&lt;&amp;&quot;&apos;&gt;" />'
##     >>> serialize(elem, "us-ascii")
##     '<tag key="&lt;&amp;&quot;&apos;&gt;" />'
##     >>> serialize(elem, "iso-8859-1")
##     '<?xml version=\'1.0\' encoding=\'iso-8859-1\'?>\n<tag key="&lt;&amp;&quot;&apos;&gt;" />'

##     >>> elem.text = u'\xe5\xf6\xf6<>'
##     >>> elem.attrib.clear()
##     >>> serialize(elem)
##     '<tag>&#229;&#246;&#246;&lt;&gt;</tag>'
##     >>> serialize(elem, "utf-8")
##     '<tag>\xc3\xa5\xc3\xb6\xc3\xb6&lt;&gt;</tag>'
##     >>> serialize(elem, "us-ascii")
##     '<tag>&#229;&#246;&#246;&lt;&gt;</tag>'
##     >>> serialize(elem, "iso-8859-1")
##     "<?xml version='1.0' encoding='iso-8859-1'?>\n<tag>\xe5\xf6\xf6&lt;&gt;</tag>"

##     >>> elem.attrib["key"] = u'\xe5\xf6\xf6<>'
##     >>> elem.text = None
##     >>> serialize(elem)
##     '<tag key="&#229;&#246;&#246;&lt;&gt;" />'
##     >>> serialize(elem, "utf-8")
##     '<tag key="\xc3\xa5\xc3\xb6\xc3\xb6&lt;&gt;" />'
##     >>> serialize(elem, "us-ascii")
##     '<tag key="&#229;&#246;&#246;&lt;&gt;" />'
##     >>> serialize(elem, "iso-8859-1")
##     '<?xml version=\'1.0\' encoding=\'iso-8859-1\'?>\n<tag key="\xe5\xf6\xf6&lt;&gt;" />'

##     """

ENTITY_XML = """\
<!DOCTYPE points [
<!ENTITY % user-entities SYSTEM 'user-entities.xml'>
%user-entities;
]>
<document>&entity;</document>
"""

## def entity():
##     """
##     Test entity handling.

##     1) bad entities

##     >>> ElementTree.XML("<document>&entity;</document>")
##     Traceback (most recent call last):
##     ExpatError: undefined entity: line 1, column 10

##     >>> ElementTree.XML(ENTITY_XML)
##     Traceback (most recent call last):
##     ExpatError: undefined entity &entity;: line 5, column 10

##     (add more tests here)

##     """

def xmllang():
    """
    This appears to be a problem; in underlying libxml2?
    
    1) xml namespace

    >>> elem = ElementTree.XML("<tag xml:lang='en' />")
    >>> serialize(elem) # 1.1
    '<tag xml:lang="en"/>'

#   '<tag xml:lang="en" />' # ElementTree produces an extra blank
    """
    
def namespace():
    """
    Test namespace issues.



    2) other "well-known" namespaces

    >>> elem = ElementTree.XML("<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#' />")
    >>> serialize(elem) # 2.1
    '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"/>'

    >>> elem = ElementTree.XML("<html:html xmlns:html='http://www.w3.org/1999/xhtml' />")
    >>> serialize(elem) # 2.2
    '<html:html xmlns:html="http://www.w3.org/1999/xhtml"/>'

    >>> elem = ElementTree.XML("<soap:Envelope xmlns:soap='http://schemas.xmlsoap.org/soap/envelope' />")
    >>> serialize(elem) # 2.3
    '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope"/>'

    3) unknown namespaces

    """

## def qname():
##     """
##     Test QName handling.

##     1) decorated tags

##     >>> elem = ElementTree.Element("{uri}tag")
##     >>> serialize(elem) # 1.1
##     '<ns0:tag xmlns:ns0="uri" />'
##     >>> elem = ElementTree.Element(ElementTree.QName("{uri}tag"))
##     >>> serialize(elem) # 1.2
##     '<ns0:tag xmlns:ns0="uri" />'
##     >>> elem = ElementTree.Element(ElementTree.QName("uri", "tag"))
##     >>> serialize(elem) # 1.3
##     '<ns0:tag xmlns:ns0="uri" />'

##     2) decorated attributes

##     >>> elem.clear()
##     >>> elem.attrib["{uri}key"] = "value"
##     >>> serialize(elem) # 2.1
##     '<ns0:tag ns0:key="value" xmlns:ns0="uri" />'

##     >>> elem.clear()
##     >>> elem.attrib[ElementTree.QName("{uri}key")] = "value"
##     >>> serialize(elem) # 2.2
##     '<ns0:tag ns0:key="value" xmlns:ns0="uri" />'

##     3) decorated values are not converted by default, but the
##        QName wrapper can be used for values

##     >>> elem.clear()
##     >>> elem.attrib["{uri}key"] = "{uri}value"
##     >>> serialize(elem) # 3.1
##     '<ns0:tag ns0:key="{uri}value" xmlns:ns0="uri" />'

##     >>> elem.clear()
##     >>> elem.attrib["{uri}key"] = ElementTree.QName("{uri}value")
##     >>> serialize(elem) # 3.2
##     '<ns0:tag ns0:key="ns0:value" xmlns:ns0="uri" />'

##     >>> elem.clear()
##     >>> subelem = ElementTree.Element("tag")
##     >>> subelem.attrib["{uri1}key"] = ElementTree.QName("{uri2}value")
##     >>> elem.append(subelem)
##     >>> elem.append(subelem)
##     >>> serialize(elem) # 3.3
##     '<ns0:tag xmlns:ns0="uri"><tag ns1:key="ns2:value" xmlns:ns1="uri1" xmlns:ns2="uri2" /><tag ns1:key="ns2:value" xmlns:ns1="uri1" xmlns:ns2="uri2" /></ns0:tag>'

##     """

def xpath_tokenizer(p):
    """
    Test the XPath tokenizer.

    >>> # tests from the xml specification
    >>> xpath_tokenizer("*")
    ['*']
    >>> xpath_tokenizer("text()")
    ['text', '()']
    >>> xpath_tokenizer("@name")
    ['@', 'name']
    >>> xpath_tokenizer("@*")
    ['@', '*']
    >>> xpath_tokenizer("para[1]")
    ['para', '[', '1', ']']
    >>> xpath_tokenizer("para[last()]")
    ['para', '[', 'last', '()', ']']
    >>> xpath_tokenizer("*/para")
    ['*', '/', 'para']
    >>> xpath_tokenizer("/doc/chapter[5]/section[2]")
    ['/', 'doc', '/', 'chapter', '[', '5', ']', '/', 'section', '[', '2', ']']
    >>> xpath_tokenizer("chapter//para")
    ['chapter', '/', '/', 'para']
    >>> xpath_tokenizer("//para")
    ['/', '/', 'para']
    >>> xpath_tokenizer("//olist/item")
    ['/', '/', 'olist', '/', 'item']
    >>> xpath_tokenizer(".")
    ['.']
    >>> xpath_tokenizer(".//para")
    ['.', '/', '/', 'para']
    >>> xpath_tokenizer("..")
    ['..']
    >>> xpath_tokenizer("../@lang")
    ['..', '/', '@', 'lang']
    >>> xpath_tokenizer("chapter[title]")
    ['chapter', '[', 'title', ']']
    >>> xpath_tokenizer("employee[@secretary and @assistant]")
    ['employee', '[', '@', 'secretary', '', 'and', '', '@', 'assistant', ']']

    >>> # additional tests
    >>> xpath_tokenizer("{http://spam}egg")
    ['{http://spam}egg']
    >>> xpath_tokenizer("./spam.egg")
    ['.', '/', 'spam.egg']
    >>> xpath_tokenizer(".//{http://spam}egg")
    ['.', '/', '/', '{http://spam}egg']
    """
    out = []
    for op, tag in ElementPath.xpath_tokenizer(p):
        out.append(op or tag)
    return out

#
# xinclude tests (samples from appendix C of the xinclude specification)

XINCLUDE = {}

XINCLUDE["C1.xml"] = """\
<?xml version='1.0'?>
<document xmlns:xi="http://www.w3.org/2001/XInclude">
  <p>120 Mz is adequate for an average home user.</p>
  <xi:include href="disclaimer.xml"/>
</document>
"""

XINCLUDE["disclaimer.xml"] = """\
<?xml version='1.0'?>
<disclaimer>
  <p>The opinions represented herein represent those of the individual
  and should not be interpreted as official policy endorsed by this
  organization.</p>
</disclaimer>
"""

XINCLUDE["C2.xml"] = """\
<?xml version='1.0'?>
<document xmlns:xi="http://www.w3.org/2001/XInclude">
  <p>This document has been accessed
  <xi:include href="count.txt" parse="text"/> times.</p>
</document>
"""

XINCLUDE["count.txt"] = "324387"

XINCLUDE["C3.xml"] = """\
<?xml version='1.0'?>
<document xmlns:xi="http://www.w3.org/2001/XInclude">
  <p>The following is the source of the "data.xml" resource:</p>
  <example><xi:include href="data.xml" parse="text"/></example>
</document>
"""

XINCLUDE["data.xml"] = """\
<?xml version='1.0'?>
<data>
  <item><![CDATA[Brooks & Shields]]></item>
</data>
"""

XINCLUDE["C5.xml"] = """\
<?xml version='1.0'?>
<div xmlns:xi="http://www.w3.org/2001/XInclude">
  <xi:include href="example.txt" parse="text">
    <xi:fallback>
      <xi:include href="fallback-example.txt" parse="text">
        <xi:fallback><a href="mailto:bob@example.org">Report error</a></xi:fallback>
      </xi:include>
    </xi:fallback>
  </xi:include>
</div>
"""

XINCLUDE["default.xml"] = """\
<?xml version='1.0'?>
<document xmlns:xi="http://www.w3.org/2001/XInclude">
  <p>Example.</p>
  <xi:include href="samples/simple.xml"/>
</document>
"""

def xinclude_loader(href, parse="xml", encoding=None):
    try:
        data = XINCLUDE[href]
    except KeyError:
        raise IOError("resource not found")
    if parse == "xml":
        return ElementTree.XML(data)
    return data

def xinclude():
    r"""
    Basic inclusion example (XInclude C.1)

    >>> document = xinclude_loader("C1.xml")
    >>> ElementInclude.include(document, xinclude_loader)
    >>> print serialize(document) # C1
    <document>
      <p>120 Mz is adequate for an average home user.</p>
      <disclaimer>
      <p>The opinions represented herein represent those of the individual
      and should not be interpreted as official policy endorsed by this
      organization.</p>
    </disclaimer>
    </document>

    Textual inclusion example (XInclude C.2)

    >>> document = xinclude_loader("C2.xml")
    >>> ElementInclude.include(document, xinclude_loader)
    >>> print serialize(document) # C2
    <document>
      <p>This document has been accessed
      324387 times.</p>
    </document>

    Textual inclusion of XML example (XInclude C.3)

    >>> document = xinclude_loader("C3.xml")
    >>> ElementInclude.include(document, xinclude_loader)
    >>> print serialize(document) # C3
    <document>
      <p>The following is the source of the "data.xml" resource:</p>
      <example>&lt;?xml version='1.0'?&gt;
    &lt;data&gt;
      &lt;item&gt;&lt;![CDATA[Brooks &amp; Shields]]&gt;&lt;/item&gt;
    &lt;/data&gt;
    </example>
    </document>

##     Fallback example (XInclude C.5)
##     Note! Fallback support is not yet implemented

##     >>> document = xinclude_loader("C5.xml")
##     >>> ElementInclude.include(document, xinclude_loader)
##     Traceback (most recent call last):
##     IOError: resource not found
##     >>> # print serialize(document) # C5

    """

def xinclude_default():
    """
    >>> document = xinclude_loader("default.xml")
    >>> ElementInclude.include(document)
    >>> print serialize(document) # default
    <document>
      <p>Example.</p>
      <root>
       <element key="value">text</element>
       <element>text</element>tail
       <empty-element/>
    </root>
    </document>
    """

#
# xmlwriter

## def xmlwriter():
##     r"""
##     >>> file = StringIO.StringIO()
##     >>> w = SimpleXMLWriter.XMLWriter(file)
##     >>> html = w.start("html")
##     >>> x = w.start("head")
##     >>> w.element("title", "my document")
##     >>> w.data("\n")
##     >>> w.element("meta", name="hello", value="goodbye")
##     >>> w.data("\n")
##     >>> w.end()
##     >>> x = w.start("body")
##     >>> w.element("h1", "this is a heading")
##     >>> w.data("\n")
##     >>> w.element("p", u"this is a paragraph")
##     >>> w.data("\n")
##     >>> w.element("p", u"reserved characters: <&>")
##     >>> w.data("\n")
##     >>> w.element("p", u"detta är också ett stycke")
##     >>> w.data("\n")
##     >>> w.close(html)
##     >>> print file.getvalue()
##     <html><head><title>my document</title>
##     <meta name="hello" value="goodbye" />
##     </head><body><h1>this is a heading</h1>
##     <p>this is a paragraph</p>
##     <p>reserved characters: &lt;&amp;&gt;</p>
##     <p>detta &#228;r ocks&#229; ett stycke</p>
##     </body></html>
##     """

# --------------------------------------------------------------------
# reported bugs

## def bug_xmltoolkit21():
##     """
##     marshaller gives obscure errors for non-string values

##     >>> elem = ElementTree.Element(123)
##     >>> serialize(elem) # tag
##     Traceback (most recent call last):
##     TypeError: cannot serialize 123 (type int)
##     >>> elem = ElementTree.Element("elem")
##     >>> elem.text = 123
##     >>> serialize(elem) # text
##     Traceback (most recent call last):
##     TypeError: cannot serialize 123 (type int)
##     >>> elem = ElementTree.Element("elem")
##     >>> elem.tail = 123
##     >>> serialize(elem) # tail
##     Traceback (most recent call last):
##     TypeError: cannot serialize 123 (type int)
##     >>> elem = ElementTree.Element("elem")
##     >>> elem.set(123, "123")
##     >>> serialize(elem) # attribute key
##     Traceback (most recent call last):
##     TypeError: cannot serialize 123 (type int)
##     >>> elem = ElementTree.Element("elem")
##     >>> elem.set("123", 123)
##     >>> serialize(elem) # attribute value
##     Traceback (most recent call last):
##     TypeError: cannot serialize 123 (type int)

##     """

def bug_xmltoolkit25():
    """
    typo in ElementTree.findtext

    >>> tree = ElementTree.ElementTree(SAMPLE_XML)
    >>> tree.findtext("tag")
    'text'
    >>> tree.findtext("section/tag")
    'subtext'
    """

def bug_xmltoolkit28():
    """
    .//tag causes exceptions

    >>> tree = ElementTree.XML("<doc><table><tbody/></table></doc>")
    >>> summarize_list(tree.findall(".//thead"))
    []
    >>> summarize_list(tree.findall(".//tbody"))
    ['tbody']
    """

## def bug_xmltoolkitX1():
##     """
##     dump() doesn't flush the output buffer

##     >>> tree = ElementTree.XML("<doc><table><tbody/></table></doc>")
##     >>> ElementTree.dump(tree); sys.stdout.write("tail")
##     <doc><table><tbody /></table></doc>
##     tail
##     """

## def bug_xmltoolkit39():
##     """
##     non-ascii element and attribute names doesn't work

##     >>> tree = ElementTree.XML("<?xml version='1.0' encoding='iso-8859-1'?><täg />")
##     >>> ElementTree.tostring(tree, "utf-8")
##     '<t\\xc3\\xa4g />'

##     >>> tree = ElementTree.XML("<?xml version='1.0' encoding='iso-8859-1'?><tag ättr='v&#228;lue' />")
##     >>> tree.attrib
##     {u'\\xe4ttr': u'v\\xe4lue'}
##     >>> ElementTree.tostring(tree, "utf-8")
##     '<tag \\xc3\\xa4ttr="v\\xc3\\xa4lue" />'

##     >>> tree = ElementTree.XML("<?xml version='1.0' encoding='iso-8859-1'?><täg>text</täg>")
##     >>> ElementTree.tostring(tree, "utf-8")
##     '<t\\xc3\\xa4g>text</t\\xc3\\xa4g>'

##     >>> tree = ElementTree.Element(u"täg")
##     >>> ElementTree.tostring(tree, "utf-8")
##     '<t\\xc3\\xa4g />'

##     >>> tree = ElementTree.Element("tag")
##     >>> tree.set(u"ättr", u"välue")
##     >>> ElementTree.tostring(tree, "utf-8")
##     '<tag \\xc3\\xa4ttr="v\\xc3\\xa4lue" />'

##     """

## def bug_xmltoolkit45():
##     """
##     problems parsing mixed unicode/non-ascii html documents

##     latin-1 text
##     >>> p = HTMLTreeBuilder.TreeBuilder()
##     >>> p.feed("<p>välue</p>")
##     >>> serialize(p.close())
##     '<p>v&#228;lue</p>'

##     utf-8 text
##     >>> p = HTMLTreeBuilder.TreeBuilder(encoding="utf-8")
##     >>> p.feed("<p>v\xc3\xa4lue</p>")
##     >>> serialize(p.close())
##     '<p>v&#228;lue</p>'

##     utf-8 text using meta tag
##     >>> p = HTMLTreeBuilder.TreeBuilder()
##     >>> p.feed("<html><meta http-equiv='Content-Type' content='text/html; charset=utf-8'><p>v\xc3\xa4lue</p></html>")
##     >>> serialize(p.close().find("p"))
##     '<p>v&#228;lue</p>'

##     latin-1 character references
##     >>> p = HTMLTreeBuilder.TreeBuilder()
##     >>> p.feed("<p>v&#228;lue</p>")
##     >>> serialize(p.close())
##     '<p>v&#228;lue</p>'

##     latin-1 character entities
##     >>> p = HTMLTreeBuilder.TreeBuilder()
##     >>> p.feed("<p>v&auml;lue</p>")
##     >>> serialize(p.close())
##     '<p>v&#228;lue</p>'

##     mixed latin-1 text and unicode entities
##     >>> p = HTMLTreeBuilder.TreeBuilder()
##     >>> p.feed("<p>&#8221;välue&#8221;</p>")
##     >>> serialize(p.close())
##     '<p>&#8221;v&#228;lue&#8221;</p>'

##     mixed unicode and latin-1 entities
##     >>> p = HTMLTreeBuilder.TreeBuilder()
##     >>> p.feed("<p>&#8221;v&auml;lue&#8221;</p>")
##     >>> serialize(p.close())
##     '<p>&#8221;v&#228;lue&#8221;</p>'

##     """

# --------------------------------------------------------------------

if __name__ == "__main__":
    import doctest, selftest
    failed, tested = doctest.testmod(selftest)
    print tested - failed, "tests ok."
