"""
This takes the feedparser tests from here:

  http://feedparser.org/tests/wellformed/sanitize/

and rewrites them to be easier to handle (not using the internal model
of feedparser).  The input format is::

  <!--
  Description: {description}
  Expect: {expression}
  -->
  ...
  <content ...>{content}</content>
  ...

The Expect expression is checked for
``entries[0]['content'][0]['value'] == {data}``.

The output format is::

  Description: {description}
  Expect: {expression} (if data couldn't be parsed)
  Options: 

  {content, unescaped}
  ----------
  {data, unescaped, if found}

"""

import re
import os
import traceback

_desc_re = re.compile(r'\s*Description:\s*(.*)')
_expect_re = re.compile(r'\s*Expect:\s*(.*)')
_data_expect_re = re.compile(r"entries\[0\]\['[^']+'\](?:\[0\]\['value'\])?\s*==\s*(.*)")
_feed_data_expect_re = re.compile(r"feed\['[^']+'\]\s*==\s*(.*)")

def parse_content(content):
    match = _desc_re.search(content)
    desc = match.group(1)
    match = _expect_re.search(content)
    expect = match.group(1)
    data = None
    for regex in [_data_expect_re, _feed_data_expect_re]:
        match = regex.search(expect)
        if match:
            # Icky, but I'll trust it
            data = eval(match.group(1).strip())
            break
    c = None
    for tag in ['content', 'summary', 'title', 'copyright', 'tagline', 'info', 'subtitle', 'fullitem', 'body', 'description', 'content:encoded']:
        regex = re.compile(r"<%s.*?>(.*)</%s>" % (tag, tag), re.S)
        match = regex.search(content)
        if match:
            c = match.group(1)
            break
    assert c is not None
    # Seems like body isn't quoted
    if tag != 'body':
        c = c.replace('&lt;', '<')
        c = c.replace('&amp;', '&')
    # FIXME: I should really do more unescaping...
    return {
        'Description': desc,
        'Expect': expect,
        'data': data,
        'content': c}

def serialize_content(d):
    s = '''\
Description: %(Description)s
Expect: %(Expect)s
Options: 

%(content)s
''' % d
    if d.get('data') is not None:
        s += '----------\n%s' % d['data']
    return s

def translate_file(filename):
    f = open(filename, 'rb')
    c = f.read()
    f.close()
    try:
        output = serialize_content(parse_content(c))
    except:
        print('Bad data in %s:' % filename)
        print(c)
        traceback.print_exc()
        print('-'*60)
        return
    new = os.path.splitext(filename)[0] + '.data'
    f = open(new, 'wb')
    f.write(output)
    f.close()

def translate_all(dir):
    for fn in os.listdir(dir):
        fn = os.path.join(dir, fn)
        if fn.endswith('.xml'):
            translate_file(fn)
        
if __name__ == '__main__':
    translate_all(os.path.join(os.path.dirname(__file__), 'feedparser-data'))

