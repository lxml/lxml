"""Doctest module for HTML comparison.

Usage::

   >>> import lxml.html.usedoctest
   >>> # now do your HTML doctests ...

See `lxml.doctestcompare`.
"""

import sys
from lxml import doctestcompare

if sys.version_info[0] < 3:
    doctestcompare.temp_install(html=True, del_module=__name__)
