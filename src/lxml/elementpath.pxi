# cython: language_level=3

#
# ElementTree
# $Id: ElementPath.py 3375 2008-02-13 08:05:08Z fredrik $
#
# limited xpath support for element trees
#
# history:
# 2003-05-23 fl   created
# 2003-05-28 fl   added support for // etc
# 2003-08-27 fl   fixed parsing of periods in element names
# 2007-09-10 fl   new selection engine
# 2007-09-12 fl   fixed parent selector
# 2007-09-13 fl   added iterfind; changed findall to return a list
# 2007-11-30 fl   added namespaces support
# 2009-10-30 fl   added child element value filter
#
# Copyright (c) 2003-2009 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2009 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

##
# Implementation module for XPath support.  There's usually no reason
# to import this module directly; the <b>ElementTree</b> does this for
# you, if needed.
##

import cython

# Original ElementPath regex for easier CPython diff-comparison.
cdef str xpath_tokenizer_re
xpath_tokenizer_re = (
    "("
    "'[^']*'|\"[^\"]*\"|"
    "::|"
    "//?|"
    r"\.\.|"
    r"\(\)|"
    r"!=|"
    r"[/.*:\[\]\(\)@=])|"
    r"((?:\{[^}]+\})?[^/\[\]\(\)@!=\s]+)|"
    r"\s+"
    )

cdef object _tokenize_xpath = re.compile(
    "("
    # quoted strings (single or double)
    r"'[^']*'|"
    r'"[^"]*"|'
    # operators: ::, /, //, .., ()
    r"::|"
    r"//?|"
    r"\.\.|"
    r"\(\)|"
    r"!=|"
    # single-char punctuation
    r"[.*:\[\]\(\)@=]"
    ")|"
    # names, with optional {namespace}name
    "("
    r"\{[^}]*\}[^{/\[\]\(\)@!=\s]+|"
    r"[^/\[\]\(\)@!=\s]+"
    ")|"
    # ignored whitespace
    r"\s+"
).findall

cdef object _xpath_tokenizer

def _xpath_tokenizer(pattern, namespaces=None, with_prefixes=True):
    # ElementTree uses '', lxml used None originally.
    default_namespace = (namespaces.get(None) or namespaces.get('')) if namespaces else None
    parsing_attribute = False
    for token in _tokenize_xpath(pattern):
        ttype, tag = token
        if tag and tag[0] != "{":
            if ":" in tag and with_prefixes:
                prefix, uri = tag.split(":", 1)
                try:
                    if not namespaces:
                        raise KeyError
                    yield ttype, "{%s}%s" % (namespaces[prefix], uri)
                except KeyError:
                    raise SyntaxError("prefix %r not found in prefix map" % prefix) from None
            elif tag.isdecimal():
                yield token  # index
            elif default_namespace and not parsing_attribute:
                yield ttype, "{%s}%s" % (default_namespace, tag)
            else:
                yield token
            parsing_attribute = False
        else:
            yield token
            parsing_attribute = ttype == '@'


# --------------------------------------------------------------------
### Tag matching

