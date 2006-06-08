import os, sys

def publish(dirname, lxml_path, release):
    if not os.path.exists(dirname):
        os.mkdir(dirname)

    doc_dir = os.path.join(lxml_path, 'doc')
    stylesheet_url = 'style.css'

    for name in ['main.txt', 'intro.txt', 'api.txt', 'compatibility.txt',
                 'extensions.txt', 'namespace_extensions.txt', 'sax.txt',
                 'build.txt', 'FAQ.txt', 'performance.txt', 'resolvers.txt']:
        path = os.path.join(doc_dir, name)
        outname = os.path.splitext(name)[0] + '.html'
        outpath = os.path.join(dirname, outname)

        rest2html(path, outpath, stylesheet_url)
    # also convert INSTALL.txt and CHANGES.txt
    rest2html(os.path.join(lxml_path, 'INSTALL.txt'),
              os.path.join(dirname, 'installation.html'),
              stylesheet_url)
    rest2html(os.path.join(lxml_path, 'CHANGES.txt'),
              os.path.join(dirname, 'changes-%s.html' % release),
              stylesheet_url)
    os.rename(os.path.join(dirname, 'main.html'),
              os.path.join(dirname, 'index.html'))

def rest2html(source_path, dest_path, stylesheet_url):

    command = ('rest2html --stylesheet=%s --link-stylesheet %s > %s' %
               (stylesheet_url, source_path, dest_path))
    os.system(command)

if __name__ == '__main__':
    publish(sys.argv[1], sys.argv[2], sys.argv[3])
