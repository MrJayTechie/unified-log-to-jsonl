#!/usr/bin/env python3
"""Convert MacOS.Live.UnifiedLog Velociraptor output into JSONL or CSV.

Output format is chosen by the destination file extension (.csv -> CSV,
anything else -> JSONL) or by an explicit --format flag.

JSONL mode emits Timesketch-canonical fields:
  - datetime          (ISO 8601, sorted on)
  - timestamp_desc    (short label describing what this timestamp means)
  - message           (free-text shown in the timeline)
plus the rest of the Velociraptor record as searchable / filterable fields.

CSV mode emits the same data with snake_case column names that match
IRFlow Timeline's column-recognition heuristics (process_name, message,
process_image_path, etc.).

Usage:
    unified_log_converter.py <input.zip|input.json> <output.jsonl|output.csv>
    unified_log_converter.py <input> <output> --format jsonl
    unified_log_converter.py <input> <output> --format csv

The input can be a Velociraptor collection ZIP (we'll find
results/MacOS.Live.UnifiedLog.json inside) or the raw NDJSON file.
"""
from __future__ import annotations

import argparse
import csv
import json
import zipfile
from pathlib import Path


JSON_PATH_IN_ZIP = "results/MacOS.Live.UnifiedLog.json"

# Column order for CSV mode. Lowercase snake_case so IRFlow Timeline's
# heuristics auto-detect process_name, message, etc.
CSV_COLUMNS = [
    "datetime",
    "timestamp_desc",
    "message",
    "category",
    "subsystem",
    "log_category",
    "event_type",
    "message_type",
    "process_image_path",
    "process_name",
    "pid",
    "sender_image_path",
    "activity_id",
    "parent_activity_id",
    "thread_id",
    "boot_uuid",
    "data_type",
    "source",
]

# Re-map snake_case internal keys to the CamelCase shape JSONL consumers
# (Timesketch dashboards, prior versions of this converter) expect.
JSONL_KEY_MAP = {
    "category":           "Category",
    "subsystem":          "Subsystem",
    "log_category":       "LogCategory",
    "event_type":         "EventType",
    "message_type":       "MessageType",
    "process_image_path": "ProcessImagePath",
    "process_name":       "ProcessName",
    "pid":                "PID",
    "sender_image_path":  "SenderImagePath",
    "activity_id":        "ActivityID",
    "parent_activity_id": "ParentActivityID",
    "thread_id":          "ThreadID",
    "boot_uuid":          "BootUUID",
}


def open_input(path: Path):
    if path.suffix == ".zip":
        z = zipfile.ZipFile(path)
        for name in (JSON_PATH_IN_ZIP, "results/MacOS.Collection.UnifiedLog.json"):
            if name in z.namelist():
                return z.open(name)
        raise SystemExit(
            f"Couldn't find unified-log results inside {path}. "
            f"Tried {JSON_PATH_IN_ZIP} and the legacy MacOS.Collection.* path."
        )
    return path.open("rb")


def transform(record: dict) -> dict | None:
    ts = record.get("EventTime")
    if not ts:
        return None

    category = record.get("Category", "unknown")
    proc = record.get("ProcessImagePath") or ""
    proc_name = proc.rsplit("/", 1)[-1] if proc else ""
    msg = record.get("EventMessage") or ""

    if proc_name and msg:
        message = f"[{proc_name}] {msg}"
    elif msg:
        message = msg
    else:
        message = f"<{category} event>"

    return {
        "datetime":           ts,
        "timestamp_desc":     f"Unified Log: {category}",
        "message":            message,
        "data_type":          "macos:unifiedlog:event",
        "source":             "MacOS.Live.UnifiedLog",
        "category":           category,
        "subsystem":          record.get("Subsystem", ""),
        "log_category":       record.get("LogCategory", ""),
        "event_type":         record.get("EventType", ""),
        "message_type":       record.get("MessageType") or "",
        "process_image_path": proc,
        "process_name":       proc_name,
        "pid":                record.get("PID"),
        "sender_image_path":  record.get("SenderImagePath", ""),
        "activity_id":        record.get("ActivityID"),
        "parent_activity_id": record.get("ParentActivityID"),
        "thread_id":          record.get("_ThreadID"),
        "boot_uuid":          record.get("_BootUUID", ""),
    }


def to_jsonl_keys(event: dict) -> dict:
    return {JSONL_KEY_MAP.get(k, k): v for k, v in event.items()}


def detect_format(dst: Path, override: str | None) -> str:
    if override:
        return override
    return "csv" if dst.suffix.lower() == ".csv" else "jsonl"


def iter_events(src: Path):
    dropped = 0
    with open_input(src) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                dropped += 1
                continue
            event = transform(rec)
            if event is None:
                dropped += 1
                continue
            yield event
    iter_events.dropped = dropped  # type: ignore[attr-defined]


def write_jsonl(events, dst: Path) -> int:
    kept = 0
    with dst.open("w") as out:
        for ev in events:
            out.write(json.dumps(to_jsonl_keys(ev)) + "\n")
            kept += 1
    return kept


def write_csv(events, dst: Path) -> int:
    kept = 0
    with dst.open("w", newline="") as out:
        writer = csv.DictWriter(
            out, fieldnames=CSV_COLUMNS, extrasaction="ignore",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        for ev in events:
            row = dict(ev)
            # Keep CSV strictly one row per event — strip embedded newlines.
            if isinstance(row.get("message"), str):
                row["message"] = row["message"].replace("\n", " ").replace("\r", " ")
            writer.writerow(row)
            kept += 1
    return kept


def main():
    parser = argparse.ArgumentParser(
        description="Convert MacOS.Live.UnifiedLog output into JSONL or CSV.",
    )
    parser.add_argument("input",  type=Path, help="Velociraptor collection .zip OR extracted .json")
    parser.add_argument("output", type=Path, help="Destination .jsonl or .csv")
    parser.add_argument(
        "--format", choices=["jsonl", "csv"],
        help="Override output format (default: inferred from output extension)",
    )
    args = parser.parse_args()

    fmt = detect_format(args.output, args.format)
    writer = write_csv if fmt == "csv" else write_jsonl

    iter_events.dropped = 0  # type: ignore[attr-defined]
    kept = writer(iter_events(args.input), args.output)
    dropped = getattr(iter_events, "dropped", 0)

    print(f"Wrote {kept} events to {args.output} as {fmt} (dropped {dropped})")


if __name__ == "__main__":
    main()
