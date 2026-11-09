"""Accept presentation variants while rejecting semantic structure loss."""
import tempfile
from pathlib import Path
import unittest
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Border, Side
from benchmark.test_evaluator_contract import evaluator


class EnvironmentLayoutTests(unittest.TestCase):
    def setUp(self):
        self.case, self.check = evaluator('environment', 'case_1_realhitbench_environment21')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'output.xlsx'

    def evaluate(self, mutate):
        w = load_workbook(self.case / 'gold_output.xlsx')
        mutate(w.active)
        w.save(self.path)
        return self.check(self.path)['hard_task_success']

    def test_optional_total_header_and_decorative_merges(self):
        def variant(w):
            for area in ('G4:G5', 'A1:G1', 'A32:G32'):
                w.unmerge_cells(area)
            w.merge_cells('A1:F1')
            w.merge_cells('A32:H32')
        self.assertEqual(self.evaluate(variant), 1)
        self.assertEqual(self.evaluate(lambda w: [w.unmerge_cells(a) for a in ('G4:G5','A1:G1','A32:G32')]), 1)
        def bottom_label(w):
            w.unmerge_cells('G4:G5')
            w['G4']=None
            w['G5']='Total'
        self.assertEqual(self.evaluate(bottom_label), 1)

    def test_fonts_colors_borders_and_blank_styled_extent_are_ignored(self):
        def variant(w):
            for row in w:
                for cell in row:
                    cell.font = Font(name='Arial', size=18, color='FF0000')
                    cell.fill = PatternFill('solid', fgColor='FFFF00')
                    cell.border = Border(bottom=Side(style='thick', color='0000FF'))
            w['AA50'].font = Font(size=24)
        self.assertEqual(self.evaluate(variant), 1)

    def test_wrong_parent_group_and_total_merge_still_fail(self):
        def wrong_group(w):
            w.unmerge_cells('G4:G5')
            w.unmerge_cells('C4:F4')
            w.merge_cells('C4:G4')
        self.assertEqual(self.evaluate(wrong_group), 0)
        def crosses_data(w):
            w.unmerge_cells('G4:G5')
            w.merge_cells('G4:G6')
        self.assertEqual(self.evaluate(crosses_data), 0)

    def test_lost_original_group_merge_still_fails(self):
        self.assertEqual(self.evaluate(lambda w: w.unmerge_cells('C4:F4')), 0)

    def test_wrong_value_missing_statistic_and_bad_row_order_still_fail(self):
        self.assertEqual(self.evaluate(lambda w: w.__setitem__('G7', 999)), 0)
        self.assertEqual(self.evaluate(lambda w: w.__setitem__('B29', None)), 0)
        self.assertEqual(self.evaluate(lambda w: w.__setitem__('A28', '2010 Totals')), 0)
        self.assertEqual(self.evaluate(lambda w: w.__setitem__('G4', 'Wrong label')), 0)

    def test_guided_has_identical_business_contract(self):
        discovery = (self.case / 'instruction.txt').read_text(encoding='utf-8').strip()
        guided = (self.case / 'instruction_guided.txt').read_text(encoding='utf-8').strip()
        self.assertTrue(guided.endswith(discovery))
        self.assertNotIn('vertically merged as a header', guided)


if __name__ == '__main__':
    unittest.main()
