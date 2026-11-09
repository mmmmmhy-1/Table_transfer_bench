"""Run a fixed three-tool agent with API credentials kept outside Docker.

Uses the Chat Completions wire protocol directly; does not depend on an SDK.
This is a lightweight independent scaffold, not a reproduction of SWE-agent.
"""
import argparse
import concurrent.futures
import csv
import hashlib
import importlib.util
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
PRINT_LOCK = threading.Lock()
SYSTEM = """You are a spreadsheet transformation agent. Complete the user's task by
autonomously inspecting the supplied workbook, using the available tools, and
writing /workspace/submission.xlsx. You have Python, openpyxl, pandas, and numpy
in a Linux container. /input is read-only. /workspace and /tmp are writable.
There is no network, reference solution, evaluator, or answer feedback.
Use view_xlsx to inspect workbook evidence, and bash to run code and self-check.
Preserve the facts and all relationships required by the task. Decide the method
yourself. After checking your output, call submit. Do not merely describe a
solution. Call one tool at a time. You may correct errors using tool feedback.
Do not round underlying ratios unless the task requests it. Reading an xlsx with
data_only=True does not calculate formulas; missing caches are not zero values.
"""
TOOLS = [
    {'type': 'function', 'function': {
        'name': 'view_xlsx',
        'description': 'Read-only inspection of workbook sheets, coordinates, values, formulas, number formats and merge ranges. Does not infer table semantics.',
        'parameters': {'type': 'object', 'properties': {
            'path': {'type': 'string', 'description': 'Default /input/input.xlsx; may inspect /workspace/submission.xlsx.'},
            'sheet': {'type': 'string', 'description': 'Omit to list sheets; otherwise the exact sheet name.'},
            'range': {'type': 'string', 'description': 'Optional A1 rectangle, maximum 2000 cells.'}},
            'additionalProperties': False}}},
    {'type': 'function', 'function': {
        'name': 'bash', 'description': 'Execute one Linux shell command in the isolated task container. Python scripts may be written and executed. Execution is time-limited.',
        'parameters': {'type': 'object', 'properties': {'command': {'type': 'string'}},
                       'required': ['command'], 'additionalProperties': False}}},
    {'type': 'function', 'function': {
        'name': 'submit', 'description': 'Finalize /workspace/submission.xlsx. Checks only that it is a readable workbook, not answer correctness. Ends the episode.',
        'parameters': {'type': 'object', 'properties': {}, 'additionalProperties': False}}}
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True).encode('utf-8')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, obj):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def redact(text, secret=''):
    if secret:
        text = text.replace(secret, '[REDACTED]')
    return re.sub(r'\bsk-[A-Za-z0-9_-]{12,}', '[REDACTED]', text)


def run_cmd(args, timeout=90):
    result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    return result.returncode, result.stdout, result.stderr


def require_cmd(args, timeout=90):
    code, out, err = run_cmd(args, timeout)
    if code:
        raise RuntimeError(f'{args[0]} failed ({code}): {err[-3000:]}')
    return out.strip()


def source_revision(root=ROOT):
    """Git checkouts and extracted source archives are both runnable."""
    try:
        code, out, _ = run_cmd(['git', '-C', str(root), 'rev-parse', 'HEAD'])
        if code == 0:
            return out.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    revision_file = Path(root) / 'SOURCE_REVISION'
    return revision_file.read_text(encoding='utf-8').strip() if revision_file.exists() else 'unversioned_source_archive'


class APIError(RuntimeError):
    pass


def container_identity():
    """Keep bind mounts writable on Linux without running the agent as root."""
    uid = getattr(os, 'getuid', lambda: 1000)()
    gid = getattr(os, 'getgid', lambda: 1000)()
    return (uid, gid) if uid > 0 else (1000, 1000)


