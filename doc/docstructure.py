
SITE_STRUCTURE = [
    ('lxml', ('main.txt', 'intro.txt', '../INSTALL.txt', # 'lxml2.txt',
              'performance.txt', 'compatibility.txt', 'FAQ.txt')),
    ('Developing with lxml', ('tutorial.txt', '@API reference',
                              'api.txt', 'parsing.txt',
                              'validation.txt', 'xpathxslt.txt',
                              'objectify.txt', 'lxmlhtml.txt',
                              'cssselect.txt', 'elementsoup.txt',
                              'html5parser.txt')),
    ('Extending lxml', ('resolvers.txt', 'extensions.txt',
                        'element_classes.txt', 'sax.txt', 'capi.txt')),
    ('Developing lxml', ('build.txt', 'lxml-source-howto.txt',
                         '@Release Changelog', '../CREDITS.txt')),
    ]

HREF_MAP = {
    "API reference" : "api/index.html"
}

BASENAME_MAP = {
    'main' : 'index',
    'INSTALL' : 'installation',
    'CREDITS' : 'credits',
}
