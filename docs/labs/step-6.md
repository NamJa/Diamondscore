# Step 6 · 경기 목록 화면

<div class="chips"><span class="chip time">90분</span><span class="chip diff">보통</span><span class="chip goal">Step 5 컴포넌트를 조립해 날짜별 목록 + 라이브 갱신을 완성한다</span></div>

첫 화면입니다. Step 5에서 만든 `GameCard`·`DsBottomBar`·상태 컴포넌트를 조립하고, 날짜 네비게이션과
**요청 1개짜리 라이브 폴링**을 붙입니다. 목업의 홈 화면을 만듭니다.

## 1. UiState와 ViewModel

`feature/games/GamesViewModel.kt` (신선도 enum은 `domain/model`에 두어도 됩니다):

```kotlin
enum class Freshness { FRESH, OFFLINE }

data class GamesUiState(
    val date: LocalDate = LocalDate.now(SEOUL),
    val games: List<GameSummary> = emptyList(),
    val loading: Boolean = true,
    val freshness: Freshness = Freshness.FRESH,
    val lastUpdatedText: String? = null,          // "마지막 갱신 10분 전"
    val error: Boolean = false,
)

@HiltViewModel
class GamesViewModel @Inject constructor(
    private val repo: GamesRepository,
    private val savedState: SavedStateHandle,
) : ViewModel() {
    /** 갱신 시도의 결과. 이게 없으면 오프라인 배너도 오류 화면도 영원히 뜨지 않는다. */
    private data class Sync(
        val lastOk: Instant? = null,
        val lastTry: Instant? = null,   // 실패가 이어져도 매번 값이 달라져야 "n분 전"이 다시 계산된다
        val failed: Boolean = false,
        val busy: Boolean = false,
    )

    // 선택 날짜는 nav 인자가 아니라 화면 상태다 → SavedStateHandle로 프로세스 재생성까지만 보존
    private val date = MutableStateFlow(
        savedState.get<String>(KEY_DATE)?.let(LocalDate::parse) ?: LocalDate.now(SEOUL))
    private val sync = MutableStateFlow(Sync())

    @OptIn(ExperimentalCoroutinesApi::class)                      // flatMapLatest — 없으면 opt-in 경고
    val ui: StateFlow<GamesUiState> = combine(
        date.flatMapLatest { d -> repo.observeByDate(d).map { d to it } },
        sync,
    ) { (d, games), s ->
        GamesUiState(
            date = d,
            games = games,
            loading = s.busy && games.isEmpty(),
            freshness = if (s.failed) Freshness.OFFLINE else Freshness.FRESH,
            lastUpdatedText = s.lastOk?.let(::agoText),
            error = s.failed && games.isEmpty(),   // 캐시가 있으면 오류 화면 대신 배너 (목업 "오프라인(캐시)")
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), GamesUiState())

    fun move(days: Long) = setDate(date.value.plusDays(days))
    fun today() = setDate(LocalDate.now(SEOUL))
    fun refreshDay() = viewModelScope.launch { refreshNow() }        // 보고 있는 날짜 1회
    fun goNearest() = viewModelScope.launch { repo.nearestGameDay(date.value)?.let(::setDate) }

    /** 폴링 루프·재시도 버튼이 함께 쓰는 suspend 버전. 앞 요청이 안 끝났으면 건너뛴다(single-flight). */
    suspend fun refreshNow() {
        if (sync.value.busy) return
        sync.update { it.copy(busy = true) }
        val ok = runCatching { repo.refreshDay(date.value) }.isSuccess
        val now = Instant.now()
        sync.update { it.copy(busy = false, failed = !ok, lastTry = now, lastOk = if (ok) now else it.lastOk) }
    }

    private fun setDate(d: LocalDate) {
        date.value = d
        savedState[KEY_DATE] = d.toString()      // 읽기만 하고 안 쓰면 보존이 안 된다
    }

    private fun agoText(t: Instant): String =
        Duration.between(t, Instant.now()).toMinutes().let {
            if (it < 1) "마지막 갱신 방금 전" else "마지막 갱신 ${it}분 전"
        }

    private companion object { const val KEY_DATE = "date" }
}
```