class Client:
    def __init__(self, config, key):
        self.config, self.key = config, key

    def complete(self, model, messages, log, remaining):
        cfg = self.config
        body = {'model': model, 'messages': messages, 'tools': TOOLS,
                'tool_choice': 'auto', 'parallel_tool_calls': False,
                'temperature': cfg['temperature'],
                'max_tokens': min(cfg['max_tokens_per_response'], remaining)}
        encoded = canonical(body)
        for attempt in range(1, cfg['max_api_attempts'] + 1):
            start = time.monotonic()
            req = urllib.request.Request(cfg['base_url'].rstrip('/') + '/chat/completions',
                    data=encoded, headers={'Authorization': 'Bearer ' + self.key,
                    'Content-Type': 'application/json', 'User-Agent': 'TableTransferBench/0.1'})
            try:
                with urllib.request.urlopen(req, timeout=cfg['api_timeout_seconds']) as response:
                    result = json.load(response)
                if not result.get('choices'):
                    raise APIError('Response has no choices')
                log('api_response', {'attempt': attempt, 'seconds': time.monotonic() - start,
                                     'response': result})
                return result
            except urllib.error.HTTPError as exc:
                detail = redact(exc.read(4000).decode('utf-8', 'replace'), self.key)
                log('api_error', {'attempt': attempt, 'http_status': exc.code, 'detail': detail})
                if exc.code not in (408, 429, 500, 502, 503, 504) or attempt == cfg['max_api_attempts']:
                    raise APIError(f'HTTP {exc.code}: {detail}') from None
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                log('api_error', {'attempt': attempt, 'detail': str(exc)})
                if attempt == cfg['max_api_attempts']:
                    raise APIError(str(exc)) from None
            time.sleep(min(2 ** attempt, 8))
        raise APIError('API retry limit exceeded')


class Sandbox:
    def __init__(self, config, input_dir, workspace):
        self.config = config
        self.name = 'ttb-' + uuid.uuid4().hex[:16]
        uid, gid = container_identity()
        if os.name == 'posix' and os.getuid() == 0:
            os.chown(workspace, uid, gid)
        args = ['docker', 'run', '-d', '--rm', '--name', self.name,
                '--label', 'table-transfer-bench=0.1', '--network', 'none',
                '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                '--user', f'{uid}:{gid}',
                '--pids-limit', '128', '--cpus', '2', '--memory', '1g',
                '--tmpfs', '/tmp:rw,size=128m',
                '--mount', f'type=bind,src={input_dir.resolve()},dst=/input,readonly',
                '--mount', f'type=bind,src={workspace.resolve()},dst=/workspace',
                config['image']]
        require_cmd(args)

    def execute(self, argv):
        seconds = self.config['tool_timeout_seconds']
        code, out, err = run_cmd(['docker', 'exec', self.name, 'timeout', '--signal=KILL',
                                 str(seconds), *argv], timeout=seconds + 20)
        return {'exit_code': code, 'stdout': out, 'stderr': err}

    def tool(self, name, args):
        if not isinstance(args, dict):
            raise ValueError('Tool arguments must be an object')
        if name == 'bash':
            if not isinstance(args.get('command'), str):
                raise ValueError('bash requires a string command')
            return self.execute(['bash', '-lc', args['command']]), False
        if name == 'view_xlsx':
            argv = ['python', '/opt/ttb/view_xlsx.py']
            for key in ('path', 'sheet', 'range'):
                if key in args:
                    if not isinstance(args[key], str):
                        raise ValueError(f'{key} must be a string')
                    argv.extend(['--' + key, args[key]])
            return self.execute(argv), False
        if name == 'submit':
            if args:
                raise ValueError('submit takes no arguments')
            result = self.execute(['python', '-c',
                "from openpyxl import load_workbook; from pathlib import Path; "
                "p=Path('/workspace/submission.xlsx'); "
                "assert p.stat().st_size <= 20*1024*1024, 'Workbook too large'; "
                "w=load_workbook(p); print('Submitted readable workbook:',w.sheetnames); w.close()"])
            return result, result['exit_code'] == 0
        raise ValueError('Unknown tool: ' + name)

    def close(self):
        run_cmd(['docker', 'rm', '-f', self.name], timeout=30)


