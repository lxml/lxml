<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron">
  <sch:pattern id="number_of_entries">
    <sch:title>mandatory number_of_entries tests</sch:title>
    <sch:rule context="number_of_entries">
      <sch:assert test="text()=count(../entries/entry)">[ERROR] number_of_entries (<sch:value-of select="."/>) must equal the number of entries/entry elements (<sch:value-of select="count(../entries/entry)"/>)</sch:assert>
    </sch:rule>
  </sch:pattern>
</sch:schema>
