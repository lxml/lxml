# -*- coding: utf-8 -*-

"""
Test cases related to Schematron parsing and validation
"""

import unittest, sys, os.path

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

from common_imports import etree, HelperTestCase, fileInTestDir
from common_imports import doctest, make_doctest

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
        self.assert_(schema.validate(tree_valid))
        self.assert_(not schema.validate(tree_invalid))

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
    suite.addTests([unittest.makeSuite(ETreeSchematronTestCase)])
    suite.addTests(
        [make_doctest('../../../doc/validation.txt')])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
