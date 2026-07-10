# INC6.6 — Re-heat one-shot des délibérées (I6-D5) — synthèse de campagne

Repo Cortex, worktree `/tmp/wt-reheat`, branche `feat/deliberate-reheat`,
base `main@7beb5640`. DB dev `127.0.0.1:5432/cortex`, 2026-07-10.

## Décision appliquée

I6-D5 (`scratchpad/inc6-design-campagne-memoire.md`) : passe one-shot sur
les délibérées actives dont `effective_heat` < 0.25 (borne haute du cliff
mesuré, `scratchpad/inc6-audit-outils-memoire.md`, "Effet heat pur" —
familles eh≈0.24 → rangs 1-4, eh≈0.19 → rangs 22-57), relevant
`heat_base` au minimum nécessaire pour atteindre la cible, sans jamais
baisser une valeur existante.

## Formule effective_heat citée

`mcp_server/infrastructure/pg_schema.py:923-1041`,
`CREATE OR REPLACE FUNCTION effective_heat(m memories, t_now TIMESTAMPTZ,
factor REAL DEFAULT 1.0, p_factor REAL DEFAULT 0.99787)`. Deux branches :

- **Protégée** (`is_protected OR no_decay`) :
  `LEAST(1.0, GREATEST(0.0, heat_base * factor))`.
- **Décroissance** : `decayed = heat_base * factor *
  POWER(p_factor, beta * eff_decay_hours)`, clampé à
  `[GREATEST(stage_floor, 1e-38), 1.0]` — `stage_floor` ∈ {0, 0.05, 0.10}
  selon le stade de consolidation lazy-dérivé (`effective_stage()`).

Propriété exploitée (vérifiée, pas réimplémentée) : dans les deux
branches, `effective_heat` est **linéaire en `heat_base`** avant clamp,
avec un multiplicateur (`factor * decay_multiplier`, ou `factor` seul en
protégé) **indépendant de `heat_base`**. Le module
`mcp_server/core/memory_reheat.py::compute_reheat_target` sonde donc la
vraie fonction PL/pgSQL deux fois par ligne — à `heat_base` courant
(`effective_heat_before`) et à `heat_base=1.0`
(`effective_heat_at_max`, via un clone `jsonb_populate_record` de la
ligne, `mcp_server/infrastructure/pg_store_memory_reheat.py`) — et
calcule `needed = target * (1 + marge) / effective_heat_at_max`, jamais
en dessous de `heat_base` actuel (`max(...)`), jamais au-dessus de 1.0
(`min(...)`). La marge (`_FLOAT32_ROUNDTRIP_MARGIN = 1e-4`) compense la
troncature du stockage `REAL` (float4) — sans elle, la première passe
`--apply` laissait la majorité des lignes juste SOUS la cible (mesuré :
540/544 encore < 0.25 au re-scan immédiat) ; corrigée et re-testée
(`tests_py/core/test_memory_reheat.py::TestFloat32RoundtripMargin`).

## Définition "délibérée" (requête exacte de l'audit, re-comptée)

```sql
SELECT COUNT(*) FROM current_memories m
WHERE NOT m.is_stale
  AND m.source NOT IN ('post_tool_capture','codebase_analyze','seed','ingest','cls')
  AND effective_heat(m, NOW(), 1.0::real) < 0.25;
```

