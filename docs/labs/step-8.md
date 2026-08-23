# Step 8 · 순위 · 팀 · 즐겨찾기

<div class="chips"><span class="chip time">90분</span><span class="chip diff">보통</span><span class="chip goal">순위표·팀 상세·즐겨찾기 화면을 컴포넌트로 조립한다</span></div>

정보 탐색 화면을 채웁니다. Step 5의 `StandingRow`·`GameCard`를 재사용하고, 목업의 팀 컬러 헤더를 만듭니다.

## 1. 순위 화면

`feature/standings/StandingsScreen.kt` — `StandingRow` + `PlayoffDivider`(5위 뒤) 조립.

```kotlin
@Composable
fun StandingsScreen(vm: StandingsViewModel = hiltViewModel(), onTeam: (Long) -> Unit) {
    val rows by vm.ui.collectAsStateWithLifecycle()
    Column(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        TopBar("순위", trailing = { SeasonChip("2026 정규시즌") })
        StandingsHeader()   // # 팀 경기 승·패·무 승률 GB
        LazyColumn {
            rows.forEachIndexed { i, s ->
                item(key = s.team.id) { StandingRow(s) { onTeam(s.team.id) } }
                if (i == 4) item("po") { PlayoffDivider() }   // 5위 다음 진출선
            }
        }
    }
}
```

<div class="callout tip"><span class="t">진출선은 LazyColumn DSL로</span>
<code>item {}</code>은 <code>LazyListScope</code>에서만 호출됩니다 — <code>itemsIndexed</code>의 항목 람다 <strong>안에서는</strong> 쓸 수 없습니다. 위처럼 <code>rows.forEachIndexed</code>로 각 행을 <code>item</code>으로 내보내고, 5위 다음에 별도 <code>item</code>으로 <code>PlayoffDivider</code>를 끼웁니다. 공급 안 되는 컬럼은 <code>-</code>가 아니라 컬럼 자체를 숨기고, 동률은 <code>position</code>을 그대로 씁니다(무승부는 파생, Step 3 함정 1).
</div>

## 2. 팀 상세 — 컬러 헤더

목업: 구단 컬러 그라디언트 배너 + 원형 배지 + 순위/전적, 아래 정보·최근·예정 경기.

`feature/teams/TeamHeader.kt`:

```kotlin
@Composable
fun TeamHeader(team: TeamRef, record: String, isFav: Boolean, onFav: () -> Unit, onBack: () -> Unit) {
    val c = teamColor(team.id)
    Box(Modifier.fillMaxWidth()
        .background(Brush.linearGradient(listOf(c, c.copy(alpha = .55f))))
        .padding(bottom = 18.dp)) {
        Column {
            Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                IconButton(onClick = onBack) { DsIcon(Icons.Outlined.ChevronLeft, tint = Color.White) }
                IconButton(onClick = onFav) {
                    DsIcon(if (isFav) Icons.Filled.Star else Icons.Outlined.StarBorder,
                        tint = if (isFav) DsColors.gold else Color.White)
                }
            }
            Row(Modifier.padding(start = 20.dp), horizontalArrangement = Arrangement.spacedBy(14.dp),
                verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(56.dp).clip(CircleShape)
                    .background(Color.White.copy(alpha = .15f))
                    .border(2.dp, Color.White.copy(alpha = .5f), CircleShape), Alignment.Center) {
                    Text(teamShort(team.id), color = Color.White, fontWeight = FontWeight.Bold)
                }
                Column {
                    Text(team.nameKo, color = Color.White, style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold)
                    Text(record, color = Color.White.copy(alpha = .85f), style = ScoreNumber)  // 리그 5위 · 50·44·2
                }
            }
        }
    }
}
```

팀 로고는 Coil 3로 불러오고 실패 시 위 배지로 대체합니다.

```kotlin
AsyncImage(
    model = "https://img.sofascore.com/api/v1/team/${team.id}/image",
    contentDescription = team.nameKo,
    error = rememberVectorPainter(Icons.Outlined.Shield),
    modifier = Modifier.size(56.dp).clip(CircleShape),
)
```

`TeamDetailScreen`은 헤더 아래로 정보 카드(홈구장·수용인원·감독) → "최근 경기" → "다음 경기"를
`GameCard`(또는 목업의 미니 행)로 나열합니다.

## 3. 즐겨찾기

`data/repository/FavoritesRepository.kt`:

```kotlin
class FavoritesRepository @Inject constructor(private val dao: FavoriteDao) {
    fun observeTeams(): Flow<Set<Long>> =
        dao.observe("team").map { it.mapTo(mutableSetOf()) { f -> f.targetId } }
    suspend fun toggle(teamId: Long) {
        if (dao.exists("team", teamId)) dao.delete("team", teamId)
        else dao.insert(FavoriteEntity("team", teamId, System.currentTimeMillis()))
    }
}
```

`FavoritesScreen`은 목업대로 "내 구단"(다음 경기/라이브 요약 + 채운 별)과 "즐겨찾는 경기"를 보여줍니다.
빈 상태면 Step 5의 빈-상태 패턴으로 "구단을 즐겨찾기 해보세요"를 안내합니다.

<div class="callout tip"><span class="t">로컬 저장</span>
로그인 없이 Room에만 저장합니다. 즐겨찾은 구단은 경기 목록 상단 고정(§Step 6-5)과 연결됩니다.
</div>

## 4. 실행 확인

<div class="checkpoint"><span class="t"></span> 순위(진출선 포함) → 팀 선택 → 컬러 헤더의 팀 상세 → 최근 경기 → 경기 상세로 이어지고, 별을 누르면 즐겨찾기에 추가되어 목록 상단에 고정되면 성공. 목업의 순위·팀 상세·즐겨찾기와 대조하세요.</div>

<div class="pager">
<a href="#/labs/step-7">← Step 7</a>
<a href="#/labs/step-9">Step 9 · 마감·릴리스 →</a>
</div>
