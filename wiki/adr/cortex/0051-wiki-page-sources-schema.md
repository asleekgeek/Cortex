# ADR-0051: Wiki Page-Source Linkage — Dual Schema Surface

**Status:** Accepted
**Date:** 2026-07-08
**Decision-makers:** cdeust
**Related:** wiki schema (`mcp_server/infrastructure/pg_schema.py::WIKI_SCHEMA_DDL`), cortex-viz (downstream consumer)

## Context

Wiki pages already record which source file(s) they document, but the
linkage is dropped before it ever reaches the database:

- `wiki_file_doc_skeleton.py` writes a `source_file_path:` frontmatter
  key when scaffolding a file-doc page.
- Legacy pages use `file:` (a different frontmatter key) or a
  `file:<path>` tag inside `wiki.pages.tags`.
- `wiki.claim_events.evidence_refs` (JSONB) already carries `kind='file'`
  evidence references extracted per-claim during synthesis
  (`wiki_staleness.py`, `draft_synthesizer.py`).

None of these forms is queryable as a first-class DB edge. A downstream
visualizer (cortex-viz) needs to draw wiki-page → source-file edges, and
today that would require re-parsing every page's frontmatter and tags at
render time — the DB has no surface for "which files does this page
document" or its reverse, "which pages document this file."

This ADR (STEP 1 of the feature) creates that surface. The writer that
populates it from frontmatter/evidence_refs, the backfill over existing
pages, and any consolidate-cycle wiring are separate, later steps — not
implemented here.

## Decision

**Dual schema surface**, added to `WIKI_SCHEMA_DDL` and `MIGRATIONS_DDL`
in `mcp_server/infrastructure/pg_schema.py`:

1. **Edge table `wiki.page_sources`** (N:M, general case):
   ```sql
   CREATE TABLE IF NOT EXISTS wiki.page_sources (
       page_id     INTEGER NOT NULL REFERENCES wiki.pages(id) ON DELETE CASCADE,
       source_path TEXT NOT NULL,
       symbol      TEXT,
       link_kind   TEXT NOT NULL DEFAULT 'documents'
                   CHECK (link_kind IN ('documents','references','derived')),
       confidence  REAL NOT NULL DEFAULT 1.0,
       source      TEXT NOT NULL DEFAULT 'frontmatter'
                   CHECK (source IN ('frontmatter','claim_evidence','body','codebase_grounding')),
       PRIMARY KEY (page_id, source_path, link_kind)
   );
   CREATE INDEX IF NOT EXISTS idx_wiki_page_sources_path ON wiki.page_sources (source_path);
   ```
   Shape mirrors `wiki.links` (src row → typed target key). `source_path`
   is the rel path under the project source root, in canonical form (see
   Risks below). The reverse index on `source_path` is the query the viz
   edge-builder actually runs: file → page(s).

2. **Denormalized scalar `wiki.pages.documents_primary TEXT`** (nullable,
   1:1 fast path):
   - Added to the `wiki.pages` `CREATE TABLE`, adjacent to `memory_id`/
     `concept_id`.
   - Added via an idempotent `MIGRATIONS_DDL` guard (`information_schema.
     columns` existence check, `table_schema = 'wiki'` qualified) for
     already-provisioned databases, following the same pattern already
     used for `memories.heat_base_set_at` etc.

Both are additive: `CREATE TABLE IF NOT EXISTS` for the new table (safe
on fresh and existing DBs — `WIKI_SCHEMA_DDL` runs every boot), and the
`DO $$ ... ALTER TABLE ... ADD COLUMN ... END $$` guard for the new
column on existing installs.

### Rationale for the dual surface

- **The edge table is the general model.** An anchor/scope page can
  document many files (e.g. an ADR touching five modules); rarely, one
  file is documented by more than one page (a module overview plus a
  deep-dive). This is consistent with how `wiki.links` and
  `wiki.citations` already model page relationships as edge tables, not
  scalars.
- **The scalar column is a denormalized query index for the dominant
  1:1 case** (most file-doc pages document exactly one file). Wiki's
  stated design invariant is **zero joins from the recall hot path**
  (`pg_schema.py` §"Isolated `wiki` schema"). Without
  `documents_primary`, any recall-path query wanting "what file does
  this page document" would have to join `wiki.page_sources` even for
  the overwhelmingly common single-file case. The scalar keeps that
  query join-free; `wiki.page_sources` remains the source of truth for
  the N:M case and for the writer/backfill's authoritative history.

### Alternatives rejected

- **(a) Frontmatter-only.** The visualizer needs a queryable DB edge,
  not a per-file markdown parse at render time. Frontmatter stays the
  authored source of truth (files are canonical, per this repo's own
  wiki design — see `wiki.pages` comment "Files remain source of
  truth"), but the DB needs a derived index over it.
- **(b) Single scalar column only (no edge table).** Cannot represent
  the N:M case — an anchor page documenting multiple files, or a file
  documented by multiple pages, would silently lose data or force an
  arbitrary "pick one" resolution.
- **(c) Reuse `wiki.links` with a synthetic file-slug.** `wiki.links.
  dst_page_id` is a strict `FOREIGN KEY REFERENCES wiki.pages(id)`.
  Source files are not wiki pages and have no `wiki.pages` row to
  reference; forcing them through `wiki.links` would mean either
  fabricating placeholder page rows for every source file (schema
  abuse: files aren't pages, and it would pollute `wiki.pages` heat/
  citation/backlink physics with non-page rows) or relaxing the FK to
  allow dangling `dst_page_id`, which defeats the purpose of the
  constraint for every other `wiki.links` consumer.

## Consequences

- Additive migration: `Type-2 reversible` (can be dropped without data
  loss to any other table — no other table's DDL references
  `wiki.page_sources` or `documents_primary` yet). Once cortex-viz (or
  any other consumer) starts reading these columns, the contract
  becomes `Type-1` — a compatibility-breaking removal, not a
  no-op-revert.
- No writer, backfill, or consolidate-cycle wiring is part of this ADR.
  Both `wiki.page_sources` and `wiki.pages.documents_primary` are empty
  on every existing row until a later step populates them from
  frontmatter and `wiki.claim_events.evidence_refs`.
- `source_path` normalization (rel-path canonicalization against the
  project source root, symlink resolution, case sensitivity) is
  deliberately deferred to the writer step — this ADR fixes the column
  as `TEXT NOT NULL` with no format constraint yet, to avoid
  over-specifying a contract before the writer's actual normalization
  logic is designed.

## References

- `mcp_server/infrastructure/pg_schema.py::WIKI_SCHEMA_DDL`
  (`wiki.pages`, `wiki.links`, `wiki.citations`)
- `mcp_server/infrastructure/pg_schema.py::MIGRATIONS_DDL`
  (idempotent `ALTER TABLE ... ADD COLUMN` guard pattern)
- `mcp_server/core/wiki_file_doc_skeleton.py` (`source_file_path:`
  frontmatter writer)
- `mcp_server/core/wiki_staleness.py`,
  `mcp_server/core/draft_synthesizer.py` (`evidence_refs` kind='file')
- `mcp_server/handlers/consolidation/page_io.py`,
  `candidate_scan.py`, `authoring_prompts.py` (legacy
  `source_file_path` readers)
