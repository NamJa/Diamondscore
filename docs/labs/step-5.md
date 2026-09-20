# Step 5 · 공통 컴포넌트

<div class="chips"><span class="chip time">2시간</span><span class="chip diff">보통</span><span class="chip goal">목업의 화면 조각들을 재사용 Composable로 만들고 Preview로 확인한다</span></div>

화면(Step 6~8)을 조립하기 전에, 목업에 등장하는 **부품**을 먼저 만듭니다. 각 컴포넌트는 `@Preview`로
기기 없이 바로 눈으로 확인합니다 — 목업과 나란히 두고 맞추세요.

<div class="callout tip"><span class="t">왜 컴포넌트 먼저인가</span>
경기 카드는 목록·즐겨찾기·태블릿에, 라인스코어는 상세·태블릿에 재등장합니다. 한 번 잘 만들어 두면
화면 Step이 "조립"만 남습니다. Preview로 4가지 상태를 한 파일에서 검증할 수 있어 빠릅니다.
</div>

모든 컴포넌트는 `com.diamondscore.core.ui` 패키지에 두고, Step 2의 `DsColors`·`teamColor`·
`teamShort`·`ScoreNumber`·**`Display`(Bebas)**와 Step 3의 도메인 모델(`GameSummary`·`GameStatus`·
`InningRuns`·`Standing`)을 씁니다.

<div class="callout tip"><span class="t">왜 <code>core/designsystem</code>이 아니라 <code>core/ui</code>인가</span>
<code>core/designsystem</code>은 <strong>도메인을 모르는</strong> 토큰·프리미티브만 둡니다(색·타이포·테마·<code>teamColor</code>). 여기 만드는 컴포넌트들은 <code>GameSummary</code>·<code>Standing</code>을 파라미터로 받으니 도메인을 압니다 — 그래서 한 칸 위인 <code>core/ui</code>에 둡니다. 화면(<code>feature/*</code>)에 종속되지 않아 재사용되고, 나중에 모듈을 쪼갤 때 <code>:core:ui</code>가 <code>:domain</code>에 의존하는 건 정상이지만 <code>:core:designsystem</code>이 그러면 안 됩니다.
</div>

<div class="callout tip"><span class="t">브로드캐스트 × 에디토리얼 원칙</span>
<strong>라이브</strong>는 A(브로드캐스트) — 레드 그라디언트 보더 히어로 + 초대형 Bebas 스코어 + VS.
<strong>예정·종료·순위·정보</strong>는 C(에디토리얼) — 카드 없이 <strong>헤어라인 + 여백</strong>의 라인 로우.
큰 숫자·헤더는 <code>Display</code>(Bebas), 표의 작은 숫자는 <code>ScoreNumber</code>(등폭).
</div>

<div class="callout tip"><span class="t">코드에 나오는 작은 헬퍼들</span>
<code>DsIcon</code>·<code>DsTabIcon</code>·<code>CenterColumn</code>·<code>TopBar</code>·<code>pulseAlpha</code> 등 화면 전반이 쓰는
공용 조각의 <strong>전체 구현은 §6</strong>에, 라인스코어 표 전용인 <code>HeaderCell</code>·<code>TeamCell</code>·<code>TotalCell</code>은 <strong>§3의 같은 파일 안</strong>에, Preview용 <code>sampleLive</code> 등 <strong>샘플 데이터는 §7</strong>에, Step 8이 쓰는 <code>PlayerAvatar</code>·<code>StatTiles</code>·<code>StatTable</code>은 <strong>§8</strong>에 있습니다. 모두 생략 없는 구현이며 package·import는 각 파일 경로에 맞춰 채웁니다. §1~§5를 위에서부터 따라가되, 컴파일 오류가 거슬리면 §6·§7을 먼저 만들어 두고 돌아와도 됩니다.
</div>

## 1. 하단 네비게이션 (DsBottomBar)

목업의 4개 목적지 — 경기 · 순위 · 팀 · 즐겨찾기.

`core/ui/DsBottomBar.kt`:

```kotlin
enum class DsTab(val label: String) { GAMES("경기"), STANDINGS("순위"), TEAMS("팀"), FAVORITES("즐겨찾기") }

@Composable
fun DsBottomBar(current: DsTab, onSelect: (DsTab) -> Unit) {
    NavigationBar(
        containerColor = MaterialTheme.colorScheme.background,   // 브로드캐스트: 배경과 동일
        tonalElevation = 0.dp,
    ) {
        DsTab.entries.forEach { tab ->
            NavigationBarItem(
                selected = tab == current,
                onClick = { onSelect(tab) },
                icon = { DsTabIcon(tab) },
                label = { Text(tab.label, style = Display.copy(fontSize = 15.sp)) },   // Bebas 라벨
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = DsColors.live, selectedTextColor = DsColors.live,
                    indicatorColor = Color.Transparent,                                // pill 없음
                    unselectedIconColor = DsColors.muted2, unselectedTextColor = DsColors.muted2,
                ),
            )
        }
    }
}
```

아이콘은 `Icons.Outlined.CalendarMonth / EmojiEvents / Shield / StarBorder`(material-icons-extended)로
간단히 대체하거나, 목업의 라인 아이콘을 `ImageVector`로 옮깁니다.

## 2. 경기 카드 (GameCard) — 라이브 히어로 + 라인 로우

**라이브는 히어로 카드, 나머지는 라인 로우**로 분기합니다. **원정팀을 먼저** 둡니다.

`core/ui/GameCard.kt`:

```kotlin
@Composable
fun GameCard(game: GameSummary, onClick: () -> Unit) {
    if (game.status == GameStatus.LIVE) LiveHeroCard(game, onClick)
    else GameRow(game, onClick)
}

/** 라이브 — 레드 그라디언트 보더 + 초대형 Bebas 스코어 + VS. */
@Composable
private fun LiveHeroCard(g: GameSummary, onClick: () -> Unit) {
    Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(22.dp))
        .background(Brush.linearGradient(listOf(DsColors.live, DsColors.live.copy(alpha = .35f))))
        .padding(1.dp).clickable(onClick = onClick)) {
        Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(21.dp))
            .background(MaterialTheme.colorScheme.surface).padding(18.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically) {
                LiveBadge(g.statusLabel)
                Text(g.venueShort ?: "", color = DsColors.muted2, style = MaterialTheme.typography.labelSmall)
            }
            Spacer(Modifier.height(14.dp))
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Bottom) {
                HeroSide(g.away, g.awayRuns, Modifier.weight(1f))                 // 원정 먼저
                Text("VS", style = Display.copy(fontSize = 22.sp), color = DsColors.muted2)
                HeroSide(g.home, g.homeRuns, Modifier.weight(1f), accent = true)
            }
            if (g.awayStarter != null || g.homeStarter != null) {            // 선발 미정은 지어내지 않는다
                Spacer(Modifier.height(12.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(g.awayStarter?.let { "선발 $it" } ?: "", color = DsColors.textTertiary,
                        style = MaterialTheme.typography.labelSmall)
                    Text(g.homeStarter?.let { "선발 $it" } ?: "", color = DsColors.textTertiary,
                        style = MaterialTheme.typography.labelSmall)
                }
            }
        }
    }
}

