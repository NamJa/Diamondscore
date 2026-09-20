# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

DiamondScore is a KBO (Korean baseball) live-score Android app. **The repo currently contains only documentation** — there is no Gradle project checked in. The Android source exists as complete, copy-pasteable code blocks inside the Codelabs tutorial (`docs/labs/step-0..9.md`), served as a docsify site on GitHub Pages. `docs/IMPLEMENTATION_PLAN_KO.md` is the single source of truth for design, data contracts, and risks; the labs are that plan unrolled into a hands-on order.

All docs and commit-visible prose are in Korean. Keep it that way.

## Commands

Docs site (no build step — docsify renders at runtime):

```bash
python3 -m http.server -d docs 8000     # preview at http://localhost:8000
```

Query the wisetoto API from a terminal (plain curl works; `os`, `version` and `lang` query keys are all mandatory, route names are case-sensitive):

```bash
curl -sS "https://bsrest.wisetoto.com/live/Schedule_Day/20260913?os=a&version=4.1.3&lang=kr"
```

Gradle commands the labs instruct the reader to run, once an `app/` project exists:

```bash
./gradlew :app:assembleDebug
./gradlew :app:testDebugUnitTest                  # unit tests (mappers, LivePoller)
./gradlew :app:connectedDebugAndroidTest          # Compose UI tests on device
./gradlew :app:assembleRelease                    # R8 full mode; verify serialization DTOs survive
```

## Editing the docs

