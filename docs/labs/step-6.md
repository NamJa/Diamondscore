# Step 6 · 경기 상세 (라인스코어)

<div class="chips"><span class="chip time">90분</span><span class="chip diff">보통</span><span class="chip goal">이닝별 라인스코어(연장 포함)와 종료 확정을 구현한다</span></div>

경기 상세의 핵심은 **동적 라인스코어 테이블**입니다. 9회 + 연장까지 이닝 수가 경기마다 다르므로 데이터에 있는 만큼만 열을 그립니다. **없는 데이터(볼카운트·주자·라인업)의 자리는 만들지 않습니다.**

## 1. 상세 ViewModel

`feature/gamedetail/GameDetailViewModel.kt`:

```kotlin
@HiltViewModel
class GameDetailViewModel @Inject constructor(
    private val repo: GamesRepository,
    savedState: SavedStateHandle,
) : ViewModel() {
    private val id: Long = checkNotNull(savedState["eventId"])
    val ui = repo.observeGameDetail(id)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    fun refresh() = viewModelScope.launch { runCatching { repo.refreshGame(id) } }
}
```

`repo.observeGameDetail(id)`는 `GameEntity` + `innings` 테이블을 합쳐 `GameDetail`을 방출하도록 Repository에 추가합니다(DAO `@Transaction` + `@Relation` 또는 두 Flow `combine`).

## 2. 라인스코어 테이블

`feature/gamedetail/LineScoreTable.kt`. 최소 9열을 보장하고, 연장은 가로 스크롤합니다.

```kotlin
@Composable
fun LineScoreTable(away: TeamRef, home: TeamRef, innings: List<InningRuns>,
                   awayTotal: Int?, homeTotal: Int?) {
    val count = maxOf(9, innings.maxOfOrNull { it.number } ?: 9)
    Row(Modifier.horizontalScroll(rememberScrollState())) {
        Column {   // 팀 이름 열 (고정 느낌)
            HeaderCell(""); TeamCell(away.nameKo); TeamCell(home.nameKo)
        }
        for (n in 1..count) {
            val row = innings.firstOrNull { it.number == n }
            Column {
                HeaderCell("$n")
                RunCell(row?.away)       // null = 미진행 → 공백
                RunCell(row?.home)
            }
        }
        Column {   // 합계 R
            HeaderCell("R"); TotalCell(awayTotal); TotalCell(homeTotal)
        }
    }
}

@Composable private fun RunCell(run: Int?) =
    Box(Modifier.size(34.dp), Alignment.Center) { Text(run?.toString() ?: "") } // 미진행은 빈칸
```

<div class="callout danger"><span class="t">여기서 가장 많이 틀린다</span>
<code>innings.maxOfOrNull { it.number }</code>로 <strong>실제 최대 이닝</strong>을 계산하세요. 9로 고정하면 연장 경기의 결승점이 사라집니다(Step 3 함정 2). <code>period*</code> 필드는 절대 쓰지 않습니다.
</div>

## 3. 상세 화면 조립

```kotlin
@Composable
fun GameDetailScreen(vm: GameDetailViewModel = hiltViewModel(), onBack: () -> Unit) {
    val d by vm.ui.collectAsStateWithLifecycle()
    d?.let { detail ->
        Column(Modifier.verticalScroll(rememberScrollState()).padding(16.dp)) {
            ScoreHeader(detail)                     // 원정/홈 총점 + 상태 라벨(원문)
            Spacer(Modifier.height(16.dp))
            LineScoreTable(detail.summary.away, detail.summary.home, detail.innings,
                detail.summary.awayRuns, detail.summary.homeRuns)
            Spacer(Modifier.height(16.dp))
            InfoSection(venue = detail.venue, homeManager = detail.homeManager,
                awayManager = detail.awayManager, season = detail.seasonName)
            // ⚠️ 볼카운트·주자·라인업·문자중계 탭은 만들지 않는다 (KBO 미제공)
        }
    } ?: LoadingContent()
}
```

## 4. 종료 확정 처리

`inprogress → finished` 전환 시, 마지막 이닝 득점이 반영되기 전에 상태만 먼저 바뀔 수 있습니다. 전환 직후 **한 번 더** 조회합니다.

```kotlin
LaunchedEffect(d?.summary?.status) {
    if (d?.summary?.status == GameStatus.FINAL) vm.refresh()   // 확정 조회 1회
}
```

라이브 중에는 목록과 같은 스케줄러를 공유하되, 화면이 보일 때만 15초 간격으로 상세를 갱신합니다(라이브 응답에 이닝이 포함되면 이 폴링을 없앨 수 있음 — Step 1 `DS-002` 결과에 따름).

## 5. 실행 확인

경기 카드를 눌러 상세로 들어갑니다.

<div class="checkpoint"><span class="t"></span> 9이닝 경기는 1~9열, 연장 경기는 10·11열이 <strong>추가로</strong> 보이고 미진행 이닝은 빈칸이면 성공. 취소/미진행 경기는 라인스코어 대신 상태 라벨이 원문으로 보이면 됩니다.</div>

<div class="pager">
<a href="#/labs/step-5">← Step 5</a>
<a href="#/labs/step-7">Step 7 · 순위·팀·즐겨찾기 →</a>
</div>
