'''
generate Pyrex wrappers for the XML API description
'''

import vlibxml2
import sys

class codegenerator(object):
    '''
    just a cheesy little class that can be used to properly format Python code
    '''
    def __init__(self):
        self.level = 0
        self.code = '    '
        self.block = []

    def push(self, code=None):
        self.level += 1
        if code is not None:
            self.write(code)

    def pop(self, code=None):
        assert self.level > 0
        self.level -= 1
        if code is not None:
            self.write(code)

    def write(self, code=''):
        self.block.append((self.level, code))

    def dump(self):
        output = ''
        for level, line in self.block:
            output += "%s\n" % (self.code * level + line)
        return output


def convertTypedefs(doc):
    '''
    convert typedef definitions
    '''
    typedefs = doc.xpathEval('''.//typedef''')

    forwardDecls = []
    files = {}
    gen = codegenerator()
    for tdef  in typedefs:
        tdefDict = {  'name': tdef.prop('name'),
                        'file': tdef.prop('file'),
                        'type': tdef.prop('type'), }

        forwardDecls.append(tdefDict['name'])
        if not files.has_key(tdefDict['file']):
            files[tdefDict['file']] = []

        if tdefDict['type'].endswith('*'):
            codeLine = "ctypedef %(type)s%(name)s" % tdefDict
        else:
            codeLine = "ctypedef %(type)s %(name)s" % tdefDict
        files[tdefDict['file']].append(codeLine)

    fDecls = '''\n# Forward declarations for typedefs\n\n'''
    for decl in forwardDecls:
        fDecls += "ctypedef %s\n" % decl
    fDecls += '''\n# End Forward declarations for typedefs\n\n'''
    fDecls += '''\n\n# TypeDef Declarations \n\n'''
    for filename in files.keys():
        gen.write('''\n\ncdef extern from "libxml/%s.h":\n''' % filename)
        gen.push()
        for code in files[filename]:
            gen.write(code)
        gen.pop()

    return fDecls, gen.dump()

def convertStructs(doc):
    '''
    just convert the file's struct for now
    '''
    structs = doc.xpathEval('''.//struct''')

    files = {}
    forwardDecls = []
    for s in structs:
        structDict = {'name': s.prop('name'),
            'file': s.prop('file'),
            'type': s.prop('type'),
            'structName': s.prop('type').replace('struct ', ''),
            'typeName': s.prop('type').replace('struct ', '')}

        forwardDecls.append(structDict['structName'])
        if not files.has_key(structDict['file']):
            files[structDict['file']] = []
        gen = codegenerator()
        gen.write("cdef %(type)s:" % structDict)
        gen.push()
        fields = s.xpathEval('.//field')
        if len(fields) == 0:
            gen.write('pass')
        else:
            for field in fields:
                fieldDict = {   'type': field.prop('type'),
                    'name': field.prop('name'),
                    'comment': field.prop('info') ,
                    }

                # get rid of const in the type names
                fieldDict['type'] = fieldDict['type'].replace('const ', '').replace('struct ', '')

                if fieldDict['type'].endswith('*'):
                    structLine = "%(type)s%(name)s" % fieldDict
                else:
                    structLine = "%(type)s %(name)s" % fieldDict
                structLine = structLine + ' ' * (60 - len(structLine)) + '# %(comment)s' % fieldDict
                gen.write(structLine)
        gen.pop()
        gen.write("ctypedef %(typeName)s %(name)s" % structDict )
        files[structDict['file']].append(gen.dump())

    returnvalue = ''


    gen = codegenerator()
    gen.write('## Struct Declarations')
    for filename in files.keys():
        gen.write('''cdef extern from "libxml/%s.h":\n''' % filename)
        gen.push()
        for value in files[filename]:
            for line in value.split('\n'):
                gen.write(line)
        gen.pop()

    # generate the forward declarations
    fDecls = '\n### Forward declarations of structs\n'
    for decl in forwardDecls:
        fDecls += '''cdef struct %s\n''' % decl
    fDecls += '\n### End Forward declarations of structs\n'

    return fDecls, gen.dump()

def convertEnums(doc):
    enums = doc.xpathEval('''.//enum''')

    files = {}
    for s in enums:
        valueDict = {}
        for attr in 'name file value type'.split():
            valueDict[attr] = s.prop(attr)

        if not files.has_key(valueDict['file']):
            files[valueDict['file']] = {}

        if not files[valueDict['file']].has_key(valueDict['type']):
            files[valueDict['file']][valueDict['type']] = []

        files[valueDict['file']][valueDict['type']].append((valueDict['name'], valueDict['value']))

    gen = codegenerator()
    for filename in files.keys():
        gen.write('''cdef extern from "libxml/%s.h":''' % filename )
        gen.push()
        for enumKey in files[filename].keys():
            gen.write("cdef enum %s:" % enumKey)
            gen.push()
            for name, value in files[filename][enumKey]:
                gen.write(name)
            gen.pop()
            gen.write()
        gen.pop()
        gen.write()

    return gen.dump()

def buildStubs():
    '''
    generate the necessary Pyrex stubs to get Python and libxml2 playing nice
    with each other.
    '''
    doc = vlibxml2.parseDoc(open('data/libxml2-api.xml','rb').read())
    enumCode = convertEnums(doc)
    structFwds, structCode = convertStructs(doc)
    typedefFwds, typeDefCode = convertTypedefs(doc)

    print "###\n### enum code\n### "
    print enumCode
    print "###\n### forward decls for typedefs code\n### "
    print typedefFwds
    print "###\n### forward decls for structs code\n### "
    print structFwds
    print "###\n### structs code\n### "
    print structCode
    print "###\n### typdef code\n### "
    print typeDefCode

buildStubs()


