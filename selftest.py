# $Id: selftest.py 3276 2007-09-12 06:52:30Z fredrik $
# -*- coding: iso-8859-1 -*-
# elementtree selftest program

# this test script uses Python's "doctest" module to check that the
# *test script* works as expected.

# TODO: add more elementtree method tests
# TODO: add xml/html parsing tests
# TODO: etc

import re, sys, string

try:
    from StringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

from lxml import etree as ElementTree
from lxml import _elementpath as ElementPath
from lxml import ElementInclude
ET = ElementTree

#from elementtree import ElementTree
#from elementtree import ElementPath
#from elementtree import ElementInclude
#from elementtree import HTMLTreeBuilder
#from elementtree import SimpleXMLWriter

def fix_compatibility(xml_data):
    xml_data = re.sub('\s*xmlns:[a-z0-9]+="http://www.w3.org/2001/XInclude"', '', xml_data)
    xml_data = xml_data.replace(' />', '/>')
    if xml_data[-1:] == '\n':
        xml_data = xml_data[:-1]
    return xml_data

def serialize(elem, **options):
    file = BytesIO()
    tree = ElementTree.ElementTree(elem)
    tree.write(file, **options)
    try:
        encoding = options["encoding"]
    except KeyError:
        encoding = "utf-8"
    result = fix_compatibility(file.getvalue().decode(encoding))
    if sys.version_info[0] < 3:
        result = result.encode(encoding)
    return result

def summarize(elem):
    return elem.tag

def summarize_list(seq):
    return list(map(summarize, seq))

def normalize_crlf(tree):
    for elem in tree.getiterator():
        if elem.text: elem.text = elem.text.replace("\r\n", "\n")
        if elem.tail: elem.tail = elem.tail.replace("\r\n", "\n")

SAMPLE_XML = ElementTree.XML("""
<body>
  <tag class='a'>text</tag>
  <tag class='b' />
   <section>
    <tag class='b' id='inner'>subtext</tag>
   </section>
</body>
""")

#
# interface tests

def check_string(string):
    len(string)
    for char in string:
        if len(char) != 1:
            print("expected one-character string, got %r" % char)
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
        print("expected value string, got %r" % mapping["key"])

def check_element(element):
    if not hasattr(element, "tag"):
        print("no tag member")
    if not hasattr(element, "attrib"):
        print("no attrib member")
    if not hasattr(element, "text"):
        print("no text member")
    if not hasattr(element, "tail"):
        print("no tail member")
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

def sanity():
    """
    >>> from elementtree.ElementTree import *
    >>> from elementtree.ElementInclude import *
    >>> from elementtree.ElementPath import *
    >>> from elementtree.HTMLTreeBuilder import *
    >>> from elementtree.SimpleXMLWriter import *
    >>> from elementtree.TidyTools import *
    """

# doesn't work with lxml.etree
del sanity

def version():
    """
    >>> ElementTree.VERSION
    '1.3a2'
    """

# doesn't work with lxml.etree
del version

def interface():
    """
    Test element tree interface.

    >>> element = ElementTree.Element("tag")
    >>> check_element(element)
    >>> tree = ElementTree.ElementTree(element)
    >>> check_element_tree(tree)
    """

def simpleops():
    """
    >>> elem = ElementTree.XML("<body><tag/></body>")
    >>> serialize(elem)
    '<body><tag/></body>'
    >>> e = ElementTree.Element("tag2")
    >>> elem.append(e)
    >>> serialize(elem)
    '<body><tag/><tag2/></body>'
    >>> elem.remove(e)
    >>> serialize(elem)
    '<body><tag/></body>'
    >>> elem.insert(0, e)
    >>> serialize(elem)
    '<body><tag2/><tag/></body>'
    >>> elem.remove(e)
    >>> elem.extend([e])
    >>> serialize(elem)
    '<body><tag/><tag2/></body>'
    >>> elem.remove(e)
    """

