# -*- coding: utf-8 -*-
"""
Test cases related to direct loading of external libxml2 documents
"""

import unittest
import sys

from common_imports import etree, HelperTestCase


@unittest.skipIf(sys.version_info[:2] < (2, 7),
                 'Not supported for python < 2.7')
class ExternalDocumentTestCase(HelperTestCase):
    def test_external_document_type_checking(self):
        self.assertRaises(TypeError, etree.adopt_external_document, None)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ExternalDocumentTestCase)])
    return suite


if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
