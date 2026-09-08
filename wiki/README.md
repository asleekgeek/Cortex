# Project wiki

Edit authored decision pages here, using `wiki_write` or `wiki_adr` with the
absolute `project_root`, or a text editor. Run `wiki_reindex` with the same
project root to refresh `docs/adr/`; its contents are generated read-only mirrors.
For the CLI, run `python scripts/check_project_wiki.py --write`.

`manifest.json` preserves historical filenames and ID reservations. Generated
runtime indexes are ignored because their filesystem stamps belong to the
current checkout. `python scripts/check_project_wiki.py` validates mirror bytes
without reading any private wiki. See ADR-0056 for the full decision.
