"""Derive aggregate JSON, CSV, Markdown tables and localized plots from recorded runs."""

import csv
import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "benchmarks/results/2026-09-23-operations.json"
data = json.loads(path.read_text(encoding="utf-8"))
summary = []
for model in data["models"]:
    for case in ("code-search", "locate", "triage", "exec"):
        item = {"model": model, "case": case}
        for arm in ("raw", "filtered"):
            rows = [
                r
                for r in data["rows"]
                if r["model"] == model and r["case"] == case and r["arm"] == arm
            ]
            times = [r["elapsed_ms"] for r in rows if r.get("valid")]
            contexts = [
                r["tool_output_chars"] for r in rows if r.get("tool_output_chars") is not None
            ]
            item[arm] = {
                "runs": len(rows),
                "valid_runs": sum(r.get("valid", False) for r in rows),
                "selection_correct": sum(r.get("selection_correct", False) for r in rows),
                "complete_correct": sum(r.get("exact", False) for r in rows),
                "review_runs": sum(r.get("needs_review", True) for r in rows),
                "false_positive_count": sum(len(r.get("false_positive_ids", [])) for r in rows),
                "false_negative_count": sum(len(r.get("false_negative_ids", [])) for r in rows),
                "mean_ms": statistics.mean(times),
                "median_ms": statistics.median(times),
                "min_ms": min(times),
                "max_ms": max(times),
                "mean_context_chars": statistics.mean(contexts),
                "context_measurements": len(contexts),
                "mean_cold_usd": statistics.mean(r["cold_api_equivalent_usd"] for r in rows),
                "mean_adjusted_usd": statistics.mean(
                    r["cache_adjusted_api_equivalent_usd"] for r in rows
                ),
                "main_tokens": {
                    k: sum(r["main_usage"].get(k, 0) for r in rows)
                    for k in ("input_tokens", "cached_input_tokens", "output_tokens")
                },
                "jev_tokens": {
                    k: sum(r["jev_usage"].get(k, 0) for r in rows)
                    for k in ("input_tokens", "output_tokens")
                },
                "usage_complete": all(r["usage_complete"] for r in rows),
            }
        a, b = item["raw"], item["filtered"]
        item.update(
            context_reduction_pct=100 * (1 - b["mean_context_chars"] / a["mean_context_chars"]),
            cold_cost_reduction_pct=100 * (1 - b["mean_cold_usd"] / a["mean_cold_usd"]),
            adjusted_cost_reduction_pct=100 * (1 - b["mean_adjusted_usd"] / a["mean_adjusted_usd"]),
            latency_change_pct=100 * (b["mean_ms"] / a["mean_ms"] - 1),
        )
        summary.append(item)
(ROOT / "benchmarks/results/2026-09-23-operations-summary.json").write_text(
    json.dumps({"scope": data["scope"], "pricing": data["pricing"], "rows": summary}, indent=2)
    + "\n",
    encoding="utf-8",
)
with (ROOT / "benchmarks/results/2026-09-23-operations.csv").open(
    "w", newline="", encoding="utf-8"
) as stream:
    columns = [
        "model",
        "case",
        "arm",
        "repeat",
        "valid",
        "selection_correct",
        "exact",
        "needs_review",
        "elapsed_ms",
        "tool_output_chars",
        "tool_output_measurement_complete",
        "cold_api_equivalent_usd",
        "cache_adjusted_api_equivalent_usd",
        "usage_complete",
        "main_input_tokens",
        "main_cached_input_tokens",
        "main_output_tokens",
        "jev_input_tokens",
        "jev_output_tokens",
    ]
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    for row in data["rows"]:
        flat = {key: row.get(key) for key in columns}
        for source, prefix in [("main_usage", "main"), ("jev_usage", "jev")]:
            for key, value in row[source].items():
                if prefix + "_" + key in columns:
                    flat[prefix + "_" + key] = value
        writer.writerow(flat)
