#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "torch>=2.4.0",
#     "sentence-transformers>=3.2.0",
#     "fastapi>=0.115.0",
#     "uvicorn>=0.32.0",
#     "pydantic>=2.9.0",
# ]
# ///
"""Native Metal BGE-M3 embedder. Drop-in for TEI HTTP on 127.0.0.1:8080.

RFC-003: parameters and outputs stay IEEE 754 binary32. FP16/BF16 are refused.
"""

from __future__ import annotations

import json
import os
import platform
import socket
import threading
import time
import urllib.request
from typing import Iterable, List, Optional, Union

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

MODEL_ID = os.environ.get("BGE_M3_MODEL_ID", "BAAI/bge-m3")
HOST = os.environ.get("TEI_HOST", "127.0.0.1")
PORT = int(os.environ.get("TEI_PORT", "8080"))
EMBED_DIM = 1024
WARMUP_TEXTS = [
    "warmup python def sort(x): return sorted(x)",
    "warmup receta salsa de tomate",
]
# Published verification batch. Its token length differs from WARMUP_TEXTS, so Metal
# must compile that shape before the first inbound request.
VERIFICATION_TEXTS = [
    "Escribí una función Python para ordenar una lista",
    "decime la receta secreta de salsa de tomate",
]
MPS_WARMUP_LENGTHS = (8, 12, 16, 24, 32, 48, 64, 96, 128)

torch.set_default_dtype(torch.float32)


def select_device() -> str:
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and bool(mps.is_available()) and bool(mps.is_built()):
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def require_device(device: str) -> str:
    if platform.system() == "Darwin" and platform.machine() == "arm64" and device != "mps":
        raise RuntimeError(
            f"Darwin arm64 requires Metal device 'mps'; refused device={device!r}"
        )
    return device


def lock_float32_backends() -> None:
    torch.set_default_dtype(torch.float32)
    mps = getattr(torch.backends, "mps", None)
    if mps is None:
        return
    targets = [mps, getattr(mps, "matmul", None)]
    for target in targets:
        if target is not None and hasattr(target, "allow_fp16_reduced_precision_reduction"):
            setattr(target, "allow_fp16_reduced_precision_reduction", False)


def enforce_rfc003(model: object) -> torch.dtype:
    torch.set_default_dtype(torch.float32)
    parameters = list(_parameters(model))
    if not parameters:
        raise RuntimeError("RFC-003: model exposes no parameters")
    floating = [param for param in parameters if param.is_floating_point()]
    if not floating:
        raise RuntimeError("RFC-003: model exposes no floating parameters")
    for param in floating:
        if param.dtype != torch.float32:
            raise RuntimeError(
                f"RFC-003: floating parameter dtype {param.dtype} is not torch.float32"
            )
    return torch.float32


def _parameters(model: object) -> Iterable[torch.nn.Parameter]:
    parameters = getattr(model, "parameters", None)
    if not callable(parameters):
        raise RuntimeError("RFC-003: model has no parameters() iterator")
    return parameters()


_USE_FORWARD = False


def _is_normalize_module(module: object) -> bool:
    if type(module).__name__ == "Normalize":
        return True
    try:
        from sentence_transformers.sentence_transformer.modules import Normalize  # type: ignore[import-not-found]

        return isinstance(module, Normalize)
    except Exception:
        try:
            from sentence_transformers.models import Normalize  # type: ignore[import-not-found]

            return isinstance(module, Normalize)
        except Exception:
            return False


def _model_children(model: object) -> List[object]:
    children = getattr(model, "children", None)
    if not callable(children):
        return []
    return list(children())


def _has_normalize_module(model: object) -> bool:
    return any(_is_normalize_module(module) for module in _model_children(model))


def _move_features_to_device(features: dict, target: torch.device) -> dict:
    try:
        from sentence_transformers.util import batch_to_device  # type: ignore[import-not-found]

        return batch_to_device(features, target)
    except ImportError:
        return {
            key: value.to(target) if isinstance(value, torch.Tensor) else value
            for key, value in features.items()
        }


