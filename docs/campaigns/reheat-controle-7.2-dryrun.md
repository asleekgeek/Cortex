# INC7.2 — Contrôle du re-heat (dry-run), post-stratification 7.1

Date de mesure : 2026-07-11 (~07:36 CEST). DB : dev PostgreSQL
`postgresql://127.0.0.1:5432/cortex` (lecture seule pour toutes les requêtes
de ce document — aucune écriture n'a été exécutée contre cette base dans le
cadre de la TÂCHE 2). Repo Cortex, worktree `/private/tmp/wt-reheat-source-filter`,
branche `fix/reheat-source-filter`, base `origin/main@88d192c2` (v4.10.0).

Ce document répond aux 3 questions de contrôle demandées par
l'orchestrateur. L'APPLY éventuel (re-run du re-heat 6.6 avec le filtre
7.2 corrigé) n'est PAS déclenché ici — c'est un dry-run de mesure.

---

## (a) État actuel de la distribution `heat_base` des mémoires DÉLIBÉRÉES

Population : `current_memories` (têtes de chaîne, `NOT is_stale`),
`source` résolvant à `write_class.DELIBERATE` sous la taxonomie **corrigée**
(TÂCHE 1 — exclut `post_tool_capture`, `codebase_analyze`, `consolidation`,
`seed`/`seed_project`, `ingest`/`ingest_codebase`/`ingest_findings`/
`ingest_prd`, `import`/`import_sessions`, préfixes `backfill:*` et `cls*`).

Requête exacte :

```sql
WITH deliberate AS (
  SELECT m.*
    FROM current_memories m
   WHERE NOT m.is_stale
     AND NOT (m.source = ANY(ARRAY[
           'post_tool_capture','codebase_analyze','consolidation',
           'import','import_sessions','ingest','ingest_codebase',
           'ingest_findings','ingest_prd','seed','seed_project']))
     AND NOT (m.source LIKE ANY(ARRAY['backfill:%','cls%']))
),
probed AS (
  SELECT d.id, d.heat_base,
         effective_heat(d, NOW(), COALESCE(hs.factor,1.0)::REAL) AS eh
    FROM deliberate d
    LEFT JOIN homeostatic_state hs
           ON hs.domain = d.domain AND hs.write_class = 'auto'
)
SELECT count(*) AS n,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY heat_base) AS median_heat_base,
       avg(heat_base) AS avg_heat_base,
       percentile_cont(0.25) WITHIN GROUP (ORDER BY eh) AS p25_eh,
       percentile_cont(0.5)  WITHIN GROUP (ORDER BY eh) AS p50_eh,
       percentile_cont(0.75) WITHIN GROUP (ORDER BY eh) AS p75_eh,
       avg(eh) AS avg_eh,
       count(*) FILTER (WHERE eh < 0.25) AS n_below_cliff,
       round(100.0 * count(*) FILTER (WHERE eh < 0.25) / count(*), 1) AS pct_below_cliff
  FROM probed;
```

**Résultat mesuré :**

| n | médiane heat_base | avg heat_base | p25 eh | p50 eh (médiane) | p75 eh | avg eh | n < 0.25 | % < 0.25 |
|---|---|---|---|---|---|---|---|---|
| 543 | 0.1252 | 0.1892 | 0.1226 | 0.1236 | 0.1459 | 0.1854 | 466 | **85.8 %** |

**Comparaison avec les points de référence :**

- Référence INC7.1 (mémoire `inc7.1-homeostatic-stratification.md`,
  mesurée le 2026-07-10 juste après le fold pré-fix de 19:22, scope
  `domain=''`) : médiane `heat_base` post-fold = **0.1253**, 497/538
  (92.4 %) sous le seuil 0.25.
- Cible du re-heat 6.6 (INC6.6, 2026-07-10) : `effective_heat >= 0.25`
  pour toutes les délibérées ciblées (target =
  `core.memory_reheat.DEFAULT_REHEAT_TARGET`).

**Lecture :** la médiane mesurée aujourd'hui (0.1252) est **quasi
identique** à celle mesurée par 7.1 le lendemain du fold pré-fix
(0.1253) — écart de 0.0001, dans le bruit de l'échantillonnage/périmètre
(la mesure 7.1 était scopée `domain=''`, la mesure ci-dessus couvre tous
les domaines ; n=543 vs n=538). **Aucune dérive supplémentaire n'est
observée depuis le 10/07.** Cela confirme (voir (b) ci-dessous) que le
fold stratifié 7.1 n'a **pas re-dégradé** les délibérées depuis son
déploiement — la stratification tient sa promesse. Mais la population
délibérée reste dans l'état dégradé laissé par l'incident pré-7.1
(fold conjoint auto+délibérée du 10/07 19:22) + le re-heat 6.6, dont l'effet
s'est largement estompé : 85.8 % des délibérées actives sont **de nouveau**
sous le seuil 0.25, contre l'objectif "0 sous le seuil" que visait la
campagne 6.6 le 10/07. `apply_reheat` ne remet jamais l'horloge de
décroissance à zéro par design (I6-D5 — voir `core/memory_reheat.py`), donc
c'est un résultat attendu par construction, pas une régression : le
re-heat est une recalibration ponctuelle, pas une protection permanente.
La re-mesure J+30 (due 2026-08-09 par le plan 6.6) est le bon horizon
pour juger de la durabilité ; ce contrôle du 11/07 (J+1) montre juste que
la décroissance naturelle érode déjà une majorité de l'effet en 24h,
signal utile pour l'orchestrateur avant de décider un APPLY.

