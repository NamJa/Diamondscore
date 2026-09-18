# Step 8 · 순위 · 팀 · 선수 · 즐겨찾기

<div class="chips"><span class="chip time">2시간 30분</span><span class="chip diff">보통</span><span class="chip goal">순위표·팀 상세·팀 선수단·선수 상세·즐겨찾기를 컴포넌트로 조립한다</span></div>

정보 탐색 화면을 채웁니다. Step 5의 `StandingRow`·`GameCard`·`PlayerAvatar`·`StatTable`을 재사용하고,
목업의 팀 컬러 헤더를 만듭니다. **팀 색과 앱 액센트를 구분해 쓰는 첫 화면들**입니다(Step 2 §8) —
엠블럼·등번호·팀명은 구단 색, 탭·링크·대표 기록은 앱 액센트입니다.

화면 흐름은 이렇습니다.

```
순위 ─┐
      ├→ 팀 상세 ──→ 팀 정보(선수단·연혁) ──→ 선수 정보
팀 ───┘      └→ 경기 상세
```

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

무승부는 `draw_count`로 직접 오고, 연속 기록(`straight`, "2승")도 함께 옵니다. 진출권 배지 데이터는 없으므로 5위 뒤 진출선은 UI 고정 규칙으로만 그립니다.

## 2. 팀 상세 — 컬러 헤더

목업(두산 베어스 기준): 구단 컬러 글로우 + 원형 배지 + 순위/전적, 아래 구단 정보·선수단 진입점·최근/다음 경기.

### 2.1 Repository — `Team_Info`를 **두 번** 부른다

`data/repository/TeamsRepository.kt`. 선수단은 포지션마다 한 번씩 와야 합니다(Step 3 함정 9).
팀 상세와 팀 정보(선수단) **두 화면이 이 하나를 같이 씁니다** — 그래서 모델도 하나입니다.

```kotlin
class TeamsRepository @Inject constructor(
    private val api: WisetotoApi, private val dao: GameDao,
) {
    fun observeTeam(id: Long): Flow<TeamDetail> {
        val info = flow { emit(fetchInfo(id)) }
        return combine(dao.observeByTeam(id).map { it.map(GameEntity::toSummary) }, info) { games, (p, b) ->
            val d = p?.detail ?: b?.detail          // 구단 정보는 두 응답에 똑같이 실려 온다
            val now = Instant.now()
            TeamDetail(
                team = TeamRef(id, teamNameKo(id, d?.name.orEmpty()), teamShort(id)),
                nameEn = d?.nameEn, stadium = d?.stadiumName, manager = d?.director,
                history = d?.history.orEmpty().map { it.toHistoryEntry() },
                pitchers = p?.players.orEmpty().toRoster(),
                batters = b?.players.orEmpty().toRoster(),
                recent = games.filter { it.status == GameStatus.FINAL }.takeLast(4).reversed(),
                upcoming = games.filter { it.status == GameStatus.SCHEDULED && it.startsAt >= now }.take(2),
            )
        }
    }

    /** 투수(0)·타자(1) 2회. 병렬로 치고, 한쪽이 실패해도 나머지로 화면은 뜬다. */
    private suspend fun fetchInfo(id: Long): Pair<TeamInfoDto?, TeamInfoDto?> = coroutineScope {
        val p = async { runCatching { api.teamInfo(id, 0).body().teamInfo }.getOrNull() }
        val b = async { runCatching { api.teamInfo(id, 1).body().teamInfo }.getOrNull() }
        p.await() to b.await()
    }

    /** 선수 상세. 화면 진입 시 1회 — 서버 캐시가 1시간이라 이걸로 충분하다. */
    suspend fun player(id: Long): PlayerDetail? =
        runCatching { api.playerInfo(id).body().info?.toDetail() }.getOrNull()
}
```

<div class="callout warn"><span class="t">요청이 2회인 건 실수가 아니다</span>
<code>api.teamInfo(id, 0)</code>만 부르면 <strong>투수만</strong> 옵니다(두산 43명). 타자 47명은 <code>player_position=1</code>이 있어야 옵니다. 두 응답 모두 <code>team_detail</code>(명칭·구장·감독·연혁)을 똑같이 싣고 있으므로 먼저 도착한 쪽을 씁니다. 응답은 각 8 KB, 서버 캐시 1시간이고 팀 화면에서만 부르므로 OkHttp <code>Cache</code>까지 붙일 필요는 없습니다 — 화면을 오갈 때 반복 호출이 거슬리면 그때 넣으세요.
</div>