def simplefind():
    """
    Test find methods using the elementpath fallback.

    >>> CurrentElementPath = ElementTree.ElementPath
    >>> ElementTree.ElementPath = ElementTree._SimpleElementPath()
    >>> elem = SAMPLE_XML
    >>> elem.find("tag").tag
    'tag'
    >>> ElementTree.ElementTree(elem).find("tag").tag
    'tag'
    >>> elem.findtext("tag")
    'text'
    >>> elem.findtext("tog")
    >>> elem.findtext("tog", "default")
    'default'
    >>> ElementTree.ElementTree(elem).findtext("tag")
    'text'
    >>> summarize_list(elem.findall("tag"))
    ['tag', 'tag']
    >>> summarize_list(elem.findall(".//tag"))
    ['tag', 'tag', 'tag']

    Path syntax doesn't work in this case.

    >>> elem.find("section/tag")
    >>> elem.findtext("section/tag")
    >>> elem.findall("section/tag")
    []

    >>> ElementTree.ElementPath = CurrentElementPath
    """

# doesn't work with lxml.etree
del simplefind

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
    >>> summarize_list(elem.findall(".//tag[@class]"))
    ['tag', 'tag', 'tag']
    >>> summarize_list(elem.findall(".//tag[@class='a']"))
    ['tag']
    >>> summarize_list(elem.findall(".//tag[@class='b']"))
    ['tag', 'tag']
    >>> summarize_list(elem.findall(".//tag[@id]"))
    ['tag']
    >>> summarize_list(elem.findall(".//section[tag]"))
    ['section']
    >>> summarize_list(elem.findall(".//section[element]"))
    []
    >>> summarize_list(elem.findall("../tag"))
    []
    >>> summarize_list(elem.findall("section/../tag"))
    ['tag', 'tag']
    >>> summarize_list(ElementTree.ElementTree(elem).findall("./tag"))
    ['tag', 'tag']

    FIXME: ET's Path module handles this case incorrectly; this gives
    a warning in 1.3, and the behaviour will be modified in 1.4.

    >>> summarize_list(ElementTree.ElementTree(elem).findall("/tag"))
    ['tag', 'tag']
    """

def bad_find():
    """
    Check bad or unsupported path expressions.

    >>> elem = SAMPLE_XML
    >>> elem.findall("/tag")
    Traceback (most recent call last):
    SyntaxError: cannot use absolute path on element

    # this is supported in ET 1.3:
    #>>> elem.findall("section//")
    #Traceback (most recent call last):
    #SyntaxError: invalid path
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
    <root xmlns="http://namespace/">
       <element key="value">text</element>
       <element>text</element>tail
       <empty-element/>
    </root>

##     <ns0:root xmlns:ns0="http://namespace/">
##        <ns0:element key="value">text</ns0:element>
##        <ns0:element>text</ns0:element>tail
##        <ns0:empty-element/>
##     </ns0:root>
    """

def parsehtml():
    """
    Test HTML parsing.

    >>> # p = HTMLTreeBuilder.TreeBuilder()
    >>> p = ElementTree.HTMLParser()
    >>> p.feed("<p><p>spam<b>egg</b></p>")
    >>> serialize(p.close())
    '<p>spam<b>egg</b></p>'
    """

# doesn't work with lxml.etree
del parsehtml

def parseliteral():
    r"""
    >>> element = ElementTree.XML("<html><body>text</body></html>")
    >>> ElementTree.ElementTree(element).write(sys.stdout)
    <html><body>text</body></html>
    >>> element = ElementTree.fromstring("<html><body>text</body></html>")
    >>> ElementTree.ElementTree(element).write(sys.stdout)
    <html><body>text</body></html>

##     >>> sequence = ["<html><body>", "text</bo", "dy></html>"]
##     >>> element = ElementTree.fromstringlist(sequence)
##     >>> ElementTree.ElementTree(element).write(sys.stdout)
##     <html><body>text</body></html>

    >>> print(ElementTree.tostring(element))
    <html><body>text</body></html>

# looks different in lxml
#    >>> print(ElementTree.tostring(element, "ascii"))
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

def simpleparsefile():
    """
    Test the xmllib-based parser.

    >>> from elementtree import SimpleXMLTreeBuilder
    >>> parser = SimpleXMLTreeBuilder.TreeBuilder()
    >>> tree = ElementTree.parse("samples/simple.xml", parser)
    >>> normalize_crlf(tree)
    >>> tree.write(sys.stdout)
    <root>
       <element key="value">text</element>
       <element>text</element>tail
       <empty-element />
    </root>
    """

# doesn't work with lxml.etree
del simpleparsefile

