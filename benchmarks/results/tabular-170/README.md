# Tabular response encoding — token-delta measurement (issue #170)

Reproduce: `PYTHONPATH=. python3 benchmarks/tabular_170/measure.py`

## Gate

Issue #170: on a fixed recall corpus, tabular encoding that cuts serialized
size by **≥ 25%** vs current JSON → ship tabular as the default; otherwise keep
it an opt-in `format` param. See `MANIFEST.json` for sha/date/method and
`result.json` for the full numbers.

## Result

Corpus: `benchmarks/longmemeval/longmemeval_s.json` haystack turns as recall
memory bodies, 100 queries × 10 memories, recall's real field set (id, content,
score, heat, domain, tags, created_at, source). Size = `serialized_length`
(host char count); tokens = chars/4 (host estimator).

| Encoding | chars | tokens (est) |
|---|---|---|
| JSON | 1,146,694 | 286,674 |
| tabular | 1,086,994 | 271,749 |
| **reduction** | **5.21%** | **5.21%** |

**Decision: opt-in.** 5.21% ≪ 25%, so tabular is an opt-in `format: "tabular"`
param; the default stays `format: "json"`.

## Why so much smaller than AP's 48%

Tabular's saving is the fixed field-name overhead removed per item; its
*fraction* of the payload falls as content grows. AP's 48% was on short symbol
rows (`qualified_name`/`kind`/`score`) that are almost entirely field names.
Cortex recall memories carry long prose bodies (fixture median ~376 chars), so
the content dominates and the field-name dedup is a small fraction.

Sensitivity sweep (10 memories, uniform content length):

| content chars | JSON chars | tabular chars | reduction |
|---|---|---|---|
| 24 | 2248 | 1651 | 26.56% |
| 48 | 2488 | 1891 | 24.00% |
| 96 | 2968 | 2371 | 20.11% |
| 192 | 3928 | 3331 | 15.20% |
| 384 | 5848 | 5251 | 10.21% |
| 768 | 9688 | 9091 | 6.16% |

Tabular only crosses 25% for heavily-truncated (~24-char) content. The opt-in
param exists precisely for that regime — a wide sweep where the caller has
budget-truncated memories and wants the field-name overhead gone — while normal
recall keeps the richer, self-describing JSON default.
