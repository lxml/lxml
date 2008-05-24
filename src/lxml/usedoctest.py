"""Doctest module for XML comparison.

Usage::

   >>> import lxml.usedoctest
   >>> # now do your XML doctests ...

See `lxml.doctestcompare`
"""

import sys
from lxml import doctestcompare

if sys.version_info[0] < 3:
    doctestcompare.temp_install(del_module=__name__)
