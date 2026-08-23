# Step 5 · 공통 컴포넌트

<div class="chips"><span class="chip time">2시간</span><span class="chip diff">보통</span><span class="chip goal">목업의 화면 조각들을 재사용 Composable로 만들고 Preview로 확인한다</span></div>

화면(Step 6~8)을 조립하기 전에, 목업에 등장하는 **부품**을 먼저 만듭니다. 각 컴포넌트는 `@Preview`로
기기 없이 바로 눈으로 확인합니다 — 목업과 나란히 두고 맞추세요.

<div class="callout tip"><span class="t">왜 컴포넌트 먼저인가</span>
경기 카드는 목록·즐겨찾기·태블릿에, 라인스코어는 상세·태블릿에 재등장합니다. 한 번 잘 만들어 두면
화면 Step이 "조립"만 남습니다. Preview로 4가지 상태를 한 파일에서 검증할 수 있어 빠릅니다.
</div>

모든 컴포넌트는 `com.diamondscore.core.designsystem` 패키지에 두고, Step 2의 `DsColors`·`teamColor`·
`teamShort`·`ScoreNumber`와 Step 3의 도메인 모델(`GameSummary`·`GameStatus`·`InningRuns`·`Standing`)을 씁니다.

<div class="callout tip"><span class="t">코드에 나오는 작은 헬퍼들</span>
<code>DsIcon</code>·<code>DsTabIcon</code>·<code>CenterColumn</code>·<code>TopBar</code>·<code>HeaderCell</code>·<code>TeamCell</code>·
<code>TotalCell</code> 등 공용 조각의 <strong>완전한 코드는 §6</strong>에, Preview용 <code>sampleLive</code> 등 <strong>샘플 데이터는 §7</strong>에 있습니다. 먼저 §6·§7을 만들어 두고 위 컴포넌트를 작성하면 매끄럽습니다.
</div>

## 1. 하단 네비게이션 (DsBottomBar)

목업의 4개 목적지 — 경기 · 순위 · 팀 · 즐겨찾기.

`components/DsBottomBar.kt`:

```kotlin
enum class DsTab(val label: String) { GAMES("경기"), STANDINGS("순위"), TEAMS("팀"), FAVORITES("즐겨찾기") }

@Composable
fun DsBottomBar(current: DsTab, onSelect: (DsTab) -> Unit) {
    NavigationBar(containerColor = Color(0xFF10141A), tonalElevation = 0.dp) {
        DsTab.entries.forEach { tab ->
            NavigationBarItem(
                selected = tab == current,
                onClick = { onSelect(tab) },
                icon = { DsTabIcon(tab) },
                label = { Text(tab.label, style = MaterialTheme.typography.labelSmall) },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = DsColors.live, selectedTextColor = DsColors.live,
                    indicatorColor = Color.Transparent,
                    unselectedIconColor = DsColors.muted2, unselectedTextColor = DsColors.muted2,
                ),
            )
        }
    }
}
```

아이콘은 `Icons.Outlined.CalendarMonth / EmojiEvents / Shield / StarBorder`(material-icons-extended)로
간단히 대체하거나, 목업의 라인 아이콘을 `ImageVector`로 옮깁니다.

## 2. 경기 카드 (GameCard) — 4가지 상태

목업의 핵심 부품. **원정팀을 먼저**(위) 표시하고, 팀 컬러 바·상태 칩·등폭 점수를 씁니다.
진행/예정/종료/취소를 한 컴포넌트가 상태로 분기합니다.

`components/GameCard.kt`:

```kotlin
@Composable
fun GameCard(game: GameSummary, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        shape = RoundedCornerShape(14.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column {
            StatusRow(game)
            HorizontalDivider(color = Color(0xFF20262F))
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                TeamRow(game.away, game.awayRuns, emphasize = game.winner == Winner.AWAY)  // 원정 먼저
                TeamRow(game.home, game.homeRuns, emphasize = game.winner == Winner.HOME)
            }
        }
    }
}

@Composable
private fun StatusRow(g: GameSummary) {
    val (label, color) = when (g.status) {
        GameStatus.LIVE      -> "● ${g.statusLabel}" to DsColors.live
        GameStatus.FINAL     -> (if (g.wentExtra) "종료 · 연장" else "종료") to MaterialTheme.colorScheme.onSurfaceVariant
        GameStatus.SCHEDULED -> g.startsAt.atZone(SEOUL).toLocalTime().toString().take(5) to MaterialTheme.colorScheme.onSurface
        else                 -> g.statusLabel to DsColors.gold   // 취소·연기
    }
    Row(Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = color, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
        Text(g.venueShort ?: "", color = DsColors.muted2, style = MaterialTheme.typography.labelSmall)
    }
}

@Composable
private fun TeamRow(team: TeamRef, runs: Int?, emphasize: Boolean) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically) {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.width(4.dp).height(22.dp).clip(RoundedCornerShape(2.dp)).background(teamColor(team.id)))
            Text(team.nameKo, style = MaterialTheme.typography.titleMedium,
                fontWeight = if (emphasize) FontWeight.Bold else FontWeight.Normal)
        }
        Text(runs?.toString() ?: "-", style = ScoreNumber.copy(fontSize = 22.sp),
            color = if (emphasize) DsColors.live else MaterialTheme.colorScheme.onSurface)
    }
}
```

<div class="callout warn"><span class="t">null은 "-", 0이 아니다</span>
경기 전에는 점수가 <code>null</code>입니다. <code>runs?.toString() ?: "-"</code>로 <strong>미진행</strong>과 <strong>0점</strong>을 구분하세요(Step 3 원칙).
</div>

**Preview로 4상태 한 번에 확인** — 목업의 카드와 나란히 비교합니다.

```kotlin
@Preview(backgroundColor = 0xFF0E1116, showBackground = true, widthDp = 360)
@Composable
private fun GameCardPreview() = DiamondScoreTheme {
    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        GameCard(sampleLive) {}       // ● 6회말  LG 2 : KIA 3
        GameCard(sampleScheduled) {}  // 18:30  삼성 · 롯데
        GameCard(sampleFinalExtra) {} // 종료·연장  두산 1 : SSG 2
        GameCard(samplePostponed) {}  // 우천 연기
    }
}
```

<div class="checkpoint"><span class="t"></span> Preview 창에 4장의 카드가 목업과 같은 모습(원정 먼저·팀 컬러 바·라이브 빨강 강조·연장 표기)으로 뜨면 카드 완성.</div>

## 3. 라인스코어 테이블 (LineScoreTable)

이닝 수가 경기마다 다르고 연장이 붙습니다. **데이터에 있는 만큼만** 열을 그리고 최소 9열을 보장합니다.

`components/LineScoreTable.kt`:

```kotlin
@Composable
fun LineScoreTable(away: TeamRef, home: TeamRef, innings: List<InningRuns>, awayR: Int?, homeR: Int?) {
    val count = maxOf(9, innings.maxOfOrNull { it.number } ?: 9)
    Surface(color = Color(0xFF12161C), shape = RoundedCornerShape(12.dp),
        border = BorderStroke(1.dp, Color(0xFF232A34))) {
        Row(Modifier.horizontalScroll(rememberScrollState())) {    // 연장 시 가로 스크롤
            Column {
                HeaderCell("", width = 64.dp); TeamCell(teamShort(away.id)); TeamCell(teamShort(home.id))
            }
            for (n in 1..count) {
                val r = innings.firstOrNull { it.number == n }
                val extra = n > 9
                Column {
                    HeaderCell("$n", accent = extra)
                    RunCell(r?.away)
                    RunCell(r?.home, live = (n == count))
                }
            }
            Column {
                HeaderCell("R", strong = true); TotalCell(awayR); TotalCell(homeR)
            }
        }
    }
}

@Composable private fun RunCell(run: Int?, live: Boolean = false) =
    Box(Modifier.width(34.dp).height(38.dp), Alignment.Center) {
        Text(run?.toString() ?: "", style = ScoreNumber.copy(fontSize = 13.sp),   // 미진행 = 빈칸
            color = if (live && run != null) DsColors.live else MaterialTheme.colorScheme.onSurface)
    }

// 라인스코어 셀 — 팀 열 64dp, 이닝/R 열 34dp
@Composable
fun HeaderCell(text: String, accent: Boolean = false, strong: Boolean = false, width: Dp = 34.dp) =
    Box(Modifier.width(width).height(30.dp), Alignment.Center) {
        Text(text, style = ScoreNumber.copy(fontSize = 12.sp), color = when {
            strong -> MaterialTheme.colorScheme.onSurface
            accent -> DsColors.gold
            else   -> DsColors.muted2
        })
    }

@Composable
fun TeamCell(text: String, width: Dp = 64.dp) =
    Box(Modifier.width(width).height(38.dp).padding(start = 12.dp), Alignment.CenterStart) {
        Text(text, style = MaterialTheme.typography.labelMedium)
    }

@Composable
fun TotalCell(v: Int?, width: Dp = 34.dp) =
    Box(Modifier.width(width).height(38.dp), Alignment.Center) {
        Text(v?.toString() ?: "", style = ScoreNumber.copy(fontSize = 14.sp), fontWeight = FontWeight.Bold)
    }
```

<div class="callout danger"><span class="t">period* 를 쓰지 말 것</span>
열 개수는 <code>innings</code> 맵의 최대 번호로 계산합니다. <code>period1..9</code>만 읽으면 연장 득점이 사라집니다(Step 3 함정 2). Preview에 <strong>10이닝 경기</strong>를 하나 넣어 10열이 나오는지 꼭 확인하세요.
</div>

## 4. 순위 행 (StandingRow) + 진출선

목업의 순위표: 순위·팀(컬러)·경기·**승·패·무**·승률·게임차. 상위 5팀은 좌측 컬러 바, 5위 뒤에 진출선.

`components/StandingRow.kt`:

```kotlin
@Composable
fun StandingRow(s: Standing, onClick: () -> Unit) {
    val tierColor = when {
        s.position == 1 -> DsColors.gold
        s.position <= 5 -> Color(0xFF3A4C6B)
        else -> Color.Transparent
    }
    Row(
        Modifier.fillMaxWidth().clickable(onClick = onClick)
            .drawBehind { drawRect(tierColor, size = size.copy(width = 3.dp.toPx())) }
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("${s.position}", Modifier.width(28.dp), style = ScoreNumber,
            color = if (s.position <= 5) MaterialTheme.colorScheme.onSurface else DsColors.muted2)
        Box(Modifier.width(3.dp).height(20.dp).clip(RoundedCornerShape(2.dp)).background(teamColor(s.team.id)))
        Spacer(Modifier.width(9.dp))
        Text(s.team.nameKo, Modifier.weight(1f), style = MaterialTheme.typography.bodyLarge)
        Text("${s.games}", Modifier.width(34.dp), style = ScoreNumber, textAlign = TextAlign.Center)
        Text("${s.wins}·${s.losses}·${s.draws}", Modifier.width(78.dp),   // 승·패·무 (무 파생!)
            style = ScoreNumber, textAlign = TextAlign.Center)
        Text("%.3f".format(s.winPct).removePrefix("0"), Modifier.width(46.dp),
            style = ScoreNumber, textAlign = TextAlign.End)
        Text(if (s.gamesBehind == 0.0) "-" else "%.1f".format(s.gamesBehind),
            Modifier.width(40.dp), style = ScoreNumber, textAlign = TextAlign.End, color = DsColors.muted2)
    }
}

@Composable
fun PlayoffDivider() = Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 5.dp),
    verticalAlignment = Alignment.CenterVertically) {
    HorizontalDivider(Modifier.weight(1f), color = MaterialTheme.colorScheme.outline)
    Text(" 포스트시즌 진출선 ", color = DsColors.muted2, style = MaterialTheme.typography.labelSmall)
    HorizontalDivider(Modifier.weight(1f), color = MaterialTheme.colorScheme.outline)
}
```

