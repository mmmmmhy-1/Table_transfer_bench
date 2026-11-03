# Table Transformation Benchmark V2.1 — 数据构建与标注指南（中文）

> 本文是可实际执行的标注 SOP，配合 [V2.1 构建标准](benchmark_standard_v2.1_zh.md)、[JSON Schema](../schemas/case_metadata.schema.json) 和 [数据目录规则](../data/README.md)。新增样本应按下述顺序实施，不能仅依赖旧任务标签或表格文件名自动分类。

## 一、样本构建 SOP

| 步骤 | 标注者需要做什么 | 交付物/验收 |
|---|---|---|
| 1. 记录来源 | 记录原始数据集、具体表 ID、URL、许可与原文件；确定 `source_family_id` | 来源可回溯，同源家族不跨拆分 |
| 2. 理解表结构 | 识别数据区/标题/注释/表头/合并范围/隐藏层级，清点全部数据事实 | 可解释的 S0–S4 与结构坐标 |
| 3. 选择转换目标 | 只选有唯一可判定结果、可编程验证的操作 | OP1–OP6（单个或组合） |
| 4. 受控增删改 | 从真实表生成输入；不要无依据编造业务数值 | `input.xlsx` 和改造记录 |
| 5. 写 Agent 指令 | 明确操作、规则、留存、精度、最终文件 | `instruction.txt` |
| 6. 构建 Gold | 参考执行生成结果，保存规范化形式 | `gold_output.xlsx`、`gold_canonical.json` |
| 7. 标注 Metadata | 领域、来源、操作、结构、规模、DAG、规则等 | `metadata.json` 通过 Schema |
| 8. 独立校验 | 金标准正确性、完整性、错误注入测试 | `evaluate.py` 及审核记录 |
| 9. 人工复核 | 非原构建者审核输入-指令-Gold-标签 | 通过 / 返工 / 拒收 |
| 10. 收录与发布 | 同步更新 `data/catalog.json`；分配 Split | 不混入公开示例和隐藏测试集 |

## 二、存放目录和命名

**以领域作为唯一上级分类**。示例：

```text
data/environment/case_1_realhitbench_environment21/
data/environment/case_2_public_report/
data/finance/case_1_statistics/
```

- 案例号在领域内按新增顺序唯一，公开后不重排。
- `realhitbench` 等后缀是来源名称提示，**不是新的一级/二级分类**。
- 来自同一来源表 `environment21` 的不同任务可以是不同 Case，但必须使用相同 `source_family_id`。
- 单个 Case 既可以是 OP2，也可以是 OP2+OP3；**无需**为不同 OP 复制文件夹。

## 三、标签判定细则

### 3.1 操作选择的首要问题

问：“最终期望 Agent 改变的**数据语义与输出形态**是什么？”

| 示例 | 正确标签 | 常见误标 |
|---|---|---|
| 新建每行的 Total 指标列 | OP2 | OP3（虽然包含求和，但没有新增逻辑行） |
| 为若干组新增小计行 | OP3 | OP2（计算不等于一定生成列） |
| 麻醉方式列转为“类型 + 数值”两列并扩展记录 | OP1 | OP3（宽转长扩张行数，仍是重塑） |
| “华东-产品A-2025Q1”拆成地区/产品/年份/季度 | OP4 | OP5（不是仅仅规范已有值） |
| 将日期统一为 YYYY-MM-DD 或万元转元 | OP5 | OP4（目标是标准化值而非解析多个字段） |
| 按产品 ID 整合销售与成本工作表 | OP6 | OP1（不是简单维度移动） |

对于复杂行表头的 **层级显式化**：先视作 OP1 结构重塑的候选子型并标 S2/S3，不擅自正式增加 OP7。

### 3.2 结构标签

- S0：平表且没有 S1–S4 的复杂结构。
- S1：具有列方向的父子表头层级（标注 `column_header_depth` 和合并范围）。
- S2：具有行方向的层级/分组（标注 `row_header_depth`、关键分组语义）。
- S3：语义有效的合并单元格（标注工作表和范围，如 `A4:A5`）。
- S4：实际存在布局不规则/多数据块等情况（附具体证据），而非“看上去有颜色/标题”就标。

同一案例可以有 S1+S2+S3。**为保持可审计性**，除了标签还应记录相关结构证据；例如 `Mammal` 是分组标题、`Primate` 是其子组，二者不进入数字总计的明细行。

### 3.3 组合操作标注

`operations` 列出真实必需的语义转换；对于两个以上操作，补全：

```json
{
  "operations": ["OP2", "OP3"],
  "operation_nodes": [
    {"id": "derive_total", "operation": "OP2"},
    {"id": "generate_statistics", "operation": "OP3"}
  ],
  "dependency_edges": [["derive_total", "generate_statistics"]]
}
```

- `operation_nodes` 是各个节点，ID 在当前 Case 内唯一。
- `dependency_edges` 使用节点 ID，不使用数组下标。
- 若一个步骤的产物会被另一步使用，则连接依赖边；需避免自环/循环依赖。
- 不因 Python 读取/写入/排序等辅助行为而标注多一个原子操作。
- 如果一个操作组合不能证明真实数据依赖，应退回审核，不强行归为组合测试。

