# Step 5 · 경기 목록 화면

<div class="chips"><span class="chip time">90분</span><span class="chip diff">보통</span><span class="chip goal">날짜별 경기 목록 + 라이브 자동 갱신을 화면에 띄운다</span></div>

드디어 눈에 보이는 화면입니다. 날짜를 이동하며 경기를 보고, 라이브 경기는 **요청 1개**로 자동 갱신합니다.

## 1. UiState와 ViewModel

`feature/games/GamesViewModel.kt`:

```kotlin
data class GamesUiState(
    val date: LocalDate = LocalDate.now(ZoneId.of("Asia/Seoul")),
    val games: List<GameSummary> = emptyList(),
    val isRefreshing: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class GamesViewModel @Inject constructor(
    private val repo: GamesRepository,
    savedState: SavedStateHandle,
) : ViewModel() {
    private val date = MutableStateFlow(
        savedState.get<String>("date")?.let(LocalDate::parse)
            ?: LocalDate.now(ZoneId.of("Asia/Seoul"))
    )

    val ui: StateFlow<GamesUiState> = date
        .flatMapLatest { d -> repo.observeByDate(d).map { d to it } }
        .map { (d, games) -> GamesUiState(date = d, games = games) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), GamesUiState())

    fun move(days: Long) { date.update { it.plusDays(days) } }
    fun today() { date.value = LocalDate.now(ZoneId.of("Asia/Seoul")) }
    fun refreshLive() = viewModelScope.launch { runCatching { repo.refreshLive() } }
}
```

## 2. 경기 카드 (원정팀 먼저!)

`feature/games/GameCard.kt`. SofaScore의 `displayInverseHomeAwayTeams`에 맞춰 **원정팀을 위/왼쪽**에 둡니다.

```kotlin
@Composable
fun GameCard(g: GameSummary, onClick: () -> Unit) {
    Card(Modifier.fillMaxWidth().padding(vertical = 4.dp).clickable(onClick = onClick)) {
        Column(Modifier.padding(12.dp)) {
            StatusChip(g)                        // 상태(원문 라벨) + 라이브 강조
            TeamRow(g.away, g.awayRuns)          // 원정 먼저
            TeamRow(g.home, g.homeRuns)          // 홈 나중
        }
    }
}

@Composable private fun TeamRow(team: TeamRef, runs: Int?) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(team.nameKo, style = MaterialTheme.typography.bodyLarge)
        Text(runs?.toString() ?: "-", style = MaterialTheme.typography.titleMedium)  // null이면 "-" (0 아님)
    }
}

@Composable private fun StatusChip(g: GameSummary) {
    val label = when (g.status) {
        GameStatus.LIVE -> "● ${g.statusLabel}"       // 라이브 강조
        GameStatus.FINAL -> "종료"
        GameStatus.SCHEDULED ->
            g.startsAt.atZone(ZoneId.of("Asia/Seoul")).toLocalTime().toString().take(5)
        else -> g.statusLabel                          // 취소/연기 등 원문
    }
    AssistChip(onClick = {}, label = { Text(label) })
}
```

## 3. 목록 화면

`feature/games/GamesScreen.kt`:

```kotlin
@Composable
fun GamesScreen(vm: GamesViewModel = hiltViewModel(), onGame: (Long) -> Unit) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    Column(Modifier.fillMaxSize()) {
        DateBar(ui.date, onPrev = { vm.move(-1) }, onNext = { vm.move(1) }, onToday = vm::today)
        when {
            ui.games.isEmpty() -> EmptyDay()
            else -> LazyColumn {
                items(ui.games, key = { it.id }) { GameCard(it) { onGame(it.id) } }
            }
        }
    }
}
```

<div class="callout tip"><span class="t">stable key</span>
<code>items(..., key = { it.id })</code>로 안정적인 key를 주면 리스트 갱신 시 recomposition이 최소화됩니다.
</div>

## 4. 라이브 폴링 — 화면이 보일 때만

`GET /sport/baseball/events/live` 한 번이 진행 중인 전 경기를 줍니다. **`STARTED` 라이프사이클**에서만 20초 간격으로 돕니다.

```kotlin
@Composable
fun LivePolling(vm: GamesViewModel, hasLive: Boolean) {
    val owner = LocalLifecycleOwner.current
    LaunchedEffect(hasLive) {
        if (!hasLive) return@LaunchedEffect
        owner.repeatOnLifecycle(Lifecycle.State.STARTED) {
            while (true) {
                vm.refreshLive()
                delay(20_000L + Random.nextLong(-2000, 2000))   // jitter ±2s
            }
        }
    }
}
```

화면에서 `LivePolling(vm, hasLive = ui.games.any { it.status == GameStatus.LIVE })`로 호출합니다.

<div class="callout warn"><span class="t">홈으로 나가면 멈춰야 한다</span>
<code>repeatOnLifecycle(STARTED)</code>가 앱을 백그라운드로 보내면 자동으로 코루틴을 취소합니다. 이걸 안 쓰면 배터리·트래픽이 새고 차단 위험이 커집니다.
</div>

## 5. 실행 확인

▶로 실행합니다.

<div class="checkpoint"><span class="t"></span> 오늘 날짜의 경기가 보이고, 날짜 화살표로 과거/미래가 즉시(네트워크 없이) 바뀌면 성공. 경기일이라면 30분 켜두고 점수가 자동 갱신되는지, 홈 버튼 후 복귀 시 폴링이 멈췄다 재개되는지 확인하세요.</div>

<div class="pager">
<a href="#/labs/step-4">← Step 4</a>
<a href="#/labs/step-6">Step 6 · 경기 상세 →</a>
</div>
