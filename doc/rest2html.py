#!/usr/bin/python

# Author: David Goodger
# Contact: goodger@python.org
# Revision: $Revision: 3901 $
# Date: $Date: 2005-09-25 17:49:54 +0200 (Sun, 25 Sep 2005) $
# Copyright: This module has been placed in the public domain.

"""
A minimal front end to the Docutils Publisher, producing HTML.
"""

try:
    import locale
    locale.setlocale(locale.LC_ALL, '')
except:
    pass

from docutils.core import publish_cmdline, default_description


description = ('Generates (X)HTML documents from standalone reStructuredText '
               'sources.  ' + default_description)

publish_cmdline(writer_name='html', description=description)
