"""Controlled RRF-vs-TMM fusion ablation on LoCoMo.

source: ADR-0847"""

from __future__ import annotations

import json
import sys
from collections import defaultdict

sys.path.insert(0, "/Users/cdeust/Documents/Developments/personal/Cortex")

from mcp_server.core.scoring import (
    compute_bm25_scores,
    compute_keyword_overlap,
    compute_ngram_score,
)
from mcp_server.core.query_intent import classify_query_intent, QueryIntent

# source: ADR-0847

import importlib.util as _ilu

_fusion_path = (
    "/Users/cdeust/Documents/Developments/personal/Cortex/benchmarks/lib/fusion.py"
)
_spec = _ilu.spec_from_file_location("_cortex_fusion", _fusion_path)
_fusion = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_fusion)
wrrf_fuse = _fusion.wrrf_fuse

from benchmarks.locomo.data import (  # noqa: E402
    load_locomo,
    parse_evidence_refs,
    extract_sessions,
    CATEGORY_NAMES,
)
import os  # noqa: E402

DATA_PATH = "/Users/cdeust/Documents/Developments/personal/Cortex/benchmarks/locomo/locomo10.json"  # noqa: E501 — source: ADR-0847

# source: ADR-0847
_RECALL_AT_10_K = 10

# source: ADR-0847


SIGNAL_MIN = {"vector": 0.0, "keyword": 0.0, "ngram": 0.0, "bm25": 0.0, "recency": 0.0}


def tmm_fuse(signal_results, signal_weights):
    """Weighted theoretical-min-max score fusion.

    source: ADR-0847
    """
    scores = defaultdict(float)
    for name, results in signal_results.items():
        w = signal_weights.get(name, 0.0)
        if w <= 0 or not results:
            continue
        m = SIGNAL_MIN.get(name, 0.0)
        hi = max((s for _, s in results), default=0.0)
        denom = max(hi - m, 1e-3)
        for doc_id, raw in results:
            scores[doc_id] += w * (raw - m) / denom
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def build_embeddings(model, sessions):
    texts = [s["content"][:2000] for s in sessions]
    return model.encode(texts, show_progress_bar=False, normalize_embeddings=True)


def score_vector(model, embeddings, query):

    q = model.encode([query[:500]], normalize_embeddings=True)[0]
    sims = embeddings @ q
    scored = [(i, max(0.0, float(s))) for i, s in enumerate(sims)]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def compute_signals(model, embeddings, sessions, query):
    docs = [s["content"] for s in sessions]
    intent_info = classify_query_intent(query)
    intent = intent_info["intent"]
    is_update = intent == QueryIntent.KNOWLEDGE_UPDATE

    signals = {
        "vector": score_vector(model, embeddings, query),
        "keyword": sorted(
            [(i, compute_keyword_overlap(query, d)) for i, d in enumerate(docs)],
            key=lambda x: x[1],
            reverse=True,
        ),
        "ngram": sorted(
            [(i, compute_ngram_score(query, d)) for i, d in enumerate(docs)],
            key=lambda x: x[1],
            reverse=True,
        ),
        "bm25": sorted(
            list(enumerate(compute_bm25_scores(query, docs))),
            key=lambda x: x[1],
            reverse=True,
        ),
    }
    if is_update:
        n = len(docs)
        signals["recency"] = sorted(
            [(i, i / max(n - 1, 1)) for i in range(n)], key=lambda x: x[1], reverse=True
        )

    core_weights = intent_info.get("weights", {})
    weights = {
        "vector": core_weights.get("vector", 1.0),
        "keyword": core_weights.get("fts", 0.5) * 0.8,
        "ngram": core_weights.get("fts", 0.5) * 0.7,
        "bm25": core_weights.get("fts", 0.5) * 0.6,
    }
    if is_update:
        weights["recency"] = core_weights.get("heat", 0.5)
    return signals, weights


