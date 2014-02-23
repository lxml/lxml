# -*- coding: utf-8 -*-

"""
Test cases related to XML Schema parsing and validation
"""

import unittest, sys, os.path

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

from common_imports import etree, BytesIO, HelperTestCase, fileInTestDir
from common_imports import doctest, make_doctest


class ETreeXMLSchemaTestCase(HelperTestCase):
    def test_xmlschema(self):
        tree_valid = self.parse('<a><b></b></a>')
        tree_invalid = self.parse('<a><c></c></a>')
        schema = self.parse('''
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="a" type="AType"/>
  <xsd:complexType name="AType">
    <xsd:sequence>
      <xsd:element name="b" type="xsd:string" />
    </xsd:sequence>
  </xsd:complexType>
</xsd:schema>
''')
        schema = etree.XMLSchema(schema)
        self.assertTrue(schema.validate(tree_valid))
        self.assertFalse(schema.validate(tree_invalid))
        self.assertTrue(schema.validate(tree_valid))     # retry valid
        self.assertFalse(schema.validate(tree_invalid))  # retry invalid

    def test_xmlschema_error_log(self):
        tree_valid = self.parse('<a><b></b></a>')
        tree_invalid = self.parse('<a><c></c></a>')
        schema = self.parse('''
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="a" type="AType"/>
  <xsd:complexType name="AType">
    <xsd:sequence>
      <xsd:element name="b" type="xsd:string" />
    </xsd:sequence>
  </xsd:complexType>
</xsd:schema>
''')
        schema = etree.XMLSchema(schema)
        self.assertTrue(schema.validate(tree_valid))
        self.assertFalse(schema.error_log.filter_from_errors())

        self.assertFalse(schema.validate(tree_invalid))
        self.assertTrue(schema.error_log.filter_from_errors())
        self.assertTrue(schema.error_log.filter_types(
            etree.ErrorTypes.SCHEMAV_ELEMENT_CONTENT))

        self.assertTrue(schema.validate(tree_valid))
        self.assertFalse(schema.error_log.filter_from_errors())

        self.assertFalse(schema.validate(tree_invalid))
        self.assertTrue(schema.error_log.filter_from_errors())
        self.assertTrue(schema.error_log.filter_types(
            etree.ErrorTypes.SCHEMAV_ELEMENT_CONTENT))

    def test_xmlschema_default_attributes(self):
        schema = self.parse('''
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="a" type="AType"/>
  <xsd:complexType name="AType">
    <xsd:sequence minOccurs="4" maxOccurs="4">
      <xsd:element name="b" type="BType" />
    </xsd:sequence>
  </xsd:complexType>
  <xsd:complexType name="BType">
    <xsd:attribute name="hardy" type="xsd:string" default="hey" />
  </xsd:complexType>
</xsd:schema>
''')
        schema = etree.XMLSchema(schema, attribute_defaults=True)

        tree = self.parse('<a><b hardy="ho"/><b/><b hardy="ho"/><b/></a>')

        root = tree.getroot()
        self.assertEqual('ho', root[0].get('hardy'))
        self.assertEqual(None, root[1].get('hardy'))
        self.assertEqual('ho', root[2].get('hardy'))
        self.assertEqual(None, root[3].get('hardy'))

        self.assertTrue(schema(tree))

        root = tree.getroot()
        self.assertEqual('ho', root[0].get('hardy'))
        self.assertEqual('hey', root[1].get('hardy'))
        self.assertEqual('ho', root[2].get('hardy'))
        self.assertEqual('hey', root[3].get('hardy'))

    def test_xmlschema_parse(self):
        schema = self.parse('''
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="a" type="AType"/>
  <xsd:complexType name="AType">
    <xsd:sequence>
      <xsd:element name="b" type="xsd:string" />
    </xsd:sequence>
  </xsd:complexType>
</xsd:schema>
''')
        schema = etree.XMLSchema(schema)
        parser = etree.XMLParser(schema=schema)

        tree_valid = self.parse('<a><b></b></a>', parser=parser)
        self.assertEqual('a', tree_valid.getroot().tag)

        self.assertRaises(etree.XMLSyntaxError,
                          self.parse, '<a><c></c></a>', parser=parser)

    def test_xmlschema_parse_default_attributes(self):
        # does not work as of libxml2 2.7.3
        schema = self.parse('''
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="a" type="AType"/>
  <xsd:complexType name="AType">
    <xsd:sequence minOccurs="4" maxOccurs="4">
      <xsd:element name="b" type="BType" />
    </xsd:sequence>
  </xsd:complexType>
  <xsd:complexType name="BType">
    <xsd:attribute name="hardy" type="xsd:string" default="hey" />
  </xsd:complexType>
</xsd:schema>
''')
        schema = etree.XMLSchema(schema)
        parser = etree.XMLParser(schema=schema, attribute_defaults=True)

        tree_valid = self.parse('<a><b hardy="ho"/><b/><b hardy="ho"/><b/></a>',
                                parser=parser)
        root = tree_valid.getroot()
        self.assertEqual('ho', root[0].get('hardy'))
        self.assertEqual('hey', root[1].get('hardy'))
        self.assertEqual('ho', root[2].get('hardy'))
        self.assertEqual('hey', root[3].get('hardy'))

    def test_xmlschema_parse_default_attributes_schema_config(self):
        # does not work as of libxml2 2.7.3
        schema = self.parse('''
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="a" type="AType"/>
  <xsd:complexType name="AType">
    <xsd:sequence minOccurs="4" maxOccurs="4">
      <xsd:element name="b" type="BType" />
    </xsd:sequence>
  </xsd:complexType>
  <xsd:complexType name="BType">
    <xsd:attribute name="hardy" type="xsd:string" default="hey" />
  </xsd:complexType>
</xsd:schema>
''')
        schema = etree.XMLSchema(schema, attribute_defaults=True)
        parser = etree.XMLParser(schema=schema)

        tree_valid = self.parse('<a><b hardy="ho"/><b/><b hardy="ho"/><b/></a>',
                                parser=parser)
        root = tree_valid.getroot()
        self.assertEqual('ho', root[0].get('hardy'))
        self.assertEqual('hey', root[1].get('hardy'))
        self.assertEqual('ho', root[2].get('hardy'))
        self.assertEqual('hey', root[3].get('hardy'))

    def test_xmlschema_parse_fixed_attributes(self):
        # does not work as of libxml2 2.7.3
        schema = self.parse('''
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="a" type="AType"/>
  <xsd:complexType name="AType">
    <xsd:sequence minOccurs="3" maxOccurs="3">
      <xsd:element name="b" type="BType" />
    </xsd:sequence>
  </xsd:complexType>
  <xsd:complexType name="BType">
    <xsd:attribute name="hardy" type="xsd:string" fixed="hey" />
  </xsd:complexType>
</xsd:schema>
''')
        schema = etree.XMLSchema(schema)
        parser = etree.XMLParser(schema=schema, attribute_defaults=True)

        tree_valid = self.parse('<a><b/><b hardy="hey"/><b/></a>',
                                parser=parser)
        root = tree_valid.getroot()
        self.assertEqual('hey', root[0].get('hardy'))
        self.assertEqual('hey', root[1].get('hardy'))
        self.assertEqual('hey', root[2].get('hardy'))

    def test_xmlschema_stringio(self):
        schema_file = BytesIO('''
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="a" type="AType"/>
  <xsd:complexType name="AType">
    <xsd:sequence>
      <xsd:element name="b" type="xsd:string" />
    </xsd:sequence>
  </xsd:complexType>
</xsd:schema>
''')
        schema = etree.XMLSchema(file=schema_file)
        parser = etree.XMLParser(schema=schema)

        tree_valid = self.parse('<a><b></b></a>', parser=parser)
        self.assertEqual('a', tree_valid.getroot().tag)

        self.assertRaises(etree.XMLSyntaxError,
                          self.parse, '<a><c></c></a>', parser=parser)

    def test_xmlschema_iterparse(self):
        schema = self.parse('''
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="a" type="AType"/>
  <xsd:complexType name="AType">
    <xsd:sequence>
      <xsd:element name="b" type="xsd:string" />
    </xsd:sequence>
  </xsd:complexType>
</xsd:schema>
''')
        schema = etree.XMLSchema(schema)
        xml = BytesIO('<a><b></b></a>')
        events = [ (event, el.tag)
                   for (event, el) in etree.iterparse(xml, schema=schema) ]

        self.assertEqual([('end', 'b'), ('end', 'a')],
                          events)

    def test_xmlschema_iterparse_fail(self):
        schema = self.parse('''
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="a" type="AType"/>
  <xsd:complexType name="AType">
    <xsd:sequence>
      <xsd:element name="b" type="xsd:string" />
    </xsd:sequence>
  </xsd:complexType>
</xsd:schema>
''')
        schema = etree.XMLSchema(schema)
        self.assertRaises(
            etree.XMLSyntaxError,
            list, etree.iterparse(BytesIO('<a><c></c></a>'), schema=schema))

    def test_xmlschema_elementtree_error(self):
        self.assertRaises(ValueError, etree.XMLSchema, etree.ElementTree())

    def test_xmlschema_comment_error(self):
        self.assertRaises(ValueError, etree.XMLSchema, etree.Comment('TEST'))

    def test_xmlschema_illegal_validation_error(self):
        schema = self.parse('''
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="a" type="xsd:string"/>
</xsd:schema>
''')
        schema = etree.XMLSchema(schema)

        root = etree.Element('a')
        root.text = 'TEST'
        self.assertTrue(schema(root))

        self.assertRaises(ValueError, schema, etree.Comment('TEST'))
        self.assertRaises(ValueError, schema, etree.PI('a', 'text'))
        self.assertRaises(ValueError, schema, etree.Entity('text'))

    def test_xmlschema_invalid_schema1(self):
        schema = self.parse('''\
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <element name="a" type="AType"/>
  <xsd:complexType name="AType">
    <xsd:sequence>
      <xsd:element name="b" type="xsd:string" />
    </xsd:sequence>
  </xsd:complexType>
</xsd:schema>
''')
        self.assertRaises(etree.XMLSchemaParseError,
                          etree.XMLSchema, schema)

    def test_xmlschema_invalid_schema2(self):
        schema = self.parse('<test/>')
        self.assertRaises(etree.XMLSchemaParseError,
                          etree.XMLSchema, schema)

    def test_xmlschema_file(self):
        # this will only work if we access the file through path or
        # file object..
        f = open(fileInTestDir('test.xsd'), 'rb')
        try:
            schema = etree.XMLSchema(file=f)
        finally:
            f.close()
        tree_valid = self.parse('<a><b></b></a>')
        self.assertTrue(schema.validate(tree_valid))

    def test_xmlschema_import_file(self):
        # this will only work if we access the file through path or
        # file object..
        schema = etree.XMLSchema(file=fileInTestDir('test_import.xsd'))
        tree_valid = self.parse(
            '<a:x xmlns:a="http://codespeak.net/lxml/schema/ns1"><b></b></a:x>')
        self.assertTrue(schema.validate(tree_valid))

    def test_xmlschema_shortcut(self):
        tree_valid = self.parse('<a><b></b></a>')
        tree_invalid = self.parse('<a><c></c></a>')
        schema = self.parse('''\
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="a" type="AType"/>
  <xsd:complexType name="AType">
    <xsd:sequence>
      <xsd:element name="b" type="xsd:string" />
    </xsd:sequence>
  </xsd:complexType>
</xsd:schema>
''')
        self.assertTrue(tree_valid.xmlschema(schema))
        self.assertFalse(tree_invalid.xmlschema(schema))


