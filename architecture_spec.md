# Architecture spec — sf-core

Toolchain: Cargo for the Rust workspace. The Darwin arm64 embedder is the PEP 723 script `tools/bge_m3_mps_server.py`, run only with `uv`. The frontend stays on `pnpm`. Active compiler pin: Rust `1.94.1` (`rust-toolchain.toml`). Crate MSRV `1.91` matches `lancedb 0.40.0` / `lance 13.0.0`. Arrow crates are exact `=58.4.1` (`=58.0.0` does not resolve: DataFusion 54 requires `arrow-schema ^58.3.0`) and are imported from `sf-storage` only as `lancedb::arrow::{arrow_array, arrow_buffer, arrow_schema}`.

## ADR-001 — RFC-003 numerical representation

Store coordinates and compare bounds in IEEE 754 binary32. Accumulate dot products and norms in binary64. The hot path does not call `round`, does not format floats, and does not narrow to `f16` or `bf16`.

Parity contract (architect Q3): hypercube masks match scalar bits (0 ULP). Cosine values satisfy \(|\mathrm{simd}-\mathrm{scalar}| < 10^{-14}\) on the `f64` result. That bound is not a `to_bits` equality.

## ADR-002 — Tier 1 categorical cosine

Each **DomainHypercubeLock** carries its own cosine threshold. Allowlist polarity `0` passes when cosine is at least the threshold. Denylist polarity `1` passes when cosine is below the threshold.

## ADR-003 — Tier 2 clause gate

**ClauseSegmenter** splits the prompt, then each clause is scored against the same centroid. A breach on clause `m` stops the cascade before Tier 3.

Option 2C delimiters are newline, `;`, `,`, `#`, `.` `!` `?` when followed by whitespace or EOF, the quote and comment markers, and these case-insensitive connectors: ` y de paso `, ` además `, ` también `, ` pero `, ` y `, ` o `, ` and `, ` also `, ` plus `, ` but `, ` or `, ` und `, ` außerdem `, ` aber `. The connector text is not part of either clause. A clause of more than 14 words is re-sliced into windows of 10 words with stride 5.

## ADR-004 — Tier 3 pluggable inspector

- Mode A: every active Top-K coordinate lies inside the pre-dilated box.
- Mode B: every active coordinate lies inside the box.
- Mode C: affirmative votes reach **Subspace Coordinate Quorum (K-of-D L∞ Gate)** `K` (default 103).

`epsilon = 0` across all 1024 coordinates and PCA reduction are rejected.

## ADR-005 — Pairwise containment

A canonical domain request passes the primary **DomainHypercubeLock** (L1, L2, L3) and then Tier-3 Mode C on every **PairwiseDifferentialLock** (part of the **55 Pairwise OvO Cross-Lingual Subspace Masks**) whose id names that domain. Registries that contain no pairwise rows keep the single-lock cascade.

The pair id is lexicographic `left_right`. The stored envelope is `left`'s coordinate range. Discriminative coordinates are those outside the nine Anisotropic Rogue Dimensions (Timkey & van Schijndel, 2021) `[292, 297, 308, 329, 386, 404, 577, 616, 780]` whose ranges do not overlap; the mask keeps the 103 largest separations, or every remaining coordinate when fewer than 103 separate. Quorum is 103 in the first case and `ceil(0.10 * active)` in the second. An empty mask still stores quorum 1, and the kernel gate fail-closes if that mask is scored directly. `evaluate_pairwise_containment` skips `active_count == 0`: normalized `bge-m3` ranges overlap, so an allowlist quorum of 1 would reject every in-domain vector.

Evaluation polarity follows the side under test. Target `left` must sit inside the envelope. Target `right` must miss quorum inside that same envelope. The first failing vector aborts. The full prompt uses no clause index. A clause failure reports that index.

