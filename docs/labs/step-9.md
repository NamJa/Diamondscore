# Step 9 · 마감 — 설정·적응형·성능·릴리스

<div class="chips"><span class="chip time">90분</span><span class="chip diff">보통</span><span class="chip goal">설정 화면·탭 연결·적응형·성능을 마치고 R8 릴리스를 검증한다</span></div>

기능을 마무리합니다. 목업의 설정 화면을 만들고, 4탭을 연결하고, 태블릿 2-pane까지 붙인 뒤 릴리스 빌드를 확인합니다.

## 1. 4탭 연결 (Navigation 3)

Navigation 3는 **back stack이 그냥 관찰 가능한 리스트**입니다. `NavController`도, route 문자열도,
`NavGraph`도 없습니다 — 키를 `add`하면 앞으로 가고 `removeLastOrNull()`하면 뒤로 갑니다. 화면 목록은
`entryProvider`가 키 → Composable로 매핑합니다.

키는 Step 2의 `core/navigation/DsNavKeys.kt`에 이미 있습니다. 탭 4개는 각자 back stack을 갖습니다.

`app/src/main/java/com/diamondscore/DiamondScoreApp.kt`:

```kotlin
package com.diamondscore

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.navigation3.rememberViewModelStoreNavEntryDecorator
import androidx.navigation3.runtime.NavBackStack
import androidx.navigation3.runtime.NavEntry
import androidx.navigation3.runtime.NavKey
import androidx.navigation3.runtime.entryProvider
import androidx.navigation3.runtime.rememberDecoratedNavEntries
import androidx.navigation3.runtime.rememberNavBackStack
import androidx.navigation3.runtime.rememberSaveableStateHolderNavEntryDecorator
import androidx.navigation3.ui.NavDisplay
import com.diamondscore.core.navigation.*
import com.diamondscore.core.ui.DsBottomBar
import com.diamondscore.core.ui.DsTab
import com.diamondscore.feature.favorites.FavoritesScreen
import com.diamondscore.feature.gamedetail.GameDetailScreen
import com.diamondscore.feature.games.GamesScreen
import com.diamondscore.feature.players.PlayerDetailScreen
import com.diamondscore.feature.settings.SettingsScreen
import com.diamondscore.feature.standings.StandingsScreen
import com.diamondscore.feature.teams.TeamDetailScreen
import com.diamondscore.feature.teams.TeamRosterScreen
import com.diamondscore.feature.teams.TeamsScreen

private val DsTab.root: NavKey
    get() = when (this) {
        DsTab.GAMES -> GamesKey
        DsTab.STANDINGS -> StandingsKey
        DsTab.TEAMS -> TeamsKey
        DsTab.FAVORITES -> FavoritesKey
    }

/**
 * 키 → 화면. `stack`을 인자로 받는 게 핵심이다 — 탭마다 back stack이 다르므로
 * 각 탭의 화면은 자기 stack에 push해야 한다.
 */
private fun dsEntryProvider(stack: NavBackStack<NavKey>): (NavKey) -> NavEntry<NavKey> =
    entryProvider {
        entry<GamesKey> {
            GamesScreen(
                onGame = { id -> stack.add(GameDetailKey(id)) },
                onSettings = { stack.add(SettingsKey) },      // 목록 헤더 톱니(Step 6 §3)
            )
        }
        entry<StandingsKey> {
            StandingsScreen(onTeam = { id -> stack.add(TeamDetailKey(id)) })
        }
        entry<TeamsKey> {
            TeamsScreen(onTeam = { id -> stack.add(TeamDetailKey(id)) })
        }
        entry<FavoritesKey> {
            FavoritesScreen(
                onTeam = { id -> stack.add(TeamDetailKey(id)) },
                onSettings = { stack.add(SettingsKey) },
            )
        }
        entry<GameDetailKey> { key ->
            GameDetailScreen(key, onBack = { stack.removeLastOrNull() })
        }
        entry<TeamDetailKey> { key ->
            TeamDetailScreen(
                key,
                onGame = { id -> stack.add(GameDetailKey(id)) },
                onRoster = { id -> stack.add(TeamRosterKey(id)) },
                onBack = { stack.removeLastOrNull() },
            )
        }
        entry<TeamRosterKey> { key ->
            TeamRosterScreen(
                key,
                onPlayer = { playerKey -> stack.add(playerKey) },   // 화면이 teamId까지 채워 넘긴다
                onBack = { stack.removeLastOrNull() },
            )
        }
        entry<PlayerDetailKey> { key ->
            PlayerDetailScreen(key, onBack = { stack.removeLastOrNull() })
        }
        entry<SettingsKey> {
            SettingsScreen(onBack = { stack.removeLastOrNull() })
        }
    }

@Composable
fun DiamondScoreApp() {
    var tab by rememberSaveable { mutableStateOf(DsTab.GAMES) }

    // 탭마다 back stack 하나. rememberNavBackStack이 직렬화해 프로세스 재생성까지 살린다.
    val backStacks = DsTab.entries.associateWith { rememberNavBackStack(it.root) }
    val current = backStacks.getValue(tab)

    // 4개 stack 전부를 매 컴포지션에서 decorate → 안 보이는 탭의 ViewModel·스크롤 위치도 살아 있다.
    val decorated = backStacks.mapValues { (_, stack) ->
        rememberDecoratedNavEntries(
            backStack = stack,
            entryDecorators = listOf(
                rememberSaveableStateHolderNavEntryDecorator(),
                rememberViewModelStoreNavEntryDecorator(),
            ),
            entryProvider = dsEntryProvider(stack),
        )
    }

    Scaffold(bottomBar = { DsBottomBar(tab) { tab = it } }) { pad ->
        NavDisplay(
            entries = decorated.getValue(tab),
            onBack = { current.removeLastOrNull() },
            modifier = Modifier.padding(pad),
        )
    }
}
```

