from lxml.etree import (parse, fromstring, ElementTree,
                        Element, SubElement, XPath)
import os, shutil, re, sys, copy, time

SITE_STRUCTURE = [
    ('lxml', ('main.txt', 'intro.txt', '../INSTALL.txt', 'lxml2.txt',
              'performance.txt', 'compatibility.txt', 'FAQ.txt')),
    ('Developing with lxml', ('tutorial.txt', '@API reference',
                              'api.txt', 'parsing.txt',
                              'validation.txt', 'xpathxslt.txt',
                              'objectify.txt', 'lxmlhtml.txt',
                              'cssselect.txt', 'elementsoup.txt')),
    ('Extending lxml', ('resolvers.txt', 'extensions.txt',
                        'element_classes.txt', 'sax.txt', 'capi.txt')),
    ('Developing lxml', ('build.txt', 'lxml-source-howto.txt',
                         '@Release Changelog')),
    ]

RST2HTML_OPTIONS = " ".join([
    "--no-toc-backlinks",
    "--strip-comments",
    "--language en",
    "--date",
    ])

HREF_MAP = {
    "API reference" : "api/index.html"
}

BASENAME_MAP = {
    'main' : 'index',
    'INSTALL' : 'installation',
}

htmlnsmap = {"h" : "http://www.w3.org/1999/xhtml"}

find_title = XPath("/h:html/h:head/h:title/text()", namespaces=htmlnsmap)
find_headings = XPath("//h:h1[not(@class)]/h:a/text()", namespaces=htmlnsmap)
find_menu = XPath("//h:ul[@id=$name]", namespaces=htmlnsmap)
find_page_end = XPath("/h:html/h:body/h:div[last()]", namespaces=htmlnsmap)

replace_invalid = re.compile(r'[-_/.\s\\]').sub

def make_menu_section_head(section, menuroot):
    section_head = menuroot.xpath("//ul[@id=$section]/li", section=section)
    if not section_head:
        ul = SubElement(menuroot, "ul", id=section)
        section_head = SubElement(ul, "li")
        title = SubElement(section_head, "span", {"class":"section title"})
        title.text = section
    else:
        section_head = section_head[0]
    return section_head

def build_menu(tree, basename, section_head):
    page_title = find_title(tree)
    if page_title:
        page_title = page_title[0]
    else:
        page_title = replace_invalid('', basename.capitalize())
    build_menu_entry(page_title, basename+".html", section_head,
                     headings=find_headings(tree))

def build_menu_entry(page_title, url, section_head, headings=None):
    page_id = replace_invalid(' ', os.path.splitext(url)[0])
    ul = SubElement(section_head, "ul", {"class":"menu foreign", "id":page_id})

    title = SubElement(ul, "li", {"class":"menu title"})
    a = SubElement(title, "a", href=url)
    a.text = page_title

    if headings:
        subul = SubElement(title, "ul", {"class":"submenu"})
        for heading in headings:
            li = SubElement(subul, "li", {"class":"menu item"})
            ref = replace_invalid('-', heading.lower())
            a  = SubElement(li, "a", href=url+'#'+ref)
            a.text = heading

def merge_menu(tree, menu, name):
    menu_root = copy.deepcopy(menu)
    tree.getroot()[1][0].insert(0, menu_root) # html->body->div[class=document]
    for el in menu_root.getiterator():
        tag = el.tag
        if tag[0] != '{':
            el.tag = "{http://www.w3.org/1999/xhtml}" + tag
    current_menu = find_menu(menu_root, name=replace_invalid(' ', name))
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

    href_map = HREF_MAP.copy()
    changelog_basename = 'changes-%s' % release
    href_map['Release Changelog'] = changelog_basename + '.html'

    trees = {}
    menu = Element("div", {"class":"sidemenu"})
    # build HTML pages and parse them back
    for section, text_files in SITE_STRUCTURE:
        section_head = make_menu_section_head(section, menu)
        for filename in text_files:
            if filename.startswith('@'):
                # special menu entry
                page_title = filename[1:]
                url = href_map[page_title]
                build_menu_entry(page_title, url, section_head)
            else:
                path = os.path.join(doc_dir, filename)
                basename = os.path.splitext(os.path.basename(filename))[0]
                basename = BASENAME_MAP.get(basename, basename)
                outname = basename + '.html'
                outpath = os.path.join(dirname, outname)

                rest2html(script, path, outpath, stylesheet_url)

                tree = parse(outpath)
                trees[filename] = (tree, basename, outpath)

                build_menu(tree, basename, section_head)

    # also convert CHANGES.txt
    rest2html(script,
              os.path.join(lxml_path, 'CHANGES.txt'),
              os.path.join(dirname, 'changes-%s.html' % release),
              '')

    # integrate menu
    for tree, basename, outpath in trees.itervalues():
        new_tree = merge_menu(tree, menu, basename)
        new_tree.write(outpath)

if __name__ == '__main__':
    publish(sys.argv[1], sys.argv[2], sys.argv[3])
