"""Create a shareable HTML report and episode CSV from saved pilot results."""
import argparse
import csv
import datetime
import html
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('result_dir', type=Path)
    p.add_argument('--corrected', action='store_true', help='Use summary_corrected.json, retaining the raw report')
    args = p.parse_args()
    root = args.result_dir.resolve()
    summary_name = 'summary_corrected.json' if args.corrected else 'summary.json'
    summary = json.loads((root / summary_name).read_text(encoding='utf-8'))
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    results = summary['results']
    fields = ['model', 'case_domain', 'case_id', 'track', 'repeat', 'status',
              'hard_task_success', 'model_turns', 'tool_calls', 'tool_failures',
              'elapsed_seconds', 'prompt_tokens', 'completion_tokens', 'total_tokens', 'episode_dir']
    if args.corrected:
        fields.insert(7, 'original_hard_task_success')
    metrics_name = 'episode_metrics_corrected.csv' if args.corrected else 'episode_metrics.csv'
    with (root / metrics_name).open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)
    esc = lambda x: html.escape(str(x))
    cells = lambda values: ''.join('<td>' + esc(v) + '</td>' for v in values)
    group_rows = ''.join('<tr>' + cells([r['model'], r['track'],
        f"{r['successes']}/{r['episodes']}", f"{r['success_rate']:.1%}",
        f"{r['mean_turns']:.1f}", f"{r['mean_seconds']:.1f}",
        f"{r['total_tokens']:,}", r['api_or_infrastructure_errors']]) + '</tr>'
        for r in summary['groups'])
    by_case = {}
    for r in results:
        by_case.setdefault((r['model'], r['case_domain'], r['track']), []).append(r)
    case_rows = ''.join('<tr>' + cells([model, domain, track,
        f"{sum(x['hard_task_success'] for x in items)}/{len(items)}",
        ', '.join(str(x['hard_task_success']) for x in sorted(items, key=lambda x: x['repeat']))]) + '</tr>'
        for (model, domain, track), items in sorted(by_case.items()))
    details = []
    for r in results:
        if r['hard_task_success']:
            continue
        errors = r.get('evaluation', {}).get('errors', [])
        error_text = '\n'.join(errors[:6]) or r.get('error', '')
        rel = r['episode_dir'].replace('\\', '/')
        result_name = 'result_corrected.json' if args.corrected else 'result.json'
        link = '<a href="' + esc(rel + '/' + result_name) + '">判分</a> · <a href="' + esc(rel + '/trajectory.jsonl') + '">轨迹</a>'
        details.append('<tr>' + cells([r['model'], r['case_domain'], r['track'], r['repeat'], r['status']])
                       + '<td><pre>' + esc(error_text) + '</pre></td><td>' + link + '</td></tr>')
    total_success = sum(r['hard_task_success'] for r in results)
    date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')
    cfg = manifest['config']
    revision_note = ''
    if args.corrected:
        revision_note = '<div class="card"><strong>统一复评分</strong><p class="note">修正三处检查器限制：business 年份表头允许文本/数值等价；labor 忽略不改变关系的单格合并；共享公式求值支持标量 ISNUMBER。所有运行均离线重评，没有修改提交、重新调用模型或向模型提供评分反馈。错误年份、错误数值及缺失真正分组仍会被拒绝。</p><p><a href="report.html">原始严格评分</a> · <a href="rescore_manifest.json">修订与逐条变更记录</a></p></div>'
    report = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Table Transfer Bench 预实验</title>
<style>body{{font-family:system-ui,"Microsoft YaHei",sans-serif;color:#17243b;background:#f4f7fb;margin:0;padding:32px}}main{{max-width:1250px;margin:auto}}h1{{font-size:30px}}h2{{margin-top:32px}}.card{{background:white;border:1px solid #dbe3ef;padding:20px;border-radius:12px;margin:16px 0;overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #e5eaf2;vertical-align:top}}th{{background:#edf2f8}}pre{{white-space:pre-wrap;word-break:break-word;max-width:520px;font-size:12px;margin:0}}.note{{color:#52647b;line-height:1.7}}a{{color:#1661b3}}code{{word-break:break-all}}</style>
<main><h1>Table Transfer Bench · Agent 预实验</h1>
<p class="note">生成时间：{esc(date)} · 公开样例开发测试，不是隐藏测试集成绩。</p>
{revision_note}
<div class="card"><strong>已完成 {len(results)}/{summary['expected_episodes']} 次运行；全体提交通过 {total_success}/{len(results)}。</strong>
<p class="note">3 个独立来源表，每个模型分别执行 Discovery / Guided，每个条件 {cfg['repeats']} 次独立重复。
重复结果全部计入分母，不取最好的一次。三条样例不足以支撑稳定模型排名；提示条件差异仅提供诊断线索。</p></div>
<h2>模型 × 指令轨道</h2><div class="card"><table><tr><th>模型</th><th>轨道</th><th>通过/运行</th><th>成功率</th><th>平均轮数</th><th>平均秒数</th><th>返回 Token 总量</th><th>API/基础设施错误</th></tr>{group_rows}</table></div>
<h2>逐案例结果</h2><div class="card"><table><tr><th>模型</th><th>案例</th><th>轨道</th><th>通过/运行</th><th>各次重复（1=通过）</th></tr>{case_rows}</table></div>
<h2>未通过运行与判分证据</h2><div class="card"><table><tr><th>模型</th><th>案例</th><th>轨道</th><th>重复</th><th>结束状态</th><th>前六条错误</th><th>原始证据</th></tr>{''.join(details) or '<tr><td colspan="7">全部通过。</td></tr>'}</table></div>
<h2>运行协议与局限</h2><div class="card"><p class="note">独立轻量 function-calling scaffold，采用 view_xlsx / bash / submit，不是 SWE-agent 的严格复现。
模型自主检查并处理文件；Docker 无网络、输入只读、无 Gold/evaluator/API key。评分在容器外执行，未向模型反馈答案。
主指标要求所有必需条件同时满足，评测器修订另行记录。单元格、格式、合并等错误不能仅凭最终文件认定认知根因。</p>
<p class="note">temperature={cfg['temperature']}；单次回复最多 {cfg['max_tokens_per_response']} tokens；最多 {cfg['max_turns']} 轮；单工具 {cfg['tool_timeout_seconds']} 秒；episode 轮次间时间阈值 {cfg['episode_timeout_seconds']} 秒；返回累计 token 停止阈值 {cfg['max_total_tokens']}。
各模型保留提供商默认推理设置。Token 为成功 API 响应报告的用量，不能视为账单金额。当前容器不含 LibreOffice，使用已有 evaluator 的受限公式求值。</p>
<p>实验指纹：<code>{esc(manifest['experiment_fingerprint'])}</code><br>源版本：<code>{esc(manifest['git_revision'])}</code></p>
<p><a href="{summary_name}">完整结果 JSON</a> · <a href="{metrics_name}">逐次运行 CSV</a> · <a href="manifest.json">原始配置与数据/代码哈希</a></p></div></main></html>'''
    report_name = 'report_corrected.html' if args.corrected else 'report.html'
    (root / report_name).write_text(report, encoding='utf-8')
    print(root / report_name)


if __name__ == '__main__':
    main()
