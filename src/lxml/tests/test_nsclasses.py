# -*- coding: UTF-8 -*-

"""
Test cases related to namespace implementation classes and the
namespace registry mechanism
"""

import unittest, doctest

from common_imports import etree, HelperTestCase

class ETreeNamespaceClassesTestCase(HelperTestCase):
    class default_class(etree.ElementBase):
        pass
    class maeh_class(etree.ElementBase):
        def maeh(self):
            return u'maeh'
    class bluff_class(etree.ElementBase):
        def bluff(self):
            return u'bluff'

    def test_registry(self):
        ns = etree.Namespace(u'ns01')
        ns[u'maeh'] = self.maeh_class

        etree.Namespace(u'ns01').clear()

        etree.Namespace(u'ns02').update({u'maeh'  : self.maeh_class})
        etree.Namespace(u'ns03').update({u'bluff' : self.bluff_class}.items())
        etree.Namespace(u'ns02').clear()
        etree.Namespace(u'ns03').clear()

    def test_ns_classes(self):
        bluff_dict = {u'bluff' : self.bluff_class}
        maeh_dict  = {u'maeh'  : self.maeh_class}

        etree.Namespace(u'ns10').update(bluff_dict)

        tree = self.parse(u'<bluff xmlns="ns10"><ns11:maeh xmlns:ns11="ns11"/></bluff>')

        el = tree.getroot()
        self.assert_(isinstance(el, etree.ElementBase))
        self.assert_(hasattr(el, 'bluff'))
        self.assertFalse(hasattr(el[0], 'maeh'))
        self.assertFalse(hasattr(el[0], 'bluff'))
        self.assertEquals(el.bluff(), u'bluff')
        del el

        etree.Namespace(u'ns11').update(maeh_dict)
        el = tree.getroot()
        self.assert_(hasattr(el, 'bluff'))
        self.assert_(hasattr(el[0], 'maeh'))
        self.assertEquals(el.bluff(), u'bluff')
        self.assertEquals(el[0].maeh(), u'maeh')
        del el

        etree.Namespace(u'ns10').clear()

        tree = self.parse(u'<bluff xmlns="ns10"><ns11:maeh xmlns:ns11="ns11"/></bluff>')
        el = tree.getroot()
        self.assertFalse(hasattr(el, 'bluff'))
        self.assertFalse(hasattr(el, 'maeh'))
        self.assertFalse(hasattr(el[0], 'bluff'))
        self.assert_(hasattr(el[0], 'maeh'))

        etree.Namespace(u'ns11').clear()

    def test_create_element(self):
        bluff_dict = {u'bluff' : self.bluff_class}
        maeh_dict  = {u'maeh'  : self.maeh_class}

        etree.Namespace(u'ns20').update(bluff_dict)
        etree.Namespace(u'ns21').update(maeh_dict)

        el = etree.Element("{ns20}bluff")
        etree.SubElement(el, "{ns21}maeh")
        self.assert_(hasattr(el, 'bluff'))
        self.assert_(hasattr(el[0], 'maeh'))
        self.assertEquals(el.bluff(), u'bluff')
        self.assertEquals(el[0].maeh(), u'maeh')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(ETreeNamespaceClassesTestCase)])
    suite.addTests(
        [doctest.DocFileSuite('../../../doc/namespace_extensions.txt')])
    return suite

if __name__ == '__main__':
    unittest.main()