class ETreeXMLSchemaResolversTestCase(HelperTestCase):
    resolver_schema_int = BytesIO("""\
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:etype="http://codespeak.net/lxml/test/external"
    targetNamespace="http://codespeak.net/lxml/test/internal">
        <xsd:import namespace="http://codespeak.net/lxml/test/external" schemaLocation="XXX.xsd" />
        <xsd:element name="a" type="etype:AType"/>
</xsd:schema>""")

    resolver_schema_int2 = BytesIO("""\
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:etype="http://codespeak.net/lxml/test/external"
    targetNamespace="http://codespeak.net/lxml/test/internal">
        <xsd:import namespace="http://codespeak.net/lxml/test/external" schemaLocation="YYY.xsd" />
        <xsd:element name="a" type="etype:AType"/>
</xsd:schema>""")

    resolver_schema_ext = """\
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    targetNamespace="http://codespeak.net/lxml/test/external">
    <xsd:complexType name="AType">
      <xsd:sequence><xsd:element name="b" type="xsd:string" minOccurs="0" maxOccurs="unbounded" /></xsd:sequence>
    </xsd:complexType>
</xsd:schema>""" 

    class simple_resolver(etree.Resolver):
        def __init__(self, schema):
            self.schema = schema

        def resolve(self, url, id, context):
            assert url == 'XXX.xsd'
            return self.resolve_string(self.schema, context)

    # tests:

    def test_xmlschema_resolvers(self):
        # test that resolvers work with schema.
        parser = etree.XMLParser()
        parser.resolvers.add(self.simple_resolver(self.resolver_schema_ext))
        schema_doc = etree.parse(self.resolver_schema_int, parser = parser)
        schema = etree.XMLSchema(schema_doc)

    def test_xmlschema_resolvers_root(self):
        # test that the default resolver will get called if there's no
        # specific parser resolver.
        root_resolver = self.simple_resolver(self.resolver_schema_ext)
        etree.get_default_parser().resolvers.add(root_resolver)
        schema_doc = etree.parse(self.resolver_schema_int)
        schema = etree.XMLSchema(schema_doc)
        etree.get_default_parser().resolvers.remove(root_resolver)

    def test_xmlschema_resolvers_noroot(self):
        # test that the default resolver will not get called when a
        # more specific resolver is registered.

        class res_root(etree.Resolver):
            def resolve(self, url, id, context):
                assert False
                return None

        root_resolver = res_root()
        etree.get_default_parser().resolvers.add(root_resolver)

        parser = etree.XMLParser()
        parser.resolvers.add(self.simple_resolver(self.resolver_schema_ext))

        schema_doc = etree.parse(self.resolver_schema_int, parser = parser)
        schema = etree.XMLSchema(schema_doc)
        etree.get_default_parser().resolvers.remove(root_resolver)

    def test_xmlschema_nested_resolvers(self):
        # test that resolvers work in a nested fashion.

        resolver_schema = self.resolver_schema_ext

        class res_nested(etree.Resolver):
            def __init__(self, ext_schema):
                self.ext_schema = ext_schema

            def resolve(self, url, id, context):
                assert url == 'YYY.xsd'
                return self.resolve_string(self.ext_schema, context)

        class res(etree.Resolver):
            def __init__(self, ext_schema_1, ext_schema_2):
                self.ext_schema_1 = ext_schema_1
                self.ext_schema_2 = ext_schema_2

            def resolve(self, url, id, context):
                assert url == 'XXX.xsd'

                new_parser = etree.XMLParser()
                new_parser.resolvers.add(res_nested(self.ext_schema_2))
                new_schema_doc = etree.parse(self.ext_schema_1, parser = new_parser)
                new_schema = etree.XMLSchema(new_schema_doc)

                return self.resolve_string(resolver_schema, context)

        parser = etree.XMLParser()
        parser.resolvers.add(res(self.resolver_schema_int2, self.resolver_schema_ext))
        schema_doc = etree.parse(self.resolver_schema_int, parser = parser)
        schema = etree.XMLSchema(schema_doc)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeXMLSchemaTestCase)])
    suite.addTests([unittest.makeSuite(ETreeXMLSchemaResolversTestCase)])
    suite.addTests(
        [make_doctest('../../../doc/validation.txt')])
    return suite


if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
