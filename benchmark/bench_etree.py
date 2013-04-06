import sys, copy
from itertools import *

import benchbase
from benchbase import (with_attributes, with_text, onlylib,
                       serialized, children, nochange, BytesIO)

TEXT  = "some ASCII text"
UTEXT = u"some klingon: \F8D2"

############################################################
# Benchmarks
############################################################

class BenchMark(benchbase.TreeBenchMark):
    @nochange
    def bench_iter_children(self, root):
        for child in root:
            pass

    @nochange
    def bench_iter_children_reversed(self, root):
        for child in reversed(root):
            pass

    @nochange
    def bench_first_child(self, root):
        for i in self.repeat1000:
            child = root[0]

    @nochange
    def bench_last_child(self, root):
        for i in self.repeat1000:
            child = root[-1]

    @nochange
    def bench_middle_child(self, root):
        pos = len(root) // 2
        for i in self.repeat1000:
            child = root[pos]

    @nochange
    @with_attributes(False)
    @with_text(text=True)
    def bench_tostring_text_ascii(self, root):
        self.etree.tostring(root, method="text")

    @nochange
    @with_attributes(False)
    @with_text(text=True, utext=True)
    def bench_tostring_text_unicode(self, root):
        self.etree.tostring(root, method="text", encoding='unicode')

    @nochange
    @with_attributes(False)
    @with_text(text=True, utext=True)
    def bench_tostring_text_utf16(self, root):
        self.etree.tostring(root, method="text", encoding='UTF-16')

    @nochange
    @with_attributes(False)
    @with_text(text=True, utext=True)
    @onlylib('lxe')
    @children
    def bench_tostring_text_utf8_with_tail(self, children):
        for child in children:
            self.etree.tostring(child, method="text",
                                encoding='UTF-8', with_tail=True)

    @nochange
    @with_attributes(True, False)
    @with_text(text=True, utext=True)
    def bench_tostring_utf8(self, root):
        self.etree.tostring(root, encoding='UTF-8')

    @nochange
    @with_attributes(True, False)
    @with_text(text=True, utext=True)
    def bench_tostring_utf16(self, root):
        self.etree.tostring(root, encoding='UTF-16')

    @nochange
    @with_attributes(True, False)
    @with_text(text=True, utext=True)
    def bench_tostring_utf8_unicode_XML(self, root):
        xml = self.etree.tostring(root, encoding='UTF-8').decode('UTF-8')
        self.etree.XML(xml)

    @nochange
    @with_attributes(True, False)
    @with_text(text=True, utext=True)
    def bench_write_utf8_parse_bytesIO(self, root):
        f = BytesIO()
        self.etree.ElementTree(root).write(f, encoding='UTF-8')
        f.seek(0)
        self.etree.parse(f)

    @with_attributes(True, False)
    @with_text(text=True, utext=True)
    @serialized
    def bench_parse_bytesIO(self, root_xml):
        f = BytesIO(root_xml)
        self.etree.parse(f)

    @with_attributes(True, False)
    @with_text(text=True, utext=True)
    @serialized
    def bench_XML(self, root_xml):
        self.etree.XML(root_xml)

    @with_attributes(True, False)
    @with_text(text=True, utext=True)
    @serialized
    def bench_iterparse_bytesIO(self, root_xml):
        f = BytesIO(root_xml)
        for event, element in self.etree.iterparse(f):
            pass

    @with_attributes(True, False)
    @with_text(text=True, utext=True)
    @serialized
    def bench_iterparse_bytesIO_clear(self, root_xml):
        f = BytesIO(root_xml)
        for event, element in self.etree.iterparse(f):
            element.clear()

    def bench_append_from_document(self, root1, root2):
        # == "1,2 2,3 1,3 3,1 3,2 2,1" # trees 1 and 2, or 2 and 3, or ...
        for el in root2:
            root1.append(el)

    def bench_insert_from_document(self, root1, root2):
        pos = len(root1)//2
        for el in root2:
            root1.insert(pos, el)
            pos = pos + 1

    def bench_rotate_children(self, root):
        # == "1 2 3" # runs on any single tree independently
        for i in range(100):
            el = root[0]
            del root[0]
            root.append(el)

    def bench_reorder(self, root):
        for i in range(1,len(root)//2):
            el = root[0]
            del root[0]
            root[-i:-i] = [ el ]

    def bench_reorder_slice(self, root):
        for i in range(1,len(root)//2):
            els = root[0:1]
            del root[0]
            root[-i:-i] = els

    def bench_clear(self, root):
        root.clear()

    @nochange
    @children
    def bench_has_children(self, children):
        for child in children:
            if child and child and child and child and child:
                pass

    @nochange
    @children
    def bench_len(self, children):
        for child in children:
            map(len, repeat(child, 20))

    @children
    def bench_create_subelements(self, children):
        SubElement = self.etree.SubElement
        for child in children:
            SubElement(child, '{test}test')

    def bench_append_elements(self, root):
        Element = self.etree.Element
        for child in root:
            el = Element('{test}test')
            child.append(el)

    @nochange
    @children
    def bench_makeelement(self, children):
        empty_attrib = {}
        for child in children:
            child.makeelement('{test}test', empty_attrib)

    @nochange
    @children
    def bench_create_elements(self, children):
        Element = self.etree.Element
        for child in children:
            Element('{test}test')

    @children
    def bench_replace_children_element(self, children):
        Element = self.etree.Element
        for child in children:
            el = Element('{test}test')
            child[:] = [el]

    @children
    def bench_replace_children(self, children):
        els = [ self.etree.Element("newchild") ]
        for child in children:
            child[:] = els

    def bench_remove_children(self, root):
        for child in root:
            root.remove(child)

    def bench_remove_children_reversed(self, root):
        for child in reversed(root):
            root.remove(child)

    @children
    def bench_set_attributes(self, children):
        for child in children:
            child.set('a', 'bla')

    @with_attributes(True)
    @children
    @nochange
    def bench_get_attributes(self, children):
        for child in children:
            child.get('bla1')
            child.get('{attr}test1')

    @children
    def bench_setget_attributes(self, children):
        for child in children:
            child.set('a', 'bla')
        for child in children:
            child.get('a')

    @nochange
    def bench_root_getchildren(self, root):
        root.getchildren()

    @nochange
    def bench_root_list_children(self, root):
        list(root)

    @nochange
    @children
    def bench_getchildren(self, children):
        for child in children:
            child.getchildren()

    @nochange
    @children
    def bench_get_children_slice(self, children):
        for child in children:
            child[:]

    @nochange
    @children
    def bench_get_children_slice_2x(self, children):
        for child in children:
            child[:]
            child[:]

    @nochange
    @children
    @with_attributes(True, False)
    @with_text(utext=True, text=True, no_text=True)
    def bench_deepcopy(self, children):
        for child in children:
            copy.deepcopy(child)

    @nochange
    @with_attributes(True, False)
    @with_text(utext=True, text=True, no_text=True)
    def bench_deepcopy_all(self, root):
        copy.deepcopy(root)

    @nochange
    @children
    def bench_tag(self, children):
        for child in children:
            child.tag

    @nochange
    @children
    def bench_tag_repeat(self, children):
        for child in children:
            for i in self.repeat100:
                child.tag

    @nochange
    @with_text(utext=True, text=True, no_text=True)
    @children
    def bench_text(self, children):
        for child in children:
            child.text

    @nochange
    @with_text(utext=True, text=True, no_text=True)
    @children
    def bench_text_repeat(self, children):
        for child in children:
            for i in self.repeat500:
                child.text

    @children
    def bench_set_text(self, children):
        text = TEXT
        for child in children:
            child.text = text

    @children
    def bench_set_utext(self, children):
        text = UTEXT
        for child in children:
            child.text = text

    @nochange
    @onlylib('lxe')
    def bench_index(self, root):
        for child in root:
            root.index(child)

    @nochange
    @onlylib('lxe')
    def bench_index_slice(self, root):
        for child in root[5:100]:
            root.index(child, 5, 100)

    @nochange
    @onlylib('lxe')
    def bench_index_slice_neg(self, root):
        for child in root[-100:-5]:
            root.index(child, start=-100, stop=-5)

    @nochange
    def bench_iter_all(self, root):
        list(root.iter())

    @nochange
    def bench_iter_one_at_a_time(self, root):
        list(islice(root.iter(), 2**30, None))

    @nochange
    def bench_iter_islice(self, root):
        list(islice(root.iter(), 10, 110))

    @nochange
    def bench_iter_tag(self, root):
        list(islice(root.iter(self.SEARCH_TAG), 3, 10))

    @nochange
    def bench_iter_tag_all(self, root):
        list(root.iter(self.SEARCH_TAG))

    @nochange
    def bench_iter_tag_one_at_a_time(self, root):
        list(islice(root.iter(self.SEARCH_TAG), 2**30, None))

    @nochange
    def bench_iter_tag_none(self, root):
        list(root.iter("{ThisShould}NeverExist"))

    @nochange
    def bench_iter_tag_text(self, root):
        [ e.text for e in root.iter(self.SEARCH_TAG) ]

    @nochange
    def bench_findall(self, root):
        root.findall(".//*")

    @nochange
    def bench_findall_child(self, root):
        root.findall(".//*/" + self.SEARCH_TAG)

    @nochange
    def bench_findall_tag(self, root):
        root.findall(".//" + self.SEARCH_TAG)

    @nochange
    def bench_findall_path(self, root):
        root.findall(".//*[%s]/./%s/./*" % (self.SEARCH_TAG, self.SEARCH_TAG))

    @nochange
    @onlylib('lxe')
    def bench_xpath_path(self, root):
        ns, tag = self.SEARCH_TAG[1:].split('}')
        root.xpath(".//*[p:%s]/./p:%s/./*" % (tag,tag),
                   namespaces = {'p':ns})

    @nochange
    def bench_iterfind(self, root):
        list(root.iterfind(".//*"))

    @nochange
    def bench_iterfind_tag(self, root):
        list(root.iterfind(".//" + self.SEARCH_TAG))

    @nochange
    def bench_iterfind_islice(self, root):
        list(islice(root.iterfind(".//*"), 10, 110))

    _bench_xpath_single_xpath = None

    @nochange
    @onlylib('lxe')
    def bench_xpath_single(self, root):
        xpath = self._bench_xpath_single_xpath
        if xpath is None:
            ns, tag = self.SEARCH_TAG[1:].split('}')
            xpath = self._bench_xpath_single_xpath = self.etree.XPath(
                './/p:%s[1]' % tag, namespaces={'p': ns})
        xpath(root)

    @nochange
    def bench_find_single(self, root):
        root.find(".//%s" % self.SEARCH_TAG)

    @nochange
    def bench_iter_single(self, root):
        next(root.iter(self.SEARCH_TAG))

    _bench_xpath_two_xpath = None

    @nochange
    @onlylib('lxe')
    def bench_xpath_two(self, root):
        xpath = self._bench_xpath_two_xpath
        if xpath is None:
            ns, tag = self.SEARCH_TAG[1:].split('}')
            xpath = self._bench_xpath_two_xpath = self.etree.XPath(
                './/p:%s[position() < 3]' % tag, namespaces={'p': ns})
        xpath(root)

    @nochange
    def bench_iterfind_two(self, root):
        it = root.iterfind(".//%s" % self.SEARCH_TAG)
        next(it)
        next(it)

    @nochange
    def bench_iter_two(self, root):
        it = root.iter(self.SEARCH_TAG)
        next(it)
        next(it)


if __name__ == '__main__':
    benchbase.main(BenchMark)
