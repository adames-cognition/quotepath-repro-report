# DeepWiki: git `core.quotePath` octal-escaping drops/kills wikis for repos with non-ASCII (Japanese) filenames

Reporter: Adames Hodelin (`adames-cognition`) · Date: 2026-07-08
Repro repos (public): [`adames-cognition/quotepath-repro`](https://github.com/adames-cognition/quotepath-repro), [`adames-cognition/quotepath-repro-strict`](https://github.com/adames-cognition/quotepath-repro-strict)
Evidence + report repo: [`adames-cognition/quotepath-repro-report`](https://github.com/adames-cognition/quotepath-repro-report)

## TL;DR

The wiki pipeline consumes git path output produced with git's default `core.quotePath=true`. Any path containing non-ASCII bytes is emitted **octal-escaped and wrapped in double quotes** (e.g. `"\350\250\255...xlsx"`). These strings match no real file on disk, so:

1. **Silent omission** — if some ASCII-named files exist, the wiki generates but every non-ASCII-named file is invisible (zero citations, empty design pages, hallucinated structure). Repo: `quotepath-repro`.
2. **Hard failure** — if *no* ASCII-named files exist, generation produces nothing: the status API reports `completed` but no wiki exists and the UI resets to "Repository Not Indexed" (signature of `WikiGenerationEmptyError`). Repo: `quotepath-repro-strict`.

**Fix direction:** run git with `-c core.quotePath=false` (or `-z` null-terminated output, or unescape the octal form) everywhere file lists are ingested.

## Action-by-action reproduction with evidence

| # | Action taken | Observed result | Evidence |
|---|---|---|---|
| 1 | Created `quotepath-repro-strict`: 16 Japanese-named files, one file per commit (sparse history forces per-file fallback clustering), zero ASCII names | 16 per-file commits | Commit history: [`adames-cognition/quotepath-repro-strict/commits/main`](https://github.com/adames-cognition/quotepath-repro-strict/commits/main); representative commit adding `設計書_画面一覧.xlsx`: [`10b10aa`](https://github.com/adames-cognition/quotepath-repro-strict/commit/10b10aa) (note the quoted octal path in the diff stat) |
| 2 | Ran `git ls-files` and `git log --name-only` with default config vs `-c core.quotePath=false` | Default: **17/17 quoted-octal paths** (only later-added `!OVERVIEW.md` is literal); with `quotePath=false`: real UTF-8 names | Clone locally and run `git ls-files` vs `git -c core.quotePath=false ls-files`; see the live file tree at [`adames-cognition/quotepath-repro-strict`](https://github.com/adames-cognition/quotepath-repro-strict) (GitHub renders real UTF-8 names, but git CLI emits quoted-octal forms) |
| 3 | Same check on the base repo `quotepath-repro` (15 Japanese files + `main.py`, `utils.py`) | Only `main.py`/`utils.py` appear as real paths; all Japanese names quoted | Live repo: [`adames-cognition/quotepath-repro`](https://github.com/adames-cognition/quotepath-repro); commit adding `main.py` shows a literal path [`32187f9`](https://github.com/adames-cognition/quotepath-repro/commit/32187f9), while commits adding Japanese files show quoted octal paths (e.g. [`b86b003`](https://github.com/adames-cognition/quotepath-repro/commit/b86b003)) |
| 4 | Byte-level analysis of a representative name `設計書_画面一覧.xlsx` | First char of every quoted path is `"` = 0x22, sorting before all alphanumerics (only space 0x20 and `!` 0x21 come first) — quoted, non-existent paths dominate the top of any byte-sorted file list. The `343202` fragment in the pipeline warning `No real files found for file cluster cluster-...343202...` is octal for bytes 0xE3 0x82, the UTF-8 lead bytes of katakana — i.e. the cluster IDs are built from the *quoted* names | Analysis script: [`char_analysis.py`](https://github.com/adames-cognition/quotepath-repro-report/blob/main/char_analysis.py); raw evidence: [`evidence/05_char_analysis.log`](https://github.com/adames-cognition/quotepath-repro-report/blob/main/evidence/05_char_analysis.log) |
| 5 | Submitted `quotepath-repro-strict` for indexing via deepwiki.com UI, polled `GET https://api.devin.ai/ada/public_repo_indexing_status?repo_name=adames-cognition%2Fquotepath-repro-strict` | `unknown` → `indexing` (14:15–14:16 EDT) → `completed` (14:17 EDT) | Status endpoint (live, currently shows the post-failure cached state): [`api.devin.ai/ada/public_repo_indexing_status?repo_name=adames-cognition%2Fquotepath-repro-strict`](https://api.devin.ai/ada/public_repo_indexing_status?repo_name=adames-cognition%2Fquotepath-repro-strict) |
| 6 | Loaded `https://deepwiki.com/adames-cognition/quotepath-repro-strict` after `completed` | UI shows **"Repository Not Indexed"** with an "Index Repository" button — backend says `completed`, no wiki exists | Live broken page: [`deepwiki.com/adames-cognition/quotepath-repro-strict`](https://deepwiki.com/adames-cognition/quotepath-repro-strict) (refresh after the backend `completed` state to see the reset) |
| 7 | Inspected the successfully generated wiki for the base repo (`https://deepwiki.com/adames-cognition/quotepath-repro`, indexed 17:43–17:45 UTC) | Every citation on every page references only `main.py`/`utils.py`; pages for Japanese-named docs (`2-system-design`, `1.1-technology-stack-selection`) are empty shells; wiki hallucinates a nonexistent `docs/` directory; none of the 15 Japanese files cited | Live wiki: [`deepwiki.com/adames-cognition/quotepath-repro`](https://deepwiki.com/adames-cognition/quotepath-repro); empty design page: [`.../2-system-design`](https://deepwiki.com/adames-cognition/quotepath-repro/2-system-design); empty tech-stack page: [`.../1.1-(technology-stack-selection)`](https://deepwiki.com/adames-cognition/quotepath-repro/1.1-(technology-stack-selection)); the only populated page is the Python one: [`.../1.2-python-(python-codebase)`](https://deepwiki.com/adames-cognition/quotepath-repro/1.2-python-(python-codebase)) |
| 8 | Control test: committed `!OVERVIEW.md` (leading `!` = 0x21 sorts before quote 0x22) to the strict repo, commit `f4ee4f3` | Programmatic re-index blocked by reCAPTCHA (`POST /ada/index_public_repo` → `{"detail":"reCAPTCHA validation failed"}`); pending one manual "Index Repository" click. Expected: generation succeeds, `!OVERVIEW.md` cited, Japanese files still absent | Control commit: [`adames-cognition/quotepath-repro-strict/commit/f4ee4f3`](https://github.com/adames-cognition/quotepath-repro-strict/commit/f4ee4f3); file: [`!OVERVIEW.md`](https://github.com/adames-cognition/quotepath-repro-strict/blob/main/%21OVERVIEW.md); re-trigger at [`deepwiki.com/adames-cognition/quotepath-repro-strict`](https://deepwiki.com/adames-cognition/quotepath-repro-strict) |

Evidence files 01/02/03/05 were re-generated fresh from clean clones of the public repos in this session (Linux, git default `core.quotePath` unset ⇒ `true`), independently confirming the git-side behavior on a second platform (original repro: macOS, git 2.54.0). Items 5–8's live captures come from the original reproduction session; the strict repo's broken state and the base repo's degenerate wiki remain directly verifiable at the deepwiki.com URLs above.

## Why both failure modes follow from one bug

- Per-file fallback clusters are keyed on the git-reported (quoted) path; resolving the cluster against the working tree finds **zero real files** → `No real files found for file cluster cluster-...` warnings.
- Quoted paths all begin with 0x22, so in a byte-sorted file list they pile up at the top ahead of every alphanumeric name. With a few ASCII anchors present, generation limps through on those alone (silent-omission mode); with none, no recognizable files remain and generation yields empty output (`WikiGenerationEmptyError`) while indexing status is still marked `completed` — hence the `completed`-but-"Not Indexed" contradiction users see.

## What to check internally

- Indexing logs for `adames-cognition/quotepath-repro-strict`, ~2026-07-08 18:15–18:17 UTC: expect `No real files found for file cluster cluster-...` warnings and an empty-wiki error despite `completed` status.
- Any pipeline code shelling out to `git ls-files` / `git log --name-only` / `git diff --name-only` without `-c core.quotePath=false` or `-z`.

## Suggested fixes

1. Add `-c core.quotePath=false` (or use `-z` NUL-terminated output) to every git invocation that produces file paths.
2. Defensively unescape any `"..."`-quoted octal path before matching against disk.
3. Don't report indexing `completed` when wiki generation produced no output — surface the empty-generation error to the status endpoint/UI instead of the misleading `completed` → "Repository Not Indexed" combination.
