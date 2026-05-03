# unified-log-converter

Convert macOS Unified Log output collected by the
[`MacOS.Live.UnifiedLog`](https://github.com/MrJayTechie/MacOS-Velociraptor-Collectors/blob/main/Collectors/Live/UnifiedLog.yaml)
Velociraptor artifact into **JSONL** or **CSV** format.

## Why

The artifact emits events in Velociraptor's natural record shape
(`EventTime`, `EventMessage`, `Category`, `ProcessImagePath`, etc.). That
schema is fine for storage and for tools like Splunk that auto-extract
JSON keys, but most analyst-facing timeline tools want either canonical
JSONL fields (`datetime`, `message`, `timestamp_desc`) or tabular CSV.

This converter is a thin adapter — no parsing, deduping, or filtering;
just reshapes events without losing information.

## Pipeline

```
+------------------+    +---------------+    +-------------+
| MacOS-Velo-      |    | Dissectify    |    | this        |
| Collectors       | -> | (build + run) | -> | converter   |
| (artifact YAML)  |    |               |    |             |
+------------------+    +---------------+    +-------------+
                                                    |
                                                    v
                                       +--------------------------+
                                       | Analyst tool (your pick) |
                                       +--------------------------+
```

## Usage

```bash
# JSONL output (output extension drives the format)
python3 unified_log_converter.py \
    /path/to/UnifiedLog-<host>-<ts>.zip \
    /path/to/timeline.jsonl

# CSV output
python3 unified_log_converter.py \
    /path/to/UnifiedLog-<host>-<ts>.zip \
    /path/to/timeline.csv

# Same input, explicit format override
python3 unified_log_converter.py input.json output.txt --format jsonl

# Already-extracted results JSON also works as input
python3 unified_log_converter.py \
    /path/to/results/MacOS.Live.UnifiedLog.json \
    /path/to/timeline.jsonl
```

> **Tip:** Velociraptor collections are usually owned by `root`. Run
> `sudo chown $(whoami) <file>` before invoking the converter, or run it
> with `sudo`.

## Output formats

### JSONL

One JSON object per line. Field names follow the convention used by
Velociraptor's record viewers and prior versions of this script
(CamelCase like `Category`, `Subsystem`, `ProcessImagePath`) plus the
three Timesketch-canonical fields at the top of every event:

| Field            | Source              | Notes                                |
|------------------|---------------------|--------------------------------------|
| `datetime`       | `EventTime`         | ISO 8601                             |
| `timestamp_desc` | (computed)          | `Unified Log: <Category>`            |
| `message`        | `EventMessage`      | Prefixed with `[ProcessName]`        |
| `Category`       | preserved           |                                      |
| `Subsystem`      | preserved           |                                      |
| `LogCategory`    | preserved           |                                      |
| `EventType`      | preserved           |                                      |
| `MessageType`    | preserved           |                                      |
| `ProcessImagePath`| preserved          |                                      |
| `ProcessName`    | (computed basename) |                                      |
| `PID`            | preserved           |                                      |
| `SenderImagePath`| preserved           |                                      |
| `ActivityID`     | preserved           |                                      |
| `ParentActivityID`| preserved          |                                      |
| `ThreadID`       | preserved (`_ThreadID`) |                                  |
| `BootUUID`       | preserved (`_BootUUID`) |                                  |
| `data_type`      | (computed)          | `macos:unifiedlog:event`             |
| `source`         | (computed)          | `MacOS.Live.UnifiedLog`              |

### CSV

Tabular form with snake_case column names so tools that auto-detect
common forensic columns (`process_name`, `image`, `message`, etc.) pick
them up without manual mapping.

Column order:

```
datetime, timestamp_desc, message, category, subsystem, log_category,
event_type, message_type, process_image_path, process_name, pid,
sender_image_path, activity_id, parent_activity_id, thread_id, boot_uuid,
data_type, source
```

Embedded newlines in `message` are stripped to keep one row per event.

## Compatible analyst tools

Both output formats are deliberately generic. Confirmed working with:

- **JSONL** — [Timesketch](https://timesketch.org), `jq`, OpenSearch /
  Elasticsearch ingest, Splunk (HEC or monitor stanza), pandas
  (`read_json(lines=True)`).
- **CSV** — [IRFlow Timeline](https://github.com/r3nzsec/irflow-timeline),
  Excel, Numbers, Splunk (`csv` sourcetype), pandas (`read_csv`).

Other timeline / SIEM tools that consume JSONL or CSV should also work —
the schema is intentionally tool-agnostic.

## Events with no timestamp

Dropped on conversion. The reported `dropped` count after each run is
how many records lacked an `EventTime` field. Most timeline tools refuse
events with no timestamp anyway; doing it at conversion time keeps the
output clean.

## Related

- Artifact: [`MacOS.Live.UnifiedLog`](https://github.com/MrJayTechie/MacOS-Velociraptor-Collectors/blob/main/Collectors/Live/UnifiedLog.yaml)
- Build / run TUI: [Dissectify](https://github.com/MrJayTechie/Dissectify)
