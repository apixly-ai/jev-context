# jev-context

[English](README.md) | [简体中文](README.zh-CN.md)

**先在程序内部筛选工具结果，再把相关证据交给主模型。**

`jev-context` 在程序内采集命令输出、搜索候选、网页控件或事件记录，用 Jev 根据主模型提供的任务和上下文进行明确的语义判断。主模型收到筛选后的证据、待复核 ID 和用于查看原文的本地凭据。

支持 AI 自定义分析指令、类型化问题、输出投影、自动合批、最多 **30** 个并发请求；**不使用结果缓存**。由 JIA-ss 维护的独立开源项目，并非 TypeSafe 官方产品。

## 什么时候有效？

适合大量记录中重复、标准明确的语义判断。精确 ID、路径、selector、计算和少量短结果优先使用原生工具；规划、开放推理和写作由主模型承担。

额外调用也会增加费用和延迟。收益取决于减少多少输入、主模型价格，以及上下文是否充分；**不保证所有任务都更便宜或更快**。

[Benchmark 报告](docs/benchmarks.md) 区分公开版本实测与历史原型数据，保留负面结果，并提供可复现脚本。上下文压缩比例不能直接当作整轮成本下降比例。

## 安装

需要 Python 3.10+，支持 Linux/macOS；Windows 使用 WSL。搜索功能还需要 ripgrep。

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install 'jev-context[code] @ git+https://github.com/JIA-ss/jev-context.git@v0.1.0'
export TYPESAFE_API_KEY='your-key'
jev-context doctor
```

也可以安装 [Release](https://github.com/JIA-ss/jev-context/releases) 中的 wheel。目前没有发布到 PyPI。推理需要 Jev API key；`doctor` 和 `--plan` 不需要。推荐用 `TYPESAFE_API_KEY_FILE` 指定仅当前用户可读的密钥文件。

## 使用

```sh
jev-context query --input examples/candidates.json --analysis examples/choose.json --task 'Select the matching project' --plan
jev-context exec --task 'Find unresolved network failures' --analysis examples/triage.json -- cat examples/records.json
jev-context triage --input examples/events.jsonl --task 'Find unresolved network failures' --analysis examples/triage.json
```

还提供 `search`、`code-search`、`locate`、类型化 `batch`、原文 `read/list`。参见 [CLI 参数](docs/cli.md)、[中文入门](docs/getting-started.zh-CN.md)。`exec` 会执行调用者提供的命令，不是沙箱。

## 接入 AI

把 [配套 skill](skills/jev-context/SKILL.md) 放入 AI 的 skill 目录，并按 [接入指南](docs/agents.md) 配置使用时机。安装包不会自行改写全局配置。

调用时提供目标、范围、排除条件、成功标准和有来源的已知事实；每条记录自己的历史放在记录里。声明 `required_context` 和 `required_record_fields`，缺信息时转待复核。分析内容、类型化问题和输出投影都由调用者通过 [上下文契约](docs/context-contract.md) 控制。

原文以受限权限保存在本地，参与判断的输入会发送到固定的 TypeSafe API。未知、失败和格式错误的记录仍然可见。语义判断不能替代操作授权。参见 [安全边界](SECURITY.md)。

## 开发和验证

```sh
python -m pip install -e '.[code,dev]'
sh scripts/check.sh
# 可选、产生 API 费用：两轮，交替测试顺序，不用缓存。
python -m benchmarks.run --live --output local-results/my-live-run.json
```

配套测试、构建检查、依赖审计、CodeQL、贡献流程、安全报告入口和带校验和/来源证明的版本发布。参见 [贡献](CONTRIBUTING.md)、[开发流程](docs/development.md)、[治理](GOVERNANCE.md)、[更新记录](CHANGELOG.md) 和 [MIT 许可证](LICENSE)。

我们自己是第一个用户。私有业务流程、生产数据、身份和密钥不进入开源仓库；本机集成验收与公开合成 benchmark 分开记录。
