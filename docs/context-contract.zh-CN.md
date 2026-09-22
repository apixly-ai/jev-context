# 上下文与判断契约

[English](context-contract.md) · [中文文档首页](index.zh-CN.md)

Jev 看不到调用者的聊天历史。传入会改变答案的信息：目标、范围、有来源的事实、排除条件、
成功标准和输出要求。共享规则放 `context`；请求、页面或客户自己的历史随对应记录传入。

```json
{
  "mode": "choose",
  "context": {"scope": {"project": "Beta"}, "format": "JSON"},
  "required_context": ["scope.project", "format"],
  "required_record_fields": ["source.project", "source.format"]
}
```

输入记录的元数据放在顶层，例如
`{"id":"b","text":"导出记录","project":"Beta","format":"JSON"}`。
CLI 会将其规范化到 `source`，因此必要路径写 `source.project` 与 `source.format`，
输入不应再额外包一层 `source`。

采集器必须实际提供这些字段。必要的共享值缺失、为空或为 null 时，在采集与推理前返回
`NEEDS_CONTEXT`；`false` 和 `0` 是有效值。某条记录缺少必要字段时保留待复核；唯一选择
还需等待缺上下文的竞争候选。字段存在并不证明值正确，身份和时效仍需独立验证。

## 组合条件

用正向原子 `requirements` 表达每个条件，并通过 `expected` 指定预期真假。Jev 对每项返回
`SUPPORTED`、`CONTRADICTED` 或 `UNKNOWN`。程序规则为：有明确矛盾就排除；否则有未知就复核；
所有条件符合才匹配。不要把生成文本当成可执行逻辑。

## 自定义问题与输出

`questions` 支持 Choice、Noul、Score。`filter` 和 `review` 指定问题，并使用 `in`、`min`、`max`
判断；`order` 可设置类别顺序 `values` 或数值降序 `descending`。

`fields` 选择行字段，`output` 将自定义嵌套键映射到 `answers.intent.choice` 等路径，不执行模板代码。
默认只显示精简答案，完整分布保留在本地凭据中；记录身份和决策状态不能隐藏。

`format` 支持 `json`、`jsonl`、`text`。分析规范最多 16,000 字符，问题或原子条件最多 16 项。
自动合批按完整请求大小规划，而不是只按原文长度截断。

编辑器结构提示见 [JSON Schema](../schemas/analysis.schema.json)。运行时还验证跨字段约束，
必要上下文检查也以运行时为准。结构合法不等于条件符合业务含义。[完整配方](recipes.zh-CN.md)。
