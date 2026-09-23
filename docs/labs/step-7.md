# Step 7 · 경기 상세

<div class="chips"><span class="chip time">80분</span><span class="chip diff">보통</span><span class="chip goal">스코어보드 + 라인스코어(연장) + 정보로 상세 화면을 조립한다</span></div>

Step 5의 `LineScoreTable`을 화면에 올리고, 목업의 스코어보드·경기 정보를 붙입니다. **없는 데이터
(볼카운트·주자·라인업)의 자리는 만들지 않습니다.**

## 1. 상세 ViewModel

`feature/gamedetail/GameDetailViewModel.kt`:

```kotlin
package com.diamondscore.feature.gamedetail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.diamondscore.core.navigation.GameDetailKey
import com.diamondscore.data.repository.GamesRepository
import dagger.assisted.Assisted
import dagger.assisted.AssistedFactory
import dagger.assisted.AssistedInject
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

@HiltViewModel(assistedFactory = GameDetailViewModel.Factory::class)
class GameDetailViewModel @AssistedInject constructor(
    private val repo: GamesRepository,
    @Assisted private val key: GameDetailKey,      // ← nav 인자가 타입 그대로 들어온다
) : ViewModel() {
    val ui = repo.observeGameDetail(key.gameId)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    private var busy = false      // viewModelScope는 메인 디스패처라 플래그 하나로 충분하다

    init { refresh() }   // 진입 시 1회 — 이닝·R/H/E·투수 요약은 상세 응답에만 있다

    fun refresh() = viewModelScope.launch { refreshNow() }

    /** 폴링 루프가 쓰는 suspend 버전 — 앞 요청이 안 끝났으면 건너뛴다(single-flight, Step 6 `refreshNow`와 같은 규칙). */
    suspend fun refreshNow() {
        if (busy) return
        busy = true
        runCatching { repo.refreshGame(key.gameId) }
        busy = false
    }

    @AssistedFactory
    interface Factory {
        fun create(key: GameDetailKey): GameDetailViewModel
    }
}
```

`observeGameDetail(id)`는 `GameEntity` + `innings` 테이블 + 메모리의 상세 메타를 합쳐 `GameDetail`(요약·라인스코어·구장·R/H/E·투수 요약)을
방출합니다(Step 4). 목록 응답에는 이닝별 득점이 없어(계획서 §7.1) 상세를 한 번 받아야 이닝이 채워지므로, ViewModel의 `init`에서
`refresh()`를 한 번 호출합니다 — Step 8의 `StandingsViewModel`과 같은 방식이라 화면이 조회를 잊을 수 없습니다.

<div class="callout warn"><span class="t">Nav3에서 인자를 받는 방법은 이것뿐이다</span>
Nav2에서는 route 문자열 → <code>Bundle</code> → <code>SavedStateHandle["eventId"]</code>였습니다. Nav3는 <code>GameDetailKey(gameId)</code> <strong>객체</strong>를 back stack에 넣으므로 <code>Bundle</code>을 거치지 않습니다. 그래서 <code>savedState["eventId"]</code>는 <code>null</code>이고, <code>checkNotNull</code>이 터집니다. 대신 <code>@AssistedInject</code>로 키를 주입하면 <code>Long</code> 파싱도, <code>NavType</code>도, 키 이름 오타도 없습니다 — 타입이 맞지 않으면 컴파일이 안 됩니다.
</div>

## 2. 스코어보드 (ScoreHeader)

목업: 상단 알약형 상태 칩 → **원정(왼쪽) · FT · 홈(오른쪽)** 좌우 배치, Bebas 대형 점수, 승팀 강조.
카드가 아니라 배경 위에 그대로 얹습니다(에디토리얼 원칙 — 카드는 라이브 히어로 하나뿐, Step 5 §2).

`feature/gamedetail/ScoreHeader.kt`:

