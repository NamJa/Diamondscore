# Step 8 · 순위 · 팀 · 즐겨찾기

<div class="chips"><span class="chip time">90분</span><span class="chip diff">보통</span><span class="chip goal">순위표·팀 상세·즐겨찾기 화면을 컴포넌트로 조립한다</span></div>

정보 탐색 화면을 채웁니다. Step 5의 `StandingRow`·`GameCard`를 재사용하고, 목업의 팀 컬러 헤더를 만듭니다.

## 1. 순위 화면

`feature/standings/StandingsScreen.kt` — `StandingRow` + `PlayoffDivider`(5위 뒤) 조립.

```kotlin
@Composable
fun StandingsScreen(onTeam: (Long) -> Unit) {
    val vm: StandingsViewModel = hiltViewModel()
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
<code>item {}</code>은 <code>LazyListScope</code>에서만 호출됩니다 — <code>itemsIndexed</code>의 항목 람다 <strong>안에서는</strong> 쓸 수 없습니다. 위처럼 <code>rows.forEachIndexed</code>로 각 행을 <code>item</code>으로 내보내고, 5위 다음에 별도 <code>item</code>으로 <code>PlayoffDivider</code>를 끼웁니다. 공급 안 되는 컬럼은 <code>-</code>가 아니라 컬럼 자체를 숨기고, 동률은 <code>position</code>을 그대로 씁니다(무승부는 <code>draw_count</code>로 직접 옵니다).
</div>

**Repository · 매퍼 · ViewModel · 헤더** (완전한 코드)

`data/repository/StandingsRepository.kt` + `data/local/mapper/StandingMappers.kt`:

```kotlin
class StandingsRepository @Inject constructor(
    private val api: WisetotoApi, private val dao: StandingDao,
) {
    fun observe(year: Int): Flow<List<Standing>> = dao.observe(year).map { it.map(StandingEntity::toDomain) }

    /** 시즌 = 연도 (Step 4의 GamesRepository와 같은 규칙). 시즌 ID 같은 것은 없다. */
    fun currentSeasonYear(): Int = LocalDate.now(SEOUL).year

    suspend fun refresh(year: Int) {
        val rows = api.leagueRank(year).body().rank                  // 서버 캐시 1시간, 앱 TTL 10분
        dao.replace(year, rows.map { it.toDomain().toEntity(year) })
    }
}

// teamNameKo·teamShort는 core/common (순수 Kotlin) — core/designsystem이 아니다
fun StandingEntity.toDomain() = Standing(
    position, TeamRef(teamId, teamNameKo(teamId, ""), teamShort(teamId)),
    games, wins, losses, draws, winPct, gamesBehind, streak)

fun Standing.toEntity(year: Int) = StandingEntity(
    year, team.id, position, games, wins, losses, draws, winPct, gamesBehind, streak)
```

`feature/standings/StandingsViewModel.kt` — 현재 시즌은 repository에게 묻습니다:

```kotlin
@HiltViewModel
class StandingsViewModel @Inject constructor(
    private val repo: StandingsRepository,
) : ViewModel() {
    private val year = repo.currentSeasonYear()
    val ui: StateFlow<List<Standing>> = repo.observe(year)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
    init { viewModelScope.launch { runCatching { repo.refresh(year) } } }
}
```

<div class="callout warn"><span class="t">ViewModel에 <code>WisetotoApi</code>를 주입하지 않는다</span>
"순위 한 번만 부르면 되는데" 싶어 <code>WisetotoApi</code>를 ViewModel에 넣으면 두 가지가 동시에 깨집니다 — <code>feature</code>가 <code>data/remote</code>를 참조하고, <code>Envelope&lt;LeagueRankDto&gt;</code>가 data 레이어를 벗어납니다. 순위는 Room을 거쳐 <code>Standing</code>으로만 받습니다. 규칙을 어기는 코드는 거의 항상 이렇게 "한 번만"으로 들어옵니다.
</div>

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

무승부는 <code>draw_count</code>로 직접 오고, 연속 기록(<code>streak</code>, "6승")도 함께 옵니다. 진출권 배지 데이터는 없으므로 5위 뒤 진출선은 UI 고정 규칙으로만 그립니다.

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
    model = "https://storage.wisetoto.com/data/sports_db/team_${team.id}.png",   // _s.png는 소형
    contentDescription = team.nameKo,
    error = rememberVectorPainter(Icons.Outlined.Shield),
    modifier = Modifier.size(56.dp).clip(CircleShape),
)
```

