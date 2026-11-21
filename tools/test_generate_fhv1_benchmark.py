#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Offline contract tests for the four-quadrant fhv1 benchmark generator."""

from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path

import generate_fhv1_benchmark as generator


class GeneratorContractTest(unittest.TestCase):
    def test_default_path_is_offline_and_balanced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first, manifest_path = generator.generate("python", Path(tmp), fetch_hf=False)
            second, _ = generator.generate("receta", Path(tmp), fetch_hf=False)
            again, _ = generator.generate("python", Path(tmp) / "again", fetch_hf=False)
            self.assertEqual(first.read_text(encoding="utf-8"), again.read_text(encoding="utf-8"))
            for path, policy in ((first, "python"), (second, "receta")):
                rows = [
                    json.loads(line)
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                self.assertGreaterEqual(len(rows), 400)
                counts = {category: 0 for category in generator.CATEGORIES}
                seen = set()
                banned = generator.forbidden_surfaces(policy)
                for row in rows:
                    counts[row["category"]] += 1
                    self.assertEqual(row["expected_pass"], row["category"] == "IN_DOMAIN_VALID")
                    folded = generator.nfkc_lower(row["text"])
                    self.assertNotIn(folded, seen)
                    seen.add(folded)
                    self.assertNotIn(row["text"], banned)
                    self.assertNotIn(folded, banned)
                for category in generator.CATEGORIES:
                    self.assertGreaterEqual(counts[category], 100)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertFalse(manifest["fetch_hf"])
            self.assertEqual(manifest["total"], 400)
            self.assertEqual(manifest["sha256"], generator.dataset_sha256(
                [json.loads(line) for line in first.read_text(encoding="utf-8").splitlines()]
            ))

    def test_fetch_hf_is_refused_without_the_opt_in(self) -> None:
        code = generator.main(["--policy-id", "python", "--fetch-hf", "--out-dir", "/tmp/unused-fhv1"])
        self.assertEqual(code, 2)

    def test_source_keeps_remote_fetch_behind_the_flag(self) -> None:
        tree = ast.parse(Path(generator.__file__).read_text(encoding="utf-8"))
        calls = [
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]
        self.assertIn("fetch_hf_banks", calls)
        generate_fn = next(
            node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "generate"
        )
        gated = False
        for node in ast.walk(generate_fn):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "fetch_hf_banks"
            ):
                gated = True
        self.assertTrue(gated)


if __name__ == "__main__":
    unittest.main()
