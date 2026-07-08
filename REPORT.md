# Reproduction Report: Japanese filenames + git octal-escaping break DeepWiki generation

Date: 2026-07-08 (all timestamps EDT)
Reporter environment: macOS, git 2.54.0, GitHub account `adames-cognition`

## Summary

DeepWiki generation silently drops — or hard-fails on — files whose git-reported paths are
octal-escaped due to `core.quotePath` (default `true`). Two public repos demonstrate both
failure modes:

| Repo | Contents | Result |
|---|---|---|
| `adames-cognition/quotepath-repro` | 15 Japanese-named files + `main.py`, `utils.py` | Generation **succeeds**; Japanese files **silently absent** (zero citations; design pages empty) |
| `adames-cognition/quotepath-repro-strict` | 16 Japanese-named files, zero ASCII names | Generation **hard-fails**: indexing status reports `completed` but no wiki is produced; UI resets to "Repository Not Indexed" |

Both repos use sparse history (one file per commit) to trigger per-file fallback clustering.

## The failing characters

Evidence: `evidence/05_char_analysis.log`

- Real filename: `設計書_画面一覧.xlsx`
- UTF-8 bytes: `e8 a8 ad e8 a8 88 e6 9b b8 5f e7 94 bb e9 9d a2 e4 b8 80 e8 a6 a7 2e 78 6c 73 78`
- git-quoted display (what `ls-files` / `log --name-only` emit with default `core.quotePath=true`):
  `"\350\250\255\350\250\210\346\233\270_\347\224\273\351\235\242\344\270\200\350\246\247.xlsx"`
- **First character of every quoted path: `"` = ASCII 34 = 0x22.**
- ASCII sort order: `!`=33 < `"`=34 < `0`=48 < `A`=65 < `a`=97.
  Every quoted path sorts **before all alphanumeric names** and after only space (0x20) and
  `!` (0x21). Quoted (non-existent-on-disk) paths therefore dominate the top of any
  byte-sorted file list — which is why an `!OVERVIEW.md` control file (0x21) rescues generation.
- The `343202` fragment in the reported warning
  `No real files found for file cluster cluster-...343202...xlsx-...` is the octal encoding of
  bytes `0xE3 0x82` — the UTF-8 lead bytes of Japanese katakana. Confirmed present in the
  octal-concat of e.g. `テスト計画書.md` and `メイン処理.py`.

## Octal-escaping verification (failing lines)

Evidence: `evidence/02_strict_escaping.log` (strict repo; identical behavior in the base repo)

`git ls-files` (default `core.quotePath=true`) — every line is a quoted escape, no real path on disk matches these strings:

```text
"01_\346\212\200\350\241\223\343\202\271\343\202\277\343\203\203\343\202\257\351\201\270\345\256\232.md"
"\343\202\250\343\203\251\343\203\274\345\207\246\347\220\206\350\250\255\350\250\210\346\233\270.md"
"\343\203\206\343\202\271\343\203\210\350\250\210\347\224\273\346\233\270.md"
"\343\203\241\343\202\244\343\203\263\345\207\246\347\220\206.py"
"\345\205\261\351\200\232\351\226\242\346\225\260.py"
"\347\224\273\351\235\242\350\250\255\350\250\210/README.md"
"\350\250\255\350\250\210\346\233\270_\347\224\273\351\235\242\344\270\200\350\246\247.xlsx"
... (16/16 paths quoted)
```

`git -c core.quotePath=false ls-files` — the real UTF-8 names:

```text
01_技術スタック選定.md
エラー処理設計書.md
テスト計画書.md
メイン処理.py
共通関数.py
画面設計/README.md
設計書_画面一覧.xlsx
...
```

`git log --name-only` shows the same quoted forms per commit (sparse, one file per commit).

## Timeline of the hard failure (strict repo)

