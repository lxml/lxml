import sys
import unittest

import lxml.html


class SelectTest(unittest.TestCase):
    @staticmethod
    def _evaluate_select(multiple, options):
        options = ''.join('<option' + (' selected="selected"' if selected else '') + '>' + option + '</option>'
                          for option, selected in options)
        string = '<title>test</title><form><select%s>%s</select></form>' % \
                 (' multiple="multiple"' if multiple else '', options)
        return lxml.html.fromstring(string).find('.//select').value

    def test_single_select_value_no_options(self):
        self.assertEqual(self._evaluate_select(False, []), None)

    def test_single_select_value_no_selected_option(self):
        # If no option is selected, the HTML5 specification requires the first option to get selected.
        self.assertEqual(self._evaluate_select(False, [('a', False), ('b', False)]), 'a')

    def test_single_select_value_multiple_selected_options(self):
        # If multiple options are selected, the proposed HTML 5.1 specification
        # requires all but the last selected options to get deselected.
        self.assertEqual(self._evaluate_select(False, [('a', True), ('b', True)]), 'b')

    def test_multiple_select_value_no_selected_option(self):
        self.assertEqual(self._evaluate_select(True, [('a', False), ('b', False)]), set())

    def test_multiple_select_value_multiple_selected_options(self):
        self.assertEqual(self._evaluate_select(True, [('a', True), ('b', True)]), set(['a', 'b']))


def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromModule(sys.modules[__name__])
