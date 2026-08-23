# Step 9 · 마감 — 설정·적응형·성능·릴리스

<div class="chips"><span class="chip time">90분</span><span class="chip diff">보통</span><span class="chip goal">설정 화면·탭 연결·적응형·성능을 마치고 R8 릴리스를 검증한다</span></div>

기능을 마무리합니다. 목업의 설정 화면을 만들고, 4탭을 연결하고, 태블릿 2-pane까지 붙인 뒤 릴리스 빌드를 확인합니다.

## 1. 4탭 연결 (Navigation)

`Scaffold(bottomBar = { DsBottomBar(...) })` 아래에 4개 목적지를 놓습니다(Navigation 3 또는
Navigation-Compose). 상세·팀 상세는 탭 위로 push되고, 각 탭은 자기 back stack을 보존합니다.

```kotlin
@Composable
fun DiamondScoreApp() {
    var tab by rememberSaveable { mutableStateOf(DsTab.GAMES) }
    Scaffold(bottomBar = { DsBottomBar(tab) { tab = it } }) { pad ->
        Box(Modifier.padding(pad)) {
            when (tab) {
                DsTab.GAMES -> GamesGraph()
                DsTab.STANDINGS -> StandingsGraph()
                DsTab.TEAMS -> TeamsGraph()
                DsTab.FAVORITES -> FavoritesScreen()
            }
        }
    }
}
```

## 2. 설정 화면

목업: 테마 세그먼트(시스템/라이트/다크), 라이브 갱신 간격(20초/30초/1분), 알림(P1·비활성), 데이터 출처, 라이선스, 버전.

`feature/settings/SettingsScreen.kt`:

```kotlin
@Composable
fun SettingsScreen(vm: SettingsViewModel = hiltViewModel()) {
    val s by vm.ui.collectAsStateWithLifecycle()
    Column(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(26.dp)) {
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
```

`DsSegmented`는 M3 `SingleChoiceSegmentedButtonRow`로 만들거나, 목업처럼 둥근 배경 위 pill 3개로
직접 그립니다. 테마 선택은 DataStore에 저장하고 `DiamondScoreTheme`가 이를 읽어 다크/라이트를 전환합니다.

## 3. 상태 화면 연결

Step 5에서 만든 `LoadingCards`·`EmptyDay`·`ErrorState`·`StaleBanner`가 모든 화면에서 로딩/빈/오류/
오프라인을 담당합니다. 각 화면의 `when(ui)` 분기가 목업의 상태 화면과 1:1로 맞는지 점검합니다.

## 4. 적응형 — 태블릿 2-pane

목업의 태블릿 화면: 네비 레일 + 목록 pane + 상세 pane. `NavigableListDetailPaneScaffold`로 구현합니다.

```kotlin
@Composable
fun GamesListDetailPane() {
    val nav = rememberListDetailPaneScaffoldNavigator<Long>()
    NavigableListDetailPaneScaffold(
        navigator = nav,
        listPane = { GamesScreen(onGame = { nav.navigateTo(ListDetailPaneScaffoldRole.Detail, it) }) },
        detailPane = { nav.currentDestination?.contentKey?.let { GameDetailScreen(eventId = it) } },
    )
}
```

<div class="checkpoint"><span class="t"></span> compact(폰)은 하단 네비 + 단일 화면, expanded(태블릿)는 목업처럼 왼쪽 목록·오른쪽 상세가 나란히 뜨면 성공.</div>

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