**Repository · ViewModel · 화면** (완전한 코드)

`domain/model/Models.kt`에 도메인 모델을 하나 더 둡니다 — repository는 **도메인**을 내보내고,
`isFavorite` 같은 화면용 값은 ViewModel이 붙입니다:

```kotlin
// domain/model — data 레이어가 UI 타입을 만들지 않게 한다
data class TeamDetail(
    val team: TeamRef,
    val stadium: String?, val manager: String?,   // Team_Info — 없으면 null
    val recent: List<GameSummary>,
    val upcoming: List<GameSummary>,
)
```

최근·다음 경기는 **네트워크 없이** Room에서 꺼냅니다 — Step 4 프리페치로 시즌 전체가 이미 있습니다. 구장·감독만 `Team_Info` 1회입니다.

```kotlin
class TeamsRepository @Inject constructor(
    private val api: WisetotoApi, private val dao: GameDao,
) {
    fun observeTeam(id: Long): Flow<TeamDetail> {
        val info = flow { emit(runCatching { api.teamInfo(id).body().teamInfo?.detail }.getOrNull()) }
        return combine(dao.observeByTeam(id).map { it.map(GameEntity::toSummary) }, info) { games, d ->
            val now = Instant.now()
            TeamDetail(
                team = TeamRef(id, teamNameKo(id, d?.name ?: ""), teamShort(id)),
                stadium = d?.stadiumName, manager = d?.director,
                recent = games.filter { it.status == GameStatus.FINAL }.takeLast(5).reversed(),
                upcoming = games.filter { it.status == GameStatus.SCHEDULED && it.startsAt >= now }.take(5),
            )
        }
    }
}
```

`feature/teams/TeamDetailViewModel.kt` — UI 상태는 여기서 조립합니다:

```kotlin
data class TeamDetailUi(
    val team: TeamRef, val record: String,
    val recent: List<GameSummary>, val upcoming: List<GameSummary>,
    val isFavorite: Boolean,
    val stadium: String? = null, val manager: String? = null,
)

/** 순위(Standing)에서 전적 문자열 — "리그 5위 · 50·44·2 · .532". */
fun teamRecord(s: Standing) =
    "리그 ${s.position}위 · ${s.wins}·${s.losses}·${s.draws} · ${"%.3f".format(s.winPct).removePrefix("0")}"

@HiltViewModel(assistedFactory = TeamDetailViewModel.Factory::class)
class TeamDetailViewModel @AssistedInject constructor(
    private val repo: TeamsRepository, private val favorites: FavoritesRepository,
    @Assisted private val key: TeamDetailKey,       // ← Nav3 인자 (Step 2 core/navigation)
) : ViewModel() {
    val ui: StateFlow<TeamDetailUi?> =
        combine(repo.observeTeam(key.teamId), favorites.observeTeams()) { d, favs ->
            TeamDetailUi(d.team, record = "", d.recent, d.upcoming, isFavorite = key.teamId in favs,
                stadium = d.stadium, manager = d.manager)
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    fun toggleFavorite() = viewModelScope.launch { favorites.toggle(key.teamId) }

    @AssistedFactory
    interface Factory {
        fun create(key: TeamDetailKey): TeamDetailViewModel
    }
}

@Composable
fun TeamDetailScreen(key: TeamDetailKey, onGame: (Long) -> Unit, onBack: () -> Unit) {
    val vm = hiltViewModel<TeamDetailViewModel, TeamDetailViewModel.Factory>(
        creationCallback = { factory -> factory.create(key) },
    )
    val ui by vm.ui.collectAsStateWithLifecycle()
    ui?.let { d ->
        LazyColumn(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
            item { TeamHeader(d.team, d.record, d.isFavorite, vm::toggleFavorite, onBack) }
            item { Caption(listOfNotNull(d.stadium, d.manager?.let { "감독 $it" }).joinToString(" · ")) }
            item { SectionLabel("최근 경기") }
            items(d.recent, key = { it.id }) { GameCard(it) { onGame(it.id) } }
            item { SectionLabel("다음 경기") }
            items(d.upcoming, key = { it.id }) { GameCard(it) { onGame(it.id) } }
        }
    } ?: LoadingCards(count = 3)
}
```

