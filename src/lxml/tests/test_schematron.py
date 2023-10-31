# -*- coding: utf-8 -*-

"""
Test cases related to Schematron parsing and validation
"""

from __future__ import absolute_import

import unittest

from .common_imports import etree, HelperTestCase, make_doctest


class ETreeSchematronTestCase(HelperTestCase):
    def test_schematron(self):
        tree_valid = self.parse('<AAA><BBB/><CCC/></AAA>')
        tree_invalid = self.parse('<AAA><BBB/><CCC/><DDD/></AAA>')
        schema = self.parse('''\
<schema xmlns="http://purl.oclc.org/dsdl/schematron" >
     <pattern name="Open model">
          <rule context="AAA">
               <assert test="BBB"> BBB element is not present</assert>
               <assert test="CCC"> CCC element is not present</assert>
          </rule>
     </pattern>
     <pattern name="Closed model">
          <rule context="AAA">
               <assert test="BBB"> BBB element is not present</assert>
               <assert test="CCC"> CCC element is not present</assert>
               <assert test="count(BBB|CCC) = count (*)">There is an extra element</assert>
          </rule>
     </pattern>
</schema>
''')
        schema = etree.Schematron(schema)
        self.assertTrue(schema.validate(tree_valid))
        self.assertFalse(schema.error_log.filter_from_errors())

        self.assertFalse(schema.validate(tree_invalid))
        self.assertTrue(schema.error_log.filter_from_errors())

        self.assertTrue(schema.validate(tree_valid))             # repeat valid
        self.assertFalse(schema.error_log.filter_from_errors())  # repeat valid

    def test_schematron_elementtree_error(self):
        self.assertRaises(ValueError, etree.Schematron, etree.ElementTree())

    def test_schematron_invalid_schema(self):
        schema = self.parse('''\
<schema xmlns="http://purl.oclc.org/dsdl/schematron" >
     <pattern name="Open model">
     </pattern>
</schema>
''')
        self.assertRaises(etree.SchematronParseError,
                          etree.Schematron, schema)

    def test_schematron_invalid_schema_empty(self):
        schema = self.parse('''\
<schema xmlns="http://purl.oclc.org/dsdl/schematron" />
''')
        self.assertRaises(etree.SchematronParseError,
                          etree.Schematron, schema)

    def test_schematron_invalid_schema_namespace(self):
        # segfault
        schema = self.parse('''\
<schema xmlns="mynamespace" />
''')
        self.assertRaises(etree.SchematronParseError,
                          etree.Schematron, schema)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(ETreeSchematronTestCase)])
    suite.addTests(
        [make_doctest('../../../doc/validation.txt')])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
