# -*- coding: utf-8 -*-

"""
Web IO test cases that need Python 2.5+ (wsgiref)
"""

from __future__ import with_statement

import unittest
import textwrap
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

    def _parse_from_http(self, data, code=200, headers=None, parser=None):
        handler = HTTPRequestCollector(data, code, headers)
        with webserver(handler) as host_url:
            tree = self.etree.parse(host_url + 'TEST', parser=parser)
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

    def test_parser_input_mix(self):
        data = _bytes('<root><a/></root>')
        handler = HTTPRequestCollector(data)

        with webserver(handler) as host_url:
            tree = self.etree.parse(host_url)
            root = tree.getroot()
            self.assertEqual('a', root[0].tag)

            root = self.etree.fromstring(data)
            self.assertEqual('a', root[0].tag)

            tree = self.etree.parse(host_url)
            root = tree.getroot()
            self.assertEqual('a', root[0].tag)

            root = self.etree.fromstring(data)
            self.assertEqual('a', root[0].tag)

        root = self.etree.fromstring(data)
        self.assertEqual('a', root[0].tag)

    def test_network_dtd(self):
        data = [_bytes(textwrap.dedent(s)) for s in [
            # XML file
            '''\
            <?xml version="1.0"?>
            <!DOCTYPE root SYSTEM "./file.dtd">
            <root>&myentity;</root>
            ''',
            # DTD
            '<!ENTITY myentity "DEFINED">',
        ]]

        responses = []
        def handler(environ, start_response):
            start_response('200 OK', [])
            return [responses.pop()]

        with webserver(handler) as host_url:
            # DTD network loading enabled
            responses = data[::-1]
            tree = self.etree.parse(
                host_url + 'dir/test.xml',
                parser=self.etree.XMLParser(
                    load_dtd=True, no_network=False))
            self.assertFalse(responses)  # all read
            root = tree.getroot()
            self.assertEqual('DEFINED', root.text)

            # DTD network loading disabled
            responses = data[::-1]
            try:
                self.etree.parse(
                    host_url + 'dir/test.xml',
                    parser=self.etree.XMLParser(
                        load_dtd=True, no_network=True))
            except self.etree.XMLSyntaxError:
                self.assertTrue("myentity" in str(sys.exc_info()[1]))
            else:
                self.assertTrue(False)
            self.assertEqual(1, len(responses))  # DTD not read


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(HttpIOTestCase)])
    return suite


if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
