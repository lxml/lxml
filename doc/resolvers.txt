Document loading and URL resolving
==================================

.. contents::
..
   1  XML Catalogs
   2  URI Resolvers
   3  Document loading in context
   4  I/O access control in XSLT


The normal way to load external entities (such as DTDs) is by using
XML catalogs.  Lxml also has support for user provided document
loaders in both the parsers and XSL transformations.  These so-called
resolvers are subclasses of the etree.Resolver class.

..
  >>> try: from StringIO import StringIO
  ... except ImportError:
  ...    from io import BytesIO
  ...    def StringIO(s):
  ...        if isinstance(s, str): s = s.encode("UTF-8")
  ...        return BytesIO(s)


XML Catalogs
------------

When loading an external entity for a document, e.g. a DTD, the parser
is normally configured to prevent network access (see the
``no_network`` parser option).  Instead, it will try to load the
entity from their local file system path or, in the most common case
that the entity uses a network URL as reference, from a local XML
catalog.

`XML catalogs`_ are the preferred and agreed-on mechanism to load
external entities from XML processors.  Most tools will use them, so
it is worth configuring them properly on a system.  Many Linux
installations use them by default, but on other systems they may need
to get enabled manually.  The `libxml2 site`_ has some documentation
on `how to set up XML catalogs`_

.. _`XML catalogs`: http://www.oasis-open.org/committees/entity/spec.html
.. _`libxml2 site`: http://xmlsoft.org/
.. _`how to set up XML catalogs`: http://xmlsoft.org/catalog.html


URI Resolvers
-------------

Here is an example of a custom resolver:

.. sourcecode:: pycon

  >>> from lxml import etree

  >>> class DTDResolver(etree.Resolver):
  ...     def resolve(self, url, id, context):
  ...         print("Resolving URL '%s'" % url)
  ...         return self.resolve_string(
  ...             '<!ENTITY myentity "[resolved text: %s]">' % url, context)

This defines a resolver that always returns a dynamically generated DTD
fragment defining an entity.  The ``url`` argument passes the system URL of
the requested document, the ``id`` argument is the public ID.  Note that any
of these may be None.  The context object is not normally used by client code.

Resolving is based on the methods of the Resolver object that build
internal representations of the result document.  The following
methods exist:

* ``resolve_string`` takes a parsable string as result document
* ``resolve_filename`` takes a filename
* ``resolve_file`` takes an open file-like object that has at least a read() method
* ``resolve_empty`` resolves into an empty document

The ``resolve()`` method may choose to return None, in which case the next
registered resolver (or the default resolver) is consulted.  Resolving always
terminates if ``resolve()`` returns the result of any of the above
``resolve_*()`` methods.

Resolvers are registered local to a parser:

.. sourcecode:: pycon

  >>> parser = etree.XMLParser(load_dtd=True)
  >>> parser.resolvers.add( DTDResolver() )

Note that we instantiate a parser that loads the DTD.  This is not done by the
default parser, which does no validation.  When we use this parser to parse a
document that requires resolving a URL, it will call our custom resolver:

.. sourcecode:: pycon

  >>> xml = '<!DOCTYPE doc SYSTEM "MissingDTD.dtd"><doc>&myentity;</doc>'
  >>> tree = etree.parse(StringIO(xml), parser)
  Resolving URL 'MissingDTD.dtd'
  >>> root = tree.getroot()
  >>> print(root.text)
  [resolved text: MissingDTD.dtd]

The entity in the document was correctly resolved by the generated DTD
fragment.


Document loading in context
---------------------------

XML documents memorise their initial parser (and its resolvers) during their
life-time.  This means that a lookup process related to a document will use
the resolvers of the document's parser.  We can demonstrate this with a
resolver that only responds to a specific prefix:

.. sourcecode:: pycon

  >>> class PrefixResolver(etree.Resolver):
  ...     def __init__(self, prefix):
  ...         self.prefix = prefix
  ...         self.result_xml = '''\
  ...              <xsl:stylesheet
  ...                     xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  ...                <test xmlns="testNS">%s-TEST</test>
  ...              </xsl:stylesheet>
  ...              ''' % prefix
  ...     def resolve(self, url, pubid, context):
  ...         if url.startswith(self.prefix):
  ...             print("Resolved url %s as prefix %s" % (url, self.prefix))
  ...             return self.resolve_string(self.result_xml, context)

We demonstrate this in XSLT and use the following stylesheet as an example:

.. sourcecode:: pycon

  >>> xml_text = """\
  ... <xsl:stylesheet version="1.0"
  ...    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  ...   <xsl:include href="honk:test"/>
  ...   <xsl:template match="/">
  ...     <test>
  ...       <xsl:value-of select="document('hoi:test')/*/*/text()"/>
  ...     </test>
  ...   </xsl:template>
  ... </xsl:stylesheet>
  ... """