@Composable
private fun HeroSide(t: TeamRef, runs: Int?, mod: Modifier, accent: Boolean = false) =
    Column(mod, horizontalAlignment = Alignment.CenterHorizontally) {
        Text(teamShort(t.id), style = Display.copy(fontSize = 19.sp),
            color = if (accent) DsColors.live else MaterialTheme.colorScheme.onSurfaceVariant)
        Text(runs?.toString() ?: "-", maxLines = 1, style = Display.copy(fontSize = 60.sp),
            color = if (accent) DsColors.live else MaterialTheme.colorScheme.onSurface)   // null=미진행
    }

@Composable
private fun LiveBadge(label: String) = Row(
    Modifier.clip(RoundedCornerShape(999.dp)).background(DsColors.live)
        .padding(horizontal = 12.dp, vertical = 5.dp),
    horizontalArrangement = Arrangement.spacedBy(7.dp), verticalAlignment = Alignment.CenterVertically) {
    Box(Modifier.size(6.dp).clip(CircleShape)
        .background(Color.White.copy(alpha = pulseAlpha())))                // 깜빡임 — §6의 pulseAlpha
    Text("LIVE · $label", color = Color.White, fontWeight = FontWeight.Bold,
        style = MaterialTheme.typography.labelMedium)
}

/** 예정·종료·연기 — 카드 없이 헤어라인 + 여백의 라인 로우(에디토리얼). */
@Composable
private fun GameRow(g: GameSummary, onClick: () -> Unit) = Column {
    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)      // 위 헤어라인
    Row(Modifier.fillMaxWidth().clickable(onClick = onClick)
        .padding(horizontal = 6.dp, vertical = 14.dp),
        horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        when (g.status) {
            GameStatus.SCHEDULED -> {
                Row(verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text(g.startsAt.atZone(SEOUL).toLocalTime().toString().take(5),
                        style = Display.copy(fontSize = 20.sp), color = DsColors.muted2)
                    Column {
                        Text("${g.away.nameKo} · ${g.home.nameKo}", style = MaterialTheme.typography.bodyLarge)
                        listOfNotNull(g.awayStarter, g.homeStarter).takeIf { it.size == 2 }?.let {
                            Text("선발 ${it[0]} · ${it[1]}", color = DsColors.textTertiary,   // 둘 다 있을 때만
                                style = MaterialTheme.typography.labelSmall)
                        }
                    }
                }
                Text(g.venueShort ?: "", color = DsColors.muted2, style = MaterialTheme.typography.labelSmall)
            }
            GameStatus.FINAL -> {
                Text(buildAnnotatedFinal(g), style = MaterialTheme.typography.bodyLarge)
                Text(if (g.wentExtra) g.finalInning?.let { "연장 ${it}회" } ?: "연장" else "종료",
                    color = DsColors.muted2,
                    style = MaterialTheme.typography.labelSmall)
            }
            else -> {   // 취소·연기
                Text("${g.away.nameKo} · ${g.home.nameKo}", color = DsColors.muted2,
                    style = MaterialTheme.typography.bodyLarge)
                Text(g.statusLabel, color = DsColors.gold, style = MaterialTheme.typography.labelSmall)
            }
        }
    }
}
```

`buildAnnotatedFinal(g)`는 "두산 1 · SSG 2"에서 승팀·점수를 강조한 `AnnotatedString`을 만듭니다.

```kotlin
@Composable
private fun buildAnnotatedFinal(g: GameSummary): AnnotatedString {
    val strong = SpanStyle(color = MaterialTheme.colorScheme.onSurface, fontWeight = FontWeight.Bold)
    val dim = SpanStyle(color = DsColors.muted2)
    fun AnnotatedString.Builder.side(t: TeamRef, r: Int?, win: Boolean) =
        withStyle(if (win) strong else dim) { append("${t.nameKo} ${r ?: "-"}") }
    return buildAnnotatedString {
        side(g.away, g.awayRuns, g.winner == Winner.AWAY)   // 원정 먼저
        withStyle(dim) { append("  ·  ") }
        side(g.home, g.homeRuns, g.winner == Winner.HOME)
    }
}
```

<div class="callout warn"><span class="t">null은 "-", 0이 아니다</span>
경기 전에는 점수가 <code>null</code>입니다. <code>runs?.toString() ?: "-"</code>로 <strong>미진행</strong>과 <strong>0점</strong>을 구분하세요(Step 3 원칙).
</div>

**Preview로 4상태 한 번에 확인** — 목업의 카드와 나란히 비교합니다.

```kotlin
@Preview(backgroundColor = 0xFF07080B, showBackground = true, widthDp = 360)
@Composable
private fun GameCardPreview() = DiamondScoreTheme {
    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        GameCard(sampleLive) {}       // ● 6회말  LG 2 : KIA 3
        GameCard(sampleScheduled) {}  // 18:30  삼성 · 롯데
        GameCard(sampleFinalExtra) {} // 연장 11회  두산 1 : SSG 2
        GameCard(sampleCanceled) {}  // 취소
    }
}
```

<div class="checkpoint"><span class="t"></span> Preview 창에 4장의 카드가 목업과 같은 모습(원정 먼저·선발 한 줄·라이브 빨강 강조·연장 표기)으로 뜨면 카드 완성.</div>

## 3. 라인스코어 테이블 (LineScoreTable)

이닝 수가 경기마다 다르고 연장이 붙습니다. **데이터에 있는 만큼만** 열을 그리고 최소 9열을 보장합니다.
오른쪽 총계는 목업대로 **R · H · E** 세 열이고, H·E는 **값이 올 때만** 붙습니다(플랜 §1.3).

`core/ui/LineScoreTable.kt`:

```kotlin
@Composable
fun LineScoreTable(
    away: TeamRef, home: TeamRef, innings: List<InningRuns>,
    awayR: Int?, homeR: Int?,
    awayH: Int? = null, homeH: Int? = null, awayE: Int? = null, homeE: Int? = null,
) {
    val count = maxOf(9, innings.maxOfOrNull { it.number } ?: 9)
    Column {   // 에디토리얼: 카드 대신 위·아래 헤어라인
        HorizontalDivider(color = MaterialTheme.colorScheme.outline)
        Row(Modifier.horizontalScroll(rememberScrollState())) {    // 연장 시 가로 스크롤
            Column {
                HeaderCell("", width = 64.dp); TeamCell(teamShort(away.id)); TeamCell(teamShort(home.id))
            }
            for (n in 1..count) {
                val r = innings.firstOrNull { it.number == n }
                val extra = n > 9
                Column {
                    HeaderCell("$n", accent = extra)
                    RunCell(r?.away, "${n}회 초 원정")                      // TalkBack: "1회 초 원정 1점"
                    RunCell(r?.home, "${n}회 말 홈", live = (n == count))
                }
            }
            Column {
                HeaderCell("R", strong = true); TotalCell(awayR); TotalCell(homeR)
            }
            if (awayH != null || homeH != null) Column {       // 안타 — 공급될 때만
                HeaderCell("H"); TotalCell(awayH, muted = true); TotalCell(homeH, muted = true)
            }
            if (awayE != null || homeE != null) Column {       // 실책 — 공급될 때만
                HeaderCell("E"); TotalCell(awayE, muted = true); TotalCell(homeE, muted = true)
            }
        }
        HorizontalDivider(color = MaterialTheme.colorScheme.outline)
    }
}

