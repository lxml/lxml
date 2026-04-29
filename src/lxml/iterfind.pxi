# iterfind.pxi - ElementTree-compatible iterfind using only libxml2 types
#
# Implements the limited XPath subset from
# https://docs.python.org/3/library/xml.etree.elementtree.html#elementtree-xpath
#
# Input/output: xmlNode*. No Python element wrappers are created here;
# callers in _elementpath.pxi wrap results with _elementFactory().
# All tokenization and iteration use only libxml2 objects and C stdlib.

from libc.stdlib cimport malloc, realloc, free, strtol
from libc.string cimport memcpy, memcmp, strlen, strchr

# ---- Step / predicate type enums ----

cdef enum _IfStepType:
    STEP_CHILD          # tag  — select children with tag
    STEP_CHILD_STAR     # *    — select all children
    STEP_SELF           # .    — current node
    STEP_PARENT         # ..   — parent element
    STEP_DESCENDANTS    # //tag — all descendants with tag
    STEP_DESCENDANTS_STAR  # //*  — all descendants

cdef enum _IfPredType:
    PRED_NONE
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

cdef struct _IfPredicate:
    _IfPredType type
    xmlChar* c_key       # attr name, child tag, or NULL
    xmlChar* c_key_href  # namespace URI for key, or NULL
    xmlChar* c_value     # attr/text comparison value, or NULL
    int position         # 1-based position index (for PRED_POSITION*)

cdef struct _IfStep:
    _IfStepType type
    xmlChar* c_tag       # tag local name, or NULL for * / self / parent
    xmlChar* c_href      # namespace URI, or NULL
    bint match_any_ns    # True if {*}tag was specified
    int pred_count
    _IfPredicate* preds  # array of predicates (malloc'd)

# ---- Namespace lookup table (used by the C tokenizer to resolve prefix:tag) ----
#
# This is built once per call from the user-supplied Python ``namespaces`` dict
# in _elementpath.pxi and passed to _if_compile_path(). The compiler resolves
# all ``prefix:name`` -> ``{uri}name`` and applies the default namespace
# directly, so no Python-level (regex-based) preprocessing is needed.

cdef struct _IfNsEntry:
    xmlChar* prefix      # malloc'd prefix bytes; NULL for the default namespace
    xmlChar* uri         # malloc'd uri bytes

cdef struct _IfNsTable:
    int count
    _IfNsEntry* entries
    xmlChar* default_uri   # convenience pointer; NULL if no default ns set

# ---- Namespace table helpers ----

cdef inline void _if_ns_table_init(_IfNsTable* nst) noexcept nogil:
    nst.count = 0
    nst.entries = NULL
    nst.default_uri = NULL

cdef void _if_ns_table_free(_IfNsTable* nst) noexcept nogil:
    cdef int i
    if nst.entries is not NULL:
        for i in range(nst.count):
            if nst.entries[i].prefix is not NULL:
                free(nst.entries[i].prefix)
            if nst.entries[i].uri is not NULL:
                free(nst.entries[i].uri)
        free(nst.entries)
    nst.entries = NULL
    nst.count = 0
    nst.default_uri = NULL

cdef int _if_ns_table_add(_IfNsTable* nst, const char* prefix, int prefix_len,
                          const char* uri, int uri_len) noexcept nogil:
    """Append a (prefix, uri) entry. prefix==NULL marks the default namespace.
    Returns 0 on success, -1 on OOM.
    """
    cdef _IfNsEntry* new_entries
    cdef int new_count = nst.count + 1
    new_entries = <_IfNsEntry*>realloc(nst.entries, new_count * sizeof(_IfNsEntry))
    if new_entries is NULL:
        return -1
    nst.entries = new_entries
    nst.entries[nst.count].prefix = NULL
    nst.entries[nst.count].uri = NULL
    if prefix is not NULL:
        nst.entries[nst.count].prefix = _if_strdup(prefix, prefix_len)
        if nst.entries[nst.count].prefix is NULL:
            return -1
    nst.entries[nst.count].uri = _if_strdup(uri, uri_len)
    if nst.entries[nst.count].uri is NULL:
        return -1
    if prefix is NULL:
        nst.default_uri = nst.entries[nst.count].uri
    nst.count = new_count
    return 0

