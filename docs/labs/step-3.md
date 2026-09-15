# Step 3 · 네트워크·매핑 계층

<div class="chips"><span class="chip time">90분</span><span class="chip diff">보통</span><span class="chip goal">JSON을 도메인 모델로 안전하게 바꾸고, 함정 8개를 테스트로 고정한다</span></div>

wisetoto 응답을 앱이 쓸 모양으로 바꿉니다. 실측에서 발견한 **함정 8개**(숫자가 문자열, 취소 경기의 부분 점수, 15칸 고정 라인스코어, 목록에 섞인 WBC 경기 등)를 각각 테스트로 막는 것이 이 Step의 핵심입니다.

## 1. 공통 상수와 도메인 모델

먼저 여러 화면이 공유할 시간 상수를 한곳에 둡니다. `core/common/Time.kt`:

```kotlin
package com.diamondscore.core.common

import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

val SEOUL: ZoneId = ZoneId.of("Asia/Seoul")
val dateFmt: DateTimeFormatter = DateTimeFormatter.ofPattern("M월 d일 E", Locale.KOREAN)   // 8월 2일 토
val apiDay: DateTimeFormatter = DateTimeFormatter.ofPattern("yyyyMMdd")                     // Schedule_Day 인자
val apiMonth: DateTimeFormatter = DateTimeFormatter.ofPattern("yyyyMM")                     // Schedule_Month 인자
val apiDateTime: DateTimeFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")     // game_date 문자열
```

`domain/model/Models.kt`:

```kotlin
package com.diamondscore.domain.model

import java.time.Instant
import java.time.LocalDate

enum class GameStatus { SCHEDULED, LIVE, FINAL, CANCELED, POSTPONED, SUSPENDED, UNKNOWN }
enum class Winner { HOME, AWAY, DRAW }

data class TeamRef(val id: Long, val nameKo: String, val code: String)   // id = wisetoto team_info_seq

data class InningRuns(val number: Int, val home: Int?, val away: Int?) // null = 미진행

data class GameSummary(
    val id: Long,                    // schedule_info_seq
    val startsAt: Instant,
    val leagueDate: LocalDate,       // Asia/Seoul
    val status: GameStatus,
    val statusLabel: String,         // "경기 전" / "7회말" / "경기 종료" / "취소"
    val home: TeamRef, val away: TeamRef,
    val homeRuns: Int?, val awayRuns: Int?,   // 경기 전·취소는 null (0 아님)
    val winner: Winner?,             // FINAL일 때만
    val wentExtra: Boolean,
    val venueShort: String? = null,  // 홈구장 도시(예: 광주) — 앱 리소스(KBO_TEAMS)에서
    val homeStarter: String? = null, // 선발투수 — Schedule_Day에만 있음
    val awayStarter: String? = null,
)

/** 상세 화면용 — 요약 + 라인스코어 + R/H/E + 승·패·세이브 투수. */
data class GameDetail(
    val summary: GameSummary,
    val innings: List<InningRuns>,
    val venueName: String?,
    val homeHits: Int?, val awayHits: Int?,
    val homeErrors: Int?, val awayErrors: Int?,
    val winPitcher: String?, val losePitcher: String?, val savePitcher: String?,
)

data class Standing(
    val position: Int, val team: TeamRef,
    val games: Int, val wins: Int, val losses: Int, val draws: Int,   // draws는 API가 직접 준다
    val winPct: Double, val gamesBehind: Double,
    val streak: String?,             // "6승" / "2패"
)
```

<div class="callout tip"><span class="t">상태 enum에 <code>POSTPONED</code>·<code>SUSPENDED</code>가 남아 있는 이유</span>
wisetoto의 <code>state</code>는 <code>a</code>(예정)·<code>e</code>(종료)·<code>c</code>(취소) 세 값만 관측됐고 연기·서스펜디드를 따로 구분하지 않습니다(우천 취소도 <code>c</code>). 두 값은 지금 매핑되지 않지만 목록 화면의 "취소·연기" 섹션이 이미 쓰고 있어 그대로 둡니다. 표본이 잡히면 매퍼만 고치면 됩니다.
</div>