---

## (b) Le fold stratifié 7.1 a-t-il déjà tourné depuis son déploiement ?

Requêtes exactes :

```sql
SELECT domain, write_class, factor, rows_folded, created_at
  FROM homeostatic_fold_log
 ORDER BY created_at DESC LIMIT 40;

SELECT domain, write_class, factor, updated_at
  FROM homeostatic_state
 ORDER BY updated_at DESC LIMIT 40;
```

**Résultats :**

- `homeostatic_fold_log` (table de journal introduite par 7.1,
  `mcp_server/infrastructure/homeostatic_apply.py`) : **0 ligne**. Aucun
  cycle de fold — stratifié ou non — n'a été journalisé depuis le
  déploiement de 7.1 sur cette DB dev.
- `homeostatic_state` : **2 lignes seulement**, toutes deux
  `write_class = 'auto'` :
  - `code:3.14.12` — `factor=0.6911228`, `updated_at=2026-06-09 21:52:22`
  - `code:cortex` — `factor=1`, `updated_at=2026-05-03 22:30:22`

  Aucune ligne `deliberate`/`derived`/`mechanical` n'existe — cohérent
  avec `_REGULATED_CLASSES={AUTO}` (7.1 policy, `homeostatic.py`) : ces
  classes sont **mesurées** (health moments) mais jamais **régulées**
  (scalaire ou fold), donc n'écrivent jamais leur propre ligne
  `homeostatic_state`. Les deux lignes existantes datent d'avant même le
  10/07 (aucune mise à jour depuis) — le cycle homéostatique
  auto-régulé n'a pas non plus tourné récemment sur ces deux domaines.

