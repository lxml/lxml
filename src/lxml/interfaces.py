
class XMLParseError(Exception):
    pass

def parseFile(path):
    """Parse a file.

    Raises XMLParseError in case of errors.
    """

def parseString(text):
    """Parse XML string.

    Raise XMLParseError in case of errors.
    """

def parseMiniDOM(minidom):
    """Parse miniDOM tree into libxml tree.
    """

# simple XML object encapsulating the raw tree
class IXML:
    def getElementTree():
        """Get ElementTree representation for reading and manipulation.
        """

    def xpath(expression):
        """Execute xpath expression and return element tree nodes.
        """

    def toText():
        """Serialize this XML to text.
        """


        
class IXSLT(IXML):
    def transform(xml):
        """Transform XML according to this stylesheet.
        """
    
# ElementTree based API?
class IELementTree:
    pass

class IElement:
    tag = IAttribute('Element name')
    attrib = IAttribute('Dictionary of attributes')
    text = IAttribute('Element textual content (start)')
    tail = IAttribute('Any trailing text')

    def __getitem__(self, value):
        """Get subelement.
        """

class IText:
    pass

class IComment:
    pass


# xpath expression gives back nodes

# xslt transformation possible against XML
