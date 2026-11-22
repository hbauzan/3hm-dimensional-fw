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

    def test_embed_bypasses_normalize_module_when_normalize_false(self) -> None:
        class Transformer:
            def __call__(self, features: dict) -> dict:
                return {"token_embeddings": features["raw"]}

        class Pooling:
            def __call__(self, features: dict) -> dict:
                return {"sentence_embedding": features["token_embeddings"]}

        class Normalize:
            def __call__(self, features: dict) -> dict:
                emb = features["sentence_embedding"]
                normed = torch.nn.functional.normalize(emb, p=2, dim=1)
                return {**features, "sentence_embedding": normed}

        class FakePipelineEncoder:
            def __init__(self, dim: int = 1024) -> None:
                self.dim = dim
                self._param = torch.nn.Parameter(torch.zeros(1, dtype=torch.float32))
                self._modules = [Transformer(), Pooling(), Normalize()]
                self.encode_calls = 0

            def parameters(self):
                yield self._param

            def children(self):
                return iter(self._modules)

            def preprocess(self, texts: List[str], prompt=None) -> dict:
                rows = []
                for _ in texts:
                    vec = torch.zeros(self.dim, dtype=torch.float32)
                    vec[0] = 6.0
                    vec[1] = 8.0
                    rows.append(vec)
                return {"raw": torch.stack(rows, dim=0)}

            def __call__(self, features: dict) -> dict:
                for module in self._modules:
                    features = module(features)
                return features

            def encode(self, texts, **kwargs):
                # Deliberately mimic SentenceTransformer executing 2_Normalize even when normalize_embeddings=False.
                self.encode_calls += 1
                features = self.preprocess(list(texts))
                return self(features)["sentence_embedding"].detach().cpu().numpy()

        pipeline = FakePipelineEncoder()
        client = TestClient(self.server.create_app(pipeline, "cpu", "BAAI/bge-m3"))

        resp_true = client.post("/embed", json={"inputs": ["hola"], "normalize": True})
        self.assertEqual(resp_true.status_code, 200)
        vec_true = resp_true.json()[0]
        l2_true = sum(v * v for v in vec_true) ** 0.5
        self.assertAlmostEqual(l2_true, 1.0, delta=1e-5)

        resp_false = client.post("/embed", json={"inputs": ["hola"], "normalize": False})
        self.assertEqual(resp_false.status_code, 200)
        vec_false = resp_false.json()[0]
        l2_false = sum(v * v for v in vec_false) ** 0.5
        self.assertAlmostEqual(l2_false, 10.0, delta=1e-4)
        self.assertAlmostEqual(vec_false[0], 6.0, delta=1e-4)
        self.assertAlmostEqual(vec_false[1], 8.0, delta=1e-4)

        class BrokenNormalizePipeline:
            def __init__(self) -> None:
                self._param = torch.nn.Parameter(torch.zeros(1, dtype=torch.float32))
                self._modules = [Normalize()]

            def parameters(self):
                yield self._param

            def children(self):
                return iter(self._modules)

            def encode(self, texts, **kwargs):
                raise AssertionError("encode() must never run when Normalize cannot be bypassed")

        with self.assertRaises(RuntimeError):
            self.server._encode(
                BrokenNormalizePipeline(),
                ["hola"],
                "cpu",
                normalize=False,
                batch_size=1,
            )


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