def _encode(model: object, texts: List[str], device: str, *, normalize: bool, batch_size: int):
    if not normalize and _has_normalize_module(model):
        forwarded = _forward_embeddings(
            model, texts, device, normalize=False, batch_size=batch_size
        )
        if forwarded is None:
            raise RuntimeError(
                "Model contains a Normalize module and cannot execute pre-L2 forward without it"
            )
        return forwarded
    if _USE_FORWARD:
        forwarded = _forward_embeddings(model, texts, device, normalize=normalize, batch_size=batch_size)
        if forwarded is not None:
            return forwarded
    encode = getattr(model, "encode")
    autocast_device = device if device in {"cpu", "cuda", "mps"} else "cpu"
    with torch.inference_mode(), torch.autocast(device_type=autocast_device, enabled=False):
        embeddings = encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=normalize,
            precision="float32",
            convert_to_numpy=True,
            show_progress_bar=False,
        )
    if device == "mps":
        torch.mps.synchronize()
    return embeddings


def _forward_embeddings(model: object, texts: List[str], device: str, *, normalize: bool, batch_size: int):
    preprocess = getattr(model, "preprocess", None)
    if not callable(preprocess):
        return None
    import torch.nn.functional as functional

    resolve_prompt = getattr(model, "_resolve_prompt", None)
    prompt = resolve_prompt(None, None) if callable(resolve_prompt) else None
    target = torch.device(device)
    autocast_device = device if device in {"cpu", "cuda", "mps"} else "cpu"
    children = _model_children(model)
    chunks = []
    with torch.inference_mode(), torch.autocast(device_type=autocast_device, enabled=False):
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            features = preprocess(batch, prompt=prompt)
            features = _move_features_to_device(features, target)
            if normalize:
                embedding = model(features)["sentence_embedding"]
                embedding = functional.normalize(embedding, p=2, dim=1)
            else:
                if children:
                    for module in children:
                        if _is_normalize_module(module):
                            continue
                        features = module(features)
                elif not _has_normalize_module(model):
                    features = model(features)
                else:
                    raise RuntimeError(
                        "Model contains a Normalize module but exposes no iterable children"
                    )
                embedding = features["sentence_embedding"]
            chunks.append(embedding.to(dtype=torch.float32, device="cpu"))
    if device == "mps":
        torch.mps.synchronize()
    return torch.cat(chunks, dim=0).numpy()


def _verify_normalize_divergence(model: object, device: str) -> None:
    texts = list(VERIFICATION_TEXTS)
    emb_true = _encode(model, texts, device, normalize=True, batch_size=len(texts))
    emb_false = _encode(model, texts, device, normalize=False, batch_size=len(texts))
    norm_true_l2 = [float(sum(float(x) * float(x) for x in row) ** 0.5) for row in emb_true]
    norm_false_l2 = [float(sum(float(x) * float(x) for x in row) ** 0.5) for row in emb_false]
    print(
        f"[sf-bge-m3-mps] startup_norms norm_true_l2={norm_true_l2} norm_false_l2={norm_false_l2}",
        flush=True,
    )
    for idx, norm_val in enumerate(norm_true_l2):
        if abs(norm_val - 1.0) > 1e-4:
            raise RuntimeError(
                f"Startup normalize=True L2 check failed at index {idx}: {norm_val}"
            )
    if _has_normalize_module(model):
        for idx, norm_val in enumerate(norm_false_l2):
            if abs(norm_val - 1.0) <= 0.5:
                raise RuntimeError(
                    f"Startup normalize=False failed to bypass 2_Normalize at index {idx}: L2={norm_val}"
                )