cdef const xmlChar* _if_ns_lookup(_IfNsTable* nst,
                                  const char* prefix, int prefix_len) noexcept nogil:
    """Find the URI bound to ``prefix`` (NULL terminated up to prefix_len).
    Returns NULL if not bound.
    """
    cdef int i
    cdef _IfNsEntry* e
    if nst is NULL or nst.entries is NULL:
        return NULL
    for i in range(nst.count):
        e = &nst.entries[i]
        if e.prefix is NULL:
            continue
        if <int>strlen(<const char*>e.prefix) != prefix_len:
            continue
        if memcmp(e.prefix, prefix, prefix_len) == 0:
            return e.uri
    return NULL


# ---- Tag matching helpers (pure libxml2) ----

cdef inline bint _if_tag_matches(xmlNode* c_node,
                                  const xmlChar* c_href,
                                  const xmlChar* c_tag,
                                  bint match_any_ns) noexcept nogil:
    """Check if c_node matches the given namespace URI and local tag name.

    c_tag is NULL means wildcard (match any name).
    c_href is NULL and not match_any_ns means no namespace (or wildcard if c_tag is also NULL).
    match_any_ns means match any namespace.
    """
    cdef const xmlChar* node_href
    if c_node is NULL:
        return 0
    if c_node.type != tree.XML_ELEMENT_NODE:
        return 0

    # Check local name
    if c_tag is not NULL:
        if tree.xmlStrcmp(c_node.name, c_tag) != 0:
            return 0

    # Check namespace
    if match_any_ns:
        return 1
    node_href = _getNs(c_node)
    if c_href is NULL:
        # No namespace specified and c_tag is non-NULL: match only no-namespace nodes.
        # If c_tag is also NULL (bare *), match everything regardless of ns.
        if c_tag is not NULL:
            return node_href is NULL or node_href[0] == 0
        return 1  # bare * matches everything
    else:
        if c_href[0] == 0:
            return node_href is NULL or node_href[0] == 0
        if node_href is NULL:
            return 0
        return tree.xmlStrcmp(node_href, c_href) == 0

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

cdef inline xmlChar* _if_get_attr(xmlNode* c_node, _IfPredicate* pred) noexcept nogil:
    """Fetch the predicate's attribute, namespaced or not."""
    if pred.c_key_href is not NULL and pred.c_key_href[0] != 0:
        return tree.xmlGetNsProp(c_node, pred.c_key, pred.c_key_href)
    return tree.xmlGetNoNsProp(c_node, pred.c_key)

cdef inline bint _if_strcmp_match(const xmlChar* c_val, const xmlChar* c_target,
                                   bint want_eq) noexcept nogil:
    """Compare c_val to c_target. NULL c_val is treated as 'not equal'
    (so True for NEQ, False for EQ)."""
    if c_val is NULL:
        return not want_eq
    return (tree.xmlStrcmp(c_val, c_target) == 0) == want_eq

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

    if pred.type == PRED_NONE:
        return 1

    if pred.type == PRED_ATTR_EXISTS:
        c_val = _if_get_attr(c_node, pred)
        if c_val is NULL:
            return 0
        tree.xmlFree(c_val)
        return 1

    if pred.type == PRED_ATTR_EQ or pred.type == PRED_ATTR_NEQ:
        c_val = _if_get_attr(c_node, pred)
        matched = _if_strcmp_match(c_val, pred.c_value, pred.type == PRED_ATTR_EQ)
        if c_val is not NULL:
            tree.xmlFree(c_val)
        return matched

    if pred.type == PRED_TEXT_EQ or pred.type == PRED_TEXT_NEQ:
        c_val = tree.xmlNodeGetContent(c_node)
        matched = _if_strcmp_match(c_val, pred.c_value, pred.type == PRED_TEXT_EQ)
        if c_val is not NULL:
            tree.xmlFree(c_val)
        return matched

    if pred.type == PRED_CHILD_TAG:
        c_child = c_node.children
        while c_child is not NULL:
            if c_child.type == tree.XML_ELEMENT_NODE \
                    and _if_tag_matches(c_child, pred.c_key_href, pred.c_key, 0):
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
                    and _if_tag_matches(c_child, pred.c_key_href, pred.c_key, 0):
                c_val = tree.xmlNodeGetContent(c_child)
                if c_val is not NULL:
                    matched = (tree.xmlStrcmp(c_val, pred.c_value) == 0) == want_eq
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
                    return count == pred.position
            c_sib = c_sib.next
        return 0

    if pred.type == PRED_POSITION_FROM_END:
        # Node must have exactly pred.position later same-tag siblings.
        # pred.position == 0 means [last()]; N means [last()-N].
        if c_node.parent is NULL:
            return 0
        count = 0
        c_sib = c_node.next
        while c_sib is not NULL:
            if c_sib.type == tree.XML_ELEMENT_NODE and _if_same_tag(c_sib, c_node):
                count += 1
                if count > pred.position:
                    return 0
            c_sib = c_sib.next
        return count == pred.position

    return 0