```kotlin
@Composable
fun ScoreHeader(d: GameDetail) {
    val g = d.summary
    Column(Modifier.fillMaxWidth().padding(horizontal = 24.dp, vertical = 12.dp),
        horizontalAlignment = Alignment.CenterHorizontally) {
        StatusChip(g)
        Spacer(Modifier.height(20.dp))
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Bottom) {
            TeamScore(Modifier.weight(1f), g.away, g.awayRuns, win = g.winner == Winner.AWAY)  // 원정 먼저
            Text(if (g.status == GameStatus.FINAL) "FT" else "VS",
                Modifier.padding(bottom = 10.dp),
                style = Display.copy(fontSize = 22.sp), color = DsColors.muted2)
            TeamScore(Modifier.weight(1f), g.home, g.homeRuns, win = g.winner == Winner.HOME)
        }
        Spacer(Modifier.height(8.dp))
        Text("${g.away.nameKo} (원정${if (g.winner == Winner.AWAY) " · 승" else ""}) · " +
            "${g.home.nameKo} (홈${if (g.winner == Winner.HOME) " · 승" else ""})",
            style = MaterialTheme.typography.labelSmall, color = DsColors.muted2)
    }
}

/** 목업 상단의 알약 칩 — "종료 · 연장 11회 · 9/10 · 광주". 카드가 아닌 칩이라 라운드가 허용된다. */
@Composable
private fun StatusChip(g: GameSummary) = Surface(
    color = MaterialTheme.colorScheme.surfaceVariant, shape = RoundedCornerShape(999.dp)) {
    val text = listOfNotNull(
        statusHeadline(g),
        "${g.leagueDate.monthValue}/${g.leagueDate.dayOfMonth}",
        g.venueShort,                                  // 홈 도시 — 구장명은 아래 InfoTable에만(함정 6)
    ).joinToString(" · ")
    Text(text, Modifier.padding(horizontal = 12.dp, vertical = 5.dp),
        style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold,
        color = statusColor(g))
}

@Composable
private fun TeamScore(modifier: Modifier, t: TeamRef, runs: Int?, win: Boolean) =
    Column(modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Text(teamShort(t.id), style = Display.copy(fontSize = 22.sp),
            color = if (win) DsColors.accentSoft else DsColors.textSecondary)
        Text(runs?.toString() ?: "-",                                   // null은 "-", 0이 아니다
            style = Display.copy(fontSize = 80.sp, lineHeight = 62.sp), // Bebas 대형 스코어
            color = if (win) DsColors.live else MaterialTheme.colorScheme.onSurfaceVariant)
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
    val status = d?.summary?.status
    val now = rememberMinuteClock()
    val started = status == GameStatus.SCHEDULED && d?.summary?.startsAt?.isAfter(now) == false   // 시작 시각이 지난 예정 경기
    // 라이브(와 시작 시각이 지난 예정)만 15초 — Step 6에서 `core/ui`에 만든 LivePolling을 간격만 바꿔 그대로 쓴다(FINAL이 되면 멈춘다)
    LivePolling(hasLive = status == GameStatus.LIVE || started, intervalMs = 15_000L) { vm.refreshNow() }
    LaunchedEffect(status) {                           // 종료 확정 — §4
        if (status == GameStatus.FINAL) {
            vm.refreshNow()                            // 최종 점수·R/H/E 확정(진입 직후라 init 조회가 도는 중이면 건너뛴다)
            delay(10.minutes)                          // 투수 요약(end_summary)은 종료 7~8분 뒤에 채워진다
            if (d?.winPitcher == null) vm.refreshNow() // 10분 뒤에도 비어 있을 때만 — 이미 끝난 경기를 열 때 헛조회하지 않는다
        }
    }
    Scaffold(topBar = { DetailTopBar(onBack) }) { pad ->
        d?.let { detail ->
            Column(Modifier.padding(pad).verticalScroll(rememberScrollState()).padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)) {
                ScoreHeader(detail)
                LabeledBlock("이닝별 득점") {
                    LineScoreTable(detail.summary.away, detail.summary.home, detail.innings,
                        detail.summary.awayRuns, detail.summary.homeRuns,
                        detail.awayHits, detail.homeHits,        // 목업의 H·E 열 — 값이 올 때만 붙는다
                        detail.awayErrors, detail.homeErrors,
                        liveInning = detail.summary.finalInning.takeIf { detail.summary.status == GameStatus.LIVE })   // 진행 중인 회만 라이브 색
                }
                LabeledBlock("경기 정보") { InfoTable(detail) }   // 경기장·선발·투수 요약
                DataNote()  // "볼카운트·라인업·문자중계는 다음 단계"
                // ⚠️ 볼카운트·주자·라인업·문자중계 탭은 아직 만들지 않는다 (계획서 §1.2 P1 — 자리도 만들지 않는다)
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
package com.diamondscore.feature.gamedetail

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ChevronLeft
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.diamondscore.core.designsystem.DsColors
import com.diamondscore.core.ui.Caption
import com.diamondscore.core.ui.DsIcon
import com.diamondscore.domain.model.GameDetail
import com.diamondscore.domain.model.GameStatus
import com.diamondscore.domain.model.GameSummary

@Composable
fun DetailTopBar(onBack: () -> Unit) = Row(
    Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 14.dp),
    verticalAlignment = Alignment.CenterVertically) {
    // 아이콘만 있는 버튼은 라벨이 없으면 TalkBack이 못 읽는다 — DsIcon의 contentDescription은 Step 5 §6에서 연다
    IconButton(onClick = onBack) { DsIcon(Icons.Outlined.ChevronLeft, contentDescription = "뒤로 가기") }
    Text("경기 상세", style = MaterialTheme.typography.titleMedium)
    // 즐겨찾기 별은 두지 않는다 — 즐겨찾기는 팀 단위(계획서 §1.2)이고, 경기 단위는 P1이라 자리를 만들지 않는다(§1.6)
}

fun statusHeadline(g: GameSummary): String = when (g.status) {
    GameStatus.LIVE      -> "● ${g.statusLabel}"
    GameStatus.FINAL     -> if (g.wentExtra) "종료 · 연장 ${g.finalInning ?: ""}회" else "종료"
    GameStatus.SCHEDULED -> "예정"
    else                 -> g.statusLabel
}

@Composable
fun statusColor(g: GameSummary): Color =
    if (g.status == GameStatus.LIVE) DsColors.live else MaterialTheme.colorScheme.onSurfaceVariant

/** 안타·실책은 라인스코어의 H·E 열이 맡으므로 여기서는 반복하지 않는다(목업 동일). */
@Composable
fun InfoTable(d: GameDetail) {
    // 공급되는 행만 그린다 — null이면 행 자체를 숨긴다 (계획서 §1.3 표시 원칙)
    val rows = listOfNotNull(
        d.venueName?.let { "경기장" to it },              // 구장명은 정규화되지 않은 원문 그대로(함정 6)
        (d.summary.awayStarter ?: d.summary.homeStarter)?.let {
            "선발" to "${d.summary.awayStarter ?: "-"} · ${d.summary.homeStarter ?: "-"}" },  // 원정 · 홈 순
        d.winPitcher?.let { "승리 투수" to it },
        d.losePitcher?.let { "패전 투수" to it },
        d.savePitcher?.let { "세이브" to it },
    )
    Column {   // 에디토리얼: 카드 대신 행마다 헤어라인
        rows.forEach { (k, v) -> InfoRow(k, v) }
        if (rows.isNotEmpty()) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
    }
}

@Composable
private fun InfoRow(k: String, v: String) {
    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
    Row(Modifier.fillMaxWidth().padding(vertical = 12.dp),
        horizontalArrangement = Arrangement.SpaceBetween) {
        Text(k, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodyMedium)
        Text(v, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
fun DataNote() = Row(Modifier.padding(horizontal = 4.dp),
    horizontalArrangement = Arrangement.spacedBy(8.dp)) {
    DsIcon(Icons.Outlined.Info, size = 16.dp, tint = DsColors.muted2)
    Caption("이닝별 득점·안타·실책과 투수 요약까지 표시합니다. 볼카운트·주자·라인업·문자중계는 다음 단계(P1)에서 추가합니다.")
}
```

