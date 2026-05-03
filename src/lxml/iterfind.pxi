# iterfind.pxi - ElementTree-compatible iterfind, search-engine half.
#
# Implements the limited XPath subset from
# https://docs.python.org/3/library/xml.etree.elementtree.html#elementtree-xpath
#
# This file owns the C-level path tokenizer / compiler, the predicate
# evaluator, and a per-step "searcher" class (_IfSearcher). The Python
# entry points that drive the chain live in _elementpath.pxi.
#
# A compiled path becomes a doubly-linked list of _IfSearcher instances,
# one per step. The chain self-drives: ``_first(scope)`` and
# ``_next(cursor)`` walk the chain internally (descending into
# ``self.next._first`` on a match, cascading via ``self.prev._next`` on
# exhaustion) and return the matched leaf ``xmlNode*`` directly, or
# NULL when the chain is exhausted. Searchers hold no _Element refs --
# the caller (iterator field or function-local _Element) anchors the
# xmlDoc lifetime, and the wrapping into _Element happens once per
# yielded match in the caller.

from libc.stdlib cimport realloc, free, strtol
from libc.string cimport memcmp
from cpython.unicode cimport PyUnicode_AsUTF8, PyUnicode_AsUTF8AndSize

# Sentinel for "no namespace" in c_href slots. Encoded as a non-NULL
# pointer with c_href_len == 0; consumers compare against NULL to detect
# the wildcard ("any namespace") case, so a stable non-NULL address is
# enough -- the byte's value is never read.
cdef char _if_ns_none_byte = 0
cdef const char* _IF_NS_NONE = &_if_ns_none_byte

# ---- Step / predicate type enums ----

cdef enum _IfStepType:
    STEP_CHILD          # tag  — select children with tag
    STEP_SELF           # .    — yield the scope itself (single-shot)
    STEP_PARENT         # ..   — parent element
    STEP_DESCENDANTS    # //tag — all descendants with tag

cdef enum _IfPredType:
    PRED_ATTR_EXISTS      # [@attrib]
    PRED_ATTR_EQ          # [@attrib='value']
    PRED_ATTR_NEQ         # [@attrib!='value']
    PRED_CHILD_TAG        # [tag]
    PRED_TEXT_EQ          # [.='text']
    PRED_TEXT_NEQ         # [.!='text']
    PRED_CHILD_TEXT_EQ    # [tag='text']
    PRED_CHILD_TEXT_NEQ   # [tag!='text']
    PRED_POSITION         # [N]
    PRED_POSITION_FROM_END    # [last()] (position == 0) or [last()-N] (position == N)

# ---- Compiled step struct ----

cdef struct _IfAttrPredicate:
    const char* c_attr        # attr name bytes (not NUL-terminated; NULL for [.] text predicate)
    int c_attr_len
    const char* c_href       # namespace constraint -- see _if_tag_matches docs for the
    int c_href_len           # NULL / len==0 / len>0 three-state encoding
    const char* c_value      # comparison value bytes (NULL for [@attr] existence-only)
    int c_value_len

cdef struct _IfNodePredicate:
    const char* c_tag        # child tag local name bytes (NULL for *)
    int c_tag_len
    const char* c_href       # namespace constraint -- same three-state encoding as
    int c_href_len           # _if_tag_matches: NULL=any, len==0=no-ns, len>0=exact
    const char* c_value      # comparison value bytes (NULL for [tag] existence-only)
    int c_value_len

cdef struct _IfPosPredicate:
    int position             # 0-based position index (for PRED_POSITION*)

cdef union _IfPredVariant:
    _IfAttrPredicate attr
    _IfNodePredicate node
    _IfPosPredicate pos

cdef struct _IfPredicate:
    _IfPredType type
    _IfPredVariant data

cdef struct _IfStep:
    _IfStepType type
    const char* c_tag        # tag local name bytes (NULL for *)
    int c_tag_len
    const char* c_href       # namespace URI bytes (NULL for *)
    int c_href_len
    int pred_count
    _IfPredicate* preds      # array of predicates (malloc'd)

# ---- Namespace lookup table (used by the C tokenizer to resolve prefix:tag) ----
#
# This is built once per ``_IfSearcher.compile()`` call from the user-supplied
# Python ``namespaces`` dict and consulted by the inline tokenizer. The
# compiler resolves all ``prefix:name`` -> ``{uri}name`` and applies the
# default namespace directly, so no Python-level (regex-based) preprocessing
# is needed.

cdef struct _IfNsEntry:
    const char* prefix       # ptr into a bytes object held by the head's ns_keepalive
    int prefix_len           # 0 marks the default namespace (no prefix)
    const char* uri
    int uri_len

cdef struct _IfNsTable:
    int count
    _IfNsEntry* entries
    const char* default_uri  # ptr into ns_keepalive bytes; NULL if no default ns set
    int default_uri_len

# ---- Namespace table helpers ----

cdef inline void _if_ns_table_init(_IfNsTable* nst) noexcept nogil:
    nst.count = 0
    nst.entries = NULL
    nst.default_uri = NULL
    nst.default_uri_len = 0

cdef void _if_ns_table_free(_IfNsTable* nst) noexcept nogil:
    """Release the entries array. The prefix/uri pointers themselves are
    borrowed (they point into bytes held alive by the head's
    ns_keepalive list), so we don't free them here."""
    if nst.entries is not NULL:
        free(nst.entries)
    nst.entries = NULL
    nst.count = 0
    nst.default_uri = NULL
    nst.default_uri_len = 0