<div class="callout tip"><span class="t">전적 문자열</span>
<code>record</code>는 순위 캐시의 <code>Standing</code>을 <code>teamRecord()</code>에 넣어 채웁니다. <code>teamRecord()</code>는 표시용 문자열이니 <strong>ViewModel에서</strong> 만듭니다 — <code>StandingsRepository</code>를 하나 더 주입해 <code>observe(year)</code>를 <code>combine</code>에 넣고 해당 팀 행을 찾으면 됩니다. repository가 완성된 문자열을 내보내게 하지 마세요.
</div>

## 3. 팀 목록 (TeamsScreen)

"팀" 탭입니다. KBO 10개 구단은 Step 2의 `KBO_TEAMS`에 이미 다 있으니 **네트워크가 필요 없습니다** —
ViewModel도 만들지 않습니다.

`feature/teams/TeamsScreen.kt`:

```kotlin
@Composable
fun TeamsScreen(onTeam: (Long) -> Unit) {
    Column(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        TopBar("팀")
        LazyColumn {
            items(KBO_TEAMS.values.toList(), key = { it.id }) { t ->
                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                Row(
                    Modifier.fillMaxWidth().clickable { onTeam(t.id) }
                        .padding(horizontal = 6.dp, vertical = 16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(14.dp),
                ) {
                    Box(Modifier.width(4.dp).height(26.dp).background(teamColor(t.id)))  // 팀 컬러 바
                    Text(t.nameKo, style = MaterialTheme.typography.bodyLarge)
                }
            }
        }
    }
}
```

<div class="callout tip"><span class="t">서버에 있는데 왜 로컬 표를 쓰나</span>
<code>/extra/Team_Select</code>가 10개 구단(약칭·<code>team_ifno_seq</code>)을 주지만, 목록에 필요한 건 <strong>id·한글명·컬러</strong>뿐이고 셋 다 로컬에 있으니 요청 하나를 안 하는 쪽이 맞습니다. 팀 상세로 들어가면 그때 <code>Team_Info</code>(구장·감독)만 한 번 칩니다. 최근·다음 경기는 Room에 이미 있습니다.
</div>

## 4. 즐겨찾기

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
    // teamNameKo: com.diamondscore.core.common (순수 Kotlin)
    val teams: StateFlow<List<TeamRef>> = favorites.observeTeams()
        .map { ids -> ids.map { TeamRef(it, teamNameKo(it, ""), "") } }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
}

@Composable
fun FavoritesScreen(onTeam: (Long) -> Unit, onSettings: () -> Unit) {
    val vm: FavoritesViewModel = hiltViewModel()
    val teams by vm.teams.collectAsStateWithLifecycle()
    Column(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        // 설정 진입점은 여기 하나뿐입니다 (Step 9에서 SettingsKey로 연결)
        TopBar("즐겨찾기", trailing = {
            IconButton(onClick = onSettings) { DsIcon(Icons.Outlined.Settings, size = 22.dp) }
        })
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

## 5. 실행 확인

<div class="checkpoint"><span class="t"></span> 순위(진출선 포함) → 팀 선택 → 컬러 헤더의 팀 상세 → 최근 경기 → 경기 상세로 이어지고, 별을 누르면 즐겨찾기에 추가되어 목록 상단에 고정되면 성공. 목업의 순위·팀 상세·즐겨찾기와 대조하세요.</div>

<div class="pager">
<a href="#/labs/step-7">← Step 7</a>
<a href="#/labs/step-9">Step 9 · 마감·릴리스 →</a>
</div>
