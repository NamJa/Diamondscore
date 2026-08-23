# Step 6 · 경기 목록 화면

<div class="chips"><span class="chip time">90분</span><span class="chip diff">보통</span><span class="chip goal">Step 5 컴포넌트를 조립해 날짜별 목록 + 라이브 갱신을 완성한다</span></div>

첫 화면입니다. Step 5에서 만든 `GameCard`·`DsBottomBar`·상태 컴포넌트를 조립하고, 날짜 네비게이션과
**요청 1개짜리 라이브 폴링**을 붙입니다. 목업의 홈 화면을 그대로 만듭니다.

## 1. UiState와 ViewModel

`feature/games/GamesViewModel.kt` (신선도 enum은 `domain/model`에 두어도 됩니다):

```kotlin
enum class Freshness { FRESH, STALE, OFFLINE }

data class GamesUiState(
    val date: LocalDate = LocalDate.now(SEOUL),
    val games: List<GameSummary> = emptyList(),
    val loading: Boolean = true,
    val freshness: Freshness = Freshness.FRESH,   // FRESH / STALE / OFFLINE
    val error: Boolean = false,
)

@HiltViewModel
class GamesViewModel @Inject constructor(
    private val repo: GamesRepository,
    savedState: SavedStateHandle,
) : ViewModel() {
    private val date = MutableStateFlow(
        savedState.get<String>("date")?.let(LocalDate::parse) ?: LocalDate.now(SEOUL))

    val ui: StateFlow<GamesUiState> = date
        .flatMapLatest { d -> repo.observeByDate(d).map { d to it } }
        .map { (d, games) -> GamesUiState(date = d, games = games, loading = false) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), GamesUiState())

    fun move(days: Long) { date.update { it.plusDays(days) } }
    fun today() { date.value = LocalDate.now(SEOUL) }
    fun refreshLive() = viewModelScope.launch { runCatching { repo.refreshLive() } }
}
```

## 2. 날짜 바 (DateBar)

목업 상단: `‹ 8월 2일 토 ›` + "오늘" 버튼.

`feature/games/DateBar.kt`:

```kotlin
@Composable
fun DateBar(date: LocalDate, onPrev: () -> Unit, onNext: () -> Unit, onToday: () -> Unit) {
    val isToday = date == LocalDate.now(SEOUL)
    Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
            IconButton(onClick = onPrev) { DsIcon(Icons.Outlined.ChevronLeft) }
            Text(date.format(dateFmt), style = MaterialTheme.typography.titleMedium)  // 8월 2일 토
            IconButton(onClick = onNext) { DsIcon(Icons.Outlined.ChevronRight) }
        }
        if (!isToday) TextButton(onClick = onToday) { Text("오늘", color = DsColors.live) }
    }
}
```

`SavedStateHandle`에 선택 날짜를 보존하면 프로세스 재생성 후에도 유지됩니다.

## 3. 화면 조립

`feature/games/GamesScreen.kt` — 컴포넌트를 상태에 따라 배치합니다.

```kotlin
@Composable
fun GamesScreen(vm: GamesViewModel = hiltViewModel(), onGame: (Long) -> Unit) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    Column(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        TopBar(title = "경기", subtitle = "KBO 2026")
        DateBar(ui.date, onPrev = { vm.move(-1) }, onNext = { vm.move(1) }, onToday = vm::today)
        if (ui.freshness == Freshness.OFFLINE) StaleBanner("마지막 갱신 10분 전")

        when {
            ui.loading            -> LoadingCards()
            ui.error              -> ErrorState(onRetry = vm::refreshLive)
            ui.games.isEmpty()    -> EmptyDay(onNearest = { /* 가장 가까운 경기일 */ })
            else -> LazyColumn(
                contentPadding = PaddingValues(12.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                sectioned(ui.games).forEach { (title, items) ->
                    item { SectionLabel(title) }                       // 진행 중 / 예정 / 종료
                    items(items, key = { it.id }) { GameCard(it) { onGame(it.id) } }
                }
            }
        }
    }
}
```

`sectioned()`는 `status`로 진행 중 → 예정 → 종료 순으로 묶는 순수 함수입니다.

```kotlin
fun sectioned(games: List<GameSummary>): List<Pair<String, List<GameSummary>>> = buildList {
    fun bucket(title: String, pred: (GameSummary) -> Boolean) =
        games.filter(pred).takeIf { it.isNotEmpty() }?.let { add(title to it) }
    bucket("진행 중") { it.status == GameStatus.LIVE }
    bucket("예정")   { it.status == GameStatus.SCHEDULED }
    bucket("종료")   { it.status == GameStatus.FINAL }
    bucket("취소·연기") { it.status in setOf(GameStatus.CANCELED, GameStatus.POSTPONED, GameStatus.SUSPENDED) }
}
```

`key = { it.id }`로 안정적인 key를 주는 것을 잊지 마세요(recomposition 최소화).

<div class="callout tip"><span class="t">Scaffold + BottomBar</span>
탭 전환은 최상위 <code>Scaffold(bottomBar = { DsBottomBar(...) })</code>에서 처리하고, <code>GamesScreen</code>은 그 안에 놓습니다. Navigation은 Step 9에서 4탭을 연결합니다.
</div>

## 4. 라이브 폴링 — 화면이 보일 때만

`GET /sport/baseball/events/live` 한 번이 진행 중인 KBO 전 경기를 줍니다. **`STARTED`** 에서만 20초 간격.

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

화면에서 `LivePolling(vm, ui.games.any { it.status == GameStatus.LIVE })`.

<div class="callout warn"><span class="t">홈으로 나가면 멈춰야 한다</span>
<code>repeatOnLifecycle(STARTED)</code>가 백그라운드 진입 시 코루틴을 취소합니다. 안 쓰면 배터리·트래픽이 새고 차단 위험이 커집니다(§7).
</div>

## 5. 즐겨찾는 구단 상단 고정

Step 8에서 만들 즐겨찾기와 연결됩니다. Repository의 `observeByDate`를 즐겨찾기 Set과 `combine`해
정렬 키를 얹으면, 목업처럼 즐겨찾는 구단 경기가 위로 올라옵니다.

## 6. 실행 확인

<div class="checkpoint"><span class="t"></span> 목업의 홈 화면(진행 중·예정·종료·연기 섹션, 원정 먼저, 라이브 빨강)이 그대로 뜨고, 날짜 화살표로 과거/미래가 즉시(네트워크 없이) 바뀌면 성공. 경기일이면 30분 켜두고 자동 갱신 + 홈 복귀 시 폴링 정지/재개를 확인하세요.</div>

<div class="pager">
<a href="#/labs/step-5">← Step 5</a>
<a href="#/labs/step-7">Step 7 · 경기 상세 →</a>
</div>