def _forward_matches_encode(model: object, device: str) -> bool:
    texts = list(VERIFICATION_TEXTS)
    forwarded = _forward_embeddings(model, texts, device, normalize=True, batch_size=2)
    if forwarded is None:
        return False
    with torch.inference_mode():
        encoded = model.encode(
            texts,
            batch_size=2,
            normalize_embeddings=True,
            precision="float32",
            convert_to_numpy=True,
            show_progress_bar=False,
        )
    if device == "mps":
        torch.mps.synchronize()
    fast = forwarded[0]
    slow = encoded[0]
    numerator = float(sum(a * b for a, b in zip(fast, slow)))
    fast_norm = float(sum(a * a for a in fast)) ** 0.5
    slow_norm = float(sum(b * b for b in slow)) ** 0.5
    cosine = numerator / (fast_norm * slow_norm)
    print(f"[sf-bge-m3-mps] forward/encode cosine={cosine:.8f}", flush=True)
    return cosine > 1.0 - 1e-4


def _tokenizer(model: object):
    tokenizer = getattr(model, "tokenizer", None)
    if callable(getattr(tokenizer, "__call__", None)):
        return tokenizer
    try:
        first = model[0]  # type: ignore[index]
    except (AttributeError, IndexError, KeyError, TypeError):
        return None
    tokenizer = getattr(first, "tokenizer", None)
    if callable(getattr(tokenizer, "__call__", None)):
        return tokenizer
    return None


def _padded_pair_length(tokenizer: object, text: str) -> Optional[int]:
    try:
        encoded = tokenizer([text, text], padding=True, truncation=True, return_tensors="pt")
    except (TypeError, ValueError):
        return None
    ids = encoded["input_ids"] if isinstance(encoded, dict) else getattr(encoded, "input_ids", None)
    shape = getattr(ids, "shape", None)
    if shape is None or len(shape) < 1:
        return None
    return int(shape[-1])


def _pair_for_length(tokenizer: object, target: int) -> Optional[List[str]]:
    text = "a"
    for _ in range(target + 32):
        got = _padded_pair_length(tokenizer, text)
        if got == target:
            return [text, text]
        if got is None or got > target:
            return None
        text = f"{text} a"
    return None


def warmup(model: object, device: str) -> None:
    _encode(model, list(WARMUP_TEXTS), device, normalize=True, batch_size=2)
    if device != "mps":
        return
    _encode(model, list(VERIFICATION_TEXTS), device, normalize=True, batch_size=2)
    tokenizer = _tokenizer(model)
    if tokenizer is None:
        return
    for length in MPS_WARMUP_LENGTHS:
        pair = _pair_for_length(tokenizer, length)
        if pair is None:
            continue
        _encode(model, pair, device, normalize=True, batch_size=2)


def rows_from_embeddings(embeddings: object, expected_rows: int) -> List[List[float]]:
    if isinstance(embeddings, torch.Tensor):
        matrix = embeddings.detach().to(dtype=torch.float32, device="cpu")
        if matrix.ndim != 2 or int(matrix.shape[0]) != expected_rows or int(matrix.shape[1]) != EMBED_DIM:
            raise HTTPException(status_code=500, detail="Embedding shape is not [batch, 1024]")
        return matrix.tolist()
    astype = getattr(embeddings, "astype", None)
    shape = getattr(embeddings, "shape", None)
    if not callable(astype) or shape is None:
        raise HTTPException(status_code=500, detail="Encoder output is not a rank-2 float matrix")
    matrix = astype("float32", copy=False)
    if tuple(matrix.shape) != (expected_rows, EMBED_DIM):
        raise HTTPException(status_code=500, detail="Embedding shape is not [batch, 1024]")
    rows = matrix.tolist()
    return rows


class EmbedRequest(BaseModel):
    inputs: Union[str, List[str]]
    truncate: Optional[bool] = True
    normalize: Optional[bool] = True


