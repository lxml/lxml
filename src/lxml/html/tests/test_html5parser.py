import os
try:
    from StringIO import StringIO
except ImportError:                     # python 3
    from io import StringIO
import sys
import tempfile
import unittest
from unittest import skipUnless

from lxml.builder import ElementMaker
from lxml.etree import Element, ElementTree, ParserError
from lxml.html import html_parser, XHTML_NAMESPACE

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse 
    
try:
    from urllib import pathname2url
except ImportError:
    from urllib.request import pathname2url
    

def path2url(path):
    return urlparse.urljoin(
        'file:', pathname2url(path))


try:
    import html5lib
except ImportError:
    html5lib = None

    class BogusModules(object):
        # See PEP 302 for details on how this works
        def __init__(self, mocks):
            self.mocks = mocks

        def find_module(self, fullname, path=None):
            if fullname in self.mocks:
                return self
            return None

        def load_module(self, fullname):
            class Cls: pass
            fake_module = Cls()
            fake_module.__qualname__ = fullname
            fake_module.__name__ = fullname.rsplit('.', 1)[-1]
            mod = sys.modules.setdefault(fullname, fake_module)
            mod.__file__, mod.__loader__, mod.__path__ = "<dummy>", self, []
            mod.__dict__.update(self.mocks[fullname])
            return mod

    # Fake just enough of html5lib so that html5parser.py is importable
    # without errors.
    sys.meta_path.append(BogusModules({
        'html5lib': {
            # A do-nothing HTMLParser class
            'HTMLParser': type('HTMLParser', (object,), {
                '__init__': lambda self, **kw: None,
                }),
            },
        'html5lib.treebuilders': {
            },
        'html5lib.treebuilders.etree_lxml': {
            'TreeBuilder': 'dummy treebuilder',
            },
        }))


class Test_HTMLParser(unittest.TestCase):
    def make_one(self, **kwargs):
        from lxml.html.html5parser import HTMLParser
        return HTMLParser(**kwargs)

    @skipUnless(html5lib, 'html5lib is not installed')
    def test_integration(self):
        parser = self.make_one(strict=True)
        tree = parser.parse(XHTML_TEST_DOCUMENT)
        root = tree.getroot()
        self.assertEqual(root.tag, xhtml_tag('html'))


class Test_XHTMLParser(unittest.TestCase):
    def make_one(self, **kwargs):
        from lxml.html.html5parser import XHTMLParser
        return XHTMLParser(**kwargs)

    @skipUnless(hasattr(html5lib, 'XHTMLParser'),
                'xhtml5lib does not have XHTMLParser')
    def test_integration(self):
        # XXX: This test are untested. (html5lib no longer has an XHTMLParser)
        parser = self.make_one(strict=True)
        tree = parser.parse(XHTML_TEST_DOCUMENT)
        root = tree.getroot()
        self.assertEqual(root.tag, xhtml_tag('html'))


class Test_document_fromstring(unittest.TestCase):
    def call_it(self, *args, **kwargs):
        from lxml.html.html5parser import document_fromstring
        return document_fromstring(*args, **kwargs)

    def test_basic(self):
        parser = DummyParser(doc=DummyElementTree(root='dummy root'))
        elem = self.call_it(b'dummy input', parser=parser)
        self.assertEqual(elem, 'dummy root')
        self.assertEqual(parser.parse_args, (b'dummy input',))
        self.assertEqual(parser.parse_kwargs, {'useChardet': True})

    def test_guess_charset_not_used_for_unicode(self):
        parser = DummyParser()
        elem = self.call_it(b''.decode('ascii'), parser=parser)
        self.assertEqual(parser.parse_kwargs, {})

    def test_guess_charset_arg_gets_passed_to_parser(self):
        parser = DummyParser()
        elem = self.call_it(b'', guess_charset='gc_arg', parser=parser)
        self.assertEqual(parser.parse_kwargs, {'useChardet': 'gc_arg'})

    def test_raises_type_error_on_nonstring_input(self):
        not_a_string = None
        self.assertRaises(TypeError, self.call_it, not_a_string)

    @skipUnless(html5lib, 'html5lib is not installed')
    def test_integration(self):
        elem = self.call_it(XHTML_TEST_DOCUMENT)
        self.assertEqual(elem.tag, xhtml_tag('html'))


