# $Id: selftest.py 2213 2005-01-11 18:49:47Z fredrik $
# elementtree selftest program

# this test script uses Python's "doctest" module to check that the
# *test script* works as expected.

import sys

try:
    from StringIO import StringIO
    BytesIO = StringIO
except ImportError:
    from io import BytesIO, StringIO

from lxml import etree as ElementTree

def unserialize(text):
    file = StringIO(text)
    tree = ElementTree.parse(file)
    return tree.getroot()

def serialize(elem, encoding=None):
    file = BytesIO()
    tree = ElementTree.ElementTree(elem)
    if encoding:
        tree.write(file, encoding=encoding)
    else:
        encoding = "utf-8"
        tree.write(file)
    result = file.getvalue()
    if sys.version_info[0] >= 3:
        result = result.decode(encoding)
    result = result.replace(' />', '/>')
    if result[-1:] == '\n':
        result = result[:-1]
    return result

def summarize(elem):
    return elem.tag

def summarize_list(seq):
    return list(map(summarize, seq))

SAMPLE_XML = unserialize("""
<body>
  <tag>text</tag>
  <tag />
  <section>
    <tag>subtext</tag>
  </section>
</body>
""")

SAMPLE_XML_NS = unserialize("""
<body xmlns="http://effbot.org/ns">
  <tag>text</tag>
  <tag />
  <section>
    <tag>subtext</tag>
  </section>
</body>
""")

# interface tests

def check_string(string):
    len(string)
    for char in string:
        if len(char) != 1:
            print("expected one-character string, got %r" % char)
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
    if element.text != None:
        check_string(element.text)
    if element.tail != None:
        check_string(element.tail)

def check_element_tree(tree):
    check_element(tree.getroot())

def element():
    """
    Test element tree interface.

    >>> element = ElementTree.Element("tag")
    >>> check_element(element)
    >>> tree = ElementTree.ElementTree(element)
    >>> check_element_tree(tree)
    """

def parsefile():
    """
    Test parsing from file.  Note that we're opening the files in
    here; by default, the 'parse' function opens the file in binary
    mode, and doctest doesn't filter out carriage returns.

    >>> tree = ElementTree.parse(open("samples/simple.xml", "rb"))
    >>> tree.write(sys.stdout)
    <root>
       <element key="value">text</element>
       <element>text</element>tail
       <empty-element/>
    </root>
    >>> tree = ElementTree.parse(open("samples/simple-ns.xml", "rb"))
    >>> tree.write(sys.stdout)
    <root xmlns="http://namespace/">
       <element key="value">text</element>
       <element>text</element>tail
       <empty-element/>
    </root>
    """

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

def encoding():
    r"""
    Test encoding issues.

    >>> elem = ElementTree.Element("tag")
    >>> elem.text = u'abc'
    >>> serialize(elem)
    '<tag>abc</tag>'
    >>> serialize(elem, "utf-8")
    '<tag>abc</tag>'
    >>> serialize(elem, "us-ascii")
    '<tag>abc</tag>'
    >>> serialize(elem, "iso-8859-1").lower()
    "<?xml version='1.0' encoding='iso-8859-1'?>\n<tag>abc</tag>"

    >>> elem.text = "<&\"\'>"
    >>> serialize(elem)
    '<tag>&lt;&amp;"\'&gt;</tag>'
    >>> serialize(elem, "utf-8")
    '<tag>&lt;&amp;"\'&gt;</tag>'
    >>> serialize(elem, "us-ascii") # cdata characters
    '<tag>&lt;&amp;"\'&gt;</tag>'
    >>> serialize(elem, "iso-8859-1").lower()
    '<?xml version=\'1.0\' encoding=\'iso-8859-1\'?>\n<tag>&lt;&amp;"\'&gt;</tag>'

    >>> elem.attrib["key"] = "<&\"\'>"
    >>> elem.text = None
    >>> serialize(elem)
    '<tag key="&lt;&amp;&quot;\'&gt;"/>'
    >>> serialize(elem, "utf-8")
    '<tag key="&lt;&amp;&quot;\'&gt;"/>'
    >>> serialize(elem, "us-ascii")
    '<tag key="&lt;&amp;&quot;\'&gt;"/>'
    >>> serialize(elem, "iso-8859-1").lower()
    '<?xml version=\'1.0\' encoding=\'iso-8859-1\'?>\n<tag key="&lt;&amp;&quot;\'&gt;"/>'

    >>> elem.text = u'\xe5\xf6\xf6<>'
    >>> elem.attrib.clear()
    >>> serialize(elem)
    '<tag>&#229;&#246;&#246;&lt;&gt;</tag>'
    >>> serialize(elem, "utf-8")
    '<tag>\xc3\xa5\xc3\xb6\xc3\xb6&lt;&gt;</tag>'
    >>> serialize(elem, "us-ascii")
    '<tag>&#229;&#246;&#246;&lt;&gt;</tag>'
    >>> serialize(elem, "iso-8859-1").lower()
    "<?xml version='1.0' encoding='iso-8859-1'?>\n<tag>\xe5\xf6\xf6&lt;&gt;</tag>"

    >>> elem.attrib["key"] = u'\xe5\xf6\xf6<>'
    >>> elem.text = None
    >>> serialize(elem)
    '<tag key="&#229;&#246;&#246;&lt;&gt;"/>'
    >>> serialize(elem, "utf-8")
    '<tag key="\xc3\xa5\xc3\xb6\xc3\xb6&lt;&gt;"/>'
    >>> serialize(elem, "us-ascii")
    '<tag key="&#229;&#246;&#246;&lt;&gt;"/>'
    >>> serialize(elem, "iso-8859-1").lower()
    '<?xml version=\'1.0\' encoding=\'iso-8859-1\'?>\n<tag key="\xe5\xf6\xf6&lt;&gt;"/>'

    """

