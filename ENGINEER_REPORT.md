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

- Status endpoint went `unknown → indexing → completed`: [`api.devin.ai/ada/public_repo_indexing_status?repo_name=adames-cognition%2Fquotepath-repro-strict`](https://api.devin.ai/ada/public_repo_indexing_status?repo_name=adames-cognition%2Fquotepath-repro-strict)
- Yet the live page is still broken/reset: [`deepwiki.com/adames-cognition/quotepath-repro-strict`](https://deepwiki.com/adames-cognition/quotepath-repro-strict)
- Commit history showing the sparse, octal-quoted commits: [`quotepath-repro-strict/commits/main`](https://github.com/adames-cognition/quotepath-repro-strict/commits/main)

## Why `!OVERVIEW.md` would fix it

I added `!OVERVIEW.md` to the strict repo ([commit `f4ee4f3`](https://github.com/adames-cognition/quotepath-repro-strict/commit/f4ee4f3)). `!` is ASCII `0x21`, which sorts before the `"` (`0x22`) that starts every quoted path. If this hypothesis is right, re-indexing with that file present should give generation a recognizable anchor and let it succeed — while still dropping the Japanese files. The re-index needs one manual click on the DeepWiki page (reCAPTCHA blocks automation); the aborted programmatic attempt at 14:20 did not confirm whether the submission fired.

## Fix direction

1. Run git with `-c core.quotePath=false` (or `-z`) wherever file paths are read.
2. If you must keep quoted output, unescape `"\xxx\yyy..."` paths before matching against disk.
3. Don't return `completed` from the status API when generation produced no output; surface the empty-wiki error instead.
