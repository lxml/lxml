#
# ElementTree
# $Id: ElementPath.py 3276 2007-09-12 06:52:30Z fredrik $
#
# limited xpath support for element trees
#
# history:
# 2003-05-23 fl   created
# 2003-05-28 fl   added support for // etc
# 2003-08-27 fl   fixed parsing of periods in element names
# 2007-09-10 fl   new selection engine
#
# Copyright (c) 2003-2007 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2007 by Fredrik Lundh
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

import re

xpath_tokenizer = re.compile(
    "("
    "'[^']*'|\"[^\"]*\"|"
    "::|"
    "//?|"
    "\.\.|"
    "\(\)|"
    "[/.*:\[\]\(\)@=])|"
    "((?:\{[^}]+\})?[^/:\[\]\(\)@=\s]+)|"
    "\s+"
    ).findall

def prepare_tag(next, token):
    tag = token[1]
    def select(result):
        for elem in result:
            for e in elem.iterchildren(tag=tag):
                yield e
    return select

def prepare_star(next, token):
    def select(result):
        for elem in result:
            for e in elem:
                yield e
    return select

def prepare_dot(next, token):
    def select(result):
        return result
    return select

def prepare_iter(next, token):
    token = next()
    if token[0] == "*":
        tag = "*"
    elif not token[0]:
        tag = token[1]
    else:
        raise SyntaxError
    def select(result):
        for elem in result:
            for e in elem.iterdescendants(tag=tag):
                yield e
    return select

def prepare_dot_dot(next, token):
    def select(result):
        for elem in result:
            parent = elem.getparent()
            if parent is not None:
                yield parent
    return select

def prepare_predicate(next, token):
    # this one should probably be refactored...
    token = next()
    if token[0] == "@":
        # attribute
        token = next()
        if token[0]:
            raise SyntaxError("invalid attribute predicate")
        key = token[1]
        token = next()
        if token[0] == "]":
            def select(result):
                for elem in result:
                    if elem.get(key) is not None:
                        yield elem
        elif token[0] == "=":
            value = next()[0]
            if value[:1] == "'" or value[:1] == '"':
                value = value[1:-1]
            else:
                raise SyntaxError("invalid comparison target")
            token = next()
            def select(result):
                for elem in result:
                    if elem.get(key) == value:
                        yield elem
        if token[0] != "]":
            raise SyntaxError("invalid attribute predicate")
    elif not token[0]:
        tag = token[1]
        token = next()
        if token[0] != "]":
            raise SyntaxError("invalid node predicate")
        def select(result):
            for elem in result:
                if find(elem, tag) is not None:
                    yield elem
    else:
        raise SyntaxError("invalid predicate")
    return select

ops = {
    "": prepare_tag,
    "*": prepare_star,
    ".": prepare_dot,
    "..": prepare_dot_dot,
    "//": prepare_iter,
    "[": prepare_predicate,
    }

_cache = {}

# --------------------------------------------------------------------

def _build_path_iterator(path):
    # compile selector pattern
    try:
        return _cache[path]
    except KeyError:
        pass
    if len(_cache) > 100:
        _cache.clear()

    if path[:1] == "/":
        raise SyntaxError("cannot use absolute path on element")
    stream = iter(xpath_tokenizer(path))
    try:
        _next = stream.next
    except AttributeError:
        # Python 3
        def _next():
            return next(stream)
    token = _next()
    selector = []
    while 1:
        try:
            selector.append(ops[token[0]](_next, token))
        except StopIteration:
            raise SyntaxError("invalid path")
        try:
            token = _next()
            if token[0] == "/":
                token = _next()
        except StopIteration:
            break
    return selector

##
# Iterate over the matching nodes

def iterfind(elem, path):
    # execute selector pattern
    selector = _build_path_iterator(path)
    result = iter((elem,))
    for select in selector:
        result = select(result)
    return result

##
# Find first matching object.

def find(elem, path):
    it = iterfind(elem, path)
    try:
        try:
            _next = it.next
        except AttributeError:
            return next(it)
        else:
            return _next()
    except StopIteration:
        return None

##
# Find all matching objects.

def findall(elem, path):
    return list(iterfind(elem, path))

##
# Find text for first matching object.

def findtext(elem, path, default=None):
    el = find(elem, path)
    if el is None:
        return default
    else:
        return el.text or ''