### 2.2 헤더

`feature/teams/TeamHeader.kt`:

```kotlin
@Composable
fun TeamHeader(team: TeamRef, nameEn: String?, record: String,
               isFav: Boolean, onFav: () -> Unit, onBack: () -> Unit) {
    val base = teamColor(team.id)
    Box(Modifier.fillMaxWidth()) {
        // 팀 컬러 글로우. 원색을 면으로 깔면 두산(#232A63)·롯데(#24406E)는 다크 배경에서 안 보인다
        Box(Modifier.matchParentSize()
            .background(Brush.radialGradient(listOf(base.copy(alpha = .45f), Color.Transparent))))
        Column(Modifier.padding(bottom = 18.dp)) {
            Row(Modifier.fillMaxWidth().padding(horizontal = 6.dp, vertical = 6.dp),
                horizontalArrangement = Arrangement.SpaceBetween) {
                IconButton(onClick = onBack) { DsIcon(Icons.Outlined.ChevronLeft) }
                IconButton(onClick = onFav) {
                    DsIcon(if (isFav) Icons.Filled.Star else Icons.Outlined.StarBorder,
                        tint = if (isFav) DsColors.gold else DsColors.muted2)
                }
            }
            Row(Modifier.padding(start = 20.dp), horizontalArrangement = Arrangement.spacedBy(15.dp),
                verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(56.dp).clip(CircleShape).background(base)      // 엠블럼 = 팀 원색
                    .border(2.dp, MaterialTheme.colorScheme.onBackground.copy(alpha = .25f), CircleShape),
                    Alignment.Center) {
                    Text(teamShort(team.id), color = Color.White, fontWeight = FontWeight.Bold)
                }
                Column {
                    nameEn?.let {                                                // 팀 틴트 = 팀 색의 글자용
                        Text(it.uppercase(), style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold, letterSpacing = 0.12.em, color = teamTint(team.id))
                    }
                    Text(team.nameKo, style = Display.copy(fontSize = 34.sp))
                    Text(record, style = ScoreNumber.copy(fontSize = 14.sp),
                        color = MaterialTheme.colorScheme.onSurfaceVariant)      // 리그 5위 · 65·60·4 · .520 · 2승
                }
            }
        }
    }
}
```

팀 로고를 쓰려면 Coil 3로 불러오고 실패 시 위 배지로 대체합니다. **URL이 `http://`로 오므로 반드시 승격합니다**(Step 3 `toHttps`).

```kotlin
AsyncImage(
    model = "https://storage.wisetoto.com/data/sports_db/team_${team.id}.png",
    contentDescription = team.nameKo,
    error = rememberVectorPainter(Icons.Outlined.Shield),
    modifier = Modifier.size(56.dp).clip(CircleShape),
)
```

### 2.3 ViewModel · 화면

`core/ui/DsHelpers.kt`에 행 하나를 추가합니다 — 팀 상세·선수 상세가 같이 씁니다.

```kotlin
/** 값이 null이면 행 자체를 그리지 않는다(계획서 §1.3 표시 원칙 — 빈칸도 "-"도 두지 않는다). */
@Composable
fun KeyValueRow(label: String, value: String?, valueColor: Color = Color.Unspecified,
                onClick: (() -> Unit)? = null) {
    if (value == null) return
    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
    Row(Modifier.fillMaxWidth()
        .then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier)
        .padding(horizontal = 16.dp, vertical = 13.dp),
        horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant,
            style = MaterialTheme.typography.bodyMedium)
        Text(value, color = valueColor, style = MaterialTheme.typography.bodyMedium)
    }
}
```

`feature/teams/TeamDetailViewModel.kt` — UI 상태와 표시 문자열은 여기서 만듭니다:

