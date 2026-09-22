# Benchmarks / 性能与成本

## Public package: measured 2026-09-22

[Machine-readable results](../benchmarks/results/2026-09-22-live.json),
[fixture](../benchmarks/fixture.py), [runner](../benchmarks/run.py).

96 synthetic service records, two atomic predicates each, Jev `jev-1.13.0`,
two repetitions per arm with reversed order on repetition two. No result cache.
Wall time includes planning, network, validation and result restoration, but excludes
launching the Python interpreter and downstream primary-agent reasoning.

| Jev execution | Mean seconds | Input tokens, both repetitions | Exact complete runs |
|---|---:|---:|---:|
| Single-record serial | 39.859 | 139,496 | 2/2 |
| Automatic batching, serial | 2.757 | 60,724 | 2/2 |
| Single-record parallel, cap 30 | 3.502 | 139,496 | 2/2 |
| Automatic batching + parallel, cap 30 | 2.368 | 60,724 | 2/2 |

Batching reduced input tokens **56.47%**. Batch + parallel was **32.37% faster than
single-record parallel** and **94.06% faster than single-record serial** in this run.
All runs returned the expected selected IDs with no unresolved records; usage was
reported complete. The result file retains usage, request counts, workers and timings.
These are API-reported tokens, not estimated character counts.

Two runs are a smoke benchmark, not a statistically powered study. Inputs repeat eight
record patterns and are easier than open-world tasks. Network variation is significant;
serial batching was faster than single-record parallel here. A cap of 30 is an upper
bound, not a claim that every request used 30 workers or that 30 is always optimal.

这里证明的是**同一个 Jev 任务的执行优化**，不是相对于主模型 16 倍加速。
两轮测试不能证明普遍质量；合成记录不代表所有业务数据。所有负面和失败结果
必须保留，不能把少量样本的正确率包装成生产保证。

## Historical prototype: primary-agent workflow comparison

Before this standalone package was extracted, a private prototype was tested on
fixed synthetic code-search, browser-control and incident-triage candidates. Two paired
runs used an Astra/medium primary-agent baseline. The following numeric observations
are historical, not measurements of this release. Private full traces are not shipped
because they contain local environment and agent configuration. They therefore have
less public reproducibility than the fresh benchmark above.

| Prototype workflow | Returned context reduction | Cold API-equivalent cost reduction | Total latency change |
|---|---:|---:|---:|
| Code search | 96.13% | 20.58% | **+10.21% slower** |
| Browser control selection | 88.47% | 4.37% | **+4.02% slower** |
| Incident triage | 97.26% | 25.18% | **+1.52% slower** |

Selected IDs matched the expected answers in these fixtures; the raw triage arm also
returned an extra review. The cost figures include the extra Jev step and the primary
model's observed input/output under the historical cold-token price assumptions.
They are API-equivalent estimates, not subscription bills or evidence of money saved
on this particular account. They are not current provider price quotes.

历史结果说明：上下文可以明显缩短，费用可能下降，但额外判断也可能让整段任务
变慢。本次公开版还没有独立复测主模型端到端价格和质量，因此不承诺这些历史
百分比能在公开版或你的模型上复现。

## Reproduce and price your own workload

```sh
python -m pip install -e '.[code,dev]'
python -m benchmarks.run --output local-results/offline-new.json
# Billable; uses configured Jev credentials and never caches results.
python -m benchmarks.run --live --output local-results/live-new.json
```

Each output path must be new so an old or failed run is not overwritten. The offline
mode measures planning only; it is not evidence of model quality or live latency.

For a downstream agent A/B, keep the primary model, reasoning setting, task, candidate
corpus and expected answers fixed. Alternate raw-native and filtered arms; include
collection, Jev, retries, main-agent continuation and any evidence rereads in elapsed
time and usage. Record incomplete/review/failed runs, exact selection or task success,
false omissions, returned context bytes/tokens and input/output tokens **per model**.
A smaller packet alone is not a quality or cost result.

Use your provider's current prices (including cached-input rates where applicable):

```
raw_cost = main_input * main_input_rate + main_output * main_output_rate
filtered_cost = filtered_main_input * main_input_rate
              + filtered_main_output * main_output_rate
              + jev_input * jev_input_rate + jev_output * jev_output_rate
```

Rates must use the same currency and token unit. Include retries and evidence rereads.
If usage is incomplete, label cost as a lower bound. Report both negative and positive
results. Cheap primary models, small inputs, poor context or frequent rereads can erase
the saving. No fixed dollar claim is inferred from the public model-layer benchmark.

## First-user integration acceptance / 首个用户的集成验收

[Sanitized observations](../benchmarks/results/2026-09-22-migration.json) cover the
maintainer's installed source annotation, Telegram maintenance planning and SRE
routing entrypoints with synthetic data and real Jev calls. All three preserved their
expected decisions and withheld raw input from the compact packet. No message was
sent and no production action was authorized by the test. Existing workflow scripts,
identities and fallback contracts remain private and unchanged.

A separate two-repetition migration A/B used 48 synthetic DNS signals and included
Python process startup: the legacy backend averaged **1.413 s**, the public package
**1.797 s** (**27.2% slower**). Both returned 48/48 correct decisions on each run and
identical usage (6,752 input + 1,913 output tokens per run). No raw signals were in
the returned packet. This small test establishes compatibility, **not a migration
speedup**. The isolated package boundary and transport differ; two runs cannot
attribute the difference to one cause. The privacy-preserving integration bridge
adds a subprocess per whole batch, not per record.

迁移后功能保留，但本次小批量测量没有提速、没有降低模型用量。我们保留这个
负面结果，不把开源封装本身当成性能优化。合批/并发的收益应与迁移成本分别看。
