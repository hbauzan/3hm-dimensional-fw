#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
#     "lancedb>=0.20.0",
#     "openpyxl>=3.1.5",
#     "pyarrow>=18.0.0",
# ]
# ///
"""Verify 0-ULP IEEE 754 binary64 bit parity across LanceDB, live HTTP JSON, and XLSX/CSV/Parquet exports."""

from __future__ import annotations

import argparse
import csv
import io
import json
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path

import httpx
import lancedb
import openpyxl
import pyarrow.parquet as pq

DIM = 1024
VECTOR_FIELDS = ("min", "max", "mean", "span", "variance", "std_dev")
ROGUE_DIMS = frozenset((292, 297, 308, 329, 386, 404, 577, 616, 780))


@dataclass
class ParityReport:
    profile_id: str
    policy_id: str
    normalize: bool
    sample_count: int
    envelope_floats_checked: int
    raw_sample_rows_checked: int
    raw_sample_floats_checked: int
    xlsx_parts: int


def f64_bits(value: float) -> bytes:
    return struct.pack("!d", float(value))


def bits_equal(a: float, b: float) -> bool:
    return f64_bits(a) == f64_bits(b)


def assert_bits_equal(context: str, got: float, expected: float) -> None:
    got_f = float(got)
    exp_f = float(expected)
    got_b = struct.pack("!d", got_f)
    exp_b = struct.pack("!d", exp_f)
    if got_b != exp_b:
        raise AssertionError(
            f"0-ULP mismatch at {context}: got={got_f!r} (0x{got_b.hex()}) "
            f"!= expected={exp_f!r} (0x{exp_b.hex()})"
        )


