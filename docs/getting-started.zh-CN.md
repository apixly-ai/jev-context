# 中文使用说明

需要 Linux/macOS、Python 3.10+；代码搜索还需要 `rg`。安装 `code` extra 可解析
JS/TS/Go，Python 使用标准库 AST。原生 Windows 暂不支持，可使用 WSL。

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install 'jev-context[code] @ git+https://github.com/JIA-ss/jev-context.git@v0.1.0'
export TYPESAFE_API_KEY='你自己的密钥'
jev-context doctor
```

`doctor` 默认不联网；`--live` 才会发出一次小额计费测试。也可用
`TYPESAFE_API_KEY_FILE` 指向自己拥有、权限 0600 的普通文件。不要把密钥放进参数或 Git。

原始结果由程序采集和处理，主模型只读取精简结果。`complete=true` 只表示本次输入的
判定已完成，不证明现实世界事实或执行权限；`review_ids`/`NEEDS_CONTEXT` 需要补充
对应证据。不要重复运行可能已经产生副作用的采集命令。

```sh
jev-context query --input examples/records.json --task '找出当前建连失败' --analysis examples/triage.json
jev-context code-search 'session|state' --root src --task '寻找状态持久化实现'
jev-context triage --input examples/events.jsonl --task '找出当前建连失败' --analysis examples/triage.json
```

支持自动合批、连接复用，推理并发上限 30，没有结果缓存。原文保存在本地私有
archive/receipt 中，按 ID 回查。可复现 benchmark、完整命令、调用 skill 与限制
见本仓库英文文档及双语 README。当前提供 GitHub Release 安装包，不假定已上架 PyPI。
