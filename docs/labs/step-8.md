# Step 8 · 마감 — 접근성·적응형·성능·릴리스

<div class="chips"><span class="chip time">90분</span><span class="chip diff">보통</span><span class="chip goal">출시 품질로 다듬고 R8 릴리스 빌드를 검증한다</span></div>

기능은 끝났습니다. 이제 접근성·태블릿 대응·성능을 다듬고, 난독화된 릴리스 빌드가 실제로 도는지 확인합니다.

## 1. 설정 화면

`feature/settings/SettingsScreen.kt` — 테마(시스템/라이트/다크), 라이브 폴링 간격, **데이터 출처 표기**.

```kotlin
@Composable
fun SettingsScreen() {
    Column(Modifier.padding(16.dp)) {
        ThemePicker()                 // DataStore에 저장
        PollingIntervalPicker()
        ListItem(
            headlineContent = { Text("데이터 출처") },
            supportingContent = { Text("SofaScore · 개인 용도") },
        )
        ListItem(headlineContent = { Text("오픈소스 라이선스") }, modifier = Modifier.clickable { /* OSS */ })
    }
}
```

<div class="callout warn"><span class="t">출처 표기는 필수</span>
데이터 출처(SofaScore)와 개인 용도임을 앱에 명시하세요. 로고·선수 이미지를 재배포하지 않습니다.
</div>

## 2. 접근성

각 화면에서 확인합니다.

- **TalkBack 순서**: 스코어 헤더 → 라인스코어 → 정보 순으로 읽히는지. `Modifier.semantics { }` 로 라인스코어에 `contentDescription = "1회 초 원정 1점"` 형태 요약 제공.
- **터치 영역 48dp**: 날짜 화살표·즐겨찾기 버튼 등.
- **글꼴 200%**: 설정 → 디스플레이 → 글꼴 최대. 라인스코어가 가로 스크롤로 살아남는지.
- 장식 이미지는 `contentDescription = null`.

```bash
# Accessibility Scanner 앱으로 각 화면 스캔, 또는:
./gradlew :app:connectedDebugAndroidTest   # semantics 기반 UI 테스트
```

## 3. 적응형 레이아웃

`NavigableListDetailPaneScaffold`로 태블릿/폴더블에서 목록-상세를 나란히 놓습니다.

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

<div class="checkpoint"><span class="t"></span> compact(휴대폰)은 단일 화면 + 하단 네비, expanded(태블릿)는 목록·상세가 나란히 뜨면 성공.</div>

## 4. 성능

```bash
# Baseline Profile 생성 (Macrobenchmark 모듈)
./gradlew :app:generateBaselineProfile
```

- UI state는 `@Immutable` data class, 리스트는 `ImmutableList`로 만들어 strong-skipping이 깨지지 않게.
- `items(..., key = ...)` 안정 key 유지(Step 5).
- 경기일 30분 라이브를 켜두고 배터리·메모리를 관찰(Android Studio Profiler). 누수·과도한 recomposition이 없는지.

## 5. R8 릴리스 빌드 검증

```bash
./gradlew :app:assembleRelease
```

<div class="callout danger"><span class="t">직렬화 클래스 생존 확인</span>
R8이 kotlinx.serialization DTO를 지우면 릴리스에서만 파싱 크래시가 납니다. 릴리스 APK를 <strong>실제로 실행</strong>해 경기 목록이 뜨는지 확인하세요. 문제가 있으면 <code>@Serializable</code> 클래스 keep 규칙을 <code>proguard-rules.pro</code>에 추가합니다.
</div>

```
# proguard-rules.pro (필요 시)
-keep,includedescriptorclasses class com.diamondscore.data.remote.dto.** { *; }
-keepclassmembers class com.diamondscore.data.remote.dto.** { *; }
```

## 6. 최종 점검 (Definition of Done)

<div class="checkpoint"><span class="t"></span> 아래가 모두 예면 앱 완성입니다.</div>

- [ ] 오늘·선택 날짜의 모든 경기가 보인다
- [ ] 라이브 점수·이닝이 화면 표시 중 자동 갱신된다
- [ ] 경기→팀, 순위→팀 이동과 back 문맥 복원
- [ ] 오프라인에서 마지막 데이터 + 갱신 시각 표시
- [ ] 결측·일부 필드 부재에도 크래시 없음
- [ ] 범위 밖(볼카운트·선수 기록)의 UI 자리를 만들지 않았다
- [ ] compact/expanded, 라이트/다크, 200% 글꼴에서 검증
- [ ] R8 릴리스 빌드가 실제로 동작

<div class="callout ok"><span class="t">완성 🎉</span>
축하합니다 — SofaScore 데이터로 도는 KBO 실시간 앱을 처음부터 만들었습니다. 더 확장하려면 P1(문자중계·라인업·선수 기록)에 보조 소스를 붙이거나, 공개 배포를 위해 <a href="#/IMPLEMENTATION_PLAN_KO">전체 계획서</a> §13(BFF 전환)을 참고하세요.
</div>

<div class="pager">
<a href="#/labs/step-7">← Step 7</a>
<a href="#/">홈으로 ↑</a>
</div>
