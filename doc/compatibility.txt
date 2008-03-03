=======================================
ElementTree compatibility of lxml.etree
=======================================

A lot of care has been taken to ensure compatibility between etree and
ElementTree.  Nonetheless, some differences and incompatibilities exist:

* Importing etree is obviously different; etree uses a lower-case
  package name, while ElementTree uses a combination of upper-case and
  lower case in imports:

  .. sourcecode:: python

    # etree
    from lxml.etree import Element

    # ElementTree
    from elementtree.ElementTree import Element

    # ElementTree in the Python 2.5 standard library
    from xml.etree.ElementTree import Element

  When switching over code from ElementTree to lxml.etree, and you're using
  the package name prefix 'ElementTree', you can do the following:

  .. sourcecode:: python

    # instead of
    from elementtree import ElementTree
    # use
    from lxml import etree as ElementTree

* lxml.etree offers a lot more functionality, such as XPath, XSLT, Relax NG,
  and XML Schema support, which (c)ElementTree does not offer.

* etree has a different idea about Python unicode strings than ElementTree.
  In most parts of the API, ElementTree uses plain strings and unicode strings
  as what they are.  This includes Element.text, Element.tail and many other
  places.  However, the ElementTree parsers assume by default that any string
  (`str` or `unicode`) contains ASCII data.  They raise an exception if
  strings do not match the expected encoding.

  etree has the same idea about plain strings (`str`) as ElementTree.  For
  unicode strings, however, etree assumes throughout the API that they are
  Python unicode encoded strings rather than byte data.  This includes the
  parsers.  It is therefore perfectly correct to pass XML unicode data into
  the etree parsers in form of Python unicode strings.  It is an error, on the
  other hand, if unicode strings specify an encoding in their XML declaration,
  as this conflicts with the characteristic encoding of Python unicode
  strings.

* ElementTree allows you to place an Element in two different trees at the
  same time.  Thus, this:

  .. sourcecode:: python

    a = Element('a')
    b = SubElement(a, 'b')
    c = Element('c')
    c.append(b)

  will result in the following tree a:

  .. sourcecode:: xml

    <a><b /></a>

  and the following tree c:

  .. sourcecode:: xml

    <c><b /></c>

  In lxml, this behavior is different, because lxml is built on top of a tree
  that maintains parent relationships for elements (like W3C DOM).  This means
  an element can only exist in a single tree at the same time.  Adding an
  element in some tree to another tree will cause this element to be moved.

  So, for tree a we will get:

  .. sourcecode:: xml

    <a></a>

  and for tree c we will get:

  .. sourcecode:: xml

    <c><b/></c>

  Unfortunately this is a rather fundamental difference in behavior, which is
  hard to change.  It won't affect some applications, but if you want to port
  code you must unfortunately make sure that it doesn't affect yours.

* etree allows navigation to the parent of a node by the ``getparent()``
  method and to the siblings by calling ``getnext()`` and ``getprevious()``.
  This is not possible in ElementTree as the underlying tree model does not
  have this information.

* When trying to set a subelement using __setitem__ that is in fact not an
  Element but some other object, etree raises a TypeError, and ElementTree
  raises an AssertionError.  This also applies to some other places of the
  API.  In general, etree tries to avoid AssertionErrors in favour of being
  more specific about the reason for the exception.

* When parsing fails in ``iterparse()``, ElementTree up to version
  1.2.x raises a low-level ``ExpatError`` instead of a ``SyntaxError``
  as the other parsers.  Both lxml and ElementTree 1.3 raise a
  ``ParseError`` for parser errors.

* The ``iterparse()`` function in lxml is implemented based on the libxml2
  parser and tree generator.  This means that modifications of the document
  root or the ancestors of the current element during parsing can irritate the
  parser and even segfault.  While this is not a problem in the Python object
  structure used by ElementTree, the C tree underlying lxml suffers from it.
  The golden rule for ``iterparse()`` on lxml therefore is: do not touch
  anything that will have to be touched again by the parser later on.  See the
  lxml parser documentation on this.

