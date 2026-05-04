/* Link verification test for lxml dependencies.
 *
 * Verifies that libxml2, libxslt, and zlib (the libraries lxml depends on)
 * are correctly built and linkable for the Nanvix target. This is a smoke
 * test that exercises the dependency chain without requiring CPython.
 */
#include <libxml/parser.h>
#include <libxslt/xslt.h>
#include <string.h>

static const char *TEST_XML = "<doc><p>lxml deps OK</p></doc>";

int main(void) {
    xmlDocPtr doc;

    xmlInitParser();
    xsltInit();

    doc = xmlParseMemory(TEST_XML, (int)strlen(TEST_XML));
    if (!doc) return 1;

    xmlFreeDoc(doc);
    xsltCleanupGlobals();
    xmlCleanupParser();
    return 0;
}