class Test_fragments_fromstring(unittest.TestCase):
    def call_it(self, *args, **kwargs):
        from lxml.html.html5parser import fragments_fromstring
        return fragments_fromstring(*args, **kwargs)

    def test_basic(self):
        parser = DummyParser(fragments='fragments')
        fragments = self.call_it(b'dummy input', parser=parser)
        self.assertEqual(fragments, 'fragments')
        self.assertEqual(parser.parseFragment_kwargs, {'useChardet': False})

    def test_guess_charset_arg_gets_passed_to_parser(self):
        parser = DummyParser()
        elem = self.call_it(b'', guess_charset='gc_arg', parser=parser)
        self.assertEqual(parser.parseFragment_kwargs, {'useChardet': 'gc_arg'})

    def test_guess_charset_not_used_for_unicode(self):
        parser = DummyParser()
        elem = self.call_it(b''.decode('ascii'), parser=parser)
        self.assertEqual(parser.parseFragment_kwargs, {})

    def test_raises_type_error_on_nonstring_input(self):
        not_a_string = None
        self.assertRaises(TypeError, self.call_it, not_a_string)

    def test_no_leading_text_strips_empty_leading_text(self):
        parser = DummyParser(fragments=['', 'tail'])
        fragments = self.call_it('', parser=parser, no_leading_text=True)
        self.assertEqual(fragments, ['tail'])

    def test_no_leading_text_raises_error_if_leading_text(self):
        parser = DummyParser(fragments=['leading text', 'tail'])
        self.assertRaises(ParserError, self.call_it,
                          '', parser=parser, no_leading_text=True)

    @skipUnless(html5lib, 'html5lib is not installed')
    def test_integration(self):
        fragments = self.call_it('a<b>c</b>')
        self.assertEqual(len(fragments), 2)
        self.assertEqual(fragments[0], 'a')
        self.assertEqual(fragments[1].tag, xhtml_tag('b'))


class Test_fragment_fromstring(unittest.TestCase):
    def call_it(self, *args, **kwargs):
        from lxml.html.html5parser import fragment_fromstring
        return fragment_fromstring(*args, **kwargs)

    def test_basic(self):
        element = DummyElement()
        parser = DummyParser(fragments=[element])
        self.assertEqual(self.call_it('html', parser=parser), element)

    def test_raises_type_error_on_nonstring_input(self):
        not_a_string = None
        self.assertRaises(TypeError, self.call_it, not_a_string)

    def test_create_parent(self):
        parser = DummyParser(fragments=['head', Element('child')])
        elem = self.call_it('html', parser=parser, create_parent='parent')
        self.assertEqual(elem.tag, 'parent')
        self.assertEqual(elem.text, 'head')
        self.assertEqual(elem[0].tag, 'child')

    def test_create_parent_default_type_no_ns(self):
        parser = DummyParser(fragments=[], namespaceHTMLElements=False)
        elem = self.call_it('html', parser=parser, create_parent=True)
        self.assertEqual(elem.tag, 'div')

    def test_raises_error_on_leading_text(self):
        parser = DummyParser(fragments=['leading text'])
        self.assertRaises(ParserError, self.call_it, 'html', parser=parser)

    def test_raises_error_if_no_elements_found(self):
        parser = DummyParser(fragments=[])
        self.assertRaises(ParserError, self.call_it, 'html', parser=parser)

    def test_raises_error_if_multiple_elements_found(self):
        parser = DummyParser(fragments=[DummyElement(), DummyElement()])
        self.assertRaises(ParserError, self.call_it, 'html', parser=parser)

    def test_raises_error_if_tail(self):
        parser = DummyParser(fragments=[DummyElement(tail='tail')])
        self.assertRaises(ParserError, self.call_it, 'html', parser=parser)


class Test_fromstring(unittest.TestCase):
    def call_it(self, *args, **kwargs):
        from lxml.html.html5parser import fromstring
        return fromstring(*args, **kwargs)

    def test_returns_whole_doc_if_input_contains_html_tag(self):
        parser = DummyParser(root='the doc')
        self.assertEqual(self.call_it('<html></html>', parser=parser),
                         'the doc')

    def test_returns_whole_doc_if_input_contains_doctype(self):
        parser = DummyParser(root='the doc')
        self.assertEqual(self.call_it('<!DOCTYPE html>', parser=parser),
                         'the doc')

    def test_returns_whole_doc_if_input_is_encoded(self):
        parser = DummyParser(root='the doc')
        input = '<!DOCTYPE html>'.encode('ascii')
        self.assertEqual(self.call_it(input, parser=parser),
                         'the doc')

    def test_returns_whole_doc_if_head_not_empty(self, use_ns=True):
        E = HTMLElementMaker(namespaceHTMLElements=use_ns)
        root = E.html(E.head(E.title()))
        parser = DummyParser(root=root)
        self.assertEqual(self.call_it('', parser=parser), root)

    def test_returns_whole_doc_if_head_not_empty_no_ns(self):
        self.test_returns_whole_doc_if_head_not_empty(use_ns=False)

    def test_returns_unwraps_body_if_single_element(self):
        E = HTMLElementMaker()
        elem = E.p('test')
        root = E.html(E.head(), E.body(elem))
        parser = DummyParser(root=root)
        self.assertEqual(self.call_it('', parser=parser), elem)

    def test_returns_body_if_has_text(self):
        E = HTMLElementMaker()
        elem = E.p('test')
        body = E.body('text', elem)
        root = E.html(E.head(), body)
        parser = DummyParser(root=root)
        self.assertEqual(self.call_it('', parser=parser), body)

    def test_returns_body_if_single_element_has_tail(self):
        E = HTMLElementMaker()
        elem = E.p('test')
        elem.tail = 'tail'
        body = E.body(elem)
        root = E.html(E.head(), body)
        parser = DummyParser(root=root)
        self.assertEqual(self.call_it('', parser=parser), body)

    def test_wraps_multiple_fragments_in_div_no_ns(self):
        E = HTMLElementMaker(namespaceHTMLElements=False)
        parser = DummyParser(root=E.html(E.head(), E.body(E.h1(), E.p())),
                             namespaceHTMLElements=False)
        elem = self.call_it('', parser=parser)
        self.assertEqual(elem.tag, 'div')

    def test_wraps_multiple_fragments_in_span_no_ns(self):
        E = HTMLElementMaker(namespaceHTMLElements=False)
        parser = DummyParser(root=E.html(E.head(), E.body('foo', E.a('link'))),
                             namespaceHTMLElements=False)
        elem = self.call_it('', parser=parser)
        self.assertEqual(elem.tag, 'span')

    def test_raises_type_error_on_nonstring_input(self):
        not_a_string = None
        self.assertRaises(TypeError, self.call_it, not_a_string)

    @skipUnless(html5lib, 'html5lib is not installed')
    def test_integration_whole_doc(self):
        elem = self.call_it(XHTML_TEST_DOCUMENT)
        self.assertEqual(elem.tag, xhtml_tag('html'))

    @skipUnless(html5lib, 'html5lib is not installed')
    def test_integration_single_fragment(self):
        elem = self.call_it('<p></p>')
        self.assertEqual(elem.tag, xhtml_tag('p'))