## 4. 종료 확정 처리

`LIVE → FINAL`(`state: e`) 전환 시 최종 점수와 R/H/E는 상태와 함께 오지만, **승·패·세이브 투수(`end_summary`)는 7~8분 뒤에 채워집니다**(계획서 §2.4 실측 — 그 전엔 `null`). 전환 직후 한 번, 그리고 **10분 뒤에도** 투수 요약이 비어 있으면 한 번 더 조회합니다 — §3의 `LaunchedEffect(status)`가 그 코드입니다.
`status`가 키라서 `LIVE → FINAL`로 바뀔 때만 발화하고, 같은 블록이 없으면 승·패·세이브 투수 행은 영영 비어 있습니다.
비었는지는 **10분을 기다린 뒤에** 봅니다. 이미 끝난 경기를 열면 Room의 `FINAL` 행이 먼저 방출되는데, 그때는 `init`의 상세 조회가 아직 끝나지 않아 투수 요약도 비어 보입니다 — 여기서 바로 판정하면 끝난 경기를 열 때마다 10분 뒤 헛조회가 한 번씩 나갑니다(2026-09-23 실측: 18:09:29 진입 → 18:19:29 같은 요청).

`InfoTable`은 `null` 행을 숨기므로(§3) 투수 요약이 늦게 와도 화면이 깨지지 않고 행이 나중에 나타납니다.

