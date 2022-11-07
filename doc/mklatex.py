# The script builds the LaTeX documentation.
# Testing:
#    python mklatex.py latex .. 1.0

from docstructure import SITE_STRUCTURE, BASENAME_MAP
import os, shutil, re, sys, datetime

TARGET_FILE = "lxmldoc.tex"

RST2LATEX_OPTIONS = " ".join([
#    "--no-toc-backlinks",
    "--strip-comments",
    "--language en",
#    "--date",
#    "--use-latex-footnotes",
    "--use-latex-citations",
    "--use-latex-toc",
    "--font-encoding=T1",
    "--output-encoding=utf-8",
    "--input-encoding=utf-8",
    "--graphicx-option=pdftex",
    ])

htmlnsmap = {"h" : "http://www.w3.org/1999/xhtml"}

replace_invalid = re.compile(r'[-_/.\s\\]').sub
replace_content = re.compile(r"\{[^\}]*\}").sub

replace_epydoc_macros = re.compile(r'(,\s*amssymb|dvips\s*,\s*)').sub
replace_rst_macros = re.compile(r'(\\usepackage\{color}|\\usepackage\[[^]]*]\{hyperref})').sub

BASENAME_MAP = BASENAME_MAP.copy()
BASENAME_MAP.update({'api' : 'lxmlapi'})

# LaTeX snippets

DOCUMENT_CLASS = r"""
\documentclass[10pt,english]{report}
\usepackage[a4paper]{geometry}
\usepackage{tabularx}
\usepackage{ifthen}
\usepackage[pdftex]{graphicx}
\parindent0pt
\parskip1ex

%%% Fallback definitions for Docutils-specific commands

% providelength (provide a length variable and set default, if it is new)
\providecommand*{\DUprovidelength}[2]{
  \ifthenelse{\isundefined{#1}}{\newlength{#1}\setlength{#1}{#2}}{}
}

% docinfo (width of docinfo table)
\DUprovidelength{\DUdocinfowidth}{0.9\textwidth}

% titlereference role
\providecommand*{\DUroletitlereference}[1]{\textsl{#1}}

"""

PYGMENTS_IMPORT = r"""
\usepackage{fancyvrb}
\input{_part_pygments.tex}
"""

EPYDOC_IMPORT = r"""
\input{_part_epydoc.tex}
"""

def write_chapter(master, title, filename):
    filename = os.path.join(os.path.dirname(filename),
                            "_part_%s" % os.path.basename(filename))
    master.write(r"""
\chapter{{{}}}
\label{{{}}}
\input{{{}}}
""".format(title, filename, filename))


# the program ----

def rest2latex(script, source_path, dest_path):
    command = ('%s %s %s  %s > %s' %
               (sys.executable, script, RST2LATEX_OPTIONS,
                source_path, dest_path))
    os.system(command)

def build_pygments_macros(filename):
    from pygments.formatters import LatexFormatter
    text = LatexFormatter().get_style_defs()
    with open(filename, "w") as f:
        f.write(text)
        f.write('\n')

def copy_epydoc_macros(src, dest, existing_header_lines):
    doc = open(src)
    out = open(dest, "w")
    for line in doc:
        if line.startswith('%% generator') \
                or line.startswith('% generated by ') \
                or '\\begin{document}' in line \
                or '\\makeindex' in line:
            break
        if line.startswith('%') or \
                r'\documentclass' in line or \
                r'\makeindex' in line or \
                r'{inputenc}' in line:
            continue
        if line.startswith(r'\usepackage'):
            if line in existing_header_lines:
                continue
            if '{hyperref}' in line:
                line = line.replace('black', 'blue')
        out.write( replace_epydoc_macros('', line) )
    out.close()
    doc.close()

def noop(input):
    return input

counter_no = 0

def tex_postprocess(src_path, dest_path, want_header=False, process_line=noop):
    """
    Postprocessing of the LaTeX file generated from ReST.

    Reads file src_path and saves to dest_path only the true content
    (without the document header and final) - so it is suitable
    to be used as part of the longer document.

    Returns the title of document

    If want_header is set, returns also the document header (as
    the list of lines).
    """
    header = []
    add_header_line = header.append
    global counter_no
    counter_no = counter_no + 1
    counter_text = "listcnt%d" % counter_no

    search_title = re.compile(r'\\title{([^{}]*(?:{[^}]*})*)}').search
    skipping = re.compile(r'(\\end{document}|\\tableofcontents|^%)').search

    with open(src_path) as src:
        src_text = src.read()

    dest = open(dest_path, "w")

    title = search_title(src_text)
    if title:
        # remove any commands from the title
        title = re.sub(r'\\\w+({[^}]*})?', '', title.group(1))

    iter_lines = iter(src_text.splitlines())
    for l in iter_lines:
        l = process_line(l)
        if not l:
            continue
        if want_header:
            add_header_line(replace_rst_macros('', l))
        if l.startswith("\\maketitle"):
            break

    for l in iter_lines:
        l = process_line(l)
        if skipping(l):
            # To-Do minitoc instead of tableofcontents
            continue
        elif r"\hypertarget{old-versions}" in l:
            break
        elif "listcnt0" in l:
            l = l.replace("listcnt0", counter_text)
        dest.write(l + '\n')

    dest.close()

    if not title:
        raise Exception("Bueee, no title in %s" % src_path)
    return title, header

