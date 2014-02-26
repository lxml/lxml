=======================
What's new in lxml 2.0?
=======================

.. contents::
..
   1  Changes in etree and objectify
     1.1  Incompatible changes
     1.2  Enhancements
     1.3  Deprecation
   2  New modules
     2.1  lxml.usedoctest
     2.2  lxml.html
     2.3  lxml.cssselect


During the development of the lxml 1.x series, a couple of quirks were
discovered in the design that made the API less obvious and its future
extensions harder than necessary. lxml 2.0 is a soft evolution of lxml 1.x
towards a simpler, more consistent and more powerful API - with some major
extensions.  Wherever possible, lxml 1.3 comes close to the semantics of lxml
2.0, so that migrating should be easier for code that currently runs with 1.3.

One of the important internal changes was the switch from the Pyrex_
compiler to Cython_, which provides better optimisation and improved
support for newer Python language features.  This allows the code of
lxml to become more Python-like again, while the performance improves
as Cython continues its own development.  The code simplification,
which will continue throughout the 2.x series, will hopefully make it
even easier for users to contribute.

.. _Cython: http://www.cython.org/
.. _Pyrex:  http://www.cosc.canterbury.ac.nz/~greg/python/Pyrex/


Changes in etree and objectify
==============================

A graduation towards a more consistent API cannot go without a certain amount
of incompatible changes.  The following is a list of those differences that
applications need to take into account when migrating from lxml 1.x to lxml
2.0.

Incompatible changes
--------------------

* lxml 0.9 introduced a feature called `namespace implementation`_.  The
  global ``Namespace`` factory was added to register custom element classes
  and have lxml.etree look them up automatically.  However, the later
  development of further class lookup mechanisms made it appear less and less
  adequate to register this mapping at a global level, so lxml 1.1 first
  removed the namespace based lookup from the default setup and lxml 2.0
  finally removes the global namespace registry completely.  As all other
  lookup mechanisms, the namespace lookup is now local to a parser, including
  the registry itself.  Applications that use a module-level parser can easily
  map its ``get_namespace()`` method to a global ``Namespace`` function to
  mimic the old behaviour.

  .. _`namespace implementation`: element_classes.html#implementing-namespaces

* Some API functions now require passing options as keyword arguments,
  as opposed to positional arguments.  This restriction was introduced
  to make the API usage independent of future extensions such as the
  addition of new positional arguments.  Users should not rely on the
  position of an optional argument in function signatures and instead
  pass it explicitly named.  This also improves code readability - it
  is common good practice to pass options in a consistent way
  independent of their position, so many people may not even notice
  the change in their code.  Another important reason is compatibility
  with cElementTree, which also enforces keyword-only arguments in a
  couple of places.

* XML tag names are validated when creating an Element.  This does not
  apply to HTML tags, where only HTML special characters are
  forbidden.  The distinction is made by the ``SubElement()`` factory,
  which tests if the tree it works on is an HTML tree, and by the
  ``.makeelement()`` methods of parsers, which behave differently for
  the ``XMLParser()`` and the ``HTMLParser()``.

* XPath now raises exceptions specific to the part of the execution that
  failed: ``XPathSyntaxError`` for parser errors and ``XPathEvalError`` for
  errors that occurred during the evaluation.  Note that the distinction only
  works for the ``XPath()`` class.  The other two evaluators only have a
  single evaluation call that includes the parsing step, and will therefore
  only raise an ``XPathEvalError``.  Applications can catch both exceptions
  through the common base class ``XPathError`` (which also exists in earlier
  lxml versions).

* Network access in parsers is now disabled by default, i.e. the
  ``no_network`` option defaults to True.  Due to a somewhat 'interesting'
  implementation in libxml2, this does not affect the first document (i.e. the
  URL that is parsed), but only subsequent documents, such as a DTD when
  parsing with validation.  This means that you will have to check the URL you
  pass, instead of relying on lxml to prevent *any* access to external
  resources.  As this can be helpful in some use cases, lxml does not work
  around it.

* The type annotations in lxml.objectify (the ``pytype`` attribute) now use
  ``NoneType`` for the None value as this is the correct Python type name.
  Previously, lxml 1.x used a lower case ``none``.

* Another change in objectify regards the way it deals with ambiguous types.
  Previously, setting a value like the string ``"3"`` through normal attribute
  access would let it come back as an integer when reading the object
  attribute.  lxml 2.0 prevents this by always setting the ``pytype``
  attribute to the type the user passed in, so ``"3"`` will come back as a
  string, while the number ``3`` will come back as a number.  To remove the
  type annotation on serialisation, you can use the ``deannotate()`` function.

* The C-API function ``findOrBuildNodeNs()`` was replaced by the more generic
  ``findOrBuildNodeNsPrefix()`` that accepts an additional default prefix.


Enhancements
------------

Most of the enhancements of lxml 2.0 were made under the hood.  Most people
won't even notice them, but they make the maintenance of lxml easier and thus
facilitate further enhancements and an improved integration between lxml's
features.