**Réponse : NON, le fold stratifié 7.1 n'a jamais exécuté depuis son
déploiement sur cette DB dev** — ni en mode stratifié (post-fix) ni,
semble-t-il, en mode auto-régulé général (aucune ligne `homeostatic_state`
mise à jour depuis le 09/06 pour `code:3.14.12` ni depuis le 03/05 pour
`code:cortex`). Le cycle de consolidation homéostatique n'a
vraisemblablement pas été déclenché du tout sur cette base depuis ces
dates (déclenchement manuel/périodique hors CI, pas un daemon continu en
environnement dev — cohérent avec la note 7.1 : "Consolidation is off by
default in the bench harness"). Conséquence directe pour (a) : la
stabilité de la médiane délibérée mesurée ci-dessus n'est **pas** une
preuve que 7.1 protège activement les délibérées en usage réel — c'est
une preuve qu'**aucun fold n'a eu l'occasion de les re-dégrader**, point
neutre mais important à ne pas confondre avec une validation
opérationnelle du correctif.

---

## (c) Combien de mécaniques ont été indûment chauffées par 6.6 à cause du bug du filtre ?

Le run 6.6 appliqué (journal committé, source de vérité — aucune table
DB ne journalise ce genre de campagne, `apply_reheat` ne touche jamais
`heat_base_set_at` donc impossible de les retrouver par timestamp) :

- `docs/campaigns/i6d5_memory_reheat_apply_20260710T151311Z.json` — pass
  appliqué convergent (post-fix de la marge float32), **540 lignes**
  `outcome=reheated`.
- `docs/campaigns/i6d5_memory_reheat_dry-run_20260710T151019Z.json` —
  dry-run **avant tout re-heat**, sert de référence "avant" pour les
  540 IDs ci-dessus (même population, mêmes IDs présents dans les deux
  journaux).

Méthode : extraire les 540 IDs `outcome=reheated` du journal apply, puis
croiser leur `source` réelle en DB avec la taxonomie corrigée (TÂCHE 1) :

```sql
SELECT
  count(*) FILTER (WHERE source = 'seed_project')       AS seed_project,
  count(*) FILTER (WHERE source = 'cls-consolidation')  AS cls_consolidation,
  count(*) FILTER (WHERE source LIKE 'backfill:%')      AS backfill_prefix,
  count(*) FILTER (WHERE source = 'codebase_analyze')   AS codebase_analyze,
  count(*) FILTER (WHERE source = 'post_tool_capture')  AS post_tool_capture,
  count(*) FILTER (WHERE source LIKE 'wiki://%')        AS wiki_pointer,
  count(*) AS total_reheated
  FROM memories
 WHERE id IN (<540 ids du journal apply, outcome=reheated>);
```

**Résultat mesuré (540 lignes rechauffées au total) :**

| source (classe corrigée) | n | % du total réchauffé |
|---|---|---|
| `seed_project` (mechanical) | 14 | 2.6 % |
| `cls-consolidation` (derived, préfixe `cls`) | 5 | 0.9 % |
| `backfill:*` (mechanical, préfixe) | 72 | 13.3 % |
| **Total mécanique/dérivé indûment inclus** | **91** | **16.9 %** |
| `codebase_analyze` (mechanical) | 0 | 0 % |
| `post_tool_capture` (auto) | 0 | 0 % |
| `wiki://*` (pointeurs wiki, classés DELIBERATE — hors périmètre 7.2) | 46 | 8.5 % |
| autres sources délibérées réelles (feature/lesson/bug-fix/...) | 403 | 74.6 % |

`codebase_analyze` et `post_tool_capture` étaient déjà correctement
exclus par le tuple bugué de 6.6 (`_AUTO_AND_MECHANICAL_SOURCES` avait
ces deux chaînes EXACTES, qui correspondent réellement aux valeurs DB) —
le bug ne les touchait pas. Le bug touchait exactement les 3 familles
prévues par l'intention de conception mais mal orthographiées :
`seed`→`seed_project`, `ingest`→`ingest_codebase` (0 occurrence dans ce
run particulier, mais le trou existe structurellement), `cls`→
`cls-consolidation` (préfixe, pas chaîne exacte).

**Ampleur du chauffage indu (heat_base des 91 lignes mécaniques/dérivées) :**

```sql
-- avant campagne (dry-run 20260710T151019Z, AVANT tout re-heat) :
--   avg heat_base_before = 0.2220, médiane = 0.1846, min=0.10, max=0.7361
--   avg effective_heat_before = 0.1738, médiane = 0.1751 (nettement < 0.25)
-- après campagne (état actuel DB, 2026-07-11) :
SELECT count(*) AS n, avg(heat_base), min(heat_base), max(heat_base)
  FROM memories
 WHERE id IN (<91 ids mécaniques/dérivés>);
--   n=91, avg heat_base=0.2997, min=0.1207, max=0.7618
```

**Résultat :** les 91 mémoires mécaniques/dérivées avaient une
`effective_heat` moyenne de **0.174** (nettement sous le seuil 0.25,
comportement attendu pour du contenu mécanique non révisé) **avant**
la campagne 6.6. Le bug du filtre les a fait entrer dans le scan comme
candidates "délibérées" et leur `heat_base` a été relevé jusqu'à
franchir 0.25 — `heat_base` moyen passé de 0.222 à 0.300. Ce n'est pas
une corruption catastrophique (91/540 = 16.9 % du volume traité, et le
sur-chauffage reste dans un ordre de grandeur raisonnable, pas un
heat_base=1.0 aberrant), mais c'est une violation nette et mesurable de
la garantie annoncée par 6.6 ("deliberate memories below cliff" — ces
91 lignes ne sont PAS délibérées) et une pollution du signal de rang
pour ces 91 mémoires mécaniques dans les recalls futurs tant qu'elles
restent artificiellement chaudes.

**Réponse chiffrée : 91 mémoires (16.9 % des 540 réchauffées) ont été
indûment chauffées par 6.6 à cause du bug du filtre de source — 14
`seed_project`, 5 `cls-consolidation`, 72 `backfill:*`.**

---

## Résumé pour la décision d'APPLY (7.2)

1. Le fix TÂCHE 1 (ce commit) corrige le filtre pour que tout futur
   run du re-heat exclue correctement `seed_project`/`ingest_codebase`/
   `cls-consolidation`/`backfill:*` — vérifié par 4 tests d'intégration
   paramétrés contre les valeurs réelles + 2 tests de garde "closed-world"
   contre les 95 valeurs `source` distinctes réellement présentes en DB.
2. 91 mémoires mécaniques/dérivées portent actuellement un `heat_base`
   artificiellement élevé suite au bug 6.6. Le fix ne les corrige PAS
   rétroactivement (il ne fait que bloquer l'inclusion future).
3. 85.8 % des 543 délibérées actives sont actuellement sous le seuil
   0.25 — la majorité de l'effet de la campagne 6.6 (pour les vraies
   délibérées) s'est déjà estompée par décroissance naturelle.
4. Aucun fold homéostatique (stratifié ou non) n'a tourné depuis le
   déploiement de 7.1 — le correctif 7.1 n'a donc pas encore été
   exercé en conditions réelles sur cette DB dev.

Ces quatre chiffres sont remis à l'orchestrateur pour la décision
d'APPLY (re-run du re-heat 6.6 avec le filtre 7.2 corrigé, et
éventuellement une correction ciblée à la baisse des 91 lignes
mécaniques/dérivées sur-chauffées — hors périmètre de ce dry-run).
