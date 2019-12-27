# -*- coding: utf-8 -*-

"""
Test cases related to RelaxNG parsing and validation
"""

from __future__ import absolute_import

import unittest

from .common_imports import (
    etree, BytesIO, _bytes, HelperTestCase, fileInTestDir, make_doctest, skipif
)

try:
    import rnc2rng
except ImportError:
    rnc2rng = None


class ETreeRelaxNGTestCase(HelperTestCase):
    def test_relaxng(self):
        tree_valid = self.parse('<a><b></b></a>')
        tree_invalid = self.parse('<a><c></c></a>')
        schema = self.parse('''\
<element name="a" xmlns="http://relaxng.org/ns/structure/1.0">
  <zeroOrMore>
     <element name="b">
       <text />
     </element>
  </zeroOrMore>
</element>
''')
        schema = etree.RelaxNG(schema)
        self.assertTrue(schema.validate(tree_valid))
        self.assertFalse(schema.error_log.filter_from_errors())

        self.assertFalse(schema.validate(tree_invalid))
        self.assertTrue(schema.error_log.filter_from_errors())

        self.assertTrue(schema.validate(tree_valid))             # repeat valid
        self.assertFalse(schema.error_log.filter_from_errors())  # repeat valid

    def test_relaxng_stringio(self):
        tree_valid = self.parse('<a><b></b></a>')
        tree_invalid = self.parse('<a><c></c></a>')
        schema_file = BytesIO('''\
<element name="a" xmlns="http://relaxng.org/ns/structure/1.0">
  <zeroOrMore>
     <element name="b">
       <text />
     </element>
  </zeroOrMore>
</element>
''')
        schema = etree.RelaxNG(file=schema_file)
        self.assertTrue(schema.validate(tree_valid))
        self.assertFalse(schema.validate(tree_invalid))

    def test_relaxng_elementtree_error(self):
        self.assertRaises(ValueError, etree.RelaxNG, etree.ElementTree())

    def test_relaxng_error(self):
        tree_invalid = self.parse('<a><c></c></a>')
        schema = self.parse('''\
<element name="a" xmlns="http://relaxng.org/ns/structure/1.0">
  <zeroOrMore>
     <element name="b">
       <text />
     </element>
  </zeroOrMore>
</element>
''')
        schema = etree.RelaxNG(schema)
        self.assertFalse(schema.validate(tree_invalid))
        errors = schema.error_log
        self.assertTrue([log for log in errors
                         if log.level_name == "ERROR"])
        self.assertTrue([log for log in errors
                         if "not expect" in log.message])

    def test_relaxng_generic_error(self):
        tree_invalid = self.parse('''\
        <test>
          <reference id="my-ref">This is my unique ref.</reference>
          <data ref="my-ref">Valid data</data>
          <data ref="myref">Invalid data</data>
        </test>
        ''')
        schema = self.parse('''\
        <grammar datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes"
                 xmlns="http://relaxng.org/ns/structure/1.0">
          <define name="by-ref">
            <data type="IDREF"/>
          </define>
          <start>
            <element name="test">
              <zeroOrMore>
                <element name="reference">
                  <attribute name="id">
                    <data type="ID"/>
                  </attribute>
                  <text/>
                </element>
              </zeroOrMore>
              <zeroOrMore>
                <element name="data">
                  <attribute name="ref">
                    <data type="IDREF"/>
                  </attribute>
                  <text/>
                </element>
              </zeroOrMore>
            </element>
          </start>
        </grammar>
        ''')

        schema = etree.RelaxNG(schema)
        self.assertFalse(schema.validate(tree_invalid))
        errors = schema.error_log
        self.assertTrue(errors)
        self.assertTrue([log for log in errors if "IDREF" in log.message])
        self.assertTrue([log for log in errors if "myref" in log.message])

    def test_relaxng_invalid_schema(self):
        schema = self.parse('''\
<element name="a" xmlns="http://relaxng.org/ns/structure/1.0">
  <zeroOrMore>
     <element name="b" />
  </zeroOrMore>
</element>
''')
        self.assertRaises(etree.RelaxNGParseError,
                          etree.RelaxNG, schema)

    def test_relaxng_invalid_schema2(self):
        schema = self.parse('''\
<grammar xmlns="http://relaxng.org/ns/structure/1.0" />
''')
        self.assertRaises(etree.RelaxNGParseError,
                          etree.RelaxNG, schema)

    def test_relaxng_invalid_schema3(self):
        schema = self.parse('''\
<grammar xmlns="http://relaxng.org/ns/structure/1.0">
  <define name="test">
    <element name="test"/>
  </define>
</grammar>
''')
        self.assertRaises(etree.RelaxNGParseError,
                          etree.RelaxNG, schema)

    def test_relaxng_invalid_schema4(self):
        # segfault
        schema = self.parse('''\
<element name="a" xmlns="mynamespace" />
''')
        self.assertRaises(etree.RelaxNGParseError,
                          etree.RelaxNG, schema)

    def test_relaxng_include(self):
        # this will only work if we access the file through path or
        # file object..
        f = open(fileInTestDir('test1.rng'), 'rb')
        try:
            schema = etree.RelaxNG(file=f)
        finally:
            f.close()

    def test_relaxng_shortcut(self):
        tree_valid = self.parse('<a><b></b></a>')
        tree_invalid = self.parse('<a><c></c></a>')
        schema = self.parse('''\
<element name="a" xmlns="http://relaxng.org/ns/structure/1.0">
  <zeroOrMore>
     <element name="b">
       <text />
     </element>
  </zeroOrMore>
</element>
''')
        self.assertTrue(tree_valid.relaxng(schema))
        self.assertFalse(tree_invalid.relaxng(schema))

    def test_multiple_elementrees(self):
        tree = self.parse('<a><b>B</b><c>C</c></a>')
        schema = etree.RelaxNG( self.parse('''\
<element name="a" xmlns="http://relaxng.org/ns/structure/1.0">
  <element name="b">
    <text />
  </element>
  <element name="c">
    <text />
  </element>
</element>
''') )
        self.assertTrue(schema.validate(tree))
        self.assertFalse(schema.error_log.filter_from_errors())

        self.assertTrue(schema.validate(tree))                   # repeat valid
        self.assertFalse(schema.error_log.filter_from_errors())  # repeat valid

        schema = etree.RelaxNG( self.parse('''\
<element name="b" xmlns="http://relaxng.org/ns/structure/1.0">
  <text />
</element>
''') )
        c_tree = etree.ElementTree(tree.getroot()[1])
        self.assertEqual(self._rootstring(c_tree), _bytes('<c>C</c>'))
        self.assertFalse(schema.validate(c_tree))
        self.assertTrue(schema.error_log.filter_from_errors())

        b_tree = etree.ElementTree(tree.getroot()[0])
        self.assertEqual(self._rootstring(b_tree), _bytes('<b>B</b>'))
        self.assertTrue(schema.validate(b_tree))
        self.assertFalse(schema.error_log.filter_from_errors())


