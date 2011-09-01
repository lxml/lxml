# this is a package

import os

def get_include():
    """
    Returns a list of header include paths (for lxml itself, libxml2
    and libxslt) needed to compile C code against lxml if it was built
    with statically linked libraries.
    """
    lxml_path = __path__[0]
    include_path = os.path.join(lxml_path, 'include')
    includes = [lxml_path]

    for name in os.listdir(include_path):
        includes.append(os.path.join(include_path, name))

    return includes