Note that it needs to resolve two URIs: ``honk:test`` when compiling the XSLT
document (i.e. when resolving ``xsl:import`` and ``xsl:include`` elements) and
``hoi:test`` at transformation time, when calls to the ``document`` function
are resolved.  If we now register different resolvers with two different
parsers, we can parse our document twice in different resolver contexts:

.. sourcecode:: pycon

  >>> hoi_parser = etree.XMLParser()
  >>> normal_doc = etree.parse(StringIO(xml_text), hoi_parser)

  >>> hoi_parser.resolvers.add( PrefixResolver("hoi") )
  >>> hoi_doc = etree.parse(StringIO(xml_text), hoi_parser)

  >>> honk_parser = etree.XMLParser()
  >>> honk_parser.resolvers.add( PrefixResolver("honk") )
  >>> honk_doc = etree.parse(StringIO(xml_text), honk_parser)

These contexts are important for the further behaviour of the documents.  They
memorise their original parser so that the correct set of resolvers is used in
subsequent lookups.  To compile the stylesheet, XSLT must resolve the
``honk:test`` URI in the ``xsl:include`` element.  The ``hoi`` resolver cannot
do that:

.. sourcecode:: pycon

  >>> transform = etree.XSLT(normal_doc)
  Traceback (most recent call last):
    ...
  lxml.etree.XSLTParseError: Cannot resolve URI honk:test

  >>> transform = etree.XSLT(hoi_doc)
  Traceback (most recent call last):
    ...
  lxml.etree.XSLTParseError: Cannot resolve URI honk:test

However, if we use the ``honk`` resolver associated with the respective
document, everything works fine:

.. sourcecode:: pycon

  >>> transform = etree.XSLT(honk_doc)
  Resolved url honk:test as prefix honk

Running the transform accesses the same parser context again, but since it now
needs to resolve the ``hoi`` URI in the call to the document function, its
``honk`` resolver will fail to do so:

.. sourcecode:: pycon

  >>> result = transform(normal_doc)
  Traceback (most recent call last):
    ...
  lxml.etree.XSLTApplyError: Cannot resolve URI hoi:test

  >>> result = transform(hoi_doc)
  Traceback (most recent call last):
    ...
  lxml.etree.XSLTApplyError: Cannot resolve URI hoi:test

  >>> result = transform(honk_doc)
  Traceback (most recent call last):
    ...
  lxml.etree.XSLTApplyError: Cannot resolve URI hoi:test

This can only be solved by adding a ``hoi`` resolver to the original parser:

.. sourcecode:: pycon

  >>> honk_parser.resolvers.add( PrefixResolver("hoi") )
  >>> result = transform(honk_doc)
  Resolved url hoi:test as prefix hoi
  >>> print(str(result)[:-1])
  <?xml version="1.0"?>
  <test>hoi-TEST</test>

We can see that the ``hoi`` resolver was called to generate a document that
was then inserted into the result document by the XSLT transformation.  Note
that this is completely independent of the XML file you transform, as the URI
is resolved from within the stylesheet context:

.. sourcecode:: pycon

  >>> result = transform(normal_doc)
  Resolved url hoi:test as prefix hoi
  >>> print(str(result)[:-1])
  <?xml version="1.0"?>
  <test>hoi-TEST</test>

It may be seen as a matter of taste what resolvers the generated document
inherits.  For XSLT, the output document inherits the resolvers of the input
document and not those of the stylesheet.  Therefore, the last result does not
inherit any resolvers at all.


I/O access control in XSLT
--------------------------

By default, XSLT supports all extension functions from libxslt and libexslt as
well as Python regular expressions through EXSLT.  Some extensions enable
style sheets to read and write files on the local file system.

XSLT has a mechanism to control the access to certain I/O operations during
the transformation process.  This is most interesting where XSL scripts come
from potentially insecure sources and must be prevented from modifying the
local file system.  Note, however, that there is no way to keep them from
eating up your precious CPU time, so this should not stop you from thinking
about what XSLT you execute.

Access control is configured using the ``XSLTAccessControl`` class.  It can be
called with a number of keyword arguments that allow or deny specific
operations:

.. sourcecode:: pycon

  >>> transform = etree.XSLT(honk_doc)
  Resolved url honk:test as prefix honk
  >>> result = transform(normal_doc)
  Resolved url hoi:test as prefix hoi

  >>> ac = etree.XSLTAccessControl(read_network=False)
  >>> transform = etree.XSLT(honk_doc, access_control=ac)
  Resolved url honk:test as prefix honk
  >>> result = transform(normal_doc)
  Traceback (most recent call last):
    ...
  lxml.etree.XSLTApplyError: xsltLoadDocument: read rights for hoi:test denied

There are a few things to keep in mind:

* XSL parsing (``xsl:import``, etc.) is not affected by this mechanism
* ``read_file=False`` does not imply ``write_file=False``, all controls are
  independent.
* ``read_file`` only applies to files in the file system.  Any other scheme
  for URLs is controlled by the ``*_network`` keywords.
* If you need more fine-grained control than switching access on and off, you
  should consider writing a custom document loader that returns empty
  documents or raises exceptions if access is denied.
