# -*- coding: utf-8 -*-

"""
Test cases related to ISO-Schematron parsing and validation
"""

import unittest, sys, os.path
from lxml import isoschematron

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

from common_imports import etree, HelperTestCase, fileInTestDir
from common_imports import doctest, make_doctest

class ETreeISOSchematronTestCase(HelperTestCase):
    def test_schematron(self):
        tree_valid = self.parse('<AAA><BBB/><CCC/></AAA>')
        tree_invalid = self.parse('<AAA><BBB/><CCC/><DDD/></AAA>')
        schema = self.parse('''\
<schema xmlns="http://purl.oclc.org/dsdl/schematron" >
    <pattern id="OpenModel">
        <title>Open Model</title>
        <rule context="AAA">
            <assert test="BBB"> BBB element is not present</assert>
            <assert test="CCC"> CCC element is not present</assert>
        </rule>
    </pattern>
    <pattern id="ClosedModel">
        <title>Closed model"</title>
        <rule context="AAA">
            <assert test="BBB"> BBB element is not present</assert>
            <assert test="CCC"> CCC element is not present</assert>
            <assert test="count(BBB|CCC) = count (*)">There is an extra element</assert>
        </rule>
    </pattern>
</schema>
''')
        schema = isoschematron.Schematron(schema)
        self.assert_(schema.validate(tree_valid))
        self.assert_(not schema.validate(tree_invalid))

    def test_schematron_elementtree_error(self):
        self.assertRaises(ValueError, isoschematron.Schematron, etree.ElementTree())

    # an empty pattern is valid in iso schematron
    def test_schematron_empty_pattern(self):
        schema = self.parse('''\
<schema xmlns="http://purl.oclc.org/dsdl/schematron" >
    <pattern id="OpenModel">
        <title>Open model</title>
    </pattern>
</schema>
''')
        schema = isoschematron.Schematron(schema)
        self.assert_(schema)
        
    def test_schematron_invalid_schema_empty(self):
        schema = self.parse('''\
<schema xmlns="http://purl.oclc.org/dsdl/schematron" />
''')
        self.assertRaises(etree.SchematronParseError,
                          isoschematron.Schematron, schema)

    def test_schematron_invalid_schema_namespace(self):
        schema = self.parse('''\
<schema xmlns="mynamespace" />
''')
        self.assertRaises(etree.SchematronParseError,
                          isoschematron.Schematron, schema)

    def test_schematron_from_tree(self):
        schema = self.parse('''\
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron">
  <sch:pattern id="number_of_entries">
    <sch:title>mandatory number_of_entries tests</sch:title>
    <sch:rule context="number_of_entries">
      <sch:assert test="text()=count(../entries/entry)">[ERROR] number_of_entries (<sch:value-of select="."/>) must equal the number of entries/entry elements (<sch:value-of select="count(../entries/entry)"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>
</sch:schema>
''')
        schematron = isoschematron.Schematron(schema)
        self.assert_(isinstance(schematron, isoschematron.Schematron))

    def test_schematron_from_element(self):
        schema = self.parse('''\
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron">
  <sch:pattern id="number_of_entries">
    <sch:title>mandatory number_of_entries tests</sch:title>
    <sch:rule context="number_of_entries">
      <sch:assert test="text()=count(../entries/entry)">[ERROR] number_of_entries (<sch:value-of select="."/>) must equal the number of entries/entry elements (<sch:value-of select="count(../entries/entry)"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>
</sch:schema>
''')
        schematron = isoschematron.Schematron(schema.getroot())
        self.assert_(isinstance(schematron, isoschematron.Schematron))

    def test_schematron_from_file(self):
        schematron = isoschematron.Schematron(file=fileInTestDir('test.sch'))
        self.assert_(isinstance(schematron, isoschematron.Schematron))

    def test_schematron_call(self):
        schema = self.parse('''\
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron">
  <sch:pattern id="number_of_entries">
    <sch:title>mandatory number_of_entries tests</sch:title>
    <sch:rule context="number_of_entries">
      <sch:assert test="text()=count(../entries/entry)">[ERROR] number_of_entries (<sch:value-of select="."/>) must equal the number of entries/entry elements (<sch:value-of select="count(../entries/entry)"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>
</sch:schema>
''')
        tree_valid = self.parse('''\
<message>
  <number_of_entries>0</number_of_entries>
  <entries>
  </entries>
</message>
''')
        tree_invalid = self.parse('''\
<message>
  <number_of_entries>3</number_of_entries>
  <entries>
    <entry>Entry 1</entry>
    <entry>Entry 2</entry>
  </entries>
</message>
''')
        schematron = isoschematron.Schematron(schema)
        self.assert_(schematron(tree_valid), schematron.error_log)
        valid = schematron(tree_invalid)
        self.assert_(not valid)

    def test_schematron_validate(self):
        schema = self.parse('''\
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron">
  <sch:pattern id="number_of_entries">
    <sch:title>mandatory number_of_entries tests</sch:title>
    <sch:rule context="number_of_entries">
      <sch:assert test="text()=count(../entries/entry)">[ERROR] number_of_entries (<sch:value-of select="."/>) must equal the number of entries/entry elements (<sch:value-of select="count(../entries/entry)"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>
</sch:schema>
''')
        tree_valid = self.parse('''\
<message>
  <number_of_entries>0</number_of_entries>
  <entries>
  </entries>
</message>
''')
        tree_invalid = self.parse('''\
<message>
  <number_of_entries>3</number_of_entries>
  <entries>
    <entry>Entry 1</entry>
    <entry>Entry 2</entry>
  </entries>
</message>
''')
        schematron = isoschematron.Schematron(schema)
        self.assert_(schematron.validate(tree_valid), schematron.error_log)
        valid = schematron.validate(tree_invalid)
        self.assert_(not valid)

    def test_schematron_assertValid(self):
        schema = self.parse('''\
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron">
  <sch:pattern id="number_of_entries">
    <sch:title>mandatory number_of_entries tests</sch:title>
    <sch:rule context="number_of_entries">
      <sch:assert test="text()=count(../entries/entry)">[ERROR] number_of_entries (<sch:value-of select="."/>) must equal the number of entries/entry elements (<sch:value-of select="count(../entries/entry)"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>
</sch:schema>
''')
        tree_valid = self.parse('''\
<message>
  <number_of_entries>0</number_of_entries>
  <entries>
  </entries>
</message>
''')
        tree_invalid = self.parse('''\
<message>
  <number_of_entries>3</number_of_entries>
  <entries>
    <entry>Entry 1</entry>
    <entry>Entry 2</entry>
  </entries>
</message>
''')
        schematron = isoschematron.Schematron(schema)
        self.assert_(schematron(tree_valid), schematron.error_log)
        self.assertRaises(etree.DocumentInvalid, schematron.assertValid,
                          tree_invalid)

    def test_schematron_error_log(self):
        schema = self.parse('''\
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron">
  <sch:pattern id="number_of_entries">
    <sch:title>mandatory number_of_entries tests</sch:title>
    <sch:rule context="number_of_entries">
      <sch:assert test="text()=count(../entries/entry)">[ERROR] number_of_entries (<sch:value-of select="."/>) must equal the number of entries/entry elements (<sch:value-of select="count(../entries/entry)"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>
</sch:schema>
''')
        tree_valid = self.parse('''\
<message>
  <number_of_entries>0</number_of_entries>
  <entries>
  </entries>
</message>
''')
        tree_invalid = self.parse('''\
<message>
  <number_of_entries>3</number_of_entries>
  <entries>
    <entry>Entry 1</entry>
    <entry>Entry 2</entry>
  </entries>
</message>
''')
        schematron = isoschematron.Schematron(schema)
        self.assert_(schematron(tree_valid), schematron.error_log)
        valid = schematron(tree_invalid)
        self.assert_(not valid)
        self.assertEquals(len(schematron.error_log), 1,
                          'expected single error: %s (%s errors)' %
                          (schematron.error_log, len(schematron.error_log)))

    def test_schematron_result_report(self):
        schema = self.parse('''\
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron">
  <sch:pattern id="number_of_entries">
    <sch:title>mandatory number_of_entries tests</sch:title>
    <sch:rule context="number_of_entries">
      <sch:assert test="text()=count(../entries/entry)">[ERROR] number_of_entries (<sch:value-of select="."/>) must equal the number of entries/entry elements (<sch:value-of select="count(../entries/entry)"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>
</sch:schema>
''')
        tree_valid = self.parse('''\
<message>
  <number_of_entries>0</number_of_entries>
  <entries>
  </entries>
</message>
''')
        tree_invalid = self.parse('''\
<message>
  <number_of_entries>3</number_of_entries>
  <entries>
    <entry>Entry 1</entry>
    <entry>Entry 2</entry>
  </entries>
</message>
''')
        schematron = isoschematron.Schematron(schema, store_report=True)
        self.assert_(schematron(tree_valid), schematron.error_log)
        valid = schematron(tree_invalid)
        self.assert_(not valid)
        self.assert_(
            isinstance(schematron.validation_report, etree._ElementTree),
            'expected a validation report result tree, got: %s' %
            (schematron.validation_report))

        schematron = isoschematron.Schematron(schema, store_report=False)
        self.assert_(schematron(tree_valid), schematron.error_log)
        valid = schematron(tree_invalid)
        self.assert_(not valid)
        self.assert_(schematron.validation_report is None,
            'validation reporting switched off, still: %s' %
            (schematron.validation_report))

    def test_schematron_store_schematron(self):
        schema = self.parse('''\
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron">
  <sch:pattern id="number_of_entries">
    <sch:title>mandatory number_of_entries tests</sch:title>
    <sch:rule context="number_of_entries">
      <sch:assert test="text()=count(../entries/entry)">[ERROR] number_of_entries (<sch:value-of select="."/>) must equal the number of entries/entry elements (<sch:value-of select="count(../entries/entry)"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>
</sch:schema>
''')
        schematron = isoschematron.Schematron(schema)
        self.assert_(schematron.validator_xslt is None)

        schematron = isoschematron.Schematron(schema, store_schematron=True) 
        self.assert_(isinstance(schematron.schematron, etree._ElementTree),
                     'expected schematron schema to be stored')

    def test_schematron_store_xslt(self):
        schema = self.parse('''\
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron">
  <sch:pattern id="number_of_entries">
    <sch:title>mandatory number_of_entries tests</sch:title>
    <sch:rule context="number_of_entries">
      <sch:assert test="text()=count(../entries/entry)">[ERROR] number_of_entries (<sch:value-of select="."/>) must equal the number of entries/entry elements (<sch:value-of select="count(../entries/entry)"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>
</sch:schema>
''')
        schematron = isoschematron.Schematron(schema)
        self.assert_(schematron.validator_xslt is None)

        schematron = isoschematron.Schematron(schema, store_xslt=True) 
        self.assert_(isinstance(schematron.validator_xslt, etree._ElementTree),
                     'expected validator xslt to be stored')
       
    def test_schematron_abstract(self):
        schema = self.parse('''\
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron">
  <sch:title>iso schematron validation</sch:title>
  <sch:ns uri="http://www.w3.org/2001/XMLSchema-instance" prefix="xsi"/>
  <sch:ns uri="http://codespeak.net/lxml/objectify/pytype" prefix="py"/>

  <!-- of course, these only really make sense when combined with a schema that
       ensures datatype xs:dateTime -->
       
  <sch:pattern abstract="true" id="abstract.dateTime.tz_utc">
    <sch:rule context="$datetime">
      <sch:let name="tz" value="concat(substring-after(substring-after(./text(), 'T'), '+'), substring-after(substring-after(./text(), 'T'), '-'))"/>
      <sch:let name="lastchar" value="substring(./text(), string-length(./text()))"/>
      <sch:assert test="$lastchar='Z' or $tz='00:00'">[ERROR] element (<sch:value-of select="name(.)"/>) dateTime value (<sch:value-of select="."/>) is not qualified as UTC (tz: <sch:value-of select="$tz"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>

  <sch:pattern abstract="true" id="abstract.dateTime.tz_utc_nillable">
    <sch:rule context="$datetime">
      <sch:let name="tz" value="concat(substring-after(substring-after(./text(), 'T'), '+'), substring-after(substring-after(./text(), 'T'), '-'))"/>
      <sch:let name="lastchar" value="substring(./text(), string-length(./text()))"/>
      <sch:assert test="@xsi:nil='true'  or ($lastchar='Z' or $tz='00:00')">[ERROR] element (<sch:value-of select="name(.)"/>) dateTime value (<sch:value-of select="."/>) is not qualified as UTC (tz: <sch:value-of select="$tz"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>

  <sch:pattern is-a="abstract.dateTime.tz_utc" id="datetime" >
    <sch:param name="datetime" value="datetime"/>
  </sch:pattern>

  <sch:pattern is-a="abstract.dateTime.tz_utc_nillable" id="nillableDatetime">
    <sch:param name="datetime" value="nillableDatetime"/>
  </sch:pattern>

</sch:schema>
''')
        valid_trees = [
            self.parse('''\
<root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <datetime>2009-12-10T15:21:00Z</datetime>
  <nillableDatetime xsi:nil="true"/>
</root>
'''),
            self.parse('''\
<root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <datetime>2009-12-10T15:21:00Z</datetime>
  <nillableDatetime>2009-12-10T15:21:00Z</nillableDatetime>
</root>
'''),
            self.parse('''\
<root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <datetime>2009-12-10T15:21:00+00:00</datetime>
  <nillableDatetime>2009-12-10T15:21:00-00:00</nillableDatetime>
</root>
'''),
            ]
                       
        schematron = isoschematron.Schematron(schema)
        for tree_valid in valid_trees:
            self.assert_(schematron(tree_valid), schematron.error_log)

        tree_invalid = self.parse('''\
<root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <datetime>2009-12-10T16:21:00+01:00</datetime>
  <nillableDatetime>2009-12-10T16:21:00+01:00</nillableDatetime>
</root>
''')
        expected = 2
        valid = schematron(tree_invalid)
        self.assert_(not valid)
        self.assertEquals(
            len(schematron.error_log), expected,
            'expected %s errors: %s (%s errors)' %
            (expected, schematron.error_log, len(schematron.error_log)))

        tree_invalid = self.parse('''\
<root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <datetime xsi:nil="true"/>
  <nillableDatetime>2009-12-10T16:21:00Z</nillableDatetime>
</root>
''')
        expected = 1
        valid = schematron(tree_invalid)
        self.assert_(not valid)
        self.assertEquals(
            len(schematron.error_log), expected,
            'expected %s errors: %s (%s errors)' %
            (expected, schematron.error_log, len(schematron.error_log)))

    def test_schematron_phases(self):
        schema = self.parse('''\
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron">
  <sch:title>iso schematron validation</sch:title>
  <sch:ns uri="http://www.w3.org/2001/XMLSchema-instance" prefix="xsi"/>
  <sch:ns uri="http://codespeak.net/lxml/objectify/pytype" prefix="py"/>

  <sch:phase id="mandatory">
    <sch:active pattern="number_of_entries"/>
  </sch:phase>

  <sch:phase id="datetime_checks">
    <sch:active pattern="datetime"/>
    <sch:active pattern="nillableDatetime"/>
  </sch:phase>

  <sch:phase id="full">
    <sch:active pattern="number_of_entries"/>
    <sch:active pattern="datetime"/>
    <sch:active pattern="nillableDatetime"/>
  </sch:phase>

  <!-- of course, these only really make sense when combined with a schema that
       ensures datatype xs:dateTime -->
  
  <sch:pattern abstract="true" id="abstract.dateTime.tz_utc">
    <sch:rule context="$datetime">
      <sch:let name="tz" value="concat(substring-after(substring-after(./text(), 'T'), '+'), substring-after(substring-after(./text(), 'T'), '-'))"/>
      <sch:let name="lastchar" value="substring(./text(), string-length(./text()))"/>
      <sch:assert test="$lastchar='Z' or $tz='00:00'">[ERROR] element (<sch:value-of select="name(.)"/>) dateTime value (<sch:value-of select="."/>) is not qualified as UTC (tz: <sch:value-of select="$tz"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>

  <sch:pattern abstract="true" id="abstract.dateTime.tz_utc_nillable">
    <sch:rule context="$datetime">
      <sch:let name="tz" value="concat(substring-after(substring-after(./text(), 'T'), '+'), substring-after(substring-after(./text(), 'T'), '-'))"/>
      <sch:let name="lastchar" value="substring(./text(), string-length(./text()))"/>
      <sch:assert test="@xsi:nil='true'  or ($lastchar='Z' or $tz='00:00')">[ERROR] element (<sch:value-of select="name(.)"/>) dateTime value (<sch:value-of select="."/>) is not qualified as UTC (tz: <sch:value-of select="$tz"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>

  <sch:pattern id="number_of_entries">
    <sch:title>mandatory number_of_entries test</sch:title>
    <sch:rule context="number_of_entries">
      <sch:assert test="text()=count(../entries/entry)">[ERROR] number_of_entries (<sch:value-of select="."/>) must equal the number of entries/entry elements (<sch:value-of select="count(../entries/entry)"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>

  <sch:pattern  id="datetime" is-a="abstract.dateTime.tz_utc">
    <sch:param name="datetime" value="datetime"/>
  </sch:pattern>

  <sch:pattern  id="nillableDatetime" is-a="abstract.dateTime.tz_utc_nillable">
    <sch:param name="datetime" value="nillableDatetime"/>
  </sch:pattern>

</sch:schema>
''')
        tree_valid = self.parse('''\
<message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <datetime>2009-12-10T15:21:00Z</datetime>
  <nillableDatetime xsi:nil="true"/>
  <number_of_entries>0</number_of_entries>
  <entries>
  </entries>
</message>
''')
        tree_invalid = self.parse('''\
<message>
  <datetime>2009-12-10T16:21:00+01:00</datetime>
  <nillableDatetime>2009-12-10T16:21:00+01:00</nillableDatetime>
  <number_of_entries>3</number_of_entries>
  <entries>
    <entry>Entry 1</entry>
    <entry>Entry 2</entry>
  </entries>
</message>
''')
        # check everything (default phase #ALL)
        schematron = isoschematron.Schematron(schema)
        self.assert_(schematron(tree_valid), schematron.error_log)
        expected = 3
        valid = schematron(tree_invalid)
        self.assert_(not valid)
        self.assertEquals(
            len(schematron.error_log), expected,
            'expected %s errors: %s (%s errors)' %
            (expected, schematron.error_log, len(schematron.error_log)))

        # check phase mandatory
        schematron = isoschematron.Schematron(
            schema, compile_params={'phase': 'mandatory'})
        self.assert_(schematron(tree_valid), schematron.error_log)
        expected = 1
        valid = schematron(tree_invalid)
        self.assert_(not valid)
        self.assertEquals(
            len(schematron.error_log), expected,
            'expected %s errors: %s (%s errors)' %
            (expected, schematron.error_log, len(schematron.error_log)))

        # check phase datetime_checks
        schematron = isoschematron.Schematron(
            schema, compile_params={'phase': 'datetime_checks'})
        self.assert_(schematron(tree_valid), schematron.error_log)
        expected = 2
        valid = schematron(tree_invalid)
        self.assert_(not valid)
        self.assertEquals(
            len(schematron.error_log), expected,
            'expected %s errors: %s (%s errors)' %
            (expected, schematron.error_log, len(schematron.error_log)))

        # check phase full
        schematron = isoschematron.Schematron(
            schema, compile_params={'phase': 'full'})
        self.assert_(schematron(tree_valid), schematron.error_log)
        expected = 3
        valid = schematron(tree_invalid)
        self.assert_(not valid)
        self.assertEquals(
            len(schematron.error_log), expected,
            'expected %s errors: %s (%s errors)' %
            (expected, schematron.error_log, len(schematron.error_log)))
                                      
    def test_schematron_phases_kwarg(self):
        schema = self.parse('''\
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron">
  <sch:title>iso schematron validation</sch:title>
  <sch:ns uri="http://www.w3.org/2001/XMLSchema-instance" prefix="xsi"/>
  <sch:ns uri="http://codespeak.net/lxml/objectify/pytype" prefix="py"/>

  <sch:phase id="mandatory">
    <sch:active pattern="number_of_entries"/>
  </sch:phase>

  <sch:phase id="datetime_checks">
    <sch:active pattern="datetime"/>
    <sch:active pattern="nillableDatetime"/>
  </sch:phase>

  <sch:phase id="full">
    <sch:active pattern="number_of_entries"/>
    <sch:active pattern="datetime"/>
    <sch:active pattern="nillableDatetime"/>
  </sch:phase>

  <!-- of course, these only really make sense when combined with a schema that
       ensures datatype xs:dateTime -->
  
  <sch:pattern abstract="true" id="abstract.dateTime.tz_utc">
    <sch:rule context="$datetime">
      <sch:let name="tz" value="concat(substring-after(substring-after(./text(), 'T'), '+'), substring-after(substring-after(./text(), 'T'), '-'))"/>
      <sch:let name="lastchar" value="substring(./text(), string-length(./text()))"/>
      <sch:assert test="$lastchar='Z' or $tz='00:00'">[ERROR] element (<sch:value-of select="name(.)"/>) dateTime value (<sch:value-of select="."/>) is not qualified as UTC (tz: <sch:value-of select="$tz"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>

  <sch:pattern abstract="true" id="abstract.dateTime.tz_utc_nillable">
    <sch:rule context="$datetime">
      <sch:let name="tz" value="concat(substring-after(substring-after(./text(), 'T'), '+'), substring-after(substring-after(./text(), 'T'), '-'))"/>
      <sch:let name="lastchar" value="substring(./text(), string-length(./text()))"/>
      <sch:assert test="@xsi:nil='true'  or ($lastchar='Z' or $tz='00:00')">[ERROR] element (<sch:value-of select="name(.)"/>) dateTime value (<sch:value-of select="."/>) is not qualified as UTC (tz: <sch:value-of select="$tz"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>

  <sch:pattern id="number_of_entries">
    <sch:title>mandatory number_of_entries test</sch:title>
    <sch:rule context="number_of_entries">
      <sch:assert test="text()=count(../entries/entry)">[ERROR] number_of_entries (<sch:value-of select="."/>) must equal the number of entries/entry elements (<sch:value-of select="count(../entries/entry)"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>

  <sch:pattern  id="datetime" is-a="abstract.dateTime.tz_utc">
    <sch:param name="datetime" value="datetime"/>
  </sch:pattern>

  <sch:pattern  id="nillableDatetime" is-a="abstract.dateTime.tz_utc_nillable">
    <sch:param name="datetime" value="nillableDatetime"/>
  </sch:pattern>

</sch:schema>
''')
        tree_valid = self.parse('''\
<message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <datetime>2009-12-10T15:21:00Z</datetime>
  <nillableDatetime xsi:nil="true"/>
  <number_of_entries>0</number_of_entries>
  <entries>
  </entries>
</message>
''')
        tree_invalid = self.parse('''\
<message>
  <datetime>2009-12-10T16:21:00+01:00</datetime>
  <nillableDatetime>2009-12-10T16:21:00+01:00</nillableDatetime>
  <number_of_entries>3</number_of_entries>
  <entries>
    <entry>Entry 1</entry>
    <entry>Entry 2</entry>
  </entries>
</message>
''')
        # check everything (default phase #ALL)
        schematron = isoschematron.Schematron(schema)
        self.assert_(schematron(tree_valid), schematron.error_log)
        expected = 3
        valid = schematron(tree_invalid)
        self.assert_(not valid)
        self.assertEquals(
            len(schematron.error_log), expected,
            'expected %s errors: %s (%s errors)' %
            (expected, schematron.error_log, len(schematron.error_log)))

        # check phase mandatory
        schematron = isoschematron.Schematron(schema, phase='mandatory')
        self.assert_(schematron(tree_valid), schematron.error_log)
        expected = 1
        valid = schematron(tree_invalid)
        self.assert_(not valid)
        self.assertEquals(
            len(schematron.error_log), expected,
            'expected %s errors: %s (%s errors)' %
            (expected, schematron.error_log, len(schematron.error_log)))

        # check phase datetime_checks
        schematron = isoschematron.Schematron(schema, phase='datetime_checks')
        self.assert_(schematron(tree_valid), schematron.error_log)
        expected = 2
        valid = schematron(tree_invalid)
        self.assert_(not valid)
        self.assertEquals(
            len(schematron.error_log), expected,
            'expected %s errors: %s (%s errors)' %
            (expected, schematron.error_log, len(schematron.error_log)))

        # check phase full
        schematron = isoschematron.Schematron(schema, phase='full')
        self.assert_(schematron(tree_valid), schematron.error_log)
        expected = 3
        valid = schematron(tree_invalid)
        self.assert_(not valid)
        self.assertEquals(
            len(schematron.error_log), expected, 'expected %s errors: %s (%s errors)' %
            (expected, schematron.error_log, len(schematron.error_log)))
                                      
    def test_schematron_xmlschema_embedded(self):
        schema = self.parse('''\
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:sch="http://purl.oclc.org/dsdl/schematron">
    <xs:element name="message">
        <xs:complexType>
            <xs:sequence>
                <xs:element name="number_of_entries" type="xs:positiveInteger">
                    <xs:annotation>
                        <xs:appinfo>
                            <sch:pattern id="number_of_entries">
                                <sch:title>mandatory number_of_entries tests</sch:title>
                                <sch:rule context="number_of_entries">
                                    <sch:assert test="text()=count(../entries/entry)">[ERROR] number_of_entries (<sch:value-of select="."/>) must equal the number of entries/entry elements (<sch:value-of select="count(../entries/entry)"/>)</sch:assert>
                                </sch:rule>
                            </sch:pattern>
                        </xs:appinfo>
                    </xs:annotation>
                </xs:element>
                <xs:element name="entries">
                    <xs:complexType>
                        <xs:sequence>
                            <xs:element name="entry" type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
                        </xs:sequence>
                    </xs:complexType>
                </xs:element>
            </xs:sequence>
        </xs:complexType>
    </xs:element>
</xs:schema>
''')
        tree_valid = self.parse('''\
<message>
  <number_of_entries>2</number_of_entries>
  <entries>
    <entry>Entry 1</entry>
    <entry>Entry 2</entry>
  </entries>
</message>
''')
        tree_invalid = self.parse('''\
<message>
  <number_of_entries>1</number_of_entries>
  <entries>
    <entry>Entry 1</entry>
    <entry>Entry 2</entry>
  </entries>
</message>
''')
        xmlschema = etree.XMLSchema(schema)
        schematron = isoschematron.Schematron(schema)
        # fwiw, this must also be XMLSchema-valid
        self.assert_(xmlschema(tree_valid), xmlschema.error_log)
        self.assert_(schematron(tree_valid))
        # still schema-valid
        self.assert_(xmlschema(tree_invalid), xmlschema.error_log)
        self.assert_(not schematron(tree_invalid))

    def test_schematron_relaxng_embedded(self):
        schema = self.parse('''\
<grammar xmlns="http://relaxng.org/ns/structure/1.0"
  xmlns:sch="http://purl.oclc.org/dsdl/schematron"
  datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
  <start>
    <ref name="message"/>
  </start>
  <define name="message">
    <element name="message">
      <element name="number_of_entries">
        <!-- RelaxNG can be mixed freely with stuff from other namespaces -->
        <sch:pattern id="number_of_entries">
          <sch:title>mandatory number_of_entries tests</sch:title>
          <sch:rule context="number_of_entries">
            <sch:assert test="text()=count(../entries/entry)">[ERROR] number_of_entries (<sch:value-of select="."/>) must equal the number of entries/entry elements (<sch:value-of select="count(../entries/entry)"/>)</sch:assert>
          </sch:rule>
        </sch:pattern>
        <data type="positiveInteger"/>
      </element>
      <element name="entries">
        <zeroOrMore>
          <element name="entry"><data type="string"/></element>
        </zeroOrMore>
      </element>
    </element>
  </define>
</grammar>
''')
        tree_valid = self.parse('''\
<message>
  <number_of_entries>2</number_of_entries>
  <entries>
    <entry>Entry 1</entry>
    <entry>Entry 2</entry>
  </entries>
</message>
''')
        tree_invalid = self.parse('''\
<message>
  <number_of_entries>1</number_of_entries>
  <entries>
    <entry>Entry 1</entry>
    <entry>Entry 2</entry>
  </entries>
</message>
''')
        relaxng = etree.RelaxNG(schema)
        schematron = isoschematron.Schematron(schema)
        # fwiw, this must also be RelaxNG-valid
        self.assert_(relaxng(tree_valid), relaxng.error_log)
        self.assert_(schematron(tree_valid))
        # still schema-valid
        self.assert_(relaxng(tree_invalid), relaxng.error_log)
        self.assert_(not schematron(tree_invalid))

    def test_schematron_invalid_args(self):
        schema = self.parse('''\
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron">
  <sch:pattern id="number_of_entries">
    <sch:title>mandatory number_of_entries tests</sch:title>
    <sch:rule context="number_of_entries">
      <sch:assert test="text()=count(../entries/entry)">[ERROR] number_of_entries (<sch:value-of select="."/>) must equal the number of entries/entry elements (<sch:value-of select="count(../entries/entry)"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>
</sch:schema>
''')
        # handing phase as keyword arg will *not* raise the type error
        self.assertRaises(TypeError, isoschematron.Schematron, schema,
                          compile_params={'phase': None})

    def test_schematron_customization(self):
        class MySchematron(isoschematron.Schematron):
            def _extract(self, root):
                schematron = (root.xpath(
                    '//sch:schema',
                    namespaces={'sch': "http://purl.oclc.org/dsdl/schematron"})
                    or [None])[0]
                return schematron
                              
            def _include(self, schematron, **kwargs):
                raise RuntimeError('inclusion unsupported')
            
            def _expand(self, schematron, **kwargs):
                raise RuntimeError('expansion unsupported')
            
            def _validation_errors(self, validationReport):
                valid = etree.XPath(
                    'count(//svrl:successful-report[@flag="critical"])=1',
                    namespaces={'svrl': isoschematron.SVRL_NS})(
                    validationReport)
                if valid:
                    return []
                error = etree.Element('Error')
                error.text = 'missing critical condition report'
                return [error]

        tree_valid = self.parse('<AAA><BBB/><CCC/></AAA>')
        tree_invalid = self.parse('<AAA><BBB/><CCC/><DDD/></AAA>')
        schema = self.parse('''\
<schema xmlns="http://www.example.org/yet/another/schema/dialect">
  <schema xmlns="http://purl.oclc.org/dsdl/schematron" >
    <pattern id="OpenModel">
      <title>Open Model</title>
      <rule context="AAA">
        <report test="BBB" flag="info">BBB element must be present</report>
        <report test="CCC" flag="info">CCC element must be present</report>
      </rule>
    </pattern>
    <pattern id="ClosedModel">
      <title>Closed model"</title>
      <rule context="AAA">
        <report test="BBB" flag="info">BBB element must be present</report>
        <report test="CCC" flag="info">CCC element must be present</report>
        <report test="count(BBB|CCC) = count(*)" flag="critical">Only BBB and CCC children must be present</report>
      </rule>
    </pattern>
  </schema>
</schema>
''')
        # check if overridden _include is run
        self.assertRaises(RuntimeError, MySchematron, schema, store_report=True)
        # check if overridden _expand is run
        self.assertRaises(RuntimeError, MySchematron, schema, store_report=True,
                          include=False)
        
        schema = MySchematron(schema, store_report=True, include=False,
                              expand=False)
        self.assert_(schema.validate(tree_valid))
        self.assert_(not schema.validate(tree_invalid))

    #TODO: test xslt parameters for inclusion, expand & compile steps (?)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeISOSchematronTestCase)])
    suite.addTests(
        [make_doctest('../../../doc/validation.txt')])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
