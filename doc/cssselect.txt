==============
lxml.cssselect
==============

lxml supports a number of interesting languages for tree traversal and element
selection.  The most important is obviously XPath_, but there is also
ObjectPath_ in the `lxml.objectify`_ module.  The newest child of this family
is `CSS selection`_, which is made available in form of the ``lxml.cssselect``
module.

Although it started its life in lxml, cssselect_ is now an independent project.
It translates CSS selectors to XPath 1.0 expressions that can be used with
lxml's XPath engine.  ``lxml.cssselect`` adds a few convenience shortcuts into
that package.


.. _XPath: xpathxslt.html#xpath
.. _ObjectPath: objectify.html#objectpath
.. _`lxml.objectify`: objectify.html
.. _`CSS selection`: http://www.w3.org/TR/CSS21/selector.html
.. _cssselect: http://packages.python.org/cssselect/

.. contents::
..
   1  The CSSSelector class
   2  CSS Selectors
     2.1  Namespaces
   3  Limitations


The CSSSelector class
=====================

The most important class in the ``lxml.cssselect`` module is ``CSSSelector``.  It
provides the same interface as the XPath_ class, but accepts a CSS selector
expression as input:

.. sourcecode:: pycon

    >>> from lxml.cssselect import CSSSelector
    >>> sel = CSSSelector('div.content')
    >>> sel  #doctest: +ELLIPSIS
    <CSSSelector ... for 'div.content'>
    >>> sel.css
    'div.content'

The selector actually compiles to XPath, and you can see the
expression by inspecting the object:

.. sourcecode:: pycon

    >>> sel.path
    "descendant-or-self::div[@class and contains(concat(' ', normalize-space(@class), ' '), ' content ')]"

To use the selector, simply call it with a document or element
object:

.. sourcecode:: pycon

    >>> from lxml.etree import fromstring
    >>> h = fromstring('''<div id="outer">
    ...   <div id="inner" class="content body">
    ...       text
    ...   </div></div>''')
    >>> [e.get('id') for e in sel(h)]
    ['inner']

Using ``CSSSelector`` is equivalent to translating with ``cssselect``
and using the ``XPath`` class:

.. sourcecode:: pycon

    >>> from cssselect import GenericTranslator
    >>> from lxml.etree import XPath
    >>> sel = XPath(GenericTranslator().css_to_xpath('div.content'))

``CSSSelector`` takes a ``translator`` parameter to let you choose which
translator to use. It can be ``'xml'`` (the default), ``'xhtml'``, ``'html'``
or a `Translator object`_.

.. _Translator object: http://packages.python.org/cssselect/#cssselect.GenericTranslator


The cssselect method
====================

lxml ``Element`` objects have a ``cssselect`` convenience method.

.. sourcecode:: pycon

    >>> h.cssselect('div.content') == sel(h)
    True

Note however that pre-compiling the expression with the ``CSSSelector`` or
``XPath`` class can provide a substantial speedup.

The method also accepts a ``translator`` parameter. On ``HtmlElement``
objects, the default is changed to ``'html'``.


Supported Selectors
===================

Most `Level 3`_ selectors are supported. The details are in the
`cssselect documentation`_.

.. _Level 3: http://www.w3.org/TR/2011/REC-css3-selectors-20110929/
.. _cssselect documentation: http://packages.python.org/cssselect/#supported-selectors


Namespaces
==========

In CSS you can use ``namespace-prefix|element``, similar to
``namespace-prefix:element`` in an XPath expression.  In fact, it maps
one-to-one, and the same rules are used to map namespace prefixes to
namespace URIs: the ``CSSSelector`` class accepts a dictionary as its
``namespaces`` argument.