if sys.version_info[0] >= 3:
    encoding.__doc__ = encoding.__doc__.replace("u'", "'")

def qname():
    """
    Test QName handling.

    1) decorated tags

    >>> elem = ElementTree.Element("{uri}tag")
    >>> serialize(elem) # 1.1
    '<ns0:tag xmlns:ns0="uri"/>'

##     2) decorated attributes

##     >>> elem.attrib["{uri}key"] = "value"
##     >>> serialize(elem) # 2.1
##     '<ns0:tag ns0:key="value" xmlns:ns0="uri"/>'

    """

def cdata():
    """
    Test CDATA handling (etc).

    >>> serialize(unserialize("<tag>hello</tag>"))
    '<tag>hello</tag>'
    >>> serialize(unserialize("<tag>&#104;&#101;&#108;&#108;&#111;</tag>"))
    '<tag>hello</tag>'
    >>> serialize(unserialize("<tag><![CDATA[hello]]></tag>"))
    '<tag>hello</tag>'

    """

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
    >>> elem = SAMPLE_XML_NS
    >>> summarize_list(elem.findall("tag"))
    []
    >>> summarize_list(elem.findall("{http://effbot.org/ns}tag"))
    ['{http://effbot.org/ns}tag', '{http://effbot.org/ns}tag']
    >>> summarize_list(elem.findall(".//{http://effbot.org/ns}tag"))
    ['{http://effbot.org/ns}tag', '{http://effbot.org/ns}tag', '{http://effbot.org/ns}tag']
    """

# XXX only deep copying is supported

def copy():
    """
    Test copy handling (etc).

    >>> import copy
    >>> e1 = unserialize("<tag>hello<foo/></tag>")
    >>> # e2 = copy.copy(e1)
    >>> e3 = copy.deepcopy(e1)
    >>> e1.find("foo").tag = "bar"

    >>> serialize(e1).replace(' ', '')
    '<tag>hello<bar/></tag>'

##     >>> serialize(e2).replace(' ', '')
##     '<tag>hello<bar/></tag>'

    >>> serialize(e3).replace(' ', '')
    '<tag>hello<foo/></tag>'

    """

def attrib():
    """
    Test attribute handling.

    >>> elem = ElementTree.Element("tag")
    >>> elem.get("key") # 1.1
    >>> elem.get("key", "default") # 1.2
    'default'
    >>> elem.set("key", "value")
    >>> elem.get("key") # 1.3
    'value'

    >>> elem = ElementTree.Element("tag", key="value")
    >>> elem.get("key") # 2.1
    'value'
    >>> elem.attrib # 2.2
    {'key': 'value'}

    >>> elem = ElementTree.Element("tag", {"key": "value"})
    >>> elem.get("key") # 3.1
    'value'
    >>> elem.attrib # 3.2
    {'key': 'value'}

    >>> elem = ElementTree.Element("tag", {"key": "other"}, key="value")
    >>> elem.get("key") # 4.1
    'value'
    >>> elem.attrib # 4.2
    {'key': 'value'}

    """

def makeelement():
    """
    Test makeelement handling.

    >>> elem = ElementTree.Element("tag")
    >>> subelem = elem.makeelement("subtag", {"key": "value"})
    >>> elem.append(subelem)
    >>> serialize(elem)
    '<tag><subtag key="value"/></tag>'

    >>> elem.clear()
    >>> serialize(elem)
    '<tag/>'
    >>> elem.append(subelem)
    >>> serialize(elem)
    '<tag><subtag key="value"/></tag>'

    """

## def observer():
##     """
##     Test observers.

##     >>> def observer(action, elem):
##     ...     print("%s %s" % (action, elem.tag))
##     >>> builder = ElementTree.TreeBuilder()
##     >>> builder.addobserver(observer)
##     >>> parser = ElementTree.XMLParser(builder)
##     >>> parser.feed(open("samples/simple.xml", "rb").read())
##     start root
##     start element
##     end element
##     start element
##     end element
##     start empty-element
##     end empty-element
##     end root

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
##     SyntaxError: undefined entity: line 1, column 10

##     2) custom entity

##     >>> parser = ElementTree.XMLParser()
##     >>> parser.entity["entity"] = "text"
##     >>> parser.feed(ENTITY_XML)
##     >>> root = parser.close()
##     >>> serialize(root)
##     '<document>text</document>'

##     """

if __name__ == "__main__":
    import doctest, selftest2
    failed, tested = doctest.testmod(selftest2)
    print("%d tests ok." % (tested - failed))
