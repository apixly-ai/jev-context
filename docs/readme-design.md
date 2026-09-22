# README design notes

[简体中文](readme-design.zh-CN.md)

The README answers five questions in order: what is it, why should I use it, what
proves that, how do I try it, and how do I connect it to my agent?

References reviewed for this redesign:

- [uv README](https://github.com/astral-sh/uv/blob/main/README.md): concise positioning,
  an early benchmark graphic, highlights, then installation and focused examples.
- [bat README](https://github.com/sharkdp/bat/blob/master/README.md): visual demonstrations
  beside features and practical platform-specific installation information.
- [GitHub README guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes): introduce purpose, usefulness and getting started;
  keep detailed reference material in separate documents.
- [GitHub image/link syntax](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax): relative repository assets keep images attached to the corresponding branch.

Our design uses an original workflow illustration, data-derived charts, three
advantage/evidence rows and one runnable example. Every metric is linked to its
scope and data. Historical trade-offs remain visible. Images have descriptive alt
text; important numbers also appear as text/tables. The project does not borrow
another project's artwork or imply its performance applies here.

Charts: `python scripts/render_assets.py` after installing `.[docs]`.
The hero is repository-owned SVG; the statistical charts use Matplotlib. PNGs work
across GitHub renderers and SVG sources remain available for revision.
