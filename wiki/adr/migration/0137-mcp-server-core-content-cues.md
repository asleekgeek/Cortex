---
title: "ADR-0137 — mcp_server/core/content_cues.py rationale"
status: accepted
source: mcp_server/core/content_cues.py
---

# ADR-0137 — mcp_server/core/content_cues.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 1 (docstring)

````text
Language-aware decision / error / success cue detection (issue #158).
````

## module — original line 3 (docstring)

````text
Pure business logic — no I/O. Single purpose: decide whether memory
content carries a decision, error, or success cue so the write gate can
honor ``bypass_decision`` / ``bypass_error`` and the neuromodulation
success signal regardless of the language the note is written in.
````

## module — original line 8 (docstring)

````text
Detection order and rationale
-----------------------------
1. **Structural markers** (error detector only, checked first): runtime
   artifacts — traceback headers, stack-trace frames, CamelCase
   exception class names, POSIX signal names — are emitted by
   interpreters and runtimes in fixed ASCII form regardless of the
   author's natural language. They are matched case-SENSITIVELY because
   the casing is the signal (``ValueError`` vs. prose "value error").
2. **Multilingual keyword sets**: per-language regex fragments, one
   entry per language, each with a provenance comment listing the
   surface forms it covers. English entries are byte-for-byte the
   pre-#158 patterns, so English behavior is a strict superset of the
   old behavior (no English regressions).
````

## module — original line 22 (docstring)

````text
Language selection (each language must trace to a source):
  - en — original behavior (``_DECISION_KW`` / ``_ERROR_KW`` /
    ``_SUCCESS_KW`` before this module existed).
  - es, pt, ru, ja — the four languages Stack Overflow runs dedicated
    non-English sites for (es/pt/ru/ja.stackoverflow.com), the best
    available demand signal for non-English developer populations.
    source: https://en.wikipedia.org/wiki/Stack_Overflow ("available in
    English, Spanish, Russian, Portuguese, and Japanese").
  - de, fr — remaining top web content languages after the above.
    source: https://w3techs.com/technologies/overview/content_language
    (W3Techs, Usage statistics of content languages for websites).
  - ro — the reporting user's repro language in issue #158.
````

## module — original line 35 (docstring)

````text
Precision/recall trade-off (deliberate, recall-biased): a false
positive here costs one extra stored memory that ``try_curation``
merges/links afterwards (see ``write_gate.determine_bypass`` docstring);
a false negative silently drops a decision/error note as a "duplicate"
(the issue #158 failure). Stems therefore use ``\\w*`` suffixes to cover
inflection, and rare cross-language collisions (noted inline) are
accepted. The ``important``/``critical`` tag and ``force=True`` remain
the universal, language-independent fallback.
````

## module — original line 44 (docstring)

````text
For languages not listed, keyword detection does not fire; structural
error markers still work, and the tag/force fallback always works.

````

## is_decision_cue — original line 254 (docstring)

````text
True when content carries a decision cue in any covered language.
````

## module — original line 55 (comment)

````text
# CPython traceback header — fixed string emitted by the interpreter.
# source: https://docs.python.org/3/library/traceback.html
````

## module — original line 58 (comment)

````text
# CPython traceback frame line: File "app.py", line 3
# source: https://docs.python.org/3/library/traceback.html
````

## module — original line 61 (comment)

````text
# JVM / Node stack frame: "at pkg.Cls.m(File.java:42)" /
# "at fn (/app/x.js:10:5)".
# sources: java.lang.Throwable#printStackTrace javadoc;  # noqa: ERA001
# https://v8.dev/docs/stack-trace-api
````

## module — original line 66 (comment)

````text
# CamelCase exception class identifiers (ValueError,
# NullPointerException) as printed by runtimes.
# sources: PEP 8 (exception names use the suffix "Error");
# Java tutorial/JLS convention (suffix "Exception")
````

## module — original line 71 (comment)

````text
# POSIX signal names printed by shells/runtimes on abnormal exit.
# source: POSIX.1-2017 <signal.h>
````

## module — original line 76 (comment)

````text
# ── Decision cues ──────────────────────────────────────────────────────────
# "made a choice": decide / choose / switch / migrate / select / opt.
````

## module — original line 79 (comment)

````text
# en: verbatim pre-#158 _DECISION_KW (thermodynamics.py) — regression anchor
````

## module — original line 116 (comment)

````text
# ja: 決定 (decision), 決め(た/ました) (decided), 選択 (selection),
#     選ん/選び (chose), 採用 (adopted), 移行 (migrated). No \b — CJK
#     text has no word boundaries; substring match is the correct form.
````

## module — original line 120 (comment)

````text
# ro: (am) decis, decidem, decizie/decizia, (am) ales, alegem,
#     aleasă, optat, optăm, migrat. Issue #158 repro language.
#     Collision note: \bales\b also matches the English plural "ales"
#     (beers) — accepted, see recall-bias rationale in module docstring.
````

## module — original line 132 (comment)

````text
# en: verbatim pre-#158 _ERROR_KW (thermodynamics.py) — regression anchor
````

## module — original line 173 (comment)

````text
# ja: エラー (error), 例外 (exception), 失敗 (failure), バグ (bug),
#     クラッシュ (crash), タイムアウト (timeout),  # noqa: ERA001
#     拒否 (denied/rejected),  # noqa: ERA001
#     壊れ (broken), 不具合 (defect/glitch)  # noqa: ERA001
````

## module — original line 189 (comment)

````text
# en: verbatim pre-#158 _SUCCESS_KW (write_gate.py) — regression anchor
````

## module — original line 225 (comment)

````text
# ja: 修正 (fix), 解決 (resolved), 成功 (success), 完了 (completed),
#     直した/直しました (fixed)  # noqa: ERA001
````

## module — original line 249 (comment)

````text
# Case-sensitive on purpose — casing is the structural signal (see docstring).
````