```kotlin
data class TeamDetailUi(
    val team: TeamRef, val nameEn: String?, val record: String,
    val stadium: String?, val manager: String?,
    val pitcherCount: Int, val batterCount: Int,
    val recent: List<GameSummary>, val upcoming: List<GameSummary>,
    val isFavorite: Boolean,
)

/** "리그 5위 · 65·60·4 · .520 · 2승" — 표시 문자열이라 repository가 아니라 여기서 만든다. */
fun teamRecord(s: Standing): String = buildString {
    append("리그 ${s.position}위 · ${s.wins}·${s.losses}·${s.draws}")
    append(" · ${"%.3f".format(s.winPct).removePrefix("0")}")
    s.streak?.let { append(" · $it") }
}

@HiltViewModel(assistedFactory = TeamDetailViewModel.Factory::class)
class TeamDetailViewModel @AssistedInject constructor(
    private val repo: TeamsRepository,
    private val standings: StandingsRepository,
    private val favorites: FavoritesRepository,
    @Assisted private val key: TeamDetailKey,       // ← Nav3 인자 (Step 2 core/navigation)
) : ViewModel() {
    val ui: StateFlow<TeamDetailUi?> = combine(
        repo.observeTeam(key.teamId),
        standings.observe(standings.currentSeasonYear()),
        favorites.observeTeams(),
    ) { d, table, favs ->
        TeamDetailUi(
            team = d.team, nameEn = d.nameEn,
            record = table.firstOrNull { it.team.id == key.teamId }?.let(::teamRecord).orEmpty(),
            stadium = d.stadium, manager = d.manager,
            pitcherCount = d.pitchers.size, batterCount = d.batters.size,
            recent = d.recent, upcoming = d.upcoming,
            isFavorite = key.teamId in favs,
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    fun toggleFavorite() = viewModelScope.launch { favorites.toggle(key.teamId) }

    @AssistedFactory
    interface Factory { fun create(key: TeamDetailKey): TeamDetailViewModel }
}

@Composable
fun TeamDetailScreen(key: TeamDetailKey, onGame: (Long) -> Unit, onRoster: (Long) -> Unit, onBack: () -> Unit) {
    val vm = hiltViewModel<TeamDetailViewModel, TeamDetailViewModel.Factory>(
        creationCallback = { factory -> factory.create(key) },
    )
    val ui by vm.ui.collectAsStateWithLifecycle()
    ui?.let { d ->
        LazyColumn(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
            item { TeamHeader(d.team, d.nameEn, d.record, d.isFavorite, vm::toggleFavorite, onBack) }
            item { SectionLabel("구단 정보") }
            item { KeyValueRow("홈구장", d.stadium) }
            item { KeyValueRow("감독", d.manager) }
            item {
                KeyValueRow("선수단", "투수 ${d.pitcherCount} · 타자 ${d.batterCount} ›",
                    valueColor = MaterialTheme.colorScheme.primary,     // 이동은 앱 기능 = 액센트
                    onClick = { onRoster(d.team.id) })
            }
            item { SectionLabel("최근 경기") }
            items(d.recent, key = { it.id }) { g -> GameCard(g) { onGame(g.id) } }
            item { SectionLabel("다음 경기") }
            items(d.upcoming, key = { it.id }) { g -> GameCard(g) { onGame(g.id) } }
            item { Caption("최근·다음 경기는 Step 4 프리페치로 받아 둔 시즌 일정에서 옵니다 — 네트워크 없이 열립니다.") }
        }
    } ?: LoadingCards(count = 3)
}
```

<div class="callout danger"><span class="t">예정 경기에 선발 투수를 그리지 마세요</span>
<code>Schedule_Month</code> 행에는 <code>home_pitcher</code>·<code>away_pitcher</code>가 <strong>아예 없습니다</strong>(<code>game_timestamp</code>도 없습니다). 선발은 <code>Schedule_Day</code>에만 있으므로, 프리페치로만 채워진 미래 경기의 <code>homeStarter</code>는 <code>null</code>입니다. <code>GameCard</code>는 <code>null</code>을 그리지 않으니 그대로 두면 되고, 당일 <code>refreshDay()</code>가 돌면 같은 행에 선발이 덮어써집니다. 여기서 "선발 미정" 같은 문자열을 만들어 넣으면 표시 원칙 위반입니다.
</div>

