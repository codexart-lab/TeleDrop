# TeleDrop Batch Upgrade — Design Spec

Date: 2026-09-29
Status: conversational design approved; awaiting written-spec review

## Goal

Upgrade TeleDrop (single-file CLI v1.3, `teledrop.py`, deps `requests` + `tqdm`) with six features from `Prompt.txt`: live batch dashboard, upload history, summary reports, resume of interrupted uploads, persistent crash-safe state, and duplicate detection. Preserve all existing behavior and invocations; stay lightweight and CLI-first; no new external dependencies beyond stdlib.

## Agreed decisions

1. **Layout** — restructure into a `teledrop/` package; keep a thin root `teledrop.py` shim so `python teledrop.py urls.txt` works exactly as before. Add `tests/`.
2. **Dashboard** — stdlib ANSI rendering (`\033[K`, cursor movement, `shutil.get_terminal_size()`); automatic permanent fallback to plain logging when not a TTY or on any render error. Optional via `--dashboard` / `--no-dashboard`; auto-on when stdout is a TTY.
3. **Dedup default** — `--duplicate-mode url` with skipping ON. Modes: `none | url | hash | both`. Hash mode computes SHA-256 via streaming chunked reads (1 MiB) during download — never loads a whole file into memory. `--skip-duplicates` / `--no-skip-duplicates` override on/off.
4. **State location** — `.teledrop/` in repo root (gitignored): `teledrop.db` (SQLite, primary state) plus optional atomic-written `state.json` for simple batch metadata.
5. **Concurrency** — strictly sequential pipeline. No worker pool.

## Architecture

```
teledrop/
├── __init__.py      # VERSION, colors, banner constants
├── cli.py           # argparse dispatch; subcommands vs target-positional
├── config.py        # load_config() moved verbatim from current code
├── utils.py         # normalize_url, sha256_streaming, format_bytes/duration, sanitize_text
├── database.py      # sqlite3 wrapper: schema, WAL, busy_timeout=5000, all queries
├── batch.py         # BatchManager: create/resume/list/interrupt; per-item transitions
├── dedup.py         # URL-seen set + hash lookup against DB
├── downloader.py    # download_image() from current code + chunk-hash during write
├── uploader.py      # send_photo_to_telegram(); returns message_id on success
├── dashboard.py     # ANSI live renderer + fallback logger
├── history.py       # `teledrop history` formatting
├── reports.py       # summary box + JSON/TXT export
└── runner.py        # sequential per-item pipeline wiring the above
teledrop.py          # compat shim: `from teledrop.cli import main; main()`
tests/               # stdlib unittest suite
```

Dependency flow matches the spec's diagram: CLI → Batch Manager → {State(DB), Dedup, Downloader, Uploader}; Dashboard, History, Reports read from the same DB.

## Data model (SQLite)

One DB at `.teledrop/teledrop.db`, WAL mode, `busy_timeout=5000`.

**`uploads`** table — spec schema plus `batch_id`:

```sql
CREATE TABLE IF NOT EXISTS uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    source_url TEXT NOT NULL,
    normalized_url TEXT,
    filename TEXT,
    file_size INTEGER,
    sha256 TEXT,
    status TEXT NOT NULL,
    telegram_message_id TEXT,
    telegram_chat_id TEXT,
    error TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_upload_url ON uploads(normalized_url);
CREATE INDEX IF NOT EXISTS idx_upload_sha256 ON uploads(sha256);
CREATE INDEX IF NOT EXISTS idx_upload_status ON uploads(status);
CREATE INDEX IF NOT EXISTS idx_upload_batch_status ON uploads(batch_id, status);
```

Item statuses: `pending → downloading → uploading → completed | failed | skipped`. Row inserted as `pending` before any network work; each transition commits immediately. `completed` only after Telegram returns `ok:true` with a message id.

**`batches`** table:

```sql
CREATE TABLE IF NOT EXISTS batches (
    id TEXT PRIMARY KEY,              -- YYYYMMDD-HHMMSS-xxxx
    input_file TEXT NOT NULL,
    status TEXT NOT NULL,             -- running|completed|completed_with_errors|interrupted|cancelled
    total INTEGER NOT NULL,
    duplicate_mode TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    finished_at TEXT
);
```

Counters (completed/failed/skipped) are always derived from `uploads` via indexed queries — never stored redundantly.

**Crash semantics:** worst case an item is left at `downloading`/`uploading` after a kill. Resume treats both as not-done and retries them. Nothing lost, nothing double-uploaded. Corrupt DB on open → back up to `teledrop.db.corrupt-<ts>`, start fresh, warn user.

## Batch lifecycle & resume

