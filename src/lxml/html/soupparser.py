__doc__ = """External interface to the BeautifulSoup HTML parser.
"""

__all__ = ["fromstring", "parse", "convert_tree"]

import re
from lxml import etree, html
from BeautifulSoup import \
     BeautifulSoup, Tag, Comment, ProcessingInstruction, NavigableString, \
     Declaration


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
    if makeelement is None:
        makeelement = html.html_parser.makeelement
    root = _convert_tree(beautiful_soup_tree, makeelement)
    children = root.getchildren()
    for child in children:
        root.remove(child)
    return children


# helpers

def _parse(source, beautifulsoup, makeelement, **bsargs):
    if beautifulsoup is None:
        beautifulsoup = BeautifulSoup
    if makeelement is None:
        makeelement = html.html_parser.makeelement
    if 'convertEntities' not in bsargs:
        bsargs['convertEntities'] = 'html'
    tree = beautifulsoup(source, **bsargs)
    root = _convert_tree(tree, makeelement)
    # from ET: wrap the document in a html root element, if necessary
    if len(root) == 1 and root[0].tag == "html":
        return root[0]
    root.tag = "html"
    return root

declaration_re = re.compile(r'DOCTYPE\s*HTML(?:\s+PUBLIC)?'
'(?:\s+(\'[^\']*\'|"[^"]*"))?'  '(?:\s+(\'[^\']*\'|"[^"]*"))?', re.IGNORECASE)

def _convert_tree(beautiful_soup_tree, makeelement):
    # Split the tree into three parts:
    # i) everything before the root element: document type
    # declaration, comments, processing instructions, whitespace
    # ii) the root(s),
    # iii) everything after the root: comments, processing
    # instructions, whitespace
    first_element_index, last_element_index = float('inf'), 0
    for i, e in enumerate(beautiful_soup_tree):
        if isinstance(e, Tag):
            first_element_index = min(i, first_element_index)
            last_element_index = i
    last_element_index += 1

    # For a nice, well-formatted document, root (below) is a list
    # consisting of a single <html> tag. However, the document may be
    # a soup like '<meta><head><title>Hello</head><body>Hi all<\p>'. In
    # this example root is a list containing meta, head and body
    # elements.
    pre_root = beautiful_soup_tree.contents[:first_element_index]
    root = beautiful_soup_tree.contents[first_element_index:last_element_index]
    post_root = beautiful_soup_tree.contents[last_element_index:]

    # Check if the documents starts with a document type declaration.
    uri, extid = None, None
    decl = pre_root[0] if len(pre_root) > 0 else None
    if isinstance(decl, Declaration):
        m = declaration_re.match(decl.string)
        if not m:
            # Could not parse doctype. Should we raise an exception?
            # Print a warning message? Just let it pass?
            pass
        else:
            g = m.groups()
            extid, uri = '', ''
            if len(g) >= 1 and g[0] is not None:
                extid = g[0][1:-1] # [1:-1] strips quotes/hyphens
            if len(g) >= 2 and g[1] is not None:
                uri = g[1][1:-1] # [1:-1] strips quotes/hyphens
        pre_root = pre_root[1:]

    # Create root _Element which we shall return.
    if len(root) == 1 and root[0].name.lower() == 'html':
        res_root = makeelement(root[0].name,
                               attrib = dict(root[0].attrs),
                               URI=uri, ExternalID=extid)
        root = root[0].contents
    else:
        # Wrap all elements under a <html> tag, and process them.
        res_root = makeelement('html', URI=uri, ExternalID=extid)

    # Process descendants of the root
    _convert_children(res_root, root, makeelement)

    # Process pre_root
    prev = res_root
    for e in reversed(pre_root):
        if isinstance(e, Comment):
            comment = etree.Comment(e)
            prev.addprevious(comment)
            prev = comment
        elif isinstance(e, ProcessingInstruction):
            PI = etree.ProcessingInstruction(*e.split(' ', 1))
            prev.addprevious(PI)
            prev = PI
        elif isinstance(e, NavigableString) and e.string.strip() == '':
            pass
        else:
            raise Exception('Invalid pre-root element %r' % e)

    # ditto for post_root
    prev = res_root
    for e in post_root:
        if isinstance(e, Comment):
            comment = etree.Comment(e)
            prev.addnext(comment)
            prev = comment
        elif isinstance(e, ProcessingInstruction):
            PI = etree.ProcessingInstruction(*child.split(' ', 1))
            prev.addnext(PI)
            prev = PI
        elif isinstance(e, NavigableString) and e.string.strip() == '':
            pass
        else:
            raise Exception('Invalid post-root element %r' % e)

    return res_root

def _convert_children(parent, beautiful_soup_tree, makeelement):
    SubElement = etree.SubElement
    et_child = None
    for child in beautiful_soup_tree:
        if isinstance(child, Tag):
            et_child = SubElement(parent, child.name, attrib=dict(
                [(k, unescape(v)) for (k,v) in child.attrs]))
            _convert_children(et_child, child, makeelement)
        elif type(child) is NavigableString:
            _append_text(parent, et_child, unescape(child))
        else:
            if isinstance(child, Comment):
                parent.append(etree.Comment(child))
            elif isinstance(child, ProcessingInstruction):
                parent.append(etree.ProcessingInstruction(
                    *child.split(' ', 1)))
            elif isinstance(child, Declaration):
                raise Exception('Document type declaration in the wrong place.')
                pass
            else: # CData
                _append_text(parent, et_child, unescape(child))

def _append_text(parent, element, text):
    if element is None:
        parent.text = (parent.text or '') + text
    else:
        element.tail = (element.tail or '') + text


# copied from ET's ElementSoup

try:
    from html.entities import name2codepoint # Python 3
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
            return m.group(0) # use as is
    return handle_entities(unescape_entity, string)