def iterparse():
    """
    Test iterparse interface.

    >>> iterparse = ElementTree.iterparse

    >>> context = iterparse("samples/simple.xml")
    >>> for action, elem in context:
    ...   print("%s %s" % (action, elem.tag))
    end element
    end element
    end empty-element
    end root
    >>> context.root.tag
    'root'

    >>> context = iterparse("samples/simple-ns.xml")
    >>> for action, elem in context:
    ...   print("%s %s" % (action, elem.tag))
    end {http://namespace/}element
    end {http://namespace/}element
    end {http://namespace/}empty-element
    end {http://namespace/}root

    >>> events = ()
    >>> context = iterparse("samples/simple.xml", events)
    >>> for action, elem in context:
    ...   print("%s %s" % (action, elem.tag))

    >>> events = ()
    >>> context = iterparse("samples/simple.xml", events=events)
    >>> for action, elem in context:
    ...   print("%s %s" % (action, elem.tag))

    >>> events = ("start", "end")
    >>> context = iterparse("samples/simple.xml", events)
    >>> for action, elem in context:
    ...   print("%s %s" % (action, elem.tag))
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
    ...     print("%s %s" % (action, elem.tag))
    ...   else:
    ...     print("%s %s" % (action, elem))
    start-ns ('', 'http://namespace/')
    start {http://namespace/}root
    start {http://namespace/}element
    end {http://namespace/}element
    start {http://namespace/}element
    end {http://namespace/}element
    start {http://namespace/}empty-element
    end {http://namespace/}empty-element
    end {http://namespace/}root
    end-ns None

    """

def fancyparsefile():
    """
    Test the "fancy" parser.

    Sanity check.
    >>> from elementtree import XMLTreeBuilder
    >>> parser = XMLTreeBuilder.FancyTreeBuilder()
    >>> tree = ElementTree.parse("samples/simple.xml", parser)
    >>> normalize_crlf(tree)
    >>> tree.write(sys.stdout)
    <root>
       <element key="value">text</element>
       <element>text</element>tail
       <empty-element />
    </root>

    Callback check.
    >>> class MyFancyParser(XMLTreeBuilder.FancyTreeBuilder):
    ...     def start(self, elem):
    ...         print("START %s" % elem.tag)
    ...     def end(self, elem):
    ...         print("END %s" % elem.tag)
    >>> parser = MyFancyParser()
    >>> tree = ElementTree.parse("samples/simple.xml", parser)
    START root
    START element
    END element
    START element
    END element
    START empty-element
    END empty-element
    END root
    """

# doesn't work with lxml.etree
del fancyparsefile

