# Step 7 · 순위 · 팀 · 즐겨찾기

<div class="chips"><span class="chip time">90분</span><span class="chip diff">보통</span><span class="chip goal">순위표·팀 상세·팀 즐겨찾기를 완성한다</span></div>

정보 탐색 화면을 채웁니다. 순위표는 **승-패-무**(무는 파생)를 보여주고, 팀 상세는 최근/예정 경기를, 즐겨찾기는 로컬에 저장합니다.

## 1. 순위 Repository·ViewModel

`data/repository/StandingsRepository.kt`:

```kotlin
class StandingsRepository @Inject constructor(
    private val api: SofaScoreApi, private val dao: StandingDao,
) {
    fun observe(seasonId: Long): Flow<List<Standing>> =
        dao.observe(seasonId).map { it.map(StandingEntity::toDomain) }

    suspend fun refresh(seasonId: Long) {
        val rows = api.standings(seasonId).standings.firstOrNull()?.rows.orEmpty()
        dao.replace(seasonId, rows.map { it.toDomain().toEntity(seasonId) })   // TTL 10분 캐시
    }
}
```

## 2. 순위 화면

`feature/standings/StandingsScreen.kt`:

```kotlin
@Composable
fun StandingsScreen(vm: StandingsViewModel = hiltViewModel(), onTeam: (Long) -> Unit) {
    val rows by vm.ui.collectAsStateWithLifecycle()
    LazyColumn {
        stickyHeader { StandingHeader() }        // 순위 팀 경기 승 패 무 승률 GB 득실
        items(rows, key = { it.team.id }) { s -> StandingRow(s) { onTeam(s.team.id) } }
    }
}

@Composable private fun StandingRow(s: Standing, onClick: () -> Unit) {
    Row(Modifier.fillMaxWidth().clickable(onClick = onClick).padding(8.dp)) {
        Cell("${s.position}", .8f); Cell(s.team.nameKo, 3f)
        Cell("${s.games}", 1f); Cell("${s.wins}", 1f); Cell("${s.losses}", 1f)
        Cell("${s.draws}", 1f)                                     // ← 파생 무승부
        Cell("%.3f".format(s.winPct), 1.4f)
        Cell(if (s.gamesBehind == 0.0) "-" else "%.1f".format(s.gamesBehind), 1.2f)
        Cell(s.runDiff, 1.2f)
        s.playoffTier?.let { PlayoffBadge(it) }                    // promotion.text
    }
}
```

<div class="callout tip"><span class="t">공급 안 되는 컬럼은 숨긴다</span>
값이 없는 컬럼은 <code>-</code> 대신 컬럼 자체를 그리지 마세요. 동률 순서는 앱에서 재계산하지 않고 <code>position</code> 순서를 그대로 씁니다.
</div>

## 3. 팀 상세

`feature/teams/TeamDetailScreen.kt` — 팀 정보 + 최근/예정 경기(`/team/{id}/events/last|next/{page}`).

```kotlin
@Composable
fun TeamDetailScreen(vm: TeamDetailViewModel = hiltViewModel(), onGame: (Long) -> Unit) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    LazyColumn {
        item { TeamHeader(ui.team, isFavorite = ui.isFavorite, onFav = vm::toggleFavorite) }
        item { SectionTitle("최근 경기") }
        items(ui.recent, key = { it.id }) { GameCard(it) { onGame(it.id) } }
        item { SectionTitle("다음 경기") }
        items(ui.upcoming, key = { it.id }) { GameCard(it) { onGame(it.id) } }
    }
}
```

팀 로고는 Coil 3로 불러오되, 실패 시 팀 컬러 모노그램으로 대체합니다.

```kotlin
AsyncImage(
    model = "https://img.sofascore.com/api/v1/team/${team.id}/image",
    contentDescription = team.nameKo,
    error = painterResource(R.drawable.ic_team_placeholder),
    modifier = Modifier.size(48.dp),
)
```

## 4. 즐겨찾기 (로컬)

`data/repository/FavoritesRepository.kt`:

```kotlin
class FavoritesRepository @Inject constructor(private val dao: FavoriteDao) {
    fun observeTeams(): Flow<Set<Long>> =
        dao.observe("team").map { it.map { f -> f.targetId }.toSet() }
    suspend fun toggle(teamId: Long) {
        if (dao.exists("team", teamId)) dao.delete("team", teamId)
        else dao.insert(FavoriteEntity("team", teamId, System.currentTimeMillis()))
    }
}
```

경기 목록에서 즐겨찾는 팀의 경기를 **상단 고정**하려면, `observeByDate` 결과를 즐겨찾기 Set과 `combine`해 정렬 키를 얹습니다.

## 5. 실행 확인

<div class="checkpoint"><span class="t"></span> 순위 → 팀 선택 → 팀 상세의 최근 경기 → 경기 상세로 이동하고, 뒤로가기로 각 화면의 스크롤·선택이 복원되면 성공. 즐겨찾기 별을 누르면 목록 상단에 고정됩니다.</div>

<div class="pager">
<a href="#/labs/step-6">← Step 6</a>
<a href="#/labs/step-8">Step 8 · 마감·릴리스 →</a>
</div>
