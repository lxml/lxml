#!/usr/bin/env python

import operator
import os.path
import sys
import xml.etree.ElementTree as ET

BUILD_SOURCE_FILE = os.path.join("src", "lxml", "xmlerror.pxi")
BUILD_DEF_FILE    = os.path.join("src", "lxml", "includes", "xmlerror.pxd")

# map enum name to Python variable name and alignment for constant name
ENUM_MAP = {
    'xmlErrorLevel'       : ('__ERROR_LEVELS',  'XML_ERR_'),
    'xmlErrorDomain'      : ('__ERROR_DOMAINS', 'XML_FROM_'),
    'xmlParserErrors'     : ('__PARSER_ERROR_TYPES',   'XML_'),
#    'xmlXPathError'       : ('__XPATH_ERROR_TYPES',   ''),
#    'xmlSchemaValidError' : ('__XMLSCHEMA_ERROR_TYPES',   'XML_'),
    'xmlRelaxNGValidErr'  : ('__RELAXNG_ERROR_TYPES',   'XML_'),
    }

ENUM_ORDER = (
    'xmlErrorLevel',
    'xmlErrorDomain',
    'xmlParserErrors',
#    'xmlXPathError',
#    'xmlSchemaValidError',
    'xmlRelaxNGValidErr')

COMMENT = """
# This section is generated by the script '%s'.

""" % os.path.basename(sys.argv[0])


def split(lines):
    lines = iter(lines)
    pre = []
    for line in lines:
        pre.append(line)
        if line.startswith('#') and "BEGIN: GENERATED CONSTANTS" in line:
            break
    pre.append('')
    old = []
    for line in lines:
        if line.startswith('#') and "END: GENERATED CONSTANTS" in line:
            break
        old.append(line.rstrip('\n'))
    post = ['', line]
    post.extend(lines)
    post.append('')
    return pre, old, post


def regenerate_file(filename, result):
    new = COMMENT + '\n'.join(result)

    # read .pxi source file
    with open(filename, 'r', encoding="utf-8") as f:
        pre, old, post = split(f)

    if new.strip() == '\n'.join(old).strip():
        # no changes
        return False

    # write .pxi source file
    with open(filename, 'w', encoding="utf-8") as f:
        f.write(''.join(pre))
        f.write(new)
        f.write(''.join(post))

    return True


def parse_enums(doc_dir, api_filename, enum_dict):
    tree = ET.parse(os.path.join(doc_dir, api_filename))
    for enum in tree.iterfind('symbols/enum'):
        enum_type = enum.get('type')
        if enum_type not in ENUM_MAP:
            continue
        entries = enum_dict.get(enum_type)
        if not entries:
            print("Found enum", enum_type)
            entries = enum_dict[enum_type] = []
        entries.append((
            enum.get('name'),
            int(enum.get('value')),
            enum.get('info', '').strip(),
        ))


def main(doc_dir):
    enum_dict = {}
    parse_enums(doc_dir, 'libxml2-api.xml',   enum_dict)
    #parse_enums(doc_dir, 'libxml-xmlerror.html',   enum_dict)
    #parse_enums(doc_dir, 'libxml-xpath.html',      enum_dict)
    #parse_enums(doc_dir, 'libxml-xmlschemas.html', enum_dict)
    #parse_enums(doc_dir, 'libxml-relaxng.html',    enum_dict)

    # regenerate source files
    pxi_result = []
    append_pxi = pxi_result.append
    pxd_result = []
    append_pxd = pxd_result.append

    append_pxd('cdef extern from "libxml/xmlerror.h":')

    ctypedef_indent = ' '*4
    constant_indent = ctypedef_indent*2

    for enum_name in ENUM_ORDER:
        constants = enum_dict[enum_name]
        constants.sort(key=operator.itemgetter(1))
        pxi_name, prefix = ENUM_MAP[enum_name]

        append_pxd(ctypedef_indent + 'ctypedef enum %s:' % enum_name)
        append_pxi('cdef object %s = """\\' % pxi_name)

        prefix_len = len(prefix)
        length = 2  # each string ends with '\n\0'
        for name, val, descr in constants:
            if descr and descr != str(val):
                line = '%-50s = %7d # %s' % (name, val, descr)
            else:
                line = '%-50s = %7d' % (name, val)
            append_pxd(constant_indent + line)

            if name[:prefix_len] == prefix and len(name) > prefix_len:
                name = name[prefix_len:]
            line = '%s=%d' % (name, val)
            append_pxi(line)
            length += len(line) + 2  # + '\n\0'

        append_pxd('')
        append_pxi('"""')
        append_pxi('')

    # write source files
    print("Updating file %s" % BUILD_SOURCE_FILE)
    updated = regenerate_file(BUILD_SOURCE_FILE, pxi_result)
    if not updated:
        print("No changes.")

    print("Updating file %s" % BUILD_DEF_FILE)
    updated = regenerate_file(BUILD_DEF_FILE,    pxd_result)
    if not updated:
        print("No changes.")

    print("Done")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1].lower() in ('-h', '--help'):
        print("This script generates the constants in file %s" % BUILD_SOURCE_FILE)
        print("Call as")
        print(sys.argv[0], "/path/to/libxml2-doc-dir")
        sys.exit(len(sys.argv) > 1)

    main(sys.argv[1])
