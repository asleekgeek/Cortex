"""File-loop fixtures: real wrappers and an optional file-backed store double."""

from __future__ import annotations

import hashlib
from types import SimpleNamespace
from unittest.mock import patch

from mcp_server.handlers import codebase_analyze as codebase
from mcp_server.handlers import codebase_analyze_batch
from mcp_server.handlers import remember, wiki_seed_codebase as wiki
from mcp_server.handlers._telemetry_wrap import instrument
from tests_py.handlers._remember_bulk_fakes import harness, original, run


def analysis(relative, content):
    return SimpleNamespace(
        path=relative,
        text=content,
        definitions=[],
        language="python",
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )


def memory_text(parsed):
    return f"# File: `{parsed.path}`\n{parsed.text}"


def codebase_patches(env):
    for name, callback in (
        ("_parse_one_file", analysis),
        ("build_memory_content", memory_text),
        (
            "_set_memory_metadata",
            lambda store, mid: store.events.append(("metadata", mid)),
        ),
        ("persist_entities", lambda store, parsed, mid, domain: (1, 2)),
    ):
        env.stack.enter_context(patch.object(codebase, name, callback))


def enable_state_writes(env, target):
    """Model the store's persistent file changing; never open a database."""
    settings = remember.get_memory_settings()
    settings.DB_PATH = settings.SQLITE_FALLBACK_PATH = str(target)
    insert = env.store.insert

    def write(*args, **kwargs):
        result = insert(*args, **kwargs)
        target.write_text(f"persisted row {len(env.store.rows)} in the store file")
        return result

    env.stack.enter_context(patch.object(remember, "insert_and_post_process", write))


def file_scenario(mode, paths, root, options=None):
    options = options or {}
    with harness() as env:
        codebase_patches(env)
        if options.get("state_file"):
            enable_state_writes(env, options["state_file"])
        if options.get("force_batch"):
            assert mode == "codebase"
            target = codebase_analyze_batch
            env.stack.enter_context(
                patch.object(target, "file_reads_are_independent", return_value=True)
            )
        if options.get("failure"):
            options["failure"](env)
        env.reference = original(remember, "remember")["_handler_impl"]
        if mode == "codebase":
            result = _codebase_call(env, paths, root, options)
        else:
            result = _wiki_call(env, paths, root, options)
        return result, env


def _codebase_call(env, paths, root, options):
    fn = codebase._process_files
    if options.get("reference"):
        namespace = original(codebase, "codebase")
        namespace["remember_handler"] = instrument(
            "remember", env.reference, result_count_key=None
        )
        fn = namespace["_process_files"]
    try:
        return run(
            fn(paths, root, options.get("existing", {}), True, "fixture", env.store)
        )
    except BaseException as exc:
        return type(exc), str(exc)


def _wiki_call(env, paths, root, options):
    files = [(path, str(path.relative_to(root))) for path in paths]
    env.stack.enter_context(patch.object(wiki, "_collect_files", return_value=files))
    fn = wiki.handler
    if options.get("reference"):
        namespace = original(wiki, "wiki_seed")
        namespace["h_remember"] = instrument(
            "remember", env.reference, result_count_key=None
        )
        fn = namespace["handler"]
    return run(fn({"repo_root": str(root), "run_pipeline": False}))
