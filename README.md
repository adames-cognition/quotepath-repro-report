# DeepWiki breaks on Japanese filenames because git quotes them in octal

**Reporter:** Adames Hodelin (`adames-cognition`) · **Date:** 2026-07-08  
**Repro repos:** [`quotepath-repro`](https://github.com/adames-cognition/quotepath-repro) · [`quotepath-repro-strict`](https://github.com/adames-cognition/quotepath-repro-strict)  
**Full report + logs:** [`quotepath-repro-report`](https://github.com/adames-cognition/quotepath-repro-report)

## In one sentence

The observed behavior is consistent with DeepWiki consuming git path output with `core.quotePath=true` (the default). Non-ASCII filenames come out wrapped in `"` and octal-escaped, so they don't match real files on disk, and the wiki either silently ignores them or fails outright.

## Two failure modes

| Scenario | Repo | What happens |
|---|---|---|
| Some ASCII files exist | [`quotepath-repro`](https://github.com/adames-cognition/quotepath-repro) (15 Japanese files + `main.py`/`utils.py`) | Wiki generates, but only cites the ASCII files. Japanese docs become [empty pages](https://deepwiki.com/adames-cognition/quotepath-repro/2-system-design). |
| No ASCII files exist | [`quotepath-repro-strict`](https://github.com/adames-cognition/quotepath-repro-strict) (Japanese only) | Backend says `completed`, but the UI resets to "Repository Not Indexed". This matches the `WikiGenerationEmptyError` signature described in the original issue. |

## The smoking gun

**Evidence:** raw escaping comparison [`evidence/02_strict_escaping.log`](https://github.com/adames-cognition/quotepath-repro-report/blob/main/evidence/02_strict_escaping.log); char analysis [`evidence/05_char_analysis.log`](https://github.com/adames-cognition/quotepath-repro-report/blob/main/evidence/05_char_analysis.log) + script [`char_analysis.py`](https://github.com/adames-cognition/quotepath-repro-report/blob/main/char_analysis.py)

Clone the strict repo and run these two commands:

```sh
git ls-files
# Every path is quoted octal, e.g.
# "\350\250\255\350\250\210\346\233\270_\347\224\273\351\235\242\344\270\200\350\246\247.xlsx"

git -c core.quotePath=false ls-files
# The real UTF-8 names appear:
# 設計書_画面一覧.xlsx
```

The quoted strings start with `"` (ASCII `0x22`). That makes them sort before any normal filename, so they dominate the top of the file list even though they don't exist on disk. The `343202` fragment in the reported warning is the octal form of UTF-8 bytes `0xE3 0x82` (the lead bytes of Japanese katakana). Our reproduction did not emit that exact warning, but the byte math lines up with how a pipeline using the quoted path could build cluster IDs from the escaped string. ([analysis script](https://github.com/adames-cognition/quotepath-repro-report/blob/main/char_analysis.py))

## Hard failure captured

For `quotepath-repro-strict`:

- Status endpoint went `unknown → indexing → completed`: [`api.devin.ai/ada/public_repo_indexing_status?repo_name=adames-cognition%2Fquotepath-repro-strict`](https://api.devin.ai/ada/public_repo_indexing_status?repo_name=adames-cognition%2Fquotepath-repro-strict) — timestamped poll in [`evidence/04_strict_status_poll.log`](https://github.com/adames-cognition/quotepath-repro-report/blob/main/evidence/04_strict_status_poll.log)
- Yet the live page is still broken/reset: [`deepwiki.com/adames-cognition/quotepath-repro-strict`](https://deepwiki.com/adames-cognition/quotepath-repro-strict) — captured in [`evidence/08_strict_ui_state.log`](https://github.com/adames-cognition/quotepath-repro-report/blob/main/evidence/08_strict_ui_state.log) and screenshot [`08_strict_ui_state.png`](https://github.com/adames-cognition/quotepath-repro-report/blob/main/evidence/08_strict_ui_state.png)
- Commit history showing the sparse, octal-quoted commits: [`quotepath-repro-strict/commits/main`](https://github.com/adames-cognition/quotepath-repro-strict/commits/main) — full commit log in [`evidence/01_strict_commits.log`](https://github.com/adames-cognition/quotepath-repro-report/blob/main/evidence/01_strict_commits.log)

## Control test: `!OVERVIEW.md` tests the sort/anchor theory

I added `!OVERVIEW.md` to the strict repo ([commit `f4ee4f3`](https://github.com/adames-cognition/quotepath-repro-strict/commit/f4ee4f3); file [`!OVERVIEW.md`](https://github.com/adames-cognition/quotepath-repro-strict/blob/main/%21OVERVIEW.md)). `!` is ASCII `0x21`, which sorts before the `"` (`0x22`) that starts every quoted path. Re-indexing should expose whether the failure is really about the pipeline being unable to find any real-file anchor:

- **If the wiki now generates but only cites `!OVERVIEW.md`**, it confirms the silent-omission mechanism: one ASCII-sorted anchor is enough to rescue generation, and every Japanese file is still dropped.
- **If the wiki still fails**, the simple sort/anchor theory is incomplete — something else (e.g. how the clusterer handles *all* quoted paths, not just their sort order) is also breaking generation.

Either outcome narrows the actual bug. The control commit is already in the repo; only the re-index is pending.

## Potential Fix direction (just spitballing)

1. Run git with `-c core.quotePath=false` (or `-z`) wherever file paths are read.
2. If you must keep quoted output, unescape `"\xxx\yyy..."` paths before matching against disk.
3. Don't return `completed` from the status API when generation produced no output; surface the empty-wiki error instead.
