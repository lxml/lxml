This is my first crack at wrapping the libxml2 libraries using Pyrex.


No warranty for this software.  It may memory leak, it may trash your files.
It may even kill you.

But I'm not responsible.  Use it at your own risk.  I'll fix bugs as quick as I
can (if I hear about them).

All code is released under a standard BSD license.  See LICENSE.TXT for the
complete details.

Victor Ng
email: vng1@mac.com

---


How to use vlibxml2:

It's pretty straight forward.  I only exposed a couple methods right
now.  There's undoubtedly bugs and weird glitches that I'm just not
aware of.  Please email me any bugs you find.

Just read through the test.py script to see what to do.

The simplest stuff is:

>>> import vlibxml2
>>> node = vlibxml2.newNode('foo')
>>> node.setProp('bar', '123')
>>> print node
<foo bar="123"/>

Parsing an existing document:

>>> doc = vlibxml2.parseDoc(open('yourfile.xml','rb').read())

Grabbing nodes via XPath:

>>> doc.xpathEval('//title')

It's easy.  If you can't figure it out - just read the test cases and
play with it.  It probably won't make your computer blow up.




