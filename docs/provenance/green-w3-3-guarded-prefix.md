# W3-3: guarded single-text BERT prefix

The original fixed-character cap is still rejected: whitespace, controls and
whole-word WordPiece handling invalidate a universal short prefix. The new
implementation keeps the full text unless it can prove a particular prefix
already contains every model token. Stored text, cache keys, embedding
normalization and batch encoding are unchanged.

## Evidence and safety conditions

The pinned tokenizer has BERT normalization, BERT pre-tokenization, WordPiece,
right truncation and the single template `[CLS] A [SEP]`. The model has no default
prompt. The guard checks these conditions at model load. Added tokens that are
normalized or contain whitespace disable the optimization; such tokens could
otherwise span a selected boundary. Other model configurations keep their normal
encoding path. Eligible-tokenizer errors are not hidden or converted to a fallback.

[BERT normalization](https://raw.githubusercontent.com/huggingface/tokenizers/v0.22.2/tokenizers/src/normalizers/bert.rs)
retains ASCII space/tab/CR/LF as whitespace. The
[BERT pre-tokenizer](https://raw.githubusercontent.com/huggingface/tokenizers/v0.22.2/tokenizers/src/pre_tokenizers/bert.rs)
splits on whitespace before
[WordPiece](https://raw.githubusercontent.com/huggingface/tokenizers/v0.22.2/tokenizers/src/models/wordpiece/mod.rs)
processes complete words, including its whole-word length and UNK checks. Cutting
after a retained whitespace boundary does not change any preceding word. If that
prefix already fills the model's configured token budget, later words cannot
change its retained input tokens. The final scalar encode sees the same token
arrays, padding length and normalization.

This is a conditional optimization, not a promise that every input can be capped.
The known `a + 9998 spaces + b` counterexample stays whole, as do unbroken long
words and controls that join letters across the input.

## Cost probe, not an accuracy threshold

The initial probe position is1450 characters. It is the maximum observed retained
token end among the six 10000-character fixtures whose original token sequence
fills the pinned model's256-token budget. It is recorded in
[the observations](green-w3-3-prefix-observations.json), derived by
`scripts.measure_embedding_prefix` from the cached tokenizer. Ordinary prose
supplies1450; the other saturated cases end at763,916,1083,296 and1170.

This number only selects where to try an optimization. The code advances to a
whole-word boundary and checks the actual token count. No margin or universal
bound is inferred from the sample. A conservative whitespace cost guard retains
the full input when the stripped prefix is shorter than the model budget; this
cannot change any output even if a normalizer expands characters.

## Verification

The cached-tokenizer regression runs all16 adversarial fixtures of10000characters.
It verifies IDs, masks and type IDs exactly, including the long-word UNK boundary,
combining marks, invisible controls, Chinese, emoji and explicit special tokens.
Additional tests cover unsupported configurations, normalized/whitespace added
tokens, prompts, left truncation, insufficient budgets and tokenizer failures.

A diagnostic prototype, before the final whitespace cost guard, also produced
bit-identical real MiniLM vectors on all16 fixtures (Python3.12.11, CPU, model
revision1110a243). Its prose median was11.021ms→9.785ms; its sparse-space case
incurred extra tokenization. Those preliminary timings do not establish the
performance of the final implementation. Final model timing and full ordered
gates must be recorded on the committed implementation before publication.

Batch inputs are deliberately outside this optimization: changing raw lengths
can change SentenceTransformer's length sorting and batch membership, which
would require separate numerical-equivalence evidence.