def writefile():
    """
    >>> elem = ElementTree.Element("tag")
    >>> elem.text = "text"
    >>> serialize(elem)
    '<tag>text</tag>'
    >>> ElementTree.SubElement(elem, "subtag").text = "subtext"
    >>> serialize(elem)
    '<tag>text<subtag>subtext</subtag></tag>'

##     Test tag suppression
##     >>> elem.tag = None
##     >>> serialize(elem)
##     'text<subtag>subtext</subtag>'
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

def encoding():
    r"""
    Test encoding issues.

    >>> elem = ElementTree.Element("tag")
    >>> elem.text = u'abc'
    >>> serialize(elem)
    '<tag>abc</tag>'
    >>> serialize(elem, encoding="utf-8")
    '<tag>abc</tag>'
    >>> serialize(elem, encoding="us-ascii")
    '<tag>abc</tag>'
    >>> serialize(elem, encoding="iso-8859-1").lower()
    "<?xml version='1.0' encoding='iso-8859-1'?>\n<tag>abc</tag>"

    >>> elem.text = "<&\"\'>"
    >>> serialize(elem)
    '<tag>&lt;&amp;"\'&gt;</tag>'
    >>> serialize(elem, encoding="utf-8")
    '<tag>&lt;&amp;"\'&gt;</tag>'
    >>> serialize(elem, encoding="us-ascii") # cdata characters
    '<tag>&lt;&amp;"\'&gt;</tag>'
    >>> serialize(elem, encoding="iso-8859-1").lower()
    '<?xml version=\'1.0\' encoding=\'iso-8859-1\'?>\n<tag>&lt;&amp;"\'&gt;</tag>'

    >>> elem.attrib["key"] = "<&\"\'>"
    >>> elem.text = None
    >>> serialize(elem)
    '<tag key="&lt;&amp;&quot;\'&gt;"/>'
    >>> serialize(elem, encoding="utf-8")
    '<tag key="&lt;&amp;&quot;\'&gt;"/>'
    >>> serialize(elem, encoding="us-ascii")
    '<tag key="&lt;&amp;&quot;\'&gt;"/>'
    >>> serialize(elem, encoding="iso-8859-1").lower()
    '<?xml version=\'1.0\' encoding=\'iso-8859-1\'?>\n<tag key="&lt;&amp;&quot;\'&gt;"/>'

    >>> elem.text = u'\xe5\xf6\xf6<>'
    >>> elem.attrib.clear()
    >>> serialize(elem)
    '<tag>&#229;&#246;&#246;&lt;&gt;</tag>'
    >>> serialize(elem, encoding="utf-8")
    '<tag>\xc3\xa5\xc3\xb6\xc3\xb6&lt;&gt;</tag>'
    >>> serialize(elem, encoding="us-ascii")
    '<tag>&#229;&#246;&#246;&lt;&gt;</tag>'
    >>> serialize(elem, encoding="iso-8859-1").lower()
    "<?xml version='1.0' encoding='iso-8859-1'?>\n<tag>\xe5\xf6\xf6&lt;&gt;</tag>"

    >>> elem.attrib["key"] = u'\xe5\xf6\xf6<>'
    >>> elem.text = None
    >>> serialize(elem)
    '<tag key="&#229;&#246;&#246;&lt;&gt;"/>'
    >>> serialize(elem, encoding="utf-8")
    '<tag key="\xc3\xa5\xc3\xb6\xc3\xb6&lt;&gt;"/>'
    >>> serialize(elem, encoding="us-ascii")
    '<tag key="&#229;&#246;&#246;&lt;&gt;"/>'
    >>> serialize(elem, encoding="iso-8859-1").lower()
    '<?xml version=\'1.0\' encoding=\'iso-8859-1\'?>\n<tag key="\xe5\xf6\xf6&lt;&gt;"/>'
    """

if sys.version_info[0] >= 3:
    encoding.__doc__ = encoding.__doc__.replace("u'", "'")

def methods():
    r"""
    Test serialization methods.

    >>> e = ET.XML("<html><link/><script>1 &lt; 2</script></html>")
    >>> e.tail = "\n"
    >>> serialize(e)
    '<html><link /><script>1 &lt; 2</script></html>\n'
    >>> serialize(e, method=None)
    '<html><link /><script>1 &lt; 2</script></html>\n'
    >>> serialize(e, method="xml")
    '<html><link /><script>1 &lt; 2</script></html>\n'
    >>> serialize(e, method="html")
    '<html><link><script>1 < 2</script></html>\n'
    >>> serialize(e, method="text")
    '1 < 2\n'

    """

# doesn't work with lxml.etree
del methods

def iterators():
    """
    Test iterators.

    >>> e = ET.XML("<html><body>this is a <i>paragraph</i>.</body>..</html>")
    >>> summarize_list(e.iter())
    ['html', 'body', 'i']
    >>> summarize_list(e.find("body").iter())
    ['body', 'i']
    >>> "".join(e.itertext())
    'this is a paragraph...'
    >>> "".join(e.find("body").itertext())
    'this is a paragraph.'
    """

ENTITY_XML = """\
<!DOCTYPE points [
<!ENTITY % user-entities SYSTEM 'user-entities.xml'>
%user-entities;
]>
<document>&entity;</document>
"""

def entity():
    """
    Test entity handling.

    1) bad entities

    >>> ElementTree.XML("<document>&entity;</document>")
    Traceback (most recent call last):
    ExpatError: undefined entity: line 1, column 10

    >>> ElementTree.XML(ENTITY_XML)
    Traceback (most recent call last):
    ExpatError: undefined entity &entity;: line 5, column 10

    (add more tests here)

    """

# doesn't work with lxml.etree
del entity

def error(xml):
    """
    Test error handling.

    >>> error("foo").position
    (1, 0)
    >>> error("<tag>&foo;</tag>").position
    (1, 5)
    >>> error("foobar<").position
    (1, 6)

    """
    try:
        ET.XML(xml)
    except ET.ParseError:
        return sys.exc_value

# doesn't work with lxml.etree -> different positions
del error

def namespace():
    """
    Test namespace issues.

    1) xml namespace

    >>> elem = ElementTree.XML("<tag xml:lang='en' />")
    >>> serialize(elem) # 1.1
    '<tag xml:lang="en"/>'

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

