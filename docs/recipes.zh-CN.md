# 按任务选择用法

[English](recipes.md) · [中文文档首页](index.zh-CN.md)

选择配方、写好分析契约，再替换采集器或输入路径。主模型应看到处理后的结果包，而不是先接收全量原文。

## 自定义命令输出

创建 `analysis.json`：

```json
{
  "mode": "filter",
  "context": {
    "scope": "只判断当前请求尝试",
    "success": "保留尚未恢复的建连故障",
    "exclusions": "忽略随后已成功的历史故障"
  },
  "required_context": ["scope", "success", "exclusions"],
  "requirements": [
    {"id":"network","statement":"当前请求在 DNS、TCP 或 TLS 建连阶段失败。","expected":true},
    {"id":"response","statement":"当前请求已收到 HTTP 响应头。","expected":false}
  ],
  "fields": ["source_id", "text", "answers", "source"]
}
```

采集命令应输出这样的 JSON 数组：

```json
[
  {"id":"req-17","text":"收到任何 HTTP 响应前，TLS 校验失败。","request_id":"req-17"},
  {"id":"req-18","text":"之前超时，当前请求已返回 HTTP 200。","request_id":"req-18"}
]
```

```sh
jev-filter exec --analysis analysis.json \
  --task '找出当前请求的网络建连故障' \
  -- your-collector --json
```

`your-collector` 是你已有的采集命令，不由本项目提供。要直接尝试，可将数组保存为
`records.json`，把命令替换为 `cat records.json`。在 `--` 前加 `--plan` 只规划、不推理，
但仍会执行一次采集命令。普通文本按自包含段落拆分；每行有充分上下文时才按行拆分。

## 结合上下文选择

仓库提供 [分析示例](../examples/choose.json) 和 [候选示例](../examples/candidates.json)：

```sh
jev-filter query --input examples/candidates.json \
  --analysis examples/choose.json \
  --task '选择属于 Beta 项目的 JSON 导出'
```

`context` 区分看起来相似的候选。`required_record_fields` 会拦住缺项目或格式信息的竞争候选。
只传真实观察到的元数据；字段存在并不证明内容正确。

## 搜索完整代码符号

```sh
jev-filter code-search 'retry|backoff' --root ./src \
  --task '找出会重试临时网络故障的实现'
```

词法搜索缩小候选，采集器将命中扩展为完整函数或方法。npm 平台包包含 Python 与 JS/TS/Go
解析器。它不是完整语义索引；已知准确符号时直接使用原生 rg 更合适。

## 选择网页控件

使用已有本地 Camofox 服务，以及已观察到的 session/tab ID：

```sh
jev-filter locate --session YOUR_SESSION --tab YOUR_TAB \
  --origin https://example.com \
  --task '选择结算表单中可用的继续按钮'
```

占位符要换成实际值。定位器只观察和校验，不跳转、点击或提交。保留返回 selector 的时效信息，
动作前再次核对。重复或已变化的目标转复核；特定业务的会话限制由原有工作流负责。

## 分流关联事件

```sh
jev-filter triage --input examples/events.jsonl \
  --analysis examples/triage.json \
  --task '找出当前请求的网络建连故障'
```

同一请求按事件顺序归组。历史超时后已成功，不应变成新的未恢复事件。
格式错误和证据不完整的记录保留；标签不能证明实时恢复。

## 自定义输出

用 `questions` 定义 Choice/Noul/Score，用 `output` 进行嵌套投影。
例如已有名为 `intent` 的 Choice 问题，可加入：

```json
{"output":{"record":"source_id","classification":"answers.intent.choice"}}
```

这只是应合并到完整分析规范中的片段，不是独立可运行的分析文件。
更多规则见 [上下文契约](context-contract.zh-CN.md)。