## 2. DTO — 서버 JSON 그대로 받기

모든 응답은 `{"result","code","message","data":{…}}` 봉투에 싸여 옵니다. **점수·순위·기록 수치는 대부분 문자열**(`"9"`, `"0.620"`)이고, 상세의 점수만 숫자입니다. DTO는 서버가 주는 타입 그대로 받고 변환은 매퍼가 합니다.

`data/remote/dto/Dtos.kt`:

```kotlin
package com.diamondscore.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** 공통 봉투. code "00"만 정상, "01"은 잘못된 접근(HTTP는 200). */
@Serializable data class Envelope<T>(
    val result: String? = null, val code: String? = null, val message: String? = null, val data: T? = null,
)

// ── 날짜별·월별 목록 ──
@Serializable data class ScheduleDayDto(
    @SerialName("Schedule_Day") val games: List<ScheduleGameDto> = emptyList(),
    @SerialName("league_rank") val season: SeasonMetaDto? = null,          // 조회 날짜와 무관하게 현재 시즌
)
@Serializable data class SeasonMetaDto(val season: String? = null, val start: String? = null, val end: String? = null)   // "2026-03-27"
@Serializable data class ScheduleMonthDto(@SerialName("Schedule_Month") val games: List<ScheduleGameDto> = emptyList())

@Serializable data class ScheduleGameDto(
    val seq: String,
    @SerialName("game_timestamp") val gameTimestamp: Long? = null,     // Schedule_Day에만 있음
    @SerialName("game_date") val gameDate: String? = null,             // "2026-09-13 17:00:00" (둘 다 있음)
    val state: String? = null,                                         // a / e / c
    val inning: String? = null,                                        // "bs9_1" = 9회초
    @SerialName("stadium_name") val stadiumName: String? = null,
    @SerialName("home_team_info_seq") val homeTeamSeq: String,
    @SerialName("home_team_name") val homeTeamName: String? = null,
    @SerialName("away_team_info_seq") val awayTeamSeq: String,
    @SerialName("away_team_name") val awayTeamName: String? = null,
    @SerialName("home_score") val homeScore: String? = null,           // 문자열! 취소 경기는 null
    @SerialName("away_score") val awayScore: String? = null,
    @SerialName("home_pitcher") val homePitcher: String? = null,       // 선발 (Schedule_Day)
    @SerialName("away_pitcher") val awayPitcher: String? = null,
)

// ── 경기 상세 /live/schedule/{seq} ──
@Serializable data class GameDetailEnvelopeDto(@SerialName("detail_info") val detail: GameDetailDto? = null)

@Serializable data class GameDetailDto(
    @SerialName("schedule_info_seq") val seq: String,
    @SerialName("game_timestamp") val gameTimestamp: Long,
    val state: String? = null,
    val inning: String? = null,
    @SerialName("stadium_name") val stadiumName: String? = null,
    @SerialName("home_team_info_seq") val homeTeamSeq: String,
    @SerialName("home_team_name") val homeTeamName: String? = null,
    @SerialName("away_team_info_seq") val awayTeamSeq: String,
    @SerialName("away_team_name") val awayTeamName: String? = null,
    @SerialName("home_score") val homeScore: Int? = null,              // 여기만 숫자
    @SerialName("away_score") val awayScore: Int? = null,
    val boxscore: BoxScoreDto? = null,
    @SerialName("end_summary") val endSummary: EndSummaryDto? = null,
)
@Serializable data class BoxScoreDto(
    @SerialName("home_score") val home: List<Int?> = emptyList(),      // 항상 15칸, 미진행 null
    @SerialName("away_score") val away: List<Int?> = emptyList(),
    @SerialName("home_RHEB") val homeRheb: List<Int?> = emptyList(),   // R, H, E, B(볼넷)
    @SerialName("away_RHEB") val awayRheb: List<Int?> = emptyList(),
)
@Serializable data class EndSummaryDto(@SerialName("pitcher_batter_record") val pitchers: PitcherRecordDto? = null)
@Serializable data class PitcherRecordDto(
    @SerialName("win_pitcher") val win: String? = null,               // "최민석 (14 승 4 패 0세)"
    @SerialName("lose_pitcher") val lose: String? = null,
    @SerialName("save_pitcher") val save: String? = null,
)

// ── 순위 /rank/League_Rank?year= ──
@Serializable data class LeagueRankDto(val rank: List<RankRowDto> = emptyList())
@Serializable data class RankRowDto(
    val rank: String,
    @SerialName("team_inf_seq") val teamSeq: String,                   // 오타(inf) 그대로
    @SerialName("simple_name") val simpleName: String? = null,
    @SerialName("player_count") val games: String? = null,             // 이름과 달리 경기 수
    @SerialName("win_count") val wins: String? = null,
    @SerialName("lose_count") val losses: String? = null,
    @SerialName("draw_count") val draws: String? = null,
    @SerialName("win_rate") val winRate: String? = null,
    @SerialName("win_distinction") val gamesBehind: String? = null,
    val straight: String? = null,                                      // "6승"
)

// ── 팀 /extra/Team_Info?team_info_seq= ──
@Serializable data class TeamInfoEnvelopeDto(@SerialName("team_info") val teamInfo: TeamInfoDto? = null)
@Serializable data class TeamInfoDto(@SerialName("team_detail") val detail: TeamDetailDto? = null)
@Serializable data class TeamDetailDto(
    val name: String? = null,
    @SerialName("stadium_name") val stadiumName: String? = null,
    val director: String? = null,                                      // 감독
)
```

