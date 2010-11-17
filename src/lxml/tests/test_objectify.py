# -*- coding: utf-8 -*-

"""
Tests specific to the lxml.objectify API
"""


import unittest, operator, sys, os.path

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir) # needed for Py3

from common_imports import etree, HelperTestCase, fileInTestDir
from common_imports import SillyFileLike, canonicalize, doctest, make_doctest
from common_imports import _bytes, _str, StringIO, BytesIO

from lxml import objectify

PYTYPE_NAMESPACE = "http://codespeak.net/lxml/objectify/pytype"
XML_SCHEMA_NS = "http://www.w3.org/2001/XMLSchema"
XML_SCHEMA_INSTANCE_NS = "http://www.w3.org/2001/XMLSchema-instance"
XML_SCHEMA_INSTANCE_TYPE_ATTR = "{%s}type" % XML_SCHEMA_INSTANCE_NS
XML_SCHEMA_NIL_ATTR = "{%s}nil" % XML_SCHEMA_INSTANCE_NS
TREE_PYTYPE = "TREE"
DEFAULT_NSMAP = { "py"  : PYTYPE_NAMESPACE,
                  "xsi" : XML_SCHEMA_INSTANCE_NS,
                  "xsd" : XML_SCHEMA_NS}

objectclass2xsitype = {
    # objectify built-in
    objectify.IntElement: ("int", "short", "byte", "unsignedShort",
                           "unsignedByte", "integer", "nonPositiveInteger",
                           "negativeInteger", "long", "nonNegativeInteger",
                           "unsignedLong", "unsignedInt", "positiveInteger",),
    objectify.FloatElement: ("float", "double"),
    objectify.BoolElement: ("boolean",),
    objectify.StringElement: ("string", "normalizedString", "token", "language",
                              "Name", "NCName", "ID", "IDREF", "ENTITY",
                              "NMTOKEN", ),
    # None: xsi:nil="true"
    }

xsitype2objclass = dict([ (v, k) for k in objectclass2xsitype
                          for v in objectclass2xsitype[k] ])

objectclass2pytype = {
    # objectify built-in
    objectify.IntElement: "int",
    objectify.FloatElement: "float",
    objectify.BoolElement: "bool",
    objectify.StringElement: "str",
    # None: xsi:nil="true"
    }

pytype2objclass = dict([ (objectclass2pytype[k], k)
                         for k in objectclass2pytype])

xml_str = '''\
<obj:root xmlns:obj="objectified" xmlns:other="otherNS">
  <obj:c1 a1="A1" a2="A2" other:a3="A3">
    <obj:c2>0</obj:c2>
    <obj:c2>1</obj:c2>
    <obj:c2>2</obj:c2>
    <other:c2>3</other:c2>
    <c2>4</c2>
  </obj:c1>
</obj:root>'''

