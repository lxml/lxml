__doc__ = """External interface to the BeautifulSoup HTML parser.
"""

__all__ = ["fromstring", "parse", "convert_tree"]

import re
from lxml import etree, html

try:
    from bs4 import (
        BeautifulSoup, Tag, Comment, ProcessingInstruction, NavigableString, Declaration, CData, Doctype)
except ImportError:
    from BeautifulSoup import (
        BeautifulSoup, Tag, Comment, ProcessingInstruction, NavigableString, Declaration, CData)
    class Doctype:
        pass

def fromstring(data, beautifulsoup=None, makeelement=None, **bsargs):
    """Parse a string of HTML data into an Element tree using the
    BeautifulSoup parser.

    Returns the root ``<html>`` Element of the tree.

    You can pass a different BeautifulSoup parser through the
    `beautifulsoup` keyword, and a diffent Element factory function
    through the `makeelement` keyword.  By default, the standard
    ``BeautifulSoup`` class and the default factory of `lxml.html` are
    used.
    """
    return _parse(data, beautifulsoup, makeelement, **bsargs)


def parse(file, beautifulsoup=None, makeelement=None, **bsargs):
    """Parse a file into an ElemenTree using the BeautifulSoup parser.

    You can pass a different BeautifulSoup parser through the
    `beautifulsoup` keyword, and a diffent Element factory function
    through the `makeelement` keyword.  By default, the standard
    ``BeautifulSoup`` class and the default factory of `lxml.html` are
    used.
    """
    if not hasattr(file, 'read'):
        file = open(file)
    root = _parse(file, beautifulsoup, makeelement, **bsargs)
    return etree.ElementTree(root)


def convert_tree(beautiful_soup_tree, makeelement=None):
    """Convert a BeautifulSoup tree to a list of Element trees.

    Returns a list instead of a single root Element to support
    HTML-like soup with more than one root element.

    You can pass a different Element factory through the `makeelement`
    keyword.
    """
    root = _convert_tree(beautiful_soup_tree, makeelement)
    children = root.getchildren()
    for child in children:
        root.remove(child)
    return children


# helpers

def _parse(source, beautifulsoup, makeelement, **bsargs):
    if beautifulsoup is None:
        beautifulsoup = BeautifulSoup
    if hasattr(beautifulsoup, "HTML_ENTITIES"): # bs3
        if 'convertEntities' not in bsargs:
            bsargs['convertEntities'] = 'html'
    if hasattr(beautifulsoup, "DEFAULT_BUILDER_FEATURES"): # bs4
        if 'features' not in bsargs:
            bsargs['features'] = ['html.parser'] # force bs html parser
    tree = beautifulsoup(source, **bsargs)
    root = _convert_tree(tree, makeelement)
    # from ET: wrap the document in a html root element, if necessary
    if len(root) == 1 and root[0].tag == "html":
        return root[0]
    root.tag = "html"
    return root


_parse_doctype_declaration = re.compile(
    r'DOCTYPE\s*HTML'
    r'(?:\s+PUBLIC)?(?:\s+(\'[^\']*\'|"[^"]*"))?'
    r'(?:\s+(\'[^\']*\'|"[^"]*"))?',
    re.IGNORECASE).match


class _PseudoTag:
    # Minimal imitation of BeautifulSoup.Tag
    def __init__(self, contents):
        self.name = 'html'
        self.attrs = []
        self.contents = contents

    def __iter__(self):
        return self.contents.__iter__()


