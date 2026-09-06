"""Only tiny synthetic zip/files in tmp_path; no model downloads or inference."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch
import zipfile

import pytest

from benchmarks.reranker_matrix.cache import durable_root, prepare, verify
from benchmarks.reranker_matrix.pins import ModelPin, cell


def fixture_archive(root: Path, extra: str | None = None) -> ModelPin:
    names = [
        "model.onnx",
        "config.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "tokenizer.json",
    ]
    archive = root / "fixture.zip"
    with zipfile.ZipFile(archive, "w") as target:
        for name in names:
            target.writestr("fixture/" + name, b"synthetic fixture, not a model")
        if extra:
            target.writestr(extra, b"unsafe fixture")
    return ModelPin(
        "fixture", "model.onnx", hashlib.sha256(archive.read_bytes()).hexdigest()
    )


def test_prepare_and_verify_exact_archive_with_tokenizer(tmp_path):
    pin = fixture_archive(tmp_path)
    metadata = prepare(tmp_path, pin)
    assert metadata == verify(tmp_path, pin)
    assert metadata["archive_sha256"] == pin.archive_sha256
    assert (
        metadata["onnx_sha256"]
        == hashlib.sha256(b"synthetic fixture, not a model").hexdigest()
    )
    assert prepare(tmp_path, pin) == metadata


def test_corrupted_archive_fails_before_extracting(tmp_path):
    pin = fixture_archive(tmp_path)
    (tmp_path / "fixture.zip").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        prepare(tmp_path, pin)
    assert not (tmp_path / "fixture").exists()


@pytest.mark.parametrize("name", ["model.onnx", "tokenizer.json"])
def test_model_or_tokenizer_mismatch_is_rejected(tmp_path, name):
    pin = fixture_archive(tmp_path)
    prepare(tmp_path, pin)
    (tmp_path / "fixture" / name).write_bytes(b"different fixture")
    with pytest.raises(ValueError, match="differs from pinned archive"):
        verify(tmp_path, pin)


def test_unverified_optional_vocab_is_rejected(tmp_path):
    pin = fixture_archive(tmp_path)
    prepare(tmp_path, pin)
    (tmp_path / "fixture/vocab.txt").write_text("unverified")
    with pytest.raises(ValueError, match="extra files"):
        verify(tmp_path, pin)


@pytest.mark.parametrize("path", ["../escaped", "/escaped", "elsewhere/file"])
def test_archive_paths_are_checked_before_writing(tmp_path, path):
    pin = fixture_archive(tmp_path, path)
    with pytest.raises(ValueError, match="unsafe archive path"):
        prepare(tmp_path, pin)
    assert not (tmp_path / "fixture").exists()


def test_cache_under_tmp_is_explicitly_refused(tmp_path):
    with patch.dict("os.environ", {"CORTEX_RERANKER_MATRIX_CACHE": str(tmp_path)}):
        with pytest.raises(ValueError, match="must be durable"):
            durable_root()


def test_unknown_cell_cannot_fall_back_to_default():
    with pytest.raises(ValueError, match="unknown W4-2 cell"):
        cell("l2-4x")