def qname():
    """
    Test QName handling.

    1) decorated tags

    >>> elem = ElementTree.Element("{uri}tag")
    >>> serialize(elem) # 1.1
    '<ns0:tag xmlns:ns0="uri"/>'
    >>> elem = ElementTree.Element(ElementTree.QName("{uri}tag"))
    >>> serialize(elem) # 1.2
    '<ns0:tag xmlns:ns0="uri"/>'
    >>> elem = ElementTree.Element(ElementTree.QName("uri", "tag"))
    >>> serialize(elem) # 1.3
    '<ns0:tag xmlns:ns0="uri"/>'

# ns/attribute order ...

##     2) decorated attributes

##     >>> elem.clear()
##     >>> elem.attrib["{uri}key"] = "value"
##     >>> serialize(elem) # 2.1
##     '<ns0:tag ns0:key="value" xmlns:ns0="uri"/>'

##     >>> elem.clear()
##     >>> elem.attrib[ElementTree.QName("{uri}key")] = "value"
##     >>> serialize(elem) # 2.2
##     '<ns0:tag ns0:key="value" xmlns:ns0="uri"/>'

##     3) decorated values are not converted by default, but the
##        QName wrapper can be used for values

##     >>> elem.clear()
##     >>> elem.attrib["{uri}key"] = "{uri}value"
##     >>> serialize(elem) # 3.1
##     '<ns0:tag ns0:key="{uri}value" xmlns:ns0="uri"/>'

##     >>> elem.clear()
##     >>> elem.attrib["{uri}key"] = ElementTree.QName("{uri}value")
##     >>> serialize(elem) # 3.2
##     '<ns0:tag ns0:key="ns0:value" xmlns:ns0="uri"/>'

##     >>> elem.clear()
##     >>> subelem = ElementTree.Element("tag")
##     >>> subelem.attrib["{uri1}key"] = ElementTree.QName("{uri2}value")
##     >>> elem.append(subelem)
##     >>> elem.append(subelem)
##     >>> serialize(elem) # 3.3
##     '<ns0:tag xmlns:ns0="uri"><tag ns1:key="ns2:value" xmlns:ns1="uri1" xmlns:ns2="uri2"/><tag ns1:key="ns2:value" xmlns:ns1="uri1" xmlns:ns2="uri2"/></ns0:tag>'

    """

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
    ['chapter', '//', 'para']
    >>> xpath_tokenizer("//para")
    ['//', 'para']
    >>> xpath_tokenizer("//olist/item")
    ['//', 'olist', '/', 'item']
    >>> xpath_tokenizer(".")
    ['.']
    >>> xpath_tokenizer(".//para")
    ['.', '//', 'para']
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
    ['.', '//', '{http://spam}egg']
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
    >>> print(serialize(document)) # C1
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
    >>> print(serialize(document)) # C2
    <document>
      <p>This document has been accessed
      324387 times.</p>
    </document>

    Textual inclusion of XML example (XInclude C.3)

    >>> document = xinclude_loader("C3.xml")
    >>> ElementInclude.include(document, xinclude_loader)
    >>> print(serialize(document)) # C3
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
##     >>> # print(serialize(document)) # C5

    """

def xinclude_default():
    """
    >>> document = xinclude_loader("default.xml")
    >>> ElementInclude.include(document)
    >>> print(serialize(document)) # default
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

def xmlwriter():
    r"""
    >>> file = BytesIO()
    >>> w = SimpleXMLWriter.XMLWriter(file)
    >>> html = w.start("html")
    >>> x = w.start("head")
    >>> w.element("title", "my document")
    >>> w.data("\n")
    >>> w.element("meta", name="hello", value="goodbye")
    >>> w.data("\n")
    >>> w.end()
    >>> x = w.start("body")
    >>> w.element("h1", "this is a heading")
    >>> w.data("\n")
    >>> w.element("p", u"this is a paragraph")
    >>> w.data("\n")
    >>> w.element("p", u"reserved characters: <&>")
    >>> w.data("\n")
    >>> w.element("p", u"detta är också ett stycke")
    >>> w.data("\n")
    >>> w.close(html)
    >>> print(file.getvalue())
    <html><head><title>my document</title>
    <meta name="hello" value="goodbye" />
    </head><body><h1>this is a heading</h1>
    <p>this is a paragraph</p>
    <p>reserved characters: &lt;&amp;&gt;</p>
    <p>detta &#228;r ocks&#229; ett stycke</p>
    </body></html>
    """