<div class="callout danger"><span class="t">여기서 한 번은 틀립니다 — <code>entryProvider</code>는 stack별로 만든다</span>
<code>entryProvider</code>를 <code>DiamondScoreApp</code> 안에서 한 번만 만들고 "현재 탭 stack"을 클로저로 잡으면 조용히 깨집니다. <code>rememberDecoratedNavEntries</code>는 <strong>back stack 내용이 바뀔 때만</strong> 엔트리를 다시 만들기 때문에, 첫 컴포지션(경기 탭)에서 만들어진 순위·팀·즐겨찾기 엔트리가 <strong>경기 탭 stack</strong>을 잡은 채 남습니다. 그 상태로 순위 탭에서 팀을 누르면 팀 상세가 경기 탭에 쌓입니다. 위처럼 <code>stack</code>을 <strong>인자로 받는 함수</strong>로 만들면 애초에 잡을 수가 없습니다.
</div>

`MainActivity`는 `@AndroidEntryPoint`가 붙어 있어야 `hiltViewModel()`이 동작합니다. 테마는 여기서
정해집니다 — §2에서 만들 `SettingsStore`의 값을 Step 2 §10의 `DiamondScoreTheme(dark = …)`에 넘깁니다.

`app/src/main/java/com/diamondscore/MainActivity.kt` (완전한 코드) — `pollIntervalMs`·`LocalPollIntervalMs`·
`SettingsViewModel`·`SettingsState`는 §2에서 만드니, **§2를 먼저 만든 뒤 붙여넣으세요**:

```kotlin
package com.diamondscore

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.diamondscore.core.common.pollIntervalMs
import com.diamondscore.core.designsystem.DiamondScoreTheme
import com.diamondscore.core.ui.LocalPollIntervalMs
import com.diamondscore.feature.settings.SettingsViewModel
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val settings: SettingsViewModel = hiltViewModel()
            val s by settings.ui.collectAsStateWithLifecycle()
            // 폴링 간격은 값으로만 내려보낸다 — feature:games가 feature:settings를 모르게(§2)
            CompositionLocalProvider(LocalPollIntervalMs provides pollIntervalMs(s.interval)) {
                DiamondScoreTheme(
                    dark = when (s.theme) {           // 세그먼트 라벨 → Boolean
                        "라이트" -> false
                        "다크" -> true
                        else -> isSystemInDarkTheme()   // "시스템"
                    }
                ) { DiamondScoreApp() }
            }
        }
    }
}
```

<div class="callout warn"><span class="t">decorator 2개는 옵션이 아니다</span>
<code>NavDisplay</code>의 기본값은 <code>rememberSaveableStateHolderNavEntryDecorator()</code> 하나뿐입니다. 여기에 <strong><code>rememberViewModelStoreNavEntryDecorator()</code></strong>를 직접 추가해야:
<ul>
<li>화면마다(정확히는 <code>NavEntry.contentKey</code>마다) <strong>별개의 ViewModel</strong>이 생깁니다 — 경기 A 상세와 경기 B 상세가 ViewModel을 공유하지 않습니다.</li>
<li>back으로 pop되면 그 ViewModel이 <code>onCleared()</code>됩니다.</li>
</ul>
빼먹으면 <code>GameDetailViewModel</code> 하나가 재사용돼 다른 경기를 눌러도 이전 점수가 보입니다. 직접 목록을 넘길 때는 기본값도 함께 넣어야 한다는 점을 잊지 마세요.
</div>