def score(case_dir, submission):
    """Invoke the existing case evaluator unchanged, outside the agent sandbox."""
    spec = importlib.util.spec_from_file_location('case_eval_' + uuid.uuid4().hex, case_dir / 'evaluate.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.evaluate(submission)


def diagnostics(errors):
    """Report observable error symptoms; do not claim inferred cognitive causes."""
    found = set()
    for error in errors:
        low = error.lower()
        if any(s in low for s in ('merge', 'header', 'sheet name', 'sheet name/count', 'dimensions', 'column', 'row count', 'worksheet')):
            found.add('structure_or_schema')
        if any(s in low for s in ('format', 'percent', 'percentage-point')):
            found.add('number_format_or_unit')
        if 'formula' in low:
            found.add('formula_execution')
        if 'expected' in low and 'got' in low:
            found.add('cell_content')
        if 'notes' in low or 'key changed' in low:
            found.add('preservation')
    return sorted(found)


def truncated(value, limit):
    text = json.dumps(value, ensure_ascii=False)
    if len(text) <= limit:
        return text
    return text[:limit // 2] + '\n[TRUNCATED: request a smaller range]\n' + text[-limit // 2:]


def run_episode(job, cfg, key, output_root, fingerprint):
    model, case, track, repeat = job
    case_dir = ROOT / case['path']
    model_slug = re.sub(r'[^A-Za-z0-9_.-]', '_', model)
    case_slug = case['domain'] + '__' + Path(case['path']).name
    episode_dir = output_root / model_slug / case_slug / track / f'repeat_{repeat:02d}'
    episode_dir.mkdir(parents=True, exist_ok=True)
    result_path = episode_dir / 'result.json'
    if result_path.exists():
        existing = read_json(result_path)
        if existing.get('experiment_fingerprint') != fingerprint:
            raise ValueError('Existing result belongs to a different configuration: ' + str(result_path))
        return existing
    # A crashed episode may leave files; never reuse those as a fresh model answer.
    workspace = episode_dir / 'workspace'
    if workspace.exists() and any(workspace.iterdir()):
        raise ValueError('Incomplete episode has files; choose a new output directory: ' + str(workspace))
    workspace.mkdir(exist_ok=True)
    input_dir = episode_dir / 'input'
    input_dir.mkdir(exist_ok=True)
    instruction_file = 'instruction.txt' if track == 'discovery' else 'instruction_guided.txt'
    instruction = (case_dir / instruction_file).read_text(encoding='utf-8')
    shutil.copy2(case_dir / 'input.xlsx', input_dir / 'input.xlsx')
    (input_dir / 'instruction.txt').write_text(instruction, encoding='utf-8')
    start = time.monotonic()
    trajectory = episode_dir / 'trajectory.jsonl'

    def log(event, data):
        obj = {'event': event, 'elapsed_seconds': round(time.monotonic() - start, 3), **data}
        with trajectory.open('a', encoding='utf-8') as f:
            f.write(redact(json.dumps(obj, ensure_ascii=False), key) + '\n')

    messages = [{'role': 'system', 'content': SYSTEM},
                {'role': 'user', 'content': 'Input: /input/input.xlsx\nOutput: /workspace/submission.xlsx\n\n' + instruction}]
    result = {'model': model, 'case_id': case['case_id'], 'case_domain': case['domain'],
              'source_family_id': case['source_family_id'], 'track': track, 'repeat': repeat,
              'experiment_fingerprint': fingerprint, 'episode_dir': str(episode_dir.relative_to(output_root)),
              'status': 'not_started', 'hard_task_success': 0,
              'model_turns': 0, 'tool_calls': 0, 'tool_failures': 0,
              'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0,
              'usage_missing_calls': 0, 'response_models': [], 'submitted': False}
    sandbox = None
    log('episode_start', {'model': model, 'case_id': case['case_id'], 'track': track,
                           'repeat': repeat, 'messages': messages})
    try:
        sandbox = Sandbox(cfg, input_dir, workspace)
        client = Client(cfg, key)
        result['status'] = 'turn_limit'
        for turn in range(1, cfg['max_turns'] + 1):
            if time.monotonic() - start >= cfg['episode_timeout_seconds']:
                result['status'] = 'episode_timeout'
                break
            remaining = cfg['max_total_tokens'] - result['total_tokens']
            # This is an observed-usage stop budget, not a preflight tokenizer.
            if remaining < 1024:
                result['status'] = 'token_budget'
                break
            response = client.complete(model, messages, log, remaining)
            result['model_turns'] = turn
            returned_model = response.get('model')
            if returned_model and returned_model not in result['response_models']:
                result['response_models'].append(returned_model)
            usage = response.get('usage') or {}
            if not usage:
                result['usage_missing_calls'] += 1
            for field in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
                result[field] += int(usage.get(field) or 0)
            choice = response['choices'][0]
            raw_message = choice.get('message') or {}
            message = {k: raw_message[k] for k in ('role', 'content', 'tool_calls', 'reasoning_content') if k in raw_message}
            message['role'] = 'assistant'
            messages.append(message)
            calls = message.get('tool_calls') or []
            if not calls:
                messages.append({'role': 'user', 'content': 'Use the available tools to finish the workbook. Call submit when /workspace/submission.xlsx is ready. Text alone does not submit it.'})
                log('no_tool_call', {'turn': turn, 'finish_reason': choice.get('finish_reason')})
                continue
            for call in calls:
                result['tool_calls'] += 1
                name = call.get('function', {}).get('name', '')
                try:
                    args = json.loads(call['function'].get('arguments') or '{}')
                    observation, submitted = sandbox.tool(name, args)
                except Exception as exc:
                    observation, submitted = {'exit_code': 1, 'error': str(exc)}, False
                if observation.get('exit_code', 0):
                    result['tool_failures'] += 1
                log('tool', {'turn': turn, 'tool_call': call, 'observation': observation})
                messages.append({'role': 'tool', 'tool_call_id': call['id'],
                                 'content': truncated(observation, cfg['max_observation_chars'])})
                if submitted:
                    result['submitted'] = True
                    result['status'] = 'submitted'
            if result['submitted']:
                break
    except APIError as exc:
        result['status'] = 'api_error'
        result['error'] = redact(str(exc), key)
    except Exception as exc:
        result['status'] = 'infrastructure_error'
        result['error'] = redact(str(exc), key)
    finally:
        if sandbox is not None:
            try:
                sandbox.close()
            except Exception as exc:
                result['cleanup_error'] = str(exc)
    result['elapsed_seconds'] = round(time.monotonic() - start, 3)
    submission = workspace / 'submission.xlsx'
    if submission.is_file():
        result['submission_sha256'] = digest(submission.read_bytes())
        try:
            result['evaluation'] = score(case_dir, submission)
            if result['submitted']:
                result['hard_task_success'] = int(result['evaluation'].get('hard_task_success') == 1)
            result['error_symptoms'] = diagnostics(result['evaluation'].get('errors', []))
        except Exception as exc:
            result['evaluation'] = {'hard_task_success': 0, 'errors': [str(exc)]}
            result['status'] = 'evaluator_error'
    else:
        result['evaluation'] = {'hard_task_success': 0, 'errors': ['No submission.xlsx produced']}
    write_json(episode_dir / 'messages.json', json.loads(redact(json.dumps(messages, ensure_ascii=False), key)))
    write_json(result_path, result)
    with PRINT_LOCK:
        print(json.dumps({'model': model, 'case': case['domain'], 'track': track, 'repeat': repeat,
              'status': result['status'], 'success': result['hard_task_success'],
              'turns': result['model_turns'], 'seconds': result['elapsed_seconds']}, ensure_ascii=False), flush=True)
    return result


def aggregate(results):
    groups = {}
    for result in results:
        key = (result['model'], result['track'])
        groups.setdefault(key, []).append(result)
    rows = []
    for (model, track), items in sorted(groups.items()):
        rows.append({'model': model, 'track': track, 'episodes': len(items),
                     'successes': sum(r['hard_task_success'] for r in items),
                     'success_rate': sum(r['hard_task_success'] for r in items) / len(items),
                     'mean_turns': sum(r['model_turns'] for r in items) / len(items),
                     'mean_seconds': sum(r['elapsed_seconds'] for r in items) / len(items),
                     'total_tokens': sum(r['total_tokens'] for r in items),
                     'api_or_infrastructure_errors': sum(r['status'] in ('api_error', 'infrastructure_error', 'evaluator_error') for r in items)})
    return rows


def save_summary(output_root, results, fingerprint, expected):
    rows = aggregate(results)
    write_json(output_root / 'summary.json', {'experiment_fingerprint': fingerprint,
               'expected_episodes': expected, 'completed_episodes': len(results),
               'groups': rows, 'results': sorted(results, key=lambda r: (r['model'], r['case_id'], r['track'], r['repeat']))})
    if rows:
        with (output_root / 'summary.csv').open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'benchmark/config.json')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--models', nargs='+')
    parser.add_argument('--tracks', nargs='+', choices=['discovery', 'guided'])
    parser.add_argument('--cases', nargs='+', help='Optional domain names or exact case IDs')
    parser.add_argument('--repeats', type=int)
    parser.add_argument('--workers', type=int)
    parser.add_argument('--key-stdin', action='store_true', help='Read key from stdin instead of PARATERA_API_KEY; never saved')
    args = parser.parse_args()
    cfg = read_json(args.config)
    for field in ('models', 'tracks', 'repeats', 'workers'):
        if getattr(args, field) is not None:
            cfg[field] = getattr(args, field)
    if min(cfg['repeats'], cfg['workers'], cfg['max_turns']) < 1:
        parser.error('repeats/workers/max_turns must be positive')
    key = sys.stdin.read().strip() if args.key_stdin else os.environ.get('PARATERA_API_KEY', '').strip()
    if not key:
        parser.error('Provide PARATERA_API_KEY or --key-stdin')
    output_root = args.output_dir.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    catalog = read_json(ROOT / 'data/catalog.json')
    cases = [c for c in catalog['cases'] if not args.cases or c['domain'] in args.cases or c['case_id'] in args.cases]
    if not cases:
        parser.error('No matching cases')
    source_files = ['data/catalog.json', 'benchmark/runner.py', 'benchmark/view_xlsx.py', 'benchmark/Dockerfile', 'benchmark/requirements-docker.lock', 'scripts/formula_eval.py']
    for case in cases:
        source_files.extend(case['path'] + '/' + f for f in ('input.xlsx', 'instruction.txt', 'instruction_guided.txt', 'evaluate.py', 'gold_output.xlsx', 'gold_canonical.json'))
    hashes = {p: digest((ROOT / p).read_bytes()) for p in source_files}
    image_id = require_cmd(['docker', 'image', 'inspect', cfg['image'], '--format', '{{.Id}}'])
    fingerprint = digest(canonical({'config': cfg, 'files': hashes, 'image_id': image_id}))
    manifest = {'scaffold': 'TTB lightweight three-tool function-calling agent v0.1 (not SWE-agent)',
                'config': cfg, 'image_id': image_id, 'file_sha256': hashes,
                'git_revision': source_revision(),
                'host_python': sys.version,
                'host_packages': {name: importlib.metadata.version(name) for name in ('openpyxl', 'lxml', 'jsonschema')},
                'experiment_fingerprint': fingerprint,
                'data_role': 'public_demo_development_only',
                'notes': ['Fresh independent episode for every repeat; no best-of selection.',
                          'Provider-default reasoning; equal settings do not imply equal hidden reasoning compute.',
                          'Observed cumulative total_tokens triggers budget stop; a request may cross the stop threshold.',
                          'Episode wall-time limit is checked between model turns; an in-flight API/tool call may finish after it.',
                          'API retries may incur unreported costs; token totals count successful responses only.',
                          'No LibreOffice recalculation in this baseline; current case evaluators support restricted uncached formulas.']}
    manifest_path = output_root / 'manifest.json'
    if manifest_path.exists() and read_json(manifest_path)['experiment_fingerprint'] != fingerprint:
        parser.error('Output directory has a different experiment; use a fresh directory')
    write_json(manifest_path, manifest)
    # Interleave models so a provider outage or interruption does not exhaust only one model.
    jobs = [(model, case, track, repeat) for repeat in range(1, cfg['repeats'] + 1)
            for case in cases for track in cfg['tracks'] for model in cfg['models']]
    print(json.dumps({'episodes': len(jobs), 'output': str(output_root), 'workers': cfg['workers']}), flush=True)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg['workers']) as pool:
        # Use the immutable image ID for every episode even if somebody retags it.
        runtime_config = {**cfg, 'image': image_id}
        futures = [pool.submit(run_episode, job, runtime_config, key, output_root, fingerprint) for job in jobs]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            save_summary(output_root, results, fingerprint, len(jobs))
    print(json.dumps({'completed': len(results), 'groups': aggregate(results)}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
