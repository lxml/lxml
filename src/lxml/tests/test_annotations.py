"""
Test typing annotations.
"""


import unittest
import sys
from io import BytesIO

from .common_imports import etree
from .common_imports import HelperTestCase
from lxml import builder, sax


class TypingTestCase(HelperTestCase):
    """Typing test cases
    """

    def test_subscripted_generic(self):
        # Test that all generic types can be subscripted.
        # Based on PEP 560 implemented in python 3.7.

        if sys.version_info[:2] >= (3, 7):
            etree._ElementTree[int]
            xml_parser: etree.XMLParser[int]
            html_parser: etree.HTMLParser[int]
            element_maker: builder.ElementMaker[int]
            element_tree_content_handler: sax.ElementTreeContentHandler[int]
            id_dict: etree._IDDict[int]
            element_unicode_result: etree._ElementUnicodeResult[int]

        # Subscripting etree._Element should fail with the error:
        # TypeError: 'type' object is not subscriptable
        # Make sure that the test works and it is indeed failing.
        self.assertRaises(TypeError, lambda: etree._Element[int])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(TypingTestCase)])
    return suite


if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