@cython.final
@cython.internal
cdef class _MultiTagMatcher:
    """
    Match an xmlNode against a list of tags.
    """
    cdef list _py_tags
    cdef qname* _cached_tags
    cdef size_t _cached_tags_count
    cdef size_t _cached_doc_dict_size
    cdef _Document _cached_doc
    cdef int _node_types
    cdef bint _all_tags_in_dict

    def __cinit__(self, tags):
        self._initTagMatch(tags)

    def __dealloc__(self):
        self._clear()

    def __repr__(self):
        cdef bytes href, name
        if self._py_tags:
            tags = [
                repr(f"{{{href.decode('utf8')}}}{name.decode('utf8')}" if href else name.decode('utf8'))
                for href, name in self._py_tags
            ]
        else:
            tags = []

        if self._node_types & (1 << tree.XML_COMMENT_NODE):
            tags.append('Comment')
        if self._node_types & (1 << tree.XML_PI_NODE):
            tags.append('ProcessingInstruction')
        if self._node_types & (1 << tree.XML_ENTITY_REF_NODE):
            tags.append('Entity')
        if self._node_types & (1 << tree.XML_ELEMENT_NODE):
            tags.append('Element')

        return f"_MultiTagMatcher([{', '.join(tags)}])"

    cdef copy(self):
        matcher: _MultiTagMatcher = _newMultiTagMatcher(None)
        matcher._py_tags = self._py_tags
        matcher._node_types = self._node_types
        return matcher

    cdef bint rejectsAll(self) noexcept:
        return not self._cached_tags_count and not self._node_types

    cdef bint rejectsAllAttributes(self) noexcept:
        return not self._cached_tags_count

    cdef bint matchesType(self, int node_type) noexcept:
        if node_type == tree.XML_ELEMENT_NODE and self._cached_tags_count:
            return True
        return self._node_types & (1 << node_type)

    cdef void _clear(self) noexcept:
        cdef size_t i, count
        count = self._cached_tags_count
        self._cached_tags_count = 0
        if self._cached_tags:
            for i in range(count):
                cpython.ref.Py_XDECREF(self._cached_tags[i].href)
            python.lxml_free(self._cached_tags)
            self._cached_tags = NULL

    cdef _initTagMatch(self, tags):
        if tags is None or tags == ():
            # no selection in tags argument => match anything
            self._node_types = (
                1 << tree.XML_COMMENT_NODE |
                1 << tree.XML_PI_NODE |
                1 << tree.XML_ENTITY_REF_NODE |
                1 << tree.XML_ELEMENT_NODE)
        else:
            self._py_tags = []
            self._storeTags(tags, set())

    cdef _storeTags(self, tag, set seen):
        if tag is Comment:
            self._node_types |= 1 << tree.XML_COMMENT_NODE
        elif tag is ProcessingInstruction:
            self._node_types |= 1 << tree.XML_PI_NODE
        elif tag is Entity:
            self._node_types |= 1 << tree.XML_ENTITY_REF_NODE
        elif tag is Element:
            self._node_types |= 1 << tree.XML_ELEMENT_NODE
        elif python._isString(tag):
            if tag in seen:
                return
            seen.add(tag)
            if tag in ('*', '{*}*'):
                self._node_types |= 1 << tree.XML_ELEMENT_NODE
            else:
                href, name = _getNsTag(tag)
                if name == b'*':
                    name = None
                if href is None:
                    href = b''  # no namespace
                elif href == b'*':
                    href = None  # wildcard: any namespace, including none
                self._py_tags.append((href, name))
        elif isinstance(tag, QName):
            self._storeTags(tag.text, seen)
        else:
            # support a sequence of tags
            for item in tag:
                self._storeTags(item, seen)

    cdef inline int cacheTags(self, _Document doc, bint force_into_dict=False) except -1:
        """
        Look up the tag names in the doc dict to enable string pointer comparisons.
        """
        same_doc = doc is self._cached_doc
        if same_doc and self._all_tags_in_dict:
            # All tags were already found in the document dict => dict growth is irrelevant.
            return 0

        cdef size_t dict_size = tree.xmlDictSize(doc._c_doc.dict)
        if same_doc and dict_size == self._cached_doc_dict_size:
            # doc and dict didn't change => names are already cached.
            return 0

        self._cacheTags(doc, force_into_dict)
        self._cached_doc = doc
        self._cached_doc_dict_size = dict_size
        return 0

    cdef int _cacheTags(self, _Document doc, bint force_into_dict=False) except -1:
        self._cached_tags_count = 0
        if not self._py_tags:
            self._all_tags_in_dict = True
            return 0
        if not self._cached_tags:
            self._cached_tags = <qname*>python.lxml_malloc(len(self._py_tags), sizeof(qname))
            if not self._cached_tags:
                self._cached_doc = None
                raise MemoryError()
        self._cached_tags_count = <size_t>_mapTagsToQnameMatchArray(
            doc._c_doc, self._py_tags, self._cached_tags, force_into_dict)
        self._all_tags_in_dict = self._cached_tags_count == len(self._py_tags)
        return 0

    cdef inline bint matches(self, xmlNode* c_node) noexcept:
        cdef qname* c_qname
        if self._node_types & (1 << c_node.type):
            return True
        elif c_node.type == tree.XML_ELEMENT_NODE:
            for c_qname in self._cached_tags[:self._cached_tags_count]:
                if _tagMatchesExactly(c_node, c_qname):
                    return True
        return False

    cdef inline bint matchesNsTag(self, const_xmlChar* c_href,
                                  const_xmlChar* c_name) noexcept:
        cdef qname* c_qname
        if self._node_types & (1 << tree.XML_ELEMENT_NODE):
            return True
        for c_qname in self._cached_tags[:self._cached_tags_count]:
            if _nsTagMatchesExactly(c_href, c_name, c_qname):
                return True
        return False

    cdef inline bint matchesAttribute(self, xmlAttr* c_attr) noexcept:
        """Attribute matches differ from Element matches in that they do
        not care about node types.
        """
        cdef qname* c_qname
        for c_qname in self._cached_tags[:self._cached_tags_count]:
            if _tagMatchesExactly(<xmlNode*>c_attr, c_qname):
                return True
        return False


cdef _MultiTagMatcher _newMultiTagMatcher(tags):
    return <_MultiTagMatcher> _MultiTagMatcher.__new__(_MultiTagMatcher, tags)


# --------------------------------------------------------------------
### Element iteration

cdef class _ElementMatchIterator:
    cdef _Element _node
    cdef _node_to_node_function _next_element
    cdef _MultiTagMatcher _matcher

    @cython.final
    cdef _initTagMatcher(self, tags):
        self._matcher = _newMultiTagMatcher(tags)

    def __iter__(self):
        return self

    @cython.final
    cdef int _storeNext(self, _Element node) except -1:
        doc = node._doc
        doc.lock_read()
        try:
            self._matcher.cacheTags(doc)
            c_node = self._next_element(node._c_node)
            while c_node is not NULL and not self._matcher.matches(c_node):
                c_node = self._next_element(c_node)
            # store Python ref to next node to make sure it's kept alive
            self._node = _elementFactory(doc, c_node) if c_node is not NULL else None
        finally:
            doc.unlock_read()
        return 0

    def __next__(self):
        cdef _Element current_node = self._node
        if current_node is None:
            raise StopIteration
        self._storeNext(current_node)
        return current_node


