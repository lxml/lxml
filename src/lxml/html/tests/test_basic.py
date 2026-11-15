import doctest
import sys
import unittest
from lxml import etree, html

class TestBasicFeatures(unittest.TestCase):
    def test_various_mixins(self):
        base_url = "http://example.org"
        doc = html.fromstring("""
        <root>
            <!-- comment -->
            &entity;
            <el/>
        </root>
        """, base_url=base_url)
        self.assertEqual(doc.getroottree().docinfo.URL, base_url)
        self.assertEqual(len(doc), 2)
        self.assertIsInstance(doc[0], html.HtmlComment)
        self.assertIsInstance(doc[1], html.HtmlElement)
        for child in doc:
            # base_url makes sense on all nodes (kinda) whereas `classes` or
            # `get_rel_links` not really
            self.assertEqual(child.base_url, base_url)

    def test_set_empty_attribute(self):
        e = html.Element('e')
        e.set('a')
        e.set('b', None)
        e.set('c', '')
        self.assertEqual(
            html.tostring(e),
            b'<e a b c=""></e>',
            "Attributes set to `None` should yield empty attributes"
        )
        self.assertEqual(e.get('a'), '', "getting the empty attribute results in an empty string")
        self.assertEqual(e.attrib, {
            'a': '',
            'b': '',
            'c': '',
        })

    def test_element_head_body(self):
        doc = html.fromstring("""
        <HTML>
          <HEAD>
          </HEAD>
          <BODY>
            <p>
          </body>
        </HTML>
        """)

        head = doc.head
        body = doc.body

        self.assertIs(doc.head, head)
        self.assertIs(doc.body, body)
        self.assertIs(doc[0].head, head)
        self.assertIs(doc[0].body, body)
        self.assertIs(doc[1].head, head)
        self.assertIs(doc[1].body, body)
        self.assertIs(doc[1][0].head, head)
        self.assertIs(doc[1][0].body, body)

    def test_element_head_body_empty(self):
        doc = html.fromstring("""
        <HTML>
        </HTML>
        """)
        self.assertIsNone(doc.head)
        self.assertIsNone(doc.body)

    def test_drop_tag_text_tail_and_children(self):
        doc = html.fromstring(
            '<div>lead<a>a-text<b>b-text</b>b-tail<!--c-->c-tail</a>a-tail'
            '<i>i-text</i>i-tail<u>u-text</u>u-tail</div>')
        a, i, u = doc
        a.drop_tag()
        self.assertEqual(
            html.tostring(doc, encoding='unicode'),
            '<div>leada-text<b>b-text</b>b-tail<!--c-->c-taila-tail'
            '<i>i-text</i>i-tail<u>u-text</u>u-tail</div>')
        i.drop_tag()
        u.drop_tag()
        self.assertEqual(
            html.tostring(doc, encoding='unicode'),
            '<div>leada-text<b>b-text</b>b-tail<!--c-->c-taila-tail'
            'i-texti-tailu-textu-tail</div>')
        b, comment = doc
        self.assertEqual(b.tail, 'b-tail')
        self.assertEqual(comment.tail, 'c-taila-taili-texti-tailu-textu-tail')

    def test_drop_tag_comment_keeps_tail_but_not_text(self):
        doc = html.fromstring('<div>lead<!--note-->tail<b/></div>')
        doc[0].drop_tag()
        self.assertEqual(html.tostring(doc, encoding='unicode'), '<div>leadtail<b></b></div>')
        self.assertEqual(doc.text, 'leadtail')

    def test_drop_tag_many_siblings(self):
        count = 200
        doc = html.fromstring(
            '<div>' + '<span>x<b>y</b>z</span>-<!--c-->' * count + '</div>')
        for span in doc.findall('span'):
            span.drop_tag()
        self.assertEqual(len(doc), 2 * count)
        self.assertEqual(
            html.tostring(doc, encoding='unicode'),
            '<div>x' + '<b>y</b>z-<!--c-->x' * (count - 1) + '<b>y</b>z-<!--c--></div>')

    def test_drop_tree_joins_tail(self):
        doc = html.fromstring('<div>lead<a>gone<b/></a>a-tail<i>i</i>i-tail<u/>u-tail</div>')
        a, i, u = doc
        a.drop_tree()
        self.assertEqual(doc.text, 'leada-tail')
        i.drop_tree()
        u.drop_tree()
        self.assertEqual(len(doc), 0)
        self.assertEqual(doc.text, 'leada-taili-tailu-tail')

    def test_drop_tree_many_siblings(self):
        count = 200
        doc = html.fromstring(
            '<div><p>a</p>' + '<script>s</script> tail ' * count + '</div>')
        for script in doc.findall('script'):
            script.drop_tree()
        self.assertEqual(
            html.tostring(doc, encoding='unicode'),
            '<div><p>a</p>' + ' tail ' * count + '</div>')

    def test_drop_text_merge_is_transparent(self):
        # Merged text must be indistinguishable from the pre-merge behaviour.
        def build():
            return html.fromstring(
                '<div>l\xe9ad<a>A&amp;<b>B</b>&lt;bt&gt;</a>&eacute;at'
                '<!--c-->ct<i>i\u20ac</i>it<u/>ut<p>x</p></div>')

        doc = build()
        a, comment, i, u, p = doc
        a.drop_tag()
        i.drop_tag()
        u.drop_tree()
        # a.text goes to doc.text, the tail goes after <b>'s tail
        self.assertEqual(doc.text, 'l\xe9adA&')
        b = doc[0]
        self.assertEqual(b.tail, '<bt>\xe9at')
        self.assertEqual(comment.tail, 'cti\u20acitut')
        self.assertEqual(
            doc.xpath('text()'), ['l\xe9adA&', '<bt>\xe9at', 'cti€itut'])
        self.assertEqual(
            doc.xpath('count(//text())'), 5.0)
        self.assertEqual(
            list(doc.itertext()), ['l\xe9adA&', 'B', '<bt>\xe9at', 'cti\u20acitut', 'x'])
        self.assertEqual(
            html.tostring(doc, encoding='unicode'),
            '<div>l\xe9adA&amp;<b>B</b>&lt;bt&gt;\xe9at<!--c-->cti\u20acitut<p>x</p></div>')
        self.assertEqual(
            html.tostring(doc, method='xml', encoding='unicode'),
            '<div>l\xe9adA&amp;<b>B</b>&lt;bt&gt;\xe9at<!--c-->cti\u20acitut<p>x</p></div>')
        self.assertEqual(
            etree.tostring(doc, method='c14n'),
            '<div>l\xe9adA&amp;<b>B</b>&lt;bt&gt;\xe9at<!--c-->cti\u20acitut<p>x</p></div>'.encode('utf8'))
        # the dropped elements keep their own tail
        self.assertEqual(a.tail, '\xe9at')
        self.assertEqual(u.tail, 'ut')

        # replacing the merged text drops all of it
        doc.text = 'new'
        b.tail = 'tail'
        comment.tail = None
        self.assertEqual(
            html.tostring(doc, encoding='unicode'),
            '<div>new<b>B</b>tail<!--c--><p>x</p></div>')
        self.assertEqual(doc.xpath('text()'), ['new', 'tail'])
        self.assertEqual(
            list(doc.itertext()), ['new', 'B', 'tail', 'x'])

        # the text of a comment is not merged by drop_tag(), its tail is
        doc = html.fromstring('<div><!--gone-->t1<b/>t2</div>')
        doc[0].drop_tag()
        self.assertEqual(doc.text, 't1')
        doc[0].drop_tree()
        self.assertEqual(doc.text, 't1t2')
        self.assertEqual(doc.xpath('text()'), ['t1t2'])

    def test_drop_tag_entity_does_not_move_dtd_nodes(self):
        # The children iterator of an entity reference would walk the
        # sibling chain of its declaration in the internal DTD.
        parser = etree.XMLParser(resolve_entities=False, load_dtd=False)
        parser.set_element_class_lookup(html.HtmlElementClassLookup())
        root = etree.fromstring(
            b'<!DOCTYPE html [<!ENTITY ext SYSTEM "x"><!--c--><?pi x?>]>'
            b'<html><body><p>a&ext;b</p></body></html>', parser)
        entity = root[0][0][0]
        self.assertIsInstance(entity, html.HtmlEntity)
        entity.drop_tag()
        self.assertEqual(len(root[0][0]), 0)
        self.assertEqual(root[0][0].text, 'ab')
        self.assertEqual(
            etree.tostring(root.getroottree()),
            b'<!DOCTYPE html [\n<!ENTITY ext SYSTEM "x">\n<!--c--><?pi x?>]>\n'
            b'<html><body><p>ab</p></body></html>')

    def test_drop_tag_merges_into_dict_interned_text(self):
        # Whitespace runs of 16 to 59 bytes are stored in the parser dict.
        ws = ' ' * 20
        doc = html.fromstring(
            '<div>%s<b>x</b>%s<i>y</i>%s<u><s>z</s></u>%s</div>' % (ws, ws, ws, ws))
        doc[0].drop_tag()
        doc[0].drop_tree()
        doc[0].drop_tag()
        self.assertEqual(doc.text, ws + 'x' + ws + ws)
        self.assertEqual(doc[0].tail, ws)
        self.assertEqual(doc.xpath('text()'), [ws + 'x' + ws + ws, ws])
        self.assertEqual(
            html.tostring(doc, encoding='unicode'),
            '<div>%sx%s%s<s>z</s>%s</div>' % (ws, ws, ws, ws))

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([doctest.DocFileSuite('test_basic.txt')])
    suite.addTests([doctest.DocTestSuite(html)])
    suite.addTest(unittest.TestLoader().loadTestsFromModule(sys.modules[__name__]))
    return suite

if __name__ == '__main__':
    unittest.main()
