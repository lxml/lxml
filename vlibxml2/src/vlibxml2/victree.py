'''
ElementTree compatible API for vlibxml2
'''
import re
import vlibxml2
import vlibxml2_mod

# The following regular expression will match
# the 'old-style' regexs used by ElementTree.
# Basically ".//name", "//name", "//name[@id=attribute]"
oldRE = re.compile("\.?//([^[]+)((\[@id=)(\S+)(\]))?$")

def parse(utf8String):
    '''
    parse an incoming XML fragment and generate an Element object
    '''
    elem = _Element()
    elem._node = vlibxml2.parseDoc(utf8String).rootElement()
    return elem

def Element(name, **kwargs):
    elem = _Element()
    elem._node = vlibxml2.newNode(name)
    elem._node.setContent('')
    for key in kwargs.keys():
        elem._node.setProp(key, str(kwargs[key]))
    return elem

class _Element(object):

    def _get_tag(self):
        return self._node.name()
    def _set_tag(self, tag):
        self._node.setName(tag)
    tag = property(_get_tag, _set_tag)

    def children(self):
        result = []
        childNodes = self._node.children()
        elementTypes = vlibxml2_mod.const_xmlElementType()
        for node in childNodes:
            if node.type() <> elementTypes.getXML_ELEMENT_NODE():
                # we want to skip over anything that's not an Element
                continue
            elem = _Element()
            elem._node = node
            result.append(elem)
        return result

    def clearChildren(self):
        for node in self._node.children():
            node.unlinkNode()

    def replaceNode(self, other):
        self._node.replaceNode(other._node)

    def items(self):
        return self._node.properties().values()

    def keys(self):
        return self._node.properties().keys()

    def append(self, other):
        self._node.addChild(other._node)

    def set(self, propName, propValue):
        if type(propValue) <> str:
            propValue = str(propValue)
        self._node.setProp(propName, propValue)

    def find(self, etreeXpath):
        '''
        the half-baked XPath syntax of ElementTree is supported here.

        Use xpathEval to get full access to libxml2 XPath goodness
        '''
        matches = oldRE.match(etreeXpath)
        if matches is None:
            raise '''Invalid ElementTree style XPath! "%s"''' % etreeXpath
        
        name, id = (matches.groups()[0], matches.groups()[3])
        if id is not None:
            fixedXPath = "//%s[@id='%s']" % (name, id)
        else:
            fixedXPath = "//%s" % name

        nodes = self.xpathEval(fixedXPath)
        if len(nodes) > 0:
            return nodes[0]
        return None

    def xpathEval(self, xpathExpr):
        result = []
        for node in self._node.xpathEval(xpathExpr):
            elem = _Element()
            elem._node = node
            result.append(elem)
        return result

    def __eq__(self, other):
        if other == None:
            return False
        if self._node == other._node:
            return True
        return False

    def __hash__(self):
        return "%s-%d" % (self.__class__.__name__, self._node.__hash__())

    def __getitem__(self, key):
        return self._node.prop(key)

    def __setitem__(self, key, value):
        self._node.setProp(key, value)

    def __str__(self):
        return str(self._node)

    def _get_text(self):
        return self._node.content()
    def _set_text(self, value):
        self._node.setContent(value)

    text = property(_get_text, _set_text)