def _escape_sql(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def load_lancedb_profile(db: lancedb.DBConnection, profile_id: str) -> dict:
    table = db.open_table("fhv1_profiles")
    arrow = table.search(None).where(f"profile_id = {_escape_sql(profile_id)}").limit(None).to_arrow()
    if arrow.num_rows != 1:
        raise RuntimeError(f"expected 1 row in fhv1_profiles for {profile_id}, found {arrow.num_rows}")
    row = {col: arrow[col][0].as_py() for col in arrow.column_names}
    return row


def load_lancedb_samples(db: lancedb.DBConnection, profile_id: str) -> dict[str, dict]:
    table = db.open_table("fhv1_calibration_samples")
    arrow = table.search(None).where(f"profile_id = {_escape_sql(profile_id)}").limit(None).to_arrow()
    samples: dict[str, dict] = {}
    cols = arrow.column_names
    data = {col: arrow[col].to_pylist() for col in cols}
    for idx in range(arrow.num_rows):
        sid = data["sample_id"][idx]
        samples[sid] = {
            "sample_id": sid,
            "policy_id": data["policy_id"][idx],
            "strategy_tag": data["strategy_tag"][idx],
            "source_ref": data["source_ref"][idx],
            "raw_text": data["raw_text"][idx],
            "vector": data["vector"][idx],
        }
    return samples


def list_all_profiles(db: lancedb.DBConnection) -> list[dict]:
    table = db.open_table("fhv1_profiles")
    arrow = table.to_arrow()
    rows = []
    for idx in range(arrow.num_rows):
        rows.append(
            {
                "profile_id": arrow["profile_id"][idx].as_py(),
                "policy_id": arrow["policy_id"][idx].as_py(),
                "version": arrow["version"][idx].as_py(),
                "normalize": arrow["normalize"][idx].as_py(),
            }
        )
    return rows


def verify_profile_json(
    profile: dict,
    payload: dict,
) -> int:
    pid = profile["profile_id"]
    for key in ("profile_id", "policy_id", "version", "polarity", "normalize", "sample_count", "augmented_llm"):
        if payload.get(key) != profile[key]:
            raise AssertionError(f"{pid} JSON metadata mismatch for {key}: {payload.get(key)!r} != {profile[key]!r}")

    tiers = payload.get("movement_tier_codes")
    if tiers != profile["movement_tier_codes"]:
        raise AssertionError(f"{pid} JSON movement_tier_codes mismatch")

    checked = 0
    for field in VECTOR_FIELDS:
        lance_vec = profile[f"{field}_vector"]
        json_vec = payload.get(field)
        if not isinstance(json_vec, list) or len(json_vec) != DIM:
            raise AssertionError(f"{pid} JSON {field} length != {DIM}")
        for dim in range(DIM):
            assert_bits_equal(f"{pid} json.{field}[{dim}]", json_vec[dim], lance_vec[dim])
            checked += 1
    return checked


def verify_csv_export(profile: dict, raw_csv: bytes) -> int:
    pid = profile["profile_id"]
    reader = csv.DictReader(io.StringIO(raw_csv.decode("utf-8")))
    expected_cols = ["dim", "is_rogue_dim", *VECTOR_FIELDS, "movement_tier"]
    if reader.fieldnames != expected_cols:
        raise AssertionError(f"{pid} CSV header mismatch: {reader.fieldnames!r} != {expected_cols!r}")

    tiers = profile["movement_tier_codes"]
    rows = list(reader)
    if len(rows) != DIM:
        raise AssertionError(f"{pid} CSV row count {len(rows)} != {DIM}")

    checked = 0
    for dim, row in enumerate(rows):
        if int(row["dim"]) != dim:
            raise AssertionError(f"{pid} CSV dim mismatch at row {dim}: {row['dim']!r}")
        expected_rogue = 1 if dim in ROGUE_DIMS else 0
        if int(row["is_rogue_dim"]) != expected_rogue:
            raise AssertionError(f"{pid} CSV is_rogue_dim mismatch at dim {dim}")
        if int(row["movement_tier"]) != int(tiers[dim]):
            raise AssertionError(f"{pid} CSV movement_tier mismatch at dim {dim}")
        for field in VECTOR_FIELDS:
            assert_bits_equal(
                f"{pid} csv.{field}[{dim}]",
                float(row[field]),
                profile[f"{field}_vector"][dim],
            )
            checked += 1
    return checked


def verify_parquet_export(profile: dict, raw_parquet: bytes) -> int:
    pid = profile["profile_id"]
    table = pq.read_table(io.BytesIO(raw_parquet))
    if table.num_rows != DIM:
        raise AssertionError(f"{pid} Parquet row count {table.num_rows} != {DIM}")
    expected_cols = ["dim", "is_rogue_dim", *VECTOR_FIELDS, "movement_tier"]
    if table.column_names != expected_cols:
        raise AssertionError(f"{pid} Parquet columns mismatch: {table.column_names!r}")

    dims = table["dim"].to_pylist()
    rogues = table["is_rogue_dim"].to_pylist()
    tiers = table["movement_tier"].to_pylist()
    lance_tiers = profile["movement_tier_codes"]
    field_cols = {field: table[field].to_pylist() for field in VECTOR_FIELDS}

    checked = 0
    for dim in range(DIM):
        if int(dims[dim]) != dim:
            raise AssertionError(f"{pid} Parquet dim mismatch at row {dim}")
        if bool(rogues[dim]) != (dim in ROGUE_DIMS):
            raise AssertionError(f"{pid} Parquet is_rogue_dim mismatch at dim {dim}")
        if int(tiers[dim]) != int(lance_tiers[dim]):
            raise AssertionError(f"{pid} Parquet movement_tier mismatch at dim {dim}")
        for field in VECTOR_FIELDS:
            assert_bits_equal(
                f"{pid} parquet.{field}[{dim}]",
                field_cols[field][dim],
                profile[f"{field}_vector"][dim],
            )
            checked += 1
    return checked


def _verify_one_xlsx_bytes(
    profile: dict,
    samples_by_id: dict[str, dict],
    xlsx_bytes: bytes,
    part_label: str,
    seen_sample_ids: set[str],
    verify_raw_samples: bool,
) -> tuple[int, int, int]:
    pid = profile["profile_id"]
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), read_only=True, data_only=True)
    try:
        if "Summary_Envelope" not in wb.sheetnames or "Raw_Samples_Matrix" not in wb.sheetnames:
            raise AssertionError(f"{pid} {part_label} missing expected sheets: {wb.sheetnames!r}")

        summary_ws = wb["Summary_Envelope"]
        summary_rows = list(summary_ws.iter_rows(values_only=True))
        expected_summary_header = ("dim", "is_rogue_dim", *VECTOR_FIELDS, "movement_tier")
        if not summary_rows or tuple(summary_rows[0]) != expected_summary_header:
            raise AssertionError(
                f"{pid} {part_label} Summary_Envelope header mismatch: {summary_rows[0] if summary_rows else None!r}"
            )
        if len(summary_rows) != DIM + 1:
            raise AssertionError(
                f"{pid} {part_label} Summary_Envelope row count {len(summary_rows) - 1} != {DIM}"
            )

        tiers = profile["movement_tier_codes"]
        env_checked = 0
        for dim in range(DIM):
            row = summary_rows[dim + 1]
            if int(row[0]) != dim:
                raise AssertionError(f"{pid} {part_label} Summary_Envelope dim mismatch at row {dim}")
            if int(row[1]) != (1 if dim in ROGUE_DIMS else 0):
                raise AssertionError(f"{pid} {part_label} Summary_Envelope is_rogue_dim mismatch at dim {dim}")
            for offset, field in enumerate(VECTOR_FIELDS, start=2):
                assert_bits_equal(
                    f"{pid} {part_label}.Summary_Envelope.{field}[{dim}]",
                    row[offset],
                    profile[f"{field}_vector"][dim],
                )
                env_checked += 1
            if int(row[8]) != int(tiers[dim]):
                raise AssertionError(f"{pid} {part_label} Summary_Envelope movement_tier mismatch at dim {dim}")

        raw_ws = wb["Raw_Samples_Matrix"]
        raw_iter = raw_ws.iter_rows(values_only=True)
        raw_header = next(raw_iter, None)
        expected_raw_header = (
            "sample_id",
            "policy_id",
            "strategy_tag",
            "source_ref",
            "raw_text",
            *(f"dim_{d}" for d in range(DIM)),
        )
        if raw_header is None or tuple(raw_header) != expected_raw_header:
            raise AssertionError(f"{pid} {part_label} Raw_Samples_Matrix header mismatch")

        raw_rows = 0
        raw_floats = 0
        for row in raw_iter:
            sid = str(row[0])
            if sid in seen_sample_ids:
                raise AssertionError(f"{pid} {part_label} duplicate sample_id {sid}")
            if sid not in samples_by_id:
                raise AssertionError(f"{pid} {part_label} unknown sample_id {sid}")
            seen_sample_ids.add(sid)
            expected = samples_by_id[sid]
            if row[1] != expected["policy_id"]:
                raise AssertionError(f"{pid} {part_label} sample {sid} policy_id mismatch")
            if row[2] != expected["strategy_tag"]:
                raise AssertionError(f"{pid} {part_label} sample {sid} strategy_tag mismatch")
            if row[3] != expected["source_ref"]:
                raise AssertionError(f"{pid} {part_label} sample {sid} source_ref mismatch")
            cell_text = "" if row[4] is None else str(row[4])
            if cell_text != expected["raw_text"]:
                raise AssertionError(f"{pid} {part_label} sample {sid} raw_text mismatch")
            if verify_raw_samples:
                vec = expected["vector"]
                for dim in range(DIM):
                    assert_bits_equal(
                        f"{pid} {part_label}.Raw_Samples_Matrix[{sid}].dim_{dim}",
                        row[5 + dim],
                        vec[dim],
                    )
                    raw_floats += 1
            raw_rows += 1
        return env_checked, raw_rows, raw_floats
    finally:
        wb.close()


