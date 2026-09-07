# W3-2: rejected normalized batch, exact raw-vector reuse retained

The requested contract is exact score identity, not a numeric tolerance.
On 2026-09-07 the actual pinned neural engine compared the exact helper bodies
at `4407e5e7f80d28463b170b6d3ecab05c2dd20193` and
`60e5646b47b68807495cf03e6ce6b2107758d55f` after the final main rebase.

The five-neighbor public synthetic fixture is `NormalizedBatch.setUp` in
`tests_py/handlers/test_remember_batch_encoding.py`. Model:
`sentence-transformers/all-MiniLM-L6-v2`, revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, CPU float32 vectors.
Four paired repetitions were measured, with the first discarded.
Raw stored-vector bytes and neighbor read order were unchanged, but normalized
vectors differed by up to 1.6391277313232422e-7 and scores by up to
1.1920928955078125e-7. All three retained pairs failed strict score equality.
CPU median improved from 18.112 to 10.507 ms (seven API encodes to two), but
that does not satisfy the identity gate. No tolerance has been adopted.

The normalized scoring path therefore retains scalar encoding in its original
order. A separate safe reuse remains: when curation's merged text equals the
incoming raw text exactly, reuse this write's existing vector object. Changed
text still requires an encode; an older candidate's vector is never reused.
The general target of at most two encodes per remember is NOT met.

Raw experiment: `/private/tmp/cortex-green-w3-2-neural-final.json`;
harness: `/private/tmp/cortex-green-w3-2-neural-final-measure.py`;
command: root `.venv/bin/python` plus that script's `--checkout` pointing to
`/private/tmp/cortex-green-w3-2-final` at the measured revision, and `--output`
pointing to a new file. Historical measurements describe the rejected batch,
not the restored scalar implementation. Full retrieval floors remain separate.
