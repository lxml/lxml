"""
Test cases specifically for the XMLPullParser.

Aiming to be broader than the tests from CPython in "tests_elementtree.py".
"""

import itertools
import unittest

from .common_imports import etree, ElementTree


WITH_ETREE = True
WITH_ELEMENTTREE = True
WITH_PIS = True
WITH_COMMENTS = True

WITH_SHAPE_HIGHT = 3
WITH_CHUNKS = True
WITH_FUZZING = True
WITH_PARSED_ENTITIES = True

EVENT_TYPES = ("start", "end", "start-ns", "end-ns", "comment", "pi")
NAMES = ("a", "b", "item", "name", "x")
PREFIXES = ("p", "q", "r2")


def normalize(events):
    """Turn raw pull-parser events into comparable tuples."""
    result = []
    for action, obj in events:
        if action in ("start", "end"):
            result.append((action, obj.tag))
        elif action == "start-ns":
            result.append((action, obj))  # (prefix, uri)
        elif action == "end-ns":
            result.append((action, None))
        elif action == "comment":
            result.append((action, obj.text))
        elif action == "pi":
            # Note: lxml's PIs have target+text, ET's PIs have both in "text"
            text = obj.text
            target = getattr(obj, 'target', None)
            if target is not None:
                text = f"{target} {text}"
            result.append((action, text))
    return result


def feed_in_chunks(xml, chunk_size, parser_class, event_types=EVENT_TYPES):
    """Feed the document in fixed-size chunks, reading events after each feed."""
    parser = parser_class(events=event_types)
    events = []
    for pos in range(0, len(xml), chunk_size):
        parser.feed(xml[pos:pos + chunk_size])
        events.extend(normalize(parser.read_events()))
    parser.close()
    events.extend(normalize(parser.read_events()))
    return events


def enumerate_shapes(height):
    """
    Yield every tree shape of height at most `height`.

    A shape is a tuple of child shapes; a leaf is the empty tuple.
    Each node has 0, 1 or 2 children.
    """
    if height == 1:
        yield ()
        return
    yield ()
    subshapes = list(enumerate_shapes(height - 1))
    for child_count in (1, 2):
        for children in itertools.product(subshapes, repeat=child_count):
            yield children


def build_element(shape, event_types, counter, scope):
    """
    Build the XML and expected events for a shape.

    `scope` maps prefixes to URIs; the key None is the default namespace.
    Names, declarations, prefix use and comment/PI placement are all chosen
    from the element's pre-order index, so the output is deterministic.
    Returns (xml_text, expected_events).
    """
    idx = counter[0]
    counter[0] += 1

    local = NAMES[idx % len(NAMES)]

    new_scope = dict(scope)
    decls = []
    if idx % 2 == 0:
        prefix = PREFIXES[idx % len(PREFIXES)]
        uri = f"urn:{prefix}:{idx % len(PREFIXES)}"
        decls.append((prefix, uri))
        new_scope[prefix] = uri
    elif idx % 3 == 1 and any(k is not None for k in scope):
        prefix = sorted(k for k in scope if k is not None)[0]
    else:
        prefix = None  # unprefixed: resolves to the default namespace, if any

    qname = local if prefix is None else f"{prefix}:{local}"
    uri = new_scope.get(prefix)
    tag = f"{{{uri}}}{local}" if uri else local

    # Comment before this element's start tag (in the parent's content).
    before_xml, before_events = "", []
    if WITH_COMMENTS and idx % 5 == 3:
        before_xml = f"<!--before-{idx}-->"
        if 'comment' in event_types:
            before_events = [("comment", f"before-{idx}")]

    # Processing instruction as the first content of this element.
    inner_start_xml, inner_start_events = "", []
    if WITH_PIS and idx % 4 == 1:
        inner_start_xml = f"<?pi-{idx} data-{idx}?>"
        if 'pi' in event_types:
            inner_start_events = [("pi", f"pi-{idx} data-{idx}")]

    # Comment as the last content of this element, before its end tag.
    inner_end_xml, inner_end_events = "", []
    if WITH_COMMENTS and idx % 3 == 2:
        inner_end_xml = f"<!--after-{idx}-->"
        if 'comment' in event_types:
            inner_end_events = [("comment", f"after-{idx}")]

    children_xml, children_events = [], []
    for child_shape in shape:
        cx, ce = build_element(child_shape, event_types, counter, new_scope)
        children_xml.append(cx)
        children_events.extend(ce)

    attrs = "".join(f' xmlns:{p}="{u}"' for p, u in decls)
    start_ns_events = [("start-ns", decl) for decl in decls] if 'start-ns' in event_types else []
    end_ns_events = [("end-ns", None) for _ in decls] if 'end-ns' in event_types else []

    content_xml = inner_start_xml + "".join(children_xml) + inner_end_xml
    content_events = inner_start_events + children_events + inner_end_events

    body = []
    if content_xml:
        xml = f"<{qname}{attrs}>{content_xml}</{qname}>"
        if 'start' in event_types:
            body.append(("start", tag))
        body.extend(content_events)
        if 'end' in event_types:
            body.append(("end", tag))
    else:
        xml = f"<{qname}{attrs}/>"
        if 'start' in event_types:
            body.append(("start", tag))
        if 'end' in event_types:
            body.append(("end", tag))

    return before_xml + xml, before_events + start_ns_events + body + end_ns_events


