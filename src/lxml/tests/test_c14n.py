import unittest
from lxml import c14n

class C14nTestCase(unittest.TestCase):
    def test_c14n_1(self):
        self.assertEquals(
            '<foo>Bar</foo>',
            c14n.canonicalize('<foo >Bar</foo >'))

    def test_c14n_attributes(self):
        self.assertEquals(
            '<foo a="A" b="B"></foo>',
            c14n.canonicalize('<foo b="B"  a="A"  />'))
        

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(C14nTestCase)])
    return suite

if __name__ == '__main__':
    unittest.main()