## 3. Retrofit API와 네트워크 모듈

`data/remote/WisetotoApi.kt`. **경로는 대소문자를 구분합니다** — `Schedule_Day`를 `schedule_day`로 쓰면 404입니다.

```kotlin
package com.diamondscore.data.remote

import com.diamondscore.data.remote.dto.*
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

interface WisetotoApi {
    /** 날짜별 경기 목록. date = yyyyMMdd (하이픈 형식은 "잘못된 접근"). 라이브 갱신도 이걸 20초마다 부른다. */
    @GET("live/Schedule_Day/{date}")
    suspend fun scheduleDay(@Path("date") date: String): Envelope<ScheduleDayDto>

    /** 월별 일정. month = yyyyMM. 팀 필터는 선택. 시즌 프리페치용. */
    @GET("live/Schedule_Month/{month}")
    suspend fun scheduleMonth(
        @Path("month") month: String,
        @Query("team_info_seq") teamId: Long? = null,
    ): Envelope<ScheduleMonthDto>

    /** 경기 상세 — 라인스코어(15칸)·R/H/E·종료 요약. 서버 캐시 2초. */
    @GET("live/schedule/{seq}")
    suspend fun game(@Path("seq") id: Long): Envelope<GameDetailEnvelopeDto>

    /** 순위표. year = 시즌 연도. 서버 캐시 1시간. */
    @GET("rank/League_Rank")
    suspend fun leagueRank(@Query("year") year: Int): Envelope<LeagueRankDto>

    /** 구단 정보(정식 명칭·홈구장·감독). */
    @GET("extra/Team_Info")
    suspend fun teamInfo(@Query("team_info_seq") teamId: Long): Envelope<TeamInfoEnvelopeDto>
}

class WisetotoException(val code: String?, message: String?) : RuntimeException("[$code] $message")

/** 봉투를 벗긴다. code "00"이 아니면 예외 — HTTP 200에 오류가 실려 오기 때문에 여기서 걸러야 한다. */
fun <T> Envelope<T>.body(): T =
    if (code == "00" && data != null) data else throw WisetotoException(code, message)
```

`data/remote/di/NetworkModule.kt` — OkHttp + Retrofit 3 + kotlinx.serialization. **`os=a&lang=kr` 쿼리가 없으면 모든 경로가 `01 잘못된 접근`** 이므로 인터셉터가 항상 붙입니다.