def build_document(shape, event_types=EVENT_TYPES):
    """Build a standalone document for a shape, with no inherited namespaces."""
    return build_element(shape, event_types, [0], {})


OUTER_TEMPLATES = [
    # No namespaces, no comments or PIs around the entity.
    dict(root_prefix=None, root_uri=None, before=(), after=(),
         top_comment=None, inside_comment=None, inside_pi=False),
    # Default namespace, siblings on both sides, comments and a PI.
    #dict(root_prefix=None, root_uri="urn:default", before=("pre",), after=("post",),
    #     top_comment="top", inside_comment="mid", inside_pi=True),
    # Prefixed root; the entity's unprefixed names must not pick up this prefix.
    #dict(root_prefix="o", root_uri="urn:outer", before=("x",), after=(),
    #     top_comment=None, inside_comment=None, inside_pi=True),
    # Prefix "p" also used by the entity's generated declarations (shadowing).
    dict(root_prefix="p", root_uri="urn:p", before=(), after=("y", "z"),
         top_comment="t2", inside_comment="m2", inside_pi=False),
]


def build_outer(tpl, event_types, fragment, fragment_events):
    """
    Wrap an entity fragment in an outer document built from a template.

    Returns (xml_text, expected_events). The DOCTYPE declares entity `e`
    as the fragment, and the root references it between sibling elements.
    """
    prefix, uri = tpl["root_prefix"], tpl["root_uri"]

    def qualify(local):
        return local if prefix is None else f"{prefix}:{local}"

    def expand(local):
        return f"{{{uri}}}{local}" if uri else local

    decl = ""
    if uri:
        decl = f' xmlns:{prefix}="{uri}"' if prefix else f' xmlns="{uri}"'

    root_qname = qualify("r")
    root_tag = expand("r")

    top_xml, top_events = "", []
    if WITH_COMMENTS and tpl["top_comment"]:
        top_xml = f"<!--{tpl['top_comment']}-->"
        if 'comment' in event_types:
            top_events = [("comment", tpl["top_comment"])]

    body_xml, body_events = [], []

    def sibling(name):
        tag_name = expand(name)
        events = []
        if 'start' in event_types:
            events.append(("start", tag_name))
        if 'end' in event_types:
            events.append(("end", tag_name))
        return (f"<{qualify(name)}/>", events)

    for name in tpl["before"]:
        sx, se = sibling(name)
        body_xml.append(sx)
        body_events.extend(se)

    if WITH_COMMENTS and tpl["inside_comment"]:
        body_xml.append(f"<!--{tpl['inside_comment']}-->")
        if 'comment' in event_types:
            body_events.append(("comment", tpl["inside_comment"]))

    body_xml.append("&e;")
    body_events.extend(fragment_events)

    if WITH_PIS and tpl["inside_pi"]:
        body_xml.append("<?outer data?>")
        if 'pi' in event_types:
            body_events.append(("pi", "outer data"))

    for name in tpl["after"]:
        sx, se = sibling(name)
        body_xml.append(sx)
        body_events.extend(se)

    doctype = f"<!DOCTYPE {root_qname} [ <!ENTITY e '{fragment}'> ]>"
    xml = (doctype + top_xml + f"<{root_qname}{decl}>"
           + "".join(body_xml) + f"</{root_qname}>")

    ns_events = [("start-ns", (prefix or "", uri))] if uri and 'start-ns' in event_types else []
    end_ns_events = [("end-ns", None)] if uri and 'end-ns' in event_types else []
    expected = top_events + ns_events
    if 'start' in event_types:
        expected.append(("start", root_tag))
    expected += body_events
    if 'end' in event_types:
        expected.append(("end", root_tag))
    expected += end_ns_events

    return xml, expected


