import time
import re
import vlibxml2

data = open('data/chromewaves.xml','rb').read()

start = time.time()
titleRE = re.compile("<title>([^<]*)")
for i in range(2000):
    titleRE.findall(data)
finish = time.time()
print "%0.2f seconds for regex matching" % (finish-start)

doc = vlibxml2.parseDoc(data)
start = time.time()
for i in range(2000):
    doc.xpathEval('//title')
finish = time.time()
print "%0.2f seconds for xpath matching" % (finish-start)