def publish(dirname, lxml_path, release):
    if not os.path.exists(dirname):
        os.mkdir(dirname)

    book_title = "lxml %s" % release

    doc_dir = os.path.join(lxml_path, 'doc')
    script = os.path.join(doc_dir, 'rest2latex.py')
    pubkey = os.path.join(doc_dir, 'pubkey.asc')

    shutil.copy(pubkey, dirname)

    # build pygments macros
    build_pygments_macros(os.path.join(dirname, '_part_pygments.tex'))

    # Used in postprocessing of generated LaTeX files
    header = []
    titles = {}

    replace_interdoc_hyperrefs = re.compile(
        r'\\href\{([^/}]+)[.]([^./}]+)\}').sub
    replace_docinternal_hyperrefs = re.compile(
        r'\\href\{\\#([^}]+)\}').sub
    replace_image_paths = re.compile(
        r'^(\\includegraphics{)').sub
    def build_hyperref(match):
        basename, extension = match.groups()
        outname = BASENAME_MAP.get(basename, basename)
        if '#' in extension:
            anchor = extension.split('#')[-1]
            return r"\hyperref[%s]" % anchor
        elif extension != 'html':
            return r'\href{{https://lxml.de/{}.{}}}'.format(
                outname, extension)
        else:
            return r"\hyperref[_part_%s.tex]" % outname
    def fix_relative_hyperrefs(line):
        line = replace_image_paths(r'\1../html/', line)
        if r'\href' not in line:
            return line
        line = replace_interdoc_hyperrefs(build_hyperref, line)
        return replace_docinternal_hyperrefs(r'\\hyperref[\1]', line)

    # Building pages
    for section, text_files in SITE_STRUCTURE:
        for filename in text_files:
            if filename.startswith('@'):
                continue
                #page_title = filename[1:]
                #url = href_map[page_title]
                #build_menu_entry(page_title, url, section_head)

            basename = os.path.splitext(os.path.basename(filename))[0]
            basename = BASENAME_MAP.get(basename, basename)
            outname = basename + '.tex'
            outpath = os.path.join(dirname, outname)
            path = os.path.join(doc_dir, filename)

            print("Creating %s" % outname)
            rest2latex(script, path, outpath)

            final_name = os.path.join(dirname, os.path.dirname(outname),
                                      "_part_%s" % os.path.basename(outname))

            title, hd = tex_postprocess(outpath, final_name,
                                        want_header = not header,
                                        process_line=fix_relative_hyperrefs)
            if not header:
                header = hd
            titles[outname] = title

    # integrate generated API docs

    print("Integrating API docs")
    apidocsname = 'api.tex'
    apipath = os.path.join(dirname, apidocsname)
    tex_postprocess(apipath, os.path.join(dirname, "_part_%s" % apidocsname),
                    process_line=fix_relative_hyperrefs)
    copy_epydoc_macros(apipath, os.path.join(dirname, '_part_epydoc.tex'),
                       set(header))

    # convert CHANGES.txt

    print("Integrating ChangeLog")
    find_version_title = re.compile(
        r'(.*\\section\{)([0-9][^\} ]*)\s+\(([^)]+)\)(\}.*)').search
    def fix_changelog(line):
        m = find_version_title(line)
        if m:
            line = "%sChanges in version %s, released %s%s" % m.groups()
        else:
            line = line.replace(r'\subsection{', r'\subsection*{')
        return line

    chgname = 'changes-%s.tex' % release
    chgpath = os.path.join(dirname, chgname)
    rest2latex(script,
               os.path.join(lxml_path, 'CHANGES.txt'),
               chgpath)
    tex_postprocess(chgpath, os.path.join(dirname, "_part_%s" % chgname),
                    process_line=fix_changelog)

    # Writing a master file
    print("Building %s\n" % TARGET_FILE)
    master = open( os.path.join(dirname, TARGET_FILE), "w")
    for hln in header:
        if hln.startswith(r"\documentclass"):
            #hln = hln.replace('article', 'book')
            hln = DOCUMENT_CLASS + EPYDOC_IMPORT
        elif hln.startswith(r"\begin{document}"):
            # pygments and epydoc support
            master.write(PYGMENTS_IMPORT)
        elif hln.startswith(r"\title{"):
            hln = replace_content(
                r'{%s\\\\\\vspace{1cm}\\includegraphics[width=2.5cm]{../html/tagpython-big.png}}' % book_title, hln)
        elif hln.startswith(r"\date{"):
            hln = replace_content(
                r'{%s}' % datetime.date.today().isoformat(), hln)
        elif hln.startswith("pdftitle"):
            hln = replace_content(
                r'{%s}' % book_title, hln)
        master.write(hln + '\n')

    master.write("\\setcounter{page}{2}\n")
    master.write("\\tableofcontents\n")

    for section, text_files in SITE_STRUCTURE:
        master.write("\n\n\\part{%s}\n" % section)
        for filename in text_files:
            if filename.startswith('@'):
                continue
                #print "Not yet implemented: %s" % filename[1:]
                #page_title = filename[1:]
                #url = href_map[page_title]
                #build_menu_entry(page_title, url, section_head)
            else:
                basename = os.path.splitext(os.path.basename(filename))[0]
                basename = BASENAME_MAP.get(basename, basename)
                outname = basename + '.tex'
            write_chapter(master, titles[outname], outname)

    master.write("\\appendix\n")
    master.write("\\begin{appendix}\n")

    write_chapter(master, "Changes", chgname)
    write_chapter(master, "Generated API documentation", apidocsname)

    master.write("\\end{appendix}\n")
    master.write("\\end{document}\n")
                

if __name__ == '__main__':
    publish(sys.argv[1], sys.argv[2], sys.argv[3])
