"""Render repository-owned diagrams and data-derived benchmark charts."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets"
OUT.mkdir(exist_ok=True)
INK = "#122039"
MUTED = "#64748b"
MINT = "#12846b"
PURPLE = "#7958d6"
AMBER = "#b66515"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 12,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.spines.bottom": False,
        "text.color": INK,
        "axes.labelcolor": MUTED,
        "xtick.color": MUTED,
        "ytick.color": INK,
        "figure.facecolor": "#f8fafc",
        "axes.facecolor": "#f8fafc",
        "svg.fonttype": "none",
    }
)
data = json.loads((ROOT / "benchmarks/results/2026-09-22-live.json").read_text())
names = ["single_serial", "batch_serial", "single_parallel", "batch_parallel"]
labels = ["Single · serial", "Batch · serial", "Single · parallel", "Batch + parallel"]
colors = ["#cbd5e1", PURPLE, "#94a3b8", MINT]
fig, axes = plt.subplots(1, 2, figsize=(13, 5.3), gridspec_kw={"width_ratios": [1.2, 1]})
fig.subplots_adjust(left=0.16, right=0.95, top=0.7, bottom=0.2, wspace=0.35)
fig.text(0.055, 0.91, "Less repeated input. Faster batched work.", fontsize=23, weight="bold")
fig.text(
    0.055,
    0.84,
    "Public Jev benchmark · 96 records × 2 predicates · 2 repetitions per arm",
    fontsize=12,
    color=MUTED,
)
for ax, key, divisor, title, limit, suffix in [
    (axes[0], "mean_ms", 1000, "Mean elapsed time", 46, "s"),
    (axes[1], "known_input_tokens", 1000, "Input tokens · both repetitions", 162, "k"),
]:
    vals = [data["summary"][name][key] / divisor for name in names]
    ax.barh(range(4), vals, color=colors, height=0.55)
    ax.invert_yaxis()
    ax.set_yticks(range(4), labels if ax == axes[0] else [""] * 4)
    ax.tick_params(axis="both", length=0)
    ax.set_xlim(0, limit)
    ax.set_title(title, loc="left", fontsize=13, pad=15, weight="bold")
    ax.set_axisbelow(True)
    ax.xaxis.grid(color="#e2e8f0")
    ax.set_xticks([0, 20, 40] if suffix == "s" else [0, 70, 140])
    for i, v in enumerate(vals):
        ax.text(
            v + limit * 0.025,
            i,
            f"{v:.2f}{suffix}" if suffix == "s" else f"{v:.1f}{suffix}",
            va="center",
            fontsize=12,
            weight="bold",
        )
fig.text(
    0.055, 0.09, "56.5% fewer input tokens with batching", color=MINT, weight="bold", fontsize=14
)
fig.text(
    0.54, 0.09, "32.4% faster vs single-record parallel", color=MINT, weight="bold", fontsize=14
)
fig.text(
    0.055,
    0.035,
    "8/8 exact runs · no result cache · cap 30 · Jev-stage measurement, not whole-agent speedup",
    fontsize=10,
    color=MUTED,
)
fig.savefig(OUT / "batch-benchmark.png", dpi=180)
fig.savefig(OUT / "batch-benchmark.svg")
plt.close(fig)
fig, axes = plt.subplots(1, 3, figsize=(13, 4.9))
fig.subplots_adjust(left=0.14, right=0.95, top=0.68, bottom=0.2, wspace=0.4)
fig.text(
    0.055,
    0.91,
    "Smaller context. Potential savings. A latency trade-off.",
    fontsize=21,
    weight="bold",
)
fig.text(
    0.055,
    0.83,
    "Historical private prototype · 3 fixed synthetic workflows · 2 paired runs · not this release",
    fontsize=11,
    color=MUTED,
)
for ax, vals, title, col in zip(
    axes,
    [[96.13, 88.47, 97.26], [20.58, 4.37, 25.18], [10.21, 4.02, 1.52]],
    ["Context reduction", "Cold API cost reduction", "Extra elapsed time"],
    [MINT, PURPLE, AMBER],
):
    ax.barh(range(3), vals, color=col, height=0.5)
    ax.invert_yaxis()
    ax.set_yticks(
        range(3), ["Code search", "Browser locate", "Log triage"] if ax == axes[0] else [""] * 3
    )
    ax.set_title(title, loc="left", fontsize=12, weight="bold", pad=15)
    ax.tick_params(length=0)
    ax.set_xlim(0, max(vals) * 1.38)
    for i, v in enumerate(vals):
        ax.text(v + max(vals) * 0.04, i, f"{v:.1f}%", va="center", weight="bold")
    ax.set_axisbelow(True)
    ax.xaxis.grid(color="#e2e8f0")
fig.text(
    0.055,
    0.09,
    "Cost = historical API-equivalent estimate. All three workflows were slower.",
    fontsize=12,
    color=AMBER,
    weight="bold",
)
fig.text(
    0.055,
    0.035,
    "Private raw traces are not published. See the report for scope and reproducibility limits.",
    fontsize=10,
    color=MUTED,
)
fig.savefig(OUT / "workflow-tradeoffs.png", dpi=180)
fig.savefig(OUT / "workflow-tradeoffs.svg")
plt.close(fig)
hero = """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="420" viewBox="0 0 1200 420" role="img" aria-labelledby="title desc">
<title id="title">jev-context</title><desc id="desc">Capture tool output, apply task-aware Jev judgments, deliver evidence to the agent. Originals stay available locally.</desc>
<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#101b2b"/><stop offset="1" stop-color="#192442"/></linearGradient><linearGradient id="accent"><stop stop-color="#83e3c4"/><stop offset="1" stop-color="#a6a0ff"/></linearGradient></defs>
<rect width="1200" height="420" rx="22" fill="url(#bg)"/>
<circle cx="1100" cy="0" r="240" fill="#8074df" opacity=".065"/>
<g font-family="Arial,Helvetica,sans-serif">
<text x="55" y="52" fill="#8eacc8" font-size="14" letter-spacing="3">TASK-AWARE TOOLS FOR AI AGENTS</text>
<text x="52" y="128" fill="#f4f8ff" font-size="68" font-weight="700">jev<tspan fill="#8ce1c6">-context</tspan></text>
<text x="55" y="173" fill="#c5d2e5" font-size="23">Filter tool output before it reaches your agent.</text>
<rect x="55" y="222" width="270" height="113" rx="13" fill="#23314a" stroke="#3a4a66"/>
<text x="77" y="254" fill="#9aacbf" font-size="13" letter-spacing="1.5">01 / CAPTURE</text>
<text x="77" y="286" fill="#f3f7ff" font-size="23" font-weight="600">Tools &amp; records</text>
<text x="77" y="311" fill="#9aacbf" font-size="16">Commands · code · DOM · logs</text>
<path d="M337 277 H419 m-9 -8 9 8 -9 8" stroke="#83e3c4" stroke-width="2" fill="none"/>
<rect x="433" y="222" width="295" height="113" rx="13" fill="#173b3c" stroke="#518f81"/>
<text x="455" y="254" fill="#8fe4c8" font-size="13" letter-spacing="1.5">02 / JUDGE</text>
<text x="455" y="286" fill="#f3f7ff" font-size="23" font-weight="600">Jev + your context</text>
<text x="455" y="311" fill="#a4c8c2" font-size="16">Typed decisions · batch · parallel</text>
<path d="M740 277 H822 m-9 -8 9 8 -9 8" stroke="#aba6f3" stroke-width="2" fill="none"/>
<rect x="838" y="222" width="307" height="113" rx="13" fill="#2c2d4e" stroke="#66628b"/>
<text x="860" y="254" fill="#b9b2fa" font-size="13" letter-spacing="1.5">03 / REASON</text>
<text x="860" y="286" fill="#f3f7ff" font-size="23" font-weight="600">Evidence for the agent</text>
<text x="860" y="311" fill="#b7b7d0" font-size="16">Relevant records + unresolved IDs</text>
<text x="55" y="383" fill="#91a5bd" font-size="16">Originals retained locally</text><text x="433" y="383" fill="#91a5bd" font-size="16">Up to 30 concurrent requests</text><text x="838" y="383" fill="#91a5bd" font-size="16">No result cache</text>
</g></svg>"""
(OUT / "hero.svg").write_text(hero)
print("Rendered hero and benchmark charts from checked-in data.")