<div class="callout tip"><span class="t">전적 문자열은 순위 캐시에서</span>
<code>record</code>는 <code>StandingsRepository.observe(year)</code>를 <code>combine</code>에 넣고 해당 팀 행을 찾아 <code>teamRecord()</code>로 만듭니다. 순위를 아직 한 번도 안 받았으면 빈 문자열이고, 받는 순간 Room Flow가 다시 방출해 채워집니다. repository가 완성된 문자열을 내보내게 하지 마세요.
</div>

## 3. 팀 정보 — 선수단과 연혁

목업의 두 번째 팀 화면입니다. 위 `observeTeam`을 **그대로** 재사용하므로 새 네트워크 코드가 없습니다.

`feature/teams/TeamRosterScreen.kt`:

```kotlin
@HiltViewModel(assistedFactory = TeamRosterViewModel.Factory::class)
class TeamRosterViewModel @AssistedInject constructor(
    repo: TeamsRepository,
    @Assisted key: TeamRosterKey,
) : ViewModel() {
    val ui: StateFlow<TeamDetail?> = repo.observeTeam(key.teamId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    @AssistedFactory
    interface Factory { fun create(key: TeamRosterKey): TeamRosterViewModel }
}

@Composable
fun TeamRosterScreen(key: TeamRosterKey, onPlayer: (PlayerDetailKey) -> Unit, onBack: () -> Unit) {
    val vm = hiltViewModel<TeamRosterViewModel, TeamRosterViewModel.Factory>(
        creationCallback = { factory -> factory.create(key) },
    )
    val d by vm.ui.collectAsStateWithLifecycle()
    var pitching by rememberSaveable { mutableStateOf(true) }

    d?.let { t ->
        // 육성선수(등번호 100번대)는 아래로 내린다 — 서버가 구분해 주지 않는 앱 규칙이다
        val (firstTeam, development) = (if (pitching) t.pitchers else t.batters)
            .partition { !it.isDevelopment }

        LazyColumn(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
            item { RosterHeader(t, onBack) }
            item { RosterTabs(pitching, t.pitchers.size, t.batters.size) { pitching = it } }

            items(firstTeam, key = { it.id }) { p ->
                RosterRow(p, t.team.id) { onPlayer(PlayerDetailKey(p.id, t.team.id)) }
            }
            if (development.isNotEmpty()) item("dev") { LabeledDivider("육성선수 · 100번대", DsColors.muted2) }   // Step 5 §4
            items(development, key = { it.id }) { p ->
                RosterRow(p, t.team.id, dim = true) { onPlayer(PlayerDetailKey(p.id, t.team.id)) }
            }

            item { SectionLabel("구단 연혁") }
            items(t.history) { e -> HistoryRow(e, t.team.id) }
            item {
                // 서버는 우승 횟수를 주지 않는다 — 연혁 문자열을 세는 앱 규칙이다
                val titles = t.history.count { "한국시리즈 우승" in it.text }
                Text("우승 ${titles}회 · 전체 ${t.history.size}건", Modifier.padding(16.dp),
                    style = Display.copy(fontSize = 14.sp), color = DsColors.live)
            }
            item { Caption("선수단은 Team_Info를 투수·타자 두 번 불러 받습니다. 목록에는 등번호·이름·사진뿐이라 포수·내야수 구분은 선수 상세에만 있습니다.") }
        }
    } ?: LoadingCards(count = 4)
}
```

**헤더·행·탭·연혁 조각** (완전한 코드)

