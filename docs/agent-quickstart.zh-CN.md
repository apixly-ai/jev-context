# 面向 agent 的快速接入

[English](agent-quickstart.md) · [完整接入参考](agents.zh-CN.md)

**一次工具调用，返回精简证据包。** AI 提供任务和上下文，Jev Filter 在程序内采集并判断；
主模型负责规划、开放推理和未确定证据。

## 第一步：安装

```sh
npm install -g @apixly/jev-filter
jev-filter doctor
```

在 AI 实际执行工具的环境配置 `TYPESAFE_API_KEY` 或 `TYPESAFE_API_KEY_FILE`，不要把凭据放进提示词。
安装配套 skill：

```sh
mkdir -p ~/.codex/skills
cp -R "$(npm root -g)/@apixly/jev-filter/skills/jev-filter" ~/.codex/skills/
```

Claude Code 使用 `~/.claude/skills/`。已有定制时先检查合并。安装包不会自动改写全局指令。

## 第二步：明确什么时候调用

| 任务 | 使用方式 |
|---|---|
| 精确路径、ID、字段、selector、计算 | 原生工具或确定性程序 |
| 大量记录、标准明确、重复语义判断 | Jev Filter |
| 规划、写作、开放推理 | 主模型 |
| 已有流程内部已经用了 Jev | 直接调用流程，不重复筛选 |

## 第三步：提供精简而充分的上下文

保存为 `analysis.json`：

```json
{
  "mode": "choose",
  "context": {"project": "Beta", "format": "JSON"},
  "required_context": ["project", "format"],
  "required_record_fields": ["source.project", "source.format"]
}
```

运行完整例子：

```sh
jev-filter query --input - --analysis analysis.json \
  --task '选择与上下文中项目和格式匹配的导出' <<'JSON'
[
  {"id":"a","text":"导出记录","project":"Alpha","format":"JSON"},
  {"id":"b","text":"导出记录","project":"Beta","format":"JSON"},
  {"id":"c","text":"导出记录","project":"Beta","format":"CSV"}
]
JSON
```

预期为 `selected_ids=["b"]`、`review_ids=[]`、`complete=true`。接入真实采集器时改用
`exec ... -- YOUR_COMMAND ARGS`，见 [命令配方](recipes.zh-CN.md)。采集应在工具内部完成，
不要先把原文倒进主模型聊天。

## 第四步：使用结果并处理不确定项

- 已完成的类型化判断按原条件使用，不重复让主模型逐条再分类。
- 有 `review_ids` 或 `complete=false` 时，只复核必要原文。
- 退出码 **2** 仍有结构化结果，不要直接丢弃。
- 回读：`jev-filter read ARCHIVE_PATH --id SOURCE_ID`。
- 权限、身份、时效和执行结果继续由原工作流验证。

Jev 不继承聊天历史。提供相关且有来源的事实，各记录自己的历史随记录传入；缺事实保留不确定。
自动合批、最多 30 个并发请求，不用结果缓存。[上下文详细说明](context-contract.zh-CN.md)。

旧命令 `jev-context` 和 Python 的 `jev_context` 导入继续兼容。
新 Python 集成使用 `from jev_filter.batch import run`。
