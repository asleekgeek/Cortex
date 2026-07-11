# INC7.7 — Amorçage `wiki.citations` pour les 154 pages existantes (M-D7) — dry-run

Repo Cortex, worktree `/tmp/wt-wiki-citations-seed`, branche
`feat/wiki-citations-seed`, base `main@1839f516` (v4.11.0). DB dev
`127.0.0.1:5432/cortex`, dry-run exécuté 2026-07-11.

## Contexte

Le write-path des citations existe depuis I6-D7/INC6.8 (4.9.0) :
`wiki_write` appelle `insert_citation` pour chaque `memory_id` réellement
utilisé lors d'une (re-)curation, dédupliqué par l'index partiel
`uq_wiki_citations_page_memory (page_id, memory_id) WHERE memory_id IS
NOT NULL`. Mais `wiki.citations` = 0 lignes en DB dev, car aucune
curation n'a tourné depuis que le câblage a été posé sur les 154 pages
existantes — INC6.8/Q5 avait explicitement refusé un backfill
rétroactif générique ("aucun backfill rétroactif, même marqué
'inferred'"), en réservant la question à une décision ultérieure une
fois une source fiable identifiée. Cet incrément (M-D7, 7.7) est cette
décision : amorcer `wiki.citations` UNIQUEMENT depuis des sources dont
la provenance est déjà assertée par le schéma, jamais inférée.

## Audit de fiabilité des sources candidates

Trois sources ont été évaluées, comptées en direct sur la DB dev
(2026-07-11) :

| Source | Requête / mécanisme | Lignes | Verdict |
|---|---|---|---|
| `wiki.pages.memory_id` | Colonne `UNIQUE REFERENCES memories(id)`, peuplée par `wiki_migrate.py::_memory_id_from_rel_path` — parse le préfixe `<memory_id>-` du nom de fichier de la page, ne retient l'id QUE s'il existe réellement dans `memories` (`_existing_memory_ids`, filtre anti-FK-morte) | **20** pages avec `memory_id IS NOT NULL` (sur 154 ; 134 à `NULL`) | **HIGH — retenue.** Pointeur FK exact, déjà asserté par le schéma, pas une inférence de cette campagne. |
| `wiki.drafts.memory_id` (via `published_page_id`) | `wiki.drafts` porte son propre `memory_id` (mémoire source du draft) et `published_page_id` (page publiée) | 32 drafts publiés, **20** avec `memory_id` non nul | **HIGH mais redondante — mesurée, pas seedée séparément.** `SELECT count(*) FROM wiki.pages p JOIN wiki.drafts d ON d.published_page_id=p.id AND d.memory_id IS NOT NULL WHERE p.memory_id=d.memory_id` → **20/20** : c'est exactement le même ensemble de paires (page_id, memory_id) que `wiki.pages.memory_id`. Zéro ligne nette supplémentaire. |
| `wiki.page_sources` | Table d'arêtes page → **fichier source** (`source_path`), PAS page → mémoire | 559 lignes (13 `documents` + 546 `references`), 58 pages distinctes | **EXCLUE — mauvais type d'entité, pas seulement "peu fiable".** Cette table ne référence aucun `memory_id` ; en dériver une citation exigerait un JOIN par correspondance approximative chemin-de-fichier ↔ contenu-de-mémoire, exactement la fabrication de provenance qu'INC6.8/Q5 a refusée pour le backfill rétroactif. (Le "~5%" évoqué dans le brief de campagne correspond au join FILE-node par égalité de hash de chemin de cortex-viz, un mécanisme voisin mais distinct — non ré-audité ici car hors périmètre : `page_sources` n'a de toute façon pas de colonne `memory_id` à en tirer.) |
| Tags / `wiki.links` dérivés | `wiki.pages.tags` (JSONB), `wiki.links` (page→page) | 0 tag contenant "memory", 0 ligne dans `wiki.links` (154 pages, 0 lien), 0 page avec `concept_id` renseigné (donc `wiki.concepts.grounding_memory_ids` inatteignable depuis une page) | **EXCLUE — chemin mort.** Aucune de ces trois voies ne relie une page à une mémoire aujourd'hui. |

