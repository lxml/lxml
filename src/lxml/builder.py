#
# Element generator factory by Fredrik Lundh.
#
# Source:
#    http://online.effbot.org/2006_11_01_archive.htm#et-builder
#    http://effbot.python-hosting.com/file/stuff/sandbox/elementlib/builder.py
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2004 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

"""
The ``E`` Element factory for generating XML documents.
"""

import lxml.etree as ET

try:
    from functools import partial
except ImportError:
    # fake it for pre-2.5 releases
    def partial(func, tag):
        return lambda *args, **kwargs: func(tag, *args, **kwargs)

try:
    callable
except NameError:
    # Python 3
    def callable(f):
        return hasattr(f, '__call__')

try:
    basestring
except NameError:
    basestring = str

try:
    unicode
except NameError:
    unicode = str


class ElementMaker(object):
    """Element generator factory.

    Unlike the ordinary Element factory, the E factory allows you to pass in
    more than just a tag and some optional attributes; you can also pass in
    text and other elements.  The text is added as either text or tail
    attributes, and elements are inserted at the right spot.  Some small
    examples::

        >>> from lxml import etree as ET
        >>> from lxml.builder import E

        >>> ET.tostring(E("tag"))
        '<tag/>'
        >>> ET.tostring(E("tag", "text"))
        '<tag>text</tag>'
        >>> ET.tostring(E("tag", "text", key="value"))
        '<tag key="value">text</tag>'
        >>> ET.tostring(E("tag", E("subtag", "text"), "tail"))
        '<tag><subtag>text</subtag>tail</tag>'

    For simple tags, the factory also allows you to write ``E.tag(...)`` instead
    of ``E('tag', ...)``::

        >>> ET.tostring(E.tag())
        '<tag/>'
        >>> ET.tostring(E.tag("text"))
        '<tag>text</tag>'
        >>> ET.tostring(E.tag(E.subtag("text"), "tail"))
        '<tag><subtag>text</subtag>tail</tag>'

    Here's a somewhat larger example; this shows how to generate HTML
    documents, using a mix of prepared factory functions for inline elements,
    nested ``E.tag`` calls, and embedded XHTML fragments::

        # some common inline elements
        A = E.a
        I = E.i
        B = E.b

        def CLASS(v):
            # helper function, 'class' is a reserved word
            return {'class': v}

        page = (
            E.html(
                E.head(
                    E.title("This is a sample document")
                ),
                E.body(
                    E.h1("Hello!", CLASS("title")),
                    E.p("This is a paragraph with ", B("bold"), " text in it!"),
                    E.p("This is another paragraph, with a ",
                        A("link", href="http://www.python.org"), "."),
                    E.p("Here are some reservered characters: <spam&egg>."),
                    ET.XML("<p>And finally, here is an embedded XHTML fragment.</p>"),
                )
            )
        )

        print ET.tostring(page)

    Here's a prettyprinted version of the output from the above script::

        <html>
          <head>
            <title>This is a sample document</title>
          </head>
          <body>
            <h1 class="title">Hello!</h1>
            <p>This is a paragraph with <b>bold</b> text in it!</p>
            <p>This is another paragraph, with <a href="http://www.python.org">link</a>.</p>
            <p>Here are some reservered characters: &lt;spam&amp;egg&gt;.</p>
            <p>And finally, here is an embedded XHTML fragment.</p>
          </body>
        </html>

    For namespace support, you can pass a namespace map (``nsmap``)
    and/or a specific target ``namespace`` to the ElementMaker class::

    >>> E = ElementMaker(namespace="http://my.ns/")
    >>> print(ET.tostring( E.test ))
    <test xmlns="http://my.ns/"/>

    >>> E = ElementMaker(namespace="http://my.ns/", nsmap={'p':'http://my.ns/'})
    >>> print(ET.tostring( E.test ))
    <p:test xmlns:p="http://my.ns/"/>
    """

    def __init__(self, typemap=None,
                 namespace=None, nsmap=None, makeelement=None):
        if namespace is not None:
            self._namespace = '{' + namespace + '}'
        else:
            self._namespace = None

        if nsmap:
            self._nsmap = dict(nsmap)
        else:
            self._nsmap = None

        if makeelement is not None:
            assert callable(makeelement)
            self._makeelement = makeelement
        else:
            self._makeelement = ET.Element

        # initialize type map for this element factory

        if typemap:
            typemap = typemap.copy()
        else:
            typemap = {}
        
        def add_text(elem, item):
            if len(elem):
                elem[-1].tail = (elem[-1].tail or "") + item
            else:
                elem.text = (elem.text or "") + item
        if str not in typemap:
            typemap[str] = add_text
        if unicode not in typemap:
            typemap[unicode] = add_text

        def add_dict(elem, item):
            attrib = elem.attrib
            for k, v in item.items():
                if isinstance(v, basestring):
                    attrib[k] = v
                else:
                    attrib[k] = typemap[type(v)](None, v)
        if dict not in typemap:
            typemap[dict] = add_dict

        def add_list(elem, lst):
            for item in lst:
                if ET.iselement(item) and item.getparent() is not None:
                    raise ValueError("Adding an item with a parent would move "
                                     "the item rather than copying.  Be "
                                     "explicit by calling either .move() or "
                                     "deepcopy().")
                self.add_item(elem, item)
        if list not in typemap:
            typemap[list] = add_list

        self._typemap = typemap

    def add_item(self, elem, item):
        get = self._typemap.get

        if callable(item):
            item = item()
        t = get(type(item))
        if t is None:
            if ET.iselement(item):
                elem.append(item)
                return
            for basetype in type(item).__mro__:
                # See if the typemap knows of any of this type's bases.
                t = get(basetype)
                if t is not None:
                    break
            else:
                raise TypeError("bad argument type: %s(%r)" %
                                (type(item).__name__, item))
        v = t(elem, item)
        if v:
            get(type(v))(elem, v)

    def __call__(self, tag, *children, **attrib):
        if self._namespace is not None and tag[0] != '{':
            tag = self._namespace + tag
        elem = self._makeelement(tag, nsmap=self._nsmap)
        if attrib:
            self._typemap.get(dict)(elem, attrib)

        for item in children:
            self.add_item(elem, item)

        return elem

    def __getattr__(self, tag):
        return partial(self, tag)

# create factory object
E = ElementMaker()
