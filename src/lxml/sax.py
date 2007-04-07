from xml.sax.handler import ContentHandler
from etree import ElementTree, Element, SubElement, LxmlError

class SaxError(LxmlError):
    pass

def _getNsTag(tag):
    if tag[0] == '{':
        return tuple(tag[1:].split('}', 1))
    else:
        return (None, tag)

class ElementTreeContentHandler(object, ContentHandler):
    """Build an lxml ElementTree from SAX events.
    """
    def __init__(self, makeelement=None):
        self._root = None
        self._element_stack = []
        self._default_ns = None
        self._ns_mapping = { None : [None] }
        self._new_mappings = {}
        if makeelement is None:
            makeelement = Element
        self._makeelement = makeelement

    def _get_etree(self):
        "Contains the generated ElementTree after parsing is finished."
        return ElementTree(self._root)

    etree = property(_get_etree, doc=_get_etree.__doc__)
    
    def setDocumentLocator(self, locator):
        pass

    def startDocument(self):
        pass

    def endDocument(self):
        pass

    def startPrefixMapping(self, prefix, uri):
        self._new_mappings[prefix] = uri
        try:
            self._ns_mapping[prefix].append(uri)
        except KeyError:
            self._ns_mapping[prefix] = [uri]
        if prefix is None:
            self._default_ns = uri

    def endPrefixMapping(self, prefix):
        ns_uri_list = self._ns_mapping[prefix]
        ns_uri_list.pop()
        if prefix is None:
            self._default_ns = ns_uri_list[-1]

    def startElementNS(self, ns_name, qname, attributes=None):
        ns_uri, local_name = ns_name
        if ns_uri:
            el_name = "{%s}%s" % ns_name
        elif self._default_ns:
            el_name = "{%s}%s" % (self._default_ns, local_name)
        else:
            el_name = local_name

        if attributes:
            attrs = {}
            try:
                iter_attributes = attributes.iteritems()
            except AttributeError:
                iter_attributes = attributes.items()

            for name_tuple, value in iter_attributes:
                if name_tuple[0]:
                    attr_name = "{%s}%s" % name_tuple
                else:
                    attr_name = name_tuple[1]
                attrs[attr_name] = value
        else:
            attrs = None

        element_stack = self._element_stack
        if self._root is None:
            element = self._root = \
                      self._makeelement(el_name, attrs, self._new_mappings)
        else:
            element = SubElement(element_stack[-1], el_name,
                                 attrs, self._new_mappings)
        element_stack.append(element)

        self._new_mappings.clear()

    def endElementNS(self, ns_name, qname):
        element = self._element_stack.pop()
        tag = element.tag
        if ns_name != _getNsTag(tag):
            raise SaxError, "Unexpected element closed: {%s}%s" % ns_name

    def startElement(self, name, attributes=None):
        self.startElementNS((None, name), name, attributes)

    def endElement(self, name):
        self.endElementNS((None, name), name)

    def characters(self, data):
        last_element = self._element_stack[-1]
        try:
            # if there already is a child element, we must append to its tail
            last_element = last_element[-1]
            last_element.tail = (last_element.tail or u'') + data
        except IndexError:
            # otherwise: append to the text
            last_element.text = (last_element.text or u'') + data

class ElementTreeProducer(object):
    """Produces SAX events for an element and children.
    """
    def __init__(self, element_or_tree, content_handler):
        try:
            element = element_or_tree.getroot()
        except AttributeError:
            element = element_or_tree
        self._element = element
        self._content_handler = content_handler
        from xml.sax.xmlreader import AttributesNSImpl as attr_class
        self._attr_class = attr_class
        self._empty_attributes = attr_class({}, {})
        
    def saxify(self):
        self._content_handler.startDocument()
        self._recursive_saxify(self._element, {})
        self._content_handler.endDocument()

    def _recursive_saxify(self, element, prefixes):
        new_prefixes = []
        build_qname = self._build_qname
        attribs = element.items()
        if attribs:
            attr_values = {}
            attr_qnames = {}
            for attr_ns_name, value in attribs:
                attr_ns_tuple = _getNsTag(attr_ns_name)
                attr_values[attr_ns_tuple] = value
                attr_qnames[attr_ns_tuple] = build_qname(
                    attr_ns_tuple[0], attr_ns_tuple[1], prefixes, new_prefixes)
            sax_attributes = self._attr_class(attr_values, attr_qnames)
        else:
            sax_attributes = self._empty_attributes

        ns_uri, local_name = _getNsTag(element.tag)
        qname = build_qname(ns_uri, local_name, prefixes, new_prefixes)

        content_handler = self._content_handler
        for prefix, uri in new_prefixes:
            content_handler.startPrefixMapping(prefix, uri)
        content_handler.startElementNS((ns_uri, local_name),
                                       qname, sax_attributes)
        if element.text:
            content_handler.characters(element.text)
        for child in element:
            self._recursive_saxify(child, prefixes)
        content_handler.endElementNS((ns_uri, local_name), qname)
        for prefix, uri in new_prefixes:
            content_handler.endPrefixMapping(prefix)
        if element.tail:
            content_handler.characters(element.tail)

    def _build_qname(self, ns_uri, local_name, prefixes, new_prefixes):
        if ns_uri is None:
            return local_name
        try:
            prefix = prefixes[ns_uri]
        except KeyError:
            prefix = prefixes[ns_uri] = u'ns%02d' % len(prefixes)
            new_prefixes.append( (prefix, ns_uri) )
        return prefix + ':' + local_name

def saxify(element_or_tree, content_handler):
    return ElementTreeProducer(element_or_tree, content_handler).saxify()
