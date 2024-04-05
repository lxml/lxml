import unittest, sys
from lxml.tests.common_imports import make_doctest, doctest
import lxml.html
from lxml.html import html_parser, XHTML_NAMESPACE

class FrameTest(unittest.TestCase):

    def test_parse_fragments_fromstring(self):
        parser = lxml.html.HTMLParser(encoding='utf-8', remove_comments=True)
        html = """<frameset>
            <frame src="main.php" name="srcpg" id="srcpg" frameborder="0" rolling="Auto" marginwidth="" marginheight="0">
        </frameset>"""
        etree_document = lxml.html.fragments_fromstring(html, parser=parser)
        self.assertEqual(len(etree_document), 1)
        root = etree_document[0]
        self.assertEqual(root.tag, "frameset")
        frame_element = root[0]
        self.assertEqual(frame_element.tag, 'frame')

    def test_parse_fromstring(self):
        parser = lxml.html.HTMLParser(encoding='utf-8', remove_comments=True)
        html = """<html><frameset>
            <frame src="main.php" name="srcpg" id="srcpg" frameborder="0" rolling="Auto" marginwidth="" marginheight="0">
        </frameset></html>"""
        etree_document = lxml.html.fromstring(html, parser=parser)
        self.assertEqual(etree_document.tag, 'html')
        self.assertEqual(len(etree_document), 1)
        frameset_element = etree_document[0]
        self.assertEqual(len(frameset_element), 1)
        frame_element = frameset_element[0]
        self.assertEqual(frame_element.tag, 'frame')


def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromModule(sys.modules[__name__])