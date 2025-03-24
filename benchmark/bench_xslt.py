import benchbase
from benchbase import onlylib


############################################################
# Benchmarks
############################################################

class XSLTBenchMark(benchbase.TreeBenchMark):
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