# doesn't work with lxml.etree
del xmlwriter

# --------------------------------------------------------------------
# reported bugs

def bug_xmltoolkit21():
    """
    marshaller gives obscure errors for non-string values

    >>> elem = ElementTree.Element(123)
    >>> serialize(elem) # tag
    Traceback (most recent call last):
    TypeError: cannot serialize 123 (type int)
    >>> elem = ElementTree.Element("elem")
    >>> elem.text = 123
    >>> serialize(elem) # text
    Traceback (most recent call last):
    TypeError: cannot serialize 123 (type int)
    >>> elem = ElementTree.Element("elem")
    >>> elem.tail = 123
    >>> serialize(elem) # tail
    Traceback (most recent call last):
    TypeError: cannot serialize 123 (type int)
    >>> elem = ElementTree.Element("elem")
    >>> elem.set(123, "123")
    >>> serialize(elem) # attribute key
    Traceback (most recent call last):
    TypeError: cannot serialize 123 (type int)
    >>> elem = ElementTree.Element("elem")
    >>> elem.set("123", 123)
    >>> serialize(elem) # attribute value
    Traceback (most recent call last):
    TypeError: cannot serialize 123 (type int)

    """

# doesn't work with lxml.etree
del bug_xmltoolkit21

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

def bug_xmltoolkitX1():
    """
    dump() doesn't flush the output buffer

    >>> tree = ElementTree.XML("<doc><table><tbody/></table></doc>")
    >>> ElementTree.dump(tree); sys.stdout.write("tail")
    <doc><table><tbody /></table></doc>
    tail
    """

# doesn't work with lxml.etree
del bug_xmltoolkitX1

def bug_xmltoolkit39():
    """
    non-ascii element and attribute names doesn't work

    >>> tree = ElementTree.XML("<?xml version='1.0' encoding='iso-8859-1'?><täg />")
    >>> ElementTree.tostring(tree, "utf-8")
    '<t\\xc3\\xa4g />'

    >>> tree = ElementTree.XML("<?xml version='1.0' encoding='iso-8859-1'?><tag ättr='v&#228;lue' />")
    >>> tree.attrib
    {u'\\xe4ttr': u'v\\xe4lue'}
    >>> ElementTree.tostring(tree, "utf-8")
    '<tag \\xc3\\xa4ttr="v\\xc3\\xa4lue" />'

    >>> tree = ElementTree.XML("<?xml version='1.0' encoding='iso-8859-1'?><täg>text</täg>")
    >>> ElementTree.tostring(tree, "utf-8")
    '<t\\xc3\\xa4g>text</t\\xc3\\xa4g>'

    >>> tree = ElementTree.Element(u"täg")
    >>> ElementTree.tostring(tree, "utf-8")
    '<t\\xc3\\xa4g />'

    >>> tree = ElementTree.Element("tag")
    >>> tree.set(u"ättr", u"välue")
    >>> ElementTree.tostring(tree, "utf-8")
    '<tag \\xc3\\xa4ttr="v\\xc3\\xa4lue" />'

    """

# doesn't work with lxml.etree
del bug_xmltoolkit39

def bug_xmltoolkit45():
    """
    problems parsing mixed unicode/non-ascii html documents

    latin-1 text
    >>> p = HTMLTreeBuilder.TreeBuilder()
    >>> p.feed("<p>välue</p>")
    >>> serialize(p.close())
    '<p>v&#228;lue</p>'

    utf-8 text
    >>> p = HTMLTreeBuilder.TreeBuilder(encoding="utf-8")
    >>> p.feed("<p>v\xc3\xa4lue</p>")
    >>> serialize(p.close())
    '<p>v&#228;lue</p>'

    utf-8 text using meta tag
    >>> p = HTMLTreeBuilder.TreeBuilder()
    >>> p.feed("<html><meta http-equiv='Content-Type' content='text/html; charset=utf-8'><p>v\xc3\xa4lue</p></html>")
    >>> serialize(p.close().find("p"))
    '<p>v&#228;lue</p>'

    latin-1 character references
    >>> p = HTMLTreeBuilder.TreeBuilder()
    >>> p.feed("<p>v&#228;lue</p>")
    >>> serialize(p.close())
    '<p>v&#228;lue</p>'

    latin-1 character entities
    >>> p = HTMLTreeBuilder.TreeBuilder()
    >>> p.feed("<p>v&auml;lue</p>")
    >>> serialize(p.close())
    '<p>v&#228;lue</p>'

    mixed latin-1 text and unicode entities
    >>> p = HTMLTreeBuilder.TreeBuilder()
    >>> p.feed("<p>&#8221;välue&#8221;</p>")
    >>> serialize(p.close())
    '<p>&#8221;v&#228;lue&#8221;</p>'

    mixed unicode and latin-1 entities
    >>> p = HTMLTreeBuilder.TreeBuilder()
    >>> p.feed("<p>&#8221;v&auml;lue&#8221;</p>")
    >>> serialize(p.close())
    '<p>&#8221;v&#228;lue&#8221;</p>'

    """