```json
{
  "error": {
    "kind": "ddi_ingress_breach",
    "code": "SEMANTIC_CONTAINMENT_BREACH",
    "message": "Fail-closed containment breach on pairwise lock 'python_receta' for clause #1.",
    "telemetry": {
      "domain_id": "python",
      "breaching_pair_lock": "python_receta",
      "breaching_clause_index": 1,
      "failing_tier": "L3_PAIRWISE_QUORUM"
    }
  }
}
```

`calibrate_canonical_pairs` embeds 16 seed sentences per canonical domain through TEI (`BAAI/bge-m3`) and overwrites `domain_hypercubes` with the 11 domain locks plus the 55 pairwise locks. The centroid of a pair is the L2-normalized difference of the two means, accumulated in binary64.

Request `quorum_k` is clamped to `[1, noise_mask.active_count()]` on the cloned lock. The playground omits `overrides` until the operator arms live tuning, so an unarmed session uses the stored quorum.

## Resolved execution decisions

| Id | Decision |
| :--- | :--- |
| Q1 | Toolchain channel `1.94.1`. |
| Q2 | `X-Semantic-Domain: *` defaults to **AnyAllowlist**. **AllLocks** requires `X-SF-Wildcard-Mode: all`. |
| Q3 | Mask bits are 0 ULP. Cosine parity uses the `1e-14` absolute bound. |
| Q4 | NeMo Guardrails is out of scope. |
| Q5 | Direct pins: `clap 4.5.23`, `half 2.4.1`, `tower 0.5.2`. Arrow is `=58.4.1` because `datafusion 54` requires `arrow-schema ^58.3.0`. `lancedb 0.40.0` is built with feature `remote` because `Error::Http` is referenced outside its cfg. That feature pulls `tonic`/`prost` 0.14, so the workspace uses that line instead of 0.12.3/0.13.4. |
| Q6 | Slice 2 is green when NEON matches scalar on this Apple M4. AVX-512 and AVX2 ship `cfg`-gated and are not executed here. |
| Q7 | `manifest.json` follows the roadmap document: `vector_dim` and `alignment_bytes` live in `state_schema`. |
| Q8 | The load process links LanceDB. RSS is measured in Slice 5. A result at or above 45 MB stops at the approval gate with the measured number. |

## Hot path

Ingress reads `POST /v1/chat/completions`, runs **InputNormalizer** (NFKC, homoglyph mapping, invisible character stripping, Base64 inspection), segments clauses via **ClauseSegmenter**, embeds one batch of shape `[1 + M, 1024]`, then runs L1 Centroid Cosine, followed by a sequential clause loop short-circuiting on Tier 2 or Tier 3 failures (recording `clauses_skipped`). A pass streams the upstream body unchanged and sets `X-SF-Decision: PASS`. A breach returns HTTP 403 `SEMANTIC_CONTAINMENT_BREACH` and does not call the upstream model.

Pre-dilated bounds (`lo - eps`, `hi + eps`) are computed when a lock is loaded, not per request on this path.

## Playground chat (`sf-ui`)

`POST /api/v1/chat` gates the latest user message on one **DomainHypercubeLock** (the registry id, or the first loaded lock when `domain_id` is omitted). Tier 1 is centroid cosine, Tier 2 is **ClauseSegmenter** cosine, Tier 3 is Mode C **Subspace Coordinate Quorum (K-of-D L∞ Gate)**. Comparisons follow lock polarity. Coordinates stay `f32`. Sequential clause early-exit records `clauses_skipped` and returns disaggregated latency telemetry.

The diagnostic binary does not call TEI. Python markers project onto the lock centroid inside the pre-dilated box and pass the cascade. Culinary markers project orthogonal to that centroid and breach Tier 1. A string that contains both stays in-domain at Tier 1, so the culinary clause can breach Tier 2. `PERMUTATION_NOISE` stays above the cosine floors and breaches Tier 3. Any other string keeps the SHA-256 projection.

