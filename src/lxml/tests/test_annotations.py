"""
Test typing annotations.
"""

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


def container_function_with_subscripted_private_element_tree():
    def function_with_subscripted_private_element_tree(
        _element_tree: etree._ElementTree[etree.Element],
    ):
        pass


class TypingTestCase(HelperTestCase):
    """Typing test cases
    """

    def test_subscripted_generic(self):
        # Test that all generic types can be subscripted.
        # Based on PEP 560.
        container_function_with_subscripted_types()

        # Subscripting etree.Element should fail with the error:
        # TypeError: 'type' Element is not subscriptable
        # Make sure that the test works and it is indeed failing.
        with self.assertRaises(TypeError):
            container_function_with_subscripted_private_element_tree()


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(TypingTestCase)])
    return suite


if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