# doesn't work with lxml.etree
del bug_xmltoolkit45

def bug_xmltoolkit46():
    """
    problems parsing open BR tags

   >>> p = HTMLTreeBuilder.TreeBuilder()
    >>> p.feed("<p>key<br>value</p>")
    >>> serialize(p.close())
    '<p>key<br />value</p>'

    """

# doesn't work with lxml.etree
del bug_xmltoolkit46

def bug_xmltoolkit54():
    """
    problems handling internally defined entities

    >>> e = ElementTree.XML("<!DOCTYPE doc [<!ENTITY ldots '&#x8230;'>]><doc>&ldots;</doc>")
    >>> serialize(e)
    '<doc>&#33328;</doc>'
    """

# doesn't work with lxml.etree
del bug_xmltoolkit54

def bug_xmltoolkit55():
    """
    make sure we're reporting the first error, not the last

    >>> e = ElementTree.XML("<!DOCTYPE doc SYSTEM 'doc.dtd'><doc>&ldots;&ndots;&rdots;</doc>")
    Traceback (most recent call last):
    ParseError: undefined entity &ldots;: line 1, column 36
    """

# doesn't work with lxml.etree
del bug_xmltoolkit55

def bug_200708_version():
    """
    >>> parser = ET.XMLParser()
    >>> parser.version
    'Expat 2.0.0'
    >>> parser.feed(open("samples/simple.xml").read())
    >>> print(serialize(parser.close()))
    <root>
       <element key="value">text</element>
       <element>text</element>tail
       <empty-element />
    </root>
    """

# doesn't work with lxml.etree
del bug_200708_version

def bug_200708_newline():
    r"""

    Preserve newlines in attributes.

    >>> e = ET.Element('SomeTag', text="def _f():\n  return 3\n")
    >>> ET.tostring(e)
    '<SomeTag text="def _f():&#10;  return 3&#10;" />'
    >>> ET.XML(ET.tostring(e)).get("text")
    'def _f():\n  return 3\n'
    >>> ET.tostring(ET.XML(ET.tostring(e)))
    '<SomeTag text="def _f():&#10;  return 3&#10;" />'
    """

# doesn't work with lxml.etree
del bug_200708_newline

def bug_200709_default_namespace():
    """

    >>> e = ET.Element("{default}elem")
    >>> s = ET.SubElement(e, "{default}elem")
    >>> serialize(e, default_namespace="default") # 1
    '<elem xmlns="default"><elem /></elem>'

    >>> e = ET.Element("{default}elem")
    >>> s = ET.SubElement(e, "{default}elem")
    >>> s = ET.SubElement(e, "{not-default}elem")
    >>> serialize(e, default_namespace="default") # 2
    '<elem xmlns="default" xmlns:ns1="not-default"><elem /><ns1:elem /></elem>'

    >>> e = ET.Element("{default}elem")
    >>> s = ET.SubElement(e, "{default}elem")
    >>> s = ET.SubElement(e, "elem") # unprefixed name
    >>> serialize(e, default_namespace="default") # 3
    Traceback (most recent call last):
    ValueError: cannot use non-qualified names with default_namespace option

    """

# doesn't work with lxml.etree
del bug_200709_default_namespace

# --------------------------------------------------------------------

if __name__ == "__main__":
    import doctest, selftest
    failed, tested = doctest.testmod(selftest)
    print("%d tests ok." % (tested - failed))
