# Step 8 · 순위 · 팀 · 즐겨찾기

<div class="chips"><span class="chip time">90분</span><span class="chip diff">보통</span><span class="chip goal">순위표·팀 상세·즐겨찾기 화면을 컴포넌트로 조립한다</span></div>

정보 탐색 화면을 채웁니다. Step 5의 `StandingRow`·`GameCard`를 재사용하고, 목업의 팀 컬러 헤더를 만듭니다.

## 1. 순위 화면

`feature/standings/StandingsScreen.kt` — `StandingRow` + `PlayoffDivider`(5위 뒤) 조립.

```kotlin
@Composable
fun StandingsScreen(vm: StandingsViewModel = hiltViewModel(), onTeam: (Long) -> Unit) {
    val rows by vm.ui.collectAsStateWithLifecycle()
    Column(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        TopBar("순위", trailing = { SeasonChip("2026 정규시즌") })
        StandingsHeader()   // # 팀 승·패·무 승률 GB
        LazyColumn {
            rows.forEachIndexed { i, s ->
                item(key = s.team.id) { StandingRow(s) { onTeam(s.team.id) } }
                if (i == 4) item("po") { PlayoffDivider() }   // 5위 다음 진출선
            }
        }
    }
}
```

<div class="callout tip"><span class="t">진출선은 LazyColumn DSL로</span>
<code>item {}</code>은 <code>LazyListScope</code>에서만 호출됩니다 — <code>itemsIndexed</code>의 항목 람다 <strong>안에서는</strong> 쓸 수 없습니다. 위처럼 <code>rows.forEachIndexed</code>로 각 행을 <code>item</code>으로 내보내고, 5위 다음에 별도 <code>item</code>으로 <code>PlayoffDivider</code>를 끼웁니다. 공급 안 되는 컬럼은 <code>-</code>가 아니라 컬럼 자체를 숨기고, 동률은 <code>position</code>을 그대로 씁니다(무승부는 파생, Step 3 함정 1).
</div>

**Repository · 매퍼 · ViewModel · 헤더** (완전한 코드)

`data/repository/StandingsRepository.kt` + `data/local/mapper/StandingMappers.kt`:

```kotlin
class StandingsRepository @Inject constructor(
    private val api: SofaScoreApi, private val dao: StandingDao,
) {
    fun observe(sid: Long): Flow<List<Standing>> = dao.observe(sid).map { it.map(StandingEntity::toDomain) }
    suspend fun refresh(sid: Long) {
        val rows = api.standings(sid).standings.firstOrNull()?.rows.orEmpty()
        dao.replace(sid, rows.map { it.toDomain().toEntity(sid) })     // TTL 10분 캐시
    }
}

fun StandingEntity.toDomain() = Standing(
    position, TeamRef(teamId, teamNameKo(teamId, ""), ""),
    games, wins, losses, draws, winPct, gamesBehind, runsFor, runsAgainst, runDiff, playoffTier)

fun Standing.toEntity(sid: Long) = StandingEntity(
    sid, team.id, position, games, wins, losses, draws,
    winPct, gamesBehind, runsFor, runsAgainst, runDiff, playoffTier)
```

`feature/standings/StandingsViewModel.kt` — 현재 시즌은 `/seasons` 첫 항목:

```kotlin
@HiltViewModel
class StandingsViewModel @Inject constructor(
    private val repo: StandingsRepository, private val api: SofaScoreApi,
) : ViewModel() {
    private val seasonId = MutableStateFlow<Long?>(null)
    val ui: StateFlow<List<Standing>> = seasonId.filterNotNull()
        .flatMapLatest { repo.observe(it) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
    init { viewModelScope.launch {
        val sid = api.seasons().seasons.first().id     // 하드코딩 금지
        seasonId.value = sid
        runCatching { repo.refresh(sid) }
    } }
}
```

`feature/standings/StandingsHeader.kt` — 컬럼 폭은 `StandingRow`와 맞춥니다:

```kotlin
@Composable
fun StandingsHeader() = Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp)) {
    val st = MaterialTheme.typography.labelSmall; val c = DsColors.muted2
    Text("#", Modifier.width(30.dp), style = st, color = c)
    Text("팀", Modifier.weight(1f).padding(start = 18.dp), style = st, color = c)   // 닷+간격 정렬
    Text("승·패·무", Modifier.width(78.dp), style = st, color = c, textAlign = TextAlign.Center)
    Text("승률", Modifier.width(46.dp), style = st, color = c, textAlign = TextAlign.End)
    Text("GB", Modifier.width(40.dp), style = st, color = c, textAlign = TextAlign.End)
}
```

