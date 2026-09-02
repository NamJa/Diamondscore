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

import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
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
            GamesScreen(onGame = { id -> stack.add(GameDetailKey(id)) })
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
                onBack = { stack.removeLastOrNull() },
            )
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

`MainActivity`는 `setContent { DiamondScoreTheme { DiamondScoreApp() } }`이고, `@AndroidEntryPoint`가
붙어 있어야 `hiltViewModel()`이 동작합니다.

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
            TopBar("설정")
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
                SettingRow("데이터 출처", "SofaScore · 개인 용도")
                SettingLink("개인정보 처리방침"); SettingLink("오픈소스 라이선스")
                SettingRow("앱 버전", "0.1.0")
            }
        }
    }
}
```

**ViewModel · 설정 헬퍼** (완전한 코드) — `Caption`·`DsIcon`은 Step 5 §6.

```kotlin
data class SettingsState(val theme: String = "다크", val interval: String = "20초")

@HiltViewModel
class SettingsViewModel @Inject constructor(private val store: SettingsStore) : ViewModel() {
    val ui = store.state.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), SettingsState())
    fun setTheme(v: String) = viewModelScope.launch { store.setTheme(v) }
    fun setInterval(v: String) = viewModelScope.launch { store.setInterval(v) }
}
// SettingsStore = Proto/Preferences DataStore 래퍼 (state: Flow<SettingsState> + setter 2개)

@Composable
fun SettingGroup(title: String, content: @Composable ColumnScope.() -> Unit) = Column {
    Text(title, Modifier.padding(bottom = 10.dp), style = MaterialTheme.typography.labelMedium,
        fontWeight = FontWeight.Bold, color = DsColors.muted2)
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
        Box(Modifier.weight(1f).clip(RoundedCornerShape(8.dp))
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
    DsIcon(Icons.Outlined.ChevronRight, size = 20.dp, tint = Color(0xFF55606D))
}
```

테마 선택은 DataStore(`SettingsStore`)에 저장하고 `DiamondScoreTheme`가 이를 읽어 다크/라이트를 전환합니다
(라이트 스킴은 Step 2 §6의 콜아웃대로 하나 더 정의).

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

1. **어느 키가 어느 pane인지** `entry`의 `metadata`로 표시합니다 — §1의 `dsEntryProvider`에 인자만 추가:

```kotlin
private fun dsEntryProvider(stack: NavBackStack<NavKey>): (NavKey) -> NavEntry<NavKey> =
    entryProvider {
        entry<GamesKey>(
            metadata = ListDetailSceneStrategy.listPane(
                detailPlaceholder = { EmptyDetail("경기를 선택하세요") },   // 넓은 화면에서 오른쪽 pane
            )
        ) {
            GamesScreen(onGame = { id -> stack.add(GameDetailKey(id)) })
        }
        entry<GameDetailKey>(metadata = ListDetailSceneStrategy.detailPane()) { key ->
            GameDetailScreen(key, onBack = { stack.removeLastOrNull() })
        }

        // 순위·팀 → 팀 상세도 같은 방식
        entry<StandingsKey>(metadata = ListDetailSceneStrategy.listPane()) { … }
        entry<TeamsKey>(metadata = ListDetailSceneStrategy.listPane()) { … }
        entry<TeamDetailKey>(metadata = ListDetailSceneStrategy.detailPane()) { key -> … }

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

<div class="checkpoint"><span class="t"></span> compact(폰)은 하단 네비 + 단일 화면, expanded(태블릿)는 목업처럼 왼쪽 목록·오른쪽 상세가 나란히 뜨면 성공. 태블릿에서 경기를 고르지 않은 상태에서 <code>detailPlaceholder</code>가 보이는지도 확인하세요.</div>

## 5. 접근성

- **TalkBack**: 라인스코어에 요약 `contentDescription`("1회 초 원정 1점"), 스코어보드 → 라인스코어 → 정보 순 읽기.
- **터치 48dp**: 날짜 화살표·별·세그먼트.
- **글꼴 200%**: 라인스코어가 가로 스크롤로 살아남는지.
- 팀 컬러 바 등 장식은 `contentDescription = null`, 색만으로 승패를 전달하지 않기(텍스트 병행).

```bash
./gradlew :app:connectedDebugAndroidTest
```

## 6. 성능

- UI state는 `@Immutable`, 리스트는 `ImmutableList`로 strong-skipping 유지.
- `items(key = { it.id })` 안정 key(Step 6).
- `AsyncImage`는 크기 고정(서브컴포지션 회피).

```bash
./gradlew :app:generateBaselineProfile
```

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
- [ ] 경기→팀, 순위→팀 이동과 back 문맥 복원
- [ ] 오프라인에서 캐시 + 마지막 갱신 표시
- [ ] 범위 밖(볼카운트·선수 기록)의 UI 자리를 만들지 않았다
- [ ] compact/expanded, 다크(+선택 시 라이트), 200% 글꼴 검증
- [ ] R8 릴리스 빌드가 실제로 동작

<div class="callout ok"><span class="t">완성 🎉</span>
목업의 모든 화면을 데이터로 살아 움직이게 만들었습니다. 확장은 P1(문자중계·라인업·선수 기록)에 보조 소스를 붙이거나, 공개 배포를 위해 <a href="#/IMPLEMENTATION_PLAN_KO">전체 계획서</a> §13(BFF 전환)을 참고하세요.
</div>

<div class="pager">
<a href="#/labs/step-8">← Step 8</a>
<a href="#/">홈으로 ↑</a>
</div>
