# Spec: survive HWiNFO starting, stopping and restarting its log

**Status:** approved by JJ 2026-10-14 10:40, with the addition below · **Owner:** deneb (workstation monitor) · 2026-10-14

## Why

JJ, 2026-10-09: *"Hardware Info TUI needs to be relaunched because if I start writing to a CSV file after it has been loaded, it doesn't catch that."*
JJ, 2026-10-14: *"I would like an agent to work on bringing those fixes that Deneb has included into its own script, but to bring them into HWiNFO-TUI."*

Today `hwinfo-tui monitor` assumes the CSV exists, is being written, and keeps growing for the whole run. Three things break that:

1. **The CSV isn't there yet** (HWiNFO not logging at logon): `monitor` exits with "file not found".
2. **HWiNFO restarts its log** (stop/start logging, HWiNFO restart): the file is truncated or recreated. `CSVReader.read_new_data` keeps seeking to the old `last_position`, past the new end, and reads nothing forever. The chart freezes with no hint why.
3. **HWiNFO stops logging**: the chart silently freezes on the last values, which read as live.

The vault works around all three with a wrapper, `second-brain/scripts/monitor/hwinfo-pane.ps1`, that waits for a fresh file, launches hwinfo-tui, and kills and relaunches it whenever the file goes stale or is recreated. The fix belongs in the tool, so every user gets it and the wrapper can be deleted.

## Outcome

`hwinfo-tui monitor <csv> <sensors…>` can be started before HWiNFO logs, and keeps showing live data across any number of log stops, restarts and recreations, with no relaunch. When data isn't flowing, the screen says so.

## Behaviour

- **Never crash on a bad file; keep waiting until it makes sense** (JJ's addition at approval: *"it should work even if the file does not exist or if the file is corrupted. You should continue watching until it makes sense and has fresh data."*). A missing file, an empty file, a header that can't be decoded or parsed, a header with none of the requested sensors yet, or a half-written last line all mean the same thing: show the waiting screen with the reason, keep polling, and start once the file has a usable header, the sensors and at least one row. If those rows are old (HWiNFO isn't logging), the data shows under the stale marker below, which stays until fresh rows arrive. *Built that way rather than holding a blank screen for fresh rows, so an archived log (and the repo's own sample CSV) can still be opened.* Malformed rows inside a good file are skipped, as they are today.
- **Waiting for the log.** If the CSV is missing or empty at start, `monitor` doesn't exit: it shows a waiting screen naming the file ("Waiting for HWiNFO to log to <path> — Sensors > Logging start"), polls, and starts normally once the file has a header and rows. Sensor matching and unit filtering run then, against the real header. A sensor name that matches nothing keeps waiting too, naming the missing sensors, since a restarted log can bring them back.
- **Log restarted.** The reader detects that the file was recreated or truncated (size below `last_position`, or a changed creation time / file identity). It then re-reads the header with the existing encoding fallback, re-maps the requested sensors to the new columns (HWiNFO can reorder columns between runs), and continues from the new file's start. History already on screen is cleared, because the old timestamps belong to a different log.
- **Log stopped (stale).** If no new row has arrived for `--stale-after` seconds (default 15, the wrapper's value), the header shows a clear "stale: no data for Ns" marker and the chart stops advancing. When rows resume, the marker clears with no action.
- **File deleted mid-run.** This is treated as "waiting for the log" with the history kept on screen. When the file reappears, the restart path above runs.
- `list-sensors` is unchanged: it still needs an existing file.

## Interface

- `monitor`'s `CSV_FILE` argument no longer requires the file to exist (typer `exists=True` removed for `monitor` only).
- New option `--stale-after SECONDS` (int, 3–3600, default 15).
- No other flags change, and the defaults keep today's behaviour for a healthy, growing log.

## Where it goes

- `data/csv_reader.py`: the file-identity check (size, creation time) in `read_new_data`, a `reopen()` that re-reads headers and re-maps sensors, and a `seconds_since_last_row` property. The reader has to survive a missing file, not just raise in `__init__`.
- `main.py` / `cli.py`: the waiting state before `initialize`; sensor validation moves after the first readable header; the stale marker passed to the layout.
- `display/layout.py`: render the waiting and stale states in the existing header line.

## Acceptance (each one a test that fails before the change)

1. Start `monitor` on a path that doesn't exist, then create the CSV with a header and rows: the app picks it up within 2 refreshes, without a restart.
2. Truncate the CSV to its header and append new rows: the new rows appear, and nothing before the truncation does.
3. Delete and recreate the CSV with columns in a different order: each sensor still shows its own column's values.
4. Stop appending for longer than `--stale-after`: the stale marker shows. Append again: it clears.
5. A file of garbage bytes, or a header with no matching sensors, keeps the app waiting without an exception. Replacing it with a good, fresh log starts the app.
6. A healthy growing file behaves exactly as today (the existing tests pass unchanged).
7. Tested by unit tests on `CSVReader` against temp files. No HWiNFO needed.

## Not in scope

- Direct sensor access without the CSV (that's a separate someday idea in the vault's HWInfo-TUI note).
- Any change to `list-sensors`, the chart, or units.
- A release: version bump, CHANGELOG, PyPI and WinGet come after JJ sees it working. Nothing is pushed without his OK.

## After it ships

`second-brain/scripts/herdr-monitor.ps1` runs `hwinfo-tui monitor` directly, and `scripts/monitor/hwinfo-pane.ps1` is deleted (vault side, deneb).
