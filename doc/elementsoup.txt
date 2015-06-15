====================
BeautifulSoup Parser
====================

BeautifulSoup_ is a Python package for working with real-world and broken HTML,
just like `lxml.html <lxmlhtml.html>`_.  As of version 4.x, it can use
`different HTML parsers
<http://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-a-parser>`_,
each of which has its advantages and disadvantages (see the link).

lxml can make use of BeautifulSoup as a parser backend, just like BeautifulSoup
can employ lxml as a parser.  When using BeautifulSoup from lxml, however, the
default is to use Python's integrated HTML parser in the
`html.parser <https://docs.python.org/3/library/html.parser.html>`_ module.
In order to make use of the HTML5 parser of
`html5lib <https://pypi.python.org/pypi/html5lib>`_ instead, it is better
to go directly through the `html5parser module <html5parser.html>`_ in
``lxml.html``.

A very nice feature of BeautifulSoup is its excellent `support for encoding
detection`_ which can provide better results for real-world HTML pages that
do not (correctly) declare their encoding.

.. _BeautifulSoup: http://www.crummy.com/software/BeautifulSoup/
.. _`support for encoding detection`: http://www.crummy.com/software/BeautifulSoup/bs4/doc/#unicode-dammit
.. _ElementSoup: http://effbot.org/zone/element-soup.htm

lxml interfaces with BeautifulSoup through the ``lxml.html.soupparser``
module.  It provides three main functions: ``fromstring()`` and ``parse()``
to parse a string or file using BeautifulSoup into an ``lxml.html``
document, and ``convert_tree()`` to convert an existing BeautifulSoup
tree into a list of top-level Elements.

.. contents::
..
   1  Parsing with the soupparser
   2  Entity handling
   3  Using soupparser as a fallback
   4  Using only the encoding detection


Parsing with the soupparser
===========================

The functions ``fromstring()`` and ``parse()`` behave as known from
lxml.  The first returns a root Element, the latter returns an
ElementTree.

There is also a legacy module called ``lxml.html.ElementSoup``, which
mimics the interface provided by Fredrik Lundh's ElementSoup_
module.  Note that the ``soupparser`` module was added in lxml 2.0.3.
Previous versions of lxml 2.0.x only have the ``ElementSoup`` module.

Here is a document full of tag soup, similar to, but not quite like, HTML:

.. sourcecode:: pycon

    >>> tag_soup = '''
    ... <meta/><head><title>Hello</head><body onload=crash()>Hi all<p>'''

All you need to do is pass it to the ``fromstring()`` function:

.. sourcecode:: pycon

    >>> from lxml.html.soupparser import fromstring
    >>> root = fromstring(tag_soup)

To see what we have here, you can serialise it:

.. sourcecode:: pycon

    >>> from lxml.etree import tostring
    >>> print(tostring(root, pretty_print=True).strip())
    <html>
      <meta/>
      <head>
        <title>Hello</title>
      </head>
      <body onload="crash()">Hi all<p/></body>
    </html>

Not quite what you'd expect from an HTML page, but, well, it was broken
already, right?  The parser did its best, and so now it's a tree.

To control how Element objects are created during the conversion
of the tree, you can pass a ``makeelement`` factory function to
``parse()`` and ``fromstring()``.  By default, this is based on the
HTML parser defined in ``lxml.html``.

For a quick comparison, libxml2 2.9.1 parses the same tag soup as
follows.  The only difference is that libxml2 tries harder to adhere
to the structure of an HTML document and moves misplaced tags where
they (likely) belong.  Note, however, that the result can vary between
parser versions.

.. sourcecode:: html

    <html>
      <head>
        <meta/>
        <title>Hello</title>
      </head>
      <body onload="crash()">Hi all<p/></body>
    </html>


Entity handling
===============

By default, the BeautifulSoup parser also replaces the entities it
finds by their character equivalent.

