# CONTEXT-MAP

| Context | Path | Relationship |
| :--- | :--- | :--- |
| Kernels | `crates/sf-kernels` | Owns **AlignedVec1024**, **NoiseBitmask1024**, **DomainHypercubeLock**, cosine, and Tier-3 evaluation. |
| Storage | `crates/sf-storage` | Persists locks in LanceDB and publishes an `ArcSwap` registry. Depends on Kernels. |
| Proxy | `crates/sf-proxy` | **InputNormalizer**, **ClauseSegmenter**, TEI embedders, cascade, OpenAI ingress. Depends on Kernels and Storage. |
| Bench | `crates/sf-bench` | **SCPB-220** fixtures, OOS injection validation, and the load SLA. Depends on Kernels, Storage, and Proxy. |

Storage does not call Proxy. Bench does not own domain rules; it drives the proxy and the kernels.