cdef bint _if_check_all_preds(xmlNode* c_node, _IfStep* step) noexcept nogil:
    """Return True if c_node passes all predicates on the step."""
    cdef int i
    for i in range(step.pred_count):
        if not _if_eval_predicate(c_node, &step.preds[i]):
            return 0
    return 1

# ---- Descendant traversal helpers ----

cdef xmlNode* _if_next_descendant_element(xmlNode* c_tree_top,
                                            xmlNode* c_node) noexcept nogil:
    """Depth-first pre-order traversal: return the next element node under
    c_tree_top after c_node. Returns NULL when done."""
    cdef xmlNode* c_next

    # Try to descend into children first
    c_next = c_node.children
    while c_next is not NULL:
        if c_next.type == tree.XML_ELEMENT_NODE:
            return c_next
        c_next = c_next.next

    # No children — try siblings, backtracking through parents
    while c_node != c_tree_top and c_node is not NULL:
        c_next = c_node.next
        while c_next is not NULL:
            if c_next.type == tree.XML_ELEMENT_NODE:
                return c_next
            c_next = c_next.next
        c_node = c_node.parent

    return NULL

# ---- C-level path tokenizer / compiler ----

cdef xmlChar* _if_strdup(const char* src, int length) noexcept nogil:
    """Allocate and copy 'length' bytes from src, null-terminate."""
    cdef xmlChar* dst
    if length < 0:
        length = <int>strlen(src)
    dst = <xmlChar*>malloc(length + 1)
    if dst is NULL:
        return NULL
    memcpy(dst, src, length)
    dst[length] = 0
    return dst

