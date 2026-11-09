#!/usr/bin/env python3
"""
tools/fetch_public_benchmarks.py
Fetches and caches public benchmark datasets from Hugging Face:
- clinc_oos (Out-of-Scope intent classification benchmark)
- deepset/prompt-injections (Jailbreak and adversarial prompt injection benchmark)

Caches processed JSON fixtures into `data/benchmarks/`.
"""

import os
import sys
import json
from pathlib import Path

CACHE_DIR = Path("data/benchmarks")

def fetch_datasets():
    print("=" * 70)
    print("3HM / sf-core Public Benchmark Dataset Fetcher")
    print("Datasets: 'clinc_oos' & 'deepset/prompt-injections'")
    print("=" * 70)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from datasets import load_dataset
    except ImportError:
        print("[!] The 'datasets' library is not installed.")
        print("[*] To install, run: pip install datasets or uv pip install datasets")
        print("[*] Note: sf-bench works 100% offline using deterministic compiled fixtures.")
        return

    # 1. Fetch clinc_oos
    clinc_path = CACHE_DIR / "clinc_oos_test.json"
    if clinc_path.exists():
        print(f"[✓] Found cached clinc_oos at {clinc_path}")
    else:
        print("[*] Fetching 'clinc_oos' (plus domain subset)...")
        try:
            clinc = load_dataset("clinc_oos", "plus", split="test")
            oos_samples = [item for item in clinc if item["intent"] == 42][:200]
            with open(clinc_path, "w", encoding="utf-8") as f:
                json.dump(oos_samples, f, indent=2)
            print(f"[✓] Saved {len(oos_samples)} out-of-scope samples to {clinc_path}")
        except Exception as e:
            print(f"[!] Warning: Failed to download clinc_oos: {e}")

    # 2. Fetch deepset/prompt-injections
    deepset_path = CACHE_DIR / "deepset_injections_test.json"
    if deepset_path.exists():
        print(f"[✓] Found cached deepset/prompt-injections at {deepset_path}")
    else:
        print("[*] Fetching 'deepset/prompt-injections'...")
        try:
            deepset = load_dataset("deepset/prompt-injections", split="test")
            injection_samples = [item for item in deepset if item["label"] == 1][:200]
            with open(deepset_path, "w", encoding="utf-8") as f:
                json.dump(injection_samples, f, indent=2)
            print(f"[✓] Saved {len(injection_samples)} injection samples to {deepset_path}")
        except Exception as e:
            print(f"[!] Warning: Failed to download deepset/prompt-injections: {e}")

    print("\n[✓] Public benchmark setup complete.")

if __name__ == "__main__":
    fetch_datasets()