@Composable private fun RunCell(run: Int?, label: String, live: Boolean = false) =
    Box(Modifier.width(34.dp).height(38.dp)
        .semantics { run?.let { contentDescription = "$label ${it}점" } },   // 미진행 셀은 낭독하지 않는다
        Alignment.Center) {
        Text(run?.toString() ?: "", style = ScoreNumber.copy(fontSize = 13.sp),   // 미진행 = 빈칸
            color = if (live && run != null) DsColors.live else MaterialTheme.colorScheme.onSurface)
    }

// 라인스코어 셀 — 팀 열 64dp, 이닝/R·H·E 열 34dp
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
fun TotalCell(v: Int?, width: Dp = 34.dp, muted: Boolean = false) =
    Box(Modifier.width(width).height(38.dp), Alignment.Center) {
        Text(v?.toString() ?: "", style = Display.copy(fontSize = if (muted) 14.sp else 18.sp),
            color = if (muted) DsColors.muted2 else MaterialTheme.colorScheme.onSurface)   // Bebas R, 작은 H·E
    }
```

<div class="callout danger"><span class="t">15칸을 그대로 그리지 말 것</span>
열 개수는 매퍼가 잘라 준 <code>innings</code>의 최대 번호로 계산합니다. 서버의 <code>boxscore</code>는 항상 15칸이고 미진행이 <code>null</code>입니다(Step 3 함정 5) — 15열을 그대로 그리면 빈 열 4~6개가 남습니다. 9회말 미실시(홈 승)도 <code>null</code>이라 빈칸으로 보입니다. Preview에 <strong>11이닝 경기</strong>를 하나 넣어 11열이 나오는지 꼭 확인하세요.
</div>

## 4. 순위 행 (StandingRow) + 진출선

에디토리얼 라인 로우: **Bebas 순위 숫자** + 팀컬러 닷 + **승·패·무**·승률·게임차·**연속**. 5위 뒤에 진출선.
(경기 수 컬럼은 목업에서 뺐습니다 — 승·패·무 합으로 알 수 있음)

`core/ui/StandingRow.kt`:

```kotlin
@Composable
fun StandingRow(s: Standing, onClick: () -> Unit) = Column {
    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)      // 위 헤어라인
    Row(
        Modifier.fillMaxWidth().clickable(onClick = onClick)
            .heightIn(min = 48.dp)                                          // 터치 타깃 48dp
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("${s.position}", Modifier.width(30.dp), style = Display.copy(fontSize = 22.sp),
            color = when { s.position == 1 -> DsColors.gold                    // 1위 골드
                           s.position <= 5 -> MaterialTheme.colorScheme.onSurface
                           else -> DsColors.muted2 })
        Box(Modifier.size(8.dp).clip(CircleShape).background(teamColor(s.team.id)))   // 팀 컬러 닷
        Spacer(Modifier.width(10.dp))
        Text(s.team.nameKo, Modifier.weight(1f), style = MaterialTheme.typography.bodyLarge,
            color = if (s.position <= 5) MaterialTheme.colorScheme.onSurface else DsColors.muted2)
        Text("${s.wins}·${s.losses}·${s.draws}", Modifier.width(78.dp),       // 승·패·무 (무는 draw_count 직접)
            style = ScoreNumber.copy(fontSize = 13.sp), textAlign = TextAlign.Center)
        Text("%.3f".format(s.winPct).removePrefix("0"), Modifier.width(46.dp),
            style = Display.copy(fontSize = 17.sp), textAlign = TextAlign.End)     // 승률 Bebas
        Text(if (s.gamesBehind == 0.0) "-" else "%.1f".format(s.gamesBehind),
            Modifier.width(40.dp), style = ScoreNumber.copy(fontSize = 12.sp),
            textAlign = TextAlign.End, color = DsColors.muted2)
        Text(s.streak.orEmpty(), Modifier.width(34.dp),                    // 연속 — 서버 straight 그대로
            style = ScoreNumber.copy(fontSize = 11.sp), textAlign = TextAlign.End,
            color = if (s.streak?.endsWith("승") == true) DsColors.win else DsColors.loss)
    }
}