cdef class ElementChildIterator(_ElementMatchIterator):
    """ElementChildIterator(self, node, tag=None, reversed=False)
    Iterates over the children of an element.
    """
    def __cinit__(self, _Element node not None, tag=None, *, bint reversed=False):
        cdef xmlNode* c_node
        _assertValidNode(node)
        self._initTagMatcher(tag)

        doc = node._doc
        doc.lock_read()
        try:
            if reversed:
                c_node = _findChildBackwards(node._c_node, 0)
                self._next_element = _previousElement
            else:
                c_node = _findChildForwards(node._c_node, 0)
                self._next_element = _nextElement
            self._matcher.cacheTags(node._doc)
            while c_node is not NULL and not self._matcher.matches(c_node):
                c_node = self._next_element(c_node)
            # store Python ref to next node to make sure it's kept alive
            self._node = _elementFactory(node._doc, c_node) if c_node is not NULL else None
        finally:
            doc.unlock_read()


cdef class SiblingsIterator(_ElementMatchIterator):
    """SiblingsIterator(self, node, tag=None, preceding=False)
    Iterates over the siblings of an element.

    You can pass the boolean keyword ``preceding`` to specify the direction.
    """
    def __cinit__(self, _Element node not None, tag=None, *, bint preceding=False):
        _assertValidNode(node)
        self._initTagMatcher(tag)
        if preceding:
            self._next_element = _previousElement
        else:
            self._next_element = _nextElement
        self._storeNext(node)


cdef class AncestorsIterator(_ElementMatchIterator):
    """AncestorsIterator(self, node, tag=None)
    Iterates over the ancestors of an element (from parent to parent).
    """
    def __cinit__(self, _Element node not None, tag=None):
        _assertValidNode(node)
        self._initTagMatcher(tag)
        self._next_element = _parentElement
        self._storeNext(node)


cdef class ElementDepthFirstIterator:
    """ElementDepthFirstIterator(self, node, tag=None, inclusive=True)
    Iterates over an element and its sub-elements in document order (depth
    first pre-order).

    Note that this also includes comments, entities and processing
    instructions.  To filter them out, check if the ``tag`` property
    of the returned element is a string (i.e. not None and not a
    factory function), or pass the ``Element`` factory for the ``tag``
    argument to receive only Elements.

    If the optional ``tag`` argument is not None, the iterator returns only
    the elements that match the respective name and namespace.

    The optional boolean argument 'inclusive' defaults to True and can be set
    to False to exclude the start element itself.

    Note that the behaviour of this iterator is completely undefined if the
    tree it traverses is modified during iteration.
    """
    # we keep Python references here to control GC
    # keep the next Element after the one we return, and the (s)top node
    cdef _Element _next_node
    cdef _Element _top_node
    cdef _MultiTagMatcher _matcher

    def __cinit__(self, _Element node not None, tag=None, *, bint inclusive=True):
        _assertValidNode(node)
        self._top_node  = node
        self._next_node = node
        self._matcher = _newMultiTagMatcher(tag)
        doc = node._doc
        doc.lock_read()
        try:
            self._matcher.cacheTags(node._doc)
            if inclusive and not self._matcher.matches(node._c_node):
                inclusive = False
        finally:
            doc.unlock_read()

        if not inclusive:
            # find start node (this cannot raise StopIteration, self._next_node != None)
            next(self)

    def __iter__(self):
        return self

    def __next__(self):
        cdef xmlNode* c_node
        cdef _Element current_node = self._next_node
        if current_node is None:
            raise StopIteration
        doc = current_node._doc
        doc.lock_read()
        try:
            c_node = current_node._c_node
            self._matcher.cacheTags(current_node._doc)
            c_node = _nextNodeDepthFirst(self._matcher, self._top_node._c_node, c_node)
            if c_node is NULL:
                self._next_node = None
            else:
                self._next_node = _elementFactory(current_node._doc, c_node)
        finally:
            doc.unlock_read()
        return current_node


cdef xmlNode* _nextNodeDepthFirst(_MultiTagMatcher matcher, xmlNode* c_top_node, xmlNode* c_node) noexcept:
    if not matcher._cached_tags_count:
        # no tag name was found in the dict => not in document either
        # try to match by node type
        c_node = _nextNodeAnyTag(matcher, c_top_node, c_node)
    else:
        c_node = _nextNodeMatchTag(matcher, c_top_node, c_node)
    return c_node


cdef xmlNode* _nextNodeAnyTag(_MultiTagMatcher matcher, xmlNode* c_top_node, xmlNode* c_node) noexcept:
    cdef int node_types = matcher._node_types
    if not node_types:
        return NULL
    tree.BEGIN_FOR_EACH_ELEMENT_FROM(c_top_node, c_node, 0)
    if node_types & (1 << c_node.type):
        return c_node
    tree.END_FOR_EACH_ELEMENT_FROM(c_node)
    return NULL


cdef xmlNode* _nextNodeMatchTag(_MultiTagMatcher matcher, xmlNode* c_top_node, xmlNode* c_node) noexcept:
    tree.BEGIN_FOR_EACH_ELEMENT_FROM(c_top_node, c_node, 0)
    if matcher.matches(c_node):
        return c_node
    tree.END_FOR_EACH_ELEMENT_FROM(c_node)
    return NULL