```kotlin
package com.diamondscore.data.remote.di

import com.diamondscore.data.remote.WisetotoApi
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import dagger.Module; import dagger.Provides
import dagger.hilt.InstallIn; import dagger.hilt.components.SingletonComponent
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Interceptor
import retrofit2.Retrofit
import javax.inject.Singleton

@Module @InstallIn(SingletonComponent::class)
object NetworkModule {
    private val json = Json { ignoreUnknownKeys = true; coerceInputValues = true; explicitNulls = false }

    @Provides @Singleton fun okHttp(): OkHttpClient = OkHttpClient.Builder()
        .addInterceptor(Interceptor { chain ->
            val url = chain.request().url.newBuilder()      // 세 키 모두 필수 — 하나라도 없으면 code 01
                .addQueryParameter("os", "a")
                .addQueryParameter("version", "4.1.3")
                .addQueryParameter("lang", "kr")
                .build()
            chain.proceed(chain.request().newBuilder().url(url)
                .header("User-Agent", "DiamondScore/0.1 (Android)")   // Python 기본 UA만 401, 나머지는 자유
                .build())
        })
        .build()

    @Provides @Singleton fun retrofit(client: OkHttpClient): Retrofit = Retrofit.Builder()
        .baseUrl("https://bsrest.wisetoto.com/")
        .client(client)
        .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
        .build()

    @Provides @Singleton fun api(retrofit: Retrofit): WisetotoApi = retrofit.create(WisetotoApi::class.java)
}
```

<div class="callout warn"><span class="t">첫 호출이 곧 <code>DS-001</code> — 응답 봉투의 <code>code</code>를 보라</span>
이 <code>OkHttpClient</code>로 <code>live/Schedule_Day/{오늘}</code>이 실기기에서 <code>code:"00"</code>으로 오는지가 계획서 <code>DS-001</code>입니다. HTTP 상태는 거의 항상 200이라 판정 기준이 못 됩니다 — <code>Envelope.body()</code>가 던지는 <code>WisetotoException</code> 여부로 봅니다. 응답 <code>Content-Type</code>은 <code>text/html</code>이지만 kotlinx 컨버터는 헤더를 보지 않으므로 그대로 파싱됩니다. 인증·토큰·서명은 없습니다.
</div>

<div class="callout tip"><span class="t">Hilt 모듈은 최상위 <code>di/</code>에 모으지 않는다</span>
<code>NetworkModule</code>은 <code>data/remote/</code> 안에, <code>DatabaseModule</code>(Step 4)은 <code>data/local/</code> 안에 둡니다. 최상위 <code>di/</code> 한 패키지에 둘을 모으면 Retrofit과 Room을 동시에 아는 패키지가 생겨, 나중에 <code>:core:network</code>·<code>:core:database</code>로 쪼갤 때 유일하게 손으로 뜯어야 하는 지점이 됩니다.
</div>

<div class="callout tip"><span class="t">Retrofit 3 컨버터 — 패키지를 헷갈리지 마세요</span>
공식 컨버터는 <code>com.squareup.retrofit2:converter-kotlinx-serialization</code>이고 패키지는 <code>retrofit2.converter.kotlinx.serialization</code>입니다. 검색하면 Retrofit 2 시절의 서드파티 <code>com.jakewharton.retrofit2...</code>가 먼저 나오는데, 그건 위 catalog가 넣은 아티팩트가 아니라 컴파일되지 않습니다. Gson/Moshi도 추가하지 마세요. 제네릭 <code>Envelope&lt;T&gt;</code>는 kotlinx가 <code>typeOf</code>로 처리하므로 별도 어댑터가 필요 없습니다.
</div>

## 4. 매퍼 — 함정을 여기서 흡수

`data/remote/mapper/Mappers.kt`:

```kotlin
package com.diamondscore.data.remote.mapper

import com.diamondscore.core.common.*
import com.diamondscore.data.remote.dto.*
import com.diamondscore.domain.model.*
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime

private val INNING_CODE = Regex("""bs(\d+)_([12])""")   // bs7_2 = 7회말

/** 함정 4·미검증: a/e/c만 확정. 그 외 값인데 점수가 있으면 진행 중으로 본다(DS-002에서 확정). */
fun mapStatus(state: String?, hasScore: Boolean): GameStatus = when (state) {
    "a" -> GameStatus.SCHEDULED
    "e" -> GameStatus.FINAL
    "c" -> GameStatus.CANCELED
    else -> if (hasScore) GameStatus.LIVE else GameStatus.UNKNOWN
}

fun inningLabel(code: String?): String? =
    INNING_CODE.matchEntire(code.orEmpty())?.destructured?.let { (n, half) -> "${n}회${if (half == "1") "초" else "말"}" }

fun inningNumber(code: String?): Int? =
    INNING_CODE.matchEntire(code.orEmpty())?.groupValues?.get(1)?.toIntOrNull()

fun statusLabel(status: GameStatus, state: String?, inning: String?): String = when (status) {
    GameStatus.SCHEDULED -> "경기 전"
    GameStatus.FINAL     -> "경기 종료"
    GameStatus.CANCELED  -> "취소"
    GameStatus.LIVE      -> inningLabel(inning) ?: "진행 중"
    else                 -> state ?: "?"                     // 미지의 값은 원문
}

/** 함정 2: "9" 같은 문자열 점수. 빈 문자열·null·비숫자는 null. */
fun String?.toRuns(): Int? = this?.trim()?.toIntOrNull()

/** 함정 8: 목록엔 WBC·시범경기·올스타전이 섞여 있다. 양 팀이 KBO 10구단이고 시즌 시작일 이후인 행만 KBO 정규 경기다. */
fun ScheduleGameDto.isKboRegular(seasonStart: LocalDate?): Boolean {
    if (homeTeamSeq.toLongOrNull() !in KBO_TEAMS || awayTeamSeq.toLongOrNull() !in KBO_TEAMS) return false
    return seasonStart == null || !toSummary().leagueDate.isBefore(seasonStart)   // 시범경기(3/12~3/24)는 여기서 빠진다
}

fun teamRef(seq: String, name: String?): TeamRef {
    val id = seq.toLong()
    return TeamRef(id, teamNameKo(id, name ?: seq), teamShort(id))
}

/** 함정 5: 15칸 고정 배열 → 진행된 이닝까지만. null = 미진행, 0 = 0점. 9회말 미실시도 null로 남는다. */
fun parseInnings(home: List<Int?>, away: List<Int?>): List<InningRuns> {
    val played = maxOf(home.indexOfLast { it != null }, away.indexOfLast { it != null }) + 1
    return (1..played).map { n -> InningRuns(n, home.getOrNull(n - 1), away.getOrNull(n - 1)) }
}

/** 목록(Schedule_Day/Month)과 상세(live/schedule)가 공유하는 요약 조립. */
internal fun buildSummary(
    id: Long, startsAt: Instant, state: String?, inning: String?,
    homeSeq: String, homeName: String?, awaySeq: String, awayName: String?,
    homeScore: Int?, awayScore: Int?, homeStarter: String? = null, awayStarter: String? = null,
): GameSummary {
    val st = mapStatus(state, hasScore = homeScore != null || awayScore != null)
    val hr = homeScore.takeUnless { st == GameStatus.CANCELED || st == GameStatus.SCHEDULED }   // 함정 3: 노게임 부분 점수 버림
    val ar = awayScore.takeUnless { st == GameStatus.CANCELED || st == GameStatus.SCHEDULED }
    val home = teamRef(homeSeq, homeName)
    return GameSummary(
        id = id,
        startsAt = startsAt,
        leagueDate = startsAt.atZone(SEOUL).toLocalDate(),          // 함정: 반드시 KST
        status = st,
        statusLabel = statusLabel(st, state, inning),
        home = home, away = teamRef(awaySeq, awayName),
        homeRuns = hr, awayRuns = ar,
        winner = if (st == GameStatus.FINAL && hr != null && ar != null) when {
            hr > ar -> Winner.HOME; hr < ar -> Winner.AWAY; else -> Winner.DRAW   // 무승부는 동점 종료
        } else null,
        wentExtra = (inningNumber(inning) ?: 0) > 9,
        venueShort = KBO_TEAMS[home.id]?.home,                      // 함정 6: 구장명은 앱 표에서
        homeStarter = homeStarter, awayStarter = awayStarter,
    )
}

fun ScheduleGameDto.toSummary(): GameSummary = buildSummary(
    id = seq.toLong(),
    startsAt = gameTimestamp?.let(Instant::ofEpochSecond)          // 함정 7: 표시용 game_date보다 timestamp 우선
        ?: LocalDateTime.parse(gameDate, apiDateTime).atZone(SEOUL).toInstant(),   // Schedule_Month엔 timestamp가 없다
    state = state, inning = inning,
    homeSeq = homeTeamSeq, homeName = homeTeamName, awaySeq = awayTeamSeq, awayName = awayTeamName,
    homeScore = homeScore.toRuns(), awayScore = awayScore.toRuns(),
    homeStarter = homePitcher, awayStarter = awayPitcher,
)

fun GameDetailDto.toSummary(): GameSummary = buildSummary(
    id = seq.toLong(), startsAt = Instant.ofEpochSecond(gameTimestamp), state = state, inning = inning,
    homeSeq = homeTeamSeq, homeName = homeTeamName, awaySeq = awayTeamSeq, awayName = awayTeamName,
    homeScore = homeScore, awayScore = awayScore,
)

fun GameDetailDto.toDetail(): GameDetail {
    val summary = toSummary()
    val box = boxscore
    val canceled = summary.status == GameStatus.CANCELED
    return GameDetail(
        summary = summary,
        innings = if (canceled || box == null) emptyList() else parseInnings(box.home, box.away),
        venueName = stadiumName,
        homeHits = box?.homeRheb?.getOrNull(1), awayHits = box?.awayRheb?.getOrNull(1),
        homeErrors = box?.homeRheb?.getOrNull(2), awayErrors = box?.awayRheb?.getOrNull(2),
        winPitcher = endSummary?.pitchers?.win, losePitcher = endSummary?.pitchers?.lose,
        savePitcher = endSummary?.pitchers?.save,
    )
}

fun RankRowDto.toDomain() = Standing(
    position = rank.toInt(),
    team = teamRef(teamSeq, simpleName),
    games = games.toRuns() ?: 0, wins = wins.toRuns() ?: 0, losses = losses.toRuns() ?: 0,
    draws = draws.toRuns() ?: 0,                               // 무승부를 직접 준다 (파생 불필요)
    winPct = winRate?.toDoubleOrNull() ?: 0.0,
    gamesBehind = gamesBehind?.toDoubleOrNull() ?: 0.0,
    streak = straight,
)
```

