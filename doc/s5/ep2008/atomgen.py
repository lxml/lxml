# atomgen.py

import os.path

from lxml import etree
from lxml.builder import ElementMaker

ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"

A = ElementMaker(namespace=ATOM_NAMESPACE,
                 nsmap={None : ATOM_NAMESPACE})

feed      = A.feed
entry     = A.entry
title     = A.title
author    = A.author
name      = A.name
link      = A.link
summary   = A.summary
id        = A.id
updated   = A.updated
# ... and so on and so forth ...


# plus a little validation function: isvalid()
isvalid = etree.RelaxNG(
    file=os.path.join(os.path.abspath(os.path.dirname(__file__)), "atom.rng"))
