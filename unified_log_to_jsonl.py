#!/usr/bin/env python3
"""Convert unified-log Velociraptor output into Timesketch JSONL.

Timesketch needs each event to have:
  - datetime          (ISO 8601, sorted on)
  - timestamp_desc    (short label describing what this timestamp means)
  - message           (free-text shown in the timeline)

Everything else is preserved as a searchable field.

Usage:
    python timesketch_convert.py <input.zip|input.json> <output.jsonl>

The input can be a Velociraptor collection ZIP (we'll find
results/MacOS.Live.UnifiedLog.json inside) or the raw NDJSON file.
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path


JSON_PATH_IN_ZIP = "results/MacOS.Live.UnifiedLog.json"


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
    # Drop rows with no timestamp — Timesketch refuses them anyway.
    ts = record.get("EventTime")
    if not ts:
        return None

    category = record.get("Category", "unknown")
    proc = record.get("ProcessImagePath") or ""
    proc_name = proc.rsplit("/", 1)[-1] if proc else ""
    msg = record.get("EventMessage") or ""

    # Build a short, scannable message line. Process name first so it shows
    # up at the start of every timeline row.
    if proc_name and msg:
        message = f"[{proc_name}] {msg}"
    elif msg:
        message = msg
    else:
        message = f"<{category} event>"

    return {
        "datetime": ts,
        "timestamp_desc": f"Unified Log: {category}",
        "message": message,
        "data_type": "macos:unifiedlog:event",
        "source": "MacOS.Live.UnifiedLog",
        # Preserve the rest as searchable / filterable fields.
        "Category":          category,
        "Subsystem":         record.get("Subsystem", ""),
        "LogCategory":       record.get("LogCategory", ""),
        "EventType":         record.get("EventType", ""),
        "MessageType":       record.get("MessageType") or "",
        "ProcessImagePath":  proc,
        "ProcessName":       proc_name,
        "PID":               record.get("PID"),
        "SenderImagePath":   record.get("SenderImagePath", ""),
        "ActivityID":        record.get("ActivityID"),
        "ParentActivityID":  record.get("ParentActivityID"),
        "ThreadID":          record.get("_ThreadID"),
        "BootUUID":          record.get("_BootUUID", ""),
    }


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])

    kept = 0
    dropped = 0
    with open_input(src) as fh, dst.open("w") as out:
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
            out.write(json.dumps(event) + "\n")
            kept += 1

    print(f"Wrote {kept} events to {dst} (dropped {dropped})")


if __name__ == "__main__":
    main()