def eval_fusion(fuse_fn, model, all_convos, top_k=10):
    """Return (overall_mrr, overall_r10, per_category dict)."""
    cat_hits = defaultdict(list)
    for convo in all_convos:
        sessions = convo["_sessions"]
        embeddings = convo["_embeddings"]
        for qa in convo["qa"]:
            if "question" not in qa:
                continue
            refs = parse_evidence_refs(qa.get("evidence", []))
            target_sessions = {r[0] for r in refs}
            if not target_sessions:
                continue
            cat = CATEGORY_NAMES.get(
                qa.get("category", 0), f"unknown_{qa.get('category', 0)}"
            )
            signals, weights = compute_signals(
                model, embeddings, sessions, qa["question"]
            )
            fused = (
                fuse_fn(signals, weights)
                if fuse_fn is not tmm_fuse
                else fuse_fn(signals, weights)
            )
            hit_rank = None
            for rank, (pos, _) in enumerate(fused[:top_k]):
                sidx = sessions[pos]["session_idx"]
                if sidx in target_sessions:
                    hit_rank = rank + 1
                    break
            cat_hits[cat].append(hit_rank)

    all_ranks = [r for rs in cat_hits.values() for r in rs]
    n = len(all_ranks)
    mrr = sum(1.0 / r for r in all_ranks if r) / n if n else 0.0
    r10 = sum(1 for r in all_ranks if r and r <= _RECALL_AT_10_K) / n if n else 0.0
    per_cat = {}
    for cat, ranks in cat_hits.items():
        nn = len(ranks)
        per_cat[cat] = {
            "mrr": sum(1.0 / r for r in ranks if r) / nn if nn else 0.0,
            "r10": sum(1 for r in ranks if r and r <= _RECALL_AT_10_K) / nn
            if nn
            else 0.0,
            "n": nn,
        }
    return mrr, r10, per_cat, n


def rrf_fuse(signals, weights):
    return wrrf_fuse(signals, weights, k=60)


def main():

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from sentence_transformers import SentenceTransformer  # noqa: PLC0415 — source: ADR-0847

    model_path = os.environ.get("MINILM_PATH", "/tmp/minilm")
    model = SentenceTransformer(model_path)

    raw = load_locomo(DATA_PATH)
    print(f"Loaded {len(raw)} LoCoMo conversations")

    all_convos = []
    for convo in raw:
        sessions = extract_sessions(convo["conversation"])
        if not sessions:
            continue
        embeddings = build_embeddings(model, sessions)
        all_convos.append(
            {"qa": convo["qa"], "_sessions": sessions, "_embeddings": embeddings}
        )
    print(f"Prepared {len(all_convos)} conversations with embeddings")

    results = {}
    for name, fn in [("RRF", rrf_fuse), ("TMM", tmm_fuse)]:
        mrr, r10, per_cat, n = eval_fusion(fn, model, all_convos)
        results[name] = {
            "overall_mrr": mrr,
            "overall_r10": r10,
            "n_questions": n,
            "per_category": per_cat,
        }
        print(f"\n=== {name} fusion ===")
        print(f"  Overall: MRR={mrr:.4f}  R@10={r10:.4f}  (n={n})")
        for cat, m in sorted(per_cat.items()):
            print(
                f"    {cat:<16} MRR={m['mrr']:.3f}  R@10={m['r10']:.3f}  (n={m['n']})"
            )

    delta_mrr = results["TMM"]["overall_mrr"] - results["RRF"]["overall_mrr"]
    delta_r10 = results["TMM"]["overall_r10"] - results["RRF"]["overall_r10"]
    results["delta_TMM_minus_RRF"] = {"mrr": delta_mrr, "r10": delta_r10}
    print("\n=== DELTA (TMM - RRF) ===")
    print(f"  MRR: {delta_mrr:+.4f}   R@10: {delta_r10:+.4f}")

    out = "/Users/cdeust/Documents/Developments/personal/Cortex/benchmarks/results/rrf_vs_tmm_locomo.json"  # noqa: E501 — source: ADR-0847
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