<div class="callout tip"><span class="t">"가장 가까운 경기일로" 한 줄 짜리 조회</span>
<code>goNearest()</code>는 Step 4 §4의 <code>GamesRepository.nearestGameDay</code>를 그대로 호출합니다 — 쿼리(<code>GameDao.nearestAfter</code>)도 <code>FakeGameDao</code>의 override도 리포지터리의 한 줄도 Step 4에 이미 있으므로 여기서 추가할 것은 없습니다. 시즌 프리페치가 이미 3~11월 일정을 Room에 넣어 뒀으므로 네트워크도 필요 없습니다.
</div>

<div class="callout warn"><span class="t">상태를 안 쓰면 상태 화면도 안 뜬다</span>
<code>runCatching { … }</code>로 예외를 <strong>삼키기만</strong> 하면 <code>freshness</code>·<code>error</code>는 영원히 기본값이고, Step 5에서 만든 <code>ErrorState</code>·<code>StaleBanner</code>는 앱에서 한 번도 렌더링되지 않습니다. 위처럼 실패를 <code>sync</code>에 적어 두는 것이 목업의 "오류"·"오프라인(캐시)" 두 화면을 살리는 유일한 배선입니다. 마지막 성공 시각은 프로세스가 죽으면 사라집니다 — 재시작 후에도 남기려면 계획서 §6의 <code>SyncMetaEntity(lastSuccessAt)</code>가 필요하고, 그건 이 튜토리얼 범위 밖입니다.
</div>

<div class="callout tip"><span class="t">Navigation 3에서 인자는 <code>SavedStateHandle</code>로 오지 않는다</span>
경기 목록은 탭 루트라 인자가 없습니다. 하지만 인자가 있는 화면(Step 7·8)은 다릅니다 — Nav3는 <code>Bundle</code>이 아니라 <strong>타입 있는 키 객체</strong>를 넘기므로 <code>savedState["eventId"]</code> 같은 코드는 <code>null</code>을 받습니다. 인자는 <code>@AssistedInject</code>로 키를 직접 주입해서 받습니다(Step 7). <code>SavedStateHandle</code>은 위처럼 <strong>화면이 스스로 만든 상태</strong>를 프로세스 재생성까지 살리는 용도로만 남습니다.
</div>

## 2. 날짜 바 (DateBar)

계획서 §1.3의 날짜 네비게이션(이전·다음·오늘)을 목업 상태 화면의 `‹ 9월 14일 월 ›` 형태로 만듭니다.
홈 아트보드의 5일 스트립과는 다릅니다 — 정본은 계획서 §1.3이고, 스트립이나 날짜 선택기로 바꾸고 싶으면 이 컴포저블만 갈아 끼우면 됩니다.

`feature/games/DateBar.kt`:

```kotlin
@Composable
fun DateBar(date: LocalDate, onPrev: () -> Unit, onNext: () -> Unit, onToday: () -> Unit) {
    val isToday = date == LocalDate.now(SEOUL)
    Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp)) {
            IconButton(onClick = onPrev) { DsIcon(Icons.Outlined.ChevronLeft, contentDescription = "이전 날짜") }
            Text(date.format(dateFmt), style = MaterialTheme.typography.titleMedium)  // 8월 2일 토
            IconButton(onClick = onNext) { DsIcon(Icons.Outlined.ChevronRight, contentDescription = "다음 날짜") }
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
fun GamesScreen(
    onGame: (Long) -> Unit,
    onSettings: () -> Unit = {},        // Step 9 §1의 entry<GamesKey>에서 SettingsKey로 연결
) {
    val vm: GamesViewModel = hiltViewModel()   // androidx.hilt.lifecycle.viewmodel.compose
    val ui by vm.ui.collectAsStateWithLifecycle()
    // 오늘이면 진입 시 1회 — 프리페치된 일정 위에 최신 상태(취소·선발 변경)를 덮는다
    LaunchedEffect(ui.date) { if (ui.date == LocalDate.now(SEOUL)) vm.refreshNow() }
    // 시작 시각이 지난 예정 경기도 폴링한다 — LIVE만 보면 경기 전에 열어 둔 목록은 "예정"에 머문다(§4)
    val now = rememberMinuteClock()
    val pollable = ui.games.any { it.status == GameStatus.LIVE || (it.status == GameStatus.SCHEDULED && !it.startsAt.isAfter(now)) }
    LivePolling(                                        // §4 — Step 9에서 간격을 설정값으로 바꿔 끼운다
        hasLive = pollable,
        onTick = { vm.refreshNow() },
    )
    Column(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        TopBar("경기", trailing = {                      // 목업 헤더 우측: 설정 톱니
            IconButton(onClick = onSettings) { DsIcon(Icons.Outlined.Settings, contentDescription = "설정", size = 22.dp) }
        })
        DateBar(ui.date, onPrev = { vm.move(-1) }, onNext = { vm.move(1) }, onToday = vm::today)
        // 껐다 켠 직후엔 성공 시각이 없다 → 그래도 캐시를 보고 있다는 사실은 알려준다
        if (ui.freshness == Freshness.OFFLINE) StaleBanner(ui.lastUpdatedText ?: "캐시 표시 중")

        when {
            ui.loading            -> LoadingCards()
            ui.error              -> ErrorState(onRetry = vm::refreshDay)
            ui.games.isEmpty()    -> EmptyDay(onNearest = vm::goNearest)
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
리스트에 <code>spacedBy</code>를 주지 않습니다. <strong>라이브 히어로 카드</strong>는 자체 여백을, <strong>라인 로우</strong>는 자체 상단 헤어라인(Step 5 §2 <code>GameRow</code>)을 그리므로, 로우들은 카드 간격 없이 <strong>연속</strong>돼야 에디토리얼 느낌이 삽니다. 히어로에 상하 여백이 필요하면 <code>LiveHeroCard</code> 루트에 <code>Modifier.padding(vertical = 6.dp)</code>를 넣으세요.
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

`GET /live/Schedule_Day/{오늘}` 한 번이 그날 KBO 전 경기(최대 5)의 상태·이닝·점수를 줍니다. 응답은 5KB 안팎입니다. **`STARTED`** 에서만 20초 간격(공식 앱은 4초지만 그렇게까지 칠 이유가 없습니다).

`core/ui/LivePolling.kt` — 도메인을 모르는 조각이고 §3의 `GamesScreen`과 Step 7의 `GameDetailScreen`이 함께 쓰므로 `core/ui`에 둡니다. `feature/games`에 두면 Step 7이 feature를 가로질러 import하게 되어 Step 9 §8의 완료 조건(`feature` 안에 `import com.diamondscore.feature` 0건)이 깨집니다:

```kotlin
package com.diamondscore.core.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.produceState
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.repeatOnLifecycle
import java.time.Instant
import kotlin.random.Random
import kotlinx.coroutines.delay

@Composable
fun LivePolling(hasLive: Boolean, intervalMs: Long = 20_000L, onTick: suspend () -> Unit) {
    val owner = LocalLifecycleOwner.current
    LaunchedEffect(hasLive, intervalMs) {
        if (!hasLive) return@LaunchedEffect
        owner.repeatOnLifecycle(Lifecycle.State.STARTED) {
            while (true) {
                onTick()                                        // suspend — 앞 요청이 끝난 뒤에 다음 대기가 시작된다
                delay(intervalMs + Random.nextLong(-intervalMs / 10, intervalMs / 10))   // jitter ±10%
            }
        }
    }
}

/** 1분마다 바뀌는 현재 시각 — "시작 시각이 지난 예정 경기"도 폴링 대상으로 보려고 목록·상세가 쓴다. */
@Composable
fun rememberMinuteClock(): Instant =
    produceState(Instant.now()) { while (true) { delay(60_000); value = Instant.now() } }.value
