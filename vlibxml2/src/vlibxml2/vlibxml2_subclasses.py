import vlibxml2_mod

class xmlNodeSub(vlibxml2_mod.vlibxml2_xmlNode):
    '''
    Just an empty subclass of vlibxml2_xmlNode to enable weak references
    '''
    __slots__ = ['__weakref__']

class xmlDocSub(vlibxml2_mod.vlibxml2_xmlDoc):
    '''
    Just an empty subclass of vlibxml2_xmlDoc to enable weak references
    '''
    __slots__ = ['__weakref__']
