#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
#     "pydantic>=2.9.0",
# ]
# ///
"""Offline contract tests for the fhv1 augmentation cache. No live provider calls."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import httpx

import augment_fhv1_corpus as augment


class EnvContractTest(unittest.TestCase):
    def test_parse_env_quotes_comments_and_export(self) -> None:
        parsed = augment.parse_env_content(
            "\n# comment\nexport OPENAI_API_KEY=\"sk-test\"\nGEMINI_MODEL='gemini-3.8-flash'\n\n"
        )
        self.assertEqual(parsed["OPENAI_API_KEY"], "sk-test")
        self.assertEqual(parsed["GEMINI_MODEL"], "gemini-3.8-flash")

    def test_process_env_overrides_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("OPENAI_API_KEY=from-file\n", encoding="utf-8")
            merged = augment.load_env_map(env_file, {"OPENAI_API_KEY": "from-process"})
        self.assertEqual(merged["OPENAI_API_KEY"], "from-process")

    def test_missing_provider_lists_detected_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "OPENAI_API_KEY=sk-test\nDEEPSEEK_API_KEY=sk-deep\n# GEMINI_API_KEY=hidden\n",
                encoding="utf-8",
            )
            code = augment.main(
                ["--policy-id", "python", "--text", "hello", "--env-file", str(env_file)]
            )
            captured = self._stream.getvalue()
        self.assertEqual(code, 2)
        self.assertIn("missing --provider", captured)
        self.assertIn("OPENAI_API_KEY", captured)
        self.assertIn("DEEPSEEK_API_KEY", captured)
        self.assertNotIn("sk-test", captured)

    def setUp(self) -> None:
        self._stream = __import__("io").StringIO()
        self._original = augment.sys.stderr
        augment.sys.stderr = self._stream

    def tearDown(self) -> None:
        self._captured = self._stream.getvalue()
        augment.sys.stderr = self._original


class CacheContractTest(unittest.TestCase):
    def test_mock_http_then_sha256_cache_hit(self) -> None:
        calls: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"role": "assistant", "content": "  rewritten passage  "}}
                    ]
                },
            )

        env_map = {"OPENAI_API_KEY": "sk-test", "OPENAI_MODEL": "gpt-4o-mini"}
        request = augment.AugmentRequest(
            policy_id="python", provider="openai", texts=["Keep the meaning."]
        )
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            transport = httpx.MockTransport(handler)
            with httpx.Client(transport=transport) as client:
                first, hit = augment.augment_corpus(request, env_map, out_dir, client)
                second, second_hit = augment.augment_corpus(request, env_map, out_dir, client)
            self.assertFalse(hit)
            self.assertTrue(second_hit)
            self.assertEqual(first, second)
            self.assertEqual(len(calls), 1)
            self.assertTrue(calls[0].url.path.endswith("/chat/completions"))
            payload = json.loads(calls[0].content.decode("utf-8"))
            self.assertEqual(payload["model"], "gpt-4o-mini")
            self.assertEqual(payload["temperature"], 0)
            line = json.loads(first.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(line["text"], "rewritten passage")
            manifest = json.loads(first.with_suffix(".manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["sha256"], augment.corpus_sha256("python", request.texts))
            self.assertEqual(manifest["count"], 1)

    def test_gemini_key_precedence(self) -> None:
        config = augment.resolve_provider(
            "gemini",
            {"GOOGLE_API_KEY": "from-google", "GEMINI_API_KEY": ""},
        )
        self.assertEqual(config.env_key_found, "GOOGLE_API_KEY")
        self.assertEqual(config.base_url, "https://generativelanguage.googleapis.com/v1beta/openai")
        self.assertEqual(config.model, "gemini-3.8-flash")


if __name__ == "__main__":
    unittest.main()