<div class="callout danger"><span class="t">함정 8개 — 이 파일이 막는 것</span>
① 경로 대소문자·<code>yyyyMMdd</code> 형식·<code>os/version/lang</code> 세 키 필수(API 인터페이스·인터셉터) ② 점수·순위가 <strong>문자열</strong>(<code>toRuns</code>) ③ <code>state:"c"</code>인데 노게임 부분 점수가 남아 있음(<code>buildSummary</code>) ④ 진행 중 <code>state</code> 값 미검증(<code>mapStatus</code> 폴백) ⑤ 라인스코어 15칸 고정, <code>null</code>과 <code>0</code> 구분(<code>parseInnings</code>) ⑥ 구장명 표기 비정규(앱 표 사용) ⑦ <code>game_date</code>는 표시 문자열, 변경 감지 필드 없음(<code>game_timestamp</code> 사용, 쓰기 스킵은 Step 4) ⑧ 목록에 WBC·시범경기·올스타전이 섞여 있음(<code>isKboRegular</code>).
</div>

## 5. fixture 옮기고 매퍼 테스트

Step 1에서 받은 JSON을 테스트 리소스로 옮깁니다.

```bash
mkdir -p app/src/test/resources/fixtures
cp fixtures/*.json app/src/test/resources/fixtures/
```

`app/src/test/java/.../MapperTest.kt` — 함정을 각각 검증합니다.