* ElementTree ignores comments and processing instructions when parsing XML,
  while etree will read them in and treat them as Comment or
  ProcessingInstruction elements respectively.  This is especially visible
  where comments are found inside text content, which is then split by the
  Comment element.

  You can disable this behaviour by passing the boolean ``remove_comments``
  and/or ``remove_pis`` keyword arguments to the parser you use.  For
  convenience and to support portable code, you can also use the
  ``etree.ETCompatXMLParser`` instead of the default ``etree.XMLParser``.  It
  tries to provide a default setup that is as close to the ElementTree parser
  as possible.

* The ``TreeBuilder`` class of ``lxml.etree`` uses a different
  signature for the ``start()`` method.  It accepts an additional
  argument ``nsmap`` to propagate the namespace declarations of an
  element in addition to its own namespace.  To assure compatibility
  with ElementTree (which does not support this argument), lxml checks
  if the method accepts 3 arguments before calling it, and otherwise
  drops the namespace mapping.  This should work with most existing
  ElementTree code, although there may still be conflicting cases.

* ElementTree 1.2 has a bug when serializing an empty Comment (no text
  argument given) to XML, etree serializes this successfully.

* ElementTree adds whitespace around comments on serialization, lxml does
  not.  This means that a comment text "text" that ElementTree serializes as
  "<!-- text -->" will become "<!--text-->" in lxml.

* When the string '*' is used as tag filter in the ``Element.getiterator()``
  method, ElementTree returns all elements in the tree, including comments and
  processing instructions. lxml.etree only returns real Elements, i.e. tree
  nodes that have a string tag name.  Without a filter, both libraries iterate
  over all nodes.

  Note that currently only lxml.etree supports passing the ``Element`` factory
  function as filter to select only Elements.  Both libraries support passing
  the ``Comment`` and ``ProcessingInstruction`` factories to select the
  respective tree nodes.

* ElementTree merges the target of a processing instruction into ``PI.text``,
  while lxml.etree puts it into the ``.target`` property and leaves it out of
  the ``.text`` property.  The ``pi.text`` in ElementTree therefore
  correspondents to ``pi.target + " " + pi.text`` in lxml.etree.

* Because etree is built on top of libxml2, which is namespace prefix aware,
  etree preserves namespaces declarations and prefixes while ElementTree tends
  to come up with its own prefixes (ns0, ns1, etc).  When no namespace prefix
  is given, however, etree creates ElementTree style prefixes as well.

* etree has a 'prefix' attribute (read-only) on elements giving the Element's
  prefix, if this is known, and None otherwise (in case of no namespace at
  all, or default namespace).

* etree further allows passing an 'nsmap' dictionary to the Element and
  SubElement element factories to explicitly map namespace prefixes to
  namespace URIs.  These will be translated into namespace declarations on
  that element.  This means that in the probably rare case that you need to
  construct an attribute called 'nsmap', you need to be aware that unlike in
  ElementTree, you cannot pass it as a keyword argument to the Element and
  SubElement factories directly.

* ElementTree allows QName objects as attribute values and resolves their
  prefix on serialisation (e.g. an attribute value ``QName("{myns}myname")``
  becomes "p:myname" if "p" is the namespace prefix of "myns").  lxml.etree
  also allows you to set attribute values from QName instances (and also .text
  values), but it resolves their prefix immediately and stores the plain text
  value.  So, if prefixes are modified later on, e.g. by moving a subtree to a
  different tree (which reassigns the prefix mappings), the text values will
  not be updated and you might end up with an undefined prefix.

* etree elements can be copied using ``copy.deepcopy()`` and ``copy.copy()``,
  just like ElementTree's.  However, ``copy.copy()`` does *not* create a
  shallow copy where elements are shared between trees, as this makes no sense
  in the context of libxml2 trees.  Note that lxml can deep-copy trees
  considerably faster than ElementTree, so a deep copy might still be fast
  enough to replace a shallow copy in your case.