# --------------------------------------------------------------------
### ElementPath evaluators

@cython.internal
cdef class _PathEvaluator:
    """Base class for all path evaluators."""

    cdef _PathEvaluator copy(self):
        """Return a per-run copy of this evaluator.
        This method can be overridden by subclasses if they need to separate their runtime state.
        Idempotent evaluators may return `self`.
        """
        return self

    cdef int prepare_match(self, _Document doc):
        """Do anything necessary to initialise the evaluator before starting the path search.
        """
        pass

    cdef xmlNode* reset_nodeset(self):
        """Inform the evaluator that the processing of a nodeset has ended.
        May returns an xmlNode* if one is left for processing.
        Otherwise, returns NULL.
        """
        return NULL

    cdef xmlNode* first_node(self, xmlNode* c_node):
        """Find the first node matched by this evaluator.
        `c_node` is the node that was matched by the previous evaluator in the path.
        This method can be overridden by subclasses.
        """
        return self.next_node(c_node)

    cdef xmlNode* next_node(self, xmlNode* c_node):
        """Find the next matching node, given the last matching `c_node` of this evaluator.
        This method must be overridden by subclasses.
        """
        return NULL


@cython.final
@cython.internal
cdef class _ChildPathEvaluator(_PathEvaluator):
    """Evaluator for child path expressions."""
    cdef _MultiTagMatcher _matcher

    def __cinit__(self, tag):
        if type(tag) is _MultiTagMatcher:
            # Special .copy() bypass.
            self._matcher = <_MultiTagMatcher> tag
        else:
            self._matcher = _newMultiTagMatcher(tag)

    def __repr__(self):
        return f"child::({self._matcher})"

    cdef _ChildPathEvaluator copy(self):
        return <_ChildPathEvaluator> _ChildPathEvaluator.__new__(
            _ChildPathEvaluator, self._matcher.copy())

    cdef int prepare_match(self, _Document doc):
        self._matcher.cacheTags(doc)

    cdef xmlNode* first_node(self, xmlNode* c_node):
        c_node = _find_next_element(c_node.children)
        while c_node is not NULL and not self._matcher.matches(c_node):
            c_node = _find_next_element(c_node.next)
        return c_node

    cdef xmlNode* next_node(self, xmlNode* c_node):
        while True:
            c_node = _find_next_element(c_node.next)
            if c_node is NULL or self._matcher.matches(c_node):
                return c_node


cdef xmlNode* _find_next_element(xmlNode* c_node):
    while c_node and c_node.type != tree.XML_ELEMENT_NODE:
        c_node = c_node.next
    return c_node


@cython.final
@cython.internal
cdef class _StarPathEvaluator(_PathEvaluator):
    """Evaluator for wildcard child path expressions."""

    def __repr__(self):
        return f"child::*"

    cdef xmlNode* first_node(self, xmlNode* c_node):
        return _find_next_element(c_node.children)

    cdef xmlNode* next_node(self, xmlNode* c_node):
        return _find_next_element(c_node.next)


@cython.final
@cython.internal
cdef class _SelfPathEvaluator(_PathEvaluator):
    """Evaluator for self path expressions."""

    def __repr__(self):
        return f"."

    cdef xmlNode* first_node(self, xmlNode* c_node):
        return c_node

    cdef xmlNode* next_node(self, xmlNode* c_node):
        return NULL


@cython.final
@cython.internal
cdef class _NullPathEvaluator(_PathEvaluator):
    def __repr__(self):
        return f"false()"

    cdef xmlNode* first_node(self, xmlNode* c_node):
        return NULL


@cython.final
@cython.internal
cdef class _DescendantPathEvaluator(_PathEvaluator):
    """Evaluator for descendant path expressions."""
    cdef _MultiTagMatcher _matcher
    cdef xmlNode* _top_node

    def __cinit__(self, tag):
        if type(tag) is _MultiTagMatcher:
            # Special .copy() bypass.
            self._matcher = <_MultiTagMatcher> tag
        else:
            self._matcher = _newMultiTagMatcher(tag)

    def __repr__(self):
        return f"descendant::({self._matcher})"

    cdef _DescendantPathEvaluator copy(self):
        return <_DescendantPathEvaluator> _DescendantPathEvaluator.__new__(
            _DescendantPathEvaluator, self._matcher.copy())

    cdef int prepare_match(self, _Document doc):
        self._matcher.cacheTags(doc)

    cdef xmlNode* first_node(self, xmlNode* c_node):
        self._top_node = c_node
        c_node = c_node.children
        if c_node and not self._matcher.matches(c_node):
            c_node = _nextNodeDepthFirst(self._matcher, self._top_node, c_node)
        return c_node

    cdef xmlNode* next_node(self, xmlNode* c_node):
        return _nextNodeDepthFirst(self._matcher, self._top_node, c_node)


@cython.final
@cython.internal
cdef class _ParentPathEvaluator(_PathEvaluator):
    """Evaluator for parent path expressions."""

    def __repr__(self):
        return f"parent::*"

    cdef xmlNode* first_node(self, xmlNode* c_node):
        c_parent = c_node.parent
        return c_parent if c_parent and _isElement(c_parent) else NULL

    cdef xmlNode* next_node(self, xmlNode* c_node):
        return NULL


