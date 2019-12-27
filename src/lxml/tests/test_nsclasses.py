# -*- coding: utf-8 -*-

"""
Test cases related to namespace implementation classes and the
namespace registry mechanism
"""

from __future__ import absolute_import

import unittest

from .common_imports import etree, HelperTestCase, _bytes, make_doctest

class ETreeNamespaceClassesTestCase(HelperTestCase):
    
    class default_class(etree.ElementBase):
        pass
    class maeh_class(etree.ElementBase):
        def maeh(self):
            return 'maeh'
    class bluff_class(etree.ElementBase):
        def bluff(self):
            return 'bluff'

    def setUp(self):
        super(ETreeNamespaceClassesTestCase, self).setUp()
        lookup = etree.ElementNamespaceClassLookup()
        self.Namespace = lookup.get_namespace
        parser = etree.XMLParser()
        parser.set_element_class_lookup(lookup)
        etree.set_default_parser(parser)

    def tearDown(self):
        etree.set_default_parser()
        del self.Namespace
        super(ETreeNamespaceClassesTestCase, self).tearDown()

    def test_registry(self):
        ns = self.Namespace('ns01')
        ns['maeh'] = self.maeh_class

        self.Namespace('ns01').clear()

        self.Namespace('ns02').update({'maeh'  : self.maeh_class})
        self.Namespace('ns03').update({'bluff' : self.bluff_class}.items())
        self.Namespace('ns02').clear()
        self.Namespace('ns03').clear()

    def test_ns_classes(self):
        bluff_dict = {'bluff' : self.bluff_class}
        maeh_dict  = {'maeh'  : self.maeh_class}

        self.Namespace('ns10').update(bluff_dict)

        tree = self.parse(_bytes('<bluff xmlns="ns10"><ns11:maeh xmlns:ns11="ns11"/></bluff>'))

        el = tree.getroot()
        self.assertTrue(isinstance(el, etree.ElementBase))
        self.assertTrue(hasattr(el, 'bluff'))
        self.assertFalse(hasattr(el[0], 'maeh'))
        self.assertFalse(hasattr(el[0], 'bluff'))
        self.assertEqual(el.bluff(), 'bluff')
        del el

        self.Namespace('ns11').update(maeh_dict)
        el = tree.getroot()
        self.assertTrue(hasattr(el, 'bluff'))
        self.assertTrue(hasattr(el[0], 'maeh'))
        self.assertEqual(el.bluff(), 'bluff')
        self.assertEqual(el[0].maeh(), 'maeh')
        del el

        self.Namespace('ns10').clear()

        tree = self.parse(_bytes('<bluff xmlns="ns10"><ns11:maeh xmlns:ns11="ns11"/></bluff>'))
        el = tree.getroot()
        self.assertFalse(hasattr(el, 'bluff'))
        self.assertFalse(hasattr(el, 'maeh'))
        self.assertFalse(hasattr(el[0], 'bluff'))
        self.assertTrue(hasattr(el[0], 'maeh'))

        self.Namespace('ns11').clear()

    def test_default_tagname(self):
        bluff_dict = {
            None   : self.bluff_class,
            'maeh' : self.maeh_class
            }

        ns = self.Namespace("uri:nsDefClass")
        ns.update(bluff_dict)

        tree = self.parse(_bytes('''
            <test xmlns="bla" xmlns:ns1="uri:nsDefClass" xmlns:ns2="uri:nsDefClass">
              <ns2:el1/><ns1:el2/><ns1:maeh/><ns2:maeh/><maeh/>
            </test>
            '''))

        el = tree.getroot()
        self.assertFalse(isinstance(el, etree.ElementBase))
        for child in el[:-1]:
            self.assertTrue(isinstance(child, etree.ElementBase), child.tag)
        self.assertFalse(isinstance(el[-1], etree.ElementBase))

        self.assertTrue(hasattr(el[0], 'bluff'))
        self.assertTrue(hasattr(el[1], 'bluff'))
        self.assertTrue(hasattr(el[2], 'maeh'))
        self.assertTrue(hasattr(el[3], 'maeh'))
        self.assertFalse(hasattr(el[4], 'maeh'))
        del el

        ns.clear()

    def test_create_element(self):
        bluff_dict = {'bluff' : self.bluff_class}
        self.Namespace('ns20').update(bluff_dict)

        maeh_dict  = {'maeh'  : self.maeh_class}
        self.Namespace('ns21').update(maeh_dict)

        el = etree.Element("{ns20}bluff")
        self.assertTrue(hasattr(el, 'bluff'))

        child = etree.SubElement(el, "{ns21}maeh")
        self.assertTrue(hasattr(child, 'maeh'))
        child = etree.SubElement(el, "{ns20}bluff")
        self.assertTrue(hasattr(child, 'bluff'))
        child = etree.SubElement(el, "{ns21}bluff")
        self.assertFalse(hasattr(child, 'bluff'))
        self.assertFalse(hasattr(child, 'maeh'))

        self.assertTrue(hasattr(el[0], 'maeh'))
        self.assertTrue(hasattr(el[1], 'bluff'))
        self.assertFalse(hasattr(el[2], 'bluff'))
        self.assertFalse(hasattr(el[2], 'maeh'))

        self.assertEqual(el.bluff(), 'bluff')
        self.assertEqual(el[0].maeh(), 'maeh')
        self.assertEqual(el[1].bluff(), 'bluff')

        self.Namespace('ns20').clear()
        self.Namespace('ns21').clear()

    def test_create_element_default(self):
        bluff_dict = {None : self.bluff_class}
        self.Namespace('ns30').update(bluff_dict)

        maeh_dict  = {'maeh'  : self.maeh_class}
        self.Namespace(None).update(maeh_dict)

        el = etree.Element("{ns30}bluff")
        etree.SubElement(el, "maeh")
        self.assertTrue(hasattr(el, 'bluff'))
        self.assertTrue(hasattr(el[0], 'maeh'))
        self.assertEqual(el.bluff(), 'bluff')
        self.assertEqual(el[0].maeh(), 'maeh')

        self.Namespace(None).clear()
        self.Namespace('ns30').clear()

    def test_element_creation(self):
        default, bluff, maeh = (
            self.default_class, self.bluff_class, self.maeh_class)

        class honk(etree.ElementBase):
            TAG = 'HONK'
            NAMESPACE = 'http://a.b/c'

        el = default(
            "test",
            "text",
            bluff(honk, "TaIL", maeh),
            maeh("TeXT", bluff, honk(), "TAiL"),
            "Tail")

        self.assertEqual('default_class', el.tag)
        self.assertEqual('testtext', el.text)
        self.assertEqual(None, el.tail)
        self.assertEqual(2, len(el))
        self.assertEqual(7, len(list(el.iter())))

        self.assertEqual('bluff_class', el[0].tag)
        self.assertEqual('TaIL', el[0][0].tail)
        self.assertEqual('TaIL', ''.join(el[0].itertext()))
        self.assertEqual('{http://a.b/c}HONK',
                          el[0][0].tag)
        self.assertEqual('maeh_class',
                          el[0][1].tag)

        self.assertEqual('maeh_class', el[1].tag)
        self.assertEqual('TeXT', el[1].text)
        self.assertEqual('bluff_class', el[1][0].tag)
        self.assertEqual('{http://a.b/c}HONK', el[1][1].tag)
        self.assertEqual('TAiL', el[1][1].tail)

        self.assertEqual('TeXTTAiL',
                          ''.join(el[1].itertext()))
        self.assertEqual('Tail', el[1].tail)
        self.assertEqual('TAiL', el[1][1].tail)
        self.assertEqual('bluff_class', el[1][0].tag)
        self.assertEqual('{http://a.b/c}HONK', el[1][1].tag)
        

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeNamespaceClassesTestCase)])
    suite.addTests(
        [make_doctest('../../../doc/element_classes.txt')])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
