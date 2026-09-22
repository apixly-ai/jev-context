# npm 与原生发行包

[English](distribution.md) · [中文文档首页](index.zh-CN.md)

主要安装方式是 `npm install -g @apixly/jev-filter`。Python 用户继续使用 wheel 和 library，
两种方式调用相同的语义内核。

## 打包方式

小型 Node 入口通过 `optionalDependencies` 选择平台包。平台包包含可执行文件、私有 Python
运行时与依赖、代码解析器和固定版本 ripgrep。不修改用户 Python 环境，没有 postinstall 脚本。
平台包发布到 npm，tarball 同时保存在 GitHub Releases。

这个模式参考了 [Codex](https://github.com/openai/codex/blob/main/codex-cli/scripts/build_npm_package.py)
与 [esbuild](https://github.com/evanw/esbuild/blob/main/npm/esbuild/package.json) 的平台依赖设计。

入口保留参数边界、输入输出流与退出状态，不把输入拼成 shell 命令。支持 macOS Intel/Apple Silicon
和 Linux x64/ARM64。Linux 的 Python 运行时需要 glibc，暂不支持 Alpine/musl；Windows 使用 WSL。

## 安装验收

- 安装真实 npm tarball，并禁用生命周期脚本。
- 从 PATH 中移除系统 Python 与 ripgrep。
- 用包内运行时、解析器和 rg 完成 `doctor` 与代码搜索测试。
- 独立运行 Python 3.10–3.14、macOS 的源码测试。
- 对照仓库中固定的上游 SHA-256 校验 ripgrep 下载内容。
- 随平台包附带 Python、启动器和所含依赖的许可证。

原生包改善安装体验，不自动提高语义质量。启动、磁盘占用与下载都有额外成本，不能推导速度收益。

## 发布顺序

1. 版本 PR 通过源码、安全和原生包检查后合并。
2. 在已验证提交创建 `v<version>` 标签；标签不允许改写。
3. GitHub Actions 重建四个平台包、Python 包和 npm 主包，发布校验和与来源证明。
4. 先发布四个平台 tarball，再 `npm publish --access public` 发布主包，不覆盖已有版本。
5. 从 npm Registry 全新安装，验证实际命令。

首次发布可使用已认证的维护者会话。后续可在每个包配置 npm 可信发布者，并启用仓库中的
`publish-npm.yml`，使用 GitHub OIDC，避免长期保存 Registry 密钥。配置完成前不会自行启用。