cdef inline int _if_ns_value_ptr(object val,
                                  const char** out_ptr, int* out_len) except -1:
    """Borrow a (ptr, len) pair from a str (via the cached UTF-8 buffer)
    or a bytes object (direct buffer). Caller must keep ``val`` alive --
    the pointer is invalid the moment the underlying object is freed.
    Raises TypeError on any other type.
    """
    cdef Py_ssize_t size
    if isinstance(val, str):
        out_ptr[0] = PyUnicode_AsUTF8AndSize(val, &size)
        out_len[0] = <int>size
        return 0
    if isinstance(val, bytes):
        out_ptr[0] = <const char*><bytes>val
        out_len[0] = <int>len(<bytes>val)
        return 0
    raise TypeError("namespace prefix/URI must be str or bytes, not %s"
                    % type(val).__name__)

cdef int _if_ns_table_add(_IfNsTable* nst, const char* prefix, int prefix_len,
                          const char* uri, int uri_len) noexcept nogil:
    """Append a (prefix, uri) entry. ``prefix`` may be NULL to mark the
    default namespace. The prefix/uri pointers are stored as-is; the
    caller (compile()) owns the underlying bytes via ns_keepalive.
    Returns 0 on success, -1 on OOM.
    """
    cdef _IfNsEntry* new_entries
    cdef int new_count = nst.count + 1
    new_entries = <_IfNsEntry*>realloc(nst.entries, new_count * sizeof(_IfNsEntry))
    if new_entries is NULL:
        return -1
    nst.entries = new_entries
    nst.entries[nst.count].prefix = prefix
    nst.entries[nst.count].prefix_len = prefix_len if prefix is not NULL else 0
    nst.entries[nst.count].uri = uri
    nst.entries[nst.count].uri_len = uri_len
    if prefix is NULL:
        nst.default_uri = uri
        nst.default_uri_len = uri_len
    nst.count = new_count
    return 0

cdef inline bint _slice_eq(const char* a, int a_len,
                           const char* b, int b_len) noexcept nogil:
    """Equality of two non-NUL-terminated byte slices."""
    if a_len != b_len:
        return 0
    if a_len == 0:
        return 1
    return memcmp(a, b, a_len) == 0

cdef int _if_ns_lookup(_IfNsTable* nst, const char* prefix, int prefix_len,
                       const char** out_uri, int* out_uri_len) noexcept nogil:
    """Resolve ``prefix`` to its URI. Sets out_uri / out_uri_len on
    success and returns 0; returns -1 if not bound.
    """
    cdef int i
    cdef _IfNsEntry* e
    if nst is NULL or nst.entries is NULL:
        return -1
    for i in range(nst.count):
        e = &nst.entries[i]
        if e.prefix is NULL:
            continue
        if _slice_eq(e.prefix, e.prefix_len, prefix, prefix_len):
            out_uri[0] = e.uri
            out_uri_len[0] = e.uri_len
            return 0
    return -1


# ---- Tag matching helpers (pure libxml2) ----

cdef inline bint _eq_zterm_slice(const xmlChar* zterm,
                                  const char* slice, int slice_len) noexcept nogil:
    """Length-aware compare: True if the NUL-terminated ``zterm`` equals
    the [slice, slice+slice_len) slice exactly. Safe -- never reads past
    zterm's NUL even if slice_len overshoots zterm's length.
    """
    cdef int i
    if zterm is NULL:
        return slice_len == 0
    for i in range(slice_len):
        if zterm[i] == 0 or zterm[i] != slice[i]:
            return 0
    return zterm[slice_len] == 0

cdef inline bint _if_tag_matches(xmlNode* c_node,
                                  const char* c_tag, int c_tag_len,
                                  const char* c_href, int c_href_len) noexcept nogil:
    """Check if c_node matches the given tag/namespace constraints.

    c_tag NULL means wildcard local name.
    c_href encoding:
        NULL                       -- wildcard ({*} or bare *): match any URI.
        non-NULL, c_href_len == 0  -- {} sentinel: require no namespace.
        non-NULL, c_href_len  > 0  -- exact URI match.
    """
    cdef const xmlChar* node_href
    if c_node is NULL:
        return 0
    if c_node.type != tree.XML_ELEMENT_NODE:
        return 0

    if c_tag is not NULL:
        if not _eq_zterm_slice(c_node.name, c_tag, c_tag_len):
            return 0

    if c_href is NULL:
        return 1  # any namespace
    node_href = _getNs(c_node)
    if c_href_len == 0:
        return node_href is NULL or node_href[0] == 0
    if node_href is NULL:
        return 0
    return _eq_zterm_slice(node_href, c_href, c_href_len)

cdef inline xmlNode* _if_first_child_element(xmlNode* c_node) noexcept nogil:
    """Return the first child element, or NULL."""
    cdef xmlNode* c_child
    if c_node is NULL:
        return NULL
    c_child = c_node.children
    while c_child is not NULL:
        if c_child.type == tree.XML_ELEMENT_NODE:
            return c_child
        c_child = c_child.next
    return NULL

# ---- Predicate evaluation (pure libxml2) ----

cdef inline bint _if_ns_equal(const xmlChar* a, const xmlChar* b) noexcept nogil:
    """Compare two namespace URIs (either or both may be NULL)."""
    if a == b:
        return 1
    if a is NULL or b is NULL:
        return 0
    return tree.xmlStrcmp(a, b) == 0

