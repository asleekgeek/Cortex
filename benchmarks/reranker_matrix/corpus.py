"""Fingerprint loaded corpus rows without changing the loaders or their outputs."""

from __future__ import annotations

import hashlib
import json


def loaded_corpus(original, name: str, evidence: dict):
    def load(*args, **kwargs):
        dataset = original(*args, **kwargs)
        if iter(dataset) is dataset:
            raise TypeError("corpus fingerprint requires a re-iterable dataset")
        digest = hashlib.sha256()
        count = 0
        for row in dataset:
            # Structural encoding: sorted JSON keys and newline delimiters
            # make field order immaterial while preserving record order.
            digest.update(
                json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
            )
            digest.update(b"\n")
            count += 1
        evidence[name] = {"sha256": digest.hexdigest(), "rows": count}
        return dataset

    return load
