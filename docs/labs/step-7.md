# Step 7 · 경기 상세

<div class="chips"><span class="chip time">80분</span><span class="chip diff">보통</span><span class="chip goal">스코어보드 + 라인스코어(연장) + 정보로 상세 화면을 조립한다</span></div>

Step 5의 `LineScoreTable`을 화면에 올리고, 목업의 스코어보드·경기 정보를 붙입니다. **없는 데이터
(볼카운트·주자·라인업)의 자리는 만들지 않습니다.**

## 1. 상세 ViewModel

`feature/gamedetail/GameDetailViewModel.kt`:

```kotlin
package com.diamondscore.feature.gamedetail

import com.diamondscore.core.navigation.GameDetailKey
import dagger.assisted.Assisted
import dagger.assisted.AssistedFactory
import dagger.assisted.AssistedInject
import dagger.hilt.android.lifecycle.HiltViewModel

@HiltViewModel(assistedFactory = GameDetailViewModel.Factory::class)
class GameDetailViewModel @AssistedInject constructor(
    private val repo: GamesRepository,
    @Assisted private val key: GameDetailKey,      // ← nav 인자가 타입 그대로 들어온다
) : ViewModel() {
    val ui = repo.observeGameDetail(key.eventId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    fun refresh() = viewModelScope.launch { runCatching { repo.refreshGame(key.eventId) } }

    @AssistedFactory
    interface Factory {
        fun create(key: GameDetailKey): GameDetailViewModel
    }
}
```

`observeGameDetail(id)`는 `GameEntity` + `innings` 테이블을 합쳐 `GameDetail`(요약·라인스코어·구장·감독)을
방출합니다(DAO `@Transaction` 또는 두 Flow `combine`).

<div class="callout warn"><span class="t">Nav3에서 인자를 받는 방법은 이것뿐이다</span>
Nav2에서는 route 문자열 → <code>Bundle</code> → <code>SavedStateHandle["eventId"]</code>였습니다. Nav3는 <code>GameDetailKey(eventId)</code> <strong>객체</strong>를 back stack에 넣으므로 <code>Bundle</code>을 거치지 않습니다. 그래서 <code>savedState["eventId"]</code>는 <code>null</code>이고, <code>checkNotNull</code>이 터집니다. 대신 <code>@AssistedInject</code>로 키를 주입하면 <code>Long</code> 파싱도, <code>NavType</code>도, 키 이름 오타도 없습니다 — 타입이 맞지 않으면 컴파일이 안 됩니다.
</div>

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
        Text(runs?.toString() ?: "-", style = Display.copy(fontSize = 44.sp),   // Bebas 대형 스코어
            color = if (win) MaterialTheme.colorScheme.onSurface else DsColors.muted2)
    }
}
```

## 3. 화면 조립

```kotlin
@Composable
fun GameDetailScreen(key: GameDetailKey, onBack: () -> Unit) {
    // hiltViewModel의 assisted 오버로드. import는 androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
    val vm = hiltViewModel<GameDetailViewModel, GameDetailViewModel.Factory>(
        creationCallback = { factory -> factory.create(key) },
    )
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

<div class="callout tip"><span class="t">키는 넘기고, ViewModel은 화면이 만든다</span>
<code>GameDetailScreen</code>이 <code>vm</code>을 파라미터로 받지 않고 키를 받습니다. 그러면 Step 9의 <code>entryProvider</code>가 <code>entry&lt;GameDetailKey&gt; { key -> GameDetailScreen(key, ...) }</code> 한 줄로 끝납니다. 인스턴스마다 새 ViewModel이 필요한데, 그건 Step 9에서 넣는 <code>rememberViewModelStoreNavEntryDecorator()</code>가 <code>NavEntry.contentKey</code> 기준으로 처리해 줍니다 — <code>key</code> 문자열을 직접 만들 필요가 없습니다.
</div>

### 상세 화면 조각 (완전한 코드)

`feature/gamedetail/DetailParts.kt` — `LabeledBlock`·`Caption`·`DsIcon`은 Step 5 §6에 있습니다.

```kotlin
@Composable
fun DetailTopBar(onBack: () -> Unit, favorite: Boolean, onFav: () -> Unit = {}) = Row(
    Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 14.dp),
    verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
    IconButton(onClick = onBack) { DsIcon(Icons.Outlined.ChevronLeft) }
    Text("경기 상세", style = MaterialTheme.typography.titleMedium)
    IconButton(onClick = onFav) {
        DsIcon(if (favorite) Icons.Filled.Star else Icons.Outlined.StarBorder,
            tint = if (favorite) DsColors.gold else DsColors.muted2)
    }
}

fun statusHeadline(g: GameSummary): String = when (g.status) {
    GameStatus.LIVE      -> "● ${g.statusLabel}"
    GameStatus.FINAL     -> if (g.wentExtra) "종료 · 연장" else "종료"
    GameStatus.SCHEDULED -> "예정"
    else                 -> g.statusLabel
}

@Composable
fun statusColor(g: GameSummary): Color =
    if (g.status == GameStatus.LIVE) DsColors.live else MaterialTheme.colorScheme.onSurfaceVariant

@Composable
fun InfoTable(d: GameDetail) = Surface(
    color = Color(0xFF12161C), shape = RoundedCornerShape(12.dp),
    border = BorderStroke(1.dp, Color(0xFF232A34))) {
    Column(Modifier.padding(horizontal = 14.dp)) {
        InfoRow("경기장", d.venueName ?: "-")
        InfoRow("수용 인원", d.capacity?.let { "%,d석".format(it) } ?: "-")
        InfoRow("감독", listOfNotNull(d.awayManager, d.homeManager)
            .joinToString(" · ").ifEmpty { "[감독명]" })                 // 데이터 없으면 placeholder
        InfoRow("시즌", d.seasonName ?: "KBO League 2026", last = true)
    }
}

@Composable
private fun InfoRow(k: String, v: String, last: Boolean = false) {
    Row(Modifier.fillMaxWidth().padding(vertical = 11.dp),
        horizontalArrangement = Arrangement.SpaceBetween) {
        Text(k, color = DsColors.muted2, style = MaterialTheme.typography.bodyMedium)
        Text(v, style = MaterialTheme.typography.bodyMedium)
    }
    if (!last) HorizontalDivider(color = Color(0xFF1C222A))
}

@Composable
fun DataNote() = Row(Modifier.padding(horizontal = 4.dp),
    horizontalArrangement = Arrangement.spacedBy(8.dp)) {
    DsIcon(Icons.Outlined.InfoOutline, size = 16.dp, tint = DsColors.muted2)
    Caption("KBO는 이닝별 득점까지 제공됩니다. 볼카운트·주자·라인업·선수 기록은 제공되지 않아 화면에 포함하지 않았습니다.")
}
```

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