/** 가운데 라벨이 있는 구분선. 진출선·육성선수 구분선(Step 8)이 같이 쓴다. */
@Composable
fun LabeledDivider(text: String, color: Color) = Row(
    Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 6.dp),
    verticalAlignment = Alignment.CenterVertically) {
    HorizontalDivider(Modifier.weight(1f), color = color.copy(alpha = .3f))
    Text(" $text ", color = color, style = Display.copy(fontSize = 13.sp))
    HorizontalDivider(Modifier.weight(1f), color = color.copy(alpha = .3f))
}

@Composable
fun PlayoffDivider() = LabeledDivider("POSTSEASON", DsColors.live)
```

## 5. 상태 컴포넌트 (로딩·빈 날짜·오류·오프라인)

목업의 4가지 상태를 재사용 컴포넌트로. 모든 화면이 이 넷으로 로딩/빈/오류/stale을 표현합니다.

`core/ui/States.kt`:

```kotlin
@Composable
fun LoadingCards(count: Int = 4) = Column(
    Modifier.padding(14.dp)
        .clearAndSetSemantics { contentDescription = "불러오는 중" },   // 빈 박스 4개를 각각 읽지 않게
    verticalArrangement = Arrangement.spacedBy(12.dp)) {
    val alpha = pulseAlpha(from = .5f, to = .9f, ms = 700)   // 스켈레톤은 배지보다 느리고 얕게
    repeat(count) {
        Box(Modifier.fillMaxWidth().height(84.dp).clip(RoundedCornerShape(12.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = alpha)))
    }
}