class RelaxNGCompactTestCase(HelperTestCase):

    pytestmark = skipif('rnc2rng is None')

    def test_relaxng_compact(self):
        tree_valid = self.parse('<a><b>B</b><c>C</c></a>')
        tree_invalid = self.parse('<a><b></b></a>')
        schema = etree.RelaxNG(file=fileInTestDir('test.rnc'))
        self.assertTrue(schema.validate(tree_valid))
        self.assertFalse(schema.validate(tree_invalid))

    def test_relaxng_compact_file_obj(self):
        with open(fileInTestDir('test.rnc'), 'r') as f:
            schema = etree.RelaxNG(file=f)

        tree_valid = self.parse('<a><b>B</b><c>C</c></a>')
        tree_invalid = self.parse('<a><b></b></a>')
        self.assertTrue(schema.validate(tree_valid))
        self.assertFalse(schema.validate(tree_invalid))

    def test_relaxng_compact_str(self):
        tree_valid = self.parse('<a><b>B</b></a>')
        tree_invalid = self.parse('<a><b>X</b></a>')
        rnc_str = 'element a { element b { "B" } }'
        schema = etree.RelaxNG.from_rnc_string(rnc_str)
        self.assertTrue(schema.validate(tree_valid))
        self.assertFalse(schema.validate(tree_invalid))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeRelaxNGTestCase)])
    suite.addTests(
        [make_doctest('../../../doc/validation.txt')])
    if rnc2rng is not None:
        suite.addTests([unittest.makeSuite(RelaxNGCompactTestCase)])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