**Conclusion de l'audit** : une seule source fiable et non redondante
existe dans la DB actuelle — `wiki.pages.memory_id`. 20 paires
(page_id, memory_id), toutes de fiabilité HIGH.

## Résultat du dry-run (script réel, lecture seule)

```
uv run python scripts/wiki_citation_seed.py
```

```
Scanned rows:          20
Seeded:                20
Already cited:         0
Skipped (race):        0
```

Artefact complet : `docs/campaigns/i7d7_wiki_citation_seed_dry-run_20260711T110849Z.json`
(20 entrées journalisées, chacune `{page_id, memory_id, domain,
reliability: "high_direct_memory_id", outcome: "would_seed"}`). Vérifié
en direct : `SELECT count(*) FROM wiki.citations` sur la DB dev reste à
**0** avant et après l'exécution du dry-run (aucune écriture — le script
n'exécute que des `SELECT` en mode dry-run, confirmé par lecture de
`handlers/consolidation/wiki_citation_seed_pass.py::run_wiki_citation_seed_pass`).

## Distribution par page (extrait, 20/20 lignes)

Toutes les 20 candidates sont dans le domaine `zetetic-team-subagents`
(seul domaine où des pages ont été migrées avec un `memory_id` de
filename — cohérent avec `wiki_migrate.py`'s convention, pas un biais de
cette campagne). Aucune page n'a plus d'une candidate (chaque page a au
plus un `memory_id`, colonne `UNIQUE`).

## Périmètre recommandé

**Amorcer les 20 paires HIGH uniquement.** Ne PAS étendre à
`wiki.page_sources` sous quelque tier de fiabilité que ce soit — ce
n'est pas un problème de seuil de confiance, c'est une table du mauvais
type d'entité pour cette opération. Si une source de provenance
mémoire→page fiable apparaît plus tard (ex. `wiki.claim_events.memory_id`
relié à une page via une chaîne encore à construire — aujourd'hui
`claim_events` n'a pas de `page_id`/`concept_id` peuplé exploitable,
0 page avec `concept_id` non nul), elle devra être auditée séparément
avec le même protocole avant tout élargissement.

## Rollback (si `--apply` est exécuté puis doit être annulé)

Chaque ligne écrite par cette campagne est identifiable sans ambiguïté :
`session_id = ''` (jamais utilisé par le chemin CITED_IN de `wiki_read`,
qui exige `session_id <> ''` pour son propre index partiel) ET
`(page_id, memory_id)` présent dans le journal d'apply committé.

```sql
DELETE FROM wiki.citations
WHERE session_id = ''
  AND (page_id, memory_id) IN (
    -- coller ici la liste exacte des paires du journal
    -- docs/campaigns/i7d7_wiki_citation_seed_apply_<timestamp>.json
    (867, 4196226), (868, 4196214), (869, 4196213), (870, 4196209)
    -- ... (20 paires au total, voir l'artefact JSON complet)
  );
```

Le trigger `trg_wiki_citation_bump` incrémente `wiki.pages.heat` de
+0.05 par ligne insérée (déjà saturé à 1.0 pour toutes les pages
concernées — sans effet observable) et `citation_count`. Un rollback par
`DELETE` ne décrémente PAS automatiquement `citation_count`/`heat` (pas
de trigger `AFTER DELETE` sur `wiki.citations` — vérifié,
`pg_schema.py::WIKI_TRIGGERS_DDL` ne définit qu'`AFTER INSERT`) : si un
rollback complet est requis, `citation_count` devra être recalculé
séparément (`UPDATE wiki.pages SET citation_count = (SELECT count(*)
FROM wiki.citations WHERE page_id = wiki.pages.id) WHERE id = ANY(<page
ids>)`), documenté ici pour ne pas être découvert en urgence plus tard.

## Décision requise de l'orchestrateur

Ce document est un dry-run. Aucune écriture n'a été faite. `--apply`
n'a pas été exécuté sur la DB dev — décision réservée, comme demandé.