<div class="callout tip"><span class="t">화면은 키를 모른 채로도 된다</span>
<code>GamesScreen(onGame = (Long) -&gt; Unit)</code>처럼 화면은 <strong>콜백</strong>만 노출하고, 콜백을 어떤 키로 바꿀지는 이 파일(<code>:app</code>)이 정합니다. 그래서 <code>feature:games</code>가 <code>feature:game-detail</code>을 몰라도 되고, 나중에 모듈을 쪼갤 때 feature끼리 의존이 생기지 않습니다. 인자를 받는 화면만 키 타입을 파라미터로 받습니다(Step 7·8).
</div>

<div class="callout tip"><span class="t">Nav2에서 옮겨온다면</span>
<code>NavHost</code>·<code>NavController</code>·<code>composable("game/{eventId}")</code>·<code>navArgument</code>·<code>NavType.LongType</code>·<code>popBackStack()</code>이 전부 사라집니다. 대응은 <code>NavDisplay</code>·<code>NavBackStack</code>(그냥 리스트)·<code>entry&lt;GameDetailKey&gt;</code>·<code>removeLastOrNull()</code>입니다. <code>androidx.navigation:navigation-compose</code> 의존성도 넣지 않습니다 — 예전에는 <code>hilt-navigation-compose</code>가 이걸 transitive로 끌어왔는데, 우리는 <code>hilt-lifecycle-viewmodel-compose</code>를 쓰므로 그 경로도 없습니다.
</div>

### 뒤로 가기 — 그대로 두면 맞다

`NavDisplay`는 back stack에 항목이 2개 이상일 때만 back을 가로챕니다(내부적으로
`isBackEnabled = scene.previousEntries.isNotEmpty()`). 탭 루트에서는 back을 시스템에 넘기므로
`onBack`이 아예 호출되지 않고, 앱이 정상 종료됩니다 — **빈 back stack을 방어하는 코드가 필요 없습니다.**
predictive back(뒤로 밀기 미리보기)도 `NavDisplay`가 기본으로 붙여 줍니다.

바꾸고 싶은 건 하나뿐입니다: 순위 탭 루트에서 back을 누르면 경기 탭으로 돌아가는 "홈으로 나간다"
패턴을 원한다면 `onBack`이 아니라 **탭 상태**를 다뤄야 합니다.

```kotlin
// 선택 사항. 원하지 않으면 이 블록을 넣지 마세요 — 기본 동작(앱 종료)도 정상입니다.
BackHandler(enabled = current.size == 1 && tab != DsTab.GAMES) { tab = DsTab.GAMES }
```

## 2. 설정 화면

목업: 테마 세그먼트(시스템/라이트/다크), 라이브 갱신 간격(20초/30초/1분), 알림(P1·비활성), 데이터 출처, 라이선스, 버전.

`feature/settings/SettingsScreen.kt`:

```kotlin
@Composable
fun SettingsScreen(onBack: () -> Unit) {
    val vm: SettingsViewModel = hiltViewModel()
    val s by vm.ui.collectAsStateWithLifecycle()
    Column(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) { DsIcon(Icons.AutoMirrored.Outlined.ArrowBack) }
            TopBar("설정", accentDot = false)   // 설정 화면은 워드마크 마침표 없음(목업)
        }
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(26.dp)) {
            SettingGroup("테마") {
                DsSegmented(listOf("시스템","라이트","다크"), selected = s.theme, onSelect = vm::setTheme)
            }
            SettingGroup("라이브 갱신 간격") {
                DsSegmented(listOf("20초","30초","1분"), selected = s.interval, onSelect = vm::setInterval)
                Caption("화면을 보고 있을 때만 갱신돼요. 홈으로 나가면 멈춥니다.")
            }
            SettingGroup("알림") {
                SettingSwitch("경기 시작·득점 알림", checked = false, enabled = false, hint = "준비 중")
            }
            SettingGroup("정보") {
                SettingRow("데이터 출처", "wisetoto (프로야구 LIVE) · 개인 용도")
                SettingLink("개인정보 처리방침"); SettingLink("오픈소스 라이선스")
                SettingRow("앱 버전", "0.1.0")
            }
        }
    }
}
```

설정 값은 DataStore에 저장합니다. 값 자체는 화면과 데이터 양쪽이 쓰는 도메인 모델이라
`domain/model/Settings.kt`에 두고, 읽기·쓰기는 `data/repository/SettingsStore.kt`가 맡습니다
(`datastore-preferences`는 Step 2 §4에 이미 들어 있으니 의존성은 추가하지 않습니다).