cdef inline xmlChar* _if_get_attr(xmlNode* c_node, _IfAttrPredicate* a) noexcept nogil:
    """Find an attribute on c_node matching ``a.c_attr`` plus the
    namespace constraint encoded in (a.c_href, a.c_href_len), and return
    its value as a malloc'd xmlChar* (caller must xmlFree). Returns NULL
    if not found.

    Namespace encoding (same convention as _if_tag_matches):
        c_href NULL                       -- match any namespace.
        c_href non-NULL, c_href_len == 0  -- require no namespace.
        c_href non-NULL, c_href_len  > 0  -- exact URI match.

    Walks ``c_node.properties`` directly because libxml2's xmlGetNsProp /
    xmlGetNoNsProp require NUL-terminated key/href, and our slices come
    straight from the path bytes.
    """
    cdef tree.xmlAttr* attr = c_node.properties
    while attr is not NULL:
        if _eq_zterm_slice(attr.name, a.c_attr, a.c_attr_len):
            if a.c_href is NULL:
                # any namespace
                return tree.xmlNodeGetContent(<xmlNode*>attr)
            if a.c_href_len == 0:
                # require no namespace
                if attr.ns is NULL:
                    return tree.xmlNodeGetContent(<xmlNode*>attr)
            else:
                if attr.ns is not NULL and _eq_zterm_slice(
                        attr.ns.href, a.c_href, a.c_href_len):
                    return tree.xmlNodeGetContent(<xmlNode*>attr)
        attr = attr.next
    return NULL

cdef inline bint _if_strcmp_match(const xmlChar* c_val,
                                   const char* c_target, int c_target_len,
                                   bint want_eq) noexcept nogil:
    """Compare NUL-terminated c_val to the [c_target, c_target+c_target_len)
    slice. NULL c_val is treated as 'not equal' (so True for NEQ, False
    for EQ)."""
    if c_val is NULL:
        return not want_eq
    return _eq_zterm_slice(c_val, c_target, c_target_len) == want_eq

cdef inline bint _if_same_tag(xmlNode* a, xmlNode* b) noexcept nogil:
    """True if a and b share both local name and namespace URI."""
    return (tree.xmlStrcmp(a.name, b.name) == 0
            and _if_ns_equal(_getNs(a), _getNs(b)))

cdef bint _if_eval_predicate(xmlNode* c_node, _IfPredicate* pred) noexcept nogil:
    """Evaluate a single predicate against c_node. Returns True if it passes."""
    cdef xmlChar* c_val
    cdef xmlNode* c_child
    cdef xmlNode* c_sib
    cdef bint matched
    cdef bint want_eq
    cdef int count

    if pred.type == PRED_ATTR_EXISTS:
        c_val = _if_get_attr(c_node, &pred.data.attr)
        if c_val is NULL:
            return 0
        tree.xmlFree(c_val)
        return 1

    if pred.type == PRED_ATTR_EQ or pred.type == PRED_ATTR_NEQ:
        c_val = _if_get_attr(c_node, &pred.data.attr)
        matched = _if_strcmp_match(c_val,
                                    pred.data.attr.c_value, pred.data.attr.c_value_len,
                                    pred.type == PRED_ATTR_EQ)
        if c_val is not NULL:
            tree.xmlFree(c_val)
        return matched

    if pred.type == PRED_TEXT_EQ or pred.type == PRED_TEXT_NEQ:
        # Text predicates reuse the attr variant for c_value (c_attr unused).
        c_val = tree.xmlNodeGetContent(c_node)
        matched = _if_strcmp_match(c_val,
                                    pred.data.attr.c_value, pred.data.attr.c_value_len,
                                    pred.type == PRED_TEXT_EQ)
        if c_val is not NULL:
            tree.xmlFree(c_val)
        return matched

    if pred.type == PRED_CHILD_TAG:
        c_child = c_node.children
        while c_child is not NULL:
            if c_child.type == tree.XML_ELEMENT_NODE \
                    and _if_tag_matches(c_child,
                                         pred.data.node.c_tag, pred.data.node.c_tag_len,
                                         pred.data.node.c_href, pred.data.node.c_href_len):
                return 1
            c_child = c_child.next
        return 0

    if pred.type == PRED_CHILD_TEXT_EQ or pred.type == PRED_CHILD_TEXT_NEQ:
        # Need at least one tag-matching child whose text [==/!=] value.
        # Children with NULL content contribute nothing either way.
        want_eq = pred.type == PRED_CHILD_TEXT_EQ
        c_child = c_node.children
        while c_child is not NULL:
            if c_child.type == tree.XML_ELEMENT_NODE \
                    and _if_tag_matches(c_child,
                                         pred.data.node.c_tag, pred.data.node.c_tag_len,
                                         pred.data.node.c_href, pred.data.node.c_href_len):
                c_val = tree.xmlNodeGetContent(c_child)
                if c_val is not NULL:
                    matched = _eq_zterm_slice(c_val,
                                               pred.data.node.c_value,
                                               pred.data.node.c_value_len) == want_eq
                    tree.xmlFree(c_val)
                    if matched:
                        return 1
            c_child = c_child.next
        return 0

    if pred.type == PRED_POSITION:
        # Count same-tag siblings up to and including c_node (1-based)
        if c_node.parent is NULL:
            return 0
        count = 0
        c_sib = c_node.parent.children
        while c_sib is not NULL:
            if c_sib.type == tree.XML_ELEMENT_NODE and _if_same_tag(c_sib, c_node):
                count += 1
                if c_sib == c_node:
                    return count == pred.data.pos.position
            c_sib = c_sib.next
        return 0

    if pred.type == PRED_POSITION_FROM_END:
        # Node must have exactly pred.data.pos.position later same-tag siblings.
        # position == 0 means [last()]; N means [last()-N].
        if c_node.parent is NULL:
            return 0
        count = 0
        c_sib = c_node.next
        while c_sib is not NULL:
            if c_sib.type == tree.XML_ELEMENT_NODE and _if_same_tag(c_sib, c_node):
                count += 1
                if count > pred.data.pos.position:
                    return 0
            c_sib = c_sib.next
        return count == pred.data.pos.position

    return 0