## 2. 팀 상세 — 컬러 헤더

목업: 구단 컬러 그라디언트 배너 + 원형 배지 + 순위/전적, 아래 정보·최근·예정 경기.

`feature/teams/TeamHeader.kt`:

```kotlin
@Composable
fun TeamHeader(team: TeamRef, record: String, isFav: Boolean, onFav: () -> Unit, onBack: () -> Unit) {
    val c = teamColor(team.id)
    Box(Modifier.fillMaxWidth()
        .background(Brush.linearGradient(listOf(c, c.copy(alpha = .55f))))
        .padding(bottom = 18.dp)) {
        Column {
            Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                IconButton(onClick = onBack) { DsIcon(Icons.Outlined.ChevronLeft, tint = Color.White) }
                IconButton(onClick = onFav) {
                    DsIcon(if (isFav) Icons.Filled.Star else Icons.Outlined.StarBorder,
                        tint = if (isFav) DsColors.gold else Color.White)
                }
            }
            Row(Modifier.padding(start = 20.dp), horizontalArrangement = Arrangement.spacedBy(14.dp),
                verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(56.dp).clip(CircleShape)
                    .background(Color.White.copy(alpha = .15f))
                    .border(2.dp, Color.White.copy(alpha = .5f), CircleShape), Alignment.Center) {
                    Text(teamShort(team.id), color = Color.White, fontWeight = FontWeight.Bold)
                }
                Column {
                    Text(team.nameKo, color = Color.White, style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold)
                    Text(record, color = Color.White.copy(alpha = .85f), style = ScoreNumber)  // 리그 5위 · 50·44·2
                }
            }
        }
    }
}
```

팀 로고는 Coil 3로 불러오고 실패 시 위 배지로 대체합니다.

```kotlin
AsyncImage(
    model = "https://img.sofascore.com/api/v1/team/${team.id}/image",
    contentDescription = team.nameKo,
    error = rememberVectorPainter(Icons.Outlined.Shield),
    modifier = Modifier.size(56.dp).clip(CircleShape),
)
```

**Repository · ViewModel · 화면** (완전한 코드)

```kotlin
data class TeamDetailUi(
    val team: TeamRef, val record: String,
    val recent: List<GameSummary>, val upcoming: List<GameSummary>,
    val isFavorite: Boolean = false,
)

class TeamsRepository @Inject constructor(private val api: SofaScoreApi) {
    fun observeTeam(id: Long): Flow<TeamDetailUi> = flow {
        val recent = runCatching { api.teamEvents(id, "last", 0).events }.getOrDefault(emptyList())
            .map { it.toSummary() }.takeLast(5).reversed()
        val upcoming = runCatching { api.teamEvents(id, "next", 0).events }.getOrDefault(emptyList())
            .map { it.toSummary() }.take(5)
        emit(TeamDetailUi(TeamRef(id, teamNameKo(id, ""), ""), record = "", recent, upcoming))
    }
}

/** 순위(Standing)에서 전적 문자열 — "리그 5위 · 50·44·2 · .532". */
fun teamRecord(s: Standing) =
    "리그 ${s.position}위 · ${s.wins}·${s.losses}·${s.draws} · ${"%.3f".format(s.winPct).removePrefix("0")}"

@HiltViewModel
class TeamDetailViewModel @Inject constructor(
    private val repo: TeamsRepository, private val favorites: FavoritesRepository,
    savedState: SavedStateHandle,
) : ViewModel() {
    private val teamId: Long = checkNotNull(savedState["teamId"])
    val ui: StateFlow<TeamDetailUi?> = combine(repo.observeTeam(teamId), favorites.observeTeams()) {
        d, favs -> d.copy(isFavorite = teamId in favs)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)
    fun toggleFavorite() = viewModelScope.launch { favorites.toggle(teamId) }
}

@Composable
fun TeamDetailScreen(vm: TeamDetailViewModel = hiltViewModel(), onGame: (Long) -> Unit, onBack: () -> Unit) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    ui?.let { d ->
        LazyColumn(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
            item { TeamHeader(d.team, d.record, d.isFavorite, vm::toggleFavorite, onBack) }
            item { SectionLabel("최근 경기") }
            items(d.recent, key = { it.id }) { GameCard(it) { onGame(it.id) } }
            item { SectionLabel("다음 경기") }
            items(d.upcoming, key = { it.id }) { GameCard(it) { onGame(it.id) } }
        }
    } ?: LoadingCards(count = 3)
}
```