* lxml.objectify now has its own implementation of the `E factory`_.  It uses
  the built-in type lookup mechanism of lxml.objectify, thus removing the need
  for an additional type registry mechanism (as previously available through
  the ``typemap`` parameter).

* XML entities are supported through the ``Entity()`` factory, an Entity
  element class and a parser option ``resolve_entities`` that allows to keep
  entities in the element tree when set to False.  Also, the parser will now
  report undefined entities as errors if it needs to resolve them (which is
  still the default, as in lxml 1.x).

* A major part of the XPath code was rewritten and can now benefit from a
  bigger overlap with the XSLT code.  The main benefits are improved thread
  safety in the XPath evaluators and Python RegExp support in standard XPath.

* The string results of an XPath evaluation have become 'smart' string
  subclasses.  Formerly, there was no easy way to find out where a
  string originated from.  In lxml 2.0, you can call its
  ``getparent()`` method to `find the Element that carries it`_.  This
  works for attributes (``//@attribute``) and for ``text()`` nodes,
  i.e. Element text and tails.  Strings that were constructed in the
  path expression, e.g. by the ``string()`` function or extension
  functions, will return None as their parent.

* Setting a ``QName`` object as value of the ``.text`` property or as
  an attribute value will resolve its prefix in the respective context

* Following ElementTree 1.3, the ``iterfind()`` method supports
  efficient iteration based on XPath-like expressions.

The parsers also received some major enhancements:

* ``iterparse()`` can parse HTML when passing the boolean ``html``
  keyword.

* Parse time XML Schema validation by passing an
  XMLSchema object to the ``schema`` keyword argument of a parser.

* Support for a ``target`` object that implements ElementTree's
  `TreeBuilder interface`_.

* The ``encoding`` keyword allows overriding the document encoding.


.. _`E factory`: objectify.html#tree-generation-with-the-e-factory
.. _`find the Element that carries it`: tutorial.html#using-xpath-to-find-text
.. _`TreeBuilder interface`: http://effbot.org/elementtree/elementtree-treebuilder.htm


Deprecation
-----------

The following functions and methods are now deprecated.  They are
still available in lxml 2.0 and will be removed in lxml 2.1:

* The ``tounicode()`` function was replaced by the call
  ``tostring(encoding='unicode')``.

* CamelCaseNamed module functions and methods were renamed to their
  underscore equivalents to follow `PEP 8`_ in naming.

  - ``etree.clearErrorLog()``, use ``etree.clear_error_log()``

  - ``etree.useGlobalPythonLog()``, use
    ``etree.use_global_python_log()``

  - ``etree.ElementClassLookup.setFallback()``, use
    ``etree.ElementClassLookup.set_fallback()``

  - ``etree.getDefaultParser()``, use ``etree.get_default_parser()``

  - ``etree.setDefaultParser()``, use ``etree.set_default_parser()``

  - ``etree.setElementClassLookup()``, use
    ``etree.set_element_class_lookup()``

  - ``XMLParser.setElementClassLookup()``, use ``.set_element_class_lookup()``

  - ``HTMLParser.setElementClassLookup()``, use ``.set_element_class_lookup()``

    Note that ``parser.setElementClassLookup()`` has not been removed
    yet, although ``parser.set_element_class_lookup()`` should be used
    instead.

  - ``xpath_evaluator.registerNamespace()``, use
    ``xpath_evaluator.register_namespace()``

  - ``xpath_evaluator.registerNamespaces()``, use
    ``xpath_evaluator.register_namespaces()``

  - ``objectify.setPytypeAttributeTag``, use
    ``objectify.set_pytype_attribute_tag``

  - ``objectify.setDefaultParser()``, use
    ``objectify.set_default_parser()``

* The ``.getiterator()`` method on Elements and ElementTrees was
  renamed to ``.iter()`` to follow ElementTree 1.3.

.. _`PEP 8`: http://www.python.org/dev/peps/pep-0008/


New modules
===========

The most visible changes in lxml 2.0 regard the new modules that were added.


lxml.usedoctest
---------------

A very useful module for doctests based on XML or HTML is
``lxml.doctestcompare``.  It provides a relaxed comparison mechanism
for XML and HTML in doctests.  Using it for XML comparisons is as
simple as:

.. sourcecode:: pycon

    >>> import lxml.usedoctest

and for HTML comparisons:

.. sourcecode:: pycon

    >>> import lxml.html.usedoctest


lxml.html
---------

The largest new package that was added to lxml 2.0 is `lxml.html`_.  It
contains various tools and modules for HTML handling.  The major features
include support for cleaning up HTML (removing unwanted content), a readable
HTML diff and various tools for working with links.

.. _`lxml.html`: lxmlhtml.html


lxml.cssselect
--------------

The Cascading Stylesheet Language (CSS_) has a very short and generic path
language for pointing at elements in XML/HTML trees (`CSS selectors`_).  The module
lxml.cssselect_ provides an implementation based on XPath.

.. _lxml.cssselect: cssselect.html
.. _CSS: http://www.w3.org/Style/CSS/
.. _`CSS selectors`: http://www.w3.org/TR/CSS21/selector.html