cdef bint _if_check_all_preds(xmlNode* c_node, _IfStep* step) noexcept nogil:
    """Return True if c_node passes all predicates on the step."""
    cdef int i
    for i in range(step.pred_count):
        if not _if_eval_predicate(c_node, &step.preds[i]):
            return 0
    return 1

# ---- Descendant traversal helpers ----

cdef xmlNode* _if_next_descendant_element(xmlNode* c_node,
                                            int* depth) noexcept nogil:
    """Depth-first pre-order traversal driven by a depth counter.

    ``depth`` tracks how far below the original scope ``c_node`` lives
    (1 = direct child of scope, etc.). The walker increments on
    descend and decrements on backtrack; when a backtrack would take
    the depth to 0 the search has escaped the scope and we return
    NULL.

    The caller seeds depth=1 when entering with a first child, and
    threads the same int slot across resume calls.
    """
    cdef xmlNode* c_next

    # Try to descend into children first
    c_next = c_node.children
    while c_next is not NULL:
        if c_next.type == tree.XML_ELEMENT_NODE:
            depth[0] += 1
            return c_next
        c_next = c_next.next

    # No children -- try siblings, backtracking through parents.
    # depth[0] tells us how many parent-hops remain before we'd escape
    # the scope; stop when it would reach 0.
    while depth[0] > 0:
        c_next = c_node.next
        while c_next is not NULL:
            if c_next.type == tree.XML_ELEMENT_NODE:
                return c_next
            c_next = c_next.next
        c_node = c_node.parent
        depth[0] -= 1
        if c_node is NULL:
            break

    return NULL

# ---- C-level path tokenizer / compiler ----


cdef void _if_free_step(_IfStep* step) noexcept nogil:
    """Free the predicates array on a step. The byte pointers (step.c_tag,
    step.c_href, and the c_attr / c_tag / c_href / c_value slots inside
    each variant predicate) are borrowed: they point into the path's
    UTF-8 cache or into namespace str caches held alive by the caller
    (the iterator's ``_namespaces`` dict, or the find/findall function-
    local parameter). We never free them here."""
    if step.preds is not NULL:
        free(step.preds)

cdef inline void _if_skip_whitespace(const char** pp) noexcept nogil:
    while pp[0][0] == c' ' or pp[0][0] == c'\t' or pp[0][0] == c'\n' or pp[0][0] == c'\r':
        pp[0] += 1

cdef inline bint _if_is_step_terminator(char ch) noexcept nogil:
    return ch == 0 or ch == c'/' or ch == c'['

cdef inline bint _if_is_predicate_terminator(char ch) noexcept nogil:
    return (ch == 0 or ch == c']' or ch == c'=' or ch == c'!'
            or ch == c' ' or ch == c'\t')

cdef int _if_scan_ns_tag(const char** pp, bint in_predicate,
                          const char** out_href, int* out_href_len,
                          const char** out_tag, int* out_tag_len,
                          _IfNsTable* nst, bint apply_default_ns) except -1:
    """Scan a namespaced tag at ``*pp`` and split it into namespace URI +
    local name as ptr+len pairs (zero-copy: pointers point into either
    the path bytes or nst URI bytes -- the caller keeps both alive).

    Accepted forms (Clark notation + ElementTree prefix:name):
        {uri}name, {uri}*, {*}name, {*}*, {}name
        prefix:name, prefix:*
        name, *

    Sets:
        out_href / out_href_len   namespace constraint, encoded as:
            NULL                  -- match any namespace ({*}, bare *)
            _IF_NS_NONE / 0       -- require no namespace ({}, bare name
                                     when no default ns applies)
            uri ptr / len         -- exact URI match
        out_tag  / out_tag_len    local name slice (NULL/0 for wildcard)

    ``apply_default_ns`` decides whether bare element names inherit the
    default namespace registered in ``nst``; attributes never do.

    Raises SyntaxError on unterminated ``{``, an empty tag, or an
    unknown prefix.
    """
    cdef const char* p = pp[0]
    cdef const char* href_start
    cdef int href_len
    cdef bint have_brace = False
    cdef const char* tag_start
    cdef const char* colon = NULL
    cdef const char* local_start
    cdef int prefix_len
    cdef int local_len
    cdef int tag_len
    cdef const char* uri
    cdef int uri_len

    out_href[0] = NULL  # default: any namespace (overridden below)
    out_href_len[0] = 0
    out_tag[0] = NULL
    out_tag_len[0] = 0

    # 1. Optional {uri} / {*} / {} prefix.
    if p[0] == c'{':
        p += 1
        href_start = p
        while p[0] != c'}':
            if p[0] == 0:
                raise SyntaxError("unterminated '{' in path expression")
            p += 1
        href_len = <int>(p - href_start)
        p += 1  # past '}'
        have_brace = True

        if href_len == 1 and href_start[0] == c'*':
            # {*} -- match any namespace; out_href stays NULL.
            pass
        elif href_len > 0:
            out_href[0] = href_start
            out_href_len[0] = href_len
        else:
            # {} -- require no namespace (regardless of any default).
            out_href[0] = _IF_NS_NONE

    # 2. Scan the tag part. If we did NOT see a '{', a single ':' may
    #    appear and split the token into prefix + local name.
    tag_start = p
    while p[0] != 0:
        if in_predicate:
            if _if_is_predicate_terminator(p[0]):
                break
        else:
            if _if_is_step_terminator(p[0]):
                break
        if p[0] == c':' and colon is NULL and not have_brace:
            colon = p
        p += 1
    pp[0] = p

    # 3. Resolve.
    if colon is not NULL:
        # prefix:name (no '{' was seen).
        prefix_len = <int>(colon - tag_start)
        local_start = colon + 1
        local_len = <int>(p - local_start)
        if prefix_len == 0 or local_len == 0:
            raise SyntaxError("invalid prefix:name in path expression")
        if _if_ns_lookup(nst, tag_start, prefix_len, &uri, &uri_len) < 0:
            raise SyntaxError("unknown namespace prefix in path expression")
        out_href[0] = uri
        out_href_len[0] = uri_len
        if local_len == 1 and local_start[0] == c'*':
            out_tag[0] = NULL
            out_tag_len[0] = 0
        else:
            out_tag[0] = local_start
            out_tag_len[0] = local_len
        return 0

    # Bare name or brace-prefixed name.
    tag_len = <int>(p - tag_start)
    if tag_len == 0:
        raise SyntaxError("empty tag in path expression")
    if tag_len == 1 and tag_start[0] == c'*':
        # Wildcard local name. With no brace, this is bare ``*``: match
        # anything in any namespace -- out_href stays NULL.
        out_tag[0] = NULL
        out_tag_len[0] = 0
    else:
        out_tag[0] = tag_start
        out_tag_len[0] = tag_len
        if not have_brace:
            # Bare name: inherit default ns if one is registered, else
            # require no namespace.
            if (apply_default_ns
                    and nst is not NULL and nst.default_uri is not NULL):
                out_href[0] = nst.default_uri
                out_href_len[0] = nst.default_uri_len
            else:
                out_href[0] = _IF_NS_NONE
    return 0