```

`vm`이 아니라 `onTick`을 받는 이유는 Step 9에서 설정값(20초/30초/1분)을 `intervalMs`로 내려보내기 위해서입니다.
§3의 `GamesScreen`에서는 `import com.diamondscore.core.ui.LivePolling`·`rememberMinuteClock`이 필요합니다.
목록 응답에는 이닝별 득점이 없으므로 상세 화면은 따로 폴링합니다(Step 7).

<div class="callout warn"><span class="t">LIVE만 조건으로 두면 경기 전에 열어 둔 목록은 영영 "예정"이다</span>
폴링은 Room에 이미 LIVE 행이 있을 때만 돌고, 진입 시 갱신(<code>LaunchedEffect(ui.date)</code>)은 한 번뿐입니다. 그래서 18:21에 연 목록은 18:38에 서버가 이미 3경기 모두 <code>state:"i"</code>였는데도 요청 0건으로 "예정"에 머물렀고, 홈에 나갔다 돌아와도 그대로였습니다(2026-09-23 실측 — 날짜를 바꿨다 돌아와야 LIVE가 떴습니다). §3처럼 <strong>시작 시각이 지난 예정 경기</strong>도 폴링 대상에 넣고, 그 시각이 지나는 순간을 알려고 1분마다 바뀌는 <code>rememberMinuteClock()</code>을 씁니다. 우천 지연처럼 시작이 늦어져도 LIVE·취소가 될 때까지 폴링이 이어집니다. 폴링 자체는 여전히 <code>LivePolling</code>이 <code>STARTED</code>에서만 돌립니다.
</div>

<div class="callout tip"><span class="t">여기까지가 튜토리얼 범위</span>
계획서 §7.2의 <code>LivePoller</code>는 <strong>적응형 간격</strong>(라이브가 뜸하면 1.5배, 최대 40초)과 <strong>실패 시 backoff</strong>(2배, 최대 2분)까지 가집니다. 이 랩은 그중 <strong>요청 1개 · 20초 · jitter · <code>STARTED</code>에서만</strong>(계획서 §10의 차단 완화책 4종)과 single-flight(<code>refreshNow</code>의 <code>busy</code> 가드)만 구현합니다. 나머지 둘은 별도 클래스가 필요해 범위 밖입니다.
</div>

<div class="callout warn"><span class="t">홈으로 나가면 멈춰야 한다</span>
<code>repeatOnLifecycle(STARTED)</code>가 백그라운드 진입 시 코루틴을 취소합니다. 안 쓰면 배터리·트래픽이 새고 차단 위험이 커집니다(§7).
</div>

## 5. 즐겨찾는 구단 상단 고정

Step 8에서 `FavoritesRepository`를 만든 뒤 이 화면으로 돌아와 세 줄을 고칩니다 — 그때까지는 이 절을 건너뜁니다.

```kotlin
// 1) 생성자에 추가:  private val favorites: FavoritesRepository,
// 2) combine 인자에 추가:  favorites.observeTeams(),   → 람다는 { (d, games), favs, s -> }
// 3) GamesUiState(games = …) 를 아래처럼:  sectioned()의 filter가 순서를 보존하므로 섹션 구조는 그대로다
games = games.sortedByDescending { it.home.id in favs || it.away.id in favs },
```

## 6. 실행 확인

`Scaffold`·`NavDisplay`는 Step 9에서 붙입니다. 그때까지는 `MainActivity`에 이 화면 하나만 임시로
연결해 두고 Step 7·8도 같은 자리에서 바꿔 끼우며 확인합니다(완전한 코드). 임시 화면이라 상태바 inset을 처리하지 않으므로
제목(`경기.`)이 상태바 바로 밑에 붙어 보이는 건 정상입니다 — Step 9의 `Scaffold`가 inset을 줍니다.

```kotlin
package com.diamondscore

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.diamondscore.core.designsystem.DiamondScoreTheme
import com.diamondscore.feature.games.GamesScreen
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint                      // 없으면 hiltViewModel()이 실행 시 크래시한다
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            DiamondScoreTheme {
                GamesScreen(onGame = {})     // Step 9에서 DiamondScoreApp()으로 교체
            }
        }
    }
}
```

<div class="checkpoint"><span class="t"></span> 홈 화면(진행 중·예정·종료·연기 섹션, 원정 먼저, 라이브 빨강)이 뜨고, 날짜 화살표로 과거/미래가 즉시(네트워크 없이) 바뀌면 성공. 비행기 모드는 두 경우를 나눠 보세요 — 앱을 <strong>켜 둔 채</strong> 비행기 모드로 바꾸면 <strong>갱신 시도가 있을 때</strong> 캐시 위에 "마지막 갱신 n분 전" 배너가 뜹니다. 라이브 경기가 없으면 폴링이 없어 바꾸기만 해서는 30초가 지나도 배너가 안 뜨므로(2026-09-23 실측), ‹로 전날에 갔다가 "오늘"을 눌러 갱신을 일으킵니다(라이브 폴링 중이면 20초 안에 뜹니다). 앱을 <strong>껐다 켠 뒤</strong> 비행기 모드로 들어가면 <code>lastOk</code>가 프로세스 메모리에만 있어 사라지므로 같은 자리에 "캐시 표시 중"이 떠야 합니다(§1 warn 콜아웃). 캐시가 없는 날이면 둘 다 "다시 시도"입니다. 경기일이면 <strong>첫 경기 시작 전에</strong> 열어 두고 시작 시각이 지나면 스스로 LIVE로 바뀌는지, 30분 동안 자동 갱신되는지(목록 폴링 간격 18~22초), 홈 복귀 시 폴링이 멈췄다 돌아오면 즉시 재개되는지 확인하세요.</div>

<!-- appendix:compose-api -->
## 별첨 · Compose API 사용 목적

이 Step은 첫 화면(경기 목록)과 **라이브 폴링**을 붙입니다. 사이드 이펙트·상태 수집 API가 여기서 처음 나옵니다.

**액티비티·ViewModel 연결**

| API | 이 Step에서의 사용 목적 |
|---|---|
| `setContent { … }` (activity-compose) | `MainActivity`에서 Compose 트리의 루트를 `DiamondScoreTheme { GamesScreen(…) }`로 연다 |
| `hiltViewModel()` (hilt-lifecycle-viewmodel-compose) | `GamesScreen`이 Hilt가 주입한 `GamesViewModel`을 받는다(Repository만 주입 — 규칙 1) |
| `collectAsStateWithLifecycle()` (lifecycle-compose) | `StateFlow<GamesUiState>`를 Compose `State`로 바꾼다. 화면이 `STARTED` 밖이면 수집을 멈춰, `WhileSubscribed(5000)`과 함께 Room 구독도 쉬게 한다 |
| `by` (`State` 위임) | `val ui by …`로 `.value` 없이 상태를 읽는다 |

**사이드 이펙트·상태 생산**

| API | 이 Step에서의 사용 목적 |
|---|---|
| `LaunchedEffect(ui.date)` | 진입 시와 날짜가 바뀔 때마다 실행되어, 오늘이면 1회 `refreshNow()` — 프리페치 일정 위에 최신 상태를 덮는다 |
| `LaunchedEffect(hasLive, intervalMs)` | `LivePolling` 안에서 폴링 코루틴을 띄운다. 키가 바뀌면(라이브 없음 → 있음) 기존 루프를 취소하고 다시 시작한다 |
| `LocalLifecycleOwner.current` + `repeatOnLifecycle(STARTED)` | 폴링 루프를 화면이 보일 때만 돌리고, 홈으로 나가면 멈췄다가 돌아오면 즉시 재개한다 |
| `produceState(initial) { … }` | `rememberMinuteClock()` — 1분마다 현재 시각을 `State`로 내보내, 시작 시각이 지난 예정 경기를 폴링 대상으로 편입시킨다 |

**레이아웃·컴포넌트**

| API | 이 Step에서의 사용 목적 |
|---|---|
| `LazyColumn(contentPadding = PaddingValues(…))` | 경기 목록을 필요한 만큼만 그리는 세로 리스트 |
| `item { }` / `items(list, key = { it.id })` | 섹션 라벨(진행 중/예정/종료)은 `item`, 경기 카드는 `items`. `key`로 폴링 갱신 때 카드가 재사용·재배치된다 |
| `IconButton` | 날짜 ‹ ›, 설정 톱니 — 아이콘만 있는 버튼이라 `contentDescription`을 넘긴다 |
| `TextButton` | 오늘이 아닐 때만 보이는 "오늘" 버튼 |
| `Text` / `Row` / `Column` / `Modifier.background` | 날짜 바 구성, 화면 배경을 `colorScheme.background`로 칠한다(Scaffold는 Step 9에서) |
| `MaterialTheme.typography.titleMedium` | 날짜 바의 "8월 2일 토" 스타일 |

<div class="pager">
<a href="#/labs/step-5">← Step 5</a>
<a href="#/labs/step-7">Step 7 · 경기 상세 →</a>
</div>
