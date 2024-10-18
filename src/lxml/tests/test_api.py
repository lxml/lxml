"""
Test module level API for etree.
"""


import unittest
import sys
from io import BytesIO

from .common_imports import etree
from .common_imports import HelperTestCase
from lxml import builder, sax


class APITestCase(HelperTestCase):
    """Test cases of the etree module API.
    """

    def test_class_hierarchy(self):

        element = etree.Element("test")
        # The Element class constructs an _Element instance
        self.assertIs(type(element), etree._Element)
        # _Element is a subclass implementation of Element
        self.assertTrue(issubclass(etree._Element, etree.Element))
        # Therefore, element is an instance of Element
        self.assertIsInstance(element, etree.Element)

        comment = etree.Comment("text")
        self.assertIs(type(comment), etree._Comment)
        self.assertIsInstance(comment, etree._Element)
        self.assertIsInstance(comment, etree.Element)

        pi = etree.ProcessingInstruction("target", "text")
        self.assertIs(type(pi), etree._ProcessingInstruction)
        self.assertIsInstance(pi, etree._Element)
        self.assertIsInstance(pi, etree.Element)

        entity = etree.Entity("text")
        self.assertIs(type(entity), etree._Entity)
        self.assertIsInstance(entity, etree._Element)
        self.assertIsInstance(entity, etree.Element)

        sub_element = etree.SubElement(element, "child")
        self.assertIs(type(sub_element), etree._Element)
        self.assertIsInstance(sub_element, etree.Element)

        tree = etree.ElementTree(element)
        self.assertIs(type(tree), etree._ElementTree)
        self.assertIsInstance(tree, etree.ElementTree)
        self.assertNotIsInstance(tree, etree._Element)

        # XML is a factory function and not a class.
        xml = etree.XML("<root><test/></root>")
        self.assertIs(type(xml), etree._Element)
        self.assertIsInstance(xml, etree._Element)
        self.assertIsInstance(xml, etree.Element)

        self.assertNotIsInstance(element, etree.ElementBase)
        self.assertIs(type(element), etree._Element)
        self.assertTrue(issubclass(etree.ElementBase, etree._Element))

        self.assertTrue(callable(etree.Element))
        self.assertTrue(callable(etree.ElementTree))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(APITestCase)])
    return suite


if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
