import sys, copy
from itertools import *
from StringIO import StringIO

import benchbase
from benchbase import with_attributes, with_text, onlylib, serialized

############################################################
# Benchmarks
############################################################

class XSLTBenchMark(benchbase.TreeBenchMark):
    @onlylib('lxe')
    def bench_xslt_extensions_old(self, root):
        tree = self.etree.XML("""\
<xsl:stylesheet version="1.0"
   xmlns:l="test"
   xmlns:testns="testns"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <l:data>TEST</l:data>
  <xsl:template match="/">
    <l:result>
      <xsl:for-each select="*/*">
        <xsl:copy-of select="testns:child(.)"/>
      </xsl:for-each>
    </l:result>
  </xsl:template>
</xsl:stylesheet>
""")
        def return_child(_, elements):
            return elements[0][0]

        extensions = {('testns', 'child') : return_child}

        transform = self.etree.XSLT(tree, extensions)
        for i in range(10):
            transform(root)

    @onlylib('lxe')
    def bench_xslt_document(self, root):
        transform = self.etree.XSLT(self.etree.XML("""\
<xsl:stylesheet version="1.0"
   xmlns:l="test"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <l:data>TEST</l:data>
  <xsl:template match="/">
    <l:result>
      <xsl:for-each select="*/*">
        <l:test><xsl:copy-of select="document('')//l:data/text()"/></l:test>
      </xsl:for-each>
    </l:result>
  </xsl:template>
</xsl:stylesheet>
"""))
        transform(root)

if __name__ == '__main__':
    benchbase.main(XSLTBenchMark)
