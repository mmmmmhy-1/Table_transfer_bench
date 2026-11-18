# V2.2 新案例组合审查与诊断构造规范

> 本文是现行 V2.2 的补充标准，不改变 OP1–OP7、旧案例 ID、既有 Input/Gold/Evaluator。每个**新案例**必须完成三项组合审查；旧案例允许逐案补标，不强制一次性迁移。

## 一、Core 与 Diagnostic 的不同价值

**Core Benchmark**：真实表格 + 明确可执行的英文业务指令 + 可信最终 Gold + 独立评测器。核心案例不需要能够扁平化为平表，也不必须保存中间 XLSX；不可构造结构对照或中间状态不是拒收理由。它们用于测量真实复杂表格下的端到端成功率、不同结构/规模/领域的覆盖及实际失败情况。

**Diagnostic Subset**：从核心案例中挑选适合的任务，另外提供结构等价输入、单操作对照或中间 Gold，用于解释结构因素、组合能力和错误传播。严格对照和自然复杂表格各有作用；没有控制变量时，不可把跨表性能差异解释成某个结构因素的因果作用。同源变体始终共享 `source_family_id`，不能跨 Train/Dev/Test。

## 二、新案例 OP 与 DAG 审核：三项必须记录的信息

### 1. 依赖类型（每条新案例必须审查）
- **data_dependency**：后续语义目标真正依赖前序目标产生的新业务字段、关系或记录。只对这种**必要语义依赖**填写 `dependency_edges`。
- **ordering_only**：输出呈现要求或参考脚本存在先后顺序，但无独立的语义数据依赖；在审核备注中记录，不将其伪装成 DAG 边。
- **parallel**：各操作能够独立完成，只是在最终工作簿中汇合；`dependency_edges` 可以为空。
- **mixed**：同一案例兼有真正依赖边与独立分支；单操作案例可记录为 `single`。

必须先以 Precondition / Semantic Effect / Invariant / Postcondition 判定 `operations` 和 `operation_nodes`。同一种 OP 可能重复出现，每个节点使用独立 ID。对每条真实 `dependency_edges` 记录来自哪个业务语义产物、为什么下游需要它；不能因脚本先后顺序、先读取后写入或模型的规划顺序强加依赖。审查节点数与最长依赖路径时分开统计。

### 2. 中间语义状态是否可验证（每条新案例必须审查）
- 评估一个或多个 OP 完成后，能否定义**独立于具体 Agent 代码实现、业务上有意义**的正确状态（例如拆分后的字段及源行保留、按键关联后的事实多重集合、完整层级路径、可验证的汇总基础记录）。
- 对合适的检查点，记录 `after_node`、`semantic_result`、`verification_contract`（键、重复项、原值保留、计算精度、层级、空值规则等）和是否已经实际生成文件。
- 如果中间结果具有明确的 Excel 表示，优先在 **Gold 构建时**保存 `diagnostics/intermediate_<node_id>.xlsx`，并用独立规则验证。无需每一个步骤都保存 XLSX，不要将 Python 临时字典、DataFrame 变量或一次 API 调用当作规定的语义检查点。
- 不适合的案例如实标注 `unavailable` / `not_applicable` 并说明原因，不能为了实验强行制造中间 Gold。
- 中间 Gold 只供评测与诊断，**主轨 Agent 从原始 Input 直接提交最终 XLSX**，不要求它提交任何中间文件。

### 3. 是否适合组合诊断（每条新案例必须审查）
- 可合法将完整任务拆为“原始输入→单 OP”“正确中间状态→后续 OP”“原始输入→组合目标”，且拆解后不改变业务含义时，标适合，并计划生成相应诊断指令、输入、Gold 与检查器。
- 无明确依赖、拆分引入业务歧义、中间状态不可独立核验或改变任务语义时，标不适合，并**保留在 Core**。并行任务可以用于整体执行研究，但不当作真实依赖长链的实验样本。
- 单操作与 Oracle 注入实验应在预先确定的样本集上执行，固定模型、工具环境和预算。不能只挑失败运行注入中间答案，再与总体成功率直接比较。
- 记录计划/完成状态：`planned` 表示待构建，`ready` 需要中间 Gold、子任务及评测规则均经过核验；不得宣称尚未创建的文件已经存在。

### 推荐的 Metadata 审核记录

可使用现有 `composition_notes` / `rules` 文字记录，或在新案例写入建议的 `composition_review`：