**Start (`teledrop urls.txt`):**
1. Load URLs; normalize each (strip whitespace, drop fragment, lowercase scheme/host, keep query intact).
2. Look for unfinished batch (status `running`/`interrupted`) with same input file. If found, show prompt with batch id, progress, failed, pending counts and `[R]esume / [N]ew / [C]ancel`. Non-TTY stdin defaults to Resume; `--no-resume` forces new.
3. Resume = reuse batch_id. `completed`/`skipped` rows untouched. Rows stuck at `downloading`/`uploading` reset to `pending`. Work queue built from missing-or-pending rows keyed by normalized URL (+ hash when mode includes hash) — never line index, so reordered input resolves correctly.
4. New batch = fresh id; old interrupted batches remain listed under `teledrop batches`.

**Per-item pipeline (sequential, in `runner.py`):**

```
mark downloading → stream-download + chunk-hash → commit
  → dedup check (url seen this batch / hash present in DB as completed) → mark skipped, done
  → mark uploading → Telegram send → commit ONLY on ok:true (store message_id)
  → failure: retry_count++, honor 429 retry_after, up to max_retries, then mark failed with sanitized error
```

Every transition is its own `commit()`. Pacing interval unchanged (`-i`, `--min/max-interval`).

**Ctrl+C:** handler prints `Stopping TeleDrop... Saving current state... ✓ State saved.`, marks batch `interrupted`, exits 130. In-flight item keeps last honest status.

**`teledrop retry-failed [--batch-id X]`:** select `failed` rows of latest/given batch, reset to `pending`, flip batch to `running`, re-enter pipeline. Completed items untouched by construction. Respects existing retry/interval config.

## CLI surface

Backward compatible. Upload form:

```
teledrop <target> [-c CAPTION] [-i SEC] [--min-interval S] [--max-interval S]
                  [--dashboard | --no-dashboard]
                  [--duplicate-mode none|url|hash|both]   # default url
                  [--skip-duplicates | --no-skip-duplicates]
                  [--report PATH.json|.txt]
                  [--resume | --no-resume]
                  [--version] [-h]
```

Subcommands:

```
teledrop history [--limit N] [--status S] [--clear]
teledrop batches
teledrop resume [--batch-id ID]
teledrop retry-failed [--batch-id ID]
```

Dispatch rule in `cli.py`: first arg matching a known subcommand routes there; otherwise treated as `target`. `teledrop --help` shows grouped options.

Dashboard fields: progress %, bar (terminal-width), total/completed/failed/skipped/pending, current item, status, speed (rolling byte counter / elapsed window), uploaded bytes, elapsed, ETA (remaining × avg item time), last error, retry count. Redraw throttled to ~5 Hz (time-based). Fallback = existing per-item `[+]/[-]/[SKIP]` logging.

Summary report at end of every batch: box with batch id, input, totals, uploaded bytes, duration, avg speed, retries; failed-items list with sanitized errors. `--report` writes JSON (keys per spec: batch_id, total, completed, failed, skipped, uploaded_bytes, duration_seconds, retries) or TXT.

## Security

- Bot token never written to DB, reports, or logs. Error strings sanitized (strip `bot<token>` patterns) before storage/display.
- URLs/filenames escaped/sanitized for terminal output; no shell interpolation of filenames or URLs anywhere (all subprocess-free; pure `requests` + `os`).
- SQL uses parameterized statements only.

## Performance

- Streaming SHA-256 during download chunk-writes; zero extra I/O pass; multi-GB files never fully in memory.
- Indexed queries for resume/dedup/history; counters derived, not scanned.
- Designed for 1k–100k URL batches; dashboard redraw independent of item count.

## Testing

`tests/` with stdlib `unittest` (`python -m unittest discover`); pytest-compatible but not required.

- **database:** creation, inserts, updates, queries, index presence, close/reopen persistence, WAL mode, corrupt-file recovery.
- **utils:** normalize_url cases (whitespace, fragment, case, query preserved), streaming sha256, formatters, sanitizer.
- **dedup:** duplicate URL; different URLs same hash; same URL different query params; multiple duplicates.
- **batch/runner:** create batch; transitions; simulated crash mid-batch → resume processes only pending, completed never re-uploaded (explicit 1000/450→550 scenario test); retry-failed resets only failed.
- **reports:** counts, JSON/TXT export correctness.
- **dashboard:** non-TTY triggers fallback (captured output).
- **integration:** run shim against local `http.server` fixture with monkeypatched `requests.post` (fake Telegram) → end-to-end resume + dedup + report.

No real Telegram calls in tests.

## Out of scope

Parallel workers, GUI/web dashboard, cloud sync, migration of pre-v1.3 runs (there was no persisted state before).

## Backward compatibility notes

- All existing flags behave identically when no new flags are passed (plus silent crash-safety gains).
- `config.json` handling unchanged.
- Single-URL mode still works and participates in history/dedup like any batch of one.