```kotlin
package com.diamondscore.domain.model

/** 설정 값. 세그먼트 라벨을 그대로 저장한다("시스템"·"라이트"·"다크" / "20초"·"30초"·"1분"). */
data class SettingsState(val theme: String = "다크", val interval: String = "20초")
```

`data/repository/SettingsStore.kt` (완전한 코드):

```kotlin
package com.diamondscore.data.repository

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.diamondscore.domain.model.SettingsState
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

// 델리게이트는 파일 최상단에 한 번만. 두 번 선언하면 같은 파일을 두 인스턴스가 열어 런타임에 터진다.
private val Context.dataStore by preferencesDataStore("settings")

/** `@Inject` 생성자라 Hilt가 바인딩을 알아서 만든다 — `@Provides` 모듈이 따로 필요 없다. */
@Singleton
class SettingsStore @Inject constructor(@ApplicationContext private val ctx: Context) {
    private val THEME = stringPreferencesKey("theme")
    private val INTERVAL = stringPreferencesKey("interval")

    val state: Flow<SettingsState> = ctx.dataStore.data.map { p ->
        SettingsState(p[THEME] ?: "다크", p[INTERVAL] ?: "20초")
    }

    suspend fun setTheme(v: String) { ctx.dataStore.edit { it[THEME] = v } }
    suspend fun setInterval(v: String) { ctx.dataStore.edit { it[INTERVAL] = v } }
}
```

**ViewModel · 설정 헬퍼** (생략 없는 구현 — 같은 파일 `feature/settings/SettingsScreen.kt`에 이어 붙입니다) — `Caption`·`DsIcon`은 Step 5 §6.

```kotlin
@HiltViewModel
class SettingsViewModel @Inject constructor(private val store: SettingsStore) : ViewModel() {
    val ui = store.state.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), SettingsState())
    fun setTheme(v: String) = viewModelScope.launch { store.setTheme(v) }
    fun setInterval(v: String) = viewModelScope.launch { store.setInterval(v) }
}
// SettingsStore는 위 data/repository/SettingsStore.kt. @Inject 생성자라 그대로 주입된다.

@Composable
fun SettingGroup(title: String, content: @Composable ColumnScope.() -> Unit) = Column {
    Text(title, Modifier.padding(bottom = 10.dp),                       // 목업 섹션 헤더 = Bebas 15 / .14em
        style = Display.copy(fontSize = 15.sp, letterSpacing = 0.14.em), color = DsColors.muted2)
    content()
}

@Composable
fun DsSegmented(options: List<String>, selected: String, onSelect: (String) -> Unit) = Row(
    Modifier.fillMaxWidth().clip(RoundedCornerShape(11.dp))
        .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(11.dp))
        .background(MaterialTheme.colorScheme.surface).padding(4.dp),
    horizontalArrangement = Arrangement.spacedBy(4.dp)) {
    options.forEach { opt ->
        val on = opt == selected
        Box(Modifier.weight(1f).heightIn(min = 48.dp).clip(RoundedCornerShape(8.dp))   // 터치 48dp
            .background(if (on) MaterialTheme.colorScheme.primary else Color.Transparent)   // 액티브 = 레드
            .clickable { onSelect(opt) }.padding(vertical = 8.dp), Alignment.Center) {
            Text(opt, style = MaterialTheme.typography.bodyMedium,
                fontWeight = if (on) FontWeight.Bold else FontWeight.Normal,
                color = if (on) MaterialTheme.colorScheme.onPrimary else DsColors.muted2)
        }
    }
}

@Composable
fun SettingSwitch(title: String, checked: Boolean, enabled: Boolean = true, hint: String? = null) = Row(
    Modifier.fillMaxWidth().padding(vertical = 12.dp),
    verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
    Column {
        Text(title, style = MaterialTheme.typography.bodyLarge,
            color = if (enabled) MaterialTheme.colorScheme.onSurface else DsColors.muted2)
        hint?.let { Caption(it) }
    }
    Switch(checked = checked, onCheckedChange = null, enabled = enabled)
}

@Composable
fun SettingRow(key: String, value: String) = Row(
    Modifier.fillMaxWidth().padding(vertical = 15.dp), horizontalArrangement = Arrangement.SpaceBetween) {
    Text(key, style = MaterialTheme.typography.bodyLarge)
    Text(value, style = MaterialTheme.typography.bodyMedium, color = DsColors.muted2)
}

@Composable
fun SettingLink(label: String, onClick: () -> Unit = {}) = Row(
    Modifier.fillMaxWidth().clickable(onClick = onClick).padding(vertical = 15.dp),
    verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
    Text(label, style = MaterialTheme.typography.bodyLarge)
    DsIcon(Icons.Outlined.ChevronRight, size = 20.dp, tint = DsColors.muted2)
}
```