class ObjectifyTestCase(HelperTestCase):
    """Test cases for lxml.objectify
    """
    etree = etree
    
    def XML(self, xml):
        return self.etree.XML(xml, self.parser)

    def setUp(self):
        super(ObjectifyTestCase, self).setUp()
        self.parser = self.etree.XMLParser(remove_blank_text=True)
        self.lookup = etree.ElementNamespaceClassLookup(
            objectify.ObjectifyElementClassLookup() )
        self.parser.set_element_class_lookup(self.lookup)

        self.Element = self.parser.makeelement

        ns = self.lookup.get_namespace("otherNS")
        ns[None] = self.etree.ElementBase

        self._orig_types = objectify.getRegisteredTypes()

    def tearDown(self):
        self.lookup.get_namespace("otherNS").clear()
        objectify.set_pytype_attribute_tag()
        del self.lookup
        del self.parser

        for pytype in objectify.getRegisteredTypes():
            pytype.unregister()
        for pytype in self._orig_types:
            pytype.register()
        del self._orig_types

        super(ObjectifyTestCase, self).tearDown()


    def test_element_nsmap_default(self):
        elt = objectify.Element("test")
        self.assertEquals(elt.nsmap, DEFAULT_NSMAP)

    def test_element_nsmap_empty(self):
        nsmap = {}
        elt = objectify.Element("test", nsmap=nsmap)
        self.assertEquals(list(elt.nsmap.values()), [PYTYPE_NAMESPACE])

    def test_element_nsmap_custom_prefixes(self):
        nsmap = {"mypy": PYTYPE_NAMESPACE,
                 "myxsi": XML_SCHEMA_INSTANCE_NS,
                 "myxsd": XML_SCHEMA_NS}
        elt = objectify.Element("test", nsmap=nsmap)
        self.assertEquals(elt.nsmap, nsmap)
        
    def test_element_nsmap_custom(self):
        nsmap = {"my": "someNS",
                 "myother": "someOtherNS",
                 "myxsd": XML_SCHEMA_NS}
        elt = objectify.Element("test", nsmap=nsmap)
        self.assert_(PYTYPE_NAMESPACE in elt.nsmap.values())
        for prefix, ns in nsmap.items():
            self.assert_(prefix in elt.nsmap)
            self.assertEquals(nsmap[prefix], elt.nsmap[prefix]) 
        
    def test_sub_element_nsmap_default(self):
        root = objectify.Element("root")
        root.sub = objectify.Element("test")
        self.assertEquals(root.sub.nsmap, DEFAULT_NSMAP)

    def test_sub_element_nsmap_empty(self):
        root = objectify.Element("root")
        nsmap = {}
        root.sub = objectify.Element("test", nsmap=nsmap)
        self.assertEquals(root.sub.nsmap, DEFAULT_NSMAP)

    def test_sub_element_nsmap_custom_prefixes(self):
        root = objectify.Element("root")
        nsmap = {"mypy": PYTYPE_NAMESPACE,
                 "myxsi": XML_SCHEMA_INSTANCE_NS,
                 "myxsd": XML_SCHEMA_NS}
        root.sub = objectify.Element("test", nsmap=nsmap)
        self.assertEquals(root.sub.nsmap, DEFAULT_NSMAP)
        
    def test_sub_element_nsmap_custom(self):
        root = objectify.Element("root")
        nsmap = {"my": "someNS",
                 "myother": "someOtherNS",
                 "myxsd": XML_SCHEMA_NS,}
        root.sub = objectify.Element("test", nsmap=nsmap)
        expected = nsmap.copy()
        del expected["myxsd"]
        expected.update(DEFAULT_NSMAP)
        self.assertEquals(root.sub.nsmap, expected) 
        
    def test_data_element_nsmap_default(self):
        value = objectify.DataElement("test this")
        self.assertEquals(value.nsmap, DEFAULT_NSMAP)

    def test_data_element_nsmap_empty(self):
        nsmap = {}
        value = objectify.DataElement("test this", nsmap=nsmap)
        self.assertEquals(list(value.nsmap.values()), [PYTYPE_NAMESPACE])

    def test_data_element_nsmap_custom_prefixes(self):
        nsmap = {"mypy": PYTYPE_NAMESPACE,
                 "myxsi": XML_SCHEMA_INSTANCE_NS,
                 "myxsd": XML_SCHEMA_NS}
        value = objectify.DataElement("test this", nsmap=nsmap)
        self.assertEquals(value.nsmap, nsmap)
        
    def test_data_element_nsmap_custom(self):
        nsmap = {"my": "someNS",
                 "myother": "someOtherNS",
                 "myxsd": XML_SCHEMA_NS,}
        value = objectify.DataElement("test", nsmap=nsmap)
        self.assert_(PYTYPE_NAMESPACE in value.nsmap.values())
        for prefix, ns in nsmap.items():
            self.assert_(prefix in value.nsmap)
            self.assertEquals(nsmap[prefix], value.nsmap[prefix]) 
        
    def test_sub_data_element_nsmap_default(self):
        root = objectify.Element("root")
        root.value = objectify.DataElement("test this")
        self.assertEquals(root.value.nsmap, DEFAULT_NSMAP)

    def test_sub_data_element_nsmap_empty(self):
        root = objectify.Element("root")
        nsmap = {}
        root.value = objectify.DataElement("test this", nsmap=nsmap)
        self.assertEquals(root.value.nsmap, DEFAULT_NSMAP)

    def test_sub_data_element_nsmap_custom_prefixes(self):
        root = objectify.Element("root")
        nsmap = {"mypy": PYTYPE_NAMESPACE,
                 "myxsi": XML_SCHEMA_INSTANCE_NS,
                 "myxsd": XML_SCHEMA_NS}
        root.value = objectify.DataElement("test this", nsmap=nsmap)
        self.assertEquals(root.value.nsmap, DEFAULT_NSMAP)
        
    def test_sub_data_element_nsmap_custom(self):
        root = objectify.Element("root")
        nsmap = {"my": "someNS",
                 "myother": "someOtherNS",
                 "myxsd": XML_SCHEMA_NS}
        root.value = objectify.DataElement("test", nsmap=nsmap)
        expected = nsmap.copy()
        del expected["myxsd"]
        expected.update(DEFAULT_NSMAP)
        self.assertEquals(root.value.nsmap, expected) 
        
    def test_data_element_attrib_attributes_precedence(self):
        # keyword arguments override attrib entries
        value = objectify.DataElement(23, _pytype="str", _xsi="foobar",
                                      attrib={"gnu": "muh", "cat": "meeow",
                                              "dog": "wuff"},
                                      bird="tchilp", dog="grrr")
        self.assertEquals(value.get("gnu"), "muh")
        self.assertEquals(value.get("cat"), "meeow")
        self.assertEquals(value.get("dog"), "grrr")
        self.assertEquals(value.get("bird"), "tchilp")
        
    def test_data_element_data_element_arg(self):
        # Check that DataElement preserves all attributes ObjectifiedDataElement
        # arguments
        arg = objectify.DataElement(23, _pytype="str", _xsi="foobar",
                                    attrib={"gnu": "muh", "cat": "meeow",
                                            "dog": "wuff"},
                                    bird="tchilp", dog="grrr")
        value = objectify.DataElement(arg)
        self.assert_(isinstance(value, objectify.StringElement))
        for attr in arg.attrib:
            self.assertEquals(value.get(attr), arg.get(attr))

    def test_data_element_data_element_arg_pytype_none(self):
        # Check that _pytype arg overrides original py:pytype of
        # ObjectifiedDataElement
        arg = objectify.DataElement(23, _pytype="str", _xsi="foobar",
                                    attrib={"gnu": "muh", "cat": "meeow",
                                            "dog": "wuff"},
                                    bird="tchilp", dog="grrr")
        value = objectify.DataElement(arg, _pytype="NoneType")
        self.assert_(isinstance(value, objectify.NoneElement))
        self.assertEquals(value.get(XML_SCHEMA_NIL_ATTR), "true")
        self.assertEquals(value.text, None)
        self.assertEquals(value.pyval, None)
        for attr in arg.attrib:
            #if not attr == objectify.PYTYPE_ATTRIBUTE:
            self.assertEquals(value.get(attr), arg.get(attr))

    def test_data_element_data_element_arg_pytype(self):
        # Check that _pytype arg overrides original py:pytype of
        # ObjectifiedDataElement
        arg = objectify.DataElement(23, _pytype="str", _xsi="foobar",
                                    attrib={"gnu": "muh", "cat": "meeow",
                                            "dog": "wuff"},
                                    bird="tchilp", dog="grrr")
        value = objectify.DataElement(arg, _pytype="int")
        self.assert_(isinstance(value, objectify.IntElement))
        self.assertEquals(value.get(objectify.PYTYPE_ATTRIBUTE), "int")
        for attr in arg.attrib:
            if not attr == objectify.PYTYPE_ATTRIBUTE:
                self.assertEquals(value.get(attr), arg.get(attr))

    def test_data_element_data_element_arg_xsitype(self):
        # Check that _xsi arg overrides original xsi:type of given
        # ObjectifiedDataElement
        arg = objectify.DataElement(23, _pytype="str", _xsi="foobar",
                                    attrib={"gnu": "muh", "cat": "meeow",
                                            "dog": "wuff"},
                                    bird="tchilp", dog="grrr")
        value = objectify.DataElement(arg, _xsi="xsd:int")
        self.assert_(isinstance(value, objectify.IntElement))
        self.assertEquals(value.get(XML_SCHEMA_INSTANCE_TYPE_ATTR), "xsd:int")
        self.assertEquals(value.get(objectify.PYTYPE_ATTRIBUTE), "int")
        for attr in arg.attrib:
            if not attr in [objectify.PYTYPE_ATTRIBUTE,
                            XML_SCHEMA_INSTANCE_TYPE_ATTR]:
                self.assertEquals(value.get(attr), arg.get(attr))

    def test_data_element_data_element_arg_pytype_xsitype(self):
        # Check that _pytype and _xsi args override original py:pytype and
        # xsi:type attributes of given ObjectifiedDataElement
        arg = objectify.DataElement(23, _pytype="str", _xsi="foobar",
                                    attrib={"gnu": "muh", "cat": "meeow",
                                            "dog": "wuff"},
                                    bird="tchilp", dog="grrr")
        value = objectify.DataElement(arg, _pytype="int", _xsi="xsd:int")
        self.assert_(isinstance(value, objectify.IntElement))
        self.assertEquals(value.get(objectify.PYTYPE_ATTRIBUTE), "int")
        self.assertEquals(value.get(XML_SCHEMA_INSTANCE_TYPE_ATTR), "xsd:int")
        for attr in arg.attrib:
            if not attr in [objectify.PYTYPE_ATTRIBUTE,
                            XML_SCHEMA_INSTANCE_TYPE_ATTR]:
                self.assertEquals(value.get(attr), arg.get(attr))

    def test_data_element_invalid_pytype(self):
        self.assertRaises(ValueError, objectify.DataElement, 3.1415,
                          _pytype="int")

    def test_data_element_invalid_xsi(self):
        self.assertRaises(ValueError, objectify.DataElement, 3.1415,
                          _xsi="xsd:int")
        
    def test_data_element_data_element_arg_invalid_pytype(self):
        arg = objectify.DataElement(3.1415)
        self.assertRaises(ValueError, objectify.DataElement, arg,
                          _pytype="int")

    def test_data_element_data_element_arg_invalid_xsi(self):
        arg = objectify.DataElement(3.1415)
        self.assertRaises(ValueError, objectify.DataElement, arg,
                          _xsi="xsd:int")

    def test_data_element_element_arg(self):
        arg = objectify.Element('arg')
        value = objectify.DataElement(arg)
        self.assert_(isinstance(value, objectify.ObjectifiedElement))
        for attr in arg.attrib:
            self.assertEquals(value.get(attr), arg.get(attr))
        
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

    def test_child_getattr_empty_ns(self):
        root = self.XML(xml_str)
        self.assertEquals("4", getattr(root.c1, "{}c2").text)
        self.assertEquals("0", getattr(root.c1, "c2").text)

    def test_setattr(self):
        for val in [
            2, 2**32, 1.2, "Won't get fooled again", 
            _str("W\xf6n't get f\xf6\xf6led \xe4g\xe4in", 'ISO-8859-1'), True,
            False, None]: 
            root = self.Element('root')
            attrname = 'val'
            setattr(root, attrname, val)
            result = getattr(root, attrname)
            self.assertEquals(val, result)
            self.assertEquals(type(val), type(result.pyval))
 
    def test_setattr_nonunicode(self):
        root = self.Element('root')
        attrname = 'val'
        val = _bytes("W\xf6n't get f\xf6\xf6led \xe4g\xe4in", 'ISO-8859-1')
        self.assertRaises(ValueError, setattr, root, attrname, val)
        self.assertRaises(AttributeError, getattr, root, attrname) 
 
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
        self.assertRaises(IndexError, operator.getitem, root.c1.c2, 3)

    def test_child_index_neg(self):
        root = self.XML(xml_str)
        self.assertEquals("0", root.c1.c2[0].text)
        self.assertEquals("0", root.c1.c2[-3].text)
        self.assertEquals("1", root.c1.c2[-2].text)
        self.assertEquals("2", root.c1.c2[-1].text)
        self.assertRaises(IndexError, operator.getitem, root.c1.c2, -4)

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

    # slicing

    def test_getslice_complete(self):
        root = self.XML("<root><c>c1</c><c>c2</c></root>")
        self.assertEquals(["c1", "c2"],
                          [ c.text for c in root.c[:] ])

    def test_getslice_partial(self):
        root = self.XML("<root><c>c1</c><c>c2</c><c>c3</c><c>c4</c></root>")
        test_list = ["c1", "c2", "c3", "c4"]

        self.assertEquals(test_list,
                          [ c.text for c in root.c[:] ])
        self.assertEquals(test_list[1:2],
                          [ c.text for c in root.c[1:2] ])
        self.assertEquals(test_list[-3:-1],
                          [ c.text for c in root.c[-3:-1] ])
        self.assertEquals(test_list[-3:3],
                          [ c.text for c in root.c[-3:3] ])
        self.assertEquals(test_list[-3000:3],
                          [ c.text for c in root.c[-3000:3] ])
        self.assertEquals(test_list[-3:3000],
                          [ c.text for c in root.c[-3:3000] ])

    def test_getslice_partial_neg(self):
        root = self.XML("<root><c>c1</c><c>c2</c><c>c3</c><c>c4</c></root>")
        test_list = ["c1", "c2", "c3", "c4"]

        self.assertEquals(test_list,
                          [ c.text for c in root.c[:] ])
        self.assertEquals(test_list[2:1:-1],
                          [ c.text for c in root.c[2:1:-1] ])
        self.assertEquals(test_list[-1:-3:-1],
                          [ c.text for c in root.c[-1:-3:-1] ])
        self.assertEquals(test_list[2:-3:-1],
                          [ c.text for c in root.c[2:-3:-1] ])
        self.assertEquals(test_list[2:-3000:-1],
                          [ c.text for c in root.c[2:-3000:-1] ])

    # slice assignment

    def test_setslice_complete(self):
        Element = self.Element
        root = Element("root")
        root.c = ["c1", "c2"]

        c1 = root.c[0]
        c2 = root.c[1]

        self.assertEquals([c1,c2], list(root.c))
        self.assertEquals(["c1", "c2"],
                          [ c.text for c in root.c ])

    def test_setslice_elements(self):
        Element = self.Element
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

    def test_setslice_partial(self):
        Element = self.Element
        root = Element("root")
        l = ["c1", "c2", "c3", "c4"]
        root.c = l

        self.assertEquals(["c1", "c2", "c3", "c4"],
                          [ c.text for c in root.c ])
        self.assertEquals(l,
                          [ c.text for c in root.c ])

        new_slice = ["cA", "cB"]
        l[1:2] = new_slice
        root.c[1:2] = new_slice

        self.assertEquals(["c1", "cA", "cB", "c3", "c4"], l)
        self.assertEquals(["c1", "cA", "cB", "c3", "c4"],
                          [ c.text for c in root.c ])
        self.assertEquals(l,
                          [ c.text for c in root.c ])

    def test_setslice_insert(self):
        Element = self.Element
        root = Element("root")
        l = ["c1", "c2", "c3", "c4"]
        root.c = l

        self.assertEquals(["c1", "c2", "c3", "c4"],
                          [ c.text for c in root.c ])
        self.assertEquals(l,
                          [ c.text for c in root.c ])

        new_slice = ["cA", "cB"]
        l[1:1] = new_slice
        root.c[1:1] = new_slice

        self.assertEquals(["c1", "cA", "cB", "c2", "c3", "c4"], l)
        self.assertEquals(["c1", "cA", "cB", "c2", "c3", "c4"],
                          [ c.text for c in root.c ])
        self.assertEquals(l,
                          [ c.text for c in root.c ])

    def test_setslice_insert_neg(self):
        Element = self.Element
        root = Element("root")
        l = ["c1", "c2", "c3", "c4"]
        root.c = l

        self.assertEquals(["c1", "c2", "c3", "c4"],
                          [ c.text for c in root.c ])
        self.assertEquals(l,
                          [ c.text for c in root.c ])

        new_slice = ["cA", "cB"]
        l[-2:-2] = new_slice
        root.c[-2:-2] = new_slice

        self.assertEquals(["c1", "c2", "cA", "cB", "c3", "c4"], l)
        self.assertEquals(["c1", "c2", "cA", "cB", "c3", "c4"],
                          [ c.text for c in root.c ])
        self.assertEquals(l,
                          [ c.text for c in root.c ])

    def test_setslice_empty(self):
        Element = self.Element
        root = Element("root")

        root.c = []
        self.assertRaises(
            AttributeError, getattr, root, 'c')

    def test_setslice_partial_wrong_length(self):
        Element = self.Element
        root = Element("root")
        l = ["c1", "c2", "c3", "c4"]
        root.c = l

        self.assertEquals(["c1", "c2", "c3", "c4"],
                          [ c.text for c in root.c ])
        self.assertEquals(l,
                          [ c.text for c in root.c ])

        new_slice = ["cA", "cB", "cC"]
        self.assertRaises(
            ValueError, operator.setitem,
            l, slice(1,2,-1), new_slice)
        self.assertRaises(
            ValueError, operator.setitem,
            root.c, slice(1,2,-1), new_slice)

    def test_setslice_partial_neg(self):
        Element = self.Element
        root = Element("root")
        l = ["c1", "c2", "c3", "c4"]
        root.c = l

        self.assertEquals(["c1", "c2", "c3", "c4"],
                          [ c.text for c in root.c ])
        self.assertEquals(l,
                          [ c.text for c in root.c ])

        new_slice = ["cA", "cB"]
        l[-1:1:-1] = new_slice
        root.c[-1:1:-1] = new_slice

        self.assertEquals(["c1", "c2", "cB", "cA"], l)
        self.assertEquals(["c1", "c2", "cB", "cA"],
                          [ c.text for c in root.c ])
        self.assertEquals(l,
                          [ c.text for c in root.c ])

    def test_setslice_partial_allneg(self):
        Element = self.Element
        root = Element("root")
        l = ["c1", "c2", "c3", "c4"]
        root.c = l

        self.assertEquals(["c1", "c2", "c3", "c4"],
                          [ c.text for c in root.c ])
        self.assertEquals(l,
                          [ c.text for c in root.c ])

        new_slice = ["cA", "cB"]
        l[-1:-4:-2] = new_slice
        root.c[-1:-4:-2] = new_slice

        self.assertEquals(["c1", "cB", "c3", "cA"], l)
        self.assertEquals(["c1", "cB", "c3", "cA"],
                          [ c.text for c in root.c ])
        self.assertEquals(l,
                          [ c.text for c in root.c ])

    # other stuff

    def test_set_string(self):
        # make sure strings are not handled as sequences
        Element = self.Element
        root = Element("root")
        root.c = "TEST"
        self.assertEquals(["TEST"],
                          [ c.text for c in root.c ])

    def test_setitem_string(self):
        # make sure strings are set as children
        Element = self.Element
        root = Element("root")
        root["c"] = "TEST"
        self.assertEquals(["TEST"],
                          [ c.text for c in root.c ])

    def test_setitem_string_special(self):
        # make sure 'text' etc. are set as children
        Element = self.Element
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

    def test_type_NoneType(self):
        Element = self.Element
        SubElement = self.etree.SubElement

        nil_attr = XML_SCHEMA_NIL_ATTR
        root = Element("{objectified}root")
        SubElement(root, "{objectified}none")
        SubElement(root, "{objectified}none", {nil_attr : "true"})
        self.assertFalse(isinstance(root.none, objectify.NoneElement))
        self.assertFalse(isinstance(root.none[0], objectify.NoneElement))
        self.assert_(isinstance(root.none[1], objectify.NoneElement))
        self.assertEquals(hash(root.none[1]), hash(None))
        self.assertEquals(root.none[1], None)
        self.assertFalse(root.none[1])

    def test_data_element_NoneType(self):
        value = objectify.DataElement(None)
        self.assert_(isinstance(value, objectify.NoneElement))
        self.assertEquals(value, None)
        self.assertEquals(value.get(XML_SCHEMA_NIL_ATTR), "true")

    def test_type_bool(self):
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("{objectified}root")
        root.bool = True
        self.assertEquals(root.bool, True)
        self.assertEquals(root.bool + root.bool, True + True)
        self.assertEquals(True + root.bool, True + root.bool)
        self.assertEquals(root.bool * root.bool, True * True)
        self.assertEquals(int(root.bool), int(True))
        self.assertEquals(hash(root.bool), hash(True))
        self.assertEquals(complex(root.bool), complex(True))
        self.assert_(isinstance(root.bool, objectify.BoolElement))

        root.bool = False
        self.assertEquals(root.bool, False)
        self.assertEquals(root.bool + root.bool, False + False)
        self.assertEquals(False + root.bool, False + root.bool)
        self.assertEquals(root.bool * root.bool, False * False)
        self.assertEquals(int(root.bool), int(False))
        self.assertEquals(hash(root.bool), hash(False))
        self.assertEquals(complex(root.bool), complex(False))
        self.assert_(isinstance(root.bool, objectify.BoolElement))

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
        root.s = "test"
        self.assert_(isinstance(root.s, objectify.StringElement))

    def test_type_str_intliteral(self):
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("{objectified}root")
        root.s = "3"
        self.assert_(isinstance(root.s, objectify.StringElement))

    def test_type_str_floatliteral(self):
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("{objectified}root")
        root.s = "3.72"
        self.assert_(isinstance(root.s, objectify.StringElement))

    def test_type_str_mul(self):
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("{objectified}root")
        root.s = "test"

        self.assertEquals("test" * 5, root.s * 5)
        self.assertEquals(5 * "test", 5 * root.s)

        self.assertRaises(TypeError, operator.mul, root.s, "honk")
        self.assertRaises(TypeError, operator.mul, "honk", root.s)

    def test_type_str_add(self):
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("{objectified}root")
        root.s = "test"

        s = "toast"
        self.assertEquals("test" + s, root.s + s)
        self.assertEquals(s + "test", s + root.s)
            
    def test_type_str_mod(self):
        s = "%d %f %s %r"
        el = objectify.DataElement(s)
        values = (1, 7.0, "abcd", None)
        self.assertEquals(s % values, el % values)

        s = "%d"
        el = objectify.DataElement(s)
        val = 5
        self.assertEquals(s % val, el % val)

        s = "%d %s"
        el = objectify.DataElement(s)
        val = 5
        self.assertRaises(TypeError, el.__mod__, val)

        s = ""
        el = objectify.DataElement(s)
        val = 5
        self.assertRaises(TypeError, el.__mod__, val)

    def test_type_str_hash(self):
        v = "1"
        el = objectify.DataElement(v)
        self.assertEquals(hash(el), hash("1"))

    def test_type_str_as_int(self):
        v = "1"
        el = objectify.DataElement(v)
        self.assertEquals(int(el), 1)
            
    def test_type_str_as_float(self):
        v = "1"
        el = objectify.DataElement(v)
        self.assertEquals(float(el), 1)

    def test_type_str_as_complex(self):
        v = "1"
        el = objectify.DataElement(v)
        self.assertEquals(complex(el), 1)
            
    def test_type_str_mod_data_elements(self):
        s = "%d %f %s %r"
        el = objectify.DataElement(s)
        values = (objectify.DataElement(1),
                  objectify.DataElement(7.0),
                  objectify.DataElement("abcd"),
                  objectify.DataElement(None))
        self.assertEquals(s % values, el % values)

    def test_data_element_str(self):
        value = objectify.DataElement("test")
        self.assert_(isinstance(value, objectify.StringElement))
        self.assertEquals(value, "test")

    def test_data_element_str_intliteral(self):
        value = objectify.DataElement("3")
        self.assert_(isinstance(value, objectify.StringElement))
        self.assertEquals(value, "3")

    def test_data_element_str_floatliteral(self):
        value = objectify.DataElement("3.20")
        self.assert_(isinstance(value, objectify.StringElement))
        self.assertEquals(value, "3.20")

    def test_type_ustr(self):
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("{objectified}root")
        root.s = _str("test")
        self.assert_(isinstance(root.s, objectify.StringElement))

    def test_type_ustr_intliteral(self):
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("{objectified}root")
        root.s = _str("3")
        self.assert_(isinstance(root.s, objectify.StringElement))

    def test_type_ustr_floatliteral(self):
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("{objectified}root")
        root.s = _str("3.72")
        self.assert_(isinstance(root.s, objectify.StringElement))

    def test_type_ustr_mul(self):
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("{objectified}root")
        root.s = _str("test")

        self.assertEquals(_str("test") * 5, root.s * 5)
        self.assertEquals(5 * _str("test"), 5 * root.s)

        self.assertRaises(TypeError, operator.mul, root.s, _str("honk"))
        self.assertRaises(TypeError, operator.mul, _str("honk"), root.s)

    def test_type_ustr_add(self):
        Element = self.Element
        SubElement = self.etree.SubElement
        root = Element("{objectified}root")
        root.s = _str("test")

        s = _str("toast")
        self.assertEquals(_str("test") + s, root.s + s)
        self.assertEquals(s + _str("test"), s + root.s)

    def test_data_element_ustr(self):
        value = objectify.DataElement(_str("test"))
        self.assert_(isinstance(value, objectify.StringElement))
        self.assertEquals(value, _str("test"))

    def test_data_element_ustr_intliteral(self):
        value = objectify.DataElement("3")
        self.assert_(isinstance(value, objectify.StringElement))
        self.assertEquals(value, _str("3"))

    def test_data_element_ustr_floatliteral(self):
        value = objectify.DataElement(_str("3.20"))
        self.assert_(isinstance(value, objectify.StringElement))
        self.assertEquals(value, _str("3.20"))

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

    def test_data_element_int_hash(self):
        value = objectify.DataElement(123)
        self.assertEquals(hash(value), hash(123))

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

    def test_data_element_float_hash(self):
        value = objectify.DataElement(5.5)
        self.assertEquals(hash(value), hash(5.5))

    def test_data_element_xsitypes(self):
        for xsi, objclass in xsitype2objclass.items():
            # 1 is a valid value for all ObjectifiedDataElement classes
            pyval = 1
            value = objectify.DataElement(pyval, _xsi=xsi)
            self.assert_(isinstance(value, objclass),
                         "DataElement(%s, _xsi='%s') returns %s, expected %s"
                         % (pyval, xsi, type(value), objclass))
        
    def test_data_element_xsitypes_xsdprefixed(self):
        for xsi, objclass in xsitype2objclass.items():
            # 1 is a valid value for all ObjectifiedDataElement classes
            pyval = 1
            value = objectify.DataElement(pyval, _xsi="xsd:%s" % xsi)
            self.assert_(isinstance(value, objclass),
                         "DataElement(%s, _xsi='%s') returns %s, expected %s"
                         % (pyval, xsi, type(value), objclass))
        
    def test_data_element_xsitypes_prefixed(self):
        for xsi, objclass in xsitype2objclass.items():
            # 1 is a valid value for all ObjectifiedDataElement classes
            self.assertRaises(ValueError, objectify.DataElement, 1,
                              _xsi="foo:%s" % xsi)

    def test_data_element_pytypes(self):
        for pytype, objclass in pytype2objclass.items():
            # 1 is a valid value for all ObjectifiedDataElement classes
            pyval = 1
            value = objectify.DataElement(pyval, _pytype=pytype)
            self.assert_(isinstance(value, objclass),
                         "DataElement(%s, _pytype='%s') returns %s, expected %s"
                         % (pyval, pytype, type(value), objclass))

    def test_data_element_pytype_none(self):
        pyval = 1
        pytype = "NoneType"
        objclass = objectify.NoneElement
        value = objectify.DataElement(pyval, _pytype=pytype)
        self.assert_(isinstance(value, objclass),
                     "DataElement(%s, _pytype='%s') returns %s, expected %s"
                     % (pyval, pytype, type(value), objclass))
        self.assertEquals(value.text, None)
        self.assertEquals(value.pyval, None)
            
    def test_data_element_pytype_none_compat(self):
        # pre-2.0 lxml called NoneElement "none"
        pyval = 1
        pytype = "none"
        objclass = objectify.NoneElement
        value = objectify.DataElement(pyval, _pytype=pytype)
        self.assert_(isinstance(value, objclass),
                     "DataElement(%s, _pytype='%s') returns %s, expected %s"
                     % (pyval, pytype, type(value), objclass))
        self.assertEquals(value.text, None)
        self.assertEquals(value.pyval, None)

    def test_type_unregistered(self):
        Element = self.Element
        SubElement = self.etree.SubElement
        class MyFloat(float):
            pass
        root = Element("{objectified}root")
        root.myfloat = MyFloat(5.5)
        self.assert_(isinstance(root.myfloat, objectify.FloatElement))
        self.assertEquals(root.myfloat.get(objectify.PYTYPE_ATTRIBUTE), None)

    def test_data_element_unregistered(self):
        class MyFloat(float):
            pass
        value = objectify.DataElement(MyFloat(5.5))
        self.assert_(isinstance(value, objectify.FloatElement))
        self.assertEquals(value, 5.5)
        self.assertEquals(value.get(objectify.PYTYPE_ATTRIBUTE), None)

    def test_schema_types(self):
        XML = self.XML
        root = XML('''\
        <root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <b xsi:type="boolean">true</b>
          <b xsi:type="boolean">false</b>
          <b xsi:type="boolean">1</b>
          <b xsi:type="boolean">0</b>

          <f xsi:type="float">5</f>
          <f xsi:type="double">5</f>
        
          <s xsi:type="string">5</s>
          <s xsi:type="normalizedString">5</s>
          <s xsi:type="token">5</s>
          <s xsi:type="language">5</s>
          <s xsi:type="Name">5</s>
          <s xsi:type="NCName">5</s>
          <s xsi:type="ID">5</s>
          <s xsi:type="IDREF">5</s>
          <s xsi:type="ENTITY">5</s>
          <s xsi:type="NMTOKEN">5</s>

          <l xsi:type="integer">5</l>
          <l xsi:type="nonPositiveInteger">5</l>
          <l xsi:type="negativeInteger">5</l>
          <l xsi:type="long">5</l>
          <l xsi:type="nonNegativeInteger">5</l>
          <l xsi:type="unsignedLong">5</l>
          <l xsi:type="unsignedInt">5</l>
          <l xsi:type="positiveInteger">5</l>
          
          <i xsi:type="int">5</i>
          <i xsi:type="short">5</i>
          <i xsi:type="byte">5</i>
          <i xsi:type="unsignedShort">5</i>
          <i xsi:type="unsignedByte">5</i>

          <n xsi:nil="true"/>
        </root>
        ''')

        for b in root.b:
            self.assert_(isinstance(b, objectify.BoolElement))
        self.assertEquals(True,  root.b[0])
        self.assertEquals(False, root.b[1])
        self.assertEquals(True,  root.b[2])
        self.assertEquals(False, root.b[3])

        for f in root.f:
            self.assert_(isinstance(f, objectify.FloatElement))
            self.assertEquals(5, f)
            
        for s in root.s:
            self.assert_(isinstance(s, objectify.StringElement))
            self.assertEquals("5", s)

        for i in root.i:
            self.assert_(isinstance(i, objectify.IntElement))
            self.assertEquals(5, i)

        for l in root.l:
            self.assert_(isinstance(l, objectify.IntElement))
            self.assertEquals(5, i)
            
        self.assert_(isinstance(root.n, objectify.NoneElement))
        self.assertEquals(None, root.n)

    def test_schema_types_prefixed(self):
        XML = self.XML
        root = XML('''\
        <root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <b xsi:type="xsd:boolean">true</b>
          <b xsi:type="xsd:boolean">false</b>
          <b xsi:type="xsd:boolean">1</b>
          <b xsi:type="xsd:boolean">0</b>

          <f xsi:type="xsd:float">5</f>
          <f xsi:type="xsd:double">5</f>
        
          <s xsi:type="xsd:string">5</s>
          <s xsi:type="xsd:normalizedString">5</s>
          <s xsi:type="xsd:token">5</s>
          <s xsi:type="xsd:language">5</s>
          <s xsi:type="xsd:Name">5</s>
          <s xsi:type="xsd:NCName">5</s>
          <s xsi:type="xsd:ID">5</s>
          <s xsi:type="xsd:IDREF">5</s>
          <s xsi:type="xsd:ENTITY">5</s>
          <s xsi:type="xsd:NMTOKEN">5</s>

          <l xsi:type="xsd:integer">5</l>
          <l xsi:type="xsd:nonPositiveInteger">5</l>
          <l xsi:type="xsd:negativeInteger">5</l>
          <l xsi:type="xsd:long">5</l>
          <l xsi:type="xsd:nonNegativeInteger">5</l>
          <l xsi:type="xsd:unsignedLong">5</l>
          <l xsi:type="xsd:unsignedInt">5</l>
          <l xsi:type="xsd:positiveInteger">5</l>
          
          <i xsi:type="xsd:int">5</i>
          <i xsi:type="xsd:short">5</i>
          <i xsi:type="xsd:byte">5</i>
          <i xsi:type="xsd:unsignedShort">5</i>
          <i xsi:type="xsd:unsignedByte">5</i>

          <n xsi:nil="true"/>
        </root>
        ''')

        for b in root.b:
            self.assert_(isinstance(b, objectify.BoolElement))
        self.assertEquals(True,  root.b[0])
        self.assertEquals(False, root.b[1])
        self.assertEquals(True,  root.b[2])
        self.assertEquals(False, root.b[3])

        for f in root.f:
            self.assert_(isinstance(f, objectify.FloatElement))
            self.assertEquals(5, f)
            
        for s in root.s:
            self.assert_(isinstance(s, objectify.StringElement))
            self.assertEquals("5", s)

        for i in root.i:
            self.assert_(isinstance(i, objectify.IntElement))
            self.assertEquals(5, i)

        for l in root.l:
            self.assert_(isinstance(l, objectify.IntElement))
            self.assertEquals(5, l)
            
        self.assert_(isinstance(root.n, objectify.NoneElement))
        self.assertEquals(None, root.n)
        
    def test_type_str_sequence(self):
        XML = self.XML
        root = XML(_bytes('<root><b>why</b><b>try</b></root>'))
        strs = [ str(s) for s in root.b ]
        self.assertEquals(["why", "try"],
                          strs)

    def test_type_str_cmp(self):
        XML = self.XML
        root = XML(_bytes('<root><b>test</b><b>taste</b><b></b><b/></root>'))
        self.assertFalse(root.b[0] <  root.b[1])
        self.assertFalse(root.b[0] <= root.b[1])
        self.assertFalse(root.b[0] == root.b[1])

        self.assert_(root.b[0] != root.b[1])
        self.assert_(root.b[0] >= root.b[1])
        self.assert_(root.b[0] >  root.b[1])

        self.assertEquals(root.b[0], "test")
        self.assertEquals("test", root.b[0])

        self.assertEquals("", root.b[2])
        self.assertEquals(root.b[2], "")
        self.assertEquals("", root.b[3])
        self.assertEquals(root.b[3], "")
        self.assertEquals(root.b[2], root.b[3])
        
        root.b = "test"
        self.assert_(root.b)
        root.b = ""
        self.assertFalse(root.b)
        self.assertEquals(root.b, "")
        self.assertEquals("", root.b)

    def test_type_int_cmp(self):
        XML = self.XML
        root = XML(_bytes('<root><b>5</b><b>6</b></root>'))
        self.assert_(root.b[0] <  root.b[1])
        self.assert_(root.b[0] <= root.b[1])
        self.assert_(root.b[0] != root.b[1])

        self.assertFalse(root.b[0] == root.b[1])
        self.assertFalse(root.b[0] >= root.b[1])
        self.assertFalse(root.b[0] >  root.b[1])

        self.assertEquals(root.b[0], 5)
        self.assertEquals(5, root.b[0])
        self.assertNotEquals(root.b[0], "5")

        root.b = 5
        self.assert_(root.b)
        root.b = 0
        self.assertFalse(root.b)
        
    # float + long share the NumberElement implementation with int

    def test_type_bool_cmp(self):
        XML = self.XML
        root = XML(_bytes('<root><b>false</b><b>true</b></root>'))
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

    def test_type_none_cmp(self):
        XML = self.XML
        root = XML(_bytes("""
        <root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <b xsi:nil="true"></b><b xsi:nil="true"/>
        </root>"""))
        self.assert_(root.b[0] == root.b[1])
        self.assertFalse(root.b[0])
        self.assertEquals(root.b[0], None)
        self.assertEquals(None, root.b[0])

        # doesn't work in Py3:

        #for comparison in ["abc", 5, 7.3, True, [], ()]:
        #    none = root.b[1]
        #    self.assert_(none < comparison, "%s (%s) should be < %s" %
        #                 (none, type(none), comparison) )
        #    self.assert_(comparison > none, "%s should be > %s (%s)" %
        #                 (comparison, none, type(none)) )

    def test_dataelement_xsi(self):
        el = objectify.DataElement(1, _xsi="string")
        self.assertEquals(
            el.get(XML_SCHEMA_INSTANCE_TYPE_ATTR),
            'xsd:string')

    def test_dataelement_xsi_nsmap(self):
        el = objectify.DataElement(1, _xsi="string", 
                                   nsmap={'schema': XML_SCHEMA_NS})
        self.assertEquals(
            el.get(XML_SCHEMA_INSTANCE_TYPE_ATTR),
            'schema:string')

    def test_dataelement_xsi_prefix_error(self):
        self.assertRaises(ValueError, objectify.DataElement, 1,
                          _xsi="foo:string")

    def test_pytype_annotation(self):
        XML = self.XML
        root = XML(_bytes('''\
        <a xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:py="http://codespeak.net/lxml/objectify/pytype">
          <b>5</b>
          <b>test</b>
          <c>1.1</c>
          <c>\uF8D2</c>
          <x>true</x>
          <n xsi:nil="true" />
          <n></n>
          <b xsi:type="double">5</b>
          <b xsi:type="float">5</b>
          <s xsi:type="string">23</s>
          <s py:pytype="str">42</s>
          <f py:pytype="float">300</f>
          <l py:pytype="long">2</l>
          <t py:pytype="TREE"></t>
        </a>
        '''))
        objectify.annotate(root)

        child_types = [ c.get(objectify.PYTYPE_ATTRIBUTE)
                        for c in root.iterchildren() ]
        self.assertEquals("int",   child_types[ 0])
        self.assertEquals("str",   child_types[ 1])
        self.assertEquals("float", child_types[ 2])
        self.assertEquals("str",   child_types[ 3])
        self.assertEquals("bool",  child_types[ 4])
        self.assertEquals("NoneType",  child_types[ 5])
        self.assertEquals(None,    child_types[ 6])
        self.assertEquals("float", child_types[ 7])
        self.assertEquals("float", child_types[ 8])
        self.assertEquals("str",   child_types[ 9])
        self.assertEquals("int",   child_types[10])
        self.assertEquals("int",   child_types[11])
        self.assertEquals("int",   child_types[12])
        self.assertEquals(None,    child_types[13])
        
        self.assertEquals("true", root.n.get(XML_SCHEMA_NIL_ATTR))

    def test_pytype_annotation_empty(self):
        XML = self.XML
        root = XML(_bytes('''\
        <a xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:py="http://codespeak.net/lxml/objectify/pytype">
          <n></n>
        </a>
        '''))
        objectify.annotate(root)

        child_types = [ c.get(objectify.PYTYPE_ATTRIBUTE)
                        for c in root.iterchildren() ]
        self.assertEquals(None,    child_types[0])

        objectify.annotate(root, empty_pytype="str")

        child_types = [ c.get(objectify.PYTYPE_ATTRIBUTE)
                        for c in root.iterchildren() ]
        self.assertEquals("str",    child_types[0])

    def test_pytype_annotation_use_old(self):
        XML = self.XML
        root = XML(_bytes('''\
        <a xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:py="http://codespeak.net/lxml/objectify/pytype">
          <b>5</b>
          <b>test</b>
          <c>1.1</c>
          <c>\uF8D2</c>
          <x>true</x>
          <n xsi:nil="true" />
          <n></n>
          <b xsi:type="double">5</b>
          <b xsi:type="float">5</b>
          <s xsi:type="string">23</s>
          <s py:pytype="str">42</s>
          <f py:pytype="float">300</f>
          <l py:pytype="long">2</l>
          <t py:pytype="TREE"></t>
        </a>
        '''))
        objectify.annotate(root, ignore_old=False)

        child_types = [ c.get(objectify.PYTYPE_ATTRIBUTE)
                        for c in root.iterchildren() ]
        self.assertEquals("int",   child_types[ 0])
        self.assertEquals("str",   child_types[ 1])
        self.assertEquals("float", child_types[ 2])
        self.assertEquals("str",   child_types[ 3])
        self.assertEquals("bool",  child_types[ 4])
        self.assertEquals("NoneType",  child_types[ 5])
        self.assertEquals(None,    child_types[ 6])
        self.assertEquals("float", child_types[ 7])
        self.assertEquals("float", child_types[ 8])
        self.assertEquals("str",   child_types[ 9])
        self.assertEquals("str",   child_types[10])
        self.assertEquals("float", child_types[11])
        self.assertEquals("int",   child_types[12])
        self.assertEquals(TREE_PYTYPE,  child_types[13])
        
        self.assertEquals("true", root.n.get(XML_SCHEMA_NIL_ATTR))

    def test_pytype_xsitype_annotation(self):
        XML = self.XML
        root = XML(_bytes('''\
        <a xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:py="http://codespeak.net/lxml/objectify/pytype">
          <b>5</b>
          <b>test</b>
          <c>1.1</c>
          <c>\uF8D2</c>
          <x>true</x>
          <n xsi:nil="true" />
          <n></n>
          <b xsi:type="double">5</b>
          <b xsi:type="float">5</b>
          <s xsi:type="string">23</s>
          <s py:pytype="str">42</s>
          <f py:pytype="float">300</f>
          <l py:pytype="long">2</l>
          <t py:pytype="TREE"></t>
        </a>
        '''))
        objectify.annotate(root, ignore_old=False, ignore_xsi=False,
                           annotate_xsi=1, annotate_pytype=1)
        
        # check py annotations
        child_types = [ c.get(objectify.PYTYPE_ATTRIBUTE)
                        for c in root.iterchildren() ]
        self.assertEquals("int",   child_types[ 0])
        self.assertEquals("str",   child_types[ 1])
        self.assertEquals("float", child_types[ 2])
        self.assertEquals("str",   child_types[ 3])
        self.assertEquals("bool",  child_types[ 4])
        self.assertEquals("NoneType",  child_types[ 5])
        self.assertEquals(None,    child_types[ 6])
        self.assertEquals("float", child_types[ 7])
        self.assertEquals("float", child_types[ 8])
        self.assertEquals("str",   child_types[ 9])
        self.assertEquals("str",   child_types[10])
        self.assertEquals("float",   child_types[11])
        self.assertEquals("int",     child_types[12])
        self.assertEquals(TREE_PYTYPE,  child_types[13])
        
        self.assertEquals("true", root.n.get(XML_SCHEMA_NIL_ATTR))

        child_xsitypes = [ c.get(XML_SCHEMA_INSTANCE_TYPE_ATTR)
                        for c in root.iterchildren() ]

        # check xsi annotations
        child_types = [ c.get(XML_SCHEMA_INSTANCE_TYPE_ATTR)
                        for c in root.iterchildren() ]
        self.assertEquals("xsd:integer", child_types[ 0])
        self.assertEquals("xsd:string",  child_types[ 1])
        self.assertEquals("xsd:double",  child_types[ 2])
        self.assertEquals("xsd:string",  child_types[ 3])
        self.assertEquals("xsd:boolean", child_types[ 4])
        self.assertEquals(None,          child_types[ 5])
        self.assertEquals(None,          child_types[ 6])
        self.assertEquals("xsd:double",  child_types[ 7])
        self.assertEquals("xsd:float",   child_types[ 8])
        self.assertEquals("xsd:string",  child_types[ 9])
        self.assertEquals("xsd:string",  child_types[10])
        self.assertEquals("xsd:double",  child_types[11])
        self.assertEquals("xsd:integer", child_types[12])
        self.assertEquals(None,  child_types[13])

        self.assertEquals("true", root.n.get(XML_SCHEMA_NIL_ATTR))

    def test_xsiannotate_use_old(self):
        XML = self.XML
        root = XML(_bytes('''\
        <a xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:py="http://codespeak.net/lxml/objectify/pytype">
          <b>5</b>
          <b>test</b>
          <c>1.1</c>
          <c>\uF8D2</c>
          <x>true</x>
          <n xsi:nil="true" />
          <n></n>
          <b xsi:type="double">5</b>
          <b xsi:type="float">5</b>
          <s xsi:type="string">23</s>
          <s py:pytype="str">42</s>
          <f py:pytype="float">300</f>
          <l py:pytype="long">2</l>
          <t py:pytype="TREE"></t>
        </a>
        '''))
        objectify.xsiannotate(root, ignore_old=False)

        child_types = [ c.get(XML_SCHEMA_INSTANCE_TYPE_ATTR)
                        for c in root.iterchildren() ]
        self.assertEquals("xsd:integer", child_types[ 0])
        self.assertEquals("xsd:string",  child_types[ 1])
        self.assertEquals("xsd:double",  child_types[ 2])
        self.assertEquals("xsd:string",  child_types[ 3])
        self.assertEquals("xsd:boolean", child_types[ 4])
        self.assertEquals(None,          child_types[ 5])
        self.assertEquals(None,          child_types[ 6])
        self.assertEquals("xsd:double",  child_types[ 7])
        self.assertEquals("xsd:float",   child_types[ 8])
        self.assertEquals("xsd:string",  child_types[ 9])
        self.assertEquals("xsd:string",  child_types[10])
        self.assertEquals("xsd:double",  child_types[11])
        self.assertEquals("xsd:integer", child_types[12])
        self.assertEquals(None,          child_types[13])

    def test_pyannotate_ignore_old(self):
        XML = self.XML
        root = XML(_bytes('''\
        <a xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:py="http://codespeak.net/lxml/objectify/pytype">
          <b>5</b>
          <b>test</b>
          <c>1.1</c>
          <c>\uF8D2</c>
          <x>true</x>
          <n xsi:nil="true" />
          <n></n>
          <b xsi:type="double">5</b>
          <b xsi:type="float">5</b>
          <s xsi:type="string">23</s>
          <s py:pytype="str">42</s>
          <f py:pytype="float">300</f>
          <l py:pytype="long">2</l>
          <t py:pytype="TREE"></t>
        </a>
        '''))
        objectify.pyannotate(root, ignore_old=True)

        child_types = [ c.get(objectify.PYTYPE_ATTRIBUTE)
                        for c in root.iterchildren() ]
        self.assertEquals("int",   child_types[ 0])
        self.assertEquals("str",   child_types[ 1])
        self.assertEquals("float", child_types[ 2])
        self.assertEquals("str",   child_types[ 3])
        self.assertEquals("bool",  child_types[ 4])
        self.assertEquals("NoneType",  child_types[ 5])
        self.assertEquals(None,    child_types[ 6])
        self.assertEquals("float", child_types[ 7])
        self.assertEquals("float", child_types[ 8])
        self.assertEquals("str",   child_types[ 9])
        self.assertEquals("int",   child_types[10])
        self.assertEquals("int",   child_types[11])
        self.assertEquals("int",   child_types[12])
        self.assertEquals(None,    child_types[13])
        
        self.assertEquals("true", root.n.get(XML_SCHEMA_NIL_ATTR))

    def test_pyannotate_empty(self):
        XML = self.XML
        root = XML('''\
        <a xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:py="http://codespeak.net/lxml/objectify/pytype">
          <n></n>
        </a>
        ''')
        objectify.pyannotate(root)

        child_types = [ c.get(objectify.PYTYPE_ATTRIBUTE)
                        for c in root.iterchildren() ]
        self.assertEquals(None,    child_types[0])

        objectify.annotate(root, empty_pytype="str")

        child_types = [ c.get(objectify.PYTYPE_ATTRIBUTE)
                        for c in root.iterchildren() ]
        self.assertEquals("str",    child_types[0])

    def test_pyannotate_use_old(self):
        XML = self.XML
        root = XML('''\
        <a xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:py="http://codespeak.net/lxml/objectify/pytype">
          <b>5</b>
          <b>test</b>
          <c>1.1</c>
          <c>\uF8D2</c>
          <x>true</x>
          <n xsi:nil="true" />
          <n></n>
          <b xsi:type="double">5</b>
          <b xsi:type="float">5</b>
          <s xsi:type="string">23</s>
          <s py:pytype="str">42</s>
          <f py:pytype="float">300</f>
          <l py:pytype="long">2</l>
          <t py:pytype="TREE"></t>
        </a>
        ''')
        objectify.pyannotate(root)

        child_types = [ c.get(objectify.PYTYPE_ATTRIBUTE)
                        for c in root.iterchildren() ]
        self.assertEquals("int",   child_types[ 0])
        self.assertEquals("str",   child_types[ 1])
        self.assertEquals("float", child_types[ 2])
        self.assertEquals("str",   child_types[ 3])
        self.assertEquals("bool",  child_types[ 4])
        self.assertEquals("NoneType",  child_types[ 5])
        self.assertEquals(None,    child_types[ 6])
        self.assertEquals("float", child_types[ 7])
        self.assertEquals("float", child_types[ 8])
        self.assertEquals("str",   child_types[ 9])
        self.assertEquals("str",   child_types[10])
        self.assertEquals("float", child_types[11])
        self.assertEquals("int",   child_types[12])
        self.assertEquals(TREE_PYTYPE, child_types[13])
        
        self.assertEquals("true", root.n.get(XML_SCHEMA_NIL_ATTR))
        
    def test_xsiannotate_ignore_old(self):
        XML = self.XML
        root = XML(_bytes('''\
        <a xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:py="http://codespeak.net/lxml/objectify/pytype">
          <b>5</b>
          <b>test</b>
          <c>1.1</c>
          <c>\uF8D2</c>
          <x>true</x>
          <n xsi:nil="true" />
          <n></n>
          <b xsi:type="double">5</b>
          <b xsi:type="float">5</b>
          <s xsi:type="string">23</s>
          <s py:pytype="str">42</s>
          <f py:pytype="float">300</f>
          <l py:pytype="long">2</l>
          <t py:pytype="TREE"></t>
        </a>
        '''))
        objectify.xsiannotate(root, ignore_old=True)

        child_types = [ c.get(XML_SCHEMA_INSTANCE_TYPE_ATTR)
                        for c in root.iterchildren() ]
        self.assertEquals("xsd:integer", child_types[ 0])
        self.assertEquals("xsd:string",  child_types[ 1])
        self.assertEquals("xsd:double",  child_types[ 2])
        self.assertEquals("xsd:string",  child_types[ 3])
        self.assertEquals("xsd:boolean", child_types[ 4])
        self.assertEquals(None,          child_types[ 5])
        self.assertEquals(None,          child_types[ 6])
        self.assertEquals("xsd:integer", child_types[ 7])
        self.assertEquals("xsd:integer", child_types[ 8])
        self.assertEquals("xsd:integer", child_types[ 9])
        self.assertEquals("xsd:string",  child_types[10])
        self.assertEquals("xsd:double",  child_types[11])
        self.assertEquals("xsd:integer", child_types[12])
        self.assertEquals(None,          child_types[13])

        self.assertEquals("true", root.n.get(XML_SCHEMA_NIL_ATTR))

    def test_deannotate(self):
        XML = self.XML
        root = XML(_bytes('''\
        <a xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:py="http://codespeak.net/lxml/objectify/pytype">
          <b>5</b>
          <b>test</b>
          <c>1.1</c>
          <c>\uF8D2</c>
          <x>true</x>
          <n xsi:nil="true" />
          <n></n>
          <b xsi:type="double">5</b>
          <b xsi:type="float">5</b>
          <s xsi:type="string">23</s>
          <s py:pytype="str">42</s>
          <f py:pytype="float">300</f>
          <l py:pytype="long">2</l>
          <t py:pytype="TREE"></t>
        </a>
        '''))
        objectify.deannotate(root)

        for c in root.getiterator():
            self.assertEquals(None, c.get(XML_SCHEMA_INSTANCE_TYPE_ATTR))
            self.assertEquals(None, c.get(objectify.PYTYPE_ATTRIBUTE))

        self.assertEquals("true", root.n.get(XML_SCHEMA_NIL_ATTR))

    def test_xsinil_deannotate(self):
        XML = self.XML
        root = XML(_bytes('''\
        <a xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:py="http://codespeak.net/lxml/objectify/pytype">
          <b>5</b>
          <b>test</b>
          <c>1.1</c>
          <c>\uF8D2</c>
          <x>true</x>
          <n xsi:nil="true" />
          <n></n>
          <b xsi:type="double">5</b>
          <b xsi:type="float">5</b>
          <s xsi:type="string">23</s>
          <s py:pytype="str">42</s>
          <f py:pytype="float">300</f>
          <l py:pytype="long">2</l>
          <t py:pytype="TREE"></t>
        </a>
        '''))
        objectify.annotate(
            root, ignore_old=False, ignore_xsi=False, annotate_xsi=True,
            empty_pytype='str', empty_type='string')
        objectify.deannotate(root, pytype=False, xsi=False, xsi_nil=True)

        child_types = [ c.get(XML_SCHEMA_INSTANCE_TYPE_ATTR)
                        for c in root.iterchildren() ]
        self.assertEquals("xsd:integer",  child_types[ 0])
        self.assertEquals("xsd:string",   child_types[ 1])
        self.assertEquals("xsd:double",   child_types[ 2])
        self.assertEquals("xsd:string",   child_types[ 3])
        self.assertEquals("xsd:boolean",  child_types[ 4])
        self.assertEquals(None,           child_types[ 5])
        self.assertEquals("xsd:string",   child_types[ 6])
        self.assertEquals("xsd:double",   child_types[ 7])
        self.assertEquals("xsd:float",    child_types[ 8])
        self.assertEquals("xsd:string",   child_types[ 9])
        self.assertEquals("xsd:string",   child_types[10])
        self.assertEquals("xsd:double",    child_types[11])
        self.assertEquals("xsd:integer",  child_types[12])
        self.assertEquals(None,           child_types[13])

        self.assertEquals(None, root.n.get(XML_SCHEMA_NIL_ATTR))

        for c in root.iterchildren():
            self.assertNotEquals(None, c.get(objectify.PYTYPE_ATTRIBUTE))
            # these have no equivalent in xsi:type
            if (c.get(objectify.PYTYPE_ATTRIBUTE) not in [TREE_PYTYPE, 
                "NoneType"]):
                self.assertNotEquals(
                    None, c.get(XML_SCHEMA_INSTANCE_TYPE_ATTR))

    def test_xsitype_deannotate(self):
        XML = self.XML
        root = XML(_bytes('''\
        <a xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:py="http://codespeak.net/lxml/objectify/pytype"
        xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <b>5</b>
          <b>test</b>
          <c>1.1</c>
          <c>\uF8D2</c>
          <x>true</x>
          <n xsi:nil="true" />
          <n></n>
          <b xsi:type="xsd:double">5</b>
          <b xsi:type="xsd:float">5</b>
          <s xsi:type="xsd:string">23</s>
          <s py:pytype="str">42</s>
          <f py:pytype="float">300</f>
          <l py:pytype="long">2</l>
          <t py:pytype="TREE"></t>
        </a>
        '''))
        objectify.annotate(root)
        objectify.deannotate(root, pytype=False)

        child_types = [ c.get(objectify.PYTYPE_ATTRIBUTE)
                        for c in root.iterchildren() ]
        self.assertEquals("int",   child_types[ 0])
        self.assertEquals("str",   child_types[ 1])
        self.assertEquals("float", child_types[ 2])
        self.assertEquals("str",   child_types[ 3])
        self.assertEquals("bool",  child_types[ 4])
        self.assertEquals("NoneType",  child_types[ 5])
        self.assertEquals(None,    child_types[ 6])
        self.assertEquals("float", child_types[ 7])
        self.assertEquals("float", child_types[ 8])
        self.assertEquals("str",   child_types[ 9])
        self.assertEquals("int",   child_types[10])
        self.assertEquals("int",   child_types[11])
        self.assertEquals("int",   child_types[12])
        self.assertEquals(None,    child_types[13])
        
        self.assertEquals("true", root.n.get(XML_SCHEMA_NIL_ATTR))

        for c in root.getiterator():
            self.assertEquals(None, c.get(XML_SCHEMA_INSTANCE_TYPE_ATTR))

    def test_pytype_deannotate(self):
        XML = self.XML
        root = XML(_bytes('''\
        <a xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:py="http://codespeak.net/lxml/objectify/pytype"
        xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <b xsi:type="xsd:int">5</b>
          <b xsi:type="xsd:string">test</b>
          <c xsi:type="xsd:float">1.1</c>
          <c xsi:type="xsd:string">\uF8D2</c>
          <x xsi:type="xsd:boolean">true</x>
          <n xsi:nil="true" />
          <n></n>
          <b xsi:type="xsd:double">5</b>
          <b xsi:type="xsd:float">5</b>
          <s xsi:type="xsd:string">23</s>
          <s xsi:type="xsd:string">42</s>
          <f xsi:type="xsd:float">300</f>
          <l xsi:type="xsd:long">2</l>
          <t py:pytype="TREE"></t>
        </a>
        '''))
        objectify.annotate(root)
        objectify.deannotate(root, xsi=False)

        child_types = [ c.get(XML_SCHEMA_INSTANCE_TYPE_ATTR)
                        for c in root.iterchildren() ]
        self.assertEquals("xsd:int",      child_types[ 0])
        self.assertEquals("xsd:string",   child_types[ 1])
        self.assertEquals("xsd:float",    child_types[ 2])
        self.assertEquals("xsd:string",   child_types[ 3])
        self.assertEquals("xsd:boolean",  child_types[ 4])
        self.assertEquals(None,           child_types[ 5])
        self.assertEquals(None,           child_types[ 6])
        self.assertEquals("xsd:double",   child_types[ 7])
        self.assertEquals("xsd:float",    child_types[ 8])
        self.assertEquals("xsd:string",   child_types[ 9])
        self.assertEquals("xsd:string",   child_types[10])
        self.assertEquals("xsd:float",    child_types[11])
        self.assertEquals("xsd:long",     child_types[12])
        self.assertEquals(None,           child_types[13])

        self.assertEquals("true", root.n.get(XML_SCHEMA_NIL_ATTR))

        for c in root.getiterator():
            self.assertEquals(None, c.get(objectify.PYTYPE_ATTRIBUTE))

    def test_change_pytype_attribute(self):
        XML = self.XML

        xml = _bytes('''\
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

        pytype_ns, pytype_name = objectify.PYTYPE_ATTRIBUTE[1:].split('}')
        objectify.set_pytype_attribute_tag("{TEST}test")

        root = XML(xml)
        objectify.annotate(root)

        attribs = root.xpath("//@py:%s" % pytype_name,
                             namespaces={"py" : pytype_ns})
        self.assertEquals(0, len(attribs))
        attribs = root.xpath("//@py:test",
                             namespaces={"py" : "TEST"})
        self.assertEquals(7, len(attribs))

        objectify.set_pytype_attribute_tag()
        pytype_ns, pytype_name = objectify.PYTYPE_ATTRIBUTE[1:].split('}')

        self.assertNotEqual("test", pytype_ns.lower())
        self.assertNotEqual("test", pytype_name.lower())

        root = XML(xml)
        attribs = root.xpath("//@py:%s" % pytype_name,
                             namespaces={"py" : pytype_ns})
        self.assertEquals(0, len(attribs))

        objectify.annotate(root)
        attribs = root.xpath("//@py:%s" % pytype_name,
                             namespaces={"py" : pytype_ns})
        self.assertEquals(7, len(attribs))

    def test_registered_types(self):
        orig_types = objectify.getRegisteredTypes()
        orig_types[0].unregister()
        self.assertEquals(orig_types[1:], objectify.getRegisteredTypes())

        class NewType(objectify.ObjectifiedDataElement):
            pass

        def checkMyType(s):
            return True

        pytype = objectify.PyType("mytype", checkMyType, NewType)
        self.assert_(pytype not in objectify.getRegisteredTypes())
        pytype.register()
        self.assert_(pytype in objectify.getRegisteredTypes())
        pytype.unregister()
        self.assert_(pytype not in objectify.getRegisteredTypes())

        pytype.register(before = [objectify.getRegisteredTypes()[0].name])
        self.assertEquals(pytype, objectify.getRegisteredTypes()[0])
        pytype.unregister()

        pytype.register(after = [objectify.getRegisteredTypes()[0].name])
        self.assertNotEqual(pytype, objectify.getRegisteredTypes()[0])
        pytype.unregister()

        self.assertRaises(ValueError, pytype.register,
                          before = [objectify.getRegisteredTypes()[0].name],
                          after  = [objectify.getRegisteredTypes()[1].name])

    def test_registered_type_stringify(self):
        from datetime import datetime
        def parse_date(value):
            if len(value) != 14:
                raise ValueError(value)
            Y = int(value[0:4])
            M = int(value[4:6])
            D = int(value[6:8])
            h = int(value[8:10])
            m = int(value[10:12])
            s = int(value[12:14])
            return datetime(Y, M, D, h, m, s)

        def stringify_date(date):
            return date.strftime("%Y%m%d%H%M%S")

        class DatetimeElement(objectify.ObjectifiedDataElement):
            def pyval(self):
                return parse_date(self.text)
            pyval = property(pyval)

        datetime_type = objectify.PyType(
            "datetime", parse_date, DatetimeElement, stringify_date)
        datetime_type.xmlSchemaTypes = "dateTime"
        datetime_type.register()

        NAMESPACE = "http://foo.net/xmlns"
        NAMESPACE_MAP = {'ns': NAMESPACE}

        r = objectify.Element("{%s}root" % NAMESPACE, nsmap=NAMESPACE_MAP)
        time = datetime.now()
        r.date = time

        self.assert_(isinstance(r.date, DatetimeElement))
        self.assert_(isinstance(r.date.pyval, datetime))

        self.assertEquals(r.date.pyval, parse_date(stringify_date(time)))
        self.assertEquals(r.date.text, stringify_date(time))

        r.date = objectify.E.date(time)

        self.assert_(isinstance(r.date, DatetimeElement))
        self.assert_(isinstance(r.date.pyval, datetime))

        self.assertEquals(r.date.pyval, parse_date(stringify_date(time)))
        self.assertEquals(r.date.text, stringify_date(time))

        date = objectify.DataElement(time)

        self.assert_(isinstance(date, DatetimeElement))
        self.assert_(isinstance(date.pyval, datetime))

        self.assertEquals(date.pyval, parse_date(stringify_date(time)))
        self.assertEquals(date.text, stringify_date(time))

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

    def test_object_path_default_absolute(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( "root.c1.c99" )
        self.assertEquals(None, path(root, None))
        path = objectify.ObjectPath( "root.c99.c2" )
        self.assertEquals(None, path(root, None))
        path = objectify.ObjectPath( "notroot.c99.c2" )
        self.assertEquals(None, path(root, None))

    def test_object_path_default_relative(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath( ".c1.c99" )
        self.assertEquals(None, path(root, None))
        path = objectify.ObjectPath( ".c99.c2" )
        self.assertEquals(None, path(root, None))

    def test_object_path_syntax(self):
        root = self.XML(xml_str)
        path = objectify.ObjectPath("root .    {objectified}c1.   c2")
        self.assertEquals(root.c1.c2.text, path(root).text)

        path = objectify.ObjectPath("   root.{objectified}  c1.c2  [ 0 ]   ")
        self.assertEquals(root.c1.c2.text, path(root).text)

    def test_object_path_fail_parse_empty(self):
        self.assertRaises(ValueError, objectify.ObjectPath, "")

    def test_object_path_fail_parse_empty_list(self):
        self.assertRaises(ValueError, objectify.ObjectPath, [])

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
        out = BytesIO()
        pickle.dump(root, out)

        new_root = pickle.loads(out.getvalue())
        self.assertEquals(
            etree.tostring(new_root),
            etree.tostring(root))

    def test_pickle_elementtree(self):
        import pickle

        tree = etree.ElementTree(self.XML(xml_str + "<?my pi?>"))
        out = BytesIO()
        pickle.dump(tree, out)

        new_tree = pickle.loads(out.getvalue())
        self.assert_(isinstance(new_tree, etree._ElementTree))
        self.assertEquals(
            etree.tostring(new_tree),
            etree.tostring(tree))

    def test_pickle_intelement(self):
        self._test_pickle('<x>42</x>')
        self._test_pickle(objectify.DataElement(42))

    def test_pickle_floattelement(self):
        self._test_pickle('<x>42.0</x>')
        self._test_pickle(objectify.DataElement(42.0))

    def test_pickle_strelement(self):
        self._test_pickle('<x>Pickle me!</x>')
        self._test_pickle(objectify.DataElement('Pickle me!'))

    def test_pickle_boolelement(self):
        self._test_pickle('<x>true</x>')
        self._test_pickle('<x>false</x>')
        self._test_pickle(objectify.DataElement(True))
        self._test_pickle(objectify.DataElement(False))

    def test_pickle_noneelement(self):
        self._test_pickle('''
<x xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true"/>''')
        self._test_pickle(objectify.DataElement(None))

    def _test_pickle(self, stringOrElt):
        import pickle
        if isinstance(stringOrElt, (etree._Element, etree._ElementTree)):
            elt = stringOrElt
        else:
            elt = self.XML(stringOrElt)
        out = BytesIO()
        pickle.dump(elt, out)

        new_elt = pickle.loads(out.getvalue())
        self.assertEquals(
            etree.tostring(new_elt),
            etree.tostring(elt))

    # E-Factory tests, need to use sub-elements as root element is always
    # type-looked-up as ObjectifiedElement (no annotations)
    def test_efactory_int(self):
        E = objectify.E
        root = E.root(E.val(23))
        self.assert_(isinstance(root.val, objectify.IntElement))

    def test_efactory_float(self):
        E = objectify.E
        root = E.root(E.val(233.23))
        self.assert_(isinstance(root.val, objectify.FloatElement))

    def test_efactory_str(self):
        E = objectify.E
        root = E.root(E.val("what?"))
        self.assert_(isinstance(root.val, objectify.StringElement))

    def test_efactory_unicode(self):
        E = objectify.E
        root = E.root(E.val(_str("blöödy häll", encoding="ISO-8859-1")))
        self.assert_(isinstance(root.val, objectify.StringElement))

    def test_efactory_bool(self):
        E = objectify.E
        root = E.root(E.val(True))
        self.assert_(isinstance(root.val, objectify.BoolElement))

    def test_efactory_none(self):
        E = objectify.E
        root = E.root(E.val(None))
        self.assert_(isinstance(root.val, objectify.NoneElement))

    def test_efactory_value_concatenation(self):
        E = objectify.E
        root = E.root(E.val(1, "foo", 2.0, "bar ", True, None))
        self.assert_(isinstance(root.val, objectify.StringElement))

    def test_efactory_attrib(self):
        E = objectify.E
        root = E.root(foo="bar")
        self.assertEquals(root.get("foo"), "bar")

    def test_efactory_nested(self):
        E = objectify.E
        DataElement = objectify.DataElement
        root = E.root("text", E.sub(E.subsub()), "tail", DataElement(1),
                      DataElement(2.0))
        self.assert_(isinstance(root, objectify.ObjectifiedElement))
        self.assertEquals(root.text, "text")
        self.assert_(isinstance(root.sub, objectify.ObjectifiedElement))
        self.assertEquals(root.sub.tail, "tail")
        self.assert_(isinstance(root.sub.subsub, objectify.StringElement))
        self.assertEquals(len(root.value), 2)
        self.assert_(isinstance(root.value[0], objectify.IntElement))
        self.assert_(isinstance(root.value[1], objectify.FloatElement))

    def test_efactory_subtype(self):
        class Attribute(objectify.ObjectifiedDataElement):
            def __init__(self):
                objectify.ObjectifiedDataElement.__init__(self)
                self.set("datatype", "TYPE")
                self.set("range", "0.,1.")

        attr = Attribute()
        self.assertEquals(attr.text, None)
        self.assertEquals(attr.get("datatype"), "TYPE")
        self.assertEquals(attr.get("range"), "0.,1.")

    def test_XML_base_url_docinfo(self):
        root = objectify.XML(_bytes("<root/>"), base_url="http://no/such/url")
        docinfo = root.getroottree().docinfo
        self.assertEquals(docinfo.URL, "http://no/such/url")
 
    def test_XML_set_base_url_docinfo(self):
        root = objectify.XML(_bytes("<root/>"), base_url="http://no/such/url")
        docinfo = root.getroottree().docinfo
        self.assertEquals(docinfo.URL, "http://no/such/url")
        docinfo.URL = "https://secret/url"
        self.assertEquals(docinfo.URL, "https://secret/url")
 
    def test_parse_stringio_base_url(self):
        tree = objectify.parse(BytesIO("<root/>"), base_url="http://no/such/url")
        docinfo = tree.docinfo
        self.assertEquals(docinfo.URL, "http://no/such/url")
 
    def test_parse_base_url_docinfo(self):
        tree = objectify.parse(fileInTestDir('include/test_xinclude.xml'),
                               base_url="http://no/such/url")
        docinfo = tree.docinfo
        self.assertEquals(docinfo.URL, "http://no/such/url")

    def test_xml_base(self):
        root = objectify.XML(_bytes("<root/>"), base_url="http://no/such/url")
        self.assertEquals(root.base, "http://no/such/url")
        self.assertEquals(
            root.get('{http://www.w3.org/XML/1998/namespace}base'), None)
        root.base = "https://secret/url"
        self.assertEquals(root.base, "https://secret/url")
        self.assertEquals(
            root.get('{http://www.w3.org/XML/1998/namespace}base'),
            "https://secret/url")
 
    def test_xml_base_attribute(self):
        root = objectify.XML(_bytes("<root/>"), base_url="http://no/such/url")
        self.assertEquals(root.base, "http://no/such/url")
        self.assertEquals(
            root.get('{http://www.w3.org/XML/1998/namespace}base'), None)
        root.set('{http://www.w3.org/XML/1998/namespace}base',
                 "https://secret/url")
        self.assertEquals(root.base, "https://secret/url")
        self.assertEquals(
            root.get('{http://www.w3.org/XML/1998/namespace}base'),
            "https://secret/url")

    def test_standard_lookup(self):
        XML = self.XML

        xml = _bytes('''\
        <root xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <i>5</i>
          <i>-5</i>
          <l>4294967296</l>
          <l>-4294967296</l>
          <f>1.1</f>
          <b>true</b>
          <b>false</b>
          <s>Strange things happen, where strings collide</s>
          <s>True</s>
          <s>False</s>
          <s>t</s>
          <s>f</s>
          <s></s>
          <s>None</s>
          <n xsi:nil="true" />
        </root>
        ''')
        root = XML(xml)

        for i in root.i:
            self.assert_(isinstance(i, objectify.IntElement))
        for l in root.l:
            self.assert_(isinstance(l, objectify.IntElement))
        for f in root.f:
            self.assert_(isinstance(f, objectify.FloatElement))  
        for b in root.b:
            self.assert_(isinstance(b, objectify.BoolElement))
        self.assertEquals(True,  root.b[0])
        self.assertEquals(False, root.b[1])
        for s in root.s:
            self.assert_(isinstance(s, objectify.StringElement))
        self.assert_(isinstance(root.n, objectify.NoneElement))
        self.assertEquals(None, root.n)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ObjectifyTestCase)])
    suite.addTests(doctest.DocTestSuite(objectify))
    if sys.version_info >= (2,4):
        suite.addTests(
            [make_doctest('../../../doc/objectify.txt')])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
