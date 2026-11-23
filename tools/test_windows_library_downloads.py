"""Tests for the Windows static-library download boundary.

Run with: python -m unittest discover -s tools -p test_windows_library_downloads.py
"""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlparse
import zipfile

import buildlibxml


class WindowsLibrariesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.vs = self.root / 'Visual Studio'
        (self.vs / 'VC/Tools/MSVC/14.52.37025').mkdir(parents=True)
        (self.vs / 'VC/Auxiliary/Build').mkdir(parents=True)
        (self.vs / 'VC/Auxiliary/Build/vcvarsall.bat').touch()
        self.libs = self.root / 'libs'
        self.libs.mkdir()
        self.versions = {'libxml2': '2.11.9', 'libxslt': '1.1.45',
                         'zlib': '1.4', 'iconv': '1.19'}
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, {'ProgramFiles(x86)': str(self.root),
                               'VSCMD_ARG_TGT_ARCH': 'arm64',
                               **{('LIBICONV_VERSION' if lib == 'iconv' else
                                   lib.upper() + '_VERSION'): version
                                  for lib, version in self.versions.items()}}).start()
        patch('subprocess.check_output', side_effect=[
            str(self.vs), 'VCToolsVersion=14.52.37025\nPATH=test-path',
            '195237025\n']).start()

    def archive(self, name):
        with zipfile.ZipFile(self.libs / name, 'w') as archive:
            archive.writestr(name[:-4] + '/', '')
            archive.writestr(name[:-4] + '/lib/test.lib', b'library')

    def test_uses_local_archives_for_the_exact_compiler(self):
        for lib, version in self.versions.items():
            self.archive(f'{lib}-{version}.win-arm64.msvc-195237025.zip')
        patch('buildlibxml.urlopen', side_effect=AssertionError(
            'Matching compiler-qualified local archives must be reused')).start()
        paths = buildlibxml.download_and_extract_windows_binaries(str(self.libs))
        self.assertEqual(set(paths), set(self.versions))
        for path in paths.values():
            self.assertTrue(Path(path, 'lib/test.lib').is_file())

    def test_rejects_unqualified_and_different_compiler_archives(self):
        assets = []
        for lib, version in self.versions.items():
            for suffix in ('', '.msvc-195136231'):
                name = f'{lib}-{version}.win-arm64{suffix}.zip'
                self.archive(name)
                assets.append({'name': name, 'size': 1, 'digest': 'sha256:unused'})
        response = io.BytesIO(json.dumps([
            {'tag_name': '2026.11.07', 'assets': assets}]).encode())
        response.headers = {}
        patch('buildlibxml.urlopen', return_value=response).start()
        patch('buildlibxml.urlretrieve', side_effect=AssertionError(
            'Incompatible archives must never be downloaded')).start()
        with self.assertRaisesRegex(RuntimeError, '195237025'):
            buildlibxml.download_and_extract_windows_binaries(str(self.libs))

    def test_downloads_only_matching_compiler_archives(self):
        assets = [
            {'name': f'{lib}-{version}.win-arm64.msvc-{compiler}.zip',
             'size': 1, 'digest': 'sha256:unused'}
            for lib, version in self.versions.items()
            for compiler in ('195136231', '195237025')
        ]
        response = io.BytesIO(json.dumps([
            {'tag_name': '2026.11.14', 'assets': assets}]).encode())
        response.headers = {}
        patch('buildlibxml.urlopen', return_value=response).start()
        downloads = []

        def retrieve(url, destination):
            name = unquote(Path(urlparse(url).path).name)
            self.assertEqual(Path(destination).name, name)
            downloads.append(name)
            self.archive(name)

        patch('buildlibxml.urlretrieve', side_effect=retrieve).start()
        paths = buildlibxml.download_and_extract_windows_binaries(str(self.libs))
        self.assertEqual(len(paths), 4)
        self.assertEqual(set(downloads), {
            'libxml2-2.11.9.win-arm64.msvc-195237025.zip',
            'libxslt-1.1.45.win-arm64.msvc-195237025.zip',
            'zlib-1.4.win-arm64.msvc-195237025.zip',
            'iconv-1.19.win-arm64.msvc-195237025.zip',
        })

    def test_missing_toolset_fails_before_downloading(self):
        (self.vs / 'VC/Tools/MSVC/14.52.37025').rmdir()
        patch('buildlibxml.urlopen', side_effect=AssertionError(
            'Missing toolset must be diagnosed before downloading')).start()
        with self.assertRaisesRegex(RuntimeError, 'MSVC 14.52'):
            buildlibxml.download_and_extract_windows_binaries(str(self.libs))


if __name__ == '__main__':
    unittest.main()