def _convert_tree(beautiful_soup_tree, makeelement):
    if makeelement is None:
        makeelement = html.html_parser.makeelement

    # Split the tree into three parts:
    # i) everything before the root element: document type
    # declaration, comments, processing instructions, whitespace
    # ii) the root(s),
    # iii) everything after the root: comments, processing
    # instructions, whitespace
    first_element_idx = last_element_idx = None
    html_root = declaration = None
    for i, e in enumerate(beautiful_soup_tree):
        if isinstance(e, Tag):
            if first_element_idx is None:
                first_element_idx = i
            last_element_idx = i
            if html_root is None and e.name and e.name.lower() == 'html':
                html_root = e
        elif declaration is None and isinstance(e, (Declaration, Doctype)):
            declaration = e

    # For a nice, well-formatted document, the variable roots below is
    # a list consisting of a single <html> element. However, the document
    # may be a soup like '<meta><head><title>Hello</head><body>Hi
    # all<\p>'. In this example roots is a list containing meta, head
    # and body elements.
    pre_root = beautiful_soup_tree.contents[:first_element_idx]
    roots = beautiful_soup_tree.contents[first_element_idx:last_element_idx+1]
    post_root = beautiful_soup_tree.contents[last_element_idx+1:]

    # Reorganize so that there is one <html> root...
    if html_root is not None:
        # ... use existing one if possible, ...
        i = roots.index(html_root)
        html_root.contents = roots[:i] + html_root.contents + roots[i+1:]
    else:
        # ... otherwise create a new one.
        html_root = _PseudoTag(roots)

    # Process pre_root
    res_root = _convert_node(html_root, None, makeelement)
    prev = res_root
    for e in reversed(pre_root):
        converted = _convert_node(e)
        if converted is not None:
            prev.addprevious(converted)
            prev = converted

    # ditto for post_root
    prev = res_root
    for e in post_root:
        converted = _convert_node(e)
        if converted is not None:
            prev.addnext(converted)
            prev = converted

    if declaration is not None:
        if hasattr(declaration, "output_ready"):
            # bs4, got full Doctype string
            doctype_string = declaration.output_ready().strip().strip("<!>")
        else:
            doctype_string = declaration.string
        match = _parse_doctype_declaration(doctype_string)
        if not match:
            # Something is wrong if we end up in here. Since soupparser should
            # tolerate errors, do not raise Exception, just let it pass.
            pass
        else:
            external_id, sys_uri = match.groups()
            docinfo = res_root.getroottree().docinfo
            # strip quotes and update DOCTYPE values (any of None, '', '...')
            docinfo.public_id = external_id and external_id[1:-1]
            docinfo.system_url = sys_uri and sys_uri[1:-1]

    return res_root


def _convert_node(bs_node, parent=None, makeelement=None):
    res = None
    if isinstance(bs_node, (Tag, _PseudoTag)):
        if isinstance(bs_node.attrs, dict): # bs4
            attribs = {}
            for k, v in bs_node.attrs.items():
                if isinstance(v, list):
                    v = " ".join(v)
                attribs[k] = unescape(v)
        else:
            attribs = dict((k, unescape(v)) for k, v in bs_node.attrs)
        if parent is not None:
            res = etree.SubElement(parent, bs_node.name, attrib=attribs)
        else:
            res = makeelement(bs_node.name, attrib=attribs)
        for child in bs_node:
            _convert_node(child, res)
    elif type(bs_node) is NavigableString:
        if parent is None:
            return None
        _append_text(parent, unescape(bs_node))
    elif isinstance(bs_node, Comment):
        res = etree.Comment(bs_node)
        if parent is not None:
            parent.append(res)
    elif isinstance(bs_node, ProcessingInstruction):
        if bs_node.endswith('?'):
            # The PI is of XML style (<?as df?>) but BeautifulSoup
            # interpreted it as being SGML style (<?as df>). Fix.
            bs_node = bs_node[:-1]
        res = etree.ProcessingInstruction(*bs_node.split(' ', 1))
        if parent is not None:
            parent.append(res)
    elif isinstance(bs_node, Declaration):
        pass
    elif isinstance(bs_node, CData):
        _append_text(parent, unescape(bs_node))
    return res


def _append_text(parent, text):
    if len(parent) == 0:
        parent.text = (parent.text or '') + text
    else:
        parent[-1].tail = (parent[-1].tail or '') + text


# copied from ET's ElementSoup

try:
    from html.entities import name2codepoint  # Python 3
except ImportError:
    from htmlentitydefs import name2codepoint


handle_entities = re.compile("&(\w+);").sub


def unescape(string):
    if not string:
        return ''
    # work around oddities in BeautifulSoup's entity handling
    def unescape_entity(m):
        try:
            return unichr(name2codepoint[m.group(1)])
        except KeyError:
            return m.group(0)  # use as is
    return handle_entities(unescape_entity, string)
