"""Verify pinned archives and their extracted files before any model import."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
from typing import BinaryIO
import zipfile

from benchmarks.reranker_matrix.pins import MODELS, REVISION, ModelPin, cell
from mcp_server.shared.platform import cache_dir


def durable_root() -> Path:
    root = Path(
        os.environ.get("CORTEX_RERANKER_MATRIX_CACHE", cache_dir() / "flashrank-matrix")
    )
    resolved = root.resolve()
    for temporary in (Path("/tmp"), Path("/private/tmp"), Path(tempfile.gettempdir())):
        if resolved.is_relative_to(temporary.resolve()):
            raise ValueError(
                "reranker matrix cache must be durable, outside temporary directories"
            )
    return resolved / REVISION


def digest_file(path: Path) -> str:
    with path.open("rb") as handle:
        return digest_stream(handle)


def digest_stream(handle: BinaryIO) -> str:
    digest = hashlib.sha256()
    # source: ADR-0860
    for chunk in iter(lambda: handle.read(1 << 20), b""):
        digest.update(chunk)
    return digest.hexdigest()


def archive_path(root: Path, pin: ModelPin) -> Path:
    archive = root / f"{pin.name}.zip"
    if not archive.is_file():
        raise FileNotFoundError(f"missing pinned archive {archive}; fetch {pin.url}")
    if digest_file(archive) != pin.archive_sha256:
        raise ValueError(f"archive SHA256 mismatch: {archive}")
    return archive


def checked_path(member: zipfile.ZipInfo) -> PurePosixPath:
    path = PurePosixPath(member.filename)
    if (
        not path.parts
        or "\\" in member.filename
        or path.is_absolute()
        or ".." in path.parts
    ):
        raise ValueError(f"unsafe archive path: {member.filename}")
    if stat.S_ISLNK(member.external_attr >> 16):
        raise ValueError(f"archive symlink refused: {member.filename}")
    return path


def paired_metadata(path: PurePosixPath, names: set[str], model: str) -> bool:
    # source: ADR-0860

    if (
        not path.parent.parts
        or path.parts[0] != "__MACOSX"
        or not path.name.startswith("._")
        or path.name == "._"
    ):
        return False
    target = PurePosixPath(*path.parts[1:]).with_name(path.name.removeprefix("._"))
    return target.parts[0] == model and (
        str(target) in names or str(target) + "/" in names
    )


def checked_members(archive: zipfile.ZipFile, pin: ModelPin) -> list[zipfile.ZipInfo]:
    entries = archive.infolist()
    names = {member.filename for member in entries}
    if len(names) != len(entries):
        raise ValueError("duplicate archive members")
    members = []
    for member in entries:
        path = checked_path(member)
        if paired_metadata(path, names, pin.name):
            continue
        if path.parts[0] != pin.name:
            raise ValueError(f"unsafe archive path: {member.filename}")
        members.append(member)
    # source: ADR-0860
    required = (
        pin.filename,
        "config.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "tokenizer.json",
    )
    if any(f"{pin.name}/{name}" not in names for name in required):
        raise ValueError("archive lacks a required model/tokenizer file")
    return members


def verify(root: Path, pin: ModelPin) -> dict:
    if (root / pin.name).is_symlink():
        raise ValueError("model cache directory must not be a symlink")
    with zipfile.ZipFile(archive_path(root, pin)) as archive:
        members = checked_members(archive, pin)
        for member in members:
            if member.is_dir():
                continue
            path = root / member.filename
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"cached member absent or symlink: {path}")
            with archive.open(member) as source, path.open("rb") as target:
                if digest_stream(source) != digest_stream(target):
                    raise ValueError(
                        f"cached member differs from pinned archive: {path}"
                    )
        expected = {m.filename for m in members if not m.is_dir()}
        actual = {
            p.relative_to(root).as_posix()
            for p in (root / pin.name).rglob("*")
            if p.is_file()
        }
        if actual != expected:
            raise ValueError("unverified extra files in the model cache")
        omitted = sorted(set(archive.namelist()) - {m.filename for m in members})
    return {
        "model": pin.name,
        "revision": REVISION,
        "archive_sha256": pin.archive_sha256,
        "onnx_sha256": digest_file(root / pin.name / pin.filename),
        "cache_root": str(root),
        "metadata_members_retained_only_in_archive": omitted,
    }


def prepare(root: Path, pin: ModelPin) -> dict:
    if (root / pin.name).exists():
        return verify(root, pin)
    with zipfile.ZipFile(archive_path(root, pin)) as archive:
        for member in checked_members(archive, pin):
            target = root / member.filename
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)
    return verify(root, pin)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "check", "urls"))
    parser.add_argument("name", help="model key for prepare/urls; cell for check")
    args = parser.parse_args()
    if args.action == "check":
        print(json.dumps(verify(durable_root(), cell(args.name).model)))
        return
    pin = MODELS[args.name]
    if args.action == "urls":
        print(
            json.dumps(
                {
                    "url": pin.url,
                    "sha256": pin.archive_sha256,
                    "archive": str(durable_root() / f"{pin.name}.zip"),
                }
            )
        )
        return
    print(json.dumps(prepare(durable_root(), pin)))


if __name__ == "__main__":
    main()