class Test_parse(unittest.TestCase):
    def call_it(self, *args, **kwargs):
        from lxml.html.html5parser import parse
        return parse(*args, **kwargs)

    def make_temp_file(self, contents=''):
        tmpfile = tempfile.NamedTemporaryFile(delete=False)
        try:
            tmpfile.write(contents.encode('utf8'))
            tmpfile.flush()
            tmpfile.seek(0)
            return tmpfile
        except Exception:
            try:
                tmpfile.close()
            finally:
                os.unlink(tmpfile.name)
            raise

    def test_with_file_object(self):
        parser = DummyParser(doc='the doc')
        fp = open(__file__)
        try:
            self.assertEqual(self.call_it(fp, parser=parser), 'the doc')
            self.assertEqual(parser.parse_args, (fp,))
        finally:
            fp.close()

    def test_with_file_name(self):
        parser = DummyParser(doc='the doc')
        tmpfile = self.make_temp_file('data')
        try:
            data = tmpfile.read()
        finally:
            tmpfile.close()
        try:
            self.assertEqual(self.call_it(tmpfile.name, parser=parser), 'the doc')
            fp, = parser.parse_args
            try:
                self.assertEqual(fp.read(), data)
            finally:
                fp.close()
        finally:
            os.unlink(tmpfile.name)

    def test_with_url(self):
        parser = DummyParser(doc='the doc')
        tmpfile = self.make_temp_file('content')
        try:
            data = tmpfile.read()
        finally:
            tmpfile.close()
        try:
            url = path2url(tmpfile.name)
            self.assertEqual(self.call_it(url, parser=parser), 'the doc')
            fp, = parser.parse_args
            try:
                self.assertEqual(fp.read(), data)
            finally:
                fp.close()
        finally:
            os.unlink(tmpfile.name)

    @skipUnless(html5lib, 'html5lib is not installed')
    def test_integration(self):
        doc = self.call_it(StringIO(XHTML_TEST_DOCUMENT))
        root = doc.getroot()
        self.assertEqual(root.tag, xhtml_tag('html'))


def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromModule(sys.modules[__name__])


class HTMLElementMaker(ElementMaker):
    def __init__(self, namespaceHTMLElements=True):
        initargs = dict(makeelement=html_parser.makeelement)
        if namespaceHTMLElements:
            initargs.update(namespace=XHTML_NAMESPACE,
                            nsmap={None: XHTML_NAMESPACE})
        ElementMaker.__init__(self, **initargs)


class DummyParser(object):
    def __init__(self, doc=None, root=None,
                 fragments=None, namespaceHTMLElements=True):
        self.doc = doc or DummyElementTree(root=root)
        self.fragments = fragments
        self.tree = DummyTreeBuilder(namespaceHTMLElements)

    def parse(self, *args, **kwargs):
        self.parse_args = args
        self.parse_kwargs = kwargs
        return self.doc

    def parseFragment(self, *args, **kwargs):
        self.parseFragment_args = args
        self.parseFragment_kwargs = kwargs
        return self.fragments


class DummyTreeBuilder(object):
    def __init__(self, namespaceHTMLElements=True):
        self.namespaceHTMLElements = namespaceHTMLElements


class DummyElementTree(object):
    def __init__(self, root):
        self.root = root

    def getroot(self):
        return self.root


class DummyElement(object):
    def __init__(self, tag='tag', tail=None):
        self.tag = tag
        self.tail = tail


def xhtml_tag(tag):
    return '{%s}%s' % (XHTML_NAMESPACE, tag)


XHTML_TEST_DOCUMENT = '''
    <!DOCTYPE html>
    <html>
    <head><title>TITLE</title></head>
    <body></body>
    </html>
    '''
