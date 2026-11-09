"""Regression tests for representation equivalence, without relaxing facts."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from openpyxl import Workbook, load_workbook

from benchmark.runner import ROOT, source_revision
from scripts.formula_eval import SpreadsheetFormulaEvaluator


def evaluator(domain, slug):
    case = ROOT / 'data' / domain / slug
    spec = spec_from_file_location('contract_' + domain, case / 'evaluate.py')
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return case, mod.evaluate


class ContractTests(unittest.TestCase):
    def test_year_storage_equivalence_without_accepting_wrong_years_or_values(self):
        case, check = evaluator('business', 'case_1_realhitbench_business13')
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / 'output.xlsx'
            wb = load_workbook(case / 'gold_output.xlsx')
            self.assertEqual(check(case / 'gold_output.xlsx')['hard_task_success'], 1)
            for coordinate in ('B2', 'C2', 'D2', 'E2'):
                wb.active[coordinate] = int(wb.active[coordinate].value)
            wb.save(out)
            self.assertEqual(check(out)['hard_task_success'], 1)
            for invalid in (2016, 2014.5, True):
                wb.active['B2'] = invalid
                wb.save(out)
                self.assertEqual(check(out)['hard_task_success'], 0)
            wb.active['B2'] = 2014
            wb.active['F3'] = 999
            wb.save(out)
            self.assertEqual(check(out)['hard_task_success'], 0)

    def test_singleton_merge_is_identity_but_real_group_is_required(self):
        case, check = evaluator('labor', 'case_1_realhitbench_labor43')
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / 'output.xlsx'
            wb = load_workbook(case / 'gold_output.xlsx')
            wb.active.merge_cells('E1:E1')
            wb.save(out)
            self.assertEqual(check(out)['hard_task_success'], 1)
            wb.active.unmerge_cells('A2:A4')
            wb.save(out)
            self.assertEqual(check(out)['hard_task_success'], 0)

    def test_scalar_isnumber_does_not_coerce_text_or_booleans(self):
        w = Workbook().active
        for coordinate, value in {'A1': 3, 'A2': '-', 'A3': '3', 'A4': True,
                'B1': '=ISNUMBER(A1)', 'B2': '=ISNUMBER(A2)', 'B3': '=ISNUMBER(A3)',
                'B4': '=ISNUMBER(A4)',
                'C1': '=IF(ISNUMBER(A1),A1,0)+IF(ISNUMBER(A2),A2,0)'}.items():
            w[coordinate] = value
        calc = SpreadsheetFormulaEvaluator(w)
        self.assertEqual([calc.cell(f'B{i}') for i in range(1, 5)], [True, False, False, False])
        self.assertEqual(calc.cell('C1'), 3)

    def test_source_archive_without_git_can_record_revision(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(source_revision(root), 'unversioned_source_archive')
            (root / 'SOURCE_REVISION').write_text('archive-revision', encoding='utf-8')
            self.assertEqual(source_revision(root), 'archive-revision')


if __name__ == '__main__':
    unittest.main()