Comptage audit initial (2026-07-09/10, pré-6.3) : 542 délibérées actives
au total, eh médian 0.199 (facteur homéostatique fixé à 1.0, formule
simplifiée du critère d'acceptation).

**Re-compte post-dédup 6.3** (2026-07-10, ce run, même requête
simplifiée facteur=1.0) :

| Mesure | Valeur |
|---|---|
| Délibérées actives totales | **750** |
| Délibérées actives sous 0.25 (facteur=1.0, requête audit exacte) | **456** |

Corpus a grossi de 542→750 délibérées entre l'audit et cette campagne
(nouvelles mémoires déposées par les incréments 6.1-6.5 eux-mêmes —
lessons/decisions/bug-fix committés en continu). Le dédup 6.3 a retiré
des doublons mais principalement côté auto-captures ; l'effet net sur le
compte délibéré est une croissance, pas une baisse.

**Mesure de production réelle** (facteur homéostatique par domaine, la
valeur qui gouverne effectivement le classement en recall — cf.
`pg_store_memory_dedup.py`'s convention `COALESCE(hs.factor, 1.0)`) :

| Mesure | Valeur |
|---|---|
| Délibérées actives sous 0.25 (facteur réel par domaine) | **551** |
| eh médian (délibérées, facteur réel) | 0.1399 |

## Dry-run puis apply (chiffré, distributions avant/après)

Artefacts : `docs/campaigns/i6d5_memory_reheat_dry-run_20260710T151019Z.json`
(baseline, aucune écriture), `i6d5_memory_reheat_apply_20260710T151311Z.json`
(apply final avec la marge float32 corrigée — la 2e passe converge les
quelques lignes restées sous la cible après la 1re passe pré-marge),
`i6d5_memory_reheat_apply_20260710T151329Z.json` (confirmation
idempotence, `--apply` sans effet).

| Étape | Scannées | Reheated | Unreachable | Déjà au-dessus | Race |
|---|---|---|---|---|---|
| Dry-run baseline | 551 | 544 | 7 | 0 | 0 |
| Apply (convergence, marge corrigée) | 547 | 540 | 7 | 0 | 0 |
| Dry-run post-apply | 7 | 0 | 7 | 0 | 0 |
| Apply post-apply (idempotence) | 7 | 0 | 7 | 0 | 0 |

Distribution `effective_heat` des délibérées actives (facteur réel,
`n=750`) :

| | Avant | Après |
|---|---|---|
| n sous 0.25 | 551 | **7** (irréductibles, cf. ci-dessous) |
| médiane (toutes délibérées) | 0.1399 | 0.2500 |
| min | 0.0151 | 0.0549 |
| max | 1.0 | 1.0 |

**Jamais de baisse** : vérifié par script sur le journal complet de
l'apply de convergence (`never_lowered` all-True, tous les
`heat_base_after >= heat_base_before`) ET par test d'intégration
(`TestNeverLowers::test_new_heat_base_is_never_below_original_across_many_rows`).

**7 lignes irréductibles** (`unreachable`, `heat_base=1.0` ne suffirait
pas — plafond structurel de décroissance/stade, laissées INTACTES, pas
de `heat_base` gonflée pour rien) : ids 4196187, 4196210, 4196226 +4,
`effective_heat_at_max` mesuré entre 0.17 et 0.21 — sous la cible même au
`heat_base` maximal légal. Ce sont des mémoires très anciennes/consolidées
dont le stade absorbe la décroissance quel que soit `heat_base` (voir
`core/memory_reheat.py`'s docstring pour la dérivation). Ouvre
explicitement la Question ouverte n°4 du design (politique structurelle
si J+30 montre une re-suppression massive — ces 7 en seraient un premier
signal qu'une politique de décroissance différenciée pourrait être
nécessaire, pas juste un re-heat périodique).

## G-rangs (5 échantillons, protocole exact de l'audit)

Script : `scripts/campaign_guards/i6d5_measure_reheat_ranks.py` — même
protocole que `scratchpad/measure_rank.py` (requête = 1re ligne
significative ~90 chars, embedding MiniLM production, `recall_memories()`
non scopé, intent `general`, `min_heat=0.01`, `p_max_results=60`). "Avant"
mesuré en remettant `heat_base` à sa valeur pré-campagne DANS une
transaction annulée (`ROLLBACK`, aucune écriture réelle) ; "après" = état
actuel de la DB.

| id | eh avant (échantillon) | heat_base avant | rang avant | rang après |
|---|---|---|---|---|
| 4198018 | ~0.015 (min) | 0.0339 | 1 | 1 |
| 4196447 | ~0.10 (p25) | 0.0815 | 1 | 1 |
| 4253211 | ~0.10 (médiane) | 0.0543 | 1 | 1 |
| 4201644 | ~0.159 (p75) | 0.3131 | 2 | 1 |
| 4196608 | ~0.25 (proche cliff) | 0.2594 | 98 | 98 |

**Verdict chiffré : 4/5 top-10 (rang ≤ 2 en fait), 1/5 reste hors top-10
(rang 98, inchangé).**

Lecture honnête, pas maquillée : les 4 lignes améliorées/stables en
top-3 confirment le mécanisme (I6-D5 traite correctement le suppresseur
(b), la froideur relative des délibérées). La 5e ligne (id 4196608) était
DÉJÀ à eh≈0.259 avant la campagne (quasi au niveau cible) — son delta de
heat est donc négligeable (0.2594→~0.260), et son rang 98 stable
démontre que pour CETTE ligne, la heat n'est PAS le facteur limitant :
son contenu ("Audit the integration wiring of /Users/...") entre en
compétition lexicale directe avec des familles d'auto-captures proches
(suppresseur (c) de l'audit, "banalité lexicale"). Ce cas individuel ne
suffit PAS à lui seul à trancher le critère double de D4 (13 cibles,
protocole complet requis côté orchestrateur) mais **c'est exactement le
type de signal chiffré que la décision go/no-go D4 attend** : le levier 2
(D5, cette campagne) ne suffit pas pour 100 % des cas — un contenu déjà
proche de la cible avant campagne, en compétition lexicale directe avec
des autos, reste hors top-10 malgré une heat au niveau cliff. Si ce
schéma se généralise sur les 13 cibles complètes de l'audit (mesure que
l'orchestrateur doit faire courir après 6.6+6.3+6.2 combinés), le levier
3 (D4, décote catégorielle des autos, incrément conditionnel 6.7) devient
nécessaire.

## Re-mesure programmée — J+30

**Date de re-mesure : 2026-08-09** (J+30 depuis cette campagne,
2026-07-10). Réutiliser exactement les requêtes SQL "Définition
délibérée" et "Distribution effective_heat" ci-dessus. Si la médiane
délibérée est repassée sous 0.25, la Question ouverte n°4 du design
(politique structurelle de heat à l'écriture délibérée vs. re-heat
périodique de maintenance) doit être posée à l'utilisateur avec ces
données, per I6-D5.

## Tests

`tests_py/core/test_memory_reheat.py` : 11/11 (calcul du `heat_base`
minimal, jamais-de-baisse, clamp à 1.0, cas irréductible, forme
protégée/no-decay, marge de survie au round-trip float32).
`tests_py/handlers/consolidation/test_memory_reheat_pass.py` : 8/8
(scan+sonde réels contre PL/pgSQL, écriture CAS, invariant jamais-de-
baisse sur plusieurs lignes réelles, exclusion des sources auto/
mécaniques, dry-run n'écrit rien, idempotence d'un re-run réel,
CAS rejette une écriture concurrente, ligne irréductible non fabriquée).
19/19 au total. Non-régression : `test_memory_dedup_exact.py` +
`test_memory_domain_backfill.py` + tout `tests_py/handlers/consolidation/`
= 60/60 verts (aucun impact sur les passes 6.2/6.3).

`ruff format --check` et `ruff check` : clean sur les 6 fichiers touchés.

## Fichiers

- `mcp_server/core/memory_reheat.py` — décision pure (`compute_reheat_target`).
- `mcp_server/infrastructure/pg_store_memory_reheat.py` — scan+sonde SQL,
  écriture CAS.
- `mcp_server/handlers/consolidation/memory_reheat_pass.py` — composition
  root.
- `scripts/memory_reheat.py` — CLI dry-run/--apply + journal JSON.
- `scripts/campaign_guards/i6d5_measure_reheat_ranks.py` — G-rangs (5
  échantillons, transaction annulée pour la mesure "avant").
- `tests_py/core/test_memory_reheat.py`,
  `tests_py/handlers/consolidation/test_memory_reheat_pass.py`.
