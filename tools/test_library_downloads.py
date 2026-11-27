"""Tests for downloading the library sources of static builds.

Run with: python -m unittest discover -s tools -p test_library_downloads.py
"""
import hashlib
import io
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import patch
from urllib.response import addinfourl

import buildlibxml


class SourceLibrariesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.libs = Path(self.tmp.name)
        self.addCleanup(patch.stopall)
        patch.dict(buildlibxml.ARCHIVE_HASHES, clear=True).start()

    def add_checksum(self, filename, content):
        patch.dict(buildlibxml.ARCHIVE_HASHES,
                   {filename: hashlib.sha256(content).hexdigest()}).start()

    def serve_downloads(self):
        downloads = []

        def list_directories(request):
            listing = b'<a href="1.1/">1.1/</a> <a href="2.14/">2.14/</a> <a href="2.15/">2.15/</a>'
            return addinfourl(io.BytesIO(listing), Message(), request.full_url)

        def retrieve(url, destination):
            downloads.append(url)
            Path(destination).write_bytes(b'downloaded archive')

        patch('buildlibxml.urlopen', side_effect=list_directories).start()
        patch('buildlibxml.urlretrieve', side_effect=retrieve).start()
        return downloads

    def test_uses_local_archives_of_requested_versions_without_network_access(self):
        libxml2 = self.libs / 'libxml2-2.15.4.tar.xz'
        libxml2.write_bytes(b'libxml2 archive')
        libxslt = self.libs / 'libxslt-1.1.45.tar.xz'
        libxslt.write_bytes(b'libxslt archive')
        self.add_checksum(libxslt.name, b'libxslt archive')
        for function in ('urlopen', 'urlretrieve'):
            patch('buildlibxml.' + function, side_effect=AssertionError(
                'Local archives of the requested versions must be reused')).start()
        self.assertEqual(buildlibxml.download_libxml2(str(self.libs), '2.15.4'), libxml2)
        self.assertEqual(buildlibxml.download_libxslt(str(self.libs), '1.1.45'), libxslt)

    def test_downloads_missing_archives_from_their_version_directories(self):
        downloads = self.serve_downloads()
        self.assertEqual(buildlibxml.download_libxml2(str(self.libs), '2.14.6'),
                         self.libs / 'libxml2-2.14.6.tar.xz')
        self.assertEqual(buildlibxml.download_libxslt(str(self.libs), '1.1.45'),
                         self.libs / 'libxslt-1.1.45.tar.xz')
        self.assertEqual(downloads, [
            'https://download.gnome.org/sources/libxml2/2.14/libxml2-2.14.6.tar.xz',
            'https://download.gnome.org/sources/libxslt/1.1/libxslt-1.1.45.tar.xz',
        ])

    @unittest.skipUnless(hasattr(hashlib, 'file_digest'),
                         'archive checksums are only verified in Python 3.11+')
    def test_downloads_archive_again_if_its_checksum_does_not_match(self):
        archive = self.libs / 'libxml2-2.14.6.tar.xz'
        archive.write_bytes(b'truncated archive')
        self.add_checksum(archive.name, b'downloaded archive')
        downloads = self.serve_downloads()
        self.assertEqual(buildlibxml.download_libxml2(str(self.libs), '2.14.6'), archive)
        self.assertEqual(downloads, [
            'https://download.gnome.org/sources/libxml2/2.14/libxml2-2.14.6.tar.xz',
        ])
        self.assertEqual(archive.read_bytes(), b'downloaded archive')


if __name__ == '__main__':
    unittest.main()