A pass returns the upstream body as `text/event-stream` and does not buffer the SSE payload. A breach returns HTTP 403 `application/json` and does not call the upstream model. `failing_tier` is `L1_CENTROID_COSINE`, `L2_CLAUSE_GATE`, or `L3_SPECTRAL_QUORUM`.

Request overrides replace `l1_cosine_threshold`, `l2_clause_threshold`, `quorum_k`, and `epsilon` on a clone. An epsilon override rebuilds dilated bounds from the stored epsilon: raw bound = dilated bound ± stored epsilon, then dilate again with the request epsilon. The registry lock is left unchanged.

The upstream body is OpenAI chat-completions JSON (`model`, `messages`, `stream: true`). A per-request base that already ends in `/v1` or `/openai` joins `/chat/completions`. Any other host joins `/v1/chat/completions`. `api_key` is sent as `Authorization: Bearer` and is omitted from the JSON body. `/v1/chat/completions` on `sf-proxy` keeps its process-wide base (`{base}/v1/chat/completions`) and its breach envelope (`L1_CATEGORICAL_COSINE`, `L2_SLIDING_WINDOW`, `L3_DDI_INSPECTOR`).

## Embedder runtime

`TeiHttpEmbedder` posts `{"inputs": [...], "normalize": true}` to `POST /embed` and reads a JSON matrix of 1024 binary32 coordinates. On Darwin arm64 the listener is `tools/bge_m3_mps_server.py` at `TEI_HTTP_URL` (default `http://127.0.0.1:8080`), device `mps`, dtype `torch.float32` (RFC-003). `setup.sh` stops container `sf-tei` before that bind and records the process in `.sf_tei_mps.pid`. Other hosts keep `docker-compose.tei.yml`. The Rust client is unchanged.

## Gateway daemon

The `sf-proxy` binary loads a LanceDB registry and serves both ingress routes on `SF_HOST`:`SF_PORT` (default `127.0.0.1:8088`). `POST /v1/chat/completions` still returns `BreachErrorEnvelope`. `POST /api/v1/chat` returns `ChatBreachDto` or an unbuffered `text/event-stream`. A pairwise failure on that route still uses the ADR-005 envelope. The two JSON shapes stay distinct.

`MockBatchEmbedder` does not run pairwise containment unless a batch string is exactly `BREACH`. Every other mock string is the domain centroid and cannot sit in a differential envelope. A batch string that contains `PERMUTATION_NOISE` (any case) is reprojected before the cascade: cosine stays near the centroid and Tier 3 affirmative votes stay below quorum `K`. Live tuning omits `epsilon` until the operator moves that slider, so an L1 or L2 change does not collapse stored dilation.

`SF_CORS_ORIGIN` sets `Access-Control-Allow-Origin`. An empty value or `*` allows any origin. Chat overrides clone the **DomainHypercubeLock** for that request. A registry write happens only through an explicit LanceDB reload.

The playground in `frontend/` is a separate origin. It posts to `/api/v1/chat` on this daemon and reads `ChatBreachDto` or the unbuffered event stream. The SPA maps an ADR-005 pairwise envelope onto `ChatBreachDto` with `failing_tier: L3_PAIRWISE_QUORUM` before drawing the breach card. The dev server does not proxy that call. API keys stay in browser `localStorage`. Live tuning starts disarmed. Headless checks live in `frontend/e2e` and run with `pnpm test:e2e` while this daemon is on `:8088` and Vite is on `:5173`.

## Egress semantic amplification (next milestone, not implemented)

Upstream SSE bytes still pass through `upstream.rs` unchanged after ingress allows the prompt. The next gate wraps that stream:

1. Buffer text deltas into word windows of 30 with stride 15.
2. Embed each window with the local `BAAI/bge-m3` embedder.
3. Score the window on the session's primary lock and on the ten pairwise locks that name that domain, using the same polarity rule as ADR-005.
4. On breach, drop the upstream connection and emit one SSE event: `event: sf_egress_breach` with `failing_tier: EGRESS_L3`.

No production type implements this stream in the current milestone.
