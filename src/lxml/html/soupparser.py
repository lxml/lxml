"""External interface to the BeautifulSoup HTML parser.
"""

__all__ = ["fromstring", "parse", "convert_tree"]

import re
from contextlib import contextmanager
from lxml import etree, html

try:
    from bs4 import (
        BeautifulSoup, Tag, Comment, ProcessingInstruction, NavigableString,
        Declaration, Doctype)
    _DECLARATION_OR_DOCTYPE = (Declaration, Doctype)
except ImportError:
    from BeautifulSoup import (
        BeautifulSoup, Tag, Comment, ProcessingInstruction, NavigableString,
        Declaration)
    _DECLARATION_OR_DOCTYPE = Declaration


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
    with _open_if_not_a_file(file) as fileobj:
        root = _parse(fileobj, beautifulsoup, makeelement, **bsargs)
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
    if hasattr(beautifulsoup, "HTML_ENTITIES"):  # bs3
        if 'convertEntities' not in bsargs:
            bsargs['convertEntities'] = 'html'
    if hasattr(beautifulsoup, "DEFAULT_BUILDER_FEATURES"):  # bs4
        if 'features' not in bsargs:
            bsargs['features'] = 'html.parser'  # use Python html parser
    tree = beautifulsoup(source, **bsargs)
    root = _convert_tree(tree, makeelement)
    # from ET: wrap the document in a html root element, if necessary
    if len(root) == 1 and root[0].tag == "html":
        return root[0]
    root.tag = "html"
    return root


@contextmanager
def _open_if_not_a_file(file):
    if hasattr(file, 'read'):
        yield file
    else:
        with open(file) as fileobj:
            yield fileobj


_parse_doctype_declaration = re.compile(
    r'(?:\s|[<!])*DOCTYPE\s*HTML'
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
        elif declaration is None and isinstance(e, _DECLARATION_OR_DOCTYPE):
            declaration = e

    # For a nice, well-formatted document, the variable roots below is
    # a list consisting of a single <html> element. However, the document
    # may be a soup like '<meta><head><title>Hello</head><body>Hi
    # all<\p>'. In this example roots is a list containing meta, head
    # and body elements.
    if first_element_idx is None:
        pre_root = post_root = []
        roots = beautiful_soup_tree.contents
    else:
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

    convert_node = _init_node_converters(makeelement)

    # Process pre_root
    res_root = convert_node(html_root)
    prev = res_root
    for e in reversed(pre_root):
        converted = convert_node(e)
        if converted is not None:
            prev.addprevious(converted)
            prev = converted

    # ditto for post_root
    prev = res_root
    for e in post_root:
        converted = convert_node(e)
        if converted is not None:
            prev.addnext(converted)
            prev = converted

    if declaration is not None:
        try:
            # bs4 provides full Doctype string
            doctype_string = declaration.output_ready()
        except AttributeError:
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


def _init_node_converters(makeelement):
    converters: dict = {}
    ordered_node_types: list[type] = []

    def converter(*types):
        def add(handler):
            for t in types:
                converters[t] = handler
                ordered_node_types.append(t)
            return handler
        return add

    def find_best_converter(node):
        for t in ordered_node_types:
            if isinstance(node, t):
                return converters[t]
        return None

    def get_handler(bs_node):
        try:
            return converters[type(bs_node)]
        except KeyError:
            handler = find_best_converter(bs_node)
            converters[type(bs_node)] = handler
            return handler

    def convert_node(bs_node, parent=None):
        handler = get_handler(bs_node)
        if handler is None:
            return None
        return handler(bs_node, parent)

    def map_attrs(bs_attrs) -> dict:
        if isinstance(bs_attrs, dict):  # bs4
            attribs = {}
            for k, v in bs_attrs.items():
                if isinstance(v, list):
                    v = " ".join(v)
                attribs[k] = unescape(v)
        else:
            attribs = {k: unescape(v) for k, v in bs_attrs}
        return attribs

    def append_text(parent, text):
        try:
            last_child = parent[-1]
        except IndexError:
            parent.text = (parent.text or '') + text
        else:
            last_child.tail = (last_child.tail or '') + text

    # converters are tried in order of their definition

    def create_tag(bs_node, parent):
        attrs = bs_node.attrs
        if parent is not None:
            attribs = map_attrs(attrs) if attrs else None
            res = etree.SubElement(parent, bs_node.name, attrib=attribs)
        else:
            attribs = map_attrs(attrs) if attrs else {}
            res = makeelement(bs_node.name, attrib=attribs)
        return res

    @converter(Tag, _PseudoTag)
    def convert_tag(bs_node, parent):
        res = create_tag(bs_node, parent)
        # Keep a frame for each open tag to avoid recursion for deeply nested
        # BeautifulSoup trees.
        stack = [(iter(bs_node), res, [])]
        while stack:
            children, current_parent, text_parts = stack[-1]
            try:
                child = next(children)
            except StopIteration:
                if text_parts:
                    append_text(current_parent, ''.join(text_parts))
                stack.pop()
                continue

            handler = get_handler(child)
            if handler is None:
                continue
            if handler is convert_text:
                # Batch adjacent text nodes to avoid quadratic string copying.
                text_parts.append(unescape(child))
                continue
            if text_parts:
                append_text(current_parent, ''.join(text_parts))
                text_parts.clear()
            if handler is convert_tag:
                child_res = create_tag(child, current_parent)
                stack.append((iter(child), child_res, []))
            else:
                handler(child, current_parent)
        return res

    @converter(Comment)
    def convert_comment(bs_node, parent):
        res = html.HtmlComment(bs_node)
        if parent is not None:
            parent.append(res)
        return res

    @converter(ProcessingInstruction)
    def convert_pi(bs_node, parent):
        if bs_node.endswith('?'):
            # The PI is of XML style (<?as df?>) but BeautifulSoup
            # interpreted it as being SGML style (<?as df>). Fix.
            bs_node = bs_node[:-1]
        res = etree.ProcessingInstruction(*bs_node.split(' ', 1))
        if parent is not None:
            parent.append(res)
        return res

    @converter(NavigableString)
    def convert_text(bs_node, parent):
        if parent is not None:
            append_text(parent, unescape(bs_node))
        return None

    return convert_node


# Originally copied from ET's ElementSoup.

from html.entities import name2codepoint

# work around oddities in BeautifulSoup's entity handling
def _unescape_entity(m):
    try:
        return chr(name2codepoint[m.group(1)])
    except KeyError:
        return m.group(0)  # use as is

handle_entities = re.compile(r"&(\w+);").sub


def unescape(string, _unescape_entity=_unescape_entity, _handle_entities=handle_entities) -> str:
    return _handle_entities(_unescape_entity, string) if string else ''
