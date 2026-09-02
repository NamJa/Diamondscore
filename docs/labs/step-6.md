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
    private val savedState: SavedStateHandle,
) : ViewModel() {
    // 선택 날짜는 nav 인자가 아니라 화면 상태다 → SavedStateHandle로 프로세스 재생성까지만 보존
    private val date = MutableStateFlow(
        savedState.get<String>(KEY_DATE)?.let(LocalDate::parse) ?: LocalDate.now(SEOUL))

    val ui: StateFlow<GamesUiState> = date
        .flatMapLatest { d -> repo.observeByDate(d).map { d to it } }
        .map { (d, games) -> GamesUiState(date = d, games = games, loading = false) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), GamesUiState())

    fun move(days: Long) = setDate(date.value.plusDays(days))
    fun today() = setDate(LocalDate.now(SEOUL))
    fun refreshLive() = viewModelScope.launch { runCatching { repo.refreshLive() } }

    private fun setDate(d: LocalDate) {
        date.value = d
        savedState[KEY_DATE] = d.toString()      // 읽기만 하고 안 쓰면 보존이 안 된다
    }

    private companion object { const val KEY_DATE = "date" }
}
```

<div class="callout tip"><span class="t">Navigation 3에서 인자는 <code>SavedStateHandle</code>로 오지 않는다</span>
경기 목록은 탭 루트라 인자가 없습니다. 하지만 인자가 있는 화면(Step 7·8)은 다릅니다 — Nav3는 <code>Bundle</code>이 아니라 <strong>타입 있는 키 객체</strong>를 넘기므로 <code>savedState["eventId"]</code> 같은 코드는 <code>null</code>을 받습니다. 인자는 <code>@AssistedInject</code>로 키를 직접 주입해서 받습니다(Step 7). <code>SavedStateHandle</code>은 위처럼 <strong>화면이 스스로 만든 상태</strong>를 프로세스 재생성까지 살리는 용도로만 남습니다.
</div>

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
fun GamesScreen(onGame: (Long) -> Unit) {
    val vm: GamesViewModel = hiltViewModel()   // androidx.hilt.lifecycle.viewmodel.compose
    val ui by vm.ui.collectAsStateWithLifecycle()
    Column(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        TopBar(title = "경기", subtitle = "KBO 2026")
        DateBar(ui.date, onPrev = { vm.move(-1) }, onNext = { vm.move(1) }, onToday = vm::today)
        if (ui.freshness == Freshness.OFFLINE) StaleBanner("마지막 갱신 10분 전")

        when {
            ui.loading            -> LoadingCards()
            ui.error              -> ErrorState(onRetry = vm::refreshLive)
            ui.games.isEmpty()    -> EmptyDay(onNearest = { /* 가장 가까운 경기일 */ })
            else -> LazyColumn(contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp)) {
                sectioned(ui.games).forEach { (title, items) ->
                    item { SectionLabel(title) }                       // 진행 중 / 예정 / 종료
                    items(items, key = { it.id }) { GameCard(it) { onGame(it.id) } }
                }
            }
        }
    }
}
```

<div class="callout tip"><span class="t">간격: 히어로 vs 라인 로우</span>
리스트에 <code>spacedBy</code>를 주지 않습니다. <strong>라이브 히어로 카드</strong>는 자체 여백을, <strong>라인 로우</strong>는 자체 상단 헤어라인(§Step 5 <code>GameRow</code>)을 그리므로, 로우들은 카드 간격 없이 <strong>연속</strong>돼야 에디토리얼 느낌이 삽니다. 히어로에 상하 여백이 필요하면 <code>LiveHeroCard</code> 루트에 <code>Modifier.padding(vertical = 6.dp)</code>를 넣으세요.
</div>

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
탭 전환은 최상위 <code>Scaffold(bottomBar = { DsBottomBar(...) })</code>에서 처리하고, <code>GamesScreen</code>은 그 안에 놓습니다. 탭별 back stack과 <code>NavDisplay</code> 연결은 Step 9입니다.
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
