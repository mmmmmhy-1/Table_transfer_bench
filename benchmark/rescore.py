"""Re-score saved submissions after a versioned evaluator correction.

Never invokes a model or changes a workbook. Original results remain intact.
"""
import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path

from benchmark.runner import ROOT, aggregate, diagnostics, read_json, score, source_revision, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('result_dir', type=Path)
    p.add_argument('--reason', required=True)
    args = p.parse_args()
    root = args.result_dir.resolve()
    original = read_json(root / 'summary.json')
    if original['completed_episodes'] != original['expected_episodes']:
        p.error('Finish the original matrix before applying an evaluator revision')
    catalog = {c['case_id']: c for c in read_json(ROOT / 'data/catalog.json')['cases']}
    frozen = read_json(root / 'manifest.json')
    for name, expected_hash in frozen['file_sha256'].items():
        if name.startswith('data/') and not name.endswith('/evaluate.py'):
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected_hash:
                p.error('Task input/reference changed since inference: ' + name)
    results, changes = [], []
    for raw in original['results']:
        result = copy.deepcopy(raw)
        episode = root / raw['episode_dir']
        submission = episode / 'workspace/submission.xlsx'
        result['original_hard_task_success'] = raw['hard_task_success']
        result['original_evaluation'] = raw['evaluation']
        if submission.exists():
            if hashlib.sha256(submission.read_bytes()).hexdigest() != raw['submission_sha256']:
                p.error('Submission has changed since inference: ' + str(submission))
            result['evaluation'] = score(ROOT / catalog[raw['case_id']]['path'], submission)
            result['hard_task_success'] = int(raw['submitted'] and result['evaluation'].get('hard_task_success') == 1)
            result['error_symptoms'] = diagnostics(result['evaluation'].get('errors', []))
        result['evaluation_revision_reason'] = args.reason
        if result['hard_task_success'] != raw['hard_task_success']:
            changes.append({'model': raw['model'], 'case_id': raw['case_id'], 'track': raw['track'],
                            'repeat': raw['repeat'], 'original': raw['hard_task_success'],
                            'corrected': result['hard_task_success'],
                            'original_errors': raw['evaluation'].get('errors', []),
                            'corrected_errors': result['evaluation'].get('errors', [])})
        write_json(episode / 'result_corrected.json', result)
        results.append(result)
    files = [catalog[c]['path'] + '/' + name for c in catalog for name in ('evaluate.py', 'metadata.json')]
    files.extend(['scripts/formula_eval.py', 'benchmark/rescore.py'])
    hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in files}
    rescore = {'reason': args.reason, 'original_experiment_fingerprint': original['experiment_fingerprint'],
               'evaluator_revision': 'pilot-evaluator-v2-2026-11-07', 'source_revision': source_revision(),
               'evaluator_sha256': hashes, 'changed_scores': changes,
               'notes': ['No model calls, retries, submission edits, or selective re-scoring.',
                         'All original results and traces retained; only evaluator representation equivalence corrected.']}
    write_json(root / 'rescore_manifest.json', rescore)
    write_json(root / 'summary_corrected.json', {**original, 'evaluation_revision': rescore,
                                                'groups': aggregate(results), 'results': results})
    rows = aggregate(results)
    with (root / 'summary_corrected.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({'episodes': len(results), 'changed_scores': len(changes),
                      'groups': aggregate(results)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