class EtreeFixedCaseTest(unittest.TestCase):
    etree = etree

    CASES = [
        (
            "<a><b></b></a>",
            [("start", "a"), ("start", "b"), ("end", "b"), ("end", "a")],
        ),
        (
            "<a><b/><c><d></d><e/></c></a>",
            [
                ("start", "a"),
                ("start", "b"), ("end", "b"),
                ("start", "c"),
                ("start", "d"), ("end", "d"),
                ("start", "e"), ("end", "e"),
                ("end", "c"),
                ("end", "a"),
            ],
        ),
        (
            "<a><b><c><d/></c></b><e></e></a>",
            [
                ("start", "a"),
                ("start", "b"),
                ("start", "c"),
                ("start", "d"), ("end", "d"),
                ("end", "c"),
                ("end", "b"),
                ("start", "e"), ("end", "e"),
                ("end", "a"),
            ],
        ),
        (
            '<p:a xmlns:p="urn:x"><b/></p:a>',
            [
                ("start-ns", ("p", "urn:x")),
                ("start", "{urn:x}a"),
                ("start", "b"), ("end", "b"),
                ("end", "{urn:x}a"),
                ("end-ns", None),
            ],
        ),
        (
            '<tag xmlns="abc" xmlns:p="xyz"><p:child/></tag>',
            [
                ("start-ns", ("", "abc")),
                ("start-ns", ("p", "xyz")),
                ("start", "{abc}tag"),
                ("start", "{xyz}child"), ("end", "{xyz}child"),
                ("end", "{abc}tag"),
                ("end-ns", None),
                ("end-ns", None),
            ],
        ),
        (
            "<!--top--><?pi-top x?><a><?in-pi y?><!--in--><b/></a>",
            [
                ("comment", "top"),
                ("pi", "pi-top x"),
                ("start", "a"),
                ("pi", "in-pi y"),
                ("comment", "in"),
                ("start", "b"), ("end", "b"),
                ("end", "a"),
            ],
        ),
    ]

    def test_fixed_cases(self):
        parser_class = self.etree.XMLPullParser

        for xml, expected in self.CASES:
            for chunk_size in ((1, 3, len(xml)) if WITH_CHUNKS else (len(xml),)):
                with self.subTest(xml=xml, chunk_size=chunk_size):
                    self.assertEqual(feed_in_chunks(xml, chunk_size, parser_class), expected)


class ElementTreeFixedCaseTest(EtreeFixedCaseTest):
    etree = ElementTree


class EtreeEnumeratedNestingTest(unittest.TestCase):
    etree = etree

    def test_enumerated_nesting(self):
        parser_class = self.etree.XMLPullParser

        for height in range(1, WITH_SHAPE_HIGHT+1):
            for shape_index, shape in enumerate(enumerate_shapes(height)):
                for events_count in range(1, len(EVENT_TYPES)):
                    for event_types in itertools.combinations(EVENT_TYPES, events_count):
                        xml, expected = build_document(shape, event_types)
                        for chunk_size in ((1, 3, len(xml)) if WITH_CHUNKS else (len(xml),)):
                            with self.subTest(height=height, shape=shape_index, event_types=event_types,
                                              chunk_size=chunk_size, xml=xml):
                                self.assertEqual(feed_in_chunks(xml, chunk_size, parser_class, event_types), expected)


class ElementTreeEnumeratedNestingTest(EtreeEnumeratedNestingTest):
    etree = ElementTree


