# Changelog

## [Unreleased]

- Suite 2 reports `blocked_prod` and `recall_prod` beside Mode A `blocked` / `recall`. The new count is attacks with `!contained_prod` (primary Mode C cascade, then `evaluate_pairwise_containment`). On the v0.2.1 fixtures the attack counts match Mode A: EN 64/82, ES 90/90, pooled 154/172. Clean false positives are unchanged (Mode A 36/100, production Mode C 31/100).

## 0.2.1 - 2026-11-19

- Release `v0.2.1` closing `TASK-007`: archived `roadmap/archived/v0.2-hardening-and-empirical-truth.prompt.md` and added `roadmap/HANDOFF-v0.2.1-AND-VNEXT-AUDIT.md` as the baseline audit handoff for vNext.
- CI runs the x86_64 and arm64 Rust jobs and the frontend job.
- The README now cites the measured release CPU gate (p50 0.542 µs, p99 0.583 µs), the measured embedder (MPS, p50 23.775 ms, p99 629.247 ms), and the Suite 2 autopsy (3/100, 31/100, 36/100).
- `GET /health` on `sf-ui` returns the package version and no other fields.
- v0.2.x is an Ingress-Only Semantic Firewall. This version scores ingress. Egress Semantic Amplification stays a v1.1+ stream inspector and does not wrap upstream SSE.
- Suite 2 records the first failing tier of each clean false positive. Mode A keeps the current pairwise check. Mode C calls `evaluate_pairwise_containment`.

  ```
  suite2 fp_tier matrix=EN mode=A l1=0 l2=0 l3=0 pairs=3 fp=3
  suite2 fp_tier matrix=EN mode=C l1=0 l2=0 l3=0 pairs=3 fp=3
  suite2 fp_tier matrix=ES mode=A l1=0 l2=3 l3=0 pairs=30 fp=33
  suite2 fp_tier matrix=ES mode=C l1=0 l2=3 l3=0 pairs=25 fp=28
  suite2 fp_tier matrix=pooled mode=A l1=0 l2=3 l3=0 pairs=33 fp=36
  suite2 fp_tier matrix=pooled mode=C l1=0 l2=3 l3=0 pairs=28 fp=31
  ```

