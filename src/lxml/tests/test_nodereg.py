import unittest

from lxml import noderegtest

class NodeRegTestCase(unittest.TestCase):
    def test_foo(self):
        doc = noderegtest.makeDocument('<foo><bar/></foo>')
        self.assertEquals('foo', doc.documentElement.nodeName)
        self.assertEquals('bar', doc.documentElement.firstChild.nodeName)

    def test_bar(self):
        doc = noderegtest.makeDocument('<foo/>')
        new = doc.createElementNS(None, 'bar')
        doc.documentElement.appendChild(new)
        self.assertEquals('bar', doc.documentElement.firstChild.nodeName)

    def test_baz(self):
        doc = noderegtest.makeDocument('<foo/>')
        bar = doc.createElementNS(None, 'bar')
        baz = doc.createElementNS(None, 'baz')
        bar.appendChild(baz)
        #self.assertEquals('baz', bar.firstChild.nodeName)
        flux = doc.createElementNS(None, 'flux')
        baz.appendChild(flux)
        del baz
        del bar
        del flux

    def test_four(self):
        doc = noderegtest.makeDocument('<foo/>')
        bar = doc.createElementNS(None, 'bar')
        baz = doc.createElementNS(None, 'baz')
        bar.appendChild(baz)

        
def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(NodeRegTestCase)])
    return suite

if __name__ == '__main__':
    unittest.main()
