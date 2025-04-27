"""
Test typing annotations.
"""

from __future__ import annotations

import inspect
import sys
import unittest

from .common_imports import etree
from .common_imports import HelperTestCase
from lxml import builder, sax


def container_function_with_subscripted_types():
    # The function definition is in a container so that any errors would trigger
    # when calling the function instead of during import.
    def function_with_subscripted_types(
        element_tree: etree.ElementTree[etree.Element],
        xml_parser: etree.XMLParser[etree.Element],
        html_parser: etree.HTMLParser[etree.Element],
        element_maker: builder.ElementMaker[etree.Element],
        element_tree_content_handler: sax.ElementTreeContentHandler[etree.Element],
    ):
        pass

    return function_with_subscripted_types


def container_function_with_subscripted_private_element_tree():
    def function_with_subscripted_private_element_tree(
        _element_tree: etree._ElementTree[etree.Element],
    ):
        pass

    return function_with_subscripted_private_element_tree


class TypingTestCase(HelperTestCase):
    """Typing test cases
    """

    def test_subscripted_generic(self):
        # Test that all generic types can be subscripted.
        # Based on PEP 560.
        func = container_function_with_subscripted_types()
        if sys.version_info >= (3, 10):
            inspect.get_annotations(func, eval_str=True)

        # Subscripting etree.Element should fail with the error:
        # TypeError: 'type' _ElementTree is not subscriptable
        # Make sure that the test works and it is indeed failing.
        if sys.version_info >= (3, 10):
            with self.assertRaises(TypeError):
                func = container_function_with_subscripted_private_element_tree()
                inspect.get_annotations(func, eval_str=True)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(TypingTestCase)])
    return suite


if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