cdef int _if_parse_quoted_value(const char** pp,
                                  const char** out_value, int* out_value_len) noexcept nogil:
    """Parse `'value'` or `"value"` followed by a closing `]`. Stores a
    ptr+len slice into the path bytes (zero-copy) in *out_value /
    *out_value_len, advances *pp past the `]`.
    Returns 0 on success, -1 on syntax error.
    """
    cdef const char* p = pp[0]
    cdef const char* start
    cdef char quote

    if p[0] != c'\'' and p[0] != c'"':
        return -1
    quote = p[0]
    p += 1
    start = p
    while p[0] != 0 and p[0] != quote:
        p += 1
    if p[0] != quote:
        return -1
    out_value[0] = start
    out_value_len[0] = <int>(p - start)
    p += 1
    _if_skip_whitespace(&p)
    if p[0] != c']':
        return -1
    p += 1
    pp[0] = p
    return 0


cdef int _if_parse_predicate(const char** pp, _IfPredicate* pred,
                              _IfNsTable* nst) except *:
    """Parse a predicate: the char after '['. Advances pp past ']'.
    Returns 0 on success, -1 on a non-fatal parse mismatch (caller turns
    that into a SyntaxError); may also raise SyntaxError directly via
    the inner _if_scan_ns_tag."""
    cdef const char* p = pp[0]
    cdef const char* start
    cdef char* endptr
    cdef long val

    _if_skip_whitespace(&p)

    if p[0] == c'@':
        # Attribute predicate: [@attr] or [@attr='val'] or [@attr!='val'].
        # Attributes never receive the default namespace.
        p += 1
        _if_skip_whitespace(&p)
        pred.data.attr.c_value = NULL
        pred.data.attr.c_value_len = 0
        _if_scan_ns_tag(&p, 1,
                         &pred.data.attr.c_href, &pred.data.attr.c_href_len,
                         &pred.data.attr.c_attr, &pred.data.attr.c_attr_len,
                         nst, 0)

        _if_skip_whitespace(&p)

        if p[0] == c']':
            pred.type = PRED_ATTR_EXISTS
            p += 1
            pp[0] = p
            return 0

        if p[0] == c'!' and p[1] == c'=':
            pred.type = PRED_ATTR_NEQ
            p += 2
        elif p[0] == c'=':
            pred.type = PRED_ATTR_EQ
            p += 1
        else:
            return -1

        _if_skip_whitespace(&p)
        if _if_parse_quoted_value(&p,
                                   &pred.data.attr.c_value,
                                   &pred.data.attr.c_value_len) < 0:
            return -1
        pp[0] = p
        return 0

    elif p[0] == c'.':
        # Text predicate: [.='text'] or [.!='text']. Reuses the attr
        # variant for c_value (c_attr stays NULL).
        p += 1
        _if_skip_whitespace(&p)
        pred.data.attr.c_attr = NULL
        pred.data.attr.c_attr_len = 0
        if p[0] == c'=':
            pred.type = PRED_TEXT_EQ
            p += 1
        elif p[0] == c'!' and p[1] == c'=':
            pred.type = PRED_TEXT_NEQ
            p += 2
        else:
            return -1

        _if_skip_whitespace(&p)
        if _if_parse_quoted_value(&p,
                                   &pred.data.attr.c_value,
                                   &pred.data.attr.c_value_len) < 0:
            return -1
        pp[0] = p
        return 0

    else:
        # Could be: [N], [last()], [last()-N], or [tag], [tag='text'], [tag!='text']
        start = p

        # Check for "last()" -> position 0 from end, or "last()-N" -> N from end
        if p[0] == c'l' and p[1] == c'a' and p[2] == c's' and p[3] == c't' \
           and p[4] == c'(' and p[5] == c')':
            p += 6
            _if_skip_whitespace(&p)
            pred.type = PRED_POSITION_FROM_END
            if p[0] == c']':
                pred.data.pos.position = 0
                p += 1
                pp[0] = p
                return 0
            elif p[0] == c'-':
                p += 1
                _if_skip_whitespace(&p)
                val = strtol(p, &endptr, 10)
                if endptr == p:
                    return -1
                p = endptr
                _if_skip_whitespace(&p)
                if p[0] != c']':
                    return -1
                pred.data.pos.position = <int>val
                p += 1
                pp[0] = p
                return 0
            else:
                return -1

        # Try numeric index
        if (p[0] >= c'0' and p[0] <= c'9') or p[0] == c'-':
            val = strtol(p, &endptr, 10)
            if endptr != p:
                p = endptr
                _if_skip_whitespace(&p)
                if p[0] == c']':
                    pred.type = PRED_POSITION
                    pred.data.pos.position = <int>val
                    p += 1
                    pp[0] = p
                    return 0

        # Tag predicate: [tag] or [tag='text'] or [tag!='text'].
        # Element-name predicates inherit the default namespace.
        p = start
        pred.data.node.c_value = NULL
        pred.data.node.c_value_len = 0
        _if_scan_ns_tag(&p, 1,
                         &pred.data.node.c_href, &pred.data.node.c_href_len,
                         &pred.data.node.c_tag, &pred.data.node.c_tag_len,
                         nst, 1)

        _if_skip_whitespace(&p)

        if p[0] == c']':
            pred.type = PRED_CHILD_TAG
            p += 1
            pp[0] = p
            return 0

        if p[0] == c'=':
            pred.type = PRED_CHILD_TEXT_EQ
            p += 1
        elif p[0] == c'!' and p[1] == c'=':
            pred.type = PRED_CHILD_TEXT_NEQ
            p += 2
        else:
            return -1

        _if_skip_whitespace(&p)
        if _if_parse_quoted_value(&p,
                                   &pred.data.node.c_value,
                                   &pred.data.node.c_value_len) < 0:
            return -1
        pp[0] = p
        return 0

