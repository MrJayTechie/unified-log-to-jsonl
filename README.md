# unified-log-to-jsonl

Convert macOS Unified Log output collected by the
[`MacOS.Live.UnifiedLog`](https://github.com/MrJayTechie/MacOS-Velociraptor-Collectors/blob/main/Collectors/Live/UnifiedLog.yaml)
Velociraptor artifact into [Timesketch](https://timesketch.org)-ingestible
JSONL.

## Why

The artifact emits events in Velociraptor's natural record shape
(`EventTime`, `EventMessage`, `Category`, `ProcessImagePath`, etc.). That
schema is Splunk-friendly out of the box but Timesketch rejects it because
it expects three specific fields (`datetime`, `message`, `timestamp_desc`).

This converter is a tiny adapter that reshapes the events without losing
information. It does not parse, dedupe, or filter.

## Pipeline

```
+------------------+    +---------------+    +-------------+
| MacOS-Velo-      |    | Dissectify    |    | this        |
| Collectors       | -> | (build + run) | -> | converter   |
| (artifact YAML)  |    |               |    |             |
+------------------+    +---------------+    +-------------+
                                                    |
                                                    v
                                            +---------------+
                                            | Timesketch    |
                                            | (analyst UI)  |
                                            +---------------+
```

## Usage

```bash
# From a Velociraptor collection zip
python3 unified_log_to_jsonl.py \
    /path/to/UnifiedLog-<host>-<ts>.zip \
    /path/to/timeline.jsonl

# Or from the already-extracted results JSON
python3 unified_log_to_jsonl.py \
    /path/to/results/MacOS.Live.UnifiedLog.json \
    /path/to/timeline.jsonl
```

Output is plain newline-delimited JSON. Upload it via the Timesketch web
UI ("Upload timeline") or `timesketch_importer`.

> **Tip:** Velociraptor collections are usually owned by `root`. Run
> `sudo chown $(whoami) <file>` before invoking the converter, or run the
> converter itself with `sudo`.

## Field mapping

| Source field        | Target field      | Notes                               |
|---------------------|-------------------|-------------------------------------|
| `EventTime`         | `datetime`        | ISO 8601, used by Timesketch sort   |
| `EventMessage`      | `message`         | Prefixed with `[ProcessName]` when present |
| (computed)          | `timestamp_desc`  | `Unified Log: <Category>`           |
| `Category`          | `Category`        | Preserved                           |
| `Subsystem`         | `Subsystem`       | Preserved                           |
| `LogCategory`       | `LogCategory`     | Preserved                           |
| `EventType`         | `EventType`       | Preserved                           |
| `MessageType`       | `MessageType`     | Preserved                           |
| `ProcessImagePath`  | `ProcessImagePath`| Preserved                           |
| (computed)          | `ProcessName`     | Basename of `ProcessImagePath`      |
| `PID`               | `PID`             | Preserved                           |
| `SenderImagePath`   | `SenderImagePath` | Preserved                           |
| `ActivityID`        | `ActivityID`      | Preserved                           |
| `ParentActivityID`  | `ParentActivityID`| Preserved                           |
| `_ThreadID`         | `ThreadID`        | Preserved                           |
| `_BootUUID`         | `BootUUID`        | Preserved                           |
| (computed)          | `data_type`       | `macos:unifiedlog:event`            |
| (computed)          | `source`          | `MacOS.Live.UnifiedLog`             |

Events with no `EventTime` are dropped (Timesketch refuses them anyway).

## Example Timesketch queries

After upload, useful starting points in the Timesketch search bar:

| Question                          | Query                                          |
|-----------------------------------|------------------------------------------------|
| Sudo failures                     | `Category:auth_sudo AND message:"3 incorrect"` |
| TCC denials                       | `Category:tcc AND message:deny`                |
| Lock-screen failed unlocks        | `Category:auth_result AND message:authFail*`   |
| Anything from `screensharingd`    | `ProcessName:screensharingd`                   |
| Gatekeeper exec rejections        | `Category:gatekeeper AND message:reject*`      |
| All authentication categories     | `Category:auth_*`                              |

## Related

- Artifact: [`MacOS.Live.UnifiedLog`](https://github.com/MrJayTechie/MacOS-Velociraptor-Collectors/blob/main/Collectors/Live/UnifiedLog.yaml)
- Build / run TUI: [Dissectify](https://github.com/MrJayTechie/Dissectify)
- Timesketch: <https://timesketch.org>
