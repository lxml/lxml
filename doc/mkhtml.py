from lxml.etree import parse, Element, SubElement, XPath
import os, shutil, re, sys, copy

SITE_STRUCTURE = [
    ('lxml', ('main.txt', 'intro.txt', 'FAQ.txt', 'compatibility.txt',
              'performance.txt', 'build.txt')),
    ('Developing with lxml', ('api.txt', 'parsing.txt', 'validation.txt',
                              'xpathxslt.txt', 'objectify.txt')),
    ('Extending lxml', ('resolvers.txt', 'extensions.txt', 'element_classes.txt',
                        'sax.txt', 'capi.txt')),
    ]

RST2HTML_OPTIONS = " ".join([
    "--no-toc-backlinks",
    "--strip-comments",
    ])

find_title = XPath("/h:html/h:head/h:title/text()",
                            {"h" : "http://www.w3.org/1999/xhtml"})
find_headings = XPath("//h:h1[not(@class)]/h:a/text()",
                            {"h" : "http://www.w3.org/1999/xhtml"})
find_menu = XPath("//h:ul[@id=$name]",
                  {"h" : "http://www.w3.org/1999/xhtml"})

replace_invalid = re.compile(r'[-_/.\s\\]').sub

def build_menu(tree, basename, section, menuroot):
    section_head = menuroot.xpath("//ul[@id=$section]/li", section=section)
    if not section_head:
        ul = SubElement(menuroot, "ul", id=section)
        section_head = SubElement(ul, "li")
        title = SubElement(section_head, "span", {"class":"section title"})
        title.text = section
    else:
        section_head = section_head[0]
    page_title = find_title(tree)
    if page_title:
        page_title = page_title[0]
    else:
        page_title = replace_invalid(' ', basename.capitalize())
    headings = find_headings(tree)
    if headings:
        ul = SubElement(section_head, "ul", {"class":"menu foreign", "id":basename})

        title = SubElement(ul, "li", {"class":"menu title"})
        a = SubElement(title, "a", href=basename+".html")
        a.text = page_title

        subul = SubElement(title, "ul", {"class":"submenu"})
        for heading in headings:
            li = SubElement(subul, "li", {"class":"menu item"})
            ref = replace_invalid('-', heading.lower())
            a  = SubElement(li, "a", href=basename+".html#"+ref)
            a.text = heading

def merge_menu(tree, menu, name):
    menu_root = copy.deepcopy(menu)
    tree.getroot()[1][0].insert(0, menu_root) # html->body->div[class=document]
    for el in menu_root.getiterator():
        tag = el.tag
        if tag[0] != '{':
            el.tag = "{http://www.w3.org/1999/xhtml}" + tag
    current_menu = find_menu(menu_root, name=name)
    if current_menu:
        for submenu in current_menu:
            submenu.set("class", submenu.get("class", "").
                        replace("foreign", "current"))
    return tree

def rest2html(script, source_path, dest_path, stylesheet_url):
    command = ('%s %s %s --stylesheet=%s --link-stylesheet %s > %s' %
               (sys.executable, script, RST2HTML_OPTIONS,
                stylesheet_url, source_path, dest_path))
    os.system(command)

def publish(dirname, lxml_path, release):
    if not os.path.exists(dirname):
        os.mkdir(dirname)

    doc_dir = os.path.join(lxml_path, 'doc')
    script = os.path.join(doc_dir, 'rest2html.py')
    pubkey = os.path.join(doc_dir, 'pubkey.asc')
    stylesheet_url = 'style.css'

    shutil.copy(pubkey, dirname)

    trees = {}
    menu = Element("div", {"class":"sidemenu"})
    # build HTML pages and parse them back
    for section, text_files in SITE_STRUCTURE:
        for filename in text_files:
            path = os.path.join(doc_dir, filename)
            basename = os.path.splitext(filename)[0]
            if basename == 'main':
                basename = 'index'
            outname = basename + '.html'
            outpath = os.path.join(dirname, outname)

            rest2html(script, path, outpath, stylesheet_url)

            tree = parse(outpath)
            trees[filename] = (tree, basename, outpath)

            build_menu(tree, basename, section, menu)

    # integrate menu
    for tree, basename, outpath in trees.itervalues():
        new_tree = merge_menu(tree, menu, basename)
        new_tree.write(outpath)

    # also convert INSTALL.txt and CHANGES.txt
    rest2html(script,
              os.path.join(lxml_path, 'INSTALL.txt'),
              os.path.join(dirname, 'installation.html'),
              stylesheet_url)
    rest2html(script,
              os.path.join(lxml_path, 'CHANGES.txt'),
              os.path.join(dirname, 'changes-%s.html' % release),
              stylesheet_url)

if __name__ == '__main__':
    publish(sys.argv[1], sys.argv[2], sys.argv[3])