cdef int _if_add_pred_to_step(_IfStep* step, _IfPredicate* pred) noexcept nogil:
    """Append a predicate to a step. Returns 0 on success, -1 on error."""
    cdef _IfPredicate* new_preds
    cdef int new_count = step.pred_count + 1
    new_preds = <_IfPredicate*>realloc(step.preds, new_count * sizeof(_IfPredicate))
    if new_preds is NULL:
        return -1
    new_preds[step.pred_count] = pred[0]
    step.preds = new_preds
    step.pred_count = new_count
    return 0


# ---- Per-step searcher: cdef class, linked list ----
#
# A compiled path becomes a doubly-linked list of _IfSearcher instances,
# one per step. The chain self-drives: each searcher's _first / _next
# walks the chain internally and returns a leaf match (or NULL).
#
#     _first(scope) -> xmlNode*
#         Fresh entry into ``scope``. Captures the scope, runs the
#         type-specific entry, then walks at this level: on each
#         candidate match either returns it (if leaf) or recurses
#         into ``self.next._first(candidate)`` and returns its leaf
#         match. If next exhausts in that scope, advances at this
#         level and retries. Returns NULL when this level's scope
#         is exhausted -- the caller (the prev step's ``_scan`` loop,
#         or the entry point in _elementpath.pxi) decides what to do.
#         Does NOT cascade past prev: it's a one-shot in this scope.
#
#     _next(cursor) -> xmlNode*
#         Resume in the current scope from ``cursor`` (the previous
#         match this searcher returned). Same scan/descend logic as
#         _first, but on exhaustion cascades up via
#         ``self.prev._next(self._scope_c)``. The cascade key
#         invariant: ``self._scope_c`` IS prev's cursor, because
#         prev's last match WAS the scope it handed us. Returns NULL
#         when the head's prev chain runs out -- the chain is done.
#
# State held across calls on a searcher:
#
#     _depth   -- STEP_DESCENDANTS only; counts hops below the scope
#                 so ``_if_next_descendant_element`` stops when a
#                 backtrack would escape the scope boundary.
#     _scope_c -- captured by ``_first`` (overwriting any leftover
#                 from a prior fresh entry) and used by ``_next`` on
#                 exhaustion to feed prev's resume input. Reset to
#                 NULL after that hand-off. (Redundant with
#                 ``cursor.parent`` for STEP_CHILD, but the uniform
#                 capture/return shape avoids per-type recovery.)
#
# All four methods (compile, _first, _next, _scan) are @cython.final
# so the per-yield calls are direct, not vtable-dispatched.