```json
{
  "operations": ["OP4", "OP6", "OP3"],
  "operation_nodes": [
    {"id": "parse_region_year", "operation": "OP4"},
    {"id": "join_costs", "operation": "OP6", "subtype": "J4", "table_contract": {"...": "follow existing OP6 contract"}},
    {"id": "generate_group_totals", "operation": "OP3"}
  ],
  "dependency_edges": [
    ["parse_region_year", "join_costs"],
    ["join_costs", "generate_group_totals"]
  ],
  "composition_review": {
    "dependency_type": "data_dependency",
    "dependency_rationales": [
      {"from": "parse_region_year", "to": "join_costs", "reason": "The join keys must be recovered from compound fields."},
      {"from": "join_costs", "to": "generate_group_totals", "reason": "Totals use records and costs produced by the join."}
    ],
    "ordering_constraints": [],
    "checkpoint_review": {
      "status": "available",
      "rationale": "Parsed rows have independently checkable region/year and source facts.",
      "checkpoints": [
        {"after_node": "parse_region_year",
         "semantic_result": "Records with separately parsed region and year",
         "verification_contract": "Compare keys, original numeric facts and row multiset"}
      ]
    },
    "diagnostic_review": {
      "suitable": true,
      "status": "planned",
      "rationale": "The parse-only and oracle-to-join subproblems preserve the task semantics."
    }
  }
}
```

此示例只是**局部说明**，OP6 的 `table_contract` 必须在实际案例中使用符合现行 Schema 的完整字段；不得直接复制占位符。建议 `composition_review` 设为旧案例兼容的可选 Schema 属性，但在**新案例人工 SOP 中强制完成**。只有在中间文件真正创建、验证后，才添加相应 `reference_xlsx` 路径。未升级机器 Schema 前，按本文人工审核，不谎称自动验证已实现。

## 三、英语双轨指令和数据案例注意事项

- **Discovery：`instruction.txt`，每条新案例必备**。用英语写清自然业务目标、必须保留或新增的事实、字段/结构、计算规则、单位、空值/零值/重复/除零/舍入、目标文件。不得泄漏不必要的源表坐标、正确行数、Gold 中间值、具体代码或 DAG 执行计划；真实业务必须知道的信息不能刻意隐去。
- **Guided：`instruction_guided.txt`，有诊断价值时同步编写**。在完全相同的任务和输出契约上**只增加输入侧**的表头/数据区/合并范围定位。不能增加新业务约束、指定参考实现、给出正确答案或要求新输出布局。
- 两版共享相同输入与最终 Gold/evaluator，但**分别统计**，主榜只用 Discovery。无可提供的结构定位线索时允许不创建 Guided，说明原因；不必硬凑两个版本。
- **语言表达实验 D 与 Guided 不同**：D 是同一 Discovery 信息量下改变表述，所有版本须有相同合法输出集合；Guided 则增加结构定位信息。
- 指令—Gold—Evaluator 一致：所有显式硬约束都评测；没有要求的装饰样式和坐标不能暗扣。对所有案例做 Gold PASS、错误注入 FAIL、语义等价输出 PASS；修订提示词后不能把旧提示下的实验直接当成新结果。
- 注意来源与许可证；相同原表的结构变体/单操作诊断任务必须共享 `source_family_id`；当前公开 Gold 样例不得当隐藏 Test。现有案例与 ID 不为此次规范变动自动修改。

## 四、推荐目录

```text
data/<domain>/case_<N>_<source>/
  input.xlsx
  instruction.txt
  instruction_guided.txt             # 仅当输入定位诊断有价值
  metadata.json
  gold_output.xlsx
  gold_canonical.json                # 按现有案例规范
  evaluate.py
  README.md
  diagnostics/                       # 适合诊断时可选
    intermediate_<node_id>.xlsx      # 只保存已验证的语义中间 Gold
    intermediate_contracts.json
    instruction_<node_id>.txt        # 单步/Oracle 诊断专用，不是 Guided
```

## 五、新案例的验收清单

- [ ] 来源和原始事实可追溯，记录 OP1–OP7 和 S0–S4，最终 Gold 可验证。
- [ ] `operation_nodes`、`dependency_edges` 完整，依赖/顺序/并行判定有业务语义依据，DAG 无环。
- [ ] 记录中间状态可验证性及理由；有意义、可生成的中间 XLSX 在诊断集保存并检查，不可行不强造。
- [ ] 记录组合诊断适用性及理由，清楚区分计划和已完成，不让诊断文件进入主轨 Agent。
- [ ] 提供英文 Discovery 指令；有价值时提供 Guided，严格保证两版任务与评分一致。
- [ ] Gold、独立评测、错误注入、语义等价正例、来源家族划分与 Prompt 泄漏检查均通过。
- [ ] 对没有中间 Gold 或结构对照的真实复杂案例，仍按 Core Benchmark 的要求独立评审。