@cython.final
@cython.internal
cdef class _IndexPathEvaluator(_PathEvaluator):
    """Evaluator for index path expressions."""
    cdef Py_ssize_t index, _counter

    def __cinit__(self, Py_ssize_t index):
        self.index = index  # 0-based

    def __repr__(self):
        return f"[{self.index}]"

    cdef _IndexPathEvaluator _copy(self):
        return <_IndexPathEvaluator> _IndexPathEvaluator.__new__(
            _IndexPathEvaluator, self.index)

    cdef xmlNode* reset_nodeset(self):
        self._counter = 0
        return NULL

    cdef xmlNode* first_node(self, xmlNode* c_node):
        cdef Py_ssize_t current = self._counter
        self._counter = current + 1
        return c_node if current == self.index else NULL

    cdef xmlNode* next_node(self, xmlNode* c_node):
        return NULL


@cython.final
@cython.internal
cdef class _NegIndexPathEvaluator(_PathEvaluator):
    """Evaluator for backwards index path expressions."""
    cdef Py_ssize_t index, _counter
    cdef xmlNode** node_window

    def __cinit__(self, Py_ssize_t c_index):
        c_index = -c_index
        self.index = c_index  # 1-based for modulus
        self.node_window = <xmlNode**> python.lxml_malloc(c_index, sizeof(xmlNode*))
        if self.node_window is NULL:
            raise MemoryError()

    def __repr__(self):
        return "[last()]" if self.index == 1 else f"[last()-{self.index-1}]"

    cdef _NegIndexPathEvaluator copy(self):
        return <_NegIndexPathEvaluator> _NegIndexPathEvaluator.__new__(
            _NegIndexPathEvaluator, -self.index)

    cdef xmlNode* reset_nodeset(self):
        cdef xmlNode* last_match = NULL
        if self._counter >= self.index:
            # Counter points at the oldest entry, one after the newest.
            last_match = self.node_window[self._counter % self.index]
        self._counter = 0
        return last_match

    cdef xmlNode* first_node(self, xmlNode* c_node):
        self.node_window[self._counter % self.index] = c_node
        self._counter += 1
        return NULL

    cdef xmlNode* next_node(self, xmlNode* c_node):
        return NULL


@cython.internal
cdef class _PredicatePathEvaluator(_PathEvaluator):
    """Evaluator for predicate path expressions."""

    cdef xmlNode* next_node(self, xmlNode* node):
        return NULL


@cython.final
@cython.internal
cdef class _AttributePredicatePathEvaluator(_PredicatePathEvaluator):
    """Evaluator for attribute predicate path expressions."""
    cdef bytes href, name, value
    cdef const_xmlChar* c_href
    cdef const_xmlChar* c_name
    cdef const_xmlChar* c_value
    cdef bint negated

    def __cinit__(self, name, value, bint negated=False):
        self.href, self.name = _getNsTag(name)
        self.c_name = self.name
        self.c_href = <const_xmlChar*> self.href if self.href is not None else NULL
        self.value = _utf8orNone(value)
        self.c_value = <const_xmlChar*> self.value if self.value is not None else NULL
        self.negated = negated

    def __repr__(self):
        name = self.name.decode('utf8')
        href = self.href.decode('utf8') if self.href else None
        tag = f"{{{href}}}{name}" if href else name
        return f"[@{tag} = {self.value.decode('utf8')!r}]" if self.value is not None else f"[@{tag}]"

    cdef xmlNode* first_node(self, xmlNode* c_node):
        if c_node.type != tree.XML_ELEMENT_NODE:
            return NULL
        if self.c_value is NULL:
            # Fast case, only need to check that it's there, not collect+copy the text content.
            if self.c_href is not NULL:
                has_attr = tree.xmlHasNsProp(c_node, self.c_name, self.c_href) is not NULL
            else:
                has_attr = tree.xmlHasProp(c_node, self.c_name) is not NULL
        else:
            if self.c_href is not NULL:
                c_attr_value = tree.xmlGetNsProp(c_node, self.c_name, self.c_href)
            else:
                c_attr_value = tree.xmlGetProp(c_node, self.c_name)
            if c_attr_value is NULL:
                # FIXME: Might also have been a memory allocation failure.
                return NULL
            has_attr = tree.xmlStrcmp(c_attr_value, self.c_value) == 0
            if self.negated:
                has_attr = not has_attr
            tree.xmlFree(c_attr_value)

        return c_node if has_attr else NULL


@cython.final
@cython.internal
cdef class _ChildPredicatePathEvaluator(_PredicatePathEvaluator):
    """Evaluator for child predicate path expressions."""
    cdef _MultiTagMatcher _matcher

    def __cinit__(self, tag):
        if type(tag) is _MultiTagMatcher:
            # Special .copy() bypass.
            self._matcher = <_MultiTagMatcher> tag
        else:
            self._matcher = _newMultiTagMatcher(tag)

    def __repr__(self):
        return f"[child::({self._matcher})]"

    cdef _ChildPredicatePathEvaluator copy(self):
        return <_ChildPredicatePathEvaluator> _ChildPredicatePathEvaluator.__new__(
            _ChildPredicatePathEvaluator, self._matcher.copy())

    cdef int prepare_match(self, _Document doc):
        self._matcher.cacheTags(doc)

    cdef xmlNode* first_node(self, xmlNode* c_node):
        c_child = _find_next_element(c_node.children)
        while c_child is not NULL and not self._matcher.matches(c_child):
            c_child = _find_next_element(c_child.next)
        return c_node if c_child else NULL


