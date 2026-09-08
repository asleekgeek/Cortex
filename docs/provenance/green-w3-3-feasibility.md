# W3-3: raw-character cap cannot preserve tokenization universally

The fixed-cap rejection below is the original audit. The subsequent
[guarded-prefix correction](green-w3-3-guarded-prefix.md) shortens only individually
verified prefixes and retains every counterexample in full.

## Symptôme

W3-3 proposes a character cap before embedding tokenization, sized from the
largest character span observed for 256 tokens in a corpus. Acceptance requires
unchanged embedding bytes, including inputs of 10,000 characters. These two
requirements do not justify any fixed raw prefix shorter than 10,000 characters.
This audit rejects that implementation; W3-3 optimization acceptance remains open.

## Cause racine

The engine passes the complete string to `SentenceTransformer.encode`; it does
not normalize or truncate it first. The pinned model revision is
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41` of `all-MiniLM-L6-v2`.
Its cached `sentence_bert_config.json` sets `max_seq_length=256` and
`do_lower_case=false`. The latter does not disable the tokenizer's own lowercase
normalizer: `tokenizer_config.json` has `do_lower_case=true`.

The tokenizer is BERT WordPiece with 30,522 vocabulary entries, a 100-character
limit **per normalized word**, BERT normalization and BERT pre-tokenization.
Cleaning removes NUL, replacement characters and control/format categories
(with tabs/newlines/carriage returns treated as whitespace). It spaces Chinese
characters, applies NFD accent removal and lowercasing. Spaces can disappear
without producing tokens; removed characters and combining marks can join letters
across arbitrarily long raw input. This is the behavior of the pinned
[BERT normalizer source](https://github.com/huggingface/tokenizers/blob/v0.22.2/tokenizers/src/normalizers/bert.rs)
and [BERT pre-tokenizer source](https://raw.githubusercontent.com/huggingface/tokenizers/v0.22.2/tokenizers/src/pre_tokenizers/bert.rs).

A word longer than 100 normalized characters becomes one `[UNK]`; cutting it to
100 can instead produce many WordPieces. The greedy segmentation and this
whole-word length check precede truncation. The library tokenizes first, then
truncates and inserts special tokens. For the single-text template, 256 includes
`[CLS]` and `[SEP]`, leaving at most 254 ordinary tokens.
[WordPiece implementation](https://raw.githubusercontent.com/huggingface/tokenizers/v0.22.2/tokenizers/src/models/wordpiece/mod.rs),
[tokenization and post-processing](https://raw.githubusercontent.com/huggingface/tokenizers/v0.22.2/tokenizers/src/tokenizer/mod.rs).

The serialized tokenizer JSON also contains historical 128-token padding and
truncation settings. Loading that file without overriding these would audit the
wrong limit. Installed Sentence Transformers 5.6.1 loads the model's 256 setting
into `processor_kwargs.model_max_length` (`base/modules/transformer.py:668`) and
uses `padding=True`, `truncation="longest_first"` (`:941`). Transformers 5.14.1
uses the Rust-backed `BertTokenizer`; tokenizers is 0.22.2, matching `uv.lock`.

## Changement

There is no production change and no guessed cap or margin. The patch adds:

- Sixteen synthetic 10,000-character fixtures: internal/leading whitespace,
  tabs, non-breaking spaces, controls, replacement characters, composed and
  decomposed accents, combining marks, joined emoji, Chinese punctuation,
  explicit special tokens, long words and ordinary prose.
- A tokenizer-only audit CLI with an explicit snapshot and candidate cap. It
  compares IDs, attention masks and type IDs, records configuration hashes,
  and supports an optional local JSONL corpus. Recorded token offsets are
  observations, not certified prefix boundaries or an extrapolated margin.
- An opt-in CPU model measurement using the actual `EmbeddingEngine.encode`
  conversion/normalization path, with no download and no fallback accepted.
  Each encode clears the LRU; four pairs are measured and the first discarded,
  following the plan's repetition convention. Raw CPU/wall samples and byte
  equality are reported. This branch has not been executed in this audit.
- Eight tests, including an isolated CLI process that proves the token-only
  path does not import Torch or Sentence Transformers.

## Preuve

Let `x = "a" + " " * 9998 + "b"`. Its length is 10,000 and `x.strip() == x`.
The exact cached tokenizer produces `[101, 1037, 1038, 102]`, or
`[CLS] a b [SEP]`. For **every** integer `1 <= C < 10000`, `x[:C]` contains `a`
followed only by spaces; its tokens are `[101, 1037, 102]`. Therefore no such
fixed prefix preserves the model input arrays for all accepted texts. Trimming
the outer whitespace before cutting does not repair this counterexample.

The same construction can use arbitrarily many spaces. A maximum observed on
a finite corpus, with any finite margin, cannot establish a universal bound.
For inputs already bounded to 10,000 characters, a cap of 10,000 is a no-op;
other engine callers can accept larger input, so it is not a universal bound
for that API either.

On the supplied 16-case fixture, a candidate cap of 9,999 changes model inputs
in 8 cases. The remaining cases illustrate why a passing ordinary-prose or
single-long-word fixture is insufficient. A separate cap at the configured
WordPiece limit of 100 changes the 101-letter-word case from `[UNK]` to 50
WordPieces. These are measured token differences, **not measured embedding
differences**: changed tokens refute the proposed token-preservation guarantee;
the optional model run is required to report actual vector bytes and timing.

The eight tests pass on Python 3.13.7, macOS 26.6.2 ARM64 with cached tokenizer
0.22.2. No model, DB, network download or corpus scan was run. The tokenizer-only
reports assert `torch_loaded=false` and `sentence_transformers_loaded=false`.
The exact tokenizer SHA-256 is
`be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037`;
the sentence configuration SHA-256 is
`fc1993fde0a95c24ec6c022539d41cf6e2f7c9721e5415d6fb6897472a9cd4b7`.

## Conformité

Work starts from `d72e8b83955234d8f944ac95ec39059723f710f6`. Only W3-3 audit,
fixture, test and documentation files change. `embedding_engine`, runtime
normalization, storage, W3-4 cache work and the craftsmanship baseline remain
unchanged. New Python files stay below 300 lines, functions below 40 lines,
with at most four parameters. Ruff, format and craftsmanship checks pass.

The exact safe alternative is to retain complete raw input and the tokenizer's
existing 256-token truncation. Existing exact cache/batch work (W3-4) can avoid
repeated encoding without changing text. An upstream tokenizer that stops only
after enough finalized tokens could be investigated separately, but would need
to preserve cleaning, Unicode, special-token recognition, complete-word UNK
decisions, masks and type IDs. It still cannot bound raw input scanning by an
arbitrary character constant. No such optimization is implemented or claimed
proven here.

## Candidats issues

Revise W3-3's proposed method before implementation: a corpus-derived raw cap
does not imply exact token or byte equivalence. Keep the bit-equality acceptance
criterion and this adversarial fixture when considering an alternative.

The real-model branch and performance measurements remain for the orchestrator
after its current sequential gates. Passing this audit's tests is evidence of
the feasibility limitation, not completion of the W3-3 optimization. Native
dependencies or an unavailable snapshot fail visibly; no model is downloaded.

## Runbook

Use the repository's locked Python environment and an existing snapshot:

```sh
export CORTEX_PREFIX_AUDIT_SNAPSHOT="/path/to/cached/1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
python -m unittest tests_py.infrastructure.test_embedding_prefix_feasibility -v
python -m scripts.measure_embedding_prefix --snapshot "$CORTEX_PREFIX_AUDIT_SNAPSHOT" --cap 9999 > tokens.json
python -m scripts.measure_embedding_prefix --snapshot "$CORTEX_PREFIX_AUDIT_SNAPSHOT" --cap 100 --case word_limit_boundary > word-boundary.json
```

The test class requiring the real tokenizer skips when the snapshot environment
variable is absent; it never downloads a missing fixture. To measure real neural
bytes later, add `--model`, optionally with `--case internal_spaces`. This runs
CPU inference and is intentionally separate from the lightweight checks. For
a local corpus, add `--corpus-jsonl path.jsonl` with one `{"name":"…","text":"…"}`
object per line; fixture results remain included unless `--case` narrows them.
