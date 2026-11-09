"""Offline protocol tests; Docker isolation test is opt-in and makes no API calls."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from openpyxl import Workbook

from benchmark.runner import Client, Sandbox, aggregate, redact
from benchmark.view_xlsx import inspect_workbook


class EvidenceTests(unittest.TestCase):
    def test_structure_and_percent_are_raw_evidence(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'input.xlsx'
            wb = Workbook()
            w = wb.active
            w['A1'] = 'Parent'
            w.merge_cells('A1:B1')
            w['A2'] = .15
            w['A2'].number_format = '0%'
            w['B2'] = '=A2*2'
            wb.save(path)
            result = inspect_workbook(path, w.title, 'A1:B2')
            cells = {c['coordinate']: c for c in result['cells']}
            self.assertEqual(result['merged_ranges'], ['A1:B1'])
            self.assertNotIn('B1', cells)  # No automatic parent propagation.
            self.assertEqual(cells['A2']['value'], .15)
            self.assertEqual(cells['A2']['number_format'], '0%')
            self.assertEqual(cells['B2']['value'], '=A2*2')
            self.assertIsNone(cells['B2']['cached_value'])
            with self.assertRaises(ValueError):
                inspect_workbook(path, w.title, 'A1:ZZ1000')

    def test_redacts_exact_and_key_shaped_secrets(self):
        self.assertEqual(redact('abc my-secret xyz', 'my-secret'), 'abc [REDACTED] xyz')
        self.assertNotIn('sk-examplecredential123456', redact('error sk-examplecredential123456'))

    def test_summary_counts_every_repeat_and_infrastructure_failure(self):
        items = [dict(model='M', track='discovery', hard_task_success=x,
                      model_turns=2, elapsed_seconds=4, total_tokens=20, status=status)
                 for x, status in [(1, 'submitted'), (0, 'submitted'), (0, 'api_error')]]
        row = aggregate(items)[0]
        self.assertEqual(row['episodes'], 3)
        self.assertEqual(row['successes'], 1)
        self.assertEqual(row['success_rate'], 1 / 3)
        self.assertEqual(row['api_or_infrastructure_errors'], 1)


class APITests(unittest.TestCase):
    def test_wire_protocol_and_reasoning_round_trip(self):
        captured = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                captured.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                payload = {'model': 'model-id', 'choices': [{'finish_reason': 'tool_calls',
                    'message': {'role': 'assistant', 'content': '', 'reasoning_content': 'trace',
                                'tool_calls': [{'id': 'call_1', 'type': 'function',
                                    'function': {'name': 'submit', 'arguments': '{}'}}]}}],
                    'usage': {'prompt_tokens': 12, 'completion_tokens': 3, 'total_tokens': 15}}
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())

            def log_message(self, *_):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        cfg = dict(base_url=f'http://127.0.0.1:{server.server_port}/v1', temperature=.6,
                   max_tokens_per_response=100, max_api_attempts=1, api_timeout_seconds=5)
        logs = []
        try:
            response = Client(cfg, 'test-secret').complete('M', [{'role': 'user', 'content': 'task'}],
                                                          lambda event, data: logs.append((event, data)), 500)
            self.assertEqual(response['choices'][0]['message']['reasoning_content'], 'trace')
            self.assertFalse(captured[0]['parallel_tool_calls'])
            self.assertEqual([t['function']['name'] for t in captured[0]['tools']], ['view_xlsx', 'bash', 'submit'])
            self.assertNotIn('test-secret', json.dumps(captured) + json.dumps(logs))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


@unittest.skipUnless(os.environ.get('TTB_DOCKER_TEST') == '1', 'Set TTB_DOCKER_TEST=1 for Docker integration')
class DockerTests(unittest.TestCase):
    def test_no_network_secret_gold_or_input_writes_and_valid_submit(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            inp, out = base / 'input', base / 'out'
            inp.mkdir()
            out.mkdir()
            Workbook().save(inp / 'input.xlsx')
            sandbox = Sandbox({'image': 'ttb-agent:0.1', 'tool_timeout_seconds': 10}, inp, out)
            try:
                code = """import os,pathlib,socket
from openpyxl import load_workbook
assert os.getuid() != 0
assert 'PARATERA_API_KEY' not in os.environ
assert not list(pathlib.Path('/input').glob('*gold*'))
assert not pathlib.Path('/var/run/docker.sock').exists()
try:
 pathlib.Path('/input/leak.txt').write_text('bad')
 raise AssertionError('input writable')
except OSError: pass
s=socket.socket(); s.settimeout(1)
assert s.connect_ex(('1.1.1.1',443)) != 0
s.close()
w=load_workbook('/input/input.xlsx');w.active['A1']='test';w.save('/workspace/submission.xlsx')
print('isolation and output OK')
"""
                result = sandbox.execute(['python', '-c', code])
                self.assertEqual(result['exit_code'], 0, result)
                result, submitted = sandbox.tool('submit', {})
                self.assertTrue(submitted, result)
                self.assertTrue((out / 'submission.xlsx').exists())
            finally:
                sandbox.close()


if __name__ == '__main__':
    unittest.main()
