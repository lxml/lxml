from docstructure import SITE_STRUCTURE, HREF_MAP, BASENAME_MAP
from lxml.etree import (parse, fromstring, ElementTree,
                        Element, SubElement, XPath, XML)
import os
import re
import sys
import copy
import shutil
import subprocess

try:
    from io import open as open_file
except ImportError:
    from codecs import open as open_file

RST2HTML_OPTIONS = " ".join([
    '--no-toc-backlinks',
    '--strip-comments',
    '--language en',
    '--date',
    ])

XHTML_NS = 'http://www.w3.org/1999/xhtml'
htmlnsmap = {"h" : XHTML_NS}

find_title = XPath("/h:html/h:head/h:title/text()", namespaces=htmlnsmap)
find_title_tag = XPath("/h:html/h:head/h:title", namespaces=htmlnsmap)
find_headings = XPath("//h:h1[not(@class)]//text()", namespaces=htmlnsmap)
find_heading_tag = XPath("//h:h1[@class = 'title'][1]", namespaces=htmlnsmap)
find_menu = XPath("//h:ul[@id=$name]", namespaces=htmlnsmap)
find_page_end = XPath("/h:html/h:body/h:div[last()]", namespaces=htmlnsmap)

find_words = re.compile('(\w+)').findall
replace_invalid = re.compile(r'[-_/.\s\\]').sub

def make_menu_section_head(section, menuroot):
    section_id = section + '-section'
    section_head = menuroot.xpath("//ul[@id=$section]/li", section=section_id)
    if not section_head:
        ul = SubElement(menuroot, "ul", id=section_id)
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
    page_id = replace_invalid(' ', os.path.splitext(url)[0]) + '-menu'
    ul = SubElement(section_head, "ul", {"class":"menu foreign", "id":page_id})

    title = SubElement(ul, "li", {"class":"menu title"})
    a = SubElement(title, "a", href=url)
    a.text = page_title

    if headings:
        subul = SubElement(title, "ul", {"class":"submenu"})
        for heading in headings:
            li = SubElement(subul, "li", {"class":"menu item"})
            try:
                ref = heading.getparent().getparent().get('id')
            except AttributeError:
                ref = None
            if ref is None:
                ref = '-'.join(find_words(replace_invalid(' ', heading.lower())))
            a  = SubElement(li, "a", href=url+'#'+ref)
            a.text = heading

def merge_menu(tree, menu, name):
    menu_root = copy.deepcopy(menu)
    tree.getroot()[1][0].insert(0, menu_root) # html->body->div[class=document]
    for el in menu_root.iter():
        tag = el.tag
        if tag[0] != '{':
            el.tag = "{http://www.w3.org/1999/xhtml}" + tag
    current_menu = find_menu(
        menu_root, name=replace_invalid(' ', name) + '-menu')
    if not current_menu:
        current_menu = find_menu(
            menu_root, name=replace_invalid('-', name) + '-menu')
    if current_menu:
        for submenu in current_menu:
            submenu.set("class", submenu.get("class", "").
                        replace("foreign", "current"))
    return tree

def inject_flatter_button(tree):
    head = tree.xpath('h:head[1]', namespaces=htmlnsmap)[0]
    script = SubElement(head, '{%s}script' % XHTML_NS, type='text/javascript')
    script.text = """
    (function() {
        var s = document.createElement('script');
        var t = document.getElementsByTagName('script')[0];
        s.type = 'text/javascript';
        s.async = true;
        s.src = 'http://api.flattr.com/js/0.6/load.js?mode=auto';
        t.parentNode.insertBefore(s, t);
    })();
"""
    script.tail = '\n'
    intro_div = tree.xpath('h:body//h:div[@id = "introduction"][1]', namespaces=htmlnsmap)[0]
    intro_div.insert(-1, XML(
        '<p style="text-align: center;">Like working with lxml? '
        'Happy about the time that it just saved you? <br />'
        'Show your appreciation with <a href="http://flattr.com/thing/268156/lxml-The-Python-XML-Toolkit">Flattr</a>.<br />'
        '<a class="FlattrButton" style="display:none;" rev="flattr;button:compact;" href="http://lxml.de/"></a>'
        '</p>'
        ))

