import unittest

#from lxml.nodereg import Element, ElementTree, SubElement, XML
from lxml import noderegtest

class NodeRegTestCase(unittest.TestCase):
    def test_foo(self):
        doc = noderegtest.makeDocument('<foo><bar/></foo>')
        

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(NodeRegTestCase)])
    return suite

if __name__ == '__main__':
    unittest.main()
