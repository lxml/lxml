"""
An interface to html5lib that mimics the lxml.html interface.
"""
import functools
import sys
import string

from html5lib import HTMLParser as _HTMLParser
from html5lib.treebuilders.etree_lxml import TreeBuilder
from lxml import etree
from lxml.html import Element, XHTML_NAMESPACE, _contains_block_level_tag

# python3 compatibility
try:
    _strings = basestring
except NameError:
    _strings = (bytes, str)
try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


def _dodgeUseChardet(fn):
    # html5lib does not accept useChardet as an argument, if it
    # detected the html argument would produce unicode objects.
    # However, there is no reasonable way to predict if html5lib will
    # detect the argument to be unicode (all of that code is private),
    # so we'll have to settle for a retry.

    # this decorator wraps a method, which is retried when html5lib
    # complains about the useChardet argument
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except TypeError as exception:
            if 'useChardet' not in kwargs or "'useChardet'" not in str(exception):
                # Some other issue caused the exception. Tell the caller
                raise
            kwargs.pop('useChardet')
            return fn(*args, **kwargs)
    return inner


class _DodgeUseChardetMixin(object):

    @_dodgeUseChardet
    def parse(self, *args, **kwargs):
        return super(_DodgeUseChardetMixin, self).parse(*args, **kwargs)

    @_dodgeUseChardet
    def parseFragment(self, *args, **kwargs):
        return super(_DodgeUseChardetMixin, self).parseFragment(*args, **kwargs)


class HTMLParser(_DodgeUseChardetMixin, _HTMLParser):
    """An html5lib HTML parser with lxml as tree."""

    def __init__(self, strict=False, **kwargs):
        _HTMLParser.__init__(self, strict=strict, tree=TreeBuilder, namespaceHTMLElements=False, **kwargs)


try:
    from html5lib import XHTMLParser as _XHTMLParser
except ImportError:
    pass
else:
    class XHTMLParser(_DodgeUseChardetMixin, _XHTMLParser):
        """An html5lib XHTML Parser with lxml as tree."""

        def __init__(self, strict=False, **kwargs):
            _XHTMLParser.__init__(self, strict=strict, tree=TreeBuilder, **kwargs)

    xhtml_parser = XHTMLParser()


def _find_tag(tree, tag):
    elem = tree.find(tag)
    if elem is not None:
        return elem
    return tree.find('{%s}%s' % (XHTML_NAMESPACE, tag))


def document_fromstring(html, guess_charset=None, parser=None):
    """Parse a whole document into a string."""
    if not isinstance(html, _strings):
        raise TypeError('string required')

    if parser is None:
        parser = html_parser

    options = {}
    if guess_charset is None and isinstance(html, bytes):
        # FIXME: I have no idea why the default differs from fragments_fromstring()
        guess_charset = True
    if guess_charset is not None:
        options['useChardet'] = guess_charset
    return parser.parse(html, **options).getroot()


def fragments_fromstring(html, no_leading_text=False,
                         guess_charset=None, parser=None):
    """Parses several HTML elements, returning a list of elements.

    The first item in the list may be a string.  If no_leading_text is true,
    then it will be an error if there is leading text, and it will always be
    a list of only elements.

    If `guess_charset` is `True` and the text was not unicode but a
    bytestring, the `chardet` library will perform charset guessing on the
    string.
    """
    if not isinstance(html, _strings):
        raise TypeError('string required')

    if parser is None:
        parser = html_parser

    options = {}
    if guess_charset is None and isinstance(html, bytes):
        # FIXME: I have no idea why the default differs from document_fromstring()
        guess_charset = False
    if guess_charset is not None:
        options['useChardet'] = guess_charset
    children = parser.parseFragment(html, 'div', **options)
    if children and isinstance(children[0], _strings):
        if no_leading_text:
            if children[0].strip():
                raise etree.ParserError('There is leading text: %r' %
                                        children[0])
            del children[0]
    return children


def fragment_fromstring(html, create_parent=False,
                        guess_charset=False, parser=None):
    """Parses a single HTML element; it is an error if there is more than
    one element, or if anything but whitespace precedes or follows the
    element.

    If create_parent is true (or is a tag name) then a parent node
    will be created to encapsulate the HTML in a single element.  In
    this case, leading or trailing text is allowed.
    """
    if not isinstance(html, _strings):
        raise TypeError('string required')

    accept_leading_text = bool(create_parent)

    elements = fragments_fromstring(
        html, guess_charset=guess_charset, parser=parser,
        no_leading_text=not accept_leading_text)

    if create_parent:
        if not isinstance(create_parent, _strings):
            create_parent = 'div'
        new_root = Element(create_parent)
        if elements:
            if isinstance(elements[0], _strings):
                new_root.text = elements[0]
                del elements[0]
            new_root.extend(elements)
        return new_root

    if not elements:
        raise etree.ParserError('No elements found')
    if len(elements) > 1:
        raise etree.ParserError('Multiple elements found')
    result = elements[0]
    if result.tail and result.tail.strip():
        raise etree.ParserError('Element followed by text: %r' % result.tail)
    result.tail = None
    return result


def fromstring(html, guess_charset=True, parser=None):
    """Parse the html, returning a single element/document.

    This tries to minimally parse the chunk of text, without knowing if it
    is a fragment or a document.

    base_url will set the document's base_url attribute (and the tree's docinfo.URL)
    """
    if not isinstance(html, _strings):
        raise TypeError('string required')
    doc = document_fromstring(html, parser=parser,
                              guess_charset=guess_charset)

    # document starts with doctype or <html>, full document!
    start = html[:50]
    if isinstance(start, bytes):
        # Allow text comparison in python3.
        # Decode as ascii, that also covers latin-1 and utf-8 for the
        # characters we need.
        start = start.decode('ascii', 'replace')

    start = start.lstrip().lower()
    if start.startswith('<html') or start.startswith('<!doctype'):
        return doc

    head = _find_tag(doc, 'head')

    # if the head is not empty we have a full document
    if len(head):
        return doc

    body = _find_tag(doc, 'body')

    # The body has just one element, so it was probably a single
    # element passed in
    if (len(body) == 1 and (not body.text or not body.text.strip())
        and (not body[-1].tail or not body[-1].tail.strip())):
        return body[0]

    # Now we have a body which represents a bunch of tags which have the
    # content that was passed in.  We will create a fake container, which
    # is the body tag, except <body> implies too much structure.
    if _contains_block_level_tag(body):
        body.tag = 'div'
    else:
        body.tag = 'span'
    return body


def parse(filename_url_or_file, guess_charset=True, parser=None):
    """Parse a filename, URL, or file-like object into an HTML document
    tree.  Note: this returns a tree, not an element.  Use
    ``parse(...).getroot()`` to get the document root.
    """
    if parser is None:
        parser = html_parser
    if not isinstance(filename_url_or_file, _strings):
        fp = filename_url_or_file
    elif _looks_like_url(filename_url_or_file):
        fp = urlopen(filename_url_or_file)
    else:
        fp = open(filename_url_or_file, 'rb')
    return parser.parse(fp, useChardet=guess_charset)


def _looks_like_url(str):
    scheme = urlparse(str)[0]
    if not scheme:
        return False
    elif (sys.platform == 'win32' and
            scheme in string.ascii_letters
            and len(scheme) == 1):
        # looks like a 'normal' absolute path
        return False
    else:
        return True


html_parser = HTMLParser()
