# -*- coding: utf-8 -*-

"""
Tests for thread usage in lxml.etree.
"""

import unittest, threading

from common_imports import etree, HelperTestCase

class ThreadingTestCase(HelperTestCase):
    """Threading tests"""
    etree = etree

    def test_subtree_copy(self):
        tostring = self.etree.tostring
        XML = self.etree.XML
        xml = "<root><threadtag/></root>"
        main_root = XML("<root/>")

        def run_thread():
            thread_root = XML(xml)
            main_root.append(thread_root[0])
            del thread_root

        thread = threading.Thread(target=run_thread)
        thread.start()
        thread.join()

        self.assertEquals(xml, tostring(main_root))

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ThreadingTestCase)])
    return suite

if __name__ == '__main__':
    print 'to test use test.py %s' % __file__