cdef int _if_parse_ns_tag(const char* start, int length,
                           xmlChar** out_href, xmlChar** out_tag,
                           bint* out_any_ns,
                           _IfNsTable* nst, bint apply_default_ns) noexcept nogil:
    """Parse a namespace-qualified tag and resolve any prefix.

    Accepted forms:
      ``{uri}name``      explicit namespace
      ``{*}name``        wildcard namespace
      ``{}name``         empty namespace (== "no namespace")
      ``prefix:name``    resolved against ``nst``
      ``name``           bare local name; if ``apply_default_ns`` and
                         ``nst`` has a default uri, that uri is applied
      ``*``              full wildcard
      ``{ns}*`` / ``prefix:*`` / ``*`` patterns are supported.

    Returns 0 on success, -1 on error.
    Sets out_href, out_tag. out_tag is NULL means name wildcard.
    """
    cdef const char* p = start
    cdef const char* end = start + length
    cdef const char* brace_end
    cdef const char* colon
    cdef int ns_len
    cdef int prefix_len
    cdef int local_len
    cdef const xmlChar* uri
    cdef int i

    out_any_ns[0] = 0
    out_href[0] = NULL
    out_tag[0] = NULL

    if length == 1 and p[0] == c'*':
        # bare * — match everything (no default namespace applied to *)
        return 0

    if p[0] == c'{':
        p += 1
        brace_end = <const char*>strchr(p, c'}')
        if brace_end is NULL or brace_end >= end:
            return -1
        ns_len = <int>(brace_end - p)

        # Check for {*}tag
        if ns_len == 1 and p[0] == c'*':
            out_any_ns[0] = 1
        elif ns_len > 0:
            out_href[0] = _if_strdup(p, ns_len)
            if out_href[0] is NULL:
                return -1
        else:
            # {} — empty namespace (means "no namespace")
            out_href[0] = _if_strdup("", 0)
            if out_href[0] is NULL:
                return -1

        p = brace_end + 1
        if p >= end:
            return -1

        # The tag after the namespace
        if (end - p) == 1 and p[0] == c'*':
            # {ns}* — all tags in given namespace
            out_tag[0] = NULL
        else:
            out_tag[0] = _if_strdup(p, <int>(end - p))
            if out_tag[0] is NULL:
                return -1
        return 0

    # No braces. Check for prefix:local form.
    colon = NULL
    for i in range(length):
        if start[i] == c':':
            colon = start + i
            break

    if colon is not NULL:
        prefix_len = <int>(colon - start)
        local_len = length - prefix_len - 1
        if prefix_len == 0 or local_len == 0:
            return -1
        uri = _if_ns_lookup(nst, start, prefix_len)
        if uri is NULL:
            return -1  # unknown prefix
        out_href[0] = _if_strdup(<const char*>uri, <int>strlen(<const char*>uri))
        if out_href[0] is NULL:
            return -1
        if local_len == 1 and colon[1] == c'*':
            out_tag[0] = NULL
        else:
            out_tag[0] = _if_strdup(colon + 1, local_len)
            if out_tag[0] is NULL:
                return -1
        return 0

    # No namespace — bare tag.
    if length == 0:
        return -1
    out_tag[0] = _if_strdup(start, length)
    if out_tag[0] is NULL:
        return -1
    # Apply default namespace if requested and one is configured.
    if apply_default_ns and nst is not NULL and nst.default_uri is not NULL:
        out_href[0] = _if_strdup(<const char*>nst.default_uri,
                                  <int>strlen(<const char*>nst.default_uri))
        if out_href[0] is NULL:
            return -1
    return 0

cdef void _if_free_step(_IfStep* step) noexcept nogil:
    """Free allocations inside a step (not the step itself)."""
    cdef int i
    if step.c_tag is not NULL:
        free(step.c_tag)
    if step.c_href is not NULL:
        free(step.c_href)
    if step.preds is not NULL:
        for i in range(step.pred_count):
            if step.preds[i].c_key is not NULL:
                free(step.preds[i].c_key)
            if step.preds[i].c_key_href is not NULL:
                free(step.preds[i].c_key_href)
            if step.preds[i].c_value is not NULL:
                free(step.preds[i].c_value)
        free(step.preds)

cdef void _if_free_steps(_IfStep* steps, int count) noexcept nogil:
    """Free an array of steps."""
    cdef int i
    if steps is NULL:
        return
    for i in range(count):
        _if_free_step(&steps[i])
    free(steps)

cdef inline void _if_skip_whitespace(const char** pp) noexcept nogil:
    while pp[0][0] == c' ' or pp[0][0] == c'\t' or pp[0][0] == c'\n' or pp[0][0] == c'\r':
        pp[0] += 1

cdef inline bint _if_is_step_terminator(char ch) noexcept nogil:
    return ch == 0 or ch == c'/' or ch == c'['

cdef inline bint _if_is_predicate_terminator(char ch) noexcept nogil:
    return (ch == 0 or ch == c']' or ch == c'=' or ch == c'!'
            or ch == c' ' or ch == c'\t')

cdef inline void _if_scan_tag(const char** pp, bint in_predicate) noexcept nogil:
    """Advance pp over a tag token, treating ``{...}`` (a Clark-notation
    namespace URI prefix) as opaque so the URI's slashes / brackets are
    not mistaken for path operators or predicate terminators.
    """
    cdef const char* p = pp[0]
    while p[0] != 0:
        if p[0] == c'{':
            # Skip past the matching '}' (URIs may contain '/', ']', '=' etc.)
            p += 1
            while p[0] != 0 and p[0] != c'}':
                p += 1
            if p[0] == c'}':
                p += 1
            continue
        if in_predicate:
            if _if_is_predicate_terminator(p[0]):
                break
        else:
            if _if_is_step_terminator(p[0]):
                break
        p += 1
    pp[0] = p