@Composable
fun EmptyDay(onNearest: () -> Unit) = CenterColumn {
    DsIcon(Icons.Outlined.CalendarMonth, size = 52.dp, tint = DsColors.muted2)
    Text("이 날은 경기가 없어요", style = MaterialTheme.typography.bodyLarge)
    Text("월요일은 KBO 휴식일", color = DsColors.muted2, style = MaterialTheme.typography.labelMedium)
    OutlinedButton(onClick = onNearest) { Text("가장 가까운 경기일로") }
}

@Composable
fun ErrorState(onRetry: () -> Unit) = CenterColumn {
    DsIcon(Icons.Outlined.ErrorOutline, size = 52.dp, tint = MaterialTheme.colorScheme.primary)
    Text("경기를 불러오지 못했어요", style = MaterialTheme.typography.bodyLarge)
    Text("네트워크를 확인해 주세요", color = DsColors.muted2, style = MaterialTheme.typography.labelMedium)
    Button(onClick = onRetry) { Text("다시 시도") }   // containerColor 기본값 = colorScheme.primary
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

각각 `@Preview`를 붙여 목업의 상태 화면과 대조합니다. `CenterColumn`·`pulseAlpha`는 아래 §6에 있습니다.

<div class="callout warn"><span class="t">여기서 색 상수를 직접 쓰지 않는다</span>
이 파일에 <code>Color(0xFF…)</code>를 박으면 <strong>라이트 테마에서만 조용히 깨집니다</strong> — 다크에서 만든 회색이 페이퍼 배경 위에서 그대로 회색으로 남기 때문입니다. 목업은 모든 화면에 라이트 변형이 있으므로, 배경·라인·본문은 <code>MaterialTheme.colorScheme.*</code>, 의미색은 <code>DsColors.*</code>로만 읽습니다(Step 2 §6). 예외는 구단 컬러뿐이고 그것도 <code>teamColor</code>/<code>teamTint</code>를 거칩니다.
</div>

## 6. 공용 UI 헬퍼

여러 화면·컴포넌트가 함께 쓰는 작은 조각들. `core/ui/DsHelpers.kt`:

```kotlin
/** 장식용 아이콘은 기본값 null 그대로 두고, 의미를 가진 아이콘(뒤로·즐겨찾기·설정)만 라벨을 넘긴다. */
@Composable
fun DsIcon(
    icon: ImageVector, contentDescription: String? = null,
    tint: Color = LocalContentColor.current, size: Dp = 24.dp,
) = Icon(icon, contentDescription, modifier = Modifier.size(size), tint = tint)

@Composable
fun DsTabIcon(tab: DsTab) = DsIcon(
    when (tab) {
        DsTab.GAMES      -> Icons.Outlined.CalendarMonth
        DsTab.STANDINGS  -> Icons.Outlined.EmojiEvents
        DsTab.TEAMS      -> Icons.Outlined.Shield
        DsTab.FAVORITES  -> Icons.Outlined.StarBorder
    }
)

/** 무한 반복 알파 펄스. LIVE 배지 점(1→.35, 1.3초 왕복)과 스켈레톤이 같이 쓴다. */
@Composable
fun pulseAlpha(from: Float = 1f, to: Float = .35f, ms: Int = 650): Float =
    rememberInfiniteTransition(label = "pulse").animateFloat(
        from, to, infiniteRepeatable(tween(ms), RepeatMode.Reverse), label = "a").value

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
fun TopBar(
    title: String, subtitle: String? = null,
    accentDot: Boolean = true,                    // 탭 루트는 마침표, 설정 화면은 false
    trailing: @Composable (() -> Unit)? = null,
) = Row(
    Modifier.fillMaxWidth().padding(start = 16.dp, end = 8.dp, top = 14.dp, bottom = 8.dp),
    verticalAlignment = Alignment.CenterVertically,
    horizontalArrangement = Arrangement.SpaceBetween,
) {
    Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(buildAnnotatedString {                                   // 목업 워드마크: Bebas 34 + 레드 마침표
            append(title)
            if (accentDot) withStyle(SpanStyle(color = DsColors.live)) { append(".") }
        }, style = Display.copy(fontSize = 34.sp))
        subtitle?.let { Text(it, style = MaterialTheme.typography.labelMedium, color = DsColors.muted2) }
    }
    trailing?.invoke()
}

@Composable
fun SectionLabel(text: String) = Text(
    text, Modifier.padding(start = 4.dp, top = 6.dp),
    style = Display.copy(fontSize = 15.sp, letterSpacing = 0.14.em), color = DsColors.muted2,   // 목업 섹션 헤더
)

@Composable
fun LabeledBlock(title: String, content: @Composable () -> Unit) = Column {
    Text(title, Modifier.padding(bottom = 8.dp, start = 2.dp),
        style = Display.copy(fontSize = 15.sp, letterSpacing = 0.14.em), color = DsColors.muted2)
    content()
}

@Composable
fun Caption(text: String) =
    Text(text, style = MaterialTheme.typography.labelSmall, color = DsColors.muted2)

/** 과거 시즌 전환(P1)이 들어올 때 쓸 조각 — 지금 순위 화면(Step 8)은 현재 시즌을 `Caption` 라벨로만 표시해 호출처가 없다. */
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

<div class="callout tip"><span class="t">접근성은 컴포넌트가 들고 있다</span>
Step 9 §5가 말하는 접근성 코드는 <strong>여기</strong>에 있습니다 — 라인스코어 셀의 요약 낭독(§3의 <code>RunCell</code>), 스켈레톤의 <code>clearAndSetSemantics</code>(§5의 <code>LoadingCards</code>), 그리고 위 <code>DsIcon</code>의 <code>contentDescription</code> 파라미터. <code>semantics</code>·<code>clearAndSetSemantics</code>·<code>contentDescription</code>은 <code>androidx.compose.ui.semantics</code>에서 가져옵니다. 터치 타깃은 M3가 대신 맞춰 줍니다 — <code>IconButton</code>은 48dp가 기본이고, <code>Button</code>·<code>SeasonChip</code>이 쓰는 클릭 가능한 <code>Surface</code>는 <code>minimumInteractiveComponentSize()</code>를 내부에서 적용해 보이는 크기가 작아도 터치 영역은 48dp입니다. 직접 만든 클릭 영역(<code>Modifier.clickable</code>)에만 <code>heightIn(min = 48.dp)</code>를 챙기세요.
</div>

<div class="callout tip"><span class="t">아이콘 의존성</span>
<code>Icons.Outlined.CalendarMonth</code> 등은 Step 2 §4에서 이미 넣은 <code>implementation(libs.compose.icons.extended)</code>에 들어 있습니다 — 여기서 의존성을 더 추가할 일은 없습니다. 목업의 라인 아이콘을 그대로 쓰려면 <code>ImageVector.Builder</code>로 옮겨도 됩니다.
</div>

## 7. Preview 샘플 데이터

Preview에서 4상태를 보려면 `GameSummary`를 손으로 채운 샘플이 필요합니다. §3~§8의 Preview가 쓰는
라인스코어·순위·선수단·기록 표 샘플도 같은 파일에 모읍니다. 다른 파일과 같은 main 소스셋의
`core/ui/Samples.kt`에 두세요 — Preview 함수(§2)가 main에 있으니 샘플만 `debug` 소스셋에 두면
`assembleRelease`가 `Unresolved reference: sampleLive`로 깨집니다. 릴리스에서는 R8이 통째로 지웁니다.

```kotlin
private fun sample(
    id: Long, status: GameStatus, home: Long, away: Long,
    hr: Int? = null, ar: Int? = null, label: String = "", winner: Winner? = null,
    extra: Boolean = false, fi: Int? = null, venue: String? = null, hp: String? = null, ap: String? = null,
) = GameSummary(
    id = id, startsAt = Instant.now(), leagueDate = LocalDate.now(SEOUL),
    status = status, statusLabel = label,
    home = TeamRef(home, teamNameKo(home, ""), ""), away = TeamRef(away, teamNameKo(away, ""), ""),
    homeRuns = hr, awayRuns = ar, winner = winner, wentExtra = extra, finalInning = fi,
    venueShort = venue, homeStarter = hp, awayStarter = ap,     // 선발이 없는 경기는 null 그대로
)

// 팀 id는 wisetoto team_info_seq (Step 2 KBO_TEAMS)
val sampleLive       = sample(1, GameStatus.LIVE, home = 320, away = 322, hr = 3, ar = 2, label = "6회말", venue = "광주", hp = "김민준", ap = "김태형")
val sampleScheduled  = sample(2, GameStatus.SCHEDULED, home = 317, away = 318, label = "경기 전", venue = "사직", hp = "박세웅", ap = "원태인")
val sampleFinalExtra = sample(3, GameStatus.FINAL, home = 315, away = 316, hr = 2, ar = 1, label = "경기 종료", winner = Winner.HOME, extra = true, fi = 11, venue = "인천")
val sampleCanceled   = sample(4, GameStatus.CANCELED, home = 2107, away = 319, label = "취소", venue = "창원")

// 라인스코어(§3) — sampleFinalExtra와 같은 경기. 9회까지 1-1, 11회말 끝내기라 11열이 나온다.
private val awayLine = listOf(1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
private val homeLine = listOf(0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1)
val sampleInnings11 = List(11) { i -> InningRuns(i + 1, home = homeLine[i], away = awayLine[i]) }

// 순위 행(§4) — 진출선을 보려면 5위 앞뒤가 있어야 한다(3·4위는 생략).
private fun standing(p: Int, team: Long, w: Int, l: Int, d: Int, gb: Double, streak: String?) =
    Standing(p, TeamRef(team, teamNameKo(team, ""), ""), games = w + l + d,
        wins = w, losses = l, draws = d, winPct = w.toDouble() / (w + l), gamesBehind = gb, streak = streak)

val sampleStandings = listOf(
    standing(1, 320, 82, 50, 3, 0.0, "6승"),
    standing(2, 322, 78, 54, 2, 4.0, "2패"),
    standing(5, 316, 70, 62, 3, 12.0, "1승"),
    standing(6, 317, 66, 67, 2, 16.5, null),
)

// 선수단(§8) — Preview는 네트워크를 타지 않으니 사진은 null(실루엣). 마지막은 100번대 = 육성선수.
val sampleRoster = listOf(
    RosterPlayer(1001, "양현종", 54, null, isDevelopment = false),
    RosterPlayer(1002, "김도영", 5, null, isDevelopment = false),
    RosterPlayer(1003, "박정우", 103, null, isDevelopment = true),
)

// 기록 표(§8) — 타자 월별 7열. null 셀은 "—"로, 마지막 행은 시즌 합계.
val sampleStatHeaders = listOf("월", "경기", "타수", "안타", "홈런", "타점", "타율")
val sampleStatRows = listOf(
    StatRow(listOf("4월", "24", "92", "31", "5", "18", ".337")),
    StatRow(listOf("5월", "26", "101", "28", "3", "15", ".277")),
    StatRow(listOf("6월", "7", "21", null, null, null, null)),
    StatRow(listOf("합계", "57", "214", "66", "9", "40", ".308"), emphasized = true),
)
```

## 8. 선수 아바타와 기록 표

Step 8의 **팀 선수단**·**선수 상세**가 함께 쓰는 셋입니다. 선수단 행과 선수 헤더가 같은 아바타를 쓰고,
선수 상세는 같은 표 컴포넌트로 *월별 기록*과 *최근 5경기*를 그립니다 — 타자·투수 네 벌의 표가 전부 이 하나입니다.

`core/ui/PlayerParts.kt`:

```kotlin
/** 선수 사진. 매퍼가 이미 https로 승격한 URL을 받는다(Step 3 함정 9). 없거나 실패하면 실루엣. */
@Composable
fun PlayerAvatar(photoUrl: String?, size: Dp = 34.dp) = AsyncImage(
    model = photoUrl,
    contentDescription = null,
    placeholder = rememberVectorPainter(Icons.Outlined.Person),
    error = rememberVectorPainter(Icons.Outlined.Person),
    modifier = Modifier.size(size).clip(CircleShape)
        .background(MaterialTheme.colorScheme.surfaceVariant)
        .border(1.dp, MaterialTheme.colorScheme.outline, CircleShape),
)

/** 대표 기록 4칸. 첫 칸만 앱 액센트다 — 팀 색이 아닙니다(Step 2의 역할 구분). */
@Composable
fun StatTiles(tiles: List<Pair<String, String>>) = Row(
    Modifier.fillMaxWidth().padding(horizontal = 16.dp),
    horizontalArrangement = Arrangement.spacedBy(6.dp),
) {
    tiles.forEachIndexed { i, (value, label) ->
        Column(Modifier.weight(1f)) {
            Text(value, style = Display.copy(fontSize = 32.sp), maxLines = 1,
                color = if (i == 0) DsColors.live else MaterialTheme.colorScheme.onSurface)
            Text(label, style = MaterialTheme.typography.labelSmall, color = DsColors.muted2)
        }
    }
}

/** `emphasized` = 시즌 합계 행. 셀이 `null`이면 빈칸이 아니라 `—` 로 그린다(0과 구분, Step 3 함정 12). */
data class StatRow(val cells: List<String?>, val emphasized: Boolean = false)

@Composable
fun StatTable(headers: List<String>, rows: List<StatRow>, weights: List<Float> = List(headers.size) { 1f }) = Column {
    StatLine(headers, weights, header = true)
    rows.forEach { StatLine(it.cells, weights, emphasized = it.emphasized) }
}

@Composable
private fun StatLine(cells: List<String?>, weights: List<Float>, header: Boolean = false, emphasized: Boolean = false) {
    if (!header) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
    Row(
        Modifier.fillMaxWidth()
            .background(if (emphasized) MaterialTheme.colorScheme.surface else Color.Transparent)
            .padding(horizontal = 16.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        cells.forEachIndexed { i, c ->
            Text(
                c ?: "—",
                Modifier.weight(weights.getOrElse(i) { 1f }),
                textAlign = if (i == 0) TextAlign.Start else TextAlign.End,
                style = ScoreNumber.copy(fontSize = if (header) 10.sp else 12.sp),
                fontWeight = if (emphasized) FontWeight.Bold else FontWeight.Normal,
                color = if (header || c == null) DsColors.muted2 else MaterialTheme.colorScheme.onSurface,
                maxLines = 1,
            )
        }
    }
}
```

<div class="callout tip"><span class="t">표를 컴포넌트 하나로 두는 이유</span>
타자 월별(7열)·투수 월별(8열)·타자 최근(7열)·투수 최근(7열) — 네 벌인데 다른 건 <strong>헤더 문자열과 셀 문자열</strong>뿐입니다. 열 폭은 <code>weights</code>로 넘깁니다. 도메인 → 문자열 변환은 화면(Step 8)이 하고, 이 컴포넌트는 <code>String?</code>만 압니다 — 그래서 <code>core/ui</code>에 있어도 <code>PlayerRecord</code>를 몰라도 됩니다.
</div>

<div class="checkpoint"><span class="t"></span> Preview로 카드 4상태 · 라인스코어(11이닝) · 순위 행+진출선 · 상태 4종 · 아바타/기록 표가 모두 목업과 일치하면 컴포넌트 라이브러리 완성. 다크·라이트 Preview를 <strong>둘 다</strong> 띄워 색 상수가 남아 있지 않은지 확인하세요. 다음 Step부터는 이들을 화면에 <strong>조립</strong>만 합니다.</div>

<div class="pager">
<a href="#/labs/step-4">← Step 4</a>
<a href="#/labs/step-6">Step 6 · 경기 목록 →</a>
</div>
