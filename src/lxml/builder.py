"""
Element generator factory by Fredrik Lundh.

Source:
    http://online.effbot.org/2006_11_01_archive.htm#et-builder
    http://effbot.python-hosting.com/file/stuff/sandbox/elementlib/builder.py
"""

import etree as ET

try:
    from functools import partial
except ImportError:
    # fake it for pre-2.5 releases
    def partial(func, tag):
        return lambda *args, **kwargs: func(tag, *args, **kwargs)


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
    """

    def __init__(self, typemap=None, parser=None):
        if parser is not None:
            self._makeelement = parser.makeelement
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
	typemap[str] = typemap[unicode] = add_text

	def add_dict(elem, item):
	    attrib = elem.attrib
	    for k, v in item.items():
		if isinstance(v, basestring):
		    attrib[k] = v
		else:
		    attrib[k] = typemap[type(v)](None, v)
	typemap[dict] = add_dict

	self._typemap = typemap

    def __call__(self, tag, *children, **attrib):
	get = self._typemap.get

        elem = self._makeelement(tag)
	if attrib:
	    get(dict)(elem, attrib)

        for item in children:
            if callable(item):
                item = item()
	    t = get(type(item))
	    if t is None:
		if ET.iselement(item):
		    elem.append(item)
		    continue
		raise TypeError("bad argument type: %r" % item)
	    else:
		v = t(elem, item)
		if v:
		    get(type(v))(elem, v)

        return elem

    def __getattr__(self, tag):
        return partial(self, tag)

# create factory object
E = ElementMaker()