Evidence: `evidence/04_strict_status_poll.log`, `evidence/06_trigger_index.log`,
`evidence/08_strict_ui_state.log` + `08_strict_ui_state.png`

Status endpoint: `GET https://api.devin.ai/ada/public_repo_indexing_status?repo_name=adames-cognition%2Fquotepath-repro-strict`

```text
13:51:54 ... 14:14:xx  {"status":"unknown"}      (pre-submission)
14:14:xx               index submitted via UI ("You are number 1 in the queue")
14:15:11 - 14:16:53    {"status":"indexing"}
14:17:13               {"status":"completed"}
```

Post-"completed" UI state (rendered page, `evidence/08_strict_ui_state.log`):

```text
Repository Not Indexed
This repository hasn't been indexed yet. ...
[Index Repository]
```

**The backend reports `completed` while no wiki exists and the UI resets to the
not-indexed state** — the externally visible signature of
`WikiGenerationEmptyError` ("Wiki generation produced no output... may not contain enough
recognizable code files"). Internal indexing logs should show the corresponding
`No real files found for file cluster cluster-...` warnings for this run
(repo: `adames-cognition/quotepath-repro-strict`, indexed ~2026-07-08 18:15–18:17 UTC).

## Silent-omission mode (base repo)

Evidence: generated wiki at `https://deepwiki.com/adames-cognition/quotepath-repro`
(indexed 17:43–17:45 UTC same day)

- Wiki generated successfully (2 ASCII-named files present acted as anchors).
- **Every source citation in every page references only `main.py` and `utils.py`.**
- Pages derived from Japanese-named docs (`2-system-design`, `1.1-technology-stack-selection`)
  render as empty shells.
- The wiki hallucinates a `docs/` directory that does not exist in the repo.
- None of the 15 Japanese-named files are cited anywhere.

## Control test status

- `!OVERVIEW.md` (leading `!` = 0x21, sorts before `"` = 0x22) committed and pushed to the
  strict repo (commit `f4ee4f3`).
- Re-generation could not be triggered programmatically (reCAPTCHA gates
  `POST /ada/index_public_repo`; direct call returns
  `{"detail":"reCAPTCHA validation failed"}`, evidence in shell history).
- **Pending one manual click**: open
  `https://deepwiki.com/adames-cognition/quotepath-repro-strict` and click
  "Index Repository". Expected: generation succeeds, `!OVERVIEW.md` is cited,
  Japanese-named files remain absent (matching the base-repo outcome).

## Root-cause hypothesis

The wiki pipeline consumes git path output produced with default `core.quotePath=true`.
Quoted paths like `"\350\250\255..."` (a) do not match any real file on disk, so per-file
clusters resolve to zero real files, and (b) sort to the top of the byte-sorted file list
(leading 0x22), starving generation of recognizable files when non-ASCII names dominate.
Fix direction: run git with `-c core.quotePath=false` (or unescape octal sequences) wherever
file lists are ingested.

## Evidence index

| File | Contents |
|---|---|
| `evidence/01_strict_commits.log` | 16 per-file commits, `create mode` lines showing quoted paths |
| `evidence/02_strict_escaping.log` | `ls-files` quoted vs `quotePath=false`, `log --name-only`, hex dump |
| `evidence/03_strict_push.log` | push to GitHub |
| `evidence/04_strict_status_poll.log` | timestamped status transitions (unknown → indexing → completed) |
| `evidence/05_char_analysis.log` | byte/char-level analysis (0x22 sort position, `343202` = 0xE3 0x82) |
| `evidence/06_trigger_index.log` | index submission run |
| `evidence/07_strict_page.html` | raw page HTML post-"completed" |
| `evidence/08_strict_ui_state.log/.png` | rendered UI reset to "Repository Not Indexed" despite `{"status":"completed"}` |
| `evidence/09_control_trigger.log` | control-test trigger attempts (reCAPTCHA-blocked) |
| `evidence/10_control_ui_state.log/.png` | UI state during control attempts |
