# 三工具 Agent 预实验

本运行器采用与 SpreadsheetBench 2 相近的 `view_xlsx / bash / submit` 接口，
自行实现轻量 function-calling 循环；**不是 SWE-agent，也不是 SpreadsheetBench 2 的严格复现**。
当前只用于三条公开样例的开发预实验，不构成未见测试成绩。

## 运行

需要 Python 3.11+、Docker Desktop（Linux containers）和有模型权限的 API key。

```powershell
python -m pip install -r requirements.txt
docker build -t ttb-agent:0.1 -f benchmark/Dockerfile benchmark
$credential = Read-Host 'API key' -AsSecureString
$env:PARATERA_API_KEY = [System.Net.NetworkCredential]::new('', $credential).Password
python -m benchmark.runner --output-dir runs/pilot
Remove-Item Env:PARATERA_API_KEY
```

`PARATERA_API_KEY` 只由宿主机的 API 客户端读取，不传给容器。
程序也支持 `--key-stdin`，可由凭据管理器通过 stdin 注入而不落盘。
默认使用 `https://llmapi.paratera.com/v1/chat/completions`；不依赖特定厂商 SDK。

单任务烟雾检查：

```powershell
python -m benchmark.runner --models Qwen3.6-27B --cases environment --tracks discovery --repeats 1 --workers 1 --output-dir runs/smoke
```

默认完整矩阵：3 模型 × 3 案例 × 2 指令轨道 × 3 独立重复 = 54 episodes。
模型为 Qwen3.6-27B、MiniMax-M2.5、Qwen3.7-Max。配置见 `benchmark/config.json`。
支持 `--models`、`--tracks`、`--cases`、`--repeats`、`--workers` 覆盖。

## 实验约定

- 每个 episode 使用全新容器和工作目录，输入只读，不挂载仓库、Gold、evaluator、Docker socket 或密钥。
- 容器无网络、非 root、只读根文件系统、丢弃 capabilities，并限制 CPU/内存/进程数。
- 三个工具都在容器内执行；`view_xlsx` 只暴露文件证据，不自动识别语义表头或填充合并单元格。
- `submit` 只检查输出是可读取的 XLSX。case evaluator 在容器停止后由宿主机执行，答案反馈不返回 agent。
- 固定 temperature=0.6、单次回复 max_tokens=8192、最多 50 模型调用、工具执行 60 秒。整题 1200 秒停止阈值在轮次间检查，进行中的 API/工具调用可能跨过此阈值。
- 三模型均不覆盖厂商默认 reasoning 设置。相同请求设置不等于相同内部推理计算量，需在报告中保留此限制。
- 累计返回的 total_tokens 达到 500000 后停止继续调用；这是观察到的使用量停止阈值，最后一次请求可能跨过阈值，不是精确的预分词上限。
- 只对超时、429、部分 5xx 做最多 3 次传输重试；不根据判分结果重做任务。成功响应 token 统计不包含未返回 usage 的失败请求成本。
- 每次重复独立计分，取全部运行的平均成功率，不取三次最优。基础设施/API 错误单独列出，同时保留在预定运行总数分母中。
- 没有调用 submit 的任务即使产生文件，主成功分仍为 0，但保留离线评测诊断。
- 当前环境没有 LibreOffice；三条现有 evaluator 保持不变，支持其限定范围内的无缓存公式。后续扩展任务应单独制定公式重算协议。

## 结果与恢复

输出目录包含：

```text
manifest.json                    配置、代码/数据 SHA256、Docker image ID、Git revision
summary.json / summary.csv       所有已完成运行与模型×轨道汇总
<model>/<case>/<track>/repeat_N/
  input/                         仅输入和当前指令
  workspace/submission.xlsx      模型提交，及模型创建的脚本
  trajectory.jsonl               模型响应、工具参数/完整返回、时间和 usage
  messages.json                  最终对话（工具观测按统一上限截断）
  result.json                    提交状态、现有 evaluator 结果、错误症状
```