- Suite 2 normalizes and segments each prompt, then scores the primary lock in Mode C and every non-empty pairwise lock in Mode A. EN: n_clean=10, fp=3, fpr=3/10, n_attack=82, cosine_leaks=48, recall=64/82. ES: n_clean=90, fp=33, fpr=33/90, n_attack=90, cosine_leaks=41, recall=90/90. The width-weighted holistic gate is documented in `roadmap/future-holistic-resonance-gate.md` and is not implemented.
- Clause short-circuit records `clauses_skipped` and skips the remaining CPU/SIMD clause gates. It does not skip or shrink the embedding batch of the normalized prompt and every clause.
- Seeding writes 11 base locks plus 55 pairs. The mock embedder uses the requested domain centroid with fallback to the default domain.
- Inspect clause telemetry uses a per-clause embedding. The studio mock embedder skips pairwise containment unless the batch contains the exact token `BREACH`. `sf-ui` chat returns HTTP 400 for the same invalid overrides as the gateway before dilation.
- `POST /api/v1/chat` rejects non-finite `l1_threshold`, `l2_threshold`, and `epsilon`, rejects `epsilon < 0.0`, and rejects thresholds outside `[-1.0, 1.0]` with HTTP 400 before dilation. A negative epsilon can no longer invert a denylist interval and open the gate.
- LanceDB rows persist `top_k_len` and the corpus SHA-256 manifest. Mode A scores each selected coordinate once. A lock written without an external corpus file stores an explicit empty manifest (`doc_count = 0`) instead of a fake one-row digest.
- Playground chat no longer false-breaches an in-domain prompt on an empty pairwise mask. `MockBatchEmbedder` skips pairwise containment unless the batch contains the exact token `BREACH`. `PERMUTATION_NOISE` still breaches Tier 3. The SPA renders an ADR-005 pairwise envelope as `L3_PAIRWISE_QUORUM`. Live tuning omits `epsilon` until that slider moves. `pnpm test:e2e` runs the Playwright suite in `frontend/e2e`.
- Playground **Domain id** is a `<select>` of the 11 canonical domains (`CANONICAL_DOMAINS` in `frontend/src/domain/presets.ts`, same order as `sf-storage` calibration). A stored non-canonical id stays as an extra option so the session value remains selected.
- Native Apple Silicon embedder: on Darwin arm64, `setup.sh` stops Docker `sf-tei` and serves `BAAI/bge-m3` from `tools/bge_m3_mps_server.py` (`uv`, Metal `mps`, `torch.float32`) on `127.0.0.1:8080`. `GET /health` and `POST /embed` stay drop-in compatible with `TeiHttpEmbedder`.
- Option 2C **ClauseSegmenter**: commas and trilingual discourse connectors split piggybacked clauses, and a clause longer than 14 words falls back to a window of 10 with stride 5.
- Canonical calibration (`calibrate_canonical_pairs`) builds 11 domain locks and 55 **PairwiseDifferentialLock** rows from `BAAI/bge-m3` embeddings. A named canonical domain must pass its primary lock and every pairwise lock that names it. A pairwise failure is HTTP 403 `L3_PAIRWISE_QUORUM` and names the breaching lock.
- Chat overrides clamp `quorum_k` into `[1, active_count]`. The playground leaves overrides off until the operator arms them.
- Mock upstream isolation: decoupled `ChatUpstream::Mock` in `sf-proxy` via `mock_upstream` (`MockUpstreamForwarder`), ensuring offline deterministic SSE streaming on `/api/v1/chat` without falling back to unreachable network upstreams.
- Decoupled playground in `frontend/`: the browser calls `POST /api/v1/chat` on `sf-proxy`, renders upstream SSE on PASS, and draws the Rayos X card from `ChatBreachDto` on HTTP 403. Live overrides and the upstream selector stay in the page. API keys stay in `localStorage`.
- Upstream credentials from `.env`: `sf-proxy` serves `GET /api/v1/upstream/env` resolving environment variables and `.env` files for Gemini (`GEMINI_API_KEY`, `GOOGLE_API_KEY`), DeepSeek, OpenAI, Groq, and Ollama.
- UI `.env` integration: `Playground` in `frontend/` and embedded studio in `sf-ui` include an "Usar keys de .env" toggle and "Cargar de .env" sync button, showing live detection status and automatically forwarding credentials to upstream.
- Provider defaults: default Gemini model upgraded to `gemini-3.8-flash`, added presets for Groq (`llama-3.3-70b-versatile`) and Ollama (`llama3`).
- `sf-proxy` daemon serves `POST /v1/chat/completions` and `POST /api/v1/chat` on one process. `SF_CORS_ORIGIN` selects the browser origin; an empty value allows `*`.
- `/api/v1/chat` on the daemon emits `ChatBreachDto` and streams upstream SSE without buffering. `/v1/chat/completions` still emits `BreachErrorEnvelope`. Request overrides stay ephemeral.

## 0.2.0

- **Terminology Sanitization**: Replaced all internal project terminology with formal academic and systems standards:
  - Benchmark renamed to **SCPB-220** (**Sub-Clause Piggybacking Benchmark**).
  - Tier 3 gate designated as **Subspace Coordinate Quorum (K-of-D L∞ Gate)**.
  - Background noise coordinates documented as **Anisotropic Rogue Dimensions (Timkey & van Schijndel, 2021)**.
  - 55 domain pairs formally designated as **55 Pairwise OvO (One-vs-One) Cross-Lingual Subspace Masks**.
  - Output space defined as **1024D Contrastive Embedding Manifold ($S^{1023} \subset \mathbb{R}^{1024}$)** with **deterministic IEEE 754 binary32 evaluation with 0 ULP cross-architecture parity**.