```kotlin
class MapperTest {
    private val json = kotlinx.serialization.json.Json { ignoreUnknownKeys = true; explicitNulls = false }
    private fun load(name: String) = javaClass.classLoader!!.getResourceAsStream("fixtures/$name")!!.bufferedReader().readText()
    private fun day(name: String) = json.decodeFromString<Envelope<ScheduleDayDto>>(load(name)).body().games
    private fun game(name: String) = json.decodeFromString<Envelope<GameDetailEnvelopeDto>>(load(name)).body().detail!!

    @Test fun `문자열 점수를 숫자로`() {                                                  // 함정 2
        val g = day("schedule_day_finished.json").first().toSummary()
        assertEquals(GameStatus.FINAL, g.status); assertNotNull(g.homeRuns); assertNotNull(g.awayRuns)
    }

    @Test fun `취소 경기는 점수가 null`() {                                                // 함정 3
        day("schedule_day_canceled.json").map { it.toSummary() }.forEach {
            assertEquals(GameStatus.CANCELED, it.status); assertNull(it.homeRuns); assertNull(it.awayRuns)
        }
    }

    @Test fun `예정 경기는 선발투수가 있고 점수는 null`() {
        val g = day("schedule_day_scheduled.json").first().toSummary()
        assertEquals(GameStatus.SCHEDULED, g.status); assertNull(g.homeRuns); assertNotNull(g.homeStarter)
    }

    @Test fun `연장 11회가 라인스코어에 나온다`() {                                        // 함정 5
        val d = game("game_extra.json").toDetail()
        assertEquals(11, d.innings.size); assertTrue(d.summary.wentExtra)
        assertEquals(d.summary.homeRuns, d.innings.sumOf { it.home ?: 0 })                   // 이닝 합 = 총점
    }

    @Test fun `9회말 미실시는 null이고 0점은 0이다`() {                                   // 함정 5
        val d = game("game_final.json").toDetail()   // 홈 승 → bs9_1, 9회말 없음
        assertNull(d.innings.last().home); assertEquals(0, d.innings.first { it.home == 0 }.home)
    }

    @Test fun `미지의 state는 점수가 있으면 LIVE 없으면 UNKNOWN`() {                        // 함정 4
        assertEquals(GameStatus.LIVE, mapStatus("zzz", hasScore = true))
        assertEquals(GameStatus.UNKNOWN, mapStatus("zzz", hasScore = false))
        assertEquals("7회말", inningLabel("bs7_2"))
    }

    @Test fun `3월 목록에서 WBC와 시범경기가 걸러진다`() {                                  // 함정 8
        val env = json.decodeFromString<Envelope<ScheduleMonthDto>>(load("schedule_month_march.json")).body()
        val start = LocalDate.parse("2026-03-27")   // 실제 앱은 Schedule_Day의 league_rank.start
        val kept = env.games.filter { it.isKboRegular(start) }
        assertTrue(env.games.any { it.homeTeamName == "한국" || it.awayTeamName == "한국" })   // 원본엔 WBC가 있고
        assertTrue(kept.none { it.homeTeamName == "한국" })                                    // 필터 뒤엔 없다
        assertTrue(kept.all { it.toSummary().leagueDate >= start })                             // 시범경기도 없다
    }

    @Test fun `순위표 문자열 수치와 무승부`() {                                            // 함정 2
        val rows = json.decodeFromString<Envelope<LeagueRankDto>>(load("league_rank.json")).body().rank.map { it.toDomain() }
        assertEquals(10, rows.size)
        rows.forEach { assertEquals(it.games, it.wins + it.losses + it.draws) }
    }

    @Test fun `잘못된 접근 봉투는 예외`() {                                                // 함정 1
        val env = json.decodeFromString<Envelope<ScheduleDayDto>>("""{"result":"success","code":"01","message":"잘못된 접근","data":[]}""")
        assertFailsWith<WisetotoException> { env.body() }
    }
}
```

```bash
./gradlew :app:testDebugUnitTest
```

<div class="checkpoint"><span class="t"></span> 테스트가 초록불이면 완료. 특히 <strong>연장 경기에서 10·11회 득점이 라인스코어에 나타나는지</strong>, <strong>취소 경기의 부분 점수가 사라지는지</strong>가 이 앱에서 가장 자주 깨지는 부분이니 반드시 통과시키세요.</div>

<div class="pager">
<a href="#/labs/step-2">← Step 2</a>
<a href="#/labs/step-4">Step 4 · Room·프리페치 →</a>
</div>