错误症状（内容、schema、格式等）是对 evaluator 信息的归类，不等于模型认知错误根因。
判断根因需结合工具轨迹人工复核，不能仅凭模型自述。

相同命令与相同指纹会跳过已完成 episode。配置、输入、提示、评测代码或镜像改变时，必须换新输出目录。
未完成且留有工作文件的 episode 会拒绝静默复用，需换目录，避免上一轮答案污染。
API key 不写入持久文件，并对保存的轨迹做密钥模式脱敏。请勿把其他凭据放入任务输入。

## 验证

```powershell
python -m unittest benchmark.test_baseline -v
$env:TTB_DOCKER_TEST='1'
python -m unittest benchmark.test_baseline benchmark.test_evaluator_contract -v
python scripts/validate_annotations.py
python scripts/check_public_cases.py
```

Docker 集成测试验证输入只读、无网络、无密钥/Gold 挂载、非 root 和提交路径。
其余测试验证合并/比例值不被查看工具改写、API 工具协议、密钥脱敏及重复运行聚合。

## 2026-11-07 预实验发现的检查器修正

首次 54 次推理全部使用冻结的原始评测器，原始源码包、`manifest.json`、
`summary.json` 和逐次 `result.json` 保留不变。随后发现三处确定性检查器限制：

1. business 年份表头原先要求字符串 `"2014"` / `"2015"`，但指令没有规定存储类型。
   现允许相同年份的数值表示；错误年份、小数年份和布尔值仍拒绝。
2. labor 原先把 `A52:A52` 这类单格合并视为多余分组。现忽略不改变关系的单格合并；
   缺失或多余的真正跨行/跨列分组仍拒绝。
3. 共享公式求值器补充标量 `ISNUMBER`，准确区分数字、数值文本、缺失符号和布尔值。
   这不代表支持任意 Excel 函数或数组公式。

修正后必须对整个矩阵统一离线复评，不挑选模型或个别运行；不调用模型、不修改提交。
`rescore.py` 会验证任务/Gold 未改变、提交 SHA256 与原运行一致，并另存新评分：

```powershell
python -m benchmark.rescore runs/pilot --reason 'Year-header representation equivalence; singleton-merge identity; scalar ISNUMBER support'
python -m benchmark.report runs/pilot
python -m benchmark.report runs/pilot --corrected
```

复评产生 `summary_corrected.json/csv`、逐次 `result_corrected.json` 和
`rescore_manifest.json`；HTML 报告并排保留原始成绩入口和修订原因。
修订代码有回归测试，确保错误年份、错误计算、缺失真实分组仍会失败。
后续 Environment21 布局修订见下节；原始结果和旧复评分保留不变。

从 ZIP 解压的源码也能运行；没有 Git 时会使用随包 `SOURCE_REVISION` 或标记为无版本源码，
同时继续记录实际代码/数据哈希。

## 2026-11-09：V2.2 布局契约与 OP6 增补

以远端 V2.2 为基础保留 OP7 分类和劳动案例的新标签。Environment21 两轨共用相同业务指令，
Guided 只增加输入定位。标题/脚注装饰合并宽度和 Total 纵向合并可选；原始语义表头、独立 Total 列、
数值/行序及百分比要求继续核验。字体、字号、颜色、边框和仅样式形成的空白 used-range 扩张不判错。

本轮修改了提示契约，旧模型输出的检查器重评只作为历史输出诊断，不能宣称为新提示词下的实验成绩。
`rescore.py` 保留其任务/输入哈希保护，会拒绝把指令改变后的输出当成原实验进行普通复评。
若要评测新提示，使用全新输出目录重新运行，原轨迹、提交和各版本成绩均保留。

OP6 增补的是可校验的标注/构造规范，不代表已发布 OP6 样本或训练了新模型。
见 [OP6 表格整合与拆分](op6_table_integration_v2.2_zh.md)。

参考：[SpreadsheetBench 2](https://github.com/RUCKBReasoning/SpreadsheetBench-2)。
