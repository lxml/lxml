# -*- coding: utf-8 -*-

"""
Web IO test cases that need Python 2.5+ (wsgiref)
"""

import unittest
import os
import sys
import gzip

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir)  # needed for Py3

from .common_imports import (
    etree, HelperTestCase, BytesIO, _bytes)
from .dummy_http_server import webserver, HTTPRequestCollector


class HttpIOTestCase(HelperTestCase):
    etree = etree

    def _parse_from_http(self, data, code=200, headers=None):
        handler = HTTPRequestCollector(data, code, headers)
        with webserver(handler) as host_url:
            tree = self.etree.parse(host_url + 'TEST')
        self.assertEqual([('/TEST', [])], handler.requests)
        return tree

    def test_http_client(self):
        tree = self._parse_from_http(_bytes('<root><a/></root>'))
        self.assertEqual('root', tree.getroot().tag)
        self.assertEqual('a', tree.getroot()[0].tag)

    def test_http_client_404(self):
        try:
            self._parse_from_http(_bytes('<root/>'), code=404)
        except IOError:
            self.assertTrue(True)
        else:
            self.assertTrue(False, "expected IOError")

    def test_http_client_gzip(self):
        f = BytesIO()
        gz = gzip.GzipFile(fileobj=f, mode='w', filename='test.xml')
        gz.write(_bytes('<root><a/></root>'))
        gz.close()
        data = f.getvalue()
        del f, gz

        headers = [('Content-Encoding', 'gzip')]
        tree = self._parse_from_http(data, headers=headers)
        self.assertEqual('root', tree.getroot().tag)
        self.assertEqual('a', tree.getroot()[0].tag)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(HttpIOTestCase)])
    return suite


if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
