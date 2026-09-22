<p align="center">
  <img src="docs/assets/hero.svg" alt="Jev Context：程序采集原始结果，结合任务上下文判断，再把证据交给主模型" width="100%">
</p>
<p align="center">
  <a href="README.md">English</a> · <a href="#快速开始">快速开始</a> · <a href="#接入你的-ai">接入 AI</a> · <a href="docs/benchmarks.md">Benchmark</a> · <a href="https://github.com/apixly-ai/jev-context/releases">版本发布</a>
</p>
<p align="center">
  <a href="https://github.com/apixly-ai/jev-context/actions/workflows/ci.yml"><img src="https://github.com/apixly-ai/jev-context/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/apixly-ai/jev-context/releases"><img src="https://img.shields.io/github/v/release/apixly-ai/jev-context?color=12846b" alt="Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-7958d6" alt="MIT"></a>
</p>

**放在工具与主模型之间的语义筛选器。** 在 CLI 内部采集命令输出、搜索结果、网页控件或日志，用 Jev 根据 AI 提供的任务与上下文判断，再返回相关证据和待复核 ID，减少整批原始结果进入主模型上下文。

## 三个核心优势

- **让主模型少读无关内容。** 先筛选再返回，需要时按 ID 取回原文。历史流程的返回上下文减少 **88–97%**。[证据与代价 →](docs/benchmarks.md#historical-prototype-primary-agent-workflow-comparison)
- **减少 Jev 的重复输入开销。** 自动合批，最多 30 个请求并发。公开测试输入 token 减少 **56.5%**，相比单条并发快 **32.4%**。[复现方法 →](docs/benchmarks.md#public-package-measured-2026-09-22)
- **规则由 AI 控制，结果可复核。** 自定义上下文、问题与输出；缺事实保留 `REVIEW`。**8/8 组测试结果正确**，三条已安装流程通过验收。[公开数据](benchmarks/results/2026-09-22-live.json) · [集成证据](benchmarks/results/2026-09-22-migration.json)

适合 **记录多、语义判断重复、标准明确** 的任务。精确路径、ID、selector、计算和少量短结果优先用原生工具；开放推理和写作仍交给主模型。

## 用实测说明收益

![公开 Jev 测试：自动合批减少 56.5% 输入 token，合批加并发比单条并发快 32.4%](docs/assets/batch-benchmark.png)

96 条合成记录，每条两个判断，四种方式各跑两轮，八组结果均符合预期。这是 **Jev 阶段** 的指标，不是主模型整轮任务的加速倍数。[原始数据](benchmarks/results/2026-09-22-live.json) · [方法与复现命令](docs/benchmarks.md)

**整轮费用呢？** 历史主模型 A/B 的冷输入 API 等价费用估算下降 4–25%，但三条流程都慢了 1.5–10.2%。本次独立包迁移的小批量测试也更慢、token 用量不变。这些负面结果均保留在报告里：上下文变短带来节省空间，不等于所有任务必然降本提速。

## 快速开始

**Node.js 22+ · macOS / Linux · npm 发行包不需要另外安装 Python。** Windows 使用 WSL。只有实际推理才需要 TypeSafe Jev API key。

通过 npm 安装：

```sh
npm install -g @apixly/jev-context
jev-context doctor
```


配置 key 后，在**任意目录**运行这个完整例子：

```sh
export TYPESAFE_API_KEY='your-key'

jev-context query --input - --mode choose \
  --task '选择当前仍未恢复的 DNS 故障记录' <<'JSON'
[
  {"id":"a","text":"之前 DNS 失败，现已恢复，请求成功。"},
  {"id":"b","text":"DNS 解析仍失败，无法建立连接。"}
]
JSON
```

预期选中 `b`，以下省略了诊断元数据：

```json
{"selected_ids":["b"],"review_ids":[],"complete":true}
```

小例子用于学习接口；这么短的实际输入通常直接用原生工具更合适。处理真实批量数据时，让 CLI 自己执行采集命令：

```sh
jev-context exec --task '找出尚未恢复的网络故障' \
  --analysis analysis.json -- your-collector --json
```

先复制 [分析契约示例](docs/recipes.md#1-custom-command-output)，再替换采集命令。命令以参数数组透传，不隐式启动 shell。[如何读结果与退出码 →](docs/getting-started.zh-CN.md#读懂结果)

## 接入你的 AI

能执行命令的 AI 都可以接入。不需要再启动一个代理，也不要求先部署 MCP 服务。

**1. 安装配套 skill。** npm 全局安装后，以 Codex 为例：

```sh
mkdir -p ~/.codex/skills
cp -R "$(npm root -g)/@apixly/jev-context/skills/jev-context" ~/.codex/skills/
```

其他 AI 将同一个 skill 放入其支持的目录即可。[Claude Code 与通用工具接入 →](docs/agents.md)

**2. 给 AI 一段明确的使用规则。**

```text
大量记录需要标准明确的语义判断时使用 jev-context。
传入任务、范围、排除条件、成功标准和有来源的已知事实。
让采集→分析→精简输出在一次工具调用内部完成。
复核未确定的 ID，不重复判断已完成项，不再次封装已有 Jev 流程。
精确查询和少量短结果使用原生工具。
```

**3. 把决定答案所需的上下文传进去。** Jev 不会自动继承聊天历史。共享事实放 `context`，各记录的历史随记录传入，用必要字段声明拦住缺信息的请求。问题、筛选、排序和输出投影都由调用者控制。[完整接入指南 →](docs/agents.md) · [上下文契约 →](docs/context-contract.md)

## 按任务选择入口

| 你要处理什么 | 使用 | 示例 |
|---|---|---|
| 自定义命令的大量输出 | `exec` | [采集命令](docs/recipes.md#1-custom-command-output) |
| JSON 候选记录 | `query` | [结合上下文选择](docs/recipes.md#2-select-with-context) |
| 广泛关键词命中的源代码 | `code-search` | [完整代码符号](docs/recipes.md#3-search-whole-code-symbols) |
| 本地 Camofox 页面上的控件 | `locate` | [网页选择](docs/recipes.md#4-find-a-browser-control) |
| 多请求的 JSON/JSONL 日志 | `triage` | [关联事件](docs/recipes.md#5-triage-correlated-events) |
| 已有类型化 Jev 流程 | Python `batch.run` / CLI `batch` | [程序内接入](docs/agents.md#python-workflows) |

[全部参数](docs/cli.md) · [原文复核](docs/getting-started.zh-CN.md#读懂结果) · [架构](docs/architecture.md)

## 我们自己也在用

资料标注、Telegram 维护计划和 SRE 分流已保留原接口，并用真实 Jev 调用、合成数据通过验收。私有身份、密钥和生产数据不进入开源仓库。

- **不使用结果缓存。** 明确上下文、采集边界、失败项和模型用量。
- **受保护的发布。** 必须通过 CI/安全检查，发布标签不可改写，安装包附校验和与来源证明。
- **可复用的内核。** Python library 与 npm CLI；自动合批，最多 30 个在途请求。
- **明确的边界。** 参与推理的输入会发送给 TypeSafe；`exec` 执行你提供的命令，不是沙箱；判断结果不替代操作授权。[安全说明 →](SECURITY.md)

## 参与开发

```sh
git clone https://github.com/apixly-ai/jev-context.git
cd jev-context
python -m venv .venv && . .venv/bin/activate
python -m pip install -e '.[code,dev]'
sh scripts/check.sh
npm test
```

[贡献指南](CONTRIBUTING.md) · [开发与发布](docs/development.md) · [项目治理](GOVERNANCE.md) · [更新记录](CHANGELOG.md) · [报告问题](https://github.com/apixly-ai/jev-context/issues/new/choose)

**Apixly / JIA-ss** 维护 · [MIT](LICENSE) · 独立于 TypeSafe。