```kotlin
/** 팀 상세의 `TeamHeader`보다 얕은 헤더 — 전적·즐겨찾기는 팀 상세에만 둔다. */
@Composable
private fun RosterHeader(t: TeamDetail, onBack: () -> Unit) {
    Box(Modifier.fillMaxWidth()) {
        Box(Modifier.matchParentSize().background(
            Brush.radialGradient(listOf(teamColor(t.team.id).copy(alpha = .45f), Color.Transparent))))
        Column(Modifier.padding(bottom = 14.dp)) {
            Row(Modifier.fillMaxWidth().padding(horizontal = 6.dp),
                verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = onBack) { DsIcon(Icons.Outlined.ChevronLeft) }
                Text("팀 정보", style = MaterialTheme.typography.titleMedium, color = DsColors.muted2)
            }
            Row(Modifier.padding(start = 20.dp), horizontalArrangement = Arrangement.spacedBy(15.dp),
                verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(54.dp).clip(CircleShape).background(teamColor(t.team.id)),
                    Alignment.Center) {
                    Text(teamShort(t.team.id), color = Color.White, fontWeight = FontWeight.Bold)
                }
                Column {
                    t.nameEn?.let {
                        Text(it.uppercase(), style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold, color = teamTint(t.team.id))
                    }
                    Text(t.team.nameKo, style = Display.copy(fontSize = 32.sp))
                    Caption(listOfNotNull(t.stadium, t.manager?.let { "감독 $it" }).joinToString(" · "))
                }
            }
        }
    }
}

@Composable
private fun RosterRow(p: RosterPlayer, teamId: Long, dim: Boolean = false, onClick: () -> Unit) = Column {
    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
    Row(Modifier.fillMaxWidth().clickable(onClick = onClick)
        .padding(horizontal = 16.dp, vertical = 9.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(13.dp)) {
        Text(p.number?.toString() ?: "-", Modifier.width(34.dp), textAlign = TextAlign.End,
            style = Display.copy(fontSize = 22.sp),
            color = if (dim) DsColors.muted2 else teamTint(teamId))   // 등번호 = 팀 색
        PlayerAvatar(p.photoUrl)                                       // Step 5 §8
        Text(p.name, style = MaterialTheme.typography.bodyLarge,
            color = if (dim) MaterialTheme.colorScheme.onSurfaceVariant
                    else MaterialTheme.colorScheme.onSurface)
    }
}

@Composable
private fun RosterTabs(pitching: Boolean, pitchers: Int, batters: Int, onSelect: (Boolean) -> Unit) = Row(
    Modifier.padding(horizontal = 16.dp, vertical = 10.dp),
    horizontalArrangement = Arrangement.spacedBy(8.dp)) {
    RosterChip("투수 $pitchers", pitching) { onSelect(true) }
    RosterChip("타자 $batters", !pitching) { onSelect(false) }
}

@Composable
private fun RosterChip(text: String, on: Boolean, onClick: () -> Unit) = Surface(
    onClick = onClick, shape = RoundedCornerShape(12.dp),
    color = if (on) MaterialTheme.colorScheme.primary else Color.Transparent,   // 탭 = 앱 액센트
    border = if (on) null else BorderStroke(1.dp, MaterialTheme.colorScheme.outline)) {
    Text(text, Modifier.padding(horizontal = 16.dp, vertical = 7.dp),
        style = Display.copy(fontSize = 15.sp),
        color = if (on) MaterialTheme.colorScheme.onPrimary else DsColors.muted2)
}

@Composable
private fun HistoryRow(e: TeamHistoryEntry, teamId: Long) = Column {
    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
    Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 7.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(e.year?.toString().orEmpty(), Modifier.width(44.dp), style = Display.copy(fontSize = 17.sp),
            color = if ("창단" in e.text) teamTint(teamId) else DsColors.muted2)
        Text(e.text, style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
```

<div class="callout danger"><span class="t">등번호로 <code>key</code>를 잡지 마세요</span>
<code>items(..., key = { it.number })</code>로 쓰면 <strong>두산 48번(벤자민·김영현)에서 Compose가 중복 key 예외로 크래시</strong>합니다. 등번호는 팀 안에서 유일하지 않습니다 — 키는 <code>seq</code>(=<code>RosterPlayer.id</code>)입니다. 문자열이라 정렬도 그냥 하면 <code>1, 10, 101, 104, 11 …</code>이 되고요. 둘 다 Step 3의 <code>toRoster()</code>가 처리했으니 화면은 순서를 믿고 그리면 됩니다.
</div>

## 4. 선수 정보 — 타자와 투수

목업의 마지막 화면입니다. **한 라우트인데 표가 두 벌**이므로 `when`으로 갈라 그립니다(Step 3 함정 10).

`feature/players/PlayerDetailScreen.kt`:

```kotlin
@HiltViewModel(assistedFactory = PlayerDetailViewModel.Factory::class)
class PlayerDetailViewModel @AssistedInject constructor(
    private val repo: TeamsRepository,
    @Assisted private val key: PlayerDetailKey,
) : ViewModel() {
    val ui: StateFlow<PlayerDetail?> = flow { emit(repo.player(key.playerId)) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    @AssistedFactory
    interface Factory { fun create(key: PlayerDetailKey): PlayerDetailViewModel }
}

@Composable
fun PlayerDetailScreen(key: PlayerDetailKey, onBack: () -> Unit) {
    val vm = hiltViewModel<PlayerDetailViewModel, PlayerDetailViewModel.Factory>(
        creationCallback = { factory -> factory.create(key) },
    )
    val d by vm.ui.collectAsStateWithLifecycle()
    d?.let { p ->
        Column(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)
            .verticalScroll(rememberScrollState())) {
            PlayerHeader(p.profile, key.teamId, onBack)
            when (val r = p.record) {                    // sealed라 when이 강제된다
                is PlayerRecord.Batting  -> BattingBlocks(r)
                is PlayerRecord.Pitching -> PitchingBlocks(r)
            }
            SectionLabel("프로필")
            ProfileRows(p.profile)
            Spacer(Modifier.height(24.dp))
        }
    } ?: LoadingCards(count = 3)
}
```

<div class="callout warn"><span class="t">소속 팀은 응답에 없다 — 키가 들고 온다</span>
<code>Player_Info</code>의 <code>player_detail</code>에는 이름·포지션·신체·출신교·계약 정보는 있어도 <strong>팀 필드가 없습니다.</strong> 그래서 <code>PlayerDetailKey(playerId, teamId)</code>가 팀을 함께 실어 옵니다(Step 2). 팀 색·팀명이 전부 이 <code>teamId</code>에서 나옵니다 — 선수단에서 들어왔으니 호출자는 항상 알고 있습니다.
</div>

### 4.1 헤더와 프로필

```kotlin
@Composable
private fun PlayerHeader(p: PlayerProfile, teamId: Long, onBack: () -> Unit) {
    Box(Modifier.fillMaxWidth()) {
        Box(Modifier.matchParentSize().background(
            Brush.radialGradient(listOf(teamColor(teamId).copy(alpha = .45f), Color.Transparent))))
        Column(Modifier.padding(bottom = 16.dp)) {
            Row(Modifier.fillMaxWidth().padding(horizontal = 6.dp),
                verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = onBack) { DsIcon(Icons.Outlined.ChevronLeft) }
                Text("선수 정보", style = MaterialTheme.typography.titleMedium, color = DsColors.muted2)
            }
            Row(Modifier.padding(start = 20.dp), horizontalArrangement = Arrangement.spacedBy(16.dp),
                verticalAlignment = Alignment.CenterVertically) {
                PlayerAvatar(p.photoUrl, size = 66.dp)
                Column {
                    Row(verticalAlignment = Alignment.Bottom,
                        horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                        Text(p.number?.toString().orEmpty(), style = Display.copy(fontSize = 26.sp),
                            color = teamTint(teamId))          // 등번호 = 팀 색
                        Text(p.name, style = Display.copy(fontSize = 36.sp))
                    }
                    Caption(listOfNotNull(p.position, p.bats, teamNameKo(teamId, "")).joinToString(" · "))
                }
            }
        }
    }
}

/** 만 나이는 서버가 주지 않는다 — 생년월일로 계산한다. */
private fun age(birth: LocalDate) = Period.between(birth, LocalDate.now(SEOUL)).years

@Composable
private fun ProfileRows(p: PlayerProfile) {
    fun join(vararg parts: String?) = parts.filterNotNull().takeIf { it.isNotEmpty() }?.joinToString(" · ")
    KeyValueRow("생년월일", p.birthDay?.let { "$it (${age(it)}세)" })
    KeyValueRow("신장 · 체중", join(p.heightCm?.let { "${it}cm" }, p.weightKg?.let { "${it}kg" }))
    KeyValueRow("출신교", p.school)
    KeyValueRow("입단", join(p.joinYear?.let { "${it}년" }, p.draft))
    KeyValueRow("계약금 · 연봉", join(p.signingBonus, p.salary))
    KeyValueRow("국적", p.nationality)
}
```