라이브 중에는 화면이 보일 때만 15초 간격으로 `refreshNow()`를 호출합니다(시작 시각이 지난 예정 경기도 — 경기 전에 연 상세가 "예정"에 머물지 않게, Step 6 §4와 같은 이유) — §3의 `LivePolling(hasLive = …, intervalMs = 15_000L)`이
Step 6에서 `core/ui`에 만든(`core/ui/LivePolling.kt`, package `com.diamondscore.core.ui`) 그 컴포저블이고, 간격만 목록(20초)과 다릅니다.
목록과 상세가 같은 조각을 쓰므로 `feature/games`가 아니라 `core/ui`에 있어야 `feature → feature` 참조가 생기지 않습니다(Step 9 §8 DoD). `onTick`이 `suspend`라서 `refresh()`(즉시 반환하는 `launch`)가 아니라
`refreshNow()`를 넘겨야 `busy` 가드가 살아 있고, 앞 요청이 끝난 뒤에 다음 15초가 시작됩니다. `FINAL`이 되면 `hasLive`가 `false`가 되어 폴링이 멈춥니다.
목록 응답에는 이닝별 득점이 없으므로 이 폴링은 없앨 수 없습니다(계획서 §7.1). 서버 캐시가 2초라 15초면 충분합니다.

## 5. 실행 확인

<div class="checkpoint"><span class="t"></span> 9이닝 경기는 1~9열, 연장 경기는 10·11열이 <strong>추가로</strong> 뜨고 미진행 이닝(9회말 미실시 포함)은 빈칸이면 성공(목업과 동일). 오른쪽 총계는 <strong>R</strong>과, 값이 올 때만 붙는 <strong>H·E</strong>입니다. 취소 경기는 라인스코어가 비고 상단 칩에 "취소"가 보입니다.
<br><strong>예정 경기</strong>는 이닝 칸이 <strong>비어 있는 것이 정상</strong>입니다 — <code>boxscore</code>가 전부 <code>null</code>이라 <code>parseInnings</code>가 빈 리스트를 주고(Step 3), <code>LineScoreTable</code>은 최소 9열을 보장하므로(Step 5) 1~9열 머리글만 뜨고 칸과 R은 빈칸입니다. "경기 정보"의 경기장·선발 행은 예정 경기에도 채워져 있어야 합니다.
<br><strong>진행 중 경기</strong>는 진입 시 <code>init { refresh() }</code>가 한 번 도니 진행된 이닝까지 숫자가 차 있어야 합니다. 진행 중인 회의 칸만 라이브 색이고(종료 경기에는 강조가 없습니다), 폰 폭에서도 팀 열과 R·H·E가 보이며 이닝만 가로로 밀립니다. 15초마다 점수가 바뀌고(2026-09-23 실측 간격 14.0~15.2초, 이때 목록 폴링은 멈춥니다), 홈으로 나가면 폴링이 멈춰야 합니다.</div>

<div class="pager">
<a href="#/labs/step-6">← Step 6</a>
<a href="#/labs/step-8">Step 8 · 순위·팀·선수·즐겨찾기 →</a>
</div>
