# W4-3 — observations mémoire groupées

## Symptôme

Après fusion, Titans recharge les dix premiers résultats individuellement pour
leurs embeddings. L'enrichissement par étape recharge aussi chaque candidat.
Le gate d'écriture recharge les cinq voisins pour les similarités brutes, puis
les mêmes lignes pour leurs textes normalisés et une dernière fois pour le
signal temporel. Chaque `_execute` PostgreSQL prend une connexion et une
transaction autocommit (`pg_store_ddl.py`).

## Cause racine

`search_vectors` ne renvoie que `(id, distance)`, sans contenu. Les candidats de
recall ne sont pas des lignes complètes ; un `StageDetector` arbitraire peut
consommer d'autres métadonnées que le champ de stage usuel. Remplacer ces
lectures par le contenu candidat ou par un vecteur brut modifierait les signaux.

La primitive `get_embeddings_for_memories` n'a pas exactement la sémantique de
`get_memory` sur SQLite : elle lit `memories_vec`, tandis que les lignes de la
table `memories` n'ont pas de champ embedding. Le handler recall utilise aussi
ce backend et transmet `momentum_state`. L'utiliser ici activerait donc Titans
sur SQLite. Ce changement de mécanisme est exclu de W4-3.

## Changement

`get_memories_by_ids` exécute un `SELECT * WHERE id = ANY(%s::int[])` sur PG,
un `IN` paramétré sur SQLite, et applique le normaliseur existant de chaque
backend. Une liste vide n'exécute aucune requête. Le dictionnaire de lignes
omettant les identifiants manquants ne définit pas leur ordre : les consommateurs
rejouent leurs candidats, doublons compris. Aucun repli vers N lectures unitaires.

Titans et l'assemblage exploitent ces lignes complètes ; **la projection
`SELECT *` reste présente**. Le gain porte sur les transactions supprimées.
Le gate partage une vue locale `MemoryRows` entre les trois signaux : similarité
brute, réencodage scalaire des textes normalisés, et temporalité. Le batch
W3-2 a été rejeté après différence numérique réelle : voir
`docs/provenance/green-w3-2-encoding-identity.md`. Les lignes,
le vecteur brut et les observations/calibrations W3-1a ne sont pas modifiés.
Le résultat public de `compute_similarities` reste le couple `(sims, hits)`.

## Preuve

Contexte : `d0f7c19b`, puis les patches W3-1a et W3-2 ; Python 3.14.4, doubles
déterministes, aucune DB, aucun modèle. Le script charge les corps réels des
fonctions avant/après et remplace seulement les dépendances et l'accès DB par
des spies. Il enregistre les SHA-256 des sources, les énoncés SQL et le digest
du résultat. Les nombres ci-dessous ne sont pas ceux du recall complet.

| Périmètre exécuté | Avant | Après | Résultat fixture |
|---|---:|---:|---|
| Titans, dix candidats | 10 | 1 | Identique |
| Enrichissement par étape, dix candidats | 10 | 1 | Identique |
| Signaux gate, cinq voisins template | 12 | 2 | Identique |
| Signaux gate, cinq voisins hors template | 7 | 2 | Identique |

```sh
python3 -m unittest tests_py.core.test_memory_batch_reads tests_py.handlers.test_remember_neighbor_reads -v
python3 scripts/measure_memory_batch_reads.py --before /chemin/snapshot-avant-W4-3
# Dans l'environnement existant possédant NumPy, sans installer de dépendance :
python -m unittest tests_py.infrastructure.test_memory_batch_numpy -v
```

Les tests vérifient : ordre SQL inversé, doublons, ids absents/null, contenu
complet de plus de 10 000 caractères, stage personnalisé, vecteurs null/vides,
normalisation des dates/tags/heat, absence de mutation, conservation des
textes normalisés, exceptions store/encode et absence de retry N+1. La forme
de vecteur ambiguë à `bool()` est testée sans importer NumPy. Une vérification
supplémentaire avec NumPy 2.5.1 compare le sérialiseur PG réel sur ndarray
float32/float64 : mêmes bytes float32 pour lecture unitaire/groupée, mêmes
exceptions pour tableaux invalides ; imports modèle/DB interdits pendant ce test.

## Conformité

Aucun seuil changé ; top-5/top-10 proviennent des appels remplacés. Les nouveaux
modules respectent 300 lignes, 40 lignes/fonction, quatre paramètres et trois
niveaux. Les imports ajoutés dans core sont limités à shared. Aucun ajout de
baseline. Dette existante de `remember_helpers.py` et du callback d'assemblage
conservée ; pas de refactor hors sujet. L'entrée baseline du normaliseur template
est déjà obsolète dans le prérequis W3-2 ; elle doit être retirée lors de son
intégration, sans attribuer sa correction à W4-3.

## Candidats issues

- Le champ embedding absent des lignes SQLite rendait Titans inactif sur ce
  backend ; W4-3 conserve cet état et ne choisit pas une activation implicite.
- L'ancien alignement compacté `sims`/`hits` en présence de voisins sans vecteur
  est conservé pour le signal temporel ; le corriger serait un autre changement.
- Les recherches par entité en phase 2 et les autres mécanismes de recall
  peuvent effectuer d'autres requêtes. La cible globale ≤5 après fusion doit
  être mesurée dans le profil réel, pas déduite des seuls compteurs ci-dessus.

## Runbook

Root applique W4-3 après W3-1a/W3-2, puis exécute les gates du contrat et
`benchmarks/reproduce.sh` dans l'environnement isolé. La suite légère et les
compteurs locaux ne remplacent pas les floors ni une mesure `_execute` de tout
le recall/remember réel. Aucun chiffre de CPU, latence, énergie ou qualité
retrieval n'est revendiqué ici. Aucune opération de production n'est requise.

Les observations sont réutilisées pendant l'appel, sans cache inter-requêtes.
Sous modifications concurrentes, l'ancien code pouvait relire plusieurs
versions d'un voisin ; le nouveau code conserve la version du batch. Les
garanties testées concernent un store stable ; ce n'est pas une nouvelle
transaction PostgreSQL englobant l'ensemble du recall ou du remember.