@cython.final
@cython.internal
cdef class _TextPredicatePathEvaluator(_PredicatePathEvaluator):
    """Evaluator for text predicate path expressions."""
    cdef bytes text
    cdef const_xmlChar* c_text
    cdef bint negated

    def __cinit__(self, text, bint negated=False):
        self.text = _utf8orNone(text)
        self.c_text = <const_xmlChar*> self.text if self.text else NULL
        self.negated = negated

    def __repr__(self):
        return f"[. = {self.text.decode('utf8') if self.text else ''!r}]"

    cdef xmlNode* first_node(self, xmlNode* c_node):
        has_text = _node_has_text(c_node, self.text, self.c_text)
        if self.negated:
            has_text = not has_text
        return c_node if has_text else NULL


@cython.final
@cython.internal
cdef class _ChildTextPredicatePathEvaluator(_PredicatePathEvaluator):
    """Evaluator for text-of-child predicate path expressions."""
    cdef _MultiTagMatcher _matcher
    cdef bytes text
    cdef const_xmlChar* c_text
    cdef bint negated

    def __cinit__(self, text, child_tag, bint negated=False):
        if type(child_tag) is _MultiTagMatcher:
            # Special .copy() bypass.
            self._matcher = <_MultiTagMatcher> child_tag
        else:
            self._matcher = _newMultiTagMatcher(child_tag)
        self.text = _utf8orNone(text)
        self.c_text = <const_xmlChar*> self.text if self.text else NULL
        self.negated = negated

    def __repr__(self):
        return f"[child::({self._matcher}) = {self.text.decode('utf8') if self.text else ''!r}]"

    cdef _ChildTextPredicatePathEvaluator copy(self):
        evaluator: _ChildTextPredicatePathEvaluator = <_ChildTextPredicatePathEvaluator> (
            _ChildTextPredicatePathEvaluator.__new__(
                _ChildTextPredicatePathEvaluator, None, self._matcher.copy(), self.negated))
        evaluator.text = self.text
        evaluator.c_text = self.c_text
        return evaluator

    cdef int prepare_match(self, _Document doc):
        self._matcher.cacheTags(doc)

    cdef xmlNode* first_node(self, xmlNode* c_node):
        c_child = c_node.children
        while True:
            c_child = _find_next_element(c_child)
            if c_child is NULL:
                return NULL
            if self._matcher.matches(c_child):
                has_text = _node_has_text(c_child, self.text, self.c_text)
                if self.negated:
                    has_text = not has_text
                if has_text:
                    return c_node
            c_child = c_child.next


cdef bint _node_has_text(xmlNode* c_node, bytes text, const_xmlChar* c_text):
    cdef const_xmlChar* c_node_text = NULL
    cdef size_t scount = 0

    c_text_node = c_first_text_node = _textNodeOrSkip(c_node.children)
    while c_text_node is not NULL:
        if c_text_node.content[0] != c'\0':
            c_node_text = c_text_node.content
        scount += 1
        c_child = c_text_node.next  # skip over known text nodes
        c_text_node = _textNodeOrSkip(c_text_node.next)

    # handle quick cases first
    if c_node_text is NULL:
        return c_text is NULL
    if c_text is NULL:
        return False
    if scount == 1:
        return tree.xmlStrcmp(c_node_text, c_text) == 0

    # Collecting multiple text nodes is costly either way, so let's not optimise it much.
    result = b''
    c_text_node = c_first_text_node
    while c_text_node is not NULL:
        result += <unsigned char*> c_text_node.content
        if len(result) > len(text):
            return False
        c_text_node = _textNodeOrSkip(c_text_node.next)
    return result == text


cdef _prepare_path_descendant(token):
    if token[0] == "*":
        tag = "*"
    elif not token[0]:
        tag = token[1]
    else:
        raise SyntaxError("invalid descendant")

    return _DescendantPathEvaluator(tag)