라이트 스킴(`DsLightColors`·`LightExtras`)은 Step 2 §6에, `DiamondScoreTheme(dark: Boolean)`의 분기는
Step 2 §10에 **이미 있습니다** — 여기서 더 정의할 것은 없고, 저장된 값을 `dark`로 넘기는 배선(§1의
`MainActivity`)이 전부입니다.

갱신 간격은 Step 6에서 `core/ui`에 만든 `LivePolling(hasLive, intervalMs, onTick)`(§4)으로 들어갑니다.
라벨을 밀리초로 바꾸는 함수 하나면 됩니다:

```kotlin
// core/common/PollInterval.kt — 라벨→ms 변환은 Compose를 모르는 순수 함수라 core/common에 둔다.
// 호출하는 곳은 §1의 MainActivity 한 곳이고, feature:games는 아래 LocalPollIntervalMs만 읽는다.
package com.diamondscore.core.common

/** 설정 라벨 → 폴링 간격(ms). 공식 앱(4초)보다 느린 값만 고를 수 있다. */
fun pollIntervalMs(interval: String): Long = when (interval) {
    "30초" -> 30_000L
    "1분" -> 60_000L
    else -> 20_000L          // "20초" = 기본값
}
```

값을 화면까지 내리는 길도 같은 규칙을 탑니다 — `GamesScreen`이 `SettingsViewModel`(`feature/settings`)을
직접 가져오면 §5.5를 어기므로, 설정을 아는 `:app`이 넣고 화면은 값만 읽습니다:

```kotlin
// core/ui/LocalPollInterval.kt
package com.diamondscore.core.ui

import androidx.compose.runtime.staticCompositionLocalOf

/** 폴링 간격(ms). §1의 MainActivity가 설정값을 넣는다. */
val LocalPollIntervalMs = staticCompositionLocalOf { 20_000L }
```

`GamesScreen`(Step 6 §3)의 폴링 호출부에 그대로 끼웁니다 — 설정을 바꾸면 다음 틱부터 간격이 달라집니다:

```kotlin
// LivePolling은 Step 6에서 core/ui에 만든 컴포저블 — GamesScreen도 GameDetailScreen도 여기서 가져온다
LivePolling(
    hasLive = ui.games.any { it.status == GameStatus.LIVE },
    intervalMs = LocalPollIntervalMs.current,          // core/ui
) { vm.refreshNow() }
```

## 3. 상태 화면 연결

Step 5에서 만든 `LoadingCards`·`EmptyDay`·`ErrorState`·`StaleBanner`가 모든 화면에서 로딩/빈/오류/
오프라인을 담당합니다. 각 화면의 `when(ui)` 분기가 목업의 상태 화면과 1:1로 맞는지 점검합니다.

## 4. 적응형 — 태블릿 2-pane

목업의 태블릿 화면: 목록 pane + 상세 pane. Nav3에서는 **화면을 다시 만들지 않습니다** — §1에서 만든
back stack 그대로 두고 `SceneStrategy`만 하나 끼웁니다. 창이 넓으면 두 pane, 좁으면 한 pane으로
`NavDisplay`가 알아서 갈라 놓습니다.

`nav3-adaptive`(`androidx.compose.material3.adaptive:adaptive-navigation3`)가 필요합니다.

```kotlin
import androidx.compose.material3.adaptive.ExperimentalMaterial3AdaptiveApi
import androidx.compose.material3.adaptive.navigation3.ListDetailSceneStrategy
import androidx.compose.material3.adaptive.navigation3.rememberListDetailSceneStrategy
```

`ExperimentalMaterial3AdaptiveApi`는 `@RequiresOptIn` level이 기본값(ERROR)이라 경고가 아니라
**컴파일 에러**입니다 — 아래 `dsEntryProvider`와 `DiamondScoreApp` **양쪽**에 `@OptIn`을 붙여야 빌드됩니다.
`DiamondScoreApp.kt` 최상단에 `@file:OptIn(ExperimentalMaterial3AdaptiveApi::class)` 한 줄을 두고
개별 `@OptIn`을 빼도 됩니다.

1. **어느 키가 어느 pane인지** `entry`의 `metadata`로 표시합니다 — §1의 `dsEntryProvider`에 인자만 추가:

```kotlin
@OptIn(ExperimentalMaterial3AdaptiveApi::class)                // listPane()·detailPane()
private fun dsEntryProvider(stack: NavBackStack<NavKey>): (NavKey) -> NavEntry<NavKey> =
    entryProvider {
        entry<GamesKey>(
            metadata = ListDetailSceneStrategy.listPane(
                detailPlaceholder = {                                     // 넓은 화면에서 오른쪽 pane
                    CenterColumn { Text("경기를 선택하세요", color = DsColors.muted2) }   // Step 5 §6
                },
            )
        ) {
            GamesScreen(
                onGame = { id -> stack.add(GameDetailKey(id)) },
                onSettings = { stack.add(SettingsKey) },      // 목록 헤더 톱니(Step 6 §3)
            )
        }
        entry<GameDetailKey>(metadata = ListDetailSceneStrategy.detailPane()) { key ->
            GameDetailScreen(key, onBack = { stack.removeLastOrNull() })
        }

        // 순위·팀 → 팀 상세도 같은 방식
        entry<StandingsKey>(metadata = ListDetailSceneStrategy.listPane()) { … }
        entry<TeamsKey>(metadata = ListDetailSceneStrategy.listPane()) { … }
        entry<TeamDetailKey>(metadata = ListDetailSceneStrategy.detailPane()) { key -> … }

        // 선수단은 팀 상세 안에서 다시 목록 → 선수 상세다. 그래서 키를 따로 둔 것(Step 2)
        entry<TeamRosterKey>(metadata = ListDetailSceneStrategy.listPane()) { key -> … }
        entry<PlayerDetailKey>(metadata = ListDetailSceneStrategy.detailPane()) { key -> … }

        // 설정·즐겨찾기는 pane 분할이 없으니 metadata 없이 그대로
        entry<FavoritesKey> { … }
        entry<SettingsKey> { … }
    }
```

2. **전략을 `NavDisplay`에 넘깁니다.** §1의 `DiamondScoreApp`에서 두 줄만 바뀝니다:

```kotlin
@OptIn(ExperimentalMaterial3AdaptiveApi::class)
@Composable
fun DiamondScoreApp() {
    // … tab / backStacks / current / decorated 는 §1과 동일 …
    val listDetail = rememberListDetailSceneStrategy<NavKey>()   // ← 추가

    Scaffold(bottomBar = { DsBottomBar(tab) { tab = it } }) { pad ->
        NavDisplay(
            entries = decorated.getValue(tab),
            onBack = { current.removeLastOrNull() },
            sceneStrategy = listDetail,          // ← 이 한 줄이 2-pane 전부
            modifier = Modifier.padding(pad),
        )
    }
}
```

<div class="callout tip"><span class="t"><code>sceneStrategy</code>는 단수</span>
<code>entries = …</code> 오버로드는 <code>sceneStrategy</code>(단수) 하나만 받습니다. 전략을 여러 개 겹치려면(예: 목록-상세 + 바텀시트) <code>backStack = …</code> 오버로드의 <code>sceneStrategies</code>(복수)를 써야 하는데, 그러면 탭별 back stack을 직접 decorate할 수 없습니다. 이 앱은 전략이 하나라 단수로 충분합니다.
</div>

<div class="callout tip"><span class="t">왜 코드가 이것뿐인가</span>
Nav2의 <code>NavigableListDetailPaneScaffold</code>는 별도 navigator와 별도 화면 트리를 요구해서, 폰용 그래프와 태블릿용 그래프가 사실상 두 벌이 됐습니다. Nav3의 <code>SceneStrategy</code>는 <strong>같은 back stack</strong>을 보고 "이 항목들을 한 화면에 같이 그릴 수 있나?"만 판단합니다. 그래서 목적지 정의는 한 벌이고, pane 배치·predictive back·창 크기 대응은 전략이 담당합니다.
</div>

3. **넓은 화면은 하단 탭바 대신 내비 레일.** 목업 태블릿 아트보드와 계획서 §5.5(medium 이상 = rail)가
   요구하는 부분입니다. 레일은 목업대로 아이콘 없이 라벨만 세로로 세웁니다:

```kotlin
// core/ui/DsBottomBar.kt — Step 5 §1의 DsBottomBar 아래에 추가
@Composable
fun DsNavRail(current: DsTab, onSelect: (DsTab) -> Unit) = Column(
    Modifier.fillMaxHeight().width(92.dp).padding(top = 24.dp),
    horizontalAlignment = Alignment.CenterHorizontally,
    verticalArrangement = Arrangement.spacedBy(26.dp),
) {
    DsTab.entries.forEach { tab ->
        Text(tab.label, Modifier.clickable { onSelect(tab) }                  // 터치 48dp(15sp + 위아래 14dp)
            .padding(vertical = 14.dp, horizontal = 8.dp),
            style = Display.copy(fontSize = 15.sp),
            color = if (tab == current) DsColors.live else DsColors.muted2)
    }
}
```

   `DiamondScoreApp`의 `Scaffold`를 폭으로 감쌉니다. 600dp는 material3 adaptive의 medium 경계이고,
   계획서 §5.5대로 **medium부터 레일**입니다. pane 분할 시점은 이보다 늦습니다 —
   `ListDetailSceneStrategy`가 쓰는 기본 directive(`calculatePaneScaffoldDirective`)는 compact·medium을
   모두 1-pane으로 보고 **expanded(840dp)부터** 2-pane이므로, 레일이 먼저 나타나고 목록·상세가 나란히
   서는 건 그보다 넓어진 뒤입니다:

```kotlin
BoxWithConstraints {
    val rail = maxWidth >= 600.dp
    Row {
        if (rail) DsNavRail(tab) { tab = it }
        Scaffold(bottomBar = { if (!rail) DsBottomBar(tab) { tab = it } }) { pad ->
            NavDisplay(
                entries = decorated.getValue(tab),
                onBack = { current.removeLastOrNull() },
                sceneStrategy = listDetail,
                modifier = Modifier.padding(pad),
            )
        }
    }
}
```

<div class="checkpoint"><span class="t"></span> compact(폰)은 하단 네비 + 단일 화면, expanded(태블릿)는 목업처럼 왼쪽 레일 + 목록·상세가 나란히 뜨면 성공. 태블릿에서 경기를 고르지 않은 상태에서 <code>detailPlaceholder</code>가 보이는지도 확인하세요.</div>

## 5. 접근성

컴포넌트 쪽 코드는 이미 들어가 있습니다 — 라인스코어 요약 semantics는 **Step 5 §3**에서, 아이콘마다
`contentDescription`을 넘길 수 있게 연 `DsIcon`은 **Step 5 §6**에서 넣었습니다. 여기서 다시 정의하지 말고,
기기에서 켜 놓고 점검만 합니다.

- **TalkBack**: 라인스코어가 요약("1회 초 원정 1점")으로 읽히는지, 스코어보드 → 라인스코어 → 정보 순인지.
- **터치 48dp**: 날짜 화살표·별·세그먼트(§2의 `DsSegmented`·§4의 `DsNavRail`에서 이미 맞췄습니다).
- **글꼴 200%**: 라인스코어가 가로 스크롤로 살아남는지.
- 팀 컬러 바 등 장식은 `contentDescription = null`, 색만으로 승패를 전달하지 않기(텍스트 병행).
- 로딩 skeleton(`LoadingCards`)이 TalkBack에 읽히지 않는지(계획서 §1.5).
- 점수 변경 애니메이션이 300ms 이내이고 시스템 "애니메이션 줄이기"를 존중하는지(계획서 §1.5).

계측 테스트는 Hilt 없이 도는 것부터 하나 둡니다 — 그래야 아래 명령이 빈 태스크로 지나가지 않습니다.
`app/src/androidTest/java/com/diamondscore/SettingsUiTest.kt` (완전한 코드):

```kotlin
package com.diamondscore

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.diamondscore.core.designsystem.DiamondScoreTheme
import com.diamondscore.feature.settings.DsSegmented
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

class SettingsUiTest {
    @get:Rule val compose = createComposeRule()

    @Test fun 세그먼트를_누르면_선택값이_바뀐다() {
        var picked = "20초"
        compose.setContent {
            DiamondScoreTheme { DsSegmented(listOf("20초", "30초", "1분"), picked) { picked = it } }
        }
        compose.onNodeWithText("1분").performClick()
        assertEquals("1분", picked)
    }
}
```

<div class="callout warn"><span class="t">Hilt 계측 테스트는 범위 밖</span>
<code>hiltViewModel()</code>을 쓰는 화면(<code>SettingsScreen</code>·<code>GamesScreen</code>)을 통째로 띄우려면 <code>HiltTestApplication</code>을 올리는 커스텀 러너와 <code>kspAndroidTest</code>가 더 필요합니다(Step 2 §4 주석). 그래서 계측 테스트는 <strong>ViewModel을 모르는 컴포저블</strong>만 대상으로 둡니다 — 나머지 접근성 항목은 TalkBack·글꼴 200%를 켜고 손으로 확인하세요.
</div>

```bash
./gradlew :app:connectedDebugAndroidTest
```