- The labs are code. When changing a version, package name, class, or rule, grep all of `docs/` and fix every occurrence — several past commits are "verify and fix Codelabs code consistency". Steps build on each other, so a rename in Step 2 must propagate through Step 9.
- Version numbers and the tech-stack summary appear in `README.md`, `docs/README.md`, plan §5.4, and the Step 2 version catalog. Change them together.
- Labs use HTML blocks styled by `docs/assets/codelab.css`: `<div class="chips">` header, `<div class="callout tip|warn|danger|ok">`, `<div class="checkpoint">`, `<div class="pager">` footer. Match the existing pattern.
- `docs/_sidebar.md` is the nav; `docs/index.html` holds the docsify config and a progress plugin keyed on `/labs/step-N` paths. `.nojekyll` must stay.
- Plan work items are tracked inline as `DS-nnn` IDs (e.g. `DS-001` = the app's first `Schedule_Day` call returns `code "00"` on a real device). `DS-002a/b` (live start/finish schema) are done as of 2026-09-15. Reference existing IDs rather than inventing new tracking.
- Consistency invariants that break silently: the canonical trap list (plan §3.4) is **12 items** — ①–⑧ games/rank (observed 2026-09-14/15), ⑨–⑫ teams/players (observed 2026-09-18) — and the count is repeated in Step 3 (chips, intro, danger callout), `docs/README.md` (intro, Step 3 card) and plan §3.4/§8/§9 — add a trap in all of them; Step 1's fixture filenames must match the `load(...)` names in Step 3's `MapperTest`; plan section cross-references (`§3.4-N`, `§4.2`) shift when the trap list is renumbered — grep them after any renumbering.
- The plan describes the data source as observed on 2026-09-14/15 (games, rank) and 2026-09-18 (teams, players). Re-verify against the live API before "correcting" a documented quirk — several counter-intuitive facts (three mandatory query keys, WBC rows in `Schedule_Month`, `end_summary` arriving minutes after the final) were confirmed by scripted checks, not assumed.

## Architecture (as specified in the plan and labs)

Single `:app` module with package boundaries that map 1:1 to a future module split (plan §5.1 / §5.5). Four rules that must hold in any code you write into the labs:

1. `feature`, `core/ui`, `core/designsystem` never reference `data`. ViewModels inject Repositories only.
2. DTOs and Room Entities never leave `data`. Only `domain/model` types cross boundaries.
3. `core/designsystem` knows no domain (domain-aware shared composables go in `core/ui`).
4. `data` knows no Compose (so Korean team names live in `core/common`, team colors in `core/designsystem`).

Screens don't know each other; navigation is a `(Long) -> Unit` callback that `DiamondScoreApp.kt` turns into a Navigation 3 `NavKey`. **No UseCase layer** — screen↔data is 1:1, shared logic is pure mapper functions.

Data flow: Compose → ViewModel → Repository → Room (read SSOT, ViewModels only ever collect DAO `Flow`s) ← `WisetotoApi` (Retrofit). Detail writes upsert `GameEntity` + `InningRunEntity` in one transaction; there is no server delta field, so writes are skipped when the new row equals the stored row (`data class` equality — never add timestamps to entities).

Live updates: one `GET /live/Schedule_Day/{yyyyMMdd}` refreshes the whole day (20s); detail polls `/live/schedule/{seq}` at 15s only while `LIVE` (the list has no per-inning runs). Season prefetch is `GET /live/Schedule_Month/{yyyyMM}` for months 3–11. `LivePoller` runs under `repeatOnLifecycle(STARTED)` with single-flight, adaptive interval, jitter, and backoff. WorkManager is for prefetch only, never live polling.

## Stack constraints (non-obvious, easy to break)

- AGP 9 has Kotlin built in: do **not** apply `org.jetbrains.kotlin.android`; compiler options go in top-level `kotlin { compilerOptions { } }`. Kotlin 2.4 is forced via root `buildscript` classpath.
- KSP2 only (Room, Hilt), no kapt. KSP uses standalone versioning since 2.3.0 (`2.3.11`, not `2.4.x-2.0.0`); Hilt must be ≥ 2.60 to match.
- Navigation 3 (`NavDisplay` + typed `NavKey`), never `navigation-compose`.
- kotlinx.serialization `Json` must have `ignoreUnknownKeys = true` and `explicitNulls = false`; wisetoto responses carry cache noise fields and `null` for unplayed innings. Every response is an `Envelope<T>` — HTTP is 200 even on failure; success is `code == "00"` (`Envelope.body()` throws otherwise).

## wisetoto data traps (plan §3.4 is canonical and numbered — mapping these naively is a bug)

- Route names are case-sensitive (`Schedule_Day`, `Schedule_Month`, `League_Rank`, `Team_Info`); date args are `yyyyMMdd`/`yyyyMM` only. All three query keys `os`, `version`, `lang` are mandatory (values unchecked); any missing → `code "01"` with HTTP 200.
- `Schedule_Day`/`Schedule_Month` are not KBO-only: March carries WBC games, 3/12–3/24 preseason, July the All-Star game, with no league field on rows. Keep only rows whose both team IDs are in `KBO_TEAMS` and whose date is ≥ `league_rank.start` from the `Schedule_Day` response (`isKboRegular`).
- Scores and rank numbers are **strings** in list/rank responses (`"9"`, `"0.620"`); only the detail's `home_score` is an Int. DTOs keep server types; mappers `toIntOrNull()`.
- `state` is `a` scheduled / `i` in progress (observed 2026-09-15) / `e` final / `c` canceled; anything else → `UNKNOWN`. Canceled no-games keep partial scores and innings — drop them. Detail `game_result` is an inning label ("1회초") while live and `w`/`l`/`d` after — never derive the winner from it; compare totals.
- `boxscore.home_score`/`away_score` are always 15 slots, `null` = not played (including an unplayed bottom 9th), `0` = zero runs. `parseInnings` trims to played innings; never render 15 columns.
- `inning` code `bs{N}_{1|2}` = N회 초/말; labels come from parsing it, never invented.
- On `i → e` the final score, R/H/E and `livecomment.comment_type == "fin"` arrive together, but `end_summary` (win/loss/save pitchers) and the list row's `detail.win_pitcher` fill **~7–8 minutes later**. Refetch once at the flip and once ~10 min later; never keep the 15s poll running on a `FINAL` game.
- Stadium names are not normalized (23 spellings); cards use the home city from `KBO_TEAMS`, only the detail shows `stadium_name` verbatim.
- `game_date` is a display string; use `game_timestamp` (epoch seconds) and convert to `Asia/Seoul`. `Schedule_Month` rows lack the timestamp — parse `yyyy-MM-dd HH:mm:ss` as Seoul.
- Team IDs are wisetoto `team_info_seq` (315 SSG, 316 두산, 317 롯데, 318 삼성, 319 한화, 320 KIA, 321 키움, 322 LG, 2107 NC, 2674 KT). Season = year; there is no season ID. `schedule_info_seq` is a global cross-sport counter — never compute it, always take it from a list response.
- A roster needs **two** `Team_Info` calls (`player_position` 0 = pitchers, anything else = batters); list rows carry no position, and `c_number` is a string that **repeats inside one team** (두산 has two #48 pitchers) — the list key is `player_info_seq`, never the number. `team_history` entries are split by a lowercase `l`, not a pipe; photo URLs come as `http://` and must be promoted to `https`.
- `Player_Info`'s `record` schema splits on `c_position` (pitcher vs batter; the same key can differ — `h` is hits allowed vs hits), so the domain splits it with a `sealed interface`. `month "13"` is the season total, and it does **not** equal the sum of the monthly rows — use the total row as sent. Innings come in two notations (`"29 2/3"` mixed fraction in monthly rows, `ip "0.2"` = ⅔ inning in `previous5`), `previous5`'s `era`/`avg` are running season totals rather than that game's, and rows with every field `null` are mixed in. `player_detail` has no team field — the caller passes the team in.
- Field-name typos (`team_inf_seq`, `team_ifno_seq`, `rib` = RBI, `player_count` = games) are the server's; keep them in `@SerialName`.

## wisetoto access notes

curl, OkHttp and browsers all get 200; only a `Python-urllib` User-Agent gets 401. `/extra/notice` carries the app's forced-update signal (`update.next_action`) — check it at startup. The service ToS forbids commercial reuse without consent; keep the app personal-use and poll no faster than the official app (list every 4s; we use 20s). Do not add auth-bypass workarounds if the API starts gating; the plan says circuit-open.

## Route source of truth

Routes were taken from the 프로야구 LIVE app's Retrofit interface, not guessed. When you need a route or its query keys, read `baseball-decompiled/apktool/smali_classes8/net/adwhale/obfuscated/bt6.smali` (all `@GET/@POST` annotations) and the `data/repository/*RepositoryImpl.smali` files (the `@QueryMap` keys), both gitignored but present locally; re-pull with `adb shell pm path com.tionnet.android.baseball` + `adb pull` if missing. Brute-forcing route names failed for two days because the names are mixed-case.

The full evaluation and re-verification log (SofaScore comparison, 71-check results, live capture) is `docs/wisetoto-api-eval.md` — gitignored, local only. The screen mockups live in a Claude design canvas (https://claude.ai/artifact/FVJb1Puyzw465AyJdPCTVG, 18 artboards dark+light); edit them through the `design` skill by re-seeding from working files, never by hand-editing the published page.

## Git identity and pushing

Commits are authored as `Namja <kjwoo810@gmail.com>` — set as repo-local `user.name`/`user.email`, which overrides the machine's global placen identity; keep it that way. The `origin` URL is HTTPS and the active `gh` login is a different account, so push over SSH with the NamJa key alias instead of switching accounts:

```bash
git push git@github-namja:NamJa/Diamondscore.git main
```

Commit messages are Korean, one summary line plus bullets.

## Do not commit

`.gitignore` excludes `baseball-apk/`, `baseball-decompiled/` (프로야구 LIVE APK and its apktool output), the legacy `sofascore-apk/` / `sofascore-decompiled/` dirs, and the reverse-engineering notes `docs/wisetoto-*`, `docs/sofascore-*`, `docs/kbo-baseball-endpoints.md`, `docs/extract-endpoints.py`. Keep them out of the public repo.