def inject_donate_buttons(lxml_path, rst2html_script, tree):
    command = ([sys.executable, rst2html_script]
               + RST2HTML_OPTIONS.split() + [os.path.join(lxml_path, 'README.rst')])
    rst2html = subprocess.Popen(command, stdout=subprocess.PIPE)
    stdout, _ = rst2html.communicate()
    readme = fromstring(stdout)

    intro_div = tree.xpath('h:body//h:div[@id = "introduction"][1]',
                           namespaces=htmlnsmap)[0]
    support_div = readme.xpath('h:body//h:div[@id = "support-the-project"][1]',
                               namespaces=htmlnsmap)[0]
    intro_div.append(support_div)

    legal = readme.xpath('h:body//h:div[@id = "legal-notice-for-donations"][1]',
                         namespaces=htmlnsmap)[0]
    last_div = tree.xpath('h:body//h:div//h:div', namespaces=htmlnsmap)[-1]
    last_div.addnext(legal)

def rest2html(script, source_path, dest_path, stylesheet_url):
    command = ('%s %s %s --stylesheet=%s --link-stylesheet %s > %s' %
               (sys.executable, script, RST2HTML_OPTIONS,
                stylesheet_url, source_path, dest_path))
    subprocess.call(command, shell=True)

def convert_changelog(lxml_path, changelog_file_path, rst2html_script, stylesheet_url):
    f = open_file(os.path.join(lxml_path, 'CHANGES.txt'), 'r', encoding='utf-8')
    try:
        content = f.read()
    finally:
        f.close()

    links = dict(LP='`%s <https://bugs.launchpad.net/lxml/+bug/%s>`_',
                 GH='`%s <https://github.com/lxml/lxml/issues/%s>`_')
    replace_tracker_links = re.compile('((LP|GH)#([0-9]+))').sub
    def insert_link(match):
        text, ref_type, ref_id = match.groups()
        return links[ref_type] % (text, ref_id)
    content = replace_tracker_links(insert_link, content)

    command = [sys.executable, rst2html_script] + RST2HTML_OPTIONS.split() + [
        '--link-stylesheet', '--stylesheet', stylesheet_url ]
    out_file = open(changelog_file_path, 'wb')
    try:
        rst2html = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=out_file)
        rst2html.communicate(content.encode('utf8'))
    finally:
        out_file.close()

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

                if filename == 'main.txt':
                    # inject donation buttons
                    #inject_flatter_button(tree)
                    inject_donate_buttons(lxml_path, script, tree)

                trees[filename] = (tree, basename, outpath)
                build_menu(tree, basename, section_head)

    # also convert CHANGES.txt
    convert_changelog(lxml_path, os.path.join(dirname, 'changes-%s.html' % release),
                      script, stylesheet_url)

    # generate sitemap from menu
    sitemap = XML('''\
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
      <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <title>Sitemap of lxml.de - Processing XML and HTML with Python</title>
        <meta content="lxml - the most feature-rich and easy-to-use library for processing XML and HTML in the Python language"
              name="description" />
        <meta content="Python XML, XML, XML processing, HTML, lxml, simple XML, ElementTree, etree, lxml.etree, objectify, XML parsing, XML validation, XPath, XSLT"
              name="keywords" />
      </head>
      <body>
        <h1>Sitemap of lxml.de - Processing XML and HTML with Python</h1>
      </body>
    </html>
    '''.replace('    ', ' '))
    sitemap_menu = copy.deepcopy(menu)
    SubElement(SubElement(sitemap_menu[-1], 'li'), 'a', href='http://lxml.de/files/').text = 'Download files'
    sitemap[-1].append(sitemap_menu) # append to body
    ElementTree(sitemap).write(os.path.join(dirname, 'sitemap.html'))

    # integrate sitemap into the menu
    SubElement(SubElement(menu[-1], 'li'), 'a', href='http://lxml.de/sitemap.html').text = 'Sitemap'

    # integrate menu into web pages
    for tree, basename, outpath in trees.itervalues():
        new_tree = merge_menu(tree, menu, basename)
        title = find_title_tag(new_tree)
        if title and title[0].text == 'lxml':
            title[0].text = "lxml - Processing XML and HTML with Python"
            heading = find_heading_tag(new_tree)
            if heading:
                heading[0].text = "lxml - XML and HTML with Python"
        new_tree.write(outpath)

if __name__ == '__main__':
    publish(sys.argv[1], sys.argv[2], sys.argv[3])
