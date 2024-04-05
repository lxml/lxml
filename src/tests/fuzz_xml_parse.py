"""
Fuzzes the lxml.etree.XML function with the Atheris fuzzer.

The goal is to catch unhandled exceptions and potential 
memory corruption issues in auto-generated code.
"""

import atheris
import sys

from lxml import etree


def test_etree_xml(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        etree.XML(fdp.ConsumeUnicode(sys.maxsize))
    except etree.XMLSyntaxError:
        pass
    return


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_etree_xml, enable_python_coverage=True)
    atheris.Fuzz()
