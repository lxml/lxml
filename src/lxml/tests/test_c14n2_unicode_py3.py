import unittest


class LXML_C14N2_RegressionTest(unittest.TestCase):
    def test_python3_problem_bytesio_iterparse(self):
        from lxml import etree
        from io import BytesIO
        content = BytesIO('''<?xml version="1.0" encoding="utf-8"?> <some_ns_id:some_head_elem xmlns:some_ns_id="http://www.example.com" xmlns:xhtml="http://www.w3.org/1999/xhtml"><xhtml:div></xhtml:div></some_ns_id:some_head_elem>'''.encode('utf-8'))
        def handle_div_end(event, element):
            if event == 'end' and element.tag.lower().startswith("{http://www.w3.org/1999/xhtml}div"):
                # for ns_id, ns_uri in element.nsmap.items():
                #     print(type(ns_id), type(ns_uri), ns_id, '=', ns_uri)
                etree.tostring(element, method="c14n2")
        for event, element in etree.iterparse(
            source=content,
            events=('start', 'end')
        ):
            handle_div_end(event, element)

    # def test_python3_problem_bytesio_iterparse_global_ns_registration(self):
    #     from lxml import etree
    #     from io import BytesIO
    #     etree.register_namespace('xhtml', 'http://www.w3.org/1999/xhtml')
    #     content = BytesIO('''<?xml version="1.0" encoding="utf-8"?> <some_ns_id:some_head_elem xmlns:some_ns_id="http://www.example.com" xmlns:xhtml="http://www.w3.org/1999/xhtml"><xhtml:div></xhtml:div></some_ns_id:some_head_elem>'''.encode('utf-8'))
    #     def handle_div_end(event, element):
    #         if event == 'end' and element.tag.lower().startswith("{http://www.w3.org/1999/xhtml}div"):
    #             # for ns_id, ns_uri in element.nsmap.items():
    #             #     print(type(ns_id), type(ns_uri), ns_id, '=', ns_uri)
    #             etree.tostring(element, method="c14n2")
    #     for event, element in etree.iterparse(
    #         source=content,
    #         events=('start', 'end')
    #     ):
    #         handle_div_end(event, element)
            
    def test_python3_problem_filebased_iterparse(self):
        from lxml import etree
        with open('test.xml', 'w+b') as f:
            f.write('''<?xml version="1.0" encoding="utf-8"?> <some_ns_id:some_head_elem xmlns:some_ns_id="http://www.example.com" xmlns:xhtml="http://www.w3.org/1999/xhtml"><xhtml:div></xhtml:div></some_ns_id:some_head_elem>'''.encode('utf-8'))
        def handle_div_end(event, element):
            if event == 'end' and element.tag.lower() == "{http://www.w3.org/1999/xhtml}div":
                # for ns_id, ns_uri in element.nsmap.items():
                #     print(type(ns_id), type(ns_uri), ns_id, '=', ns_uri)
                etree.tostring(element, method="c14n2")
        for event, element in etree.iterparse(
            source='test.xml',
            events=('start', 'end')
        ):
            handle_div_end(event, element)

    def test_python3_problem_filebased_parse(self):
        from lxml import etree
        with open('test.xml', 'w+b') as f:
            f.write('''<?xml version="1.0" encoding="utf-8"?> <some_ns_id:some_head_elem xmlns:some_ns_id="http://www.example.com" xmlns:xhtml="http://www.w3.org/1999/xhtml"><xhtml:div></xhtml:div></some_ns_id:some_head_elem>'''.encode('utf-8'))
        def serialize_div_element(element):        
            # for ns_id, ns_uri in element.nsmap.items():
            #     print(type(ns_id), type(ns_uri), ns_id, '=', ns_uri)
            etree.tostring(element, method="c14n2")
        tree = etree.parse(source='test.xml')
        root = tree.getroot()
        div = root.xpath('//xhtml:div', namespaces={'xhtml':'http://www.w3.org/1999/xhtml'})[0]
        serialize_div_element(div)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(LXML_C14N2_RegressionTest)])
    return suite

if __name__ == '__main__':
    print('to test use test.py %s' % __file__)