def verify_xlsx_or_zip_export(
    profile: dict,
    samples_by_id: dict[str, dict],
    raw_bytes: bytes,
    verify_raw_samples: bool,
) -> tuple[int, int, int, int]:
    pid = profile["profile_id"]
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
        names = zf.namelist()
    seen_sample_ids: set[str] = set()
    env_checked = 0
    raw_rows_total = 0
    raw_floats_total = 0

    if "xl/workbook.xml" in names:
        c_env, c_rows, c_floats = _verify_one_xlsx_bytes(
            profile,
            samples_by_id,
            raw_bytes,
            "xlsx",
            seen_sample_ids,
            verify_raw_samples,
        )
        env_checked += c_env
        raw_rows_total += c_rows
        raw_floats_total += c_floats
        parts = 1
    else:
        part_names = sorted(name for name in names if name.endswith(".xlsx"))
        if not part_names:
            raise AssertionError(f"{pid} ZIP export contained no .xlsx parts: {names!r}")
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            for part_name in part_names:
                c_env, c_rows, c_floats = _verify_one_xlsx_bytes(
                    profile,
                    samples_by_id,
                    zf.read(part_name),
                    part_name,
                    seen_sample_ids,
                    verify_raw_samples,
                )
                env_checked += c_env
                raw_rows_total += c_rows
                raw_floats_total += c_floats
        parts = len(part_names)

    if len(seen_sample_ids) != len(samples_by_id):
        raise AssertionError(
            f"{pid} XLSX Raw_Samples_Matrix row count {len(seen_sample_ids)} != LanceDB {len(samples_by_id)}"
        )
    return env_checked, raw_rows_total, raw_floats_total, parts