## 四、Metadata 的必填、推荐与约束

**必填字段**（Schema 强制）：`case_id`、`benchmark_version`、`domain`、`source_family_id`、`source`、`operations`、`structure_tags`、`split`、`case_relative_path`。

`source` 内最低要求：`source_dataset`、`source_instance`、`source_filename`、`source_url`、`license`、`modifications`。如许可未知需标 `not_verified`，**不得默认开放再分发**。

**推荐字段**：`case_number`、`case_slug`、`source_id`、`primary_operation`、`operation_nodes`、`dependency_edges`、`input_table_stats`、`gold_table_stats`、`difficulty`、`rules`、`release_role`、`dataset_status`、`evaluation`。

#### 标注示例：环境类第一条案例

```json
{
  "benchmark_version": "2.1",
  "case_id": "TTB_V2_1_RHB_environment21_OP2_OP3_001",
  "domain": "environment",
  "case_number": 1,
  "case_slug": "case_1_realhitbench_environment21",
  "case_relative_path": "data/environment/case_1_realhitbench_environment21",
  "source_family_id": "RealHiTBench_environment21",
  "source": {
    "source_dataset": "RealHiTBench",
    "source_instance": "environment21",
    "source_filename": "environment-table21.html",
    "source_url": "https://github.com/cspzyy/RealHiTBench",
    "license": "CC BY-NC 4.0",
    "modifications": ["Removed Total column", "Removed three statistical rows"]
  },
  "operations": ["OP2", "OP3"],
  "structure_tags": ["S1", "S2", "S3"],
  "split": "example",
  "release_role": "public_demo"
}
```

这是**最小字段示例**，不是覆盖实际 `metadata.json` 的替代文件；实际文件已有更详细信息。结构标签示例仅展示可确认的三种结构，S4 若标注应另附不规则布局的理由。

## 五、规模信息记录

**不允许恢复 Small/Medium 硬分层**。记录连续规模字段：

`num_sheets`、`total_data_rows`、`max_data_columns`、`non_empty_cells`、`used_range_cells`、`merged_region_count`、`input_file_bytes`、`expected_output_rows`、`output_expansion_ratio`（适用时）。

可同时记录每个工作表的规模明细。若原有元数据只存 `used_rows` / `used_columns`，应注意那是包含标题/表头的 used range，而不直接等于业务数据行数；旧样本迁移时明确区分。

## 六、指令文本验收标准

标注者检查：

- 是否可以在不求助隐藏 Gold 的情况下完成？
- 是否正确表达保留/新增/删除哪些行列？
- 是否说明如何处理 `-`、空值、0、除零、重复键和缺失记录？
- 如果有多级表头，是否明确“是否要求保留布局”，而非无意改变任务目标？
- 数值精度是计算精度还是 Excel 显示格式？是否区分？
- 对于 Guided，是否与 Discovery 共享相同事实与目标，只增加结构定位信息？
- 是否遗漏输出文件名、目标工作表或必须的顺序要求？

任何不能唯一决定正确结果的指令先修改后验收。

## 七、Gold / Evaluator 复核

- 生成 Gold 的程序应可重运行；如果按规定展示数值或公式，重新打开的内容必须正确。
- 校验器不能只把单元格二进制/样式与 Gold 逐字节比较；对未要求顺序的结果应进行语义规范化比较。
- 对必须保留的分组、合并结构、列/行顺序和数值不能过宽容。
- 核心 Hard Task Success 的判定条件需要在任务写作之前固定。
- 人工错误注入建议至少 5 类：错数、删行、重复行、错列/错维度、破坏表头或层级。多表 OP6 增加错键/错 Join 类型。
- 对组合任务尽可能核查中间步骤的可观察输出，记录首个失败节点与最终错误，避免无证据地推断“模型没理解”。

## 八、审核拒收与修订规则

**拒收/返工**：
1. 无来源或许可无法满足当前发布方式；
2. 模糊指令导致多个合理 Gold；
3. 计算缺少必要原始数据；
4. Gold 无法复现或验证器接受明显错误；
5. 结构标签与真实表结构不符；
6. 无意义的模板重复或跨 Split 同源泄漏；
7. 组合操作仅为互不相关的指令拼贴。

**分阶段发布标记**：`draft` / `reviewed` / `validated` / `frozen`（可在 `dataset_status` 使用）；只有通过独立校验及人工复核的样本才能进入正式冻结集。记录复核人及裁决备注时，注意不要公开个人隐私。

### 当前样本的说明

`data/environment/case_1_realhitbench_environment21/` 来自 **RealHiTBench environment21**，目标是新增 `Total` 列（OP2）和三条统计行（OP3）；保留 2011 Total、2010 Totals、Mammal/Primate 分组和正确的多级表头。来源许可标注为 **CC BY-NC 4.0**。此样本 **Gold 已公开**，只作为演示/开发用例，不能计入未来隐藏 Test 评测。

---

本文和 [V2.1 总规范](benchmark_standard_v2.1_zh.md) 一起构成新增样本的标准工作依据。若两份文件不一致，以 V2.1 总规范为原则，并在提交中明确标注需要澄清的边界案例。
