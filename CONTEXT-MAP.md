# CONTEXT-MAP

| Context | Path | Relationship |
| :--- | :--- | :--- |
| Kernels | `crates/sf-kernels` | Owns **AlignedVec1024**, **NoiseBitmask1024**, **DomainHypercubeLock**, cosine, Tier-3 evaluation, and **FiltroHectorV1** (**MovementTier**, Welford moments, strict AABB). The fhv1 module stays free of serializers. |
| Storage | `crates/sf-storage` | Persists locks in LanceDB and publishes an `ArcSwap` registry. Also owns `fhv1_profiles`, `fhv1_calibration_samples`, `fhv1_benchmark_runs`, and `fhv1_audit_traces` (Arrow `Float64`) plus the xlsx, zip, csv, and parquet exporter. `Fhv1Store` does not open `domain_hypercubes`. Depends on Kernels. |
| Proxy | `crates/sf-proxy` | **InputNormalizer**, **ClauseSegmenter**, TEI embedders, cascade, OpenAI ingress, the fhv1 calibration and evaluation pipeline, and `/api/v1/fhv1/*`. Chat accepts `3hm_default`, `fhv1`, and `3hm_plus_fhv1`. Depends on Kernels and Storage. |
| Bench | `crates/sf-bench` | **SCPB-220** fixtures, OOS injection validation, the load SLA, `fhv1_calibrate`, and `fhv1_benchmark`. Depends on Kernels, Storage, and Proxy. |
| Studio | `frontend/` | Playground, **Fhv1EnvelopeProfile** studio, and **Fhv1AuditTrace** explorer. Numbers on fhv1 surfaces use `String(value)`. |

Storage does not call Proxy. Bench does not own domain rules; it drives the proxy and the kernels.