def verify_profile_exports(
    db: lancedb.DBConnection,
    base_url: str,
    out_dir: Path,
    profile_id: str,
    client: httpx.Client,
    *,
    skip_download: bool = False,
    verify_raw_samples: bool = True,
) -> ParityReport:
    out_dir.mkdir(parents=True, exist_ok=True)
    profile = load_lancedb_profile(db, profile_id)
    samples = load_lancedb_samples(db, profile_id)
    if len(samples) != int(profile["sample_count"]):
        raise AssertionError(
            f"{profile_id} sample_count={profile['sample_count']} != fhv1_calibration_samples rows={len(samples)}"
        )

    json_path = out_dir / f"{profile_id}.profile.json"
    csv_path = out_dir / f"{profile_id}.csv"
    parquet_path = out_dir / f"{profile_id}.parquet"
    xlsx_path = out_dir / f"{profile_id}.xlsx"
    zip_path = out_dir / f"{profile_id}.zip"

    if skip_download:
        profile_json = json.loads(json_path.read_text(encoding="utf-8"))
        csv_bytes = csv_path.read_bytes()
        parquet_bytes = parquet_path.read_bytes()
        xlsx_bytes = zip_path.read_bytes() if zip_path.is_file() else xlsx_path.read_bytes()
    else:
        base = base_url.rstrip("/")
        resp_json = client.get(f"{base}/api/v1/fhv1/profiles/{profile_id}")
        resp_json.raise_for_status()
        profile_json = resp_json.json()
        json_path.write_bytes(resp_json.content)

        resp_csv = client.get(f"{base}/api/v1/fhv1/profiles/{profile_id}/export", params={"format": "csv"})
        resp_csv.raise_for_status()
        csv_bytes = resp_csv.content
        csv_path.write_bytes(csv_bytes)

        resp_pq = client.get(f"{base}/api/v1/fhv1/profiles/{profile_id}/export", params={"format": "parquet"})
        resp_pq.raise_for_status()
        parquet_bytes = resp_pq.content
        parquet_path.write_bytes(parquet_bytes)

        resp_xlsx = client.get(f"{base}/api/v1/fhv1/profiles/{profile_id}/export", params={"format": "xlsx"})
        resp_xlsx.raise_for_status()
        xlsx_bytes = resp_xlsx.content
        content_type = resp_xlsx.headers.get("content-type", "")
        if "application/zip" in content_type:
            zip_path.write_bytes(xlsx_bytes)
        else:
            xlsx_path.write_bytes(xlsx_bytes)

    json_checked = verify_profile_json(profile, profile_json)
    csv_checked = verify_csv_export(profile, csv_bytes)
    pq_checked = verify_parquet_export(profile, parquet_bytes)
    xlsx_env_checked, raw_rows, raw_floats, xlsx_parts = verify_xlsx_or_zip_export(
        profile, samples, xlsx_bytes, verify_raw_samples
    )

    return ParityReport(
        profile_id=profile_id,
        policy_id=profile["policy_id"],
        normalize=bool(profile["normalize"]),
        sample_count=int(profile["sample_count"]),
        envelope_floats_checked=json_checked + csv_checked + pq_checked + xlsx_env_checked,
        raw_sample_rows_checked=raw_rows,
        raw_sample_floats_checked=raw_floats,
        xlsx_parts=xlsx_parts,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify 0-ULP IEEE 754 parity for fhv1 profile exports")
    parser.add_argument("--lancedb-uri", default="data/sf-lancedb")
    parser.add_argument("--base-url", default="http://127.0.0.1:8088")
    parser.add_argument("--out-dir", default="/tmp/fhv1_task011_exports")
    parser.add_argument("--profile-id", action="append", dest="profile_ids")
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--skip-raw-samples", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db = lancedb.connect(args.lancedb_uri)
    profile_ids = args.profile_ids
    if not profile_ids:
        all_profiles = list_all_profiles(db)
        norm_true = [p for p in all_profiles if p["normalize"]]
        norm_false = [p for p in all_profiles if not p["normalize"]]
        selected: list[str] = []
        if norm_true:
            selected.append(sorted(norm_true, key=lambda p: (p["policy_id"], -p["version"]))[0]["profile_id"])
        if norm_false:
            selected.append(sorted(norm_false, key=lambda p: (p["policy_id"], -p["version"]))[0]["profile_id"])
        profile_ids = selected or [p["profile_id"] for p in all_profiles]
    if not profile_ids:
        raise SystemExit("no fhv1_profiles rows found")

    out_dir = Path(args.out_dir)
    with httpx.Client(timeout=300.0) as client:
        for pid in profile_ids:
            report = verify_profile_exports(
                db,
                args.base_url,
                out_dir,
                pid,
                client,
                skip_download=args.skip_download,
                verify_raw_samples=not args.skip_raw_samples,
            )
            print(
                f"0-ULP PASS profile_id={report.profile_id} policy_id={report.policy_id} "
                f"normalize={str(report.normalize).lower()} samples={report.sample_count} "
                f"envelope_floats={report.envelope_floats_checked} raw_rows={report.raw_sample_rows_checked} "
                f"raw_floats={report.raw_sample_floats_checked} xlsx_parts={report.xlsx_parts} max_ulp=0",
                flush=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
