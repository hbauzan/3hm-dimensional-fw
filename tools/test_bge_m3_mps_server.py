#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "torch>=2.4.0",
#     "fastapi>=0.115.0",
#     "pydantic>=2.9.0",
#     "httpx>=0.27.0",
#     "numpy>=2.0.0",
# ]
# ///
"""Behavior tests for the native Metal BGE-M3 embedder. No weight download."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path
from typing import List

import numpy as np
import torch
from fastapi.testclient import TestClient

SERVER_PATH = Path(__file__).with_name("bge_m3_mps_server.py")
WARMUP_TEXTS = [
    "warmup python def sort(x): return sorted(x)",
    "warmup receta salsa de tomate",
]


def load_server():
    import bge_m3_mps_server as server

    return server


class FakeEncoder:
    def __init__(self, dtype: torch.dtype = torch.float32, dim: int = 1024) -> None:
        self.dim = dim
        self.calls: list[tuple[list[str], dict]] = []
        self._param = torch.nn.Parameter(torch.zeros(1, dtype=dtype))

    def parameters(self):
        yield self._param

    def eval(self):
        return self

    def to(self, *args, **kwargs):
        return self

    def encode(self, texts, **kwargs):
        batch = list(texts)
        self.calls.append((batch, kwargs))
        rows = []
        for index, _text in enumerate(batch):
            vector = np.zeros(self.dim, dtype=np.float32)
            vector[index % self.dim] = 1.0 if kwargs.get("normalize_embeddings", False) else 4.0
            rows.append(vector)
        return np.stack(rows)


class Pep723ContractTest(unittest.TestCase):
    def test_inline_metadata_and_rfc003_source(self) -> None:
        source = SERVER_PATH.read_text(encoding="utf-8")
        self.assertTrue(source.startswith("#!/usr/bin/env -S uv run --script\n"))
        self.assertIn("# /// script", source)
        self.assertIn('requires-python = ">=3.11"', source)
        for dep in (
            "torch>=2.4.0",
            "sentence-transformers>=3.2.0",
            "fastapi>=0.115.0",
            "uvicorn>=0.32.0",
            "pydantic>=2.9.0",
        ):
            self.assertIn(dep, source)
        tree = ast.parse(source)
        banned_attrs = {"float16", "bfloat16", "half"}
        hits: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in banned_attrs:
                hits.append(node.attr)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "half"
            ):
                hits.append(".half()")
        self.assertEqual(hits, [])


class DeviceAndPrecisionTest(unittest.TestCase):
    def test_select_device_uses_mps_when_available(self) -> None:
        server = load_server()
        mps = torch.backends.mps
        if mps.is_available() and mps.is_built():
            self.assertEqual(server.select_device(), "mps")

    def test_require_device_fail_closed_on_darwin_arm64(self) -> None:
        server = load_server()
        import os

        if os.uname().sysname == "Darwin" and os.uname().machine == "arm64":
            with self.assertRaises(RuntimeError):
                server.require_device("cpu")
            self.assertEqual(server.require_device("mps"), "mps")
        else:
            self.assertEqual(server.require_device("cpu"), "cpu")

    def test_rfc003_rejects_non_float32_parameters(self) -> None:
        server = load_server()
        with self.assertRaises(RuntimeError):
            server.enforce_rfc003(FakeEncoder(dtype=torch.float16))
        self.assertEqual(server.enforce_rfc003(FakeEncoder()), torch.float32)


class HttpContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.server = load_server()
        self.encoder = FakeEncoder()
        self.client = TestClient(
            self.server.create_app(self.encoder, "mps", "BAAI/bge-m3")
        )

    def test_health_stays_down_until_the_http_stack_is_warm(self) -> None:
        self.client.app.state.accepting = False
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 503)
        self.client.app.state.accepting = True

    def test_health_reports_mps_float32_dim(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["model_id"], "BAAI/bge-m3")
        self.assertEqual(body["device"], "mps")
        self.assertEqual(body["dtype"], "torch.float32")
        self.assertEqual(body["dim"], 1024)
        self.assertEqual(body["mps_available"], bool(torch.backends.mps.is_available()))

    def test_embed_batch_is_float32_unit_rows(self) -> None:
        response = self.client.post(
            "/embed",
            json={
                "inputs": ["ordenar una lista", "salsa de tomate"],
                "truncate": True,
                "normalize": True,
            },
        )
        self.assertEqual(response.status_code, 200)
        matrix = response.json()
        self.assertEqual(len(matrix), 2)
        self.assertEqual(len(matrix[0]), 1024)
        norm = sum(value * value for value in matrix[0]) ** 0.5
        self.assertAlmostEqual(norm, 1.0, delta=1e-5)
        texts, kwargs = self.encoder.calls[-1]
        self.assertEqual(texts, ["ordenar una lista", "salsa de tomate"])
        self.assertTrue(kwargs["normalize_embeddings"])
        self.assertEqual(kwargs["precision"], "float32")
        self.assertFalse(kwargs["show_progress_bar"])
        self.assertEqual(kwargs["batch_size"], 2)

    def test_embed_accepts_a_single_string(self) -> None:
        response = self.client.post("/embed", json={"inputs": "solo una clausula"})
        self.assertEqual(response.status_code, 200)
        matrix = response.json()
        self.assertEqual(len(matrix), 1)
        self.assertEqual(len(matrix[0]), 1024)

    def test_embed_rejects_empty_inputs(self) -> None:
        response = self.client.post("/embed", json={"inputs": []})
        self.assertEqual(response.status_code, 400)

    def test_embed_normalize_false_preserves_unnormalized_output(self) -> None:
        response = self.client.post(
            "/embed",
            json={"inputs": ["raw clause"], "normalize": False},
        )
        self.assertEqual(response.status_code, 200)
        matrix = response.json()
        self.assertEqual(len(matrix), 1)
        self.assertEqual(len(matrix[0]), 1024)
        self.assertEqual(matrix[0][0], 4.0)
        self.assertEqual(matrix[0][1], 0.0)
        norm = sum(value * value for value in matrix[0]) ** 0.5
        self.assertAlmostEqual(norm, 4.0, delta=1e-5)
        self.assertGreater(abs(norm - 1.0), 1e-3)
        texts, kwargs = self.encoder.calls[-1]
        self.assertEqual(texts, ["raw clause"])
        self.assertFalse(kwargs["normalize_embeddings"])
        self.assertEqual(kwargs["precision"], "float32")

    def test_embed_rejects_wrong_dimension(self) -> None:
        encoder = FakeEncoder(dim=8)
        client = TestClient(self.server.create_app(encoder, "cpu", "BAAI/bge-m3"))
        response = client.post("/embed", json={"inputs": ["x"], "normalize": True})
        self.assertEqual(response.status_code, 500)


class WarmupTest(unittest.TestCase):
    def test_warmup_compiles_mps_shaders_before_traffic(self) -> None:
        server = load_server()
        encoder = FakeEncoder()
        synced: List[str] = []

        def synchronize() -> None:
            synced.append("sync")

        original = torch.mps.synchronize
        torch.mps.synchronize = synchronize
        try:
            server.warmup(encoder, "mps")
        finally:
            torch.mps.synchronize = original
        texts, kwargs = encoder.calls[0]
        self.assertEqual(texts, WARMUP_TEXTS)
        self.assertEqual(encoder.calls[1][0], server.VERIFICATION_TEXTS)
        self.assertTrue(kwargs["normalize_embeddings"])
        self.assertEqual(kwargs["precision"], "float32")
        self.assertGreaterEqual(len(synced), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