## 6. 성능

- UI state는 `@Immutable` data class로, 리스트는 `List` 그대로. Kotlin 2.4는 strong skipping이 기본이라
  `kotlinx-collections-immutable` 의존성 없이도 스킵됩니다 — 리스트를 담은 홀더에 `@Immutable`(불변) 또는
  `@Stable`(바뀌면 알려 준다)만 붙이면 충분합니다.
- `items(key = { it.id })` 안정 key(Step 6).
- `AsyncImage`는 크기 고정(서브컴포지션 회피).

<div class="callout warn"><span class="t">Baseline Profile은 이 튜토리얼 범위 밖</span>
<code>:app:generateBaselineProfile</code>은 <code>androidx.baselineprofile</code> 플러그인과 매크로벤치마크용 <code>:baselineprofile</code> 모듈이 있어야 생기는 태스크입니다. 이 앱은 <code>:app</code> 한 모듈이라 지금 실행하면 <code>Task 'generateBaselineProfile' not found</code>가 납니다 — 계획서의 <code>DS-074</code>로 남겨 둡니다.
</div>

## 7. R8 릴리스 검증

```bash
./gradlew :app:assembleRelease
```

<div class="callout danger"><span class="t">직렬화 클래스 생존 확인</span>
R8이 kotlinx.serialization DTO를 지우면 릴리스에서만 파싱 크래시가 납니다. 릴리스 APK를 <strong>실제로 실행</strong>해 경기 목록이 뜨는지 확인하세요. 문제 시 <code>proguard-rules.pro</code>에 DTO keep 규칙 추가.
</div>

## 8. 완성 점검 (Definition of Done)

<div class="checkpoint"><span class="t"></span> 아래가 모두 예면 앱 완성입니다.</div>

- [ ] 오늘·선택 날짜의 모든 경기가 목업대로 보인다(원정 먼저·4상태)
- [ ] 라이브 점수·이닝이 화면 표시 중 자동 갱신
- [ ] 연장 경기의 10회+ 열이 라인스코어에 나타난다
- [ ] 순위 승·패·무·게임차·진출선, 팀 상세 컬러 헤더
- [ ] 팀 선수단이 투수·타자 두 탭으로 뜨고 등번호가 겹쳐도 크래시하지 않는다
- [ ] 선수 상세가 타자/투수에 따라 다른 표를 그리고, 합계 행이 "13"이 아니라 "합계"로 보인다
- [ ] 기록이 없는 칸이 `0`이 아니라 `—`로 보인다
- [ ] 경기→팀, 순위→팀, 팀→선수단→선수 이동과 back 문맥 복원
- [ ] 오프라인에서 캐시 + 마지막 갱신 표시
- [ ] 범위 밖(볼카운트·문자중계·라인업·개인 순위)의 UI 자리를 만들지 않았다(알림 placeholder는 계획서 §1.3이 허용한 예외)
- [ ] 팀 색과 앱 액센트가 섞이지 않았다 — 두산(네이비)·KIA(레드)를 번갈아 열어 확인
- [ ] compact/expanded, 다크(+선택 시 라이트), 200% 글꼴 검증
- [ ] DTO·Entity가 `data` 밖으로 새지 않았다 — `grep -rn "Dto\|Entity" app/src/main/java/com/diamondscore/feature app/src/main/java/com/diamondscore/core | wc -l`이 `0`
- [ ] `data`는 Compose를 모른다 — `grep -rn "androidx.compose" app/src/main/java/com/diamondscore/data | wc -l`이 `0`
- [ ] `feature/x`가 `feature/y`를 import하지 않는다 — `grep -rn "import com.diamondscore.feature" app/src/main/java/com/diamondscore/feature | wc -l`이 `0`
- [ ] ViewModel 생성자가 `WisetotoApi`·DAO를 직접 받지 않는다 — Repository만 주입(계획서 §11)
- [ ] R8 릴리스 빌드가 실제로 동작

<div class="callout ok"><span class="t">완성 🎉</span>
목업의 모든 화면을 데이터로 살아 움직이게 만들었습니다. 확장은 P1(볼카운트·문자중계·라인업·개인 순위 — 같은 API의 <code>detail</code>·<code>Live_comment</code>·<code>lineup</code>·<code>Sector_Rank</code>)을 붙이거나, 공개 배포를 위해 <a href="#/IMPLEMENTATION_PLAN_KO">전체 계획서</a> §13(BFF 전환)을 참고하세요.
</div>

<div class="pager">
<a href="#/labs/step-8">← Step 8</a>
<a href="#/">홈으로 ↑</a>
</div>
