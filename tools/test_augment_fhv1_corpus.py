#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
#     "pydantic>=2.9.0",
# ]
# ///
"""Offline contract tests for the fhv1 augmentation cache and 1B LLM CLI. No live provider calls."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

import httpx

import augment_fhv1_corpus as augment


class EnvContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self._stream = io.StringIO()
        self._original = augment.sys.stderr
        augment.sys.stderr = self._stream

    def tearDown(self) -> None:
        self._captured = self._stream.getvalue()
        augment.sys.stderr = self._original

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

    def test_auto_provider_precedence_and_fail_closed_without_keys(self) -> None:
        env_all = {
            "GROQ_API_KEY": "gsk-secret",
            "OPENAI_API_KEY": "sk-openai",
            "DEEPSEEK_API_KEY": "sk-deepseek",
            "GEMINI_API_KEY": "gem-secret",
        }
        self.assertEqual(augment.resolve_provider("auto", env_all).provider, "gemini")

        env_no_gem = {"GROQ_API_KEY": "gsk", "OPENAI_API_KEY": "sk", "DEEPSEEK_API_KEY": "ds"}
        self.assertEqual(augment.resolve_provider("auto", env_no_gem).provider, "deepseek")

        env_openai = {"GROQ_API_KEY": "gsk", "OPENAI_API_KEY": "sk"}
        self.assertEqual(augment.resolve_provider("auto", env_openai).provider, "openai")

        env_groq = {"GROQ_API_KEY": "gsk"}
        self.assertEqual(augment.resolve_provider("auto", env_groq).provider, "groq")

        # Fail closed when zero API-keyed providers are configured, even if OLLAMA_MODEL is set.
        with self.assertRaises(ValueError):
            augment.resolve_provider("auto", {"OLLAMA_MODEL": "llama3", "OLLAMA_BASE_URL": "http://127.0.0.1:11434/v1"})

        # Explicit --provider ollama remains allowed.
        self.assertEqual(augment.resolve_provider("ollama", {"OLLAMA_MODEL": "llama3"}).provider, "ollama")


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


class LlmAugmentContractTest(unittest.TestCase):
    def test_augment_llm_expands_dedupes_guards_holdout_and_caches(self) -> None:
        calls: list[httpx.Request] = []
        holdout_line = "This exact holdout prompt must never enter the augmented calibration cache."
        dup_text = "Use pathlib.Path.iterdir to inspect immediate child directory entries cleanly."

        def handler(request: httpx.Request) -> httpx.Response:
            idx = len(calls)
            calls.append(request)
            # First call injects a duplicate, a Spanish wrong-language item, a holdout overlap, and valid EN variants.
            if idx == 0:
                variants = [
                    dup_text,
                    dup_text.upper(),  # NFKC-lower duplicate
                    "Para preparar la salsa bechamel usá manteca, harina tostada y leche fría.",  # wrong language
                    holdout_line,  # holdout overlap
                    f"Python variant alpha {idx}: prefer contextlib.ExitStack when managing variable numbers of open files.",
                    f"Python variant beta {idx}: wrap sqlite3 connections carefully and enable WAL mode for concurrent reads.",
                ]
            else:
                variants = [
                    f"Python variant gamma {idx}: combine itertools.islice with lazy generators to inspect huge log files.",
                    f"Python variant delta {idx}: pass strict=True to zip() whenever paired sequence lengths must match.",
                    f"Python variant epsilon {idx}: measure critical loop timings with time.perf_counter_ns for stable medians.",
                ]
            return httpx.Response(
                200,
                json={"choices": [{"message": {"role": "assistant", "content": json.dumps(variants)}}]},
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus_file = root / "corpus.jsonl"
            corpus_file.write_text(
                "\n".join([
                    json.dumps({"text": dup_text}),
                    json.dumps({"text": "Use dataclasses with frozen=True and slots=True for immutable Python records."}),
                ])
                + "\n",
                encoding="utf-8",
            )
            bench_file = root / "bench.jsonl"
            bench_file.write_text(
                json.dumps({"input_id": "p-1", "category": "IN_DOMAIN_VALID", "expected_pass": True, "text": holdout_line})
                + "\n",
                encoding="utf-8",
            )
            out_dir = root / "aug"
            env_file = root / ".env"
            env_file.write_text("DEEPSEEK_API_KEY=sk-secret-never-echo\n", encoding="utf-8")

            transport = httpx.MockTransport(handler)
            with httpx.Client(transport=transport) as client:
                code1 = augment.main(
                    [
                        "--augment-llm",
                        "--provider",
                        "auto",
                        "--policy-id",
                        "python",
                        "--corpus-file",
                        str(corpus_file),
                        "--benchmark-file",
                        str(bench_file),
                        "--target-count",
                        "8",
                        "--env-file",
                        str(env_file),
                        "--out-dir",
                        str(out_dir),
                    ],
                    client=client,
                )
                self.assertEqual(code1, 0)
                first_call_count = len(calls)
                self.assertGreaterEqual(first_call_count, 2)

                # Second invocation hits SHA-256 cache with zero additional HTTP calls.
                code2 = augment.main(
                    [
                        "--augment-llm",
                        "--provider",
                        "auto",
                        "--policy-id",
                        "python",
                        "--corpus-file",
                        str(corpus_file),
                        "--benchmark-file",
                        str(bench_file),
                        "--target-count",
                        "8",
                        "--env-file",
                        str(env_file),
                        "--out-dir",
                        str(out_dir),
                    ],
                    client=client,
                )
                self.assertEqual(code2, 0)
                self.assertEqual(len(calls), first_call_count)

            jsonl_files = list(out_dir.glob("python_*.jsonl"))
            self.assertEqual(len(jsonl_files), 1)
            rows = [json.loads(line) for line in jsonl_files[0].read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertGreaterEqual(len(rows), 8)
            texts = [r["text"] for r in rows]
            folded = [augment.nfkc_lower(t) for t in texts]
            self.assertEqual(len(folded), len(set(folded)))
            self.assertNotIn(augment.nfkc_lower(holdout_line), folded)
            self.assertFalse(any("bechamel" in t.lower() for t in texts))

            manifest = json.loads(jsonl_files[0].with_suffix(".manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["augmented_llm"])
            self.assertEqual(manifest["provider"], "deepseek")
            self.assertEqual(manifest["target_count"], 8)
            self.assertEqual(manifest["holdout_overlap"], 0)

    def test_augment_llm_spanish_purity_and_fail_closed_on_http_error(self) -> None:
        def failing_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": {"message": "unauthorized"}})

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus_file = root / "receta.jsonl"
            corpus_file.write_text(
                json.dumps({"text": "Sofreír la cebolla picada en aceite de oliva hasta que quede transparente."}) + "\n",
                encoding="utf-8",
            )
            bench_file = root / "receta_bench.jsonl"
            bench_file.write_text(
                json.dumps({"input_id": "r-1", "category": "IN_DOMAIN_VALID", "expected_pass": True, "text": "¿Cómo evitar que se corte la mayonesa?"}) + "\n",
                encoding="utf-8",
            )
            env_file = root / ".env"
            secret = "gem-super-secret-value-999"
            env_file.write_text(f"GEMINI_API_KEY={secret}\n", encoding="utf-8")
            out_dir = root / "aug"

            stderr_buf = io.StringIO()
            old_stderr = augment.sys.stderr
            augment.sys.stderr = stderr_buf
            try:
                with httpx.Client(transport=httpx.MockTransport(failing_handler)) as client:
                    code = augment.main(
                        [
                            "--augment-llm",
                            "--provider",
                            "auto",
                            "--policy-id",
                            "receta",
                            "--corpus-file",
                            str(corpus_file),
                            "--benchmark-file",
                            str(bench_file),
                            "--target-count",
                            "5",
                            "--env-file",
                            str(env_file),
                            "--out-dir",
                            str(out_dir),
                        ],
                        client=client,
                    )
            finally:
                augment.sys.stderr = old_stderr

            self.assertNotEqual(code, 0)
            self.assertNotIn(secret, stderr_buf.getvalue())
            self.assertEqual(list(out_dir.glob("*.jsonl")), [])

    def test_augment_llm_fails_closed_when_zero_keys_for_auto(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus_file = root / "py.jsonl"
            corpus_file.write_text(json.dumps({"text": "Use pathlib for cross-platform paths."}) + "\n", encoding="utf-8")
            env_file = root / ".env"
            env_file.write_text("# empty\n", encoding="utf-8")
            stderr_buf = io.StringIO()
            old_stderr = augment.sys.stderr
            augment.sys.stderr = stderr_buf
            try:
                code = augment.main(
                    [
                        "--augment-llm",
                        "--provider",
                        "auto",
                        "--policy-id",
                        "python",
                        "--corpus-file",
                        str(corpus_file),
                        "--target-count",
                        "5",
                        "--env-file",
                        str(env_file),
                        "--out-dir",
                        str(root / "aug"),
                    ]
                )
            finally:
                augment.sys.stderr = old_stderr
            self.assertNotEqual(code, 0)
            self.assertIn("no API-keyed provider", stderr_buf.getvalue())

    def test_augment_llm_fails_closed_when_provider_yields_only_duplicates_or_overlap(self) -> None:
        def stale_handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(
                                    [
                                        "Use pathlib for cross-platform paths.",
                                        "Compare Python tuple unpacking versus slice indexing",
                                    ]
                                ),
                            }
                        }
                    ]
                },
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus_file = root / "py.jsonl"
            corpus_file.write_text(
                json.dumps({"text": "Use pathlib for cross-platform paths."}) + "\n",
                encoding="utf-8",
            )
            env_file = root / ".env"
            env_file.write_text("OPENAI_API_KEY=sk-test-never-echo\n", encoding="utf-8")
            out_dir = root / "aug"
            stderr_buf = io.StringIO()
            old_stderr = augment.sys.stderr
            augment.sys.stderr = stderr_buf
            try:
                with httpx.Client(transport=httpx.MockTransport(stale_handler)) as client:
                    code = augment.main(
                        [
                            "--augment-llm",
                            "--provider",
                            "auto",
                            "--policy-id",
                            "python",
                            "--corpus-file",
                            str(corpus_file),
                            "--target-count",
                            "6",
                            "--env-file",
                            str(env_file),
                            "--out-dir",
                            str(out_dir),
                        ],
                        client=client,
                    )
            finally:
                augment.sys.stderr = old_stderr
            self.assertNotEqual(code, 0)
            self.assertIn("failed closed", stderr_buf.getvalue())
            self.assertNotIn("sk-test-never-echo", stderr_buf.getvalue())
            self.assertEqual(list(out_dir.glob("*.jsonl")), [])

    def test_augment_llm_default_corpus_file_and_sliding_window_holdout_guard(self) -> None:
        calls: list[httpx.Request] = []

        def window_overlap_handler(request: httpx.Request) -> httpx.Response:
            idx = len(calls)
            calls.append(request)
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(
                                    [
                                        # Contains exact 5+ word holdout phrase from fhv1_benchmark_banks.json
                                        "Compare Python tuple unpacking versus slice indexing in tight loops today.",
                                        # Valid novel python texts per round
                                        f"Use itertools.batched round {idx} in Python 3.12 to chunk large records lazily without slicing copies.",
                                        f"Configure logging.QueueHandler round {idx} with QueueListener so web workers avoid blocking disk writes.",
                                    ]
                                ),
                            }
                        }
                    ]
                },
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env_file = root / ".env"
            env_file.write_text("GROQ_API_KEY=gsk-test-123\n", encoding="utf-8")
            out_dir = root / "aug"
            with httpx.Client(transport=httpx.MockTransport(window_overlap_handler)) as client:
                code = augment.main(
                    [
                        "--augment-llm",
                        "--provider",
                        "auto",
                        "--policy-id",
                        "python",
                        "--target-count",
                        "207",
                        "--env-file",
                        str(env_file),
                        "--out-dir",
                        str(out_dir),
                    ],
                    client=client,
                )
            self.assertEqual(code, 0)
            jsonl_file = next(out_dir.glob("python_*.jsonl"))
            texts = [json.loads(line)["text"] for line in jsonl_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertGreaterEqual(len(texts), 207)
            self.assertFalse(any("Compare Python tuple unpacking versus slice indexing" in t for t in texts))


if __name__ == "__main__":
    unittest.main()
