# 本地统计与看板

[English](statistics.md)

Jev Filter 支持本地数值账本和只读浏览器看板。配置后启用，不改变筛选结果、不缓存推理，也不额外运行主模型。

```sh
# 示例单价，请替换成核实过的美元/百万 token 单价。
jev-filter stats configure --model YOUR_MODEL --counter bytes \
  --input-rate 10 --jev-input-rate 0.042 --jev-output-rate 0 \
  --price-source "已核实的价格来源" --price-date 2026-09-23
jev-filter stats report
jev-filter stats dashboard
# 导出独立 HTML 快照，不覆盖已有文件：
jev-filter stats dashboard --html usage.html
```

看板输出带访问令牌的 `127.0.0.1` 地址，启动后自动用默认浏览器打开，按 Ctrl-C 停止服务。服务器/CI 可传 `--no-open`；打开浏览器失败也会保留终端链接和服务。不指定 `--port` 时先尝试 8765，被占用则自动选择空闲端口。显式指定的端口冲突返回 `PortInUse`；`--port 0` 总是选择空闲端口。可手动刷新、按模型、UTC 日期和计数方式筛选，以及导出当前筛选的全部 JSON。卡片、图表和明细采用同一筛选范围；表格显示最近 100 条。无需前端构建、外部脚本或云服务。

## 指标定义

- **估算减少的输入 token**：本次规范化记录 JSON 的 token 数减去实际完整返回包的 token 数，包含元数据和结尾换行，仅计算一次。基线不是原始 shell 字节流，也不证明未筛选时主模型一定读取全部记录；不包括整个对话、后续重读、重试或输出变化。
- **估算输入价值**：减少量 × 配置的主模型输入单价。
- **Jev 成本估算**：实际报告的 Jev 输入/输出用量 × 配置单价。用量不完整时保留未知，不填零。这是按配置价格估算，不是账单。
- **估算净值**：输入价值 − Jev 成本，保留负数。任何所选记录无法计价或比较时，总净值为未知，单独展示可计算行的小计。不完整调用不能贡献正节省。
- **不可比较**：内部 `batch` 仅记录 Jev 用量；它没有可靠的最终主模型消息基线。透传和不完整调用也不计入减少量。

目标模型来自本地配置，**不会自动识别 Codex 或 Claude Code 的实际模型**；更换计价目标时重新配置。每条记录保留当时的价格、日期和来源，后续配置不重算历史。未计算主模型缓存折扣、输出费用变化、税费及订阅额度。

## 计数方式

| 模式 | 行为 |
|---|---|
| `bytes` | 离线 UTF-8 字节数除以 4 向上取整，属于粗估，不是模型分词。 |
| `tiktoken` | 按受支持的模型映射在本地计数；需要 Python `.[stats]` 或包含该依赖的原生包。 |
| `openai` | 显式启用官方输入计数接口，通过 `OPENAI_API_KEY` 将比较的两份文本发给 OpenAI。 |
| `anthropic` | 显式启用官方消息计数接口，通过 `ANTHROPIC_API_KEY` 将两份文本发给 Anthropic。 |

```sh
python -m pip install 'jev-filter[stats]'
jev-filter stats configure --model gpt-5.4 --counter tiktoken --input-rate YOUR_RATE
```

未知模型映射会使配置失败，不会静默套用其他模型的编码。显式传 `--encoding o200k_base` 可选择**代理编码估算**，但不证明目标模型使用该编码。tiktoken 首次使用可能下载公开编码数据，后续读取本地编码数据；这不是语义结果缓存。原生构建包含 tokenizer 依赖。

官方计数模式每次比较顺序调用两次接口，不生成答案、不跟随重定向、不自动重试，会增加网络耗时。缺少 Key、接口错误和计数缺失保留未知，不影响原工具返回。配置文件不保存密钥，仅对允许对应供应商接收的内容启用在线计数。

官方接口计算的是独立消息中的文本，不是完整 Agent 请求。Claude 官方说明预估与实际用量可能略有差异；完整任务的实际节省仍需配对基线和主模型 usage。参考 [OpenAI 计数文档](https://developers.openai.com/api/docs/guides/token-counting) 与 [Claude 计数文档](https://platform.claude.com/docs/en/build-with-claude/token-counting)。

## 覆盖与存储

配置后自动记录 CLI 的 `search`、`query`、`exec`、`code-search`、`locate`、`triage` 和 `batch`。直接调用 Python helper、`read`/`list`、仅规划的调用及统计边界前的错误不在覆盖内。不会自动补记历史节省。

默认目录 `~/.local/share/jev-filter/stats`，可用 `JEV_STATS_DIR` 更改。SQLite 只保存数值、模型/工具名、状态和价格元数据，不保存源码、查询、客户消息、原文档案路径或凭据。事务写入、私有权限；统计故障不会重试原工具。导出的 HTML/JSON 含这些统计信息，应作为私有数据保管。

```sh
jev-filter stats report --model YOUR_MODEL --since 2026-09-01 --until 2026-09-30
jev-filter stats disable                 # 保留历史，停止后续记录
JEV_STATS_DISABLED=1 jev-filter ...      # 跳过本次统计
```

本地 tokenizer、在线计数适配和看板有隔离测试；回归测试不会使用开发者的真实账本或在线计数配置。
