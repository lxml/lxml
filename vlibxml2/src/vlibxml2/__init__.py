from vlibxml2_mod import *
import vlibxml2_mod
import victree


class xmlNodeSub(vlibxml2_mod.vlibxml2_xmlNode):
    '''
    Just an empty subclass of vlibxml2_xmlNode to enable weak references
    '''
    __slots__ = ['__weakref__', '__dict__']

class xmlDocSub(vlibxml2_mod.vlibxml2_xmlDoc):
    '''
    Just an empty subclass of vlibxml2_xmlDoc to enable weak references
    '''
    __slots__ = ['__weakref__', '__dict__']

