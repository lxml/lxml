#!/usr/bin/python

"""
A minimal front end to the Docutils Publisher, producing HTML with
Pygments syntax highlighting.
"""

# Set to True if you want inline CSS styles instead of classes
INLINESTYLES = False


try:
    import locale
    locale.setlocale(locale.LC_ALL, '')
except:
    pass

# set up Pygments

from pygments.formatters import HtmlFormatter

# The default formatter
DEFAULT = HtmlFormatter(noclasses=INLINESTYLES, cssclass='syntax')

# Add name -> formatter pairs for every variant you want to use
VARIANTS = {
    # 'linenos': HtmlFormatter(noclasses=INLINESTYLES, linenos=True),
}


from docutils import nodes
from docutils.parsers.rst import directives

from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer

def pygments_directive(name, arguments, options, content, lineno,
                       content_offset, block_text, state, state_machine):
    try:
        lexer = get_lexer_by_name(arguments[0])
    except ValueError, e:
        # no lexer found - use the text one instead of an exception
        lexer = TextLexer()
    # take an arbitrary option if more than one is given
    formatter = options and VARIANTS[options.keys()[0]] or DEFAULT
    parsed = highlight(u'\n'.join(content), lexer, formatter)
    return [nodes.raw('', parsed, format='html')]

pygments_directive.arguments = (1, 0, 1)
pygments_directive.content = 1
pygments_directive.options = dict([(key, directives.flag) for key in VARIANTS])

directives.register_directive('sourcecode', pygments_directive)


# run the generation

from docutils.core import publish_cmdline, default_description

description = ('Generates (X)HTML documents from standalone reStructuredText '
               'sources.  ' + default_description)

publish_cmdline(writer_name='html', description=description)
