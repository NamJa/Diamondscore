# Step 7 · 경기 상세

<div class="chips"><span class="chip time">80분</span><span class="chip diff">보통</span><span class="chip goal">스코어보드 + 라인스코어(연장) + 정보로 상세 화면을 조립한다</span></div>

Step 5의 `LineScoreTable`을 화면에 올리고, 목업의 스코어보드·경기 정보를 붙입니다. **없는 데이터
(볼카운트·주자·라인업)의 자리는 만들지 않습니다.**

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

`observeGameDetail(id)`는 `GameEntity` + `innings` 테이블을 합쳐 `GameDetail`(요약·라인스코어·구장·감독)을
방출합니다(DAO `@Transaction` 또는 두 Flow `combine`).

## 2. 스코어보드 (ScoreHeader)

목업: 상태 라벨 → 원정팀(먼저) → 홈팀, 팀 컬러 원형 배지 + 등폭 대형 점수, 승팀 강조.

`feature/gamedetail/ScoreHeader.kt`:

```kotlin
@Composable
fun ScoreHeader(d: GameDetail) {
    Surface(color = MaterialTheme.colorScheme.surface, shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline)) {
        Column(Modifier.padding(16.dp)) {
            Text(statusHeadline(d.summary), color = statusColor(d.summary),
                modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center,
                style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(14.dp))
            TeamScoreRow(d.summary.away, d.summary.awayRuns, "원정",
                win = d.summary.winner == Winner.AWAY)
            Spacer(Modifier.height(12.dp))
            TeamScoreRow(d.summary.home, d.summary.homeRuns, "홈",
                win = d.summary.winner == Winner.HOME)
        }
    }
}

@Composable
private fun TeamScoreRow(t: TeamRef, runs: Int?, side: String, win: Boolean) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(40.dp).clip(CircleShape).background(teamColor(t.id)), Alignment.Center) {
                Text(teamShort(t.id), color = Color.White, style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold)
            }
            Column {
                Text(t.nameKo, style = MaterialTheme.typography.titleMedium,
                    fontWeight = if (win) FontWeight.Bold else FontWeight.Normal,
                    color = if (win) MaterialTheme.colorScheme.onSurface else DsColors.muted2)
                Text(if (win) "$side · 승" else side, style = MaterialTheme.typography.labelSmall, color = DsColors.muted2)
            }
        }
        Text(runs?.toString() ?: "-", style = ScoreNumber.copy(fontSize = 34.sp),
            color = if (win) MaterialTheme.colorScheme.onSurface else DsColors.muted2)
    }
}
```

## 3. 화면 조립

```kotlin
@Composable
fun GameDetailScreen(vm: GameDetailViewModel = hiltViewModel(), onBack: () -> Unit) {
    val d by vm.ui.collectAsStateWithLifecycle()
    Scaffold(topBar = { DetailTopBar(onBack, favorite = false) }) { pad ->
        d?.let { detail ->
            Column(Modifier.padding(pad).verticalScroll(rememberScrollState()).padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)) {
                ScoreHeader(detail)
                LabeledBlock("이닝별 득점") {
                    LineScoreTable(detail.summary.away, detail.summary.home, detail.innings,
                        detail.summary.awayRuns, detail.summary.homeRuns)
                }
                LabeledBlock("경기 정보") { InfoTable(detail) }   // 경기장·수용인원·감독·시즌
                DataNote()  // "KBO는 이닝별 득점까지 제공… 볼카운트·라인업은 없음"
                // ⚠️ 볼카운트·주자·라인업·문자중계 탭은 만들지 않는다
            }
        } ?: LoadingCards(count = 2)
    }
}
```

`InfoTable`은 목업의 정보 카드 그대로 — 경기장, 수용 인원(`23,000석`), 감독(데이터 없으면 `[감독명]`),
`KBO League 2026 · 1R`.

## 4. 종료 확정 처리

`inprogress → finished` 전환 시, 마지막 이닝 득점이 반영되기 전에 상태만 먼저 바뀔 수 있습니다.
전환 직후 한 번 더 조회합니다.

```kotlin
LaunchedEffect(d?.summary?.status) {
    if (d?.summary?.status == GameStatus.FINAL) vm.refresh()
}
```

라이브 중에는 화면이 보일 때만 15초 간격으로 상세를 갱신합니다(§7.1 — `events/live`에 이닝이 포함되면
이 폴링을 없앨 수 있음, `DS-002` 결과에 따름).

## 5. 실행 확인

<div class="checkpoint"><span class="t"></span> 9이닝 경기는 1~9열, 연장 경기는 10·11열이 <strong>추가로</strong> 뜨고 미진행 이닝은 빈칸이면 성공(목업과 동일). 취소/미진행은 라인스코어 대신 상태 라벨이 원문으로 보입니다.</div>

<div class="pager">
<a href="#/labs/step-6">← Step 6</a>
<a href="#/labs/step-8">Step 8 · 순위·팀·즐겨찾기 →</a>
</div>