### 4.2 표 네 벌 — 전부 `StatTable` 하나로

```kotlin
@Composable
private fun BattingBlocks(r: PlayerRecord.Batting) {
    val total = r.months.lastOrNull { it.month == null }      // 합계 행 = month null (서버의 "13")
    StatTiles(listOf(
        (total?.avg ?: "-") to "타율",
        (total?.homeRuns?.toString() ?: "-") to "홈런",
        (total?.rbi?.toString() ?: "-") to "타점",
        (total?.hits?.toString() ?: "-") to "안타",
    ))
    Caption("${total?.games ?: 0}경기 · ${total?.atBats ?: 0}타수")

    SectionLabel("월별 기록")
    StatTable(
        headers = listOf("월", "타율", "경기", "타수", "안타", "홈런", "타점"),
        weights = listOf(.8f, 1.2f, 1f, 1f, 1f, 1f, 1f),
        rows = r.months.map { m ->
            StatRow(
                listOf(m.month?.toString() ?: "합계", m.avg, m.games?.toString(), m.atBats?.toString(),
                       m.hits?.toString(), m.homeRuns?.toString(), m.rbi?.toString()),
                emphasized = m.month == null,
            )
        },
    )

    SectionLabel("최근 5경기")
    StatTable(
        headers = listOf("날짜", "상대", "타순", "타수-안타", "홈런", "타점", "누적타율"),
        weights = listOf(1f, 1f, .7f, 1.4f, .7f, .7f, 1.2f),
        rows = r.recent.map { g ->
            StatRow(listOf(
                g.date?.format(shortDate), g.opponent, g.order,
                g.atBats?.let { "$it-${g.hits ?: 0}" },
                g.homeRuns?.toString(), g.rbi?.toString(), g.cumulativeAvg))
        },
    )
    Caption("최근 경기의 타율은 그 경기 성적이 아니라 그 시점 누적값입니다.")
}

@Composable
private fun PitchingBlocks(r: PlayerRecord.Pitching) {
    val total = r.months.lastOrNull { it.month == null }
    StatTiles(listOf(
        (total?.era ?: "-") to "평균자책",
        (total?.wins?.toString() ?: "-") to "승",
        (total?.innings ?: "-") to "이닝",
        (total?.strikeOuts?.toString() ?: "-") to "탈삼진",
    ))
    Caption("${total?.losses ?: 0}패 · 세이브 ${total?.saves ?: 0} · 홀드 ${total?.holds ?: 0}")

    SectionLabel("월별 기록")
    StatTable(
        headers = listOf("월", "ERA", "승", "패", "세", "홀", "이닝", "삼진"),
        weights = listOf(.8f, 1.2f, .7f, .7f, .7f, .7f, 1.1f, .9f),
        rows = r.months.map { m ->
            StatRow(
                listOf(m.month?.toString() ?: "합계", m.era, m.wins?.toString(), m.losses?.toString(),
                       m.saves?.toString(), m.holds?.toString(), m.innings, m.strikeOuts?.toString()),
                emphasized = m.month == null,
            )
        },
    )

    SectionLabel("최근 5경기")
    StatTable(
        headers = listOf("날짜", "상대", "이닝", "투구", "피안타", "삼진", "누적ERA"),
        weights = listOf(1f, 1f, .9f, .9f, .9f, .8f, 1.2f),
        rows = r.recent.map { g ->
            StatRow(listOf(
                g.date?.format(shortDate), g.opponent, g.innings, g.pitches?.toString(),
                g.hits?.toString(), g.strikeOuts?.toString(), g.cumulativeEra))
        },
    )
    Caption("선발은 5경기가 한 달에 걸칩니다. 기록 없이 로그만 오는 경기는 — 로 남습니다.")
}
```

<div class="callout danger"><span class="t">요약 타일에 세이브·홀드를 넣지 마세요</span>
선발 투수는 세이브·홀드가 <strong>항상 0</strong>이고, 불펜 투수는 이닝·탈삼진이 작습니다. 한 레이아웃으로 둘 다 읽히게 하려면 타일은 <strong>ERA · 승 · 이닝 · 탈삼진</strong>으로 고정하고 세이브·홀드는 아랫줄 <code>Caption</code>으로 내립니다. 곽빈(선발, ERA 2.26 / 11승 / 155이닝 / 186K)과 곽도규(불펜, 1.33 / 2승 / 27이닝 / 31K)를 같은 화면에 넣어 보면 바로 확인됩니다.
</div>