<div class="callout tip"><span class="t">전적 문자열</span>
<code>record</code>는 순위 캐시의 <code>Standing</code>을 <code>teamRecord()</code>에 넣어 채웁니다. 팀 상세를 순위 데이터와 <code>combine</code>하거나, <code>TeamsRepository</code>에 <code>StandingsRepository</code>를 주입해 해당 팀 행을 찾으세요.
</div>

## 3. 즐겨찾기

`data/repository/FavoritesRepository.kt`:

```kotlin
class FavoritesRepository @Inject constructor(private val dao: FavoriteDao) {
    fun observeTeams(): Flow<Set<Long>> =
        dao.observe("team").map { it.mapTo(mutableSetOf()) { f -> f.targetId } }
    suspend fun toggle(teamId: Long) {
        if (dao.exists("team", teamId)) dao.delete("team", teamId)
        else dao.insert(FavoriteEntity("team", teamId, System.currentTimeMillis()))
    }
}
```

`feature/favorites/FavoritesScreen.kt` — 목업의 "내 구단" 목록:

```kotlin
@HiltViewModel
class FavoritesViewModel @Inject constructor(favorites: FavoritesRepository) : ViewModel() {
    val teams: StateFlow<List<TeamRef>> = favorites.observeTeams()
        .map { ids -> ids.map { TeamRef(it, teamNameKo(it, ""), "") } }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
}

@Composable
fun FavoritesScreen(vm: FavoritesViewModel = hiltViewModel(), onTeam: (Long) -> Unit) {
    val teams by vm.teams.collectAsStateWithLifecycle()
    Column(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        TopBar("즐겨찾기")
        if (teams.isEmpty()) CenterColumn {
            DsIcon(Icons.Outlined.StarBorder, size = 52.dp, tint = Color(0xFF3A4250))
            Text("즐겨찾는 구단이 없어요", style = MaterialTheme.typography.bodyLarge)
            Caption("팀 상세에서 별을 눌러 추가하면 여기와 경기 목록 상단에 고정됩니다.")
        } else LazyColumn(
            contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            item { SectionLabel("내 구단") }
            items(teams, key = { it.id }) { FavoriteTeamCard(it) { onTeam(it.id) } }
        }
    }
}

@Composable
private fun FavoriteTeamCard(team: TeamRef, onClick: () -> Unit) = Surface(
    onClick = onClick, color = MaterialTheme.colorScheme.surface, shape = RoundedCornerShape(14.dp),
    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline)) {
    Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(13.dp)) {
        Box(Modifier.size(44.dp).clip(CircleShape).background(teamColor(team.id)), Alignment.Center) {
            Text(teamShort(team.id), color = Color.White, fontWeight = FontWeight.Bold)
        }
        Text(team.nameKo, Modifier.weight(1f), style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold)
        DsIcon(Icons.Filled.Star, tint = DsColors.gold, size = 22.dp)
    }
}
```

<div class="callout tip"><span class="t">로컬 저장 · 목록 고정</span>
로그인 없이 Room에만 저장합니다. 즐겨찾은 구단을 경기 목록 상단에 고정하려면 <code>GamesRepository.observeByDate</code>를 <code>favorites.observeTeams()</code>와 <code>combine</code>해 정렬 키를 얹습니다(Step 6-5). 목업처럼 각 카드에 다음 경기/라이브 요약을 넣으려면 팀별 다음 경기를 함께 조회하세요.
</div>

## 4. 실행 확인

<div class="checkpoint"><span class="t"></span> 순위(진출선 포함) → 팀 선택 → 컬러 헤더의 팀 상세 → 최근 경기 → 경기 상세로 이어지고, 별을 누르면 즐겨찾기에 추가되어 목록 상단에 고정되면 성공. 목업의 순위·팀 상세·즐겨찾기와 대조하세요.</div>

<div class="pager">
<a href="#/labs/step-7">← Step 7</a>
<a href="#/labs/step-9">Step 9 · 마감·릴리스 →</a>
</div>
