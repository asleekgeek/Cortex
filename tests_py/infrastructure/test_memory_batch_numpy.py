"""Optional numeric verification: real NumPy, extracted serializer, no DB/model."""

from __future__ import annotations

import unittest

import numpy as np

from tests_py._memory_read_fakes import (
    Engine,
    SqlSpy,
    final_stage,
    gate_functions,
    source_functions,
)


SERIALIZER = source_functions(
    "mcp_server/infrastructure/pg_store_serialize.py",
    ["_vector_to_bytes"],
    {"np": np, "Vector": type("VectorSentinel", (), {})},
)._vector_to_bytes


class NumpyStore(SqlSpy):
    _vector_to_bytes = staticmethod(SERIALIZER)


class NumpyRowTests(unittest.TestCase):
    def test_float32_and_float64_rows_produce_exactly_the_same_bytes(self):
        for dtype in (np.float32, np.float64):
            with self.subTest(dtype=dtype):
                vector = np.asarray([1.25, -3.5, 0.0], dtype=dtype)
                store = NumpyStore(
                    {1: {"id": 1, "embedding": vector}, 2: {"id": 2, "embedding": None}}
                )
                single = store.get_memory(1)
                bulk = store.get_memories_by_ids([1, 2, 1, None, 99])
                self.assertEqual(bulk[1], single)
                self.assertEqual(
                    bulk[1]["embedding"], np.asarray(vector, dtype=np.float32).tobytes()
                )
                self.assertIsNone(bulk[2]["embedding"])
                sims, _hits = gate_functions().compute_similarities(
                    b"raw", store, Engine()
                )
                self.assertEqual(len(sims), 1)
                apply, ctx, titans = final_stage(store)
                apply([{"memory_id": 1}, {"memory_id": 2}, {"memory_id": 1}], ctx)
                self.assertEqual(
                    titans.update.call_args.args[1],
                    [single["embedding"], single["embedding"]],
                )

    def test_invalid_driver_array_raises_on_single_and_bulk_reads(self):
        for fetch, ids in (
            (NumpyStore.get_memory, 1),
            (NumpyStore.get_memories_by_ids, [1]),
        ):
            with self.subTest(fetch=fetch):
                store = NumpyStore({1: {"id": 1, "embedding": ["invalid"]}})
                with self.assertRaises(ValueError):
                    fetch(store, ids)


if __name__ == "__main__":
    unittest.main()
