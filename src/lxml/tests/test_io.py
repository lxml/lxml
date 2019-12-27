# -*- coding: utf-8 -*-

"""
IO test cases that apply to both etree and ElementTree
"""

from __future__ import absolute_import

import unittest
import tempfile, gzip, os, os.path, gc, shutil

from .common_imports import (
    etree, ElementTree, _str, _bytes,
    SillyFileLike, LargeFileLike, HelperTestCase,
    read_file, write_to_file, BytesIO, tmpfile
)


class _IOTestCaseBase(HelperTestCase):
    """(c)ElementTree compatibility for IO functions/methods
    """
    etree = None
    
    def setUp(self):
        """Setting up a minimal tree
        """
        self.root = self.etree.Element('a')
        self.root_str = self.etree.tostring(self.root)
        self.tree = self.etree.ElementTree(self.root)
        self._temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        gc.collect()
        shutil.rmtree(self._temp_dir)

    def getTestFilePath(self, name):
        return os.path.join(self._temp_dir, name)

    def buildNodes(self, element, children, depth):
        Element = self.etree.Element

        if depth == 0:
            return
        for i in range(children):
            new_element = Element('element_%s_%s' % (depth, i))
            self.buildNodes(new_element, children, depth - 1)
            element.append(new_element)

    def test_tree_io(self):
        Element = self.etree.Element
        ElementTree = self.etree.ElementTree

        element = Element('top')
        element.text = _str("qwrtioüöä\uAABB")
        tree = ElementTree(element)
        self.buildNodes(element, 10, 3)
        with open(self.getTestFilePath('testdump.xml'), 'wb') as f:
            tree.write(f, encoding='UTF-8')
        with open(self.getTestFilePath('testdump.xml'), 'rb') as f:
            tree = ElementTree(file=f)
        with open(self.getTestFilePath('testdump2.xml'), 'wb') as f:
            tree.write(f, encoding='UTF-8')
        with open(self.getTestFilePath('testdump.xml'), 'rb') as f:
            data1 = f.read()
        with open(self.getTestFilePath('testdump2.xml'), 'rb') as f:
            data2 = f.read()
        self.assertEqual(data1, data2)

    def test_tree_io_latin1(self):
        Element = self.etree.Element
        ElementTree = self.etree.ElementTree

        element = Element('top')
        element.text = _str("qwrtioüöäßÃ¡")
        tree = ElementTree(element)
        self.buildNodes(element, 10, 3)
        with open(self.getTestFilePath('testdump.xml'), 'wb') as f:
            tree.write(f, encoding='iso-8859-1')
        with open(self.getTestFilePath('testdump.xml'), 'rb') as f:
            tree = ElementTree(file=f)
        with open(self.getTestFilePath('testdump2.xml'), 'wb') as f:
            tree.write(f, encoding='iso-8859-1')
        with open(self.getTestFilePath('testdump.xml'), 'rb') as f:
            data1 = f.read()
        with open(self.getTestFilePath('testdump2.xml'), 'rb') as f:
            data2 = f.read()
        self.assertEqual(data1, data2)

    def test_write_filename(self):
        # (c)ElementTree  supports filename strings as write argument
        with tmpfile(prefix="p", suffix=".xml") as filename:
            self.tree.write(filename)
            self.assertEqual(read_file(filename, 'rb').replace(b'\n', b''),
                             self.root_str)

    def test_write_filename_special_percent(self):
        # '%20' is a URL escaped space character.
        before_test = os.listdir(tempfile.gettempdir())

        def difference(filenames):
            return sorted(
                fn for fn in set(filenames).difference(before_test)
                if fn.startswith('lxmltmp-')
            )

        with tmpfile(prefix="lxmltmp-p%20p", suffix=".xml") as filename:
            try:
                before_write = os.listdir(tempfile.gettempdir())
                self.tree.write(filename)
                after_write = os.listdir(tempfile.gettempdir())
                self.assertEqual(read_file(filename, 'rb').replace(b'\n', b''),
                                 self.root_str)
            except (AssertionError, IOError, OSError):
                print("Before write: %s, after write: %s" % (
                    difference(before_write), difference(after_write))
                )
                raise

    def test_write_filename_special_plus(self):
        # '+' is used as an escaped space character in URLs.
        with tmpfile(prefix="p+", suffix=".xml") as filename:
            self.tree.write(filename)
            self.assertEqual(read_file(filename, 'rb').replace(b'\n', b''),
                             self.root_str)

    def test_write_invalid_filename(self):
        filename = os.path.join(
            os.path.join('hopefullynonexistingpathname'),
            'invalid_file.xml')
        try:
            self.tree.write(filename)
        except IOError:
            pass
        else:
            self.assertTrue(
                False, "writing to an invalid file path should fail")

    def test_module_parse_gzipobject(self):
        # (c)ElementTree supports gzip instance as parse argument
        with tmpfile(suffix=".xml.gz") as filename:
            with gzip.open(filename, 'wb') as f:
                f.write(self.root_str)
            with gzip.open(filename, 'rb') as f_gz:
                tree = self.etree.parse(f_gz)
            self.assertEqual(self.etree.tostring(tree.getroot()), self.root_str)

    def test_class_parse_filename(self):
        # (c)ElementTree class ElementTree has a 'parse' method that returns
        # the root of the tree

        # parse from filename
        with tmpfile(suffix=".xml") as filename:
            write_to_file(filename, self.root_str, 'wb')
            tree = self.etree.ElementTree()
            root = tree.parse(filename)
            self.assertEqual(self.etree.tostring(root), self.root_str)

    def test_class_parse_filename_remove_previous(self):
        with tmpfile(suffix=".xml") as filename:
            write_to_file(filename, self.root_str, 'wb')
            tree = self.etree.ElementTree()
            root = tree.parse(filename)
            # and now do it again; previous content should still be there
            root2 = tree.parse(filename)
            self.assertEqual('a', root.tag)
            self.assertEqual('a', root2.tag)
            # now remove all references to root2, and parse again
            del root2
            root3 = tree.parse(filename)
            self.assertEqual('a', root.tag)
            self.assertEqual('a', root3.tag)
            # root2's memory should've been freed here
            # XXX how to check?

    def test_class_parse_fileobject(self):
        # (c)ElementTree class ElementTree has a 'parse' method that returns
        # the root of the tree

        # parse from file object
        handle, filename = tempfile.mkstemp(suffix=".xml")
        try:
            os.write(handle, self.root_str)
            with open(filename, 'rb') as f:
                tree = self.etree.ElementTree()
                root = tree.parse(f)
            self.assertEqual(self.etree.tostring(root), self.root_str)
        finally:
            os.close(handle)
            os.remove(filename)

    def test_class_parse_unamed_fileobject(self):
        # (c)ElementTree class ElementTree has a 'parse' method that returns
        # the root of the tree

        # parse from unnamed file object
        f = SillyFileLike()
        root = self.etree.ElementTree().parse(f)
        self.assertTrue(root.tag.endswith('foo'))

    def test_module_parse_large_fileobject(self):
        # parse from unnamed file object
        f = LargeFileLike()
        tree = self.etree.parse(f)
        root = tree.getroot()
        self.assertTrue(root.tag.endswith('root'))

    def test_module_parse_fileobject_error(self):
        class LocalError(Exception):
            pass
        class TestFile:
            def read(*args):
                raise LocalError
        f = TestFile()
        self.assertRaises(LocalError, self.etree.parse, f)

    def test_module_parse_fileobject_late_error(self):
        class LocalError(Exception):
            pass
        class TestFile:
            data = '<root>test</'
            try:
                next_char = iter(data).next
            except AttributeError:
                # Python 3
                next_char = iter(data).__next__
            counter = 0
            def read(self, amount=None):
                if amount is None:
                    while True:
                        self.read(1)
                else:
                    try:
                        self.counter += 1
                        return _bytes(self.next_char())
                    except StopIteration:
                        raise LocalError
        f = TestFile()
        self.assertRaises(LocalError, self.etree.parse, f)
        self.assertEqual(f.counter, len(f.data)+1)

    def test_module_parse_fileobject_type_error(self):
        class TestFile:
            def read(*args):
                return 1
        f = TestFile()

        try:
            expect_exc = (TypeError, self.etree.ParseError)
        except AttributeError:
            expect_exc = TypeError
        self.assertRaises(expect_exc, self.etree.parse, f)

    def test_etree_parse_io_error(self):
        # this is a directory name that contains characters beyond latin-1
        dirnameEN = _str('Directory')
        dirnameRU = _str('ÐšÐ°Ñ‚Ð°Ð»Ð¾Ð³')
        filename = _str('nosuchfile.xml')
        dn = tempfile.mkdtemp(prefix=dirnameEN)
        try:
            self.assertRaises(IOError, self.etree.parse, os.path.join(dn, filename))
        finally:
            os.rmdir(dn)
        dn = tempfile.mkdtemp(prefix=dirnameRU)
        try:
            self.assertRaises(IOError, self.etree.parse, os.path.join(dn, filename))
        finally:
            os.rmdir(dn)

    def test_parse_utf8_bom(self):
        utext = _str('Søk på nettet')
        uxml = '<?xml version="1.0" encoding="UTF-8"?><p>%s</p>' % utext
        bom = _bytes('\\xEF\\xBB\\xBF').decode(
            "unicode_escape").encode("latin1")
        self.assertEqual(3, len(bom))
        f = tempfile.NamedTemporaryFile(delete=False)
        try:
            try:
                f.write(bom)
                f.write(uxml.encode("utf-8"))
            finally:
                f.close()
            tree = self.etree.parse(f.name)
        finally:
            os.unlink(f.name)
        self.assertEqual(utext, tree.getroot().text)

    def test_iterparse_utf8_bom(self):
        utext = _str('Søk på nettet')
        uxml = '<?xml version="1.0" encoding="UTF-8"?><p>%s</p>' % utext
        bom = _bytes('\\xEF\\xBB\\xBF').decode(
            "unicode_escape").encode("latin1")
        self.assertEqual(3, len(bom))
        f = tempfile.NamedTemporaryFile(delete=False)
        try:
            try:
                f.write(bom)
                f.write(uxml.encode("utf-8"))
            finally:
                f.close()
            elements = [el for _, el in self.etree.iterparse(f.name)]
            self.assertEqual(1, len(elements))
            root = elements[0]
        finally:
            os.unlink(f.name)
        self.assertEqual(utext, root.text)

    def test_iterparse_utf16_bom(self):
        utext = _str('Søk på nettet')
        uxml = '<?xml version="1.0" encoding="UTF-16"?><p>%s</p>' % utext
        boms = _bytes('\\xFE\\xFF \\xFF\\xFE').decode(
            "unicode_escape").encode("latin1")
        self.assertEqual(5, len(boms))
        xml = uxml.encode("utf-16")
        self.assertTrue(xml[:2] in boms, repr(xml[:2]))

        f = tempfile.NamedTemporaryFile(delete=False)
        try:
            try:
                f.write(xml)
            finally:
                f.close()
            elements = [el for _, el in self.etree.iterparse(f.name)]
            self.assertEqual(1, len(elements))
            root = elements[0]
        finally:
            os.unlink(f.name)
        self.assertEqual(utext, root.text)


class ETreeIOTestCase(_IOTestCaseBase):
    etree = etree

    def test_write_compressed_text(self):
        Element = self.etree.Element
        SubElement = self.etree.SubElement
        ElementTree = self.etree.ElementTree
        text = _str("qwrtioüöä")

        root = Element('root')
        root.text = text
        child = SubElement(root, 'sub')
        child.text = 'TEXT'
        child.tail = 'TAIL'
        SubElement(root, 'sub').text = text

        tree = ElementTree(root)
        out = BytesIO()
        tree.write(out, method='text', encoding='utf8', compression=9)
        out.seek(0)

        f = gzip.GzipFile(fileobj=out)
        try:
            result = f.read().decode('utf8')
        finally:
            f.close()
        self.assertEqual(text+'TEXTTAIL'+text, result)


if ElementTree:
    class ElementTreeIOTestCase(_IOTestCaseBase):
        etree = ElementTree


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeIOTestCase)])
    if ElementTree:
        suite.addTests([unittest.makeSuite(ElementTreeIOTestCase)])
    return suite


if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