colors = {"good": "#12846b", "bad": "#b66515"}
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "svg.fonttype": "none",
        "font.size": 11,
        "figure.facecolor": "#f8fafc",
        "axes.facecolor": "#f8fafc",
        "text.color": "#122039",
        "xtick.color": "#64748b",
        "ytick.color": "#122039",
    }
)
for locale in ("en", "zh-CN"):
    cn = locale == "zh-CN"
    if cn:
        available = {f.name for f in font_manager.fontManager.ttflist}
        font = next(
            name
            for name in ("Noto Sans CJK SC", "PingFang SC", "Arial Unicode MS")
            if name in available
        )
        plt.rcParams["font.family"] = font
    fig, axes = plt.subplots(1, 3, figsize=(13, 7.2), gridspec_kw={"width_ratios": [1, 1, 1.2]})
    fig.subplots_adjust(left=0.15, right=0.97, top=0.75, bottom=0.17, wspace=0.4)
    fig.text(
        0.05,
        0.93,
        "整段任务实测：收益取决于模型与场景"
        if cn
        else "Whole-operation results: gains depend on the workload.",
        fontsize=21,
        weight="bold",
    )
    fig.text(
        0.05,
        0.865,
        "2 个主模型 · 4 类场景 · 原生与筛选各 3 轮 · 共 48 次运行"
        if cn
        else "2 primary models · 4 scenarios · 3 runs per arm · 48 real agent operations",
        fontsize=12,
        color="#64748b",
    )
    tasks = (
        {"code-search": "代码", "locate": "网页", "triage": "日志", "exec": "命令"}
        if cn
        else {"code-search": "Code", "locate": "Browser", "triage": "Logs", "exec": "Command"}
    )
    labels = [
        ("Astra" if "astra" in r["model"] else "Luna") + " · " + tasks[r["case"]] for r in summary
    ]
    specs = [
        ("context_reduction_pct", "上下文减少" if cn else "Less tool output", True),
        ("cold_cost_reduction_pct", "冷输入等价费用下降" if cn else "Lower cold API cost", True),
        ("latency_change_pct", "平均耗时变化" if cn else "Mean latency change", False),
    ]
    for index, (key, title, positive_good) in enumerate(specs):
        ax = axes[index]
        values = [r[key] for r in summary]
        ax.barh(
            range(8),
            values,
            height=0.55,
            color=[colors["good"] if (v >= 0) == positive_good else colors["bad"] for v in values],
        )
        ax.invert_yaxis()
        ax.set_yticks(range(8), labels if index == 0 else [""] * 8)
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.axvline(0, color="#cbd5e1", linewidth=1)
        ax.set_axisbelow(True)
        ax.xaxis.grid(color="#e2e8f0")
        ax.set_title(title, loc="left", fontweight="bold", fontsize=12, pad=15)
        ax.set_xlim((-6, 120) if index == 0 else (-4, 27) if index == 1 else (-9, 57))
        for i, value in enumerate(values):
            label = f"{value:+.1f}%" if index == 2 else f"{value:.1f}%"
            ax.text(
                max(0, value) + (0.8 if index == 1 else 1.2),
                i,
                label,
                va="center",
                fontsize=10,
                weight="bold",
            )
        ax.axhline(3.5, color="#cbd5e1", linewidth=0.8, linestyle="--")
    fig.text(
        0.05,
        0.09,
        "ID 选择正确 48/48 · 原生 4 次需复核 · 筛选 0 次需复核 · 未发现错误增删 ID"
        if cn
        else "48/48 correct ID sets · Raw: 4 review runs · Filtered: 0 · No observed false additions/omissions",
        fontsize=11,
        color="#122039",
    )
    fig.text(
        0.05,
        0.035,
        "费用为官方单价折算，非订阅账单；小样本，含变慢/变贵结果。2 条上下文长度缺测，未填补。"
        if cn
        else "API-equivalent prices, not subscription bills. Small sample; regressions retained. 2 context lengths missing.",
        fontsize=9,
        color="#64748b",
    )
    suffix = ".zh-CN" if cn else ""
    fig.savefig(ROOT / f"docs/assets/operations{suffix}.png", dpi=180)
    fig.savefig(ROOT / f"docs/assets/operations{suffix}.svg")
    plt.close(fig)
for locale in ("en", "zh-CN"):
    cn = locale == "zh-CN"
    lines = []
    lines += [
        "| 主模型 | 场景 | 上下文减少 | 冷输入等价费用变化 | 耗时变化 | 原生/筛选无复核完成 |"
        if cn
        else "| Primary model | Scenario | Context reduction | Cold API cost change | Latency change | Raw/filtered complete |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in summary:
        model = "Astra" if "astra" in row["model"] else "Luna"
        scenario = (
            {
                "code-search": "代码搜索",
                "locate": "网页定位",
                "triage": "日志分流",
                "exec": "自定义命令",
            }[row["case"]]
            if cn
            else row["case"]
        )
        lines.append(
            f"| {model} | {scenario} | {row['context_reduction_pct']:.1f}% | {-row['cold_cost_reduction_pct']:+.1f}% | {row['latency_change_pct']:+.1f}% | {row['raw']['complete_correct']}/3 → {row['filtered']['complete_correct']}/3 |"
        )
    (ROOT / f"benchmarks/results/operations-table.{locale}.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
print("Generated operation summary, CSV, localized charts and tables.")
