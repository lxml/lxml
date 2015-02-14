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
    root = _convert_tree(beautiful_soup_tree, makeelement)
    children = root.getchildren()
    for child in children:
        root.remove(child)
    return children


# helpers

def _parse(source, beautifulsoup, makeelement, **bsargs):
    if beautifulsoup is None:
        beautifulsoup = BeautifulSoup
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
    first_element_idx, last_element_idx = float('inf'), 0
    for i, e in enumerate(beautiful_soup_tree):
        if isinstance(e, Tag):
            first_element_idx = min(i, first_element_idx)
            last_element_idx = i

    # For a nice, well-formatted document, the variable root below is
    # a list consisting of a single <html> element. However, the document
    # may be a soup like '<meta><head><title>Hello</head><body>Hi
    # all<\p>'. In this example root is a list containing meta, head
    # and body elements.
    pre_root = beautiful_soup_tree.contents[:first_element_idx]
    root = beautiful_soup_tree.contents[first_element_idx:last_element_idx+1]
    post_root = beautiful_soup_tree.contents[last_element_idx+1:]

    # Check if the documents starts with a document type declaration.
    external_id, sys_uri = None, None
    for decl in pre_root:
        if not isinstance(decl, Declaration):
            continue
        m = declaration_re.match(decl.string)
        if not m:
            # Something is wrong if we end up in here. Since soupparser should
            # tolerate errors, do not raise Exception, just let it pass.
            pass
        else:
            g = m.groups()
            external_id, sys_uri = '', ''
            if len(g) >= 1 and g[0] is not None:
                external_id = g[0][1:-1] # [1:-1] strips quotes/hyphens
            if len(g) >= 2 and g[1] is not None:
                sys_uri = g[1][1:-1] # [1:-1] strips quotes/hyphens
        pre_root.remove(decl)
        break # Assume there is only one declaration, as there should.

    # Create root _Element which we shall return.
    if len(root) == 1 and root[0].name.lower() == 'html':
        res_root_name = root[0].name
        res_root_attrib = dict(root[0].attrs)
        root_children = root[0].contents
    else:
        res_root_name = 'html'
        res_root_attrib = { }
        # Children of new, proper root are all current top-level elements.
        root_children = root
    if makeelement is None:
        res_root = etree.HTMLParser().makehtmldocument(
            external_id, sys_uri).getroot()
        makeelement = html.html_parser.makeelement
    else:
        # We were given makeelement function, whose API most likely
        # does not support setting document type declaration.  So the
        # results declaration may be completely wrong, but there is
        # nothing we can do.
        res_root = makeelement(res_root_name, res_root_attrib)

    # Process descendants of the root
    _convert_children(res_root, root_children, makeelement)

    # Process pre_root
    prev = res_root
    for e in reversed(pre_root):
        if isinstance(e, Comment):
            comment = etree.Comment(e)
            prev.addprevious(comment)
            prev = comment
        elif isinstance(e, ProcessingInstruction):
            args = e.split(' ', 1)
            if args[1][-1] == '?':
                args[1] = args[1][:-1]
            PI = etree.ProcessingInstruction(*args)
            prev.addprevious(PI)
            prev = PI
        elif isinstance(e, NavigableString) and e.string.strip() == '':
            pass
        else:
            # Something is wrong if we end up in here. Since soupparser should
            # tolerate errors, do not raise Exception, just let it pass.
            pass

    # ditto for post_root
    prev = res_root
    for e in post_root:
        if isinstance(e, Comment):
            comment = etree.Comment(e)
            prev.addnext(comment)
            prev = comment
        elif isinstance(e, ProcessingInstruction):
            args = e.split(' ', 1)
            if args[1][-1] == '?':
                args[1] = args[1][:-1]
            PI = etree.ProcessingInstruction(*args)
            prev.addnext(PI)
            prev = PI
        elif isinstance(e, NavigableString) and e.string.strip() == '':
            pass
        else:
            pass

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
                args = e.split(' ', 1)
                if args[1][-1] == '?':
                    args[1] = args[1][:-1]
                PI = etree.ProcessingInstruction(*args)
                parent.append(PI)
            elif isinstance(child, Declaration):
                # Something is wrong if we end up in here. Since
                # soupparser should tolerate errors, do not raise
                # Exception, just let it pass.
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
