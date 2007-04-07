# -*- coding: utf-8 -*-

"""
Tests specific to the lxml.objectify API
"""


import unittest, operator

from common_imports import etree, StringIO, HelperTestCase, fileInTestDir
from common_imports import SillyFileLike, canonicalize, doctest
from common_imports import itemgetter

from lxml import objectify

xml_str = '''\
<obj:root xmlns:obj="objectified" xmlns:other="otherNS">
  <obj:c1 a1="A1" a2="A2" other:a3="A3">
    <obj:c2>0</obj:c2>
    <obj:c2>1</obj:c2>
    <obj:c2>2</obj:c2>
    <other:c2>3</other:c2>
    <c2>3</c2>
  </obj:c1>
</obj:root>'''

class ObjectifyTestCase(HelperTestCase):
    """Test cases for lxml.objectify
    """
    etree = etree

    def XML(self, xml):
        return self.etree.XML(xml, self.parser)

    def setUp(self):
        self.parser = self.etree.XMLParser(remove_blank_text=True)
        lookup = etree.ElementNamespaceClassLookup(
            objectify.ObjectifyElementClassLookup() )
        self.parser.setElementClassLookup(lookup)

        self.Element = self.parser.makeelement

        ns = self.etree.Namespace("otherNS")
        ns[None] = self.etree.ElementBase

    def tearDown(self):
        self.etree.Namespace("otherNS").clear()
        objectify.setPytypeAttributeTag()

    def test_root(self):
        root = self.Element("test")
        self.assert_(isinstance(root, objectify.ObjectifiedElement))

    def test_str(self):
        root = self.Element("test")
        self.assertEquals('', str(root))

    def test_child(self):
        root = self.XML(xml_str)
        self.assertEquals("0", root.c1.c2.text)

    def test_countchildren(self):
        root = self.XML(xml_str)
        self.assertEquals(1, root.countchildren())
        self.assertEquals(5, root.c1.countchildren())

    def test_child_getattr(self):
        root = self.XML(xml_str)
        self.assertEquals("0", getattr(root.c1, "{objectified}c2").text)
        self.assertEquals("3", getattr(root.c1, "{otherNS}c2").text)

    def test_child_nonexistant(self):
        root = self.XML(xml_str)
        self.assertRaises(AttributeError, getattr, root.c1, "NOT_THERE")
        self.assertRaises(AttributeError, getattr, root.c1, "{unknownNS}c2")

    def test_addattr(self):
        root = self.XML(xml_str)
        self.assertEquals(1, len(root.c1))
        root.addattr("c1", "test")
        self.assertEquals(2, len(root.c1))
        self.assertEquals("test", root.c1[1].text)

    def test_addattr_element(self):
        root = self.XML(xml_str)
        self.assertEquals(1, len(root.c1))

        new_el = self.Element("test", myattr="5")
        root.addattr("c1", new_el)
        self.assertEquals(2, len(root.c1))
        self.assertEquals(None, root.c1[0].get("myattr"))
        self.assertEquals("5",  root.c1[1].get("myattr"))

    def test_addattr_list(self):
        root = self.XML(xml_str)
        self.assertEquals(1, len(root.c1))

        new_el = self.Element("test")
        self.etree.SubElement(new_el, "a", myattr="A")
        self.etree.SubElement(new_el, "a", myattr="B")

        root.addattr("c1", list(new_el.a))
        self.assertEquals(3, len(root.c1))
        self.assertEquals(None, root.c1[0].get("myattr"))
        self.assertEquals("A",  root.c1[1].get("myattr"))
        self.assertEquals("B",  root.c1[2].get("myattr"))

    def test_child_addattr(self):
        root = self.XML(xml_str)
        self.assertEquals(3, len(root.c1.c2))
        root.c1.addattr("c2", 3)
        self.assertEquals(4, len(root.c1.c2))
        self.assertEquals("3", root.c1.c2[3].text)

    def test_child_index(self):
        root = self.XML(xml_str)
        self.assertEquals("0", root.c1.c2[0].text)
        self.assertEquals("1", root.c1.c2[1].text)
        self.assertEquals("2", root.c1.c2[2].text)
        self.assertRaises(IndexError, itemgetter(3), root.c1.c2)

    def test_child_index_neg(self):
        root = self.XML(xml_str)
        self.assertEquals("0", root.c1.c2[0].text)
        self.assertEquals("0", root.c1.c2[-3].text)
        self.assertEquals("1", root.c1.c2[-2].text)
        self.assertEquals("2", root.c1.c2[-1].text)
        self.assertRaises(IndexError, itemgetter(-4), root.c1.c2)

    def test_child_len(self):
        root = self.XML(xml_str)
        self.assertEquals(1, len(root))
        self.assertEquals(1, len(root.c1))
        self.assertEquals(3, len(root.c1.c2))

    def test_child_iter(self):
        root = self.XML(xml_str)
        self.assertEquals([root],
                          list(iter(root)))
        self.assertEquals([root.c1],
                          list(iter(root.c1)))
        self.assertEquals([root.c1.c2[0], root.c1.c2[1], root.c1.c2[2]],
                          list(iter((root.c1.c2))))

    def test_class_lookup(self):
        root = self.XML(xml_str)
        self.assert_(isinstance(root.c1.c2, objectify.ObjectifiedElement))
        self.assertFalse(isinstance(getattr(root.c1, "{otherNS}c2"),
                                    objectify.ObjectifiedElement))

    def test_dir(self):
        root = self.XML(xml_str)
        dir_c1 = dir(objectify.ObjectifiedElement) + ['c1']
        dir_c1.sort()
        dir_c2 = dir(objectify.ObjectifiedElement) + ['c2']
        dir_c2.sort()

        self.assertEquals(dir_c1, dir(root))
        self.assertEquals(dir_c2, dir(root.c1))

    def test_vars(self):
        root = self.XML(xml_str)
        self.assertEquals({'c1' : root.c1},    vars(root))
        self.assertEquals({'c2' : root.c1.c2}, vars(root.c1))

    def test_child_set_ro(self):
        root = self.XML(xml_str)
        self.assertRaises(TypeError, setattr, root.c1.c2, 'text',  "test")
        self.assertRaises(TypeError, setattr, root.c1.c2, 'pyval', "test")

    def test_setslice(self):
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("root")
        root.c = ["c1", "c2"]

        c1 = root.c[0]
        c2 = root.c[1]

        self.assertEquals([c1,c2], list(root.c))
        self.assertEquals(["c1", "c2"],
                          [ c.text for c in root.c ])

        root2 = Element("root2")
        root2.el = [ "test", "test" ]
        self.assertEquals(["test", "test"],
                          [ el.text for el in root2.el ])

        root.c = [ root2.el, root2.el ]
        self.assertEquals(["test", "test"],
                          [ c.text for c in root.c ])
        self.assertEquals(["test", "test"],
                          [ el.text for el in root2.el ])

        root.c[:] = [ c1, c2, c2, c1 ]
        self.assertEquals(["c1", "c2", "c2", "c1"],
                          [ c.text for c in root.c ])

    def test_set_string(self):
        # make sure strings are not handled as sequences
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("root")
        root.c = "TEST"
        self.assertEquals(["TEST"],
                          [ c.text for c in root.c ])

    def test_setitem_string(self):
        # make sure strings are set as children
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("root")
        root["c"] = "TEST"
        self.assertEquals(["TEST"],
                          [ c.text for c in root.c ])

    def test_setitem_string_special(self):
        # make sure 'text' etc. are set as children
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("root")

        root["text"] = "TEST"
        self.assertEquals(["TEST"],
                          [ c.text for c in root["text"] ])

        root["tail"] = "TEST"
        self.assertEquals(["TEST"],
                          [ c.text for c in root["tail"] ])

        root["pyval"] = "TEST"
        self.assertEquals(["TEST"],
                          [ c.text for c in root["pyval"] ])

        root["tag"] = "TEST"
        self.assertEquals(["TEST"],
                          [ c.text for c in root["tag"] ])

    def test_findall(self):
        XML = self.XML
        root = XML('<a><b><c/></b><b/><c><b/></c></a>')
        self.assertEquals(1, len(root.findall("c")))
        self.assertEquals(2, len(root.findall(".//c")))
        self.assertEquals(3, len(root.findall(".//b")))
        self.assert_(root.findall(".//b")[1] is root.getchildren()[1])

    def test_findall_ns(self):
        XML = self.XML
        root = XML('<a xmlns:x="X" xmlns:y="Y"><x:b><c/></x:b><b/><c><x:b/><b/></c><b/></a>')
        self.assertEquals(2, len(root.findall(".//{X}b")))
        self.assertEquals(3, len(root.findall(".//b")))
        self.assertEquals(2, len(root.findall("b")))

    def test_build_tree(self):
        root = self.Element('root')
        root.a = 5
        root.b = 6
        self.assert_(isinstance(root, objectify.ObjectifiedElement))
        self.assert_(isinstance(root.a, objectify.IntElement))
        self.assert_(isinstance(root.b, objectify.IntElement))

    def test_type_none(self):
        Element = self.Element
        SubElement = self.etree.SubElement

        nil_attr = "{http://www.w3.org/2001/XMLSchema-instance}nil"
        root = Element("{objectified}root")
        SubElement(root, "{objectified}none")
        SubElement(root, "{objectified}none", {nil_attr : "true"})
        self.assertFalse(isinstance(root.none, objectify.NoneElement))
        self.assertFalse(isinstance(root.none[0], objectify.NoneElement))
        self.assert_(isinstance(root.none[1], objectify.NoneElement))
        self.assertEquals(root.none[1], None)
        self.assertFalse(root.none[1])

    def test_data_element_none(self):
        value = objectify.DataElement(None)
        self.assert_(isinstance(value, objectify.NoneElement))
        self.assertEquals(value, None)

    def test_type_bool(self):
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("{objectified}root")
        root.none = 'true'
        self.assert_(isinstance(root.none, objectify.BoolElement))

    def test_data_element_bool(self):
        value = objectify.DataElement(True)
        self.assert_(isinstance(value, objectify.BoolElement))
        self.assertEquals(value, True)

        value = objectify.DataElement(False)
        self.assert_(isinstance(value, objectify.BoolElement))
        self.assertEquals(value, False)

    def test_type_str(self):
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("{objectified}root")
        root.none = "test"
        self.assert_(isinstance(root.none, objectify.StringElement))

    def test_type_str_mul(self):
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("{objectified}root")
        root.none = "test"

        self.assertEquals("test" * 5, root.none * 5)
        self.assertEquals(5 * "test", 5 * root.none)

        self.assertRaises(TypeError, operator.mul, root.none, "honk")
        self.assertRaises(TypeError, operator.mul, "honk", root.none)

    def test_type_str_add(self):
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("{objectified}root")
        root.none = "test"

        s = "toast"
        self.assertEquals("test" + s, root.none + s)
        self.assertEquals(s + "test", s + root.none)

    def test_data_element_str(self):
        value = objectify.DataElement("test")
        self.assert_(isinstance(value, objectify.StringElement))
        self.assertEquals(value, "test")

    def test_type_int(self):
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("{objectified}root")
        root.none = 5
        self.assert_(isinstance(root.none, objectify.IntElement))

    def test_data_element_int(self):
        value = objectify.DataElement(5)
        self.assert_(isinstance(value, objectify.IntElement))
        self.assertEquals(value, 5)

    def test_type_float(self):
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("{objectified}root")
        root.none = 5.5
        self.assert_(isinstance(root.none, objectify.FloatElement))

    def test_data_element_float(self):
        value = objectify.DataElement(5.5)
        self.assert_(isinstance(value, objectify.FloatElement))
        self.assertEquals(value, 5.5)

    def test_schema_types(self):
        XML = self.XML
        root = XML('''\
        <root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <a xsi:type="integer">5</a>
          <a xsi:type="string">5</a>
          <a xsi:type="float">5</a>
        </root>
        ''')

        self.assert_(isinstance(root.a[0], objectify.IntElement))
        self.assertEquals(5, root.a[0])

        self.assert_(isinstance(root.a[1], objectify.StringElement))
        self.assertEquals("5", root.a[1])

        self.assert_(isinstance(root.a[2], objectify.FloatElement))
        self.assertEquals(5.0, root.a[2])

    def test_type_str_sequence(self):
        XML = self.XML
        root = XML(u'<root><b>why</b><b>try</b></root>')
        strs = [ str(s) for s in root.b ]
        self.assertEquals(["why", "try"],
                          strs)

    def test_type_str_cmp(self):
        XML = self.XML
        root = XML(u'<root><b>test</b><b>taste</b></root>')
        self.assertFalse(root.b[0] <  root.b[1])
        self.assertFalse(root.b[0] <= root.b[1])
        self.assertFalse(root.b[0] == root.b[1])

        self.assert_(root.b[0] != root.b[1])
        self.assert_(root.b[0] >= root.b[1])
        self.assert_(root.b[0] >  root.b[1])

        self.assertEquals(root.b[0], "test")
        self.assertEquals("test", root.b[0])
        self.assert_(root.b[0] >  5)
        self.assert_(5 < root.b[0])

        root.b = "test"
        self.assert_(root.b)
        root.b = ""
        self.assertFalse(root.b)

    def test_type_int_cmp(self):
        XML = self.XML
        root = XML(u'<root><b>5</b><b>6</b></root>')
        self.assert_(root.b[0] <  root.b[1])
        self.assert_(root.b[0] <= root.b[1])
        self.assert_(root.b[0] != root.b[1])

        self.assertFalse(root.b[0] == root.b[1])
        self.assertFalse(root.b[0] >= root.b[1])
        self.assertFalse(root.b[0] >  root.b[1])

        self.assertEquals(root.b[0], 5)
        self.assertEquals(5, root.b[0])
        self.assert_(root.b[0] <  "5")
        self.assert_("5" > root.b[0])

        root.b = 5
        self.assert_(root.b)
        root.b = 0
        self.assertFalse(root.b)

    def test_type_bool_cmp(self):
        XML = self.XML
        root = XML(u'<root><b>false</b><b>true</b></root>')
        self.assert_(root.b[0] <  root.b[1])
        self.assert_(root.b[0] <= root.b[1])
        self.assert_(root.b[0] != root.b[1])

        self.assertFalse(root.b[0] == root.b[1])
        self.assertFalse(root.b[0] >= root.b[1])
        self.assertFalse(root.b[0] >  root.b[1])

        self.assertFalse(root.b[0])
        self.assert_(root.b[1])

        self.assertEquals(root.b[0], False)
        self.assertEquals(False, root.b[0])
        self.assert_(root.b[0] <  5)
        self.assert_(5 > root.b[0])

        root.b = True
        self.assert_(root.b)
        root.b = False
        self.assertFalse(root.b)

    def test_type_annotation(self):
        XML = self.XML
        root = XML(u'''\
        <a xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <b>5</b>
          <b>test</b>
          <c>1.1</c>
          <c>\uF8D2</c>
          <x>true</x>
          <n xsi:nil="true" />
          <n></n>
          <b xsi:type="double">5</b>
        </a>
        ''')
        objectify.annotate(root)

        child_types = [ c.get(objectify.PYTYPE_ATTRIBUTE)
                        for c in root.iterchildren() ]
        self.assertEquals("int",   child_types[0])
        self.assertEquals("str",   child_types[1])
        self.assertEquals("float", child_types[2])
        self.assertEquals("str",   child_types[3])
        self.assertEquals("bool",  child_types[4])
        self.assertEquals("none",  child_types[5])
        self.assertEquals(None,    child_types[6])
        self.assertEquals("float", child_types[7])

    def test_change_pytype_attribute(self):
        XML = self.XML

        xml = u'''\
        <a xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <b>5</b>
          <b>test</b>
          <c>1.1</c>
          <c>\uF8D2</c>
          <x>true</x>
          <n xsi:nil="true" />
          <n></n>
          <b xsi:type="double">5</b>
        </a>
        '''

        pytype_ns, pytype_name = objectify.PYTYPE_ATTRIBUTE[1:].split('}')
        objectify.setPytypeAttributeTag("{TEST}test")

        root = XML(xml)
        objectify.annotate(root)

        attribs = root.xpath("//@py:%s" % pytype_name, {"py" : pytype_ns})
        self.assertEquals(0, len(attribs))
        attribs = root.xpath("//@py:test", {"py" : "TEST"})
        self.assertEquals(7, len(attribs))

        objectify.setPytypeAttributeTag()
        pytype_ns, pytype_name = objectify.PYTYPE_ATTRIBUTE[1:].split('}')

        self.assertNotEqual("test", pytype_ns.lower())
        self.assertNotEqual("test", pytype_name.lower())

        root = XML(xml)
        attribs = root.xpath("//@py:%s" % pytype_name, {"py" : pytype_ns})
        self.assertEquals(0, len(attribs))

        objectify.annotate(root)
        attribs = root.xpath("//@py:%s" % pytype_name, {"py" : pytype_ns})
        self.assertEquals(7, len(attribs))

    def test_registered_types(self):
        orig_types = objectify.getRegisteredTypes()

        try:
            orig_types[0].unregister()
            self.assertEquals(orig_types[1:], objectify.getRegisteredTypes())

            class NewType(objectify.ObjectifiedDataElement):
                pass

            def checkMyType(s):
                return True

            pytype = objectify.PyType("mytype", checkMyType, NewType)
            pytype.register()
            self.assert_(pytype in objectify.getRegisteredTypes())
            pytype.unregister()

            pytype.register(before = [objectify.getRegisteredTypes()[0].name])
            self.assertEquals(pytype, objectify.getRegisteredTypes()[0])
            pytype.unregister()

            pytype.register(after = [objectify.getRegisteredTypes()[0].name])
            self.assertNotEqual(pytype, objectify.getRegisteredTypes()[0])
            pytype.unregister()

            self.assertRaises(ValueError, pytype.register,
                              before = [objectify.getRegisteredTypes()[0].name],
                              after  = [objectify.getRegisteredTypes()[1].name])

        finally:
            for pytype in objectify.getRegisteredTypes():
                pytype.unregister()
            for pytype in orig_types:
                pytype.register()

    def test_object_path(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( "root.c1.c2" )
        self.assertEquals(root.c1.c2.text, path.find(root).text)
        self.assertEquals(root.c1.c2.text, path(root).text)

    def test_object_path_list(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( ['root', 'c1', 'c2'] )
        self.assertEquals(root.c1.c2.text, path.find(root).text)
        self.assertEquals(root.c1.c2.text, path(root).text)

    def test_object_path_fail(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( "root.c1.c99" )
        self.assertRaises(AttributeError, path, root)
        self.assertEquals(None, path(root, None))

    def test_object_path_syntax(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath("root .    {objectified}c1.   c2")
        self.assertEquals(root.c1.c2.text, path(root).text)

        path = objectify.ObjectPath("   root.{objectified}  c1.c2  [ 0 ]   ")
        self.assertEquals(root.c1.c2.text, path(root).text)

    def test_object_path_hasattr(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( "root" )
        self.assert_(path.hasattr(root))
        path = objectify.ObjectPath( "root.c1" )
        self.assert_(path.hasattr(root))
        path = objectify.ObjectPath( "root.c1.c2" )
        self.assert_(path.hasattr(root))
        path = objectify.ObjectPath( "root.c1.{otherNS}c2" )
        self.assert_(path.hasattr(root))
        path = objectify.ObjectPath( "root.c1.c2[1]" )
        self.assert_(path.hasattr(root))
        path = objectify.ObjectPath( "root.c1.c2[2]" )
        self.assert_(path.hasattr(root))
        path = objectify.ObjectPath( "root.c1.c2[3]" )
        self.assertFalse(path.hasattr(root))
        path = objectify.ObjectPath( "root.c1[1].c2" )
        self.assertFalse(path.hasattr(root))

    def test_object_path_dot(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( "." )
        self.assertEquals(root.c1.c2.text, path(root).c1.c2.text)

    def test_object_path_dot_list(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( [''] )
        self.assertEquals(root.c1.c2.text, path(root).c1.c2.text)

    def test_object_path_dot_root(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( ".c1.c2" )
        self.assertEquals(root.c1.c2.text, path(root).text)

    def test_object_path_dot_root_list(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( ['', 'c1', 'c2'] )
        self.assertEquals(root.c1.c2.text, path(root).text)

    def test_object_path_index(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( "root.c1[0].c2[0]" )
        self.assertEquals(root.c1.c2.text, path(root).text)

        path = objectify.ObjectPath( "root.c1[0].c2" )
        self.assertEquals(root.c1.c2.text, path(root).text)

        path = objectify.ObjectPath( "root.c1[0].c2[1]" )
        self.assertEquals(root.c1.c2[1].text, path(root).text)

        path = objectify.ObjectPath( "root.c1.c2[2]" )
        self.assertEquals(root.c1.c2[2].text, path(root).text)

        path = objectify.ObjectPath( "root.c1.c2[-1]" )
        self.assertEquals(root.c1.c2[-1].text, path(root).text)

        path = objectify.ObjectPath( "root.c1.c2[-3]" )
        self.assertEquals(root.c1.c2[-3].text, path(root).text)

    def test_object_path_index_list(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( ['root', 'c1[0]', 'c2[0]'] )
        self.assertEquals(root.c1.c2.text, path(root).text)

        path = objectify.ObjectPath( ['root', 'c1[0]', 'c2[2]'] )
        self.assertEquals(root.c1.c2[2].text, path(root).text)

        path = objectify.ObjectPath( ['root', 'c1', 'c2[2]'] )
        self.assertEquals(root.c1.c2[2].text, path(root).text)

        path = objectify.ObjectPath( ['root', 'c1', 'c2[-1]'] )
        self.assertEquals(root.c1.c2[-1].text, path(root).text)

        path = objectify.ObjectPath( ['root', 'c1', 'c2[-3]'] )
        self.assertEquals(root.c1.c2[-3].text, path(root).text)

    def test_object_path_index_fail_parse(self):
        self.assertRaises(ValueError, objectify.ObjectPath,
                          "root.c1[0].c2[-1-2]")
        self.assertRaises(ValueError, objectify.ObjectPath,
                          ['root', 'c1[0]', 'c2[-1-2]'])

        self.assertRaises(ValueError, objectify.ObjectPath,
                          "root[2].c1.c2")
        self.assertRaises(ValueError, objectify.ObjectPath,
                          ['root[2]', 'c1', 'c2'])

        self.assertRaises(ValueError, objectify.ObjectPath,
                          [])
        self.assertRaises(ValueError, objectify.ObjectPath,
                          ['', '', ''])

    def test_object_path_index_fail_lookup(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath("root.c1[9999].c2")
        self.assertRaises(AttributeError, path, root)

        path = objectify.ObjectPath("root.c1[0].c2[9999]")
        self.assertRaises(AttributeError, path, root)

        path = objectify.ObjectPath(".c1[9999].c2[0]")
        self.assertRaises(AttributeError, path, root)

        path = objectify.ObjectPath("root.c1[-2].c2")
        self.assertRaises(AttributeError, path, root)

        path = objectify.ObjectPath("root.c1[0].c2[-4]")
        self.assertRaises(AttributeError, path, root)

    def test_object_path_ns(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( "{objectified}root.c1.c2" )
        self.assertEquals(root.c1.c2.text, path.find(root).text)
        path = objectify.ObjectPath( "{objectified}root.{objectified}c1.c2" )
        self.assertEquals(root.c1.c2.text, path.find(root).text)
        path = objectify.ObjectPath( "root.{objectified}c1.{objectified}c2" )
        self.assertEquals(root.c1.c2.text, path.find(root).text)
        path = objectify.ObjectPath( "root.c1.{objectified}c2" )
        self.assertEquals(root.c1.c2.text, path.find(root).text)
        path = objectify.ObjectPath( "root.c1.{otherNS}c2" )
        self.assertEquals(getattr(root.c1, '{otherNS}c2').text,
                          path.find(root).text)

    def test_object_path_ns_list(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( ['{objectified}root', 'c1', 'c2'] )
        self.assertEquals(root.c1.c2.text, path.find(root).text)
        path = objectify.ObjectPath( ['{objectified}root', '{objectified}c1', 'c2'] )
        self.assertEquals(root.c1.c2.text, path.find(root).text)
        path = objectify.ObjectPath( ['root', '{objectified}c1', '{objectified}c2'] )
        self.assertEquals(root.c1.c2.text, path.find(root).text)
        path = objectify.ObjectPath( ['root', '{objectified}c1', '{objectified}c2[2]'] )
        self.assertEquals(root.c1.c2[2].text, path.find(root).text)
        path = objectify.ObjectPath( ['root', 'c1', '{objectified}c2'] )
        self.assertEquals(root.c1.c2.text, path.find(root).text)
        path = objectify.ObjectPath( ['root', 'c1', '{objectified}c2[2]'] )
        self.assertEquals(root.c1.c2[2].text, path.find(root).text)
        path = objectify.ObjectPath( ['root', 'c1', '{otherNS}c2'] )
        self.assertEquals(getattr(root.c1, '{otherNS}c2').text,
                          path.find(root).text)

    def test_object_path_set(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( "root.c1.c2" )
        self.assertEquals(root.c1.c2.text, path.find(root).text)
        self.assertEquals("1", root.c1.c2[1].text)

        new_value = "my new value"
        path.setattr(root, new_value)

        self.assertEquals(new_value, root.c1.c2.text)
        self.assertEquals(new_value, path(root).text)
        self.assertEquals("1", root.c1.c2[1].text)

    def test_object_path_set_element(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( "root.c1.c2" )
        self.assertEquals(root.c1.c2.text, path.find(root).text)
        self.assertEquals("1", root.c1.c2[1].text)

        new_el = self.Element("{objectified}test")
        etree.SubElement(new_el, "{objectified}sub", myattr="ATTR").a = "TEST"
        path.setattr(root, new_el.sub)

        self.assertEquals("ATTR", root.c1.c2.get("myattr"))
        self.assertEquals("TEST", root.c1.c2.a.text)
        self.assertEquals("TEST", path(root).a.text)
        self.assertEquals("1", root.c1.c2[1].text)

    def test_object_path_set_create(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( "root.c1.c99" )
        self.assertRaises(AttributeError, path.find, root)

        new_value = "my new value"
        path.setattr(root, new_value)

        self.assertEquals(1, len(root.c1.c99))
        self.assertEquals(new_value, root.c1.c99.text)
        self.assertEquals(new_value, path(root).text)

    def test_object_path_set_create_element(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( "root.c1.c99" )
        self.assertRaises(AttributeError, path.find, root)

        new_el = self.Element("{objectified}test")
        etree.SubElement(new_el, "{objectified}sub", myattr="ATTR").a = "TEST"
        path.setattr(root, new_el.sub)

        self.assertEquals(1, len(root.c1.c99))
        self.assertEquals("ATTR", root.c1.c99.get("myattr"))
        self.assertEquals("TEST", root.c1.c99.a.text)
        self.assertEquals("TEST", path(root).a.text)

    def test_object_path_set_create_list(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( "root.c1.c99" )
        self.assertRaises(AttributeError, path.find, root)

        new_el = self.Element("{objectified}test")
        new_el.a = ["TEST1", "TEST2"]
        new_el.a[0].set("myattr", "ATTR1")
        new_el.a[1].set("myattr", "ATTR2")

        path.setattr(root, list(new_el.a))

        self.assertEquals(2, len(root.c1.c99))
        self.assertEquals("ATTR1", root.c1.c99[0].get("myattr"))
        self.assertEquals("TEST1", root.c1.c99[0].text)
        self.assertEquals("ATTR2", root.c1.c99[1].get("myattr"))
        self.assertEquals("TEST2", root.c1.c99[1].text)
        self.assertEquals("TEST1", path(root).text)

    def test_object_path_addattr(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( "root.c1.c2" )
        self.assertEquals(3, len(root.c1.c2))
        path.addattr(root, "test")
        self.assertEquals(4, len(root.c1.c2))
        self.assertEquals(["0", "1", "2", "test"],
                          [el.text for el in root.c1.c2])

    def test_object_path_addattr_element(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( "root.c1.c2" )
        self.assertEquals(3, len(root.c1.c2))

        new_el = self.Element("{objectified}test")
        etree.SubElement(new_el, "{objectified}sub").a = "TEST"

        path.addattr(root, new_el.sub)
        self.assertEquals(4, len(root.c1.c2))
        self.assertEquals("TEST", root.c1.c2[3].a.text)
        self.assertEquals(["0", "1", "2"],
                          [el.text for el in root.c1.c2[:3]])

    def test_object_path_addattr_create(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( "root.c1.c99" )
        self.assertRaises(AttributeError, path.find, root)

        new_value = "my new value"
        path.addattr(root, new_value)

        self.assertEquals(1, len(root.c1.c99))
        self.assertEquals(new_value, root.c1.c99.text)
        self.assertEquals(new_value, path(root).text)

    def test_object_path_addattr_create_element(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( "root.c1.c99" )
        self.assertRaises(AttributeError, path.find, root)

        new_el = self.Element("{objectified}test")
        etree.SubElement(new_el, "{objectified}sub", myattr="ATTR").a = "TEST"

        path.addattr(root, new_el.sub)
        self.assertEquals(1, len(root.c1.c99))
        self.assertEquals("TEST", root.c1.c99.a.text)
        self.assertEquals("TEST", path(root).a.text)
        self.assertEquals("ATTR", root.c1.c99.get("myattr"))

    def test_object_path_addattr_create_list(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( "root.c1.c99" )
        self.assertRaises(AttributeError, path.find, root)

        new_el = self.Element("{objectified}test")
        new_el.a = ["TEST1", "TEST2"]

        self.assertEquals(2, len(new_el.a))

        path.addattr(root, list(new_el.a))
        self.assertEquals(2, len(root.c1.c99))
        self.assertEquals("TEST1", root.c1.c99.text)
        self.assertEquals("TEST2", path(root)[1].text)

    def test_descendant_paths(self):
        root = self.XML(xml_str)
        self.assertEquals(
            ['{objectified}root', '{objectified}root.c1',
             '{objectified}root.c1.c2',
             '{objectified}root.c1.c2[1]', '{objectified}root.c1.c2[2]',
             '{objectified}root.c1.{otherNS}c2', '{objectified}root.c1.{}c2'],
            root.descendantpaths())

    def test_descendant_paths_child(self):
        root = self.XML(xml_str)
        self.assertEquals(
            ['{objectified}c1', '{objectified}c1.c2',
             '{objectified}c1.c2[1]', '{objectified}c1.c2[2]',
             '{objectified}c1.{otherNS}c2', '{objectified}c1.{}c2'],
            root.c1.descendantpaths())

    def test_descendant_paths_prefix(self):
        root = self.XML(xml_str)
        self.assertEquals(
            ['root.{objectified}c1', 'root.{objectified}c1.c2',
             'root.{objectified}c1.c2[1]', 'root.{objectified}c1.c2[2]',
             'root.{objectified}c1.{otherNS}c2',
             'root.{objectified}c1.{}c2'],
            root.c1.descendantpaths('root'))

    def test_pickle(self):
        import pickle

        root = self.XML(xml_str)
        out = StringIO()
        pickle.dump(root, out)

        new_root = pickle.loads(out.getvalue())
        self.assertEquals(
            etree.tostring(new_root),
            etree.tostring(root))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ObjectifyTestCase)])
    suite.addTests(
        [doctest.DocFileSuite('../../../doc/objectify.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
