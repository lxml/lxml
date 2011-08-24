# this is a package

import os

def get_include():
    """
    Returns a list of include path (libxml2, libxslt) needed to lxml.
    """
    lxml_path = __path__[0]
    include_path = os.path.join(lxml_path, 'include')
    includes = [lxml_path]

    for name in os.listdir(include_path):
        includes.append(os.path.join(include_path, name))

    return includes

