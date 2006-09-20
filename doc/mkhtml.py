import os, shutil, sys

def publish(dirname, lxml_path, release):
    if not os.path.exists(dirname):
        os.mkdir(dirname)

    doc_dir = os.path.join(lxml_path, 'doc')
    script = os.path.join(doc_dir, 'rest2html.py')
    pubkey = os.path.join(doc_dir, 'pubkey.asc')
    stylesheet_url = 'style.css'

    shutil.copy(pubkey, dirname)

    for name in ['main.txt', 'intro.txt', 'api.txt', 'compatibility.txt',
                 'extensions.txt', 'element_classes.txt', 'sax.txt',
                 'build.txt', 'FAQ.txt', 'performance.txt', 'resolvers.txt',
                 'capi.txt', 'objectify.txt']:
        path = os.path.join(doc_dir, name)
        outname = os.path.splitext(name)[0] + '.html'
        outpath = os.path.join(dirname, outname)

        rest2html(script, path, outpath, stylesheet_url)
    # also convert INSTALL.txt and CHANGES.txt
    rest2html(script,
              os.path.join(lxml_path, 'INSTALL.txt'),
              os.path.join(dirname, 'installation.html'),
              stylesheet_url)
    rest2html(script,
              os.path.join(lxml_path, 'CHANGES.txt'),
              os.path.join(dirname, 'changes-%s.html' % release),
              stylesheet_url)
    os.rename(os.path.join(dirname, 'main.html'),
              os.path.join(dirname, 'index.html'))

def rest2html(script, source_path, dest_path, stylesheet_url):
    command = ('%s %s --stylesheet=%s --link-stylesheet %s > %s' %
               (sys.executable, script, stylesheet_url, source_path, dest_path))
    os.system(command)

if __name__ == '__main__':
    publish(sys.argv[1], sys.argv[2], sys.argv[3])