<div class="callout warn"><span class="t">이 화면에서 절대 계산하지 않는 것</span>
<ul>
<li><strong>합계를 월 합으로 만들지 않습니다.</strong> 서버의 합계 행과 월별 합이 다릅니다(Step 3).</li>
<li><strong>누적 타율·ERA를 그 경기 성적으로 읽지 않습니다.</strong> 컬럼 이름에 "누적"을 박아 둔 이유입니다.</li>
<li><strong><code>null</code>을 <code>0</code>으로 메우지 않습니다.</strong> <code>StatTable</code>이 <code>—</code>로 그립니다.</li>
<li><strong><code>ip:"0.2"</code>를 0.2이닝으로 읽지 않습니다.</strong> 매퍼가 ⅔로 바꿔 둡니다.</li>
</ul>
</div>

## 5. 팀 목록 (TeamsScreen)

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
<code>/extra/Team_Select</code>가 10개 구단(약칭·<code>team_ifno_seq</code>)을 주지만, 목록에 필요한 건 <strong>id·한글명·컬러</strong>뿐이고 셋 다 로컬에 있으니 요청 하나를 안 하는 쪽이 맞습니다. 팀 상세로 들어가면 그때 <code>Team_Info</code>를 (투수·타자) 2회 칩니다. 최근·다음 경기는 Room에 이미 있습니다.
</div>

## 6. 즐겨찾기

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
        .map { ids -> ids.map { TeamRef(it, teamNameKo(it, ""), teamShort(it)) } }
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
            DsIcon(Icons.Outlined.StarBorder, size = 52.dp, tint = DsColors.muted2)
            Text("즐겨찾는 구단이 없어요", style = MaterialTheme.typography.bodyLarge)
            Caption("팀 상세에서 별을 눌러 추가하면 여기와 경기 목록 상단에 고정됩니다.")
        } else LazyColumn(
            contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            item { SectionLabel("내 구단") }
            items(teams, key = { it.id }) { t -> FavoriteTeamCard(t) { onTeam(t.id) } }
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
로그인 없이 Room에만 저장합니다. 즐겨찾은 구단을 경기 목록 상단에 고정하려면 <code>GamesRepository.observeByDate</code>를 <code>favorites.observeTeams()</code>와 <code>combine</code>해 정렬 키를 얹습니다(Step 6-5).
</div>

## 7. 실행 확인

<div class="checkpoint"><span class="t"></span> 아래가 전부 되면 완료입니다.
<ul>
<li>순위(진출선 포함) → 팀 선택 → 컬러 헤더의 팀 상세 → 최근 경기 → 경기 상세</li>
<li>팀 상세의 <strong>선수단 투수 nn · 타자 nn ›</strong> → 선수단 화면에서 투수/타자 탭 전환, 육성선수 구분선</li>
<li>선수단에서 선수 탭 → <strong>타자는 타율·홈런·타점 표, 투수는 ERA·승·이닝·삼진 표</strong>가 뜨고 섞이지 않음</li>
<li>월별 표의 마지막 행이 <code>13</code>이 아니라 <strong>합계</strong>로 강조돼 있음</li>
<li>기록이 없는 경기 행이 <code>0</code>이 아니라 <code>—</code>로 보임 (곽빈 8/22)</li>
<li>별을 누르면 즐겨찾기에 추가되어 목록 상단에 고정</li>
<li><strong>두산(네이비)과 KIA(레드)를 번갈아 열어</strong> 팀 색만 바뀌고 탭바·링크는 레드로 유지되는지</li>
<li>라이트 테마에서도 위가 전부 읽히는지 (팀 틴트가 뒤집히는 게 정상입니다)</li>
</ul>
목업의 순위·팀 상세·팀 정보·선수 정보와 대조하세요.</div>

<div class="pager">
<a href="#/labs/step-7">← Step 7</a>
<a href="#/labs/step-9">Step 9 · 마감·릴리스 →</a>
</div>