.. sourcecode:: pycon

    >>> tag_soup = '<body>&copy;&euro;&#45;&#245;&#445;<p>'
    >>> body = fromstring(tag_soup).find('.//body')
    >>> body.text
    u'\xa9\u20ac-\xf5\u01bd'

If you want them back on the way out, you can just serialise with the
default encoding, which is 'US-ASCII'.

.. sourcecode:: pycon

    >>> tostring(body)
    '<body>&#169;&#8364;-&#245;&#445;<p/></body>'

    >>> tostring(body, method="html")
    '<body>&#169;&#8364;-&#245;&#445;<p></p></body>'

Any other encoding will output the respective byte sequences.

.. sourcecode:: pycon

    >>> tostring(body, encoding="utf-8")
    '<body>\xc2\xa9\xe2\x82\xac-\xc3\xb5\xc6\xbd<p/></body>'

    >>> tostring(body, method="html", encoding="utf-8")
    '<body>\xc2\xa9\xe2\x82\xac-\xc3\xb5\xc6\xbd<p></p></body>'

    >>> tostring(body, encoding='unicode')
    u'<body>\xa9\u20ac-\xf5\u01bd<p/></body>'

    >>> tostring(body, method="html", encoding='unicode')
    u'<body>\xa9\u20ac-\xf5\u01bd<p></p></body>'


Using soupparser as a fallback
==============================

The downside of using this parser is that it is `much slower`_ than
the C implemented HTML parser of libxml2 that lxml uses.  So if
performance matters, you might want to consider using ``soupparser``
only as a fallback for certain cases.

.. _`much slower`: http://blog.ianbicking.org/2008/03/30/python-html-parser-performance/

One common problem of lxml's parser is that it might not get the
encoding right in cases where the document contains a ``<meta>`` tag
at the wrong place.  In this case, you can exploit the fact that lxml
serialises much faster than most other HTML libraries for Python.
Just serialise the document to unicode and if that gives you an
exception, re-parse it with BeautifulSoup to see if that works
better.

.. sourcecode:: pycon

    >>> tag_soup = '''\
    ... <meta http-equiv="Content-Type"
    ...       content="text/html;charset=utf-8" />
    ... <html>
    ...   <head>
    ...     <title>Hello W\xc3\xb6rld!</title>
    ...   </head>
    ...   <body>Hi all</body>
    ... </html>'''

    >>> import lxml.html
    >>> import lxml.html.soupparser

    >>> root = lxml.html.fromstring(tag_soup)
    >>> try:
    ...     ignore = tostring(root, encoding='unicode')
    ... except UnicodeDecodeError:
    ...     root = lxml.html.soupparser.fromstring(tag_soup)


Using only the encoding detection
=================================

Even if you prefer lxml's fast HTML parser, you can still benefit
from BeautifulSoup's `support for encoding detection`_ in the
``UnicodeDammit`` class.  Once it succeeds in decoding the data,
you can simply pass the resulting Unicode string into lxml's parser.

.. sourcecode:: pycon

    >>> try:
    ...    from bs4 import UnicodeDammit             # BeautifulSoup 4
    ...
    ...    def decode_html(html_string):
    ...        converted = UnicodeDammit(html_string)
    ...        if not converted.unicode_markup:
    ...            raise UnicodeDecodeError(
    ...                "Failed to detect encoding, tried [%s]",
    ...                ', '.join(converted.tried_encodings))
    ...        # print converted.original_encoding
    ...        return converted.unicode_markup
    ...
    ... except ImportError:
    ...    from BeautifulSoup import UnicodeDammit   # BeautifulSoup 3
    ...
    ...    def decode_html(html_string):
    ...        converted = UnicodeDammit(html_string, isHTML=True)
    ...        if not converted.unicode:
    ...            raise UnicodeDecodeError(
    ...                "Failed to detect encoding, tried [%s]",
    ...                ', '.join(converted.triedEncodings))
    ...        # print converted.originalEncoding
    ...        return converted.unicode

    >>> root = lxml.html.fromstring(decode_html(tag_soup))