- **Pre-Segmentation Input Normalizer**: Added deterministic, zero-allocation pre-segmentation pipeline (`InputNormalizer`) in `sf-proxy`:
  - Unicode NFKC canonicalization with Cyrillic and Greek homoglyph neutralization.
  - Invisible evasion code point stripping (`\u{200B}`, `\u{200C}`, `\u{200D}`, `\u{2060}`, `\u{FEFF}`, `\u{00AD}`).
  - High-entropy Base64 payload detection ($\ge 24$ chars), decoding UTF-8 cleartext and routing clauses into `ClauseSegmenter`.
- **Sequential Clause Early-Exit**: Multi-clause evaluation records `clauses_skipped` and skips the remaining CPU/SIMD clause gates after the first failing clause. That early return does not skip or shrink the embedding batch that already ran.
- **Disaggregated Telemetry**: Response JSON and HTTP headers (`x-sf-*`) report isolated stage latencies: `normalizer_segmenter_us`, `embedding_inference_ms`, `simd_gate_kernel_us`, and `total_pipeline_ms`. The web UI renders a dedicated disaggregated latency panel in `BreachCard`.
- **Public Benchmark Suite (`sf-bench`)**:
  - Suite 1 evaluates `SCPB-220` against global sequence cosine dilution.
  - Compiled offline via embedded binary fixtures (`crates/sf-bench/fixtures/oos_bge_m3_vectors.bin` and metadata manifest). Added `tools/generate_real_public_benchmarks.py`.
- **CERN Zenodo DOI & Documentation Overhaul**:
  - Authored `.zenodo.json` metadata for DOI archival.
  - Rewrote `README.md` with mathematical analysis of cosine dilution, algorithmic comparison ($O(D^2)$ Mahalanobis vs strict $\ell_\infty$ vs 3HM $K$-of-$D$), Timkey citation, and operational threat model boundaries.
- `POST /api/v1/chat` on `sf-ui`: three-tier gate, HTTP 403 breach telemetry, and unbuffered SSE to a per-request OpenAI-compatible upstream.
- Embedded Chat Playground in `sf-ui`: Diagnostic Studio / Chat Playground tabs, SSE thread, live lock overrides, and the Rayos X breach card. API keys stay in `localStorage`.
- `ReqwestChatForwarder::forward_dynamic` joins a request base URL and sends `Authorization: Bearer` without changing `/v1/chat/completions`.
- Calibrated chat embedder for the standalone studio: Python prompts pass into upstream SSE, culinary prompts breach at L1, piggybacked clauses breach at L2, and `PERMUTATION_NOISE` breaches the L3 spectral quorum. The Chat Playground loads those four prompts from preset chips.

## 0.1.0

- Workspace bootstrap for `sf-kernels`, `sf-storage`, `sf-proxy`, and `sf-bench` on Rust 1.94.1.
- Scalar `AlignedVec1024` gates and the `/v1/chat/completions` tracer: `X-SF-Decision: PASS` or HTTP 403 `SEMANTIC_CONTAINMENT_BREACH`.
- SIMD dispatch (AVX-512, AVX2+FMA, NEON) with 0 ULP hypercube masks and cosine parity inside `1e-14`. RFC-003 rejects the 16-ULP micro-gap that `round-4` and `f16` accept.
- LanceDB hypercube registry with SNR pruning (`--extra-pruned-dims`), SHA-256 manifests, and wait-free `ArcSwap` reloads. Arrow is pinned at 58.4.1 because DataFusion requires `^58.3`. `lancedb` feature `remote` forces tonic/prost 0.14.
- Production proxy: TEI gRPC `EmbedStream` with `normalize=true`, HTTP `/embed` fallback, wildcard AnyAllowlist / AllLocks, and SSE passthrough.
- Rompepepe 220: scalar cosine leaks 50% (inside 14.5–58.2%) and L3 Mode C contains 220/220. The 1,000 RPS gate measured p50 0.046 ms, p99 0.127 ms, RSS 10.1 MB.