class EtreeEntityResolutionTest(unittest.TestCase):
    etree = etree

    def test_fixed_entity(self):
        parser_class = self.etree.XMLPullParser

        xml = ("<!DOCTYPE r [ <!ENTITY e \"<item a1='v1'><name>zz</name></item>\"> ]>\n"
               "<r>&e;</r>")
        expected = [
            ("start", "r"),
            ("start", "item"),
            ("start", "name"), ("end", "name"),
            ("end", "item"),
            ("end", "r"),
        ]
        for chunk_size in ((1, 3, len(xml)) if WITH_CHUNKS else (len(xml),)):
            with self.subTest(chunk_size=chunk_size):
                self.assertEqual(feed_in_chunks(xml, chunk_size, parser_class), expected)

    def test_enumerated_entities_in_outer_templates(self):
        parser_class = self.etree.XMLPullParser

        for tpl_index, tpl in enumerate(OUTER_TEMPLATES):
            # Namespaces in scope at the reference point, as the entity sees them.
            scope = {tpl["root_prefix"]: tpl["root_uri"]} if tpl["root_uri"] else {}
            for shape_index, shape in enumerate(enumerate_shapes(WITH_SHAPE_HIGHT)):
                for events_count in range(1, len(EVENT_TYPES)):
                    for event_types in itertools.combinations(EVENT_TYPES, events_count):
                        fragment, fragment_events = build_element(shape, event_types, [0], scope)
                        xml, expected = build_outer(tpl, event_types, fragment, fragment_events)
                        for chunk_size in ((1, 3, len(xml)) if WITH_CHUNKS else (len(xml),)):
                            with self.subTest(template=tpl_index, shape=shape_index, event_types=event_types,
                                            chunk_size=chunk_size, xml=xml):
                                self.assertEqual(feed_in_chunks(xml, chunk_size, parser_class, event_types), expected)


class ElementTreeEntityResolutionTest(EtreeEntityResolutionTest):
    etree = ElementTree


class EtreeEntityParseFailureTest(unittest.TestCase):
    etree = etree

    def test_entity_parse_failure(self):
        parser_class = self.etree.XMLPullParser

        xml = ("<!DOCTYPE r [ <!ENTITY e \"<!--Ecomment1--><item a1='v1'><name>zz</name><!--Ecomment2--></item></FAIL>\"> ]>\n"
               "<!--Ocomment1--><r>&e;</r><!--Ocomment2-->")

        events = []
        with self.assertRaises(self.etree.XMLSyntaxError):
            parser = parser_class(events=EVENT_TYPES)
            chunk_size = 3
            for pos in range(0, len(xml), chunk_size):
                parser.feed(xml[pos:pos + chunk_size])
                events.extend(normalize(parser.read_events()))

        expected = [
            ("comment", "Ocomment1"),
            ("start", "r"),
            # No events reported from failed entities.
        ]
        self.assertEqual(events, expected)

    def test_entity_parse_failure_later(self):
        parser_class = self.etree.XMLPullParser

        xml = ("<!DOCTYPE r [ <!ENTITY e \"<!--Ecomment1--><item a1='v1'><name>zz</name><!--Ecomment2--></item>\"> ]>\n"
               "<!--Ocomment1--><r>&e;<!--Ocomment2--></FAIL><!--Ocomment3--></r>")

        events = []
        with self.assertRaises(self.etree.XMLSyntaxError):
            parser = parser_class(events=EVENT_TYPES)
            chunk_size = 3
            for pos in range(0, len(xml), chunk_size):
                parser.feed(xml[pos:pos + chunk_size])
                events.extend(normalize(parser.read_events()))

        expected = [
            ("comment", "Ocomment1"),
            ("start", "r"),
            ('comment', 'Ecomment1'),
            ('start', 'item'),
            ('start', 'name'),
            ('end', 'name'),
            ('comment', 'Ecomment2'),
            ('end', 'item'),
            ('comment', 'Ocomment2'),
        ]
        self.assertEqual(events, expected)


def test_suite():
    suite = unittest.TestSuite()

    if WITH_ETREE and etree:
        suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(EtreeFixedCaseTest)])
        if WITH_FUZZING:
            suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(EtreeEnumeratedNestingTest)])
        if WITH_PARSED_ENTITIES:
            suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(EtreeEntityResolutionTest)])
            suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(EtreeEntityParseFailureTest)])

    if WITH_ELEMENTTREE and ElementTree:
        suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(ElementTreeFixedCaseTest)])
        if WITH_FUZZING:
            suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(ElementTreeEnumeratedNestingTest)])
        if WITH_PARSED_ENTITIES:
            suite.addTests([unittest.defaultTestLoader.loadTestsFromTestCase(ElementTreeEntityResolutionTest)])

    return suite


if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