## 5. 상태 컴포넌트 (로딩·빈 날짜·오류·오프라인)

목업의 4가지 상태를 재사용 컴포넌트로. 모든 화면이 이 넷으로 로딩/빈/오류/stale을 표현합니다.

`components/States.kt`:

```kotlin
@Composable
fun LoadingCards(count: Int = 4) = Column(
    Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
    val alpha by rememberInfiniteTransition(label = "sk").animateFloat(
        .5f, .9f, infiniteRepeatable(tween(700), RepeatMode.Reverse), label = "a")
    repeat(count) {
        Box(Modifier.fillMaxWidth().height(84.dp).clip(RoundedCornerShape(12.dp))
            .background(Color(0xFF1A1F27).copy(alpha = alpha)))
    }
}

@Composable
fun EmptyDay(onNearest: () -> Unit) = CenterColumn {
    DsIcon(Icons.Outlined.CalendarMonth, size = 52.dp, tint = Color(0xFF3A4250))
    Text("이 날은 경기가 없어요", style = MaterialTheme.typography.bodyLarge)
    Text("월요일은 KBO 휴식일", color = DsColors.muted2, style = MaterialTheme.typography.labelMedium)
    OutlinedButton(onClick = onNearest) { Text("가장 가까운 경기일로") }
}

@Composable
fun ErrorState(onRetry: () -> Unit) = CenterColumn {
    DsIcon(Icons.Outlined.ErrorOutline, size = 52.dp, tint = MaterialTheme.colorScheme.primary)
    Text("경기를 불러오지 못했어요", style = MaterialTheme.typography.bodyLarge)
    Text("네트워크를 확인해 주세요", color = DsColors.muted2, style = MaterialTheme.typography.labelMedium)
    Button(onClick = onRetry, colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE0263A))) {
        Text("다시 시도")
    }
}

@Composable
fun StaleBanner(lastUpdatedText: String) = Row(
    Modifier.fillMaxWidth().padding(horizontal = 14.dp)
        .clip(RoundedCornerShape(10.dp))
        .background(DsColors.staleBg).border(1.dp, DsColors.staleLine, RoundedCornerShape(10.dp))
        .padding(horizontal = 12.dp, vertical = 8.dp),
    horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
    DsIcon(Icons.Outlined.CloudOff, size = 16.dp, tint = DsColors.gold)
    Text("오프라인 · $lastUpdatedText", color = DsColors.gold, style = MaterialTheme.typography.labelMedium)
}
```

각각 `@Preview`를 붙여 목업의 상태 화면과 대조합니다. `CenterColumn`은 아래 §6에 있습니다.

## 6. 공용 UI 헬퍼

여러 화면·컴포넌트가 함께 쓰는 작은 조각들. `core/designsystem/DsHelpers.kt`:

```kotlin
@Composable
fun DsIcon(icon: ImageVector, tint: Color = LocalContentColor.current, size: Dp = 24.dp) =
    Icon(icon, contentDescription = null, modifier = Modifier.size(size), tint = tint)

@Composable
fun DsTabIcon(tab: DsTab) = DsIcon(
    when (tab) {
        DsTab.GAMES      -> Icons.Outlined.CalendarMonth
        DsTab.STANDINGS  -> Icons.Outlined.EmojiEvents
        DsTab.TEAMS      -> Icons.Outlined.Shield
        DsTab.FAVORITES  -> Icons.Outlined.StarBorder
    }
)

/** 빈/오류 상태의 세로 가운데 정렬 컨테이너. */
@Composable
fun CenterColumn(content: @Composable ColumnScope.() -> Unit) = Column(
    Modifier.fillMaxSize().padding(24.dp),
    horizontalAlignment = Alignment.CenterHorizontally,
    verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically),
    content = content,
)

/** 화면 상단 타이틀 바 (부제 또는 우측 요소 옵션). */
@Composable
fun TopBar(title: String, subtitle: String? = null, trailing: @Composable (() -> Unit)? = null) = Row(
    Modifier.fillMaxWidth().padding(start = 16.dp, end = 8.dp, top = 14.dp, bottom = 8.dp),
    verticalAlignment = Alignment.CenterVertically,
    horizontalArrangement = Arrangement.SpaceBetween,
) {
    Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        subtitle?.let { Text(it, style = MaterialTheme.typography.labelMedium, color = DsColors.muted2) }
    }
    trailing?.invoke()
}

@Composable
fun SectionLabel(text: String) = Text(
    text, Modifier.padding(start = 4.dp, top = 6.dp),
    style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold, color = DsColors.muted2,
)

@Composable
fun LabeledBlock(title: String, content: @Composable () -> Unit) = Column {
    Text(title, Modifier.padding(bottom = 8.dp, start = 2.dp),
        style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold)
    content()
}

@Composable
fun Caption(text: String) =
    Text(text, style = MaterialTheme.typography.labelSmall, color = DsColors.muted2)

/** 순위 화면의 시즌 선택 칩. */
@Composable
fun SeasonChip(text: String, onClick: () -> Unit = {}) = Surface(
    onClick = onClick, color = MaterialTheme.colorScheme.surface, shape = RoundedCornerShape(999.dp),
    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
) {
    Row(Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(text, style = MaterialTheme.typography.labelMedium)
        DsIcon(Icons.Outlined.ExpandMore, size = 14.dp, tint = DsColors.muted2)
    }
}
```

<div class="callout tip"><span class="t">아이콘 의존성</span>
<code>Icons.Outlined.CalendarMonth</code> 등은 <code>androidx.compose.material:material-icons-extended</code>에 있습니다. Step 2 <code>dependencies</code>에 <code>implementation("androidx.compose.material:material-icons-extended")</code>를 추가하세요. 목업의 라인 아이콘을 그대로 쓰려면 <code>ImageVector.Builder</code>로 옮겨도 됩니다.
</div>

## 7. Preview 샘플 데이터

Preview에서 4상태를 보려면 `GameSummary`를 손으로 채운 샘플이 필요합니다. `debug` 소스셋에 두세요.

```kotlin
private fun sample(
    id: Long, status: GameStatus, home: Long, away: Long,
    hr: Int? = null, ar: Int? = null, label: String = "", winner: Winner? = null,
    extra: Boolean = false, venue: String? = null,
) = GameSummary(
    id = id, startsAt = Instant.now(), leagueDate = LocalDate.now(SEOUL),
    status = status, statusLabel = label,
    home = TeamRef(home, teamNameKo(home, ""), ""), away = TeamRef(away, teamNameKo(away, ""), ""),
    homeRuns = hr, awayRuns = ar, winner = winner, wentExtra = extra,
    venueShort = venue, changeTimestamp = null,
)

val sampleLive       = sample(1, GameStatus.LIVE, home = 188247, away = 188257, hr = 3, ar = 2, label = "6회말", venue = "광주")
val sampleScheduled  = sample(2, GameStatus.SCHEDULED, home = 188246, away = 188245, venue = "사직")
val sampleFinalExtra = sample(3, GameStatus.FINAL, home = 188244, away = 188248, hr = 2, ar = 1, label = "종료", winner = Winner.HOME, extra = true, venue = "인천")
val samplePostponed  = sample(4, GameStatus.POSTPONED, home = 188253, away = 188243, label = "우천 연기", venue = "창원")
```

<div class="checkpoint"><span class="t"></span> Preview로 카드 4상태 · 라인스코어(10이닝) · 순위 행+진출선 · 상태 4종이 모두 목업과 일치하면 컴포넌트 라이브러리 완성. 다음 Step부터는 이들을 화면에 <strong>조립</strong>만 합니다.</div>

<div class="pager">
<a href="#/labs/step-4">← Step 4</a>
<a href="#/labs/step-6">Step 6 · 경기 목록 →</a>
</div>