cdef int _if_parse_quoted_value(const char** pp, xmlChar** out_value) noexcept nogil:
    """Parse `'value'` or `"value"` followed by a closing `]`. Stores a
    malloc'd copy of the value in *out_value, advances *pp past the `]`.
    Returns 0 on success, -1 on syntax / OOM error.
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
    out_value[0] = _if_strdup(start, <int>(p - start))
    if out_value[0] is NULL:
        return -1
    p += 1
    _if_skip_whitespace(&p)
    if p[0] != c']':
        return -1
    p += 1
    pp[0] = p
    return 0


cdef int _if_parse_predicate(const char** pp, _IfPredicate* pred,
                              _IfNsTable* nst) noexcept nogil:
    """Parse a predicate: the char after '['. Advances pp past ']'.
    Returns 0 on success, -1 on error."""
    cdef const char* p = pp[0]
    cdef const char* start
    cdef int tag_len
    cdef char* endptr
    cdef long val
    cdef bint dummy_any_ns

    pred.type = PRED_NONE
    pred.c_key = NULL
    pred.c_key_href = NULL
    pred.c_value = NULL
    pred.position = 0

    _if_skip_whitespace(&p)

    if p[0] == c'@':
        # Attribute predicate: [@attr] or [@attr='val'] or [@attr!='val']
        p += 1
        _if_skip_whitespace(&p)
        start = p
        _if_scan_tag(&p, 1)  # in_predicate=True; handles {uri}name opaquely
        tag_len = <int>(p - start)
        if tag_len == 0:
            return -1

        # Attributes never receive the default namespace.
        if _if_parse_ns_tag(start, tag_len, &pred.c_key_href, &pred.c_key,
                             &dummy_any_ns, nst, 0) < 0:
            return -1

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
        if _if_parse_quoted_value(&p, &pred.c_value) < 0:
            return -1
        pp[0] = p
        return 0

    elif p[0] == c'.':
        # Text predicate: [.='text'] or [.!='text']
        p += 1
        _if_skip_whitespace(&p)
        if p[0] == c'=':
            pred.type = PRED_TEXT_EQ
            p += 1
        elif p[0] == c'!' and p[1] == c'=':
            pred.type = PRED_TEXT_NEQ
            p += 2
        else:
            return -1

        _if_skip_whitespace(&p)
        if _if_parse_quoted_value(&p, &pred.c_value) < 0:
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
                pred.position = 0
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
                pred.position = <int>val
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
                    pred.position = <int>val
                    p += 1
                    pp[0] = p
                    return 0

        # Tag predicate: [tag] or [tag='text'] or [tag!='text']
        p = start
        _if_scan_tag(&p, 1)  # in_predicate=True; handles {uri}name opaquely
        tag_len = <int>(p - start)
        if tag_len == 0:
            return -1

        # Element-name predicates inherit the default namespace.
        if _if_parse_ns_tag(start, tag_len, &pred.c_key_href, &pred.c_key,
                             &dummy_any_ns, nst, 1) < 0:
            return -1

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
        if _if_parse_quoted_value(&p, &pred.c_value) < 0:
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


cdef _IfStep* _if_compile_path(const char* path, int* out_count,
                                _IfNsTable* nst) noexcept nogil:
    """Compile a path string into an array of _IfStep structs.

    All ``prefix:name`` references are resolved against ``nst`` and the
    default namespace (if any) is applied to bare element names. Attribute
    names are never rewritten.

    Returns NULL on error. Sets out_count to the number of steps.
    Caller must free the result with _if_free_steps().
    """
    cdef const char* p = path
    cdef _IfStep* steps = NULL
    cdef int count = 0
    cdef int capacity = 0
    cdef _IfStep step
    cdef _IfPredicate pred
    cdef const char* tag_start
    cdef int tag_len
    cdef _IfStep* new_steps
    cdef bint any_ns
    cdef bint failed = 0

    out_count[0] = 0

    # ElementTree path-syntax rule: a leading '/' (absolute path) is not
    # valid when searching from a context element. Reject up front rather
    # than letting the per-step '/' separator silently swallow it.
    if p[0] == c'/':
        return NULL

    while p[0] != 0:
        # Initialize step
        step.c_tag = NULL
        step.c_href = NULL
        step.match_any_ns = 0
        step.pred_count = 0
        step.preds = NULL

        # Skip leading /
        if p[0] == c'/':
            if p[1] == c'/':
                # //
                p += 2
                if p[0] == 0:
                    failed = 1
                elif p[0] == c'*':
                    step.type = STEP_DESCENDANTS_STAR
                    p += 1
                else:
                    step.type = STEP_DESCENDANTS
                    tag_start = p
                    _if_scan_tag(&p, 0)  # in_predicate=False
                    tag_len = <int>(p - tag_start)
                    if tag_len == 0:
                        failed = 1
                    elif _if_parse_ns_tag(tag_start, tag_len, &step.c_href,
                                          &step.c_tag, &any_ns, nst, 1) < 0:
                        failed = 1
                    else:
                        step.match_any_ns = any_ns
            else:
                # Single /
                p += 1
                if p[0] == 0:
                    # Trailing '/': ElementTree convention is "implicit *",
                    # i.e. select all immediate children of the current
                    # context. Emit a CHILD_STAR step here rather than
                    # rewriting the path string Python-side.
                    step.type = STEP_CHILD_STAR
                else:
                    continue  # next iteration handles the tag after /
        elif p[0] == c'.':
            if p[1] == c'.':
                step.type = STEP_PARENT
                p += 2
            elif p[1] == c'/' or p[1] == 0:
                step.type = STEP_SELF
                p += 1
            else:
                # tag starting with '.' (e.g., .name — treat as tag)
                step.type = STEP_SELF
                p += 1
        elif p[0] == c'*':
            step.type = STEP_CHILD_STAR
            p += 1
        else:
            # Tag name
            step.type = STEP_CHILD
            tag_start = p
            _if_scan_tag(&p, 0)  # in_predicate=False
            tag_len = <int>(p - tag_start)
            if tag_len == 0:
                failed = 1
            elif _if_parse_ns_tag(tag_start, tag_len, &step.c_href,
                                  &step.c_tag, &any_ns, nst, 1) < 0:
                failed = 1
            else:
                step.match_any_ns = any_ns

        if failed:
            _if_free_step(&step)
            break

        # Parse predicates [...]
        while p[0] == c'[':
            p += 1
            if _if_parse_predicate(&p, &pred, nst) < 0:
                failed = 1
                break
            if _if_add_pred_to_step(&step, &pred) < 0:
                failed = 1
                break

        if failed:
            _if_free_step(&step)
            break

        # Add step to array
        if count >= capacity:
            capacity = capacity * 2 if capacity > 0 else 8
            new_steps = <_IfStep*>realloc(steps, capacity * sizeof(_IfStep))
            if new_steps is NULL:
                _if_free_step(&step)
                failed = 1
                break
            steps = new_steps
        steps[count] = step
        count += 1

    if failed:
        _if_free_steps(steps, count)
        return NULL

    out_count[0] = count
    return steps


# ---- Lazy pipeline executor: per-step cursor + depth-first walk ----
#
# Each step in the compiled path is paired with a cursor that yields one
# matching node at a time. A walker state holds N cursors (one per step)
# arranged like nested for-loops with backtracking:
#
#   advance the deepest cursor:
#     if it yielded a node and there are deeper steps, push a fresh cursor
#       rooted at that node and advance it next time;
#     if it yielded a node and we are at the last step, return that node;
#     if it is exhausted, pop and re-advance the cursor above.
#
# This means find('item/name') stops after the first item -> first name
# match (~2 node visits) instead of materialising every item and every
# name first. iterfind() pulls one match per __next__ call from the same
# state machine.

cdef struct _IfCursor:
    xmlNode* scope         # the input node for this step (= previous step's match)
    xmlNode* current       # NULL = exhausted; == scope = fresh; else = last-yielded

cdef xmlNode* _if_cursor_next(_IfStep* step, _IfCursor* cur) noexcept nogil:
    """Return the next xmlNode* this step yields against ``cur.scope``,
    or NULL when the cursor is exhausted. Calling repeatedly walks every
    match in document order, then returns NULL forever.
    """
    cdef xmlNode* node
    cdef bint fresh

    if cur.current is NULL:
        return NULL
    fresh = cur.current == cur.scope

    if step.type == STEP_SELF:
        cur.current = NULL
        if _if_check_all_preds(cur.scope, step):
            return cur.scope
        return NULL

    if step.type == STEP_PARENT:
        cur.current = NULL
        node = cur.scope.parent
        if node is not NULL and node.type == tree.XML_ELEMENT_NODE \
                and _if_check_all_preds(node, step):
            return node
        return NULL

    if step.type == STEP_CHILD or step.type == STEP_CHILD_STAR:
        cur.current = cur.scope.children if fresh else cur.current.next
        while cur.current is not NULL:
            if cur.current.type == tree.XML_ELEMENT_NODE \
                    and (step.type == STEP_CHILD_STAR
                         or _if_tag_matches(cur.current, step.c_href, step.c_tag, step.match_any_ns)) \
                    and _if_check_all_preds(cur.current, step):
                return cur.current
            cur.current = cur.current.next
        return NULL

    if step.type == STEP_DESCENDANTS or step.type == STEP_DESCENDANTS_STAR:
        cur.current = (_if_first_child_element(cur.scope) if fresh
                       else _if_next_descendant_element(cur.scope, cur.current))
        while cur.current is not NULL:
            if (step.type == STEP_DESCENDANTS_STAR
                    or _if_tag_matches(cur.current, step.c_href, step.c_tag, step.match_any_ns)) \
                    and _if_check_all_preds(cur.current, step):
                return cur.current
            cur.current = _if_next_descendant_element(cur.scope, cur.current)
        return NULL

    cur.current = NULL
    return NULL


# ---- C-level result holder ----

cdef class _IterFindResult:
    """Pure C-level result iterator over a compiled ElementPath subset.

    Owns the compiled steps array and a stack of cursors -- one per step.
    Each call to ``_next_node()`` advances the cursor stack and returns
    the next matching ``xmlNode*`` in document order, or NULL when no
    further match is reachable. Lazy: a path like ``item/name`` stops at
    the first item / first name and returns; subsequent calls keep
    walking from there.

    Exposes only cdef methods -- it does NOT implement Python's iterator
    protocol and does NOT wrap nodes into _Element. Callers (e.g.
    _elementpath.pxi) wrap results via _elementFactory() as needed.
    """
    # The compiled steps array AND the per-step cursor stack share a
    # single allocation. The buffer layout is::
    #
    #     [_IfStep × N][_IfCursor × N]
    #
    # so ``_cursors`` is just a pointer into the second half. One malloc
    # and one free per _IterFindResult instead of two.
    cdef _IfStep* _steps
    cdef int _step_count
    cdef _IfCursor* _cursors      # interior pointer into the steps buffer
    cdef int _depth               # current cursor index, -1 == exhausted

    def __cinit__(self):
        self._steps = NULL
        self._step_count = 0
        self._cursors = NULL
        self._depth = -1

    def __dealloc__(self):
        # _cursors lives in the same buffer as _steps; freed together.
        _if_free_steps(self._steps, self._step_count)

    cdef int _compile_and_run(self, xmlNode* c_node, const char* path,
                                _IfNsTable* nst) except -1:
        """Compile the path and prepare the cursor stack rooted at
        ``c_node``. No matching work is performed here -- _next_node()
        drives the lazy walk.
        """
        cdef _IfStep* steps
        cdef _IfStep* fused
        cdef int step_count = 0
        cdef int total
        cdef int i

        steps = _if_compile_path(path, &step_count, nst)
        if steps is NULL:
            raise SyntaxError("invalid path expression")

        if step_count == 0:
            self._steps = steps
            return 0

        # Realloc the steps buffer to also hold the cursors at the end.
        # On failure the original block is *not* freed by realloc, so we
        # have to free it explicitly before raising.
        total = step_count * <int>sizeof(_IfStep) + step_count * <int>sizeof(_IfCursor)
        fused = <_IfStep*>realloc(steps, total)
        if fused is NULL:
            _if_free_steps(steps, step_count)
            raise MemoryError()

        self._steps = fused
        self._step_count = step_count
        self._cursors = <_IfCursor*>(<char*>fused + step_count * <int>sizeof(_IfStep))
        for i in range(step_count):
            self._cursors[i].scope = NULL
            self._cursors[i].current = NULL    # NULL = exhausted until scope is set
        self._cursors[0].scope = c_node
        self._cursors[0].current = c_node      # current == scope marks "fresh"
        self._depth = 0
        return 0

    @cython.final
    cdef xmlNode* _next_node(self) noexcept:
        """Advance the cursor stack and return the next matching xmlNode*,
        or NULL when no further match is reachable.
        """
        cdef int last = self._step_count - 1
        cdef _IfCursor* cur
        cdef _IfCursor* child
        cdef xmlNode* m

        if self._depth < 0:
            return NULL

        while True:
            cur = &self._cursors[self._depth]
            m = _if_cursor_next(&self._steps[self._depth], cur)
            if m is not NULL:
                if self._depth == last:
                    return m
                # Descend: initialise the next-step cursor rooted at m
                self._depth += 1
                child = &self._cursors[self._depth]
                child.scope = m
                child.current = m                  # current == scope marks "fresh"
            else:
                # Backtrack
                if self._depth == 0:
                    self._depth = -1
                    return NULL
                self._depth -= 1


cdef int _iterfind_compile_into(_IterFindResult res, xmlNode* c_node,
                                 const char* c_path, object namespaces) except -1:
    """Build a namespace table from ``namespaces`` and run the compiled
    path against ``c_node`` into ``res``. ``res`` may be a subclass of
    ``_IterFindResult`` (e.g. _ElementPathIterator), in which case its
    extra fields must already be set by the caller.

    ``namespaces`` may be None or a dict mapping prefix (str) to URI (str).
    The dict's None or '' key (if any) is treated as the default namespace
    that is applied to bare element names. The dict is converted to a
    C-level namespace table once; the inner pipeline runs without the GIL.

    Raises SyntaxError on an invalid path.
    """
    cdef _IfNsTable nst
    cdef bytes prefix_bytes
    cdef bytes uri_bytes
    cdef const char* prefix_c
    cdef const char* uri_c
    cdef int prefix_len
    cdef int uri_len
    cdef object default_uri

    _if_ns_table_init(&nst)
    try:
        if namespaces:
            default_uri = namespaces.get(None)
            if default_uri is None:
                default_uri = namespaces.get('')
            elif '' in namespaces and namespaces[''] != default_uri:
                raise ValueError(
                    "Ambiguous default namespace: %r vs %r" % (
                        default_uri, namespaces['']))

            if default_uri:
                uri_bytes = default_uri.encode('utf-8') if isinstance(default_uri, str) else default_uri
                uri_c = <const char*>uri_bytes
                uri_len = <int>len(uri_bytes)
                if _if_ns_table_add(&nst, NULL, 0, uri_c, uri_len) < 0:
                    raise MemoryError()

            for key, val in namespaces.items():
                if key is None or key == '':
                    continue
                if val is None:
                    continue
                prefix_bytes = key.encode('utf-8') if isinstance(key, str) else key
                uri_bytes = val.encode('utf-8') if isinstance(val, str) else val
                prefix_c = <const char*>prefix_bytes
                uri_c = <const char*>uri_bytes
                prefix_len = <int>len(prefix_bytes)
                uri_len = <int>len(uri_bytes)
                if _if_ns_table_add(&nst, prefix_c, prefix_len, uri_c, uri_len) < 0:
                    raise MemoryError()

        res._compile_and_run(c_node, c_path, &nst)
    finally:
        _if_ns_table_free(&nst)
    return 0


cdef _IterFindResult _iterfind_run(xmlNode* c_node, const char* c_path,
                                    object namespaces):
    """Convenience wrapper: create a fresh _IterFindResult and run the path
    into it. Used by callers that don't need their own subclass instance
    (e.g. find / findall, which consume the result list directly).
    """
    cdef _IterFindResult res = _IterFindResult()
    _iterfind_compile_into(res, c_node, c_path, namespaces)
    return res