cdef _prepare_path_predicate(next):
    # FIXME: replace with real parser!!! refs:
    # http://javascript.crockford.com/tdop/tdop.html
    signature = ''
    predicate = []
    while 1:
        token = next()
        if token[0] == "]":
            break
        if token == ('', ''):
            # ignore whitespace
            continue
        if token[0] and token[0][:1] in "'\"":
            token = "'", token[0][1:-1]
        signature += token[0] or "-"
        predicate.append(token[1])

    # use signature to determine predicate type
    if signature == "@-":
        # [@attribute] predicate
        key = predicate[1]
        return _AttributePredicatePathEvaluator(key, None)
    if signature == "@-='" or signature == "@-!='":
        # [@attribute='value'] or [@attribute!='value']
        key = predicate[1]
        value = predicate[-1]
        negated = '!=' in signature
        return _AttributePredicatePathEvaluator(key, value, negated)
    if signature == "-" and not re.match(r"-?\d+$", predicate[0]):
        # [tag]
        tag = predicate[0]
        return _ChildPredicatePathEvaluator(tag)
    if signature == ".='" or signature == ".!='" or (
            (signature == "-='" or signature == "-!='")
            and not re.match(r"-?\d+$", predicate[0])):
        # [.='value'] or [tag='value'] or [.!='value'] or [tag!='value']
        tag = predicate[0]
        value = predicate[-1]
        negated = '!=' in signature
        return _ChildTextPredicatePathEvaluator(value, tag, negated) if tag else _TextPredicatePathEvaluator(value, negated)
    if signature == "-" or signature == "-()" or signature == "-()-":
        # [index] or [last()] or [last()-index]
        if signature == "-":
            # [index]
            index = int(predicate[0]) - 1
            if index < 0:
                if index == -1:
                    raise SyntaxError(
                        "indices in path predicates are 1-based, not 0-based")
                else:
                    raise SyntaxError("path index >= 1 expected")
        else:
            if predicate[0] != "last":
                raise SyntaxError("unsupported function")
            if signature == "-()-":
                try:
                    index = int(predicate[2]) - 1
                except ValueError:
                    raise SyntaxError("unsupported expression")
                if index > -2:
                    raise SyntaxError("path offset from last() must be negative")
            else:
                index = -1

        try:
            c_index: cython.Py_ssize_t = index
        except OverflowError:
            # Too large to ever find a child, but do not fail here.
            return _NullPathEvaluator()

        return _IndexPathEvaluator(index) if c_index >= 0 else _NegIndexPathEvaluator(index)

    raise SyntaxError("invalid predicate")


_cache = {}

cdef _build_path_iterator(path, namespaces, with_prefixes=True):
    """Compile a selector pattern into a list of selectors."""
    if path[-1:] == "/":
        path += "*"  # implicit all (FIXME: keep this?)

    if namespaces:
        # lxml originally used None for the default namespace but ElementTree uses the
        # more convenient (all-strings-dict) empty string, so we support both here,
        # preferring the more convenient '', as long as they aren't ambiguous.
        if None in namespaces:
            if '' in namespaces and namespaces[None] != namespaces['']:
                raise ValueError("Ambiguous default namespace provided: %r versus %r" % (
                    namespaces[None], namespaces['']))
            cache_key = (path, namespaces[None],) + tuple(sorted(
                item for item in namespaces.items() if item[0] is not None))
        else:
            cache_key = (path,) + tuple(sorted(namespaces.items()))
    else:
        cache_key = path

    try:
        return _cache[cache_key]
    except KeyError:
        pass

    if len(_cache) > 100:
        # Evict the oldest keys. Iteration is the only way to know the insertion order.
        to_evict = []
        for i, key in enumerate(_cache, 1):
            to_evict.append(key)
            if i == 8:
                break
        for key in to_evict:
            _cache.pop(key)

    if path[:1] == "/":
        raise SyntaxError("cannot use absolute path on element")
    stream = iter(_xpath_tokenizer(path, namespaces, with_prefixes=with_prefixes))
    try:
        _next = stream.next
    except AttributeError:
        # Python 3
        _next = stream.__next__
    try:
        token = _next()
    except StopIteration:
        raise SyntaxError("empty path expression") from None
    selectors = []
    while 1:
        try:
            op: str = token[0]
            if not op:
                selector = _ChildPathEvaluator(token[1])
            else:
                first_char = op[0]
                if first_char == '[':
                    selector = _prepare_path_predicate(_next)
                elif first_char == '*':
                    selector = _StarPathEvaluator()
                elif first_char == '.':
                    if op == '..':
                        selector = _ParentPathEvaluator()
                    elif not selectors:
                        # An initial "." doesn't hurt and is required if it's the only evaluator.
                        selector = _SelfPathEvaluator()
                    else:
                        # Later "." operators can be discarded as redundant.
                        selector = None
                elif first_char == '/' and op == '//':
                    selector = _prepare_path_descendant(token=_next())
                else:
                    raise SyntaxError("invalid path")

            if selector is not None:
                selectors.append(selector)
        except StopIteration:
            raise SyntaxError("invalid path") from None
        try:
            token = _next()
            if token[0] == "/":
                token = _next()
        except StopIteration:
            break
    _cache[cache_key] = selectors

    return selectors


# --------------------------------------------------------------------

cdef object _evaluate_path  # keep generator function internal