@cython.internal
cdef class _IfSearcher:
    cdef _IfStep step
    cdef _IfSearcher prev
    cdef _IfSearcher next
    cdef int _depth                # STEP_DESCENDANTS hops below scope; 0 means "back at scope"
    cdef xmlNode* _scope_c         # scope captured by _first; returned on exhaust

    def __cinit__(self):
        self.step.c_tag = NULL
        self.step.c_tag_len = 0
        self.step.c_href = NULL
        self.step.c_href_len = 0
        self.step.pred_count = 0
        self.step.preds = NULL
        self._depth = 0
        self._scope_c = NULL

    def __dealloc__(self):
        _if_free_step(&self.step)

    @cython.final
    cdef _IfSearcher compile(self, str path, dict namespaces):
        """Tokenise ``path`` and load it into self + a chain of new
        _IfSearcher instances linked via .next/.prev. ``self`` becomes
        the head; later steps are fresh _IfSearcher() instances linked
        via prev/next. Returns the leaf searcher (the tail of the
        chain), which the caller drives via ``_next`` to resume
        iteration after each yield.

        ``namespaces`` may be None or a dict mapping prefix (str) to URI
        (str). The dict's None or '' key (if any) is treated as the default
        namespace that is applied to bare element names.

        Lifetime: the caller MUST keep ``namespaces`` (and ``path``) alive
        for at least the searcher chain's lifetime. Every ``step.c_href``
        (and any predicate URI/key) borrows into ``path``'s UTF-8 cache
        or into the cache of a str value held by ``namespaces``, both of
        which are obtained via ``PyUnicode_AsUTF8AndSize``. The lookup
        table itself is a stack-local that's freed before this method
        returns.

        Raises SyntaxError on a malformed path.
        """
        cdef const char* c_path = PyUnicode_AsUTF8(path)
        cdef const char* p
        cdef _IfNsTable nst
        cdef _IfPredicate pred
        cdef _IfSearcher s
        cdef _IfSearcher prev_s
        cdef bint have_step
        cdef bint is_first_step
        cdef bint any_step
        cdef const char* prefix_c
        cdef const char* uri_c
        cdef int prefix_len
        cdef int uri_len
        cdef object default_uri

        # An absolute path doesn't make sense when searching from an
        # element context; raise the same specific message the old
        # Python _elementpath module raised so callers depending on
        # that text keep working.
        if c_path[0] == c'/':
            raise SyntaxError("cannot use absolute path on element")

        _if_ns_table_init(&nst)
        try:
            # Populate the table from the user's namespaces dict. The
            # prefix/URI byte pointers point into each str's internal
            # UTF-8 cache (PyUnicode_AsUTF8AndSize), so the str objects
            # -- and therefore the dict that holds them -- must outlive
            # the searcher chain. Iterators keep a copy on themselves;
            # find/findall keep the dict alive via the function-local
            # parameter.
            if namespaces:
                default_uri = namespaces.get(None)
                if default_uri is None:
                    default_uri = namespaces.get('')
                elif '' in namespaces and namespaces[''] != default_uri:
                    raise ValueError(
                        "Ambiguous default namespace: %r vs %r" % (
                            default_uri, namespaces['']))

                if default_uri:
                    _if_ns_value_ptr(default_uri, &uri_c, &uri_len)
                    if _if_ns_table_add(&nst, NULL, 0, uri_c, uri_len) < 0:
                        raise MemoryError()

                for key, val in namespaces.items():
                    if key is None or key == '':
                        continue
                    if val is None:
                        continue
                    _if_ns_value_ptr(key, &prefix_c, &prefix_len)
                    _if_ns_value_ptr(val, &uri_c, &uri_len)
                    if _if_ns_table_add(&nst, prefix_c, prefix_len, uri_c, uri_len) < 0:
                        raise MemoryError()

            # Tokenise and build the chain in one pass.
            #
            # For each iteration we allocate the step's searcher up front
            # (the head reuses self) and parse straight into s.step. If
            # parsing raises, s is GC-reachable as a local and Cython
            # tears its allocations down via __dealloc__ -- no manual
            # cleanup needed.
            #
            # A single '/' separator that precedes a tag (e.g. the second
            # '/' in ``a/b``) sets ``have_step = False`` and ``continue``;
            # the just-allocated s is dropped (one searcher's worth of
            # GC churn per separator, only at compile time).
            self.prev = None
            prev_s = None
            is_first_step = True
            any_step = False
            p = c_path

            while p[0] != 0:
                if is_first_step:
                    s = self
                else:
                    s = _IfSearcher()
                have_step = True

                if p[0] == c'/':
                    if p[1] == c'/':
                        # //... -- a wildcard ('*') leaves c_tag NULL,
                        # which _if_tag_matches treats as "any name".
                        p += 2
                        if p[0] == 0:
                            raise SyntaxError("invalid path expression")
                        s.step.type = STEP_DESCENDANTS
                        if p[0] == c'*':
                            p += 1
                        else:
                            _if_scan_ns_tag(&p, 0,
                                             &s.step.c_href, &s.step.c_href_len,
                                             &s.step.c_tag, &s.step.c_tag_len,
                                             &nst, 1)
                    else:
                        # Single /. Trailing '/' is implicit '*'; otherwise
                        # just a separator -- skip and let the next
                        # iteration parse the tag.
                        p += 1
                        if p[0] == 0:
                            s.step.type = STEP_CHILD  # c_tag NULL == wildcard
                        else:
                            have_step = False
                elif p[0] == c'.':
                    if p[1] == c'.':
                        s.step.type = STEP_PARENT
                        p += 2
                    else:
                        # '.' alone yields the current scope. Standalone
                        # path "." needs this; embedded "./tag" produces
                        # a redundant-but-harmless SELF step before the
                        # next step.
                        s.step.type = STEP_SELF
                        p += 1
                elif p[0] == c'*':
                    s.step.type = STEP_CHILD  # c_tag NULL == wildcard
                    p += 1
                else:
                    # Tag name
                    s.step.type = STEP_CHILD
                    _if_scan_ns_tag(&p, 0,
                                     &s.step.c_href, &s.step.c_href_len,
                                     &s.step.c_tag, &s.step.c_tag_len,
                                     &nst, 1)

                if not have_step:
                    # Drop s; the next iteration allocates a fresh one.
                    continue

                # Parse predicates [...] directly into s.step.preds.
                while p[0] == c'[':
                    p += 1
                    if _if_parse_predicate(&p, &pred, &nst) < 0:
                        raise SyntaxError("invalid path expression")
                    if _if_add_pred_to_step(&s.step, &pred) < 0:
                        raise MemoryError()

                # Link s into the chain.
                if not is_first_step:
                    s.prev = prev_s
                    prev_s.next = s
                prev_s = s
                is_first_step = False
                any_step = True

            if not any_step:
                # Empty path -- no steps produced.
                raise SyntaxError("invalid path expression")
        finally:
            _if_ns_table_free(&nst)

        # Return the tail of the chain (the leaf) so the caller can
        # resume iteration via leaf._next() after each yield.
        return prev_s

    @cython.final
    cdef xmlNode* _first(self, xmlNode* c_scope):
        """Find the first leaf match starting from ``c_scope``.

        Captures the scope, runs the type-specific entry, then walks
        forward until a candidate matches at this level. On match,
        either returns the candidate (if this is the leaf) or descends
        into ``self.next._first(candidate)`` and returns its leaf
        match. If the descended chain has no match, advances at this
        level and tries again. Returns NULL if nothing matches in this
        scope -- the caller (``self.prev``'s _scan loop, or the entry
        point) decides what to do.
        """
        cdef xmlNode* c_node = NULL
        cdef _IfStepType step_type = self.step.type

        self._scope_c = c_scope

        if step_type == STEP_CHILD:
            c_node = c_scope.children
        elif step_type == STEP_DESCENDANTS:
            c_node = _if_first_child_element(c_scope)
            self._depth = 1 if c_node is not NULL else 0
        elif step_type == STEP_SELF:
            # Single-shot: yield the scope itself (predicates apply).
            if _if_check_all_preds(c_scope, &self.step):
                if self.next is None:
                    return c_scope
                return self.next._first(c_scope)
            return NULL
        elif step_type == STEP_PARENT:
            c_node = c_scope.parent
            if c_node is not NULL and c_node.type == tree.XML_ELEMENT_NODE \
                    and _if_check_all_preds(c_node, &self.step):
                if self.next is None:
                    return c_node
                return self.next._first(c_node)
            return NULL

        return self._scan(c_node)

    @cython.final
    cdef xmlNode* _next(self, xmlNode* c_cursor):
        """Resume from ``c_cursor`` (this searcher's previous match).

        Advances at this level; on match, descends into
        ``self.next._first`` and returns its leaf match, advancing
        again if next exhausts in that scope. When this scope is
        exhausted, cascades to ``self.prev._next(self._scope_c)`` --
        ``self._scope_c`` IS prev's cursor (= prev's last match).
        Returns NULL when the chain is fully exhausted (head has no
        more matches).
        """
        cdef xmlNode* c_node = NULL
        cdef xmlNode* match
        cdef xmlNode* c_prev_cursor
        cdef _IfStepType step_type = self.step.type

        if step_type == STEP_CHILD:
            c_node = c_cursor.next
        elif step_type == STEP_DESCENDANTS:
            c_node = _if_next_descendant_element(c_cursor, &self._depth)
        # STEP_SELF / STEP_PARENT: single-shot -- c_node stays NULL.

        match = self._scan(c_node)
        if match is not NULL:
            return match

        # Exhausted at this level. Reset our state for any future fresh
        # entry, then cascade up via prev._next(prev_cursor).
        c_prev_cursor = self._scope_c
        self._scope_c = NULL
        self._depth = 0
        if self.prev is None:
            return NULL
        return self.prev._next(c_prev_cursor)

    @cython.final
    cdef xmlNode* _scan(self, xmlNode* c_node):
        """Shared scan loop: walk forward from ``c_node`` at this level,
        and on each candidate match either return (if leaf) or descend
        into ``self.next._first``, retrying at this level if next
        exhausts in the descended scope.

        Returns the leaf-matched xmlNode on success, NULL when this
        level's scope is exhausted. Caller (``_first`` returning to
        its caller, or ``_next`` cascading via prev) handles "nothing
        in this scope".
        """
        cdef _IfStepType step_type = self.step.type
        cdef xmlNode* leaf_match

        if step_type == STEP_CHILD:
            while c_node is not NULL:
                if c_node.type == tree.XML_ELEMENT_NODE \
                        and _if_tag_matches(c_node,
                                            self.step.c_tag, self.step.c_tag_len,
                                            self.step.c_href, self.step.c_href_len) \
                        and _if_check_all_preds(c_node, &self.step):
                    if self.next is None:
                        return c_node
                    leaf_match = self.next._first(c_node)
                    if leaf_match is not NULL:
                        return leaf_match
                    # next exhausted in this scope; advance and retry
                c_node = c_node.next
        elif step_type == STEP_DESCENDANTS:
            while c_node is not NULL:
                if _if_tag_matches(c_node,
                                   self.step.c_tag, self.step.c_tag_len,
                                   self.step.c_href, self.step.c_href_len) \
                        and _if_check_all_preds(c_node, &self.step):
                    if self.next is None:
                        return c_node
                    leaf_match = self.next._first(c_node)
                    if leaf_match is not NULL:
                        return leaf_match
                    # next exhausted in this scope; advance and retry
                c_node = _if_next_descendant_element(c_node, &self._depth)

        return NULL
