
"""

Fuzzes the lxml.etree.XML function with the Atheris fuzzer.

The goal is to catch unhandled exceptions and potential 
memory corruption issues in auto-generated code.

"""

import atheris
import sys

from lxml import etree as et

def TestOneInput(data):
  fdp = atheris.FuzzedDataProvider(data)

  try:
    root = et.XML(fdp.ConsumeUnicode(sys.maxsize))
  except et.XMLSyntaxError:
    None
  return

atheris.Setup(sys.argv, TestOneInput, enable_python_coverage=True)
atheris.Fuzz()
