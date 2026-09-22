# README 设计依据

[English](readme-design.md) · [中文文档首页](index.zh-CN.md)

首页依次回答：是什么、为什么用、证据是什么、如何尝试、怎样接入 AI。

本次研究参考：

- [uv](https://github.com/astral-sh/uv/blob/main/README.md)：简洁定位、提前展示性能图、突出优势，再给安装和聚焦示例。
- [bat](https://github.com/sharkdp/bat/blob/master/README.md)：在功能旁展示效果图，提供实用安装说明。
- [GitHub README 指南](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)：说明项目用途、价值与入门路径，详细参考拆到独立文档。
- [GitHub 图片与链接说明](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax)：仓库相对资源与所在分支保持一致。

首页使用自制流程图、实测图表、三项优势和完整示例。每个数字都标明数据与适用范围，
负面结果可见。图片有替代文本，关键数字也以正文或表格呈现。没有复制其他项目图片，
也没有把其他项目的性能结论套用到本项目。

中英文页面和配图分别维护。安装 `.[docs]` 后运行 `python scripts/render_assets.py` 生成图表；
流程图为 SVG，统计图由 Matplotlib 绘制，提供 PNG 与 SVG。