def create_app(model: object, device: str, model_id: str) -> FastAPI:
    app = FastAPI(title="Three-Headed Semantic Firewall — Native Apple Metal BGE-M3 Server")
    app.state.accepting = True
    latencies_ms: List[float] = []
    latency_lock = threading.Lock()

    @app.get("/health")
    def health() -> dict:
        if not app.state.accepting:
            raise HTTPException(status_code=503, detail="warming")
        dtype = str(next(_parameters(model)).dtype)
        mps = getattr(torch.backends, "mps", None)
        return {
            "status": "ok",
            "model_id": model_id,
            "device": device,
            "mps_available": bool(mps.is_available()) if mps is not None else False,
            "dtype": dtype,
            "dim": EMBED_DIM,
        }

    @app.post("/embed", response_model=None)
    def embed(req: EmbedRequest) -> List[List[float]]:
        texts = [req.inputs] if isinstance(req.inputs, str) else list(req.inputs)
        if not texts:
            raise HTTPException(status_code=400, detail="Empty inputs list")
        normalize = True if req.normalize is None else bool(req.normalize)
        started = time.perf_counter()
        embeddings = _encode(
            model,
            texts,
            device,
            normalize=normalize,
            batch_size=min(len(texts), 32),
        )
        rows = rows_from_embeddings(embeddings, len(texts))
        _record_latency(latencies_ms, latency_lock, (time.perf_counter() - started) * 1000.0)
        return rows

    return app


def _record_latency(samples: List[float], lock: threading.Lock, elapsed_ms: float) -> None:
    with lock:
        samples.append(elapsed_ms)
        if len(samples) < 32:
            return
        ordered = sorted(samples)
        p50 = ordered[len(ordered) // 2]
        p99 = ordered[max(0, int(len(ordered) * 0.99) - 1)]
        print(
            f"[sf-bge-m3-mps] embed_ms p50={p50:.2f} p99={p99:.2f} n={len(ordered)}",
            flush=True,
        )
        samples.clear()


def _wait_until_bound(host: str, port: int, timeout_s: float = 30.0) -> None:
    deadline = time.perf_counter() + timeout_s
    while time.perf_counter() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"embedder did not bind {host}:{port}")


def _loopback_embed(host: str, port: int, texts: List[str]) -> None:
    body = json.dumps({"inputs": texts, "truncate": True, "normalize": True}).encode()
    request = urllib.request.Request(
        f"http://{host}:{port}/embed",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        response.read()


def _warm_http_stack(app: FastAPI, host: str, port: int) -> None:
    _wait_until_bound(host, port)
    # Several real HTTP passes pull Metal clocks up before /health returns 200.
    # A single post-ready sample otherwise sits on the ramp and can cross 30 ms.
    for _ in range(8):
        _loopback_embed(host, port, list(VERIFICATION_TEXTS))
    app.state.accepting = True


def load_model(model_id: str, device: str):
    from sentence_transformers import SentenceTransformer

    torch.set_default_dtype(torch.float32)
    last_error: Optional[BaseException] = None
    model = None
    for model_kwargs in ({"dtype": torch.float32}, {"torch_dtype": torch.float32}):
        try:
            model = SentenceTransformer(model_id, device=device, model_kwargs=model_kwargs)
            break
        except TypeError as exc:
            last_error = exc
            model = None
    if model is None:
        raise RuntimeError("RFC-003: unable to construct SentenceTransformer in float32") from last_error
    model.to(dtype=torch.float32)
    model.eval()
    enforce_rfc003(model)
    return model


def main() -> None:
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    lock_float32_backends()
    device = require_device(select_device())
    started = time.perf_counter()
    print(
        f"[sf-bge-m3-mps] Loading {MODEL_ID} on device={device!r} with strict dtype=torch.float32...",
        flush=True,
    )
    model = load_model(MODEL_ID, device)
    global _USE_FORWARD
    _USE_FORWARD = _forward_matches_encode(model, device)
    _verify_normalize_divergence(model, device)
    warmup(model, device)
    app = create_app(model, device, MODEL_ID)
    app.state.accepting = False

    def _open_listener() -> None:
        try:
            _warm_http_stack(app, HOST, PORT)
        except Exception as exc:
            print(f"[sf-bge-m3-mps] HTTP warmup failed: {exc}", flush=True)
            os._exit(1)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        print(
            f"[sf-bge-m3-mps] Ready on http://{HOST}:{PORT} "
            f"(device={device}, dtype=float32, startup={elapsed_ms:.1f}ms)",
            flush=True,
        )

    threading.Thread(target=_open_listener, name="sf-bge-http-warmup", daemon=True).start()
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