def _evaluate_path(path_selectors: list[_PathEvaluator], start_element: _Element):
    """Generator to evaluate a sequence of path selectors against a start element."""
    cdef xmlNode* c_node
    cdef xmlNode* c_next
    _assertValidNode(start_element)

    doc = start_element._doc
    c_node = start_element._c_node

    # Copy evaluator list to use independent evaluation state and make it thread-local.
    path_selectors = [(<_PathEvaluator?> evaluator).copy() for evaluator in path_selectors]

    # The yielded element is never stored on the stack, thus path length - 1.
    cdef Py_ssize_t end_of_path = len(path_selectors) - 1
    proxy_stack: list = [None] * end_of_path
    cdef xmlNode** c_node_stack = <xmlNode**> python.lxml_malloc(end_of_path, sizeof(xmlNode*))
    if c_node_stack is NULL:
        raise MemoryError

    cdef Py_ssize_t i = 0, next_first = 0
    cdef Py_ssize_t cached_min = -1, cached_max = 0

    doc.lock_read()
    try:
        while i >= 0:
            selector = <_PathEvaluator> path_selectors[i]
            if i >= cached_max:
                selector.prepare_match(doc)
                cached_max = i + 1
                if i == cached_min:
                    cached_min = i - 1
            elif i <= cached_min:
                selector.prepare_match(doc)
                cached_min = i - 1

            if i == next_first:
                c_next = selector.first_node(c_node)
            else:
                c_next = selector.next_node(c_node)

            if c_next is NULL and i < end_of_path:
                # Reset nodeset context when leaving it.
                c_next = (<_PathEvaluator> path_selectors[i+1]).reset_nodeset()
                if c_next is not NULL:
                    # Continue with late nodeset result from negative indexing.
                    c_node_stack[i] = NULL  # exhausted
                    i += 1
                    c_node_stack[i] = NULL  # exhausted after c_next
                    next_first = i + 1

            if c_next is NULL:
                # backtrack
                i -= 1
                while i >= 0 and (c_node := c_node_stack[i]) is NULL:
                    i -= 1
                next_first = i + 1
                continue

            # step to next path level
            if i == end_of_path:
                match_element = _elementFactory(doc, c_next)
                # Guard the C node stack against deallocation during tree modifications by creating proxies at need.
                _guard_path_cnodes(doc, c_node_stack, end_of_path, proxy_stack)
                doc.unlock_read()
                try:
                    yield match_element
                    # Keep 'match_element' (and thus the current 'c_next') alive until we found its successor.
                finally:
                    if doc is not match_element._doc:
                        doc = match_element._doc  # Element was moved by the user.
                    doc.lock_read()
                next_first = i + 1
                # Reset the document dict caches to allow for tree modifications.
                cached_min = cached_max = i
            else:
                c_node_stack[i] = c_next
                i += 1
                next_first = i
            c_node = c_next

    finally:
        python.lxml_free(c_node_stack)
        doc.unlock_read()


@cython.boundscheck(False)
@cython.wraparound(False)
cdef int _guard_path_cnodes(_Document doc, xmlNode **c_node_stack, Py_ssize_t c_node_count, proxy_stack: list):
    """Make sure there is a live proxy for each C node in 'c_node_stack'."""
    cdef Py_ssize_t i

    for i in range(c_node_count):
        if c_node_stack[i] is NULL:
            proxy_stack[i] = None
        else:
            proxy = proxy_stack[i]
            if proxy is None or (<_Element> proxy)._c_node is not c_node_stack[i]:
                # You might think that using the _Document of the newest node
                # could mismatch those of previously found elements after tree modifications,
                # but those will already have their proxy and we won't even get here.
                proxy_stack[i] = _elementFactory(doc, c_node_stack[i])
    return 0


##
# Iterate over the matching nodes

cdef _elementpath_iterfind(elem: _Element, path, namespaces=None, with_prefixes=True):
    selectors = _build_path_iterator(path, namespaces, with_prefixes=with_prefixes)
    return _evaluate_path(selectors, elem) if selectors else iter([elem])


##
# Find first matching object.

cdef _elementpath_find(elem, path, namespaces=None, with_prefixes=True):
    return next(_elementpath_iterfind(elem, path, namespaces, with_prefixes=with_prefixes), None)


##
# Find all matching objects.

cdef _elementpath_findall(elem, path, namespaces=None, with_prefixes=True):
    return list(_elementpath_iterfind(elem, path, namespaces, with_prefixes))


##
# Find text for first matching object.

cdef _elementpath_findtext(elem, path, default=None, namespaces=None, with_prefixes=True):
    el = _elementpath_find(elem, path, namespaces, with_prefixes=with_prefixes)
    if el is None:
        return default
    else:
        return el.text or ''


# --------------------------------------------------------------------
# Add legacy module.

class _ElementPathModule:
    """Legacy module replacement for 'lxml._elementpath'.
    """
    @property
    def xpath_tokenizer_re(self):
        return re.compile(xpath_tokenizer_re)

    @property
    def _cache(self):
        return _cache

    @staticmethod
    def iterfind(elem, path, namespaces=None, with_prefixes=True):
        return _elementpath_iterfind(elem, path, namespaces, with_prefixes)

    @staticmethod
    def find(elem, path, namespaces=None, with_prefixes=True):
        return _elementpath_find(elem, path, namespaces, with_prefixes)

    @staticmethod
    def findall(elem, path, namespaces=None, with_prefixes=True):
        return _elementpath_findall(elem, path, namespaces, with_prefixes)

    @staticmethod
    def findtext(elem, path, default=None, namespaces=None, with_prefixes=True):
        return _elementpath_findtext(elem, path, default, namespaces, with_prefixes)

    @staticmethod
    def xpath_tokenizer(pattern, namespaces=None, with_prefixes=True):
        return _xpath_tokenizer(pattern, namespaces, with_prefixes)

sys.modules.setdefault('lxml._elementpath', _ElementPathModule())
del _ElementPathModule
