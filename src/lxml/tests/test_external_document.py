# -*- coding: utf-8 -*-
"""
Test cases related to direct loading of external libxml2 documents
"""

from __future__ import absolute_import

import sys
import unittest

from .common_imports import HelperTestCase, etree

DOC_NAME = b'libxml2:xmlDoc'
DESTRUCTOR_NAME = b'destructor:xmlFreeDoc'


class ExternalDocumentTestCase(HelperTestCase):
    def setUp(self):
        try:
            import ctypes
            from ctypes import pythonapi
            from ctypes.util import find_library
        except ImportError:
            raise unittest.SkipTest("ctypes support missing")

        def wrap(func, restype, *argtypes):
            func.restype = restype
            func.argtypes = list(argtypes)
            return func

        self.get_capsule_name = wrap(pythonapi.PyCapsule_GetName,
                                     ctypes.c_char_p, ctypes.py_object)
        self.capsule_is_valid = wrap(pythonapi.PyCapsule_IsValid, ctypes.c_int,
                                     ctypes.py_object, ctypes.c_char_p)
        self.new_capsule = wrap(pythonapi.PyCapsule_New, ctypes.py_object,
                                ctypes.c_void_p, ctypes.c_char_p,
                                ctypes.c_void_p)
        self.set_capsule_name = wrap(pythonapi.PyCapsule_SetName, ctypes.c_int,
                                     ctypes.py_object, ctypes.c_char_p)
        self.set_capsule_context = wrap(pythonapi.PyCapsule_SetContext,
                                        ctypes.c_int, ctypes.py_object,
                                        ctypes.c_char_p)
        self.get_capsule_context = wrap(pythonapi.PyCapsule_GetContext,
                                        ctypes.c_char_p, ctypes.py_object)
        self.get_capsule_pointer = wrap(pythonapi.PyCapsule_GetPointer,
                                        ctypes.c_void_p, ctypes.py_object,
                                        ctypes.c_char_p)
        self.set_capsule_pointer = wrap(pythonapi.PyCapsule_SetPointer,
                                        ctypes.c_int, ctypes.py_object,
                                        ctypes.c_void_p)
        self.set_capsule_destructor = wrap(pythonapi.PyCapsule_SetDestructor,
                                           ctypes.c_int, ctypes.py_object,
                                           ctypes.c_void_p)
        self.PyCapsule_Destructor = ctypes.CFUNCTYPE(None, ctypes.py_object)
        libxml2 = ctypes.CDLL(find_library('xml2'))
        self.create_doc = wrap(libxml2.xmlReadMemory, ctypes.c_void_p,
                               ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
                               ctypes.c_char_p, ctypes.c_int)
        self.free_doc = wrap(libxml2.xmlFreeDoc, None, ctypes.c_void_p)

    def as_capsule(self, text, capsule_name=DOC_NAME):
        if not isinstance(text, bytes):
            text = text.encode('utf-8')
        doc = self.create_doc(text, len(text), b'base.xml', b'utf-8', 0)
        ans = self.new_capsule(doc, capsule_name, None)
        self.set_capsule_context(ans, DESTRUCTOR_NAME)
        return ans

    def test_external_document_adoption(self):
        xml = '<r a="1">t</r>'
        self.assertRaises(TypeError, etree.adopt_external_document, None)
        capsule = self.as_capsule(xml)
        self.assertTrue(self.capsule_is_valid(capsule, DOC_NAME))
        self.assertEqual(DOC_NAME, self.get_capsule_name(capsule))
        # Create an lxml tree from the capsule (this is a move not a copy)
        root = etree.adopt_external_document(capsule).getroot()
        self.assertIsNone(self.get_capsule_name(capsule))
        self.assertEqual(root.text, 't')
        root.text = 'new text'
        # Now reset the capsule so we can copy it
        self.assertEqual(0, self.set_capsule_name(capsule, DOC_NAME))
        self.assertEqual(0, self.set_capsule_context(capsule, b'invalid'))
        # Create an lxml tree from the capsule (this is a copy not a move)
        root2 = etree.adopt_external_document(capsule).getroot()
        self.assertEqual(self.get_capsule_context(capsule), b'invalid')
        # Check that the modification to the tree using the transferred
        # document was successful
        self.assertEqual(root.text, root2.text)
        # Check that further modifications do not show up in the copy (they are
        # disjoint)
        root.text = 'other text'
        self.assertNotEqual(root.text, root2.text)
        # delete root and ensure root2 survives
        del root
        self.assertEqual(root2.text, 'new text')


def test_suite():
    suite = unittest.TestSuite()
    if sys.platform != 'win32':
        suite.addTests([unittest.makeSuite(ExternalDocumentTestCase)])
    return suite


if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
