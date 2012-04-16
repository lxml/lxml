"""CSS Selectors based on XPath.

This module supports selecting XML/HTML tags based on CSS selectors.
See the `CSSSelector` class for details.

This is a thin wrapper around cssselect.
"""

import sys
from lxml import etree

## Work-around the lack of absolute import in Python 2.4
#from __future__ import absolute_import
#from cssselect import Translator, SelectorSyntaxError, ExpressionError
try:
    __import__('cssselect')
except ImportError:
    raise ImportError('cssselect seems not to be installed. '
                      'See http://packages.python.org/cssselect/')

SelectorSyntaxError = sys.modules['cssselect.parser'].SelectorSyntaxError
ExpressionError = sys.modules['cssselect.xpath'].ExpressionError
Translator = sys.modules['cssselect'].Translator
Element = sys.modules['cssselect.parser'].Element
xpath_literal = sys.modules['cssselect.xpath'].xpath_literal


__all__ = ['SelectorSyntaxError', 'ExpressionError', 'CSSSelector']


class LxmlTranslator(Translator):
    """
    A custom CSS selector to XPath translator with lxml-specific extensions.
    """
    def xpath_contains_function(self, xpath, function):
        # text content, minus tags, must contain expr
        text = function.arguments
        if isinstance(text, Element):
            text = text._format_element()
        xpath.add_condition(
            'contains(__lxml_internal_css:lower-case(string(.)), %s)'
            % xpath_literal(text.lower()))
        return xpath


def _make_lower_case(context, s):
    return s.lower()

ns = etree.FunctionNamespace('http://codespeak.net/lxml/css/')
ns.prefix = '__lxml_internal_css'
ns['lower-case'] = _make_lower_case


class CSSSelector(etree.XPath):
    """A CSS selector.

    Usage::

        >>> from lxml import etree, cssselect
        >>> select = cssselect.CSSSelector("a tag > child")

        >>> root = etree.XML("<a><b><c/><tag><child>TEXT</child></tag></b></a>")
        >>> [ el.tag for el in select(root) ]
        ['child']

    To use CSS namespaces, you need to pass a prefix-to-namespace
    mapping as ``namespaces`` keyword argument::

        >>> rdfns = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
        >>> select_ns = cssselect.CSSSelector('root > rdf|Description',
        ...                                   namespaces={'rdf': rdfns})

        >>> rdf = etree.XML((
        ...     '<root xmlns:rdf="%s">'
        ...       '<rdf:Description>blah</rdf:Description>'
        ...     '</root>') % rdfns)
        >>> [(el.tag, el.text) for el in select_ns(rdf)]
        [('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description', 'blah')]
    """
    def __init__(self, css, namespaces=None):
        path = LxmlTranslator().css_to_xpath(css)
        etree.XPath.__init__(self, path, namespaces=namespaces)
        self.css = css

    def __repr__(self):
        return '<%s %s for %r>' % (
            self.__class__.__name__,
            hex(abs(id(self)))[2:],
            self.css)
