# Step 3 · 네트워크·매핑 계층

<div class="chips"><span class="chip time">110분</span><span class="chip diff">보통</span><span class="chip goal">JSON을 도메인 모델로 안전하게 바꾸고, 함정 12개를 테스트로 고정한다</span></div>

wisetoto 응답을 앱이 쓸 모양으로 바꿉니다. 실측에서 발견한 **함정 12개**(숫자가 문자열, 취소 경기의 부분 점수, 15칸 고정 라인스코어, 목록에 섞인 WBC 경기, 포지션에 따라 갈리는 선수 기록 스키마, 두 가지 이닝 표기 등)를 각각 테스트로 막는 것이 이 Step의 핵심입니다.

## 1. 공통 상수와 도메인 모델

먼저 여러 화면이 공유할 시간 상수를 한곳에 둡니다. `core/common/Time.kt`:

```kotlin
package com.diamondscore.core.common

import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

val SEOUL: ZoneId = ZoneId.of("Asia/Seoul")
val dateFmt: DateTimeFormatter = DateTimeFormatter.ofPattern("M월 d일 E", Locale.KOREAN)   // 8월 2일 토
val shortDate: DateTimeFormatter = DateTimeFormatter.ofPattern("M/d")                       // 기록 표의 9/17
val apiDay: DateTimeFormatter = DateTimeFormatter.ofPattern("yyyyMMdd")                     // Schedule_Day 인자 · previous5.game_date
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
    val finalInning: Int? = null,    // 마지막(진행 중이면 현재) 이닝 — "연장 11회" 표기용
    val venueShort: String? = null,  // 홈구장 도시(예: 광주) — 앱 리소스(KBO_TEAMS)에서
    val homeStarter: String? = null, // 선발투수 — 당일 Schedule_Day에만 있음(미래 날짜 행은 null)
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

이어서 **팀 정보·선수 정보** 모델입니다(Step 8 화면이 씁니다). 같은 파일에 둡니다.

```kotlin
// ── 팀 ──
data class RosterPlayer(
    val id: Long,                 // player_info_seq — 등번호는 겹칠 수 있어 키가 못 된다
    val name: String,
    val number: Int?,             // c_number를 숫자로. 파싱 실패는 null
    val photoUrl: String?,        // http → https 로 승격한 URL
    val isDevelopment: Boolean,   // 등번호 100 이상 = 육성선수 (서버가 주지 않는 앱 규칙)
)

data class TeamHistoryEntry(val year: Int?, val text: String)   // "1982년 l …" 를 쪼갠 것

/** 팀 상세(Step 8-2)와 팀 정보·선수단(Step 8-3)이 같이 쓴다 — 요청을 두 번 하지 않으려고 한 모델이다. */
data class TeamDetail(
    val team: TeamRef,
    val nameEn: String?,                 // "Doosan Bears"
    val stadium: String?, val manager: String?,
    val history: List<TeamHistoryEntry>,
    val pitchers: List<RosterPlayer>, val batters: List<RosterPlayer>,
    val recent: List<GameSummary>, val upcoming: List<GameSummary>,
)

// ── 선수 ──
data class PlayerProfile(
    val name: String, val number: Int?, val photoUrl: String?,
    val position: String?,                         // "포수" — 원문 그대로
    val bats: String?,                             // "우투우타"
    val birthDay: LocalDate?, val heightCm: Int?, val weightKg: Int?,
    val school: String?, val joinYear: Int?, val draft: String?,
    val signingBonus: String?, val salary: String?, val nationality: String?,
)

/** month = null 이면 그 달이 아니라 **시즌 합계**(서버의 `"13"`). */
data class BattingRow(val month: Int?, val avg: String, val games: Int?, val atBats: Int?,
                      val hits: Int?, val homeRuns: Int?, val rbi: Int?)
data class PitchingRow(val month: Int?, val era: String, val wins: Int?, val losses: Int?,
                       val saves: Int?, val holds: Int?, val innings: String?, val strikeOuts: Int?)

/** 최근 경기 한 줄. `cumulative*` 는 그 경기 성적이 아니라 **그 시점 누적값**이다. 전 필드 null인 행이 섞인다. */
data class BattingGame(val date: LocalDate?, val opponent: String, val order: String?,
                       val atBats: Int?, val hits: Int?, val homeRuns: Int?, val rbi: Int?,
                       val cumulativeAvg: String?)
data class PitchingGame(val date: LocalDate?, val opponent: String, val innings: String?,
                        val pitches: Int?, val hits: Int?, val strikeOuts: Int?,
                        val cumulativeEra: String?)

/** 한 라우트가 포지션에 따라 다른 표를 준다 — sealed로 갈라 두면 화면이 섞어 쓸 수 없다. */
sealed interface PlayerRecord {
    data class Batting(val months: List<BattingRow>, val recent: List<BattingGame>) : PlayerRecord
    data class Pitching(val months: List<PitchingRow>, val recent: List<PitchingGame>) : PlayerRecord
}

data class PlayerDetail(val profile: PlayerProfile, val record: PlayerRecord)
```

<div class="callout tip"><span class="t">왜 <code>PlayerRecord</code>만 sealed인가</span>
<code>/extra/Player_Info</code>는 라우트가 하나인데 <code>c_position</code>이 <code>"투수"</code>면 승·패·세·홀·이닝·ERA를, 아니면 타율·타수·안타·홈런·타점을 줍니다. <strong>같은 키가 다른 뜻인 칸도 있습니다</strong> — 투수의 <code>h</code>는 피안타, 타자의 <code>h</code>는 안타입니다. 하나의 넓적한 data class에 전부 nullable로 담으면 화면에서 투수 표에 타율을 그리는 실수가 컴파일을 통과합니다. sealed로 갈라 두면 <code>when</code>이 강제되고, 표 두 벌을 만드는 것이 설계상 당연해집니다.
</div>

<div class="callout tip"><span class="t">상태 enum에 <code>POSTPONED</code>·<code>SUSPENDED</code>가 남아 있는 이유</span>
wisetoto의 <code>state</code>는 <code>a</code>(예정)·<code>i</code>(진행 중)·<code>e</code>(종료)·<code>c</code>(취소) 네 값이 관측됐고 연기·서스펜디드를 따로 구분하지 않습니다(우천 취소도 <code>c</code>). 두 값은 지금 매핑되지 않지만 목록 화면의 "취소·연기" 섹션이 이미 쓰고 있어 그대로 둡니다. 표본이 잡히면 매퍼만 고치면 됩니다.
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
    val state: String? = null,                                         // a / i / e / c
    val inning: String? = null,                                        // "bs9_1" = 9회초
    @SerialName("stadium_name") val stadiumName: String? = null,
    @SerialName("home_team_info_seq") val homeTeamSeq: String,
    @SerialName("home_team_name") val homeTeamName: String? = null,
    @SerialName("away_team_info_seq") val awayTeamSeq: String,
    @SerialName("away_team_name") val awayTeamName: String? = null,
    @SerialName("home_score") val homeScore: String? = null,           // 문자열! 취소 경기는 null
    @SerialName("away_score") val awayScore: String? = null,
    @SerialName("home_pitcher") val homePitcher: String? = null,       // 선발 — 당일 Schedule_Day에만 (미래 날짜는 null)
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

// ── 팀 /extra/Team_Info?team_info_seq=&player_position= ──
@Serializable data class TeamInfoEnvelopeDto(@SerialName("team_info") val teamInfo: TeamInfoDto? = null)
@Serializable data class TeamInfoDto(
    @SerialName("team_detail") val detail: TeamDetailDto? = null,
    @SerialName("player_list") val players: List<RosterPlayerDto> = emptyList(),   // player_position이 가른다
)
@Serializable data class TeamDetailDto(
    val name: String? = null,
    @SerialName("en_simple_name") val nameEn: String? = null,          // "Doosan Bears"
    @SerialName("stadium_name") val stadiumName: String? = null,
    val director: String? = null,                                      // 감독
    @SerialName("team_history") val history: List<String> = emptyList(),  // "1982년 l \"OB 베어스\" 창단"
)
@Serializable data class RosterPlayerDto(
    val seq: String,                                                   // = player_info_seq
    val name: String,
    @SerialName("c_number") val number: String? = null,                 // 문자열! 팀 안에서 겹칠 수 있다
    val img: String? = null,                                           // http:// 로 온다
)

// ── 선수 /extra/Player_Info/{seq} ──
@Serializable data class PlayerInfoEnvelopeDto(@SerialName("player_info") val info: PlayerInfoDto? = null)
@Serializable data class PlayerInfoDto(
    @SerialName("player_detail") val detail: PlayerProfileDto? = null,
    val record: PlayerRecordDto = PlayerRecordDto(),
)
@Serializable data class PlayerProfileDto(
    val name: String? = null,
    @SerialName("c_position") val position: String? = null,   // 투수/포수/내야수/외야수 — record 스키마를 가른다
    @SerialName("p_position") val bats: String? = null,       // "우투우타"
    @SerialName("img_s") val photo: String? = null,           // http://
    @SerialName("c_number") val number: String? = null,
    @SerialName("birth_day") val birthDay: String? = null,    // "1987-06-05"
    val height: String? = null, val weight: String? = null,
    val school: String? = null, val national: String? = null,
    @SerialName("join_year") val joinYear: String? = null,
    @SerialName("n_ranking") val draft: String? = null,       // "06 두산 2차 8라운드 59순위" / "18 두산 1차" — 형식 제각각
    @SerialName("join_down_payment") val signingBonus: String? = null,   // "30000만원" = 만원 단위
    val income: String? = null,                                          // "420000만원"
)

/** 투수·타자 두 스키마를 한 DTO로 받는다(없는 칸은 null). 가르는 건 매퍼의 일이다. */
@Serializable data class PlayerRecordDto(
    val month: List<PlayerMonthDto> = emptyList(),
    val previous5: List<PlayerGameDto> = emptyList(),
)
@Serializable data class PlayerMonthDto(
    val month: String? = null,          // "3".."11" … 그리고 "13" = 시즌 합계 (13월이 아니다)
    val games: String? = null,
    // 타자
    val avg: String? = null, val ab: String? = null, val rbi: String? = null,
    // 투수
    val era: String? = null, val win: String? = null, val lose: String? = null,
    val save: String? = null, val hold: String? = null,
    val inning: String? = null,         // "29 2/3" — 대분수 문자열
    // 양쪽에 있으나 뜻이 다르다: 타자 h=안타·hr=홈런, 투수 h=피안타·hr=피홈런
    val h: String? = null, val hr: String? = null, val so: String? = null,
)
@Serializable data class PlayerGameDto(
    @SerialName("game_date") val date: String? = null,        // "20260917"
    @SerialName("matchteamname") val opponent: String? = null,
    // 타자
    val bo: String? = null, val ab: String? = null, val rbi: String? = null, val avg: String? = null,
    // 투수
    val ip: String? = null,             // "0.2" — 소수점 뒤는 10분의 1이 아니라 아웃 카운트
    val np: String? = null, val era: String? = null,
    val h: String? = null, val hr: String? = null, val so: String? = null,
)

// ── 앱 부트스트랩 /extra/notice ──
@Serializable data class NoticeDto(
    val server: NextActionDto? = null,     // 서버 차단 신호
    val update: NextActionDto? = null,     // 강제 업데이트 신호
)
@Serializable data class NextActionDto(
    @SerialName("next_action") val nextAction: String? = null,   // 평소엔 빈 문자열
)
```

<div class="callout warn"><span class="t">이 두 DTO는 <code>null</code>투성이가 정상이다</span>
<code>PlayerMonthDto</code>·<code>PlayerGameDto</code>는 실제로 절반쯤 <code>null</code>로 옵니다 — 타자를 받으면 <code>era</code>·<code>win</code> 칸이 없고, 투수를 받으면 <code>avg</code>·<code>ab</code> 칸이 없습니다. 게다가 <strong>모든 칸이 <code>null</code>인 행</strong>도 섞입니다(곽빈 8/22 롯데전 — 날짜·상대만 있고 기록이 없음). 그래서 <code>Json</code>의 <code>explicitNulls = false</code>와 전 필드 기본값이 필수입니다. 이 <code>null</code>들을 <code>0</code>으로 메우지 마세요 — 화면은 <code>—</code>로 그려야 합니다.
</div>

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

    /**
     * 구단 정보(정식 명칭·홈구장·감독·연혁) + 선수단.
     * position: 0 = 투수, 1 = 타자. **생략하면 투수만 온다** — 선수단 전체를 보려면 두 번 부른다. 서버 캐시 1시간.
     */
    @GET("extra/Team_Info")
    suspend fun teamInfo(
        @Query("team_info_seq") teamId: Long,
        @Query("player_position") position: Int,
    ): Envelope<TeamInfoEnvelopeDto>

    /** 선수 프로필 + 월별·최근 5경기 기록. `c_position`에 따라 `record` 스키마가 갈린다. 서버 캐시 1시간. */
    @GET("extra/Player_Info/{seq}")
    suspend fun playerInfo(@Path("seq") playerId: Long): Envelope<PlayerInfoEnvelopeDto>

    /** 앱 부트스트랩 — 강제 업데이트·차단 신호. 시작할 때 한 번만 부른다. */
    @GET("extra/notice")
    suspend fun notice(): Envelope<NoticeDto>
}

class WisetotoException(val code: String?, message: String?) : RuntimeException("[$code] $message")

/** 봉투를 벗긴다. code "00"이 아니면 예외 — HTTP 200에 오류가 실려 오기 때문에 여기서 걸러야 한다. */
fun <T> Envelope<T>.body(): T =
    if (code == "00" && data != null) data else throw WisetotoException(code, message)
```

`data/remote/di/NetworkModule.kt` — OkHttp + Retrofit 3 + kotlinx.serialization. **`os=a&version=4.1.3&lang=kr` 세 키 중 하나라도 없으면 모든 경로가 `01 잘못된 접근`** 이므로 인터셉터가 항상 붙입니다.

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
import java.util.concurrent.TimeUnit
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
        .callTimeout(10, TimeUnit.SECONDS)      // 폴링이 응답 없는 요청에 매달리지 않게 (계획서 §5.2)
        .connectTimeout(5, TimeUnit.SECONDS)
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

<div class="callout warn"><span class="t"><code>extra/notice</code>는 시작할 때 한 번 — 차단 신호를 무시하지 않는다</span>
계획서 <code>DS-003</code>입니다. <code>update.next_action</code>·<code>server.next_action</code>은 평소 빈 문자열이고(2026-09-20 실측), 값이 채워지면 강제 업데이트 또는 차단 신호입니다. 앱 시작 시 한 번 불러 <strong>비어 있지 않으면 폴링을 멈추고 안내를 띄웁니다</strong>. 서비스가 게이팅을 시작해도 우회 수단을 만들지 않는 것이 이 앱의 방침입니다(개인용 범위).
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

/** a/i/e/c는 2026-09-15 실측. 그 외 값은 UNKNOWN — 화면은 원문 state를 라벨로 보여준다. */
fun mapStatus(state: String?): GameStatus = when (state) {
    "a" -> GameStatus.SCHEDULED
    "i" -> GameStatus.LIVE
    "e" -> GameStatus.FINAL
    "c" -> GameStatus.CANCELED
    else -> GameStatus.UNKNOWN
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

/**
 * 함정 7: 시작 시각은 timestamp 우선. Schedule_Month엔 timestamp가 없어 `game_date` 문자열을 파싱하는데,
 * 형식이 어긋난 행 하나가 예외를 던지면 그 달 프리페치가 통째로 끊긴다 → 파싱 실패는 여기서 삼키고 null을 준다.
 */
private fun ScheduleGameDto.startInstant(): Instant? =
    gameTimestamp?.let(Instant::ofEpochSecond)
        ?: runCatching { LocalDateTime.parse(gameDate, apiDateTime).atZone(SEOUL).toInstant() }.getOrNull()

/** 함정 8: 목록엔 WBC·시범경기·올스타전이 섞여 있다. 양 팀이 KBO 10구단이고 시즌 시작일 이후인 행만 KBO 정규 경기다. */
fun ScheduleGameDto.isKboRegular(seasonStart: LocalDate?): Boolean {
    if (homeTeamSeq.toLongOrNull() !in KBO_TEAMS || awayTeamSeq.toLongOrNull() !in KBO_TEAMS) return false
    val date = startInstant()?.atZone(SEOUL)?.toLocalDate() ?: return false   // 시작 시각을 못 읽는 행은 여기서 버린다
    return seasonStart == null || !date.isBefore(seasonStart)   // 시범경기(3/12~3/24)는 여기서 빠진다
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
    val st = mapStatus(state)
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
        finalInning = inningNumber(inning),
        venueShort = KBO_TEAMS[home.id]?.home,                      // 함정 6: 구장명은 앱 표에서
        homeStarter = homeStarter, awayStarter = awayStarter,
    )
}

fun ScheduleGameDto.toSummary(): GameSummary = buildSummary(
    id = seq.toLong(),
    startsAt = startInstant()                                      // 함정 7: 표시용 game_date보다 timestamp 우선
        ?: error("시작 시각이 없는 행: seq=$seq"),                   // isKboRegular가 먼저 걸러 주므로 정상 경로엔 오지 않는다
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

// ───────────────────────── 팀 정보 ─────────────────────────

/** 이미지 URL이 전부 `http://`로 온다. Android는 기본(`usesCleartextTraffic=false`)에서 이걸 차단한다. */
fun String.toHttps(): String = if (startsWith("http://")) "https://" + removePrefix("http://") else this

/** 함정 9: 등번호 100 이상 = 육성선수. 서버가 주지 않는 **앱 규칙**이므로 상수로 드러내 둔다. */
private const val DEVELOPMENT_NUMBER_FROM = 100

fun RosterPlayerDto.toDomain() = RosterPlayer(
    id = seq.toLong(),                                   // 키는 seq다 — 등번호가 아니다
    name = name,
    number = number?.toIntOrNull(),                      // 문자열이라 그냥 정렬하면 1, 10, 101, 11 …
    photoUrl = img?.toHttps(),
    isDevelopment = (number?.toIntOrNull() ?: 0) >= DEVELOPMENT_NUMBER_FROM,
)

/** 등번호 오름차순. 번호가 겹쳐도(두산 48번 2명) 이름으로 안정 정렬할 뿐 합치지 않는다. */
fun List<RosterPlayerDto>.toRoster(): List<RosterPlayer> =
    map { it.toDomain() }.sortedWith(compareBy({ it.number ?: Int.MAX_VALUE }, { it.name }))

/** 함정 9: 연혁 구분자는 파이프(`|`)가 아니라 **소문자 `l`** 이다. `"1982년 l \"OB 베어스\" 창단"`. */
fun String.toHistoryEntry(): TeamHistoryEntry {
    val parts = trim().split(" l ", limit = 2)
    return if (parts.size == 1) TeamHistoryEntry(null, parts[0])
           else TeamHistoryEntry(parts[0].removeSuffix("년").toIntOrNull(), parts[1].trim())
}

// ───────────────────────── 선수 정보 ─────────────────────────

private val FRACTION = mapOf(0 to "", 1 to "⅓", 2 to "⅔")

/** 함정 11-①: 월별 `inning`은 `"29 2/3"` 같은 **대분수 문자열**이다. */
fun inningsFromMixed(raw: String?): String? {
    val s = raw?.trim().orEmpty()
    if (s.isEmpty()) return null
    val whole = s.substringBefore(' ')
    val outs = when (s.substringAfter(' ', "")) { "1/3" -> 1; "2/3" -> 2; else -> 0 }
    return whole + FRACTION.getValue(outs)
}

/** 함정 11-②: 최근 경기 `ip`는 `"0.2"` — 소수점 뒤가 **아웃 카운트**다. 0.2는 0.2이닝이 아니라 ⅔이닝. */
fun inningsFromIp(raw: String?): String? {
    if (raw.isNullOrBlank()) return null                     // 기록 없이 로그만 오는 행은 여기서 걸린다(함정 12)
    val whole = raw.substringBefore('.').toIntOrNull() ?: return null
    val frac = FRACTION.getValue(raw.substringAfter('.', "0").toIntOrNull()?.coerceIn(0, 2) ?: 0)
    return when {
        whole > 0          -> "$whole$frac"
        frac.isNotEmpty()  -> frac
        else               -> "0"
    }
}

/** 함정 10: `month:"13"`은 13월이 아니라 시즌 합계다. 합계 행은 `null`로 표시해 UI가 따로 그린다. */
private fun monthOrTotal(raw: String?): Int? = raw?.toIntOrNull()?.takeIf { it in 1..12 }

private fun gameDate(raw: String?): LocalDate? =
    raw?.let { runCatching { LocalDate.parse(it, apiDay) }.getOrNull() }   // "20260917"

/** 금액은 만원 단위 문자열로 온다 — `"30000만원"` → `"3억원"`. 표시 규칙이므로 값은 그대로 보존한다. */
fun String.toWon(): String {
    val man = removeSuffix("만원").trim().toLongOrNull() ?: return this
    val (eok, rest) = man / 10_000 to man % 10_000
    return when {
        eok > 0 && rest > 0 -> "${eok}억 ${rest}만원"
        eok > 0             -> "${eok}억원"
        else                -> "${man}만원"
    }
}

fun PlayerMonthDto.toBattingRow() = BattingRow(
    month = monthOrTotal(month), avg = avg.orEmpty(), games = games.toRuns(),
    atBats = ab.toRuns(), hits = h.toRuns(), homeRuns = hr.toRuns(), rbi = rbi.toRuns())

fun PlayerMonthDto.toPitchingRow() = PitchingRow(
    month = monthOrTotal(month), era = era.orEmpty(),
    wins = win.toRuns(), losses = lose.toRuns(), saves = save.toRuns(), holds = hold.toRuns(),
    innings = inningsFromMixed(inning), strikeOuts = so.toRuns())

fun PlayerGameDto.toBattingGame() = BattingGame(
    date = gameDate(date), opponent = opponent.orEmpty(), order = bo?.takeIf { it != "-" },
    atBats = ab.toRuns(), hits = h.toRuns(), homeRuns = hr.toRuns(), rbi = rbi.toRuns(),
    cumulativeAvg = avg)                                        // 함정 12: 그 경기 타율이 아니라 누적

fun PlayerGameDto.toPitchingGame() = PitchingGame(
    date = gameDate(date), opponent = opponent.orEmpty(), innings = inningsFromIp(ip),
    pitches = np.toRuns(), hits = h.toRuns(), strikeOuts = so.toRuns(),
    cumulativeEra = era)                                        // 함정 12: 누적 ERA

fun PlayerInfoDto.toDetail(): PlayerDetail? {
    val d = detail ?: return null
    return PlayerDetail(
        profile = PlayerProfile(
            name = d.name.orEmpty(), number = d.number?.toIntOrNull(),
            photoUrl = d.photo?.toHttps(), position = d.position, bats = d.bats,
            birthDay = d.birthDay?.let { runCatching { LocalDate.parse(it) }.getOrNull() },
            heightCm = d.height?.toIntOrNull(), weightKg = d.weight?.toIntOrNull(),
            school = d.school, joinYear = d.joinYear?.toIntOrNull(), draft = d.draft,
            signingBonus = d.signingBonus?.toWon(), salary = d.income?.toWon(),
            nationality = d.national,
        ),
        // 포수·내야수·외야수는 전부 타자 스키마다. 합계 행(month = null)은 항상 끝으로 — 서버도 끝에 주지만 의존하지 않는다.
        record = if (d.position == "투수") PlayerRecord.Pitching(
            months = record.month.map { it.toPitchingRow() }.sortedBy { it.month ?: Int.MAX_VALUE },
            recent = record.previous5.map { it.toPitchingGame() },
        ) else PlayerRecord.Batting(
            months = record.month.map { it.toBattingRow() }.sortedBy { it.month ?: Int.MAX_VALUE },
            recent = record.previous5.map { it.toBattingGame() },
        ),
    )
}
```

<div class="callout warn"><span class="t">합계 행을 월 합으로 만들거나 검증하지 말 것</span>
<code>month:"13"</code> 행은 월별 행의 합이 <strong>아닙니다</strong>. 양의지의 월별 경기 수를 더하면 130인데 합계 행은 123이고, 곽빈의 월별 이닝 합은 159⅔인데 합계는 155입니다(2026-09-18 실측 — 시즌 중이라 숫자 자체는 날마다 오릅니다. 변하지 않는 것은 <strong>둘이 다르다</strong>는 사실입니다). 어느 쪽이 맞는지는 서버만 알고 있으므로 <strong>합계는 합계 행을 그대로 쓰고, 월별은 월별대로 그립니다.</strong> 앱에서 더해 만들면 화면마다 다른 숫자가 나옵니다.
</div>

<div class="callout danger"><span class="t">함정 12개 — 이 파일이 막는 것</span>
<strong>경기·순위</strong>
① 경로 대소문자·<code>yyyyMMdd</code> 형식·<code>os/version/lang</code> 세 키 필수(API 인터페이스·인터셉터)
② 점수·순위가 <strong>문자열</strong>(<code>toRuns</code>)
③ <code>state:"c"</code>인데 노게임 부분 점수가 남아 있음(<code>buildSummary</code>)
④ <code>game_result</code>가 진행 중엔 이닝 라벨·종료 후엔 w/l/d라 승패는 총점 비교로(<code>buildSummary</code>)
⑤ 라인스코어 15칸 고정, <code>null</code>과 <code>0</code> 구분(<code>parseInnings</code>)
⑥ 구장명 표기 비정규 — 같은 달 안에서도 흔들림(앱 표 사용)
⑦ <code>game_date</code>는 표시 문자열, 변경 감지 필드 없음(<code>game_timestamp</code> 사용, 쓰기 스킵은 Step 4)
⑧ 목록에 WBC·시범경기·올스타전이 섞여 있음(<code>isKboRegular</code>)
<br><strong>팀·선수</strong>
⑨ 선수단은 <code>player_position</code>으로 <strong>두 번</strong> 불러야 하고, 목록에 포지션이 없고, <strong>등번호가 겹치며</strong>(키는 <code>seq</code>), 연혁 구분자가 소문자 <code>l</code>이고, 사진이 <code>http://</code>다(<code>toRoster</code>·<code>toHistoryEntry</code>·<code>toHttps</code>)
⑩ <code>c_position</code>에 따라 <code>record</code> 스키마가 통째로 갈리고, <code>month:"13"</code>이 시즌 합계로 섞여 오며, 합계는 월 합과 다르다(<code>PlayerRecord</code>·<code>monthOrTotal</code>)
⑪ 이닝 표기가 두 가지 — 월별 <code>"29 2/3"</code>(대분수), 최근 경기 <code>ip:"0.2"</code>(아웃 카운트)(<code>inningsFromMixed</code>·<code>inningsFromIp</code>)
⑫ 최근 경기의 <code>era</code>·<code>avg</code>는 그 경기가 아니라 <strong>누적값</strong>이고, 전 필드가 <code>null</code>인 행이 섞인다(<code>cumulative*</code>·nullable 유지)
</div>

## 5. fixture 옮기고 매퍼 테스트

Step 1에서 받은 JSON을 테스트 리소스로 옮깁니다.

```bash
mkdir -p app/src/test/resources/fixtures
cp fixtures/*.json app/src/test/resources/fixtures/
```

`app/src/test/java/com/diamondscore/data/remote/mapper/MapperTest.kt` — 함정을 각각 검증합니다. `@Test`는 **`org.junit.Test`** 로 가져옵니다 — kotlin-test의 JVM 아티팩트에는 `Test` 애너테이션이 들어 있지 않고(테스트 프레임워크 variant 선택에 달려 있어 AGP 9 환경에서 보장되지 않습니다), Step 4의 `RepositoryTest`도 같은 방식입니다. Step 2에서 넣은 `testImplementation(libs.kotlin.test)`에서는 `assertEquals`·`assertFailsWith`·`assertIs` 같은 **단언 함수만** 개별 import 합니다(`import kotlin.test.*` 는 쓰지 않습니다).

```kotlin
package com.diamondscore.data.remote.mapper

import com.diamondscore.data.remote.*          // WisetotoException, Envelope.body()
import com.diamondscore.data.remote.dto.*
import com.diamondscore.domain.model.*
import kotlinx.serialization.decodeFromString   // json.decodeFromString<T>(String)은 StringFormat 확장
import kotlinx.serialization.json.Json
import org.junit.Test                            // kotlin-test JVM 아티팩트에는 Test가 없다 — Step 4와 같게 JUnit4
import java.time.LocalDate
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertIs
import kotlin.test.assertNotEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class MapperTest {
    private val json = Json { ignoreUnknownKeys = true; coerceInputValues = true; explicitNulls = false }   // §3의 설정 그대로
    private fun load(name: String) = javaClass.classLoader!!.getResourceAsStream("fixtures/$name")!!.bufferedReader().readText()
    private fun day(name: String) = json.decodeFromString<Envelope<ScheduleDayDto>>(load(name)).body().games
    private fun game(name: String) = json.decodeFromString<Envelope<GameDetailEnvelopeDto>>(load(name)).body().detail!!

    @Test fun `문자열 점수를 숫자로`() {                                                  // 함정 2
        val g = day("schedule_day_finished.json").first().toSummary()
        assertEquals(GameStatus.FINAL, g.status); assertNotNull(g.homeRuns); assertNotNull(g.awayRuns)
        assertNotNull(g.homeStarter)                                   // 경기일 목록에는 선발이 채워져 있다
    }

    @Test fun `취소 경기는 점수가 null`() {                                                // 함정 3
        day("schedule_day_canceled.json").map { it.toSummary() }.forEach {
            assertEquals(GameStatus.CANCELED, it.status); assertNull(it.homeRuns); assertNull(it.awayRuns)
        }
    }

    @Test fun `예정 경기는 선발투수가 있고 점수는 null`() {
        val g = day("schedule_day_scheduled.json").first().toSummary()
        assertEquals(GameStatus.SCHEDULED, g.status); assertNull(g.homeRuns)
        assertNotNull(g.homeStarter)   // 선발은 당일 목록에만 채워진다(미래 날짜 fixture면 이 줄을 지운다)
    }

    @Test fun `연장 11회가 라인스코어에 나온다`() {                                        // 함정 5
        val d = game("game_extra.json").toDetail()
        assertEquals(11, d.innings.size); assertTrue(d.summary.wentExtra)
        assertEquals(11, d.summary.finalInning)                                              // "연장 11회" 표기용
        assertEquals(d.summary.homeRuns, d.innings.sumOf { it.home ?: 0 })                   // 이닝 합 = 총점
    }

    @Test fun `9회말 미실시는 null이고 0점은 0이다`() {                                   // 함정 5
        val d = game("game_final.json").toDetail()   // 홈 승 → bs9_1, 9회말 없음
        assertNull(d.innings.last().home); assertEquals(0, d.innings.first { it.home == 0 }.home)
    }

    @Test fun `state 매핑과 이닝 라벨`() {                                                   // 함정 4
        assertEquals(GameStatus.LIVE, mapStatus("i"))
        assertEquals(GameStatus.UNKNOWN, mapStatus("zzz"))
        assertEquals("1회초", inningLabel("bs1_1"))
        assertEquals("7회말", inningLabel("bs7_2"))
    }

    /** 라이브 fixture는 경기일에만 받을 수 있는 선택 항목 — 없으면 이 테스트만 조용히 건너뛴다. */
    @Test fun `진행 중 경기는 이닝 라벨이 그대로 상태가 된다`() {                            // 함정 4
        javaClass.classLoader!!.getResource("fixtures/schedule_day_live.json") ?: return
        val live = day("schedule_day_live.json").map { it.toSummary() }
            .firstOrNull { it.status == GameStatus.LIVE } ?: return       // 캡처 시점에 진행 중 경기가 없었을 수 있다
        assertTrue(Regex("""\d+회(초|말)""").matches(live.statusLabel))   // 몇 회인지는 캡처 시각에 달렸다
        assertNotNull(live.homeRuns)                                      // 진행 중이면 0점이라도 값이 있다
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
        // 오류 봉투의 data는 빈 객체 {} 다 — []로 쓰면 body() 전에 역직렬화가 먼저 터진다
        val env = json.decodeFromString<Envelope<ScheduleDayDto>>("""{"result":"success","code":"01","message":"잘못된 접근","data":{}}""")
        assertFailsWith<WisetotoException> { env.body() }
    }

    // ── 팀·선수 (함정 9~12) ──

    private fun team(name: String) =
        json.decodeFromString<Envelope<TeamInfoEnvelopeDto>>(load(name)).body().teamInfo!!
    private fun player(name: String) =
        json.decodeFromString<Envelope<PlayerInfoEnvelopeDto>>(load(name)).body().info!!.toDetail()!!

    @Test fun `선수단은 투수와 타자가 따로 오고 서로 겹치지 않는다`() {                    // 함정 9
        val pitchers = team("team_info_pitchers.json").players.toRoster()
        val batters  = team("team_info_batters.json").players.toRoster()
        assertTrue(pitchers.isNotEmpty() && batters.isNotEmpty())
        assertTrue((pitchers.map { it.id }.toSet() intersect batters.map { it.id }.toSet()).isEmpty())
    }

    @Test fun `등번호는 키가 아니고 숫자로 정렬된다`() {                                    // 함정 9
        val p = team("team_info_pitchers.json").players.toRoster()
        val numbers = p.map { it.number ?: Int.MAX_VALUE }
        assertEquals(numbers.sorted(), numbers)                        // 사전순이 아니라 숫자순
        assertTrue(p.size > p.mapNotNull { it.number }.distinct().size) // 두산 48번이 둘 — 번호는 안 유일
        assertEquals(p.size, p.map { it.id }.distinct().size)          // seq는 유일
        assertTrue(p.filter { it.isDevelopment }.all { (it.number ?: 0) >= 100 })
    }

    @Test fun `연혁 구분자는 파이프가 아니라 소문자 l 이다`() {                             // 함정 9
        val h = team("team_info_pitchers.json").detail!!.history.map { it.toHistoryEntry() }
        assertEquals(1982, h.first().year)                             // "1982년 l …"
        assertTrue(h.all { it.year != null })                          // 전 행이 같은 형식
        assertTrue(h.none { it.text.startsWith("l ") })                // 구분자가 본문에 남지 않았다
    }

    @Test fun `사진 URL은 https로 승격된다`() {                                            // 함정 9
        val p = team("team_info_pitchers.json").players.toRoster()
        assertTrue(p.mapNotNull { it.photoUrl }.isNotEmpty())
        assertTrue(p.mapNotNull { it.photoUrl }.all { it.startsWith("https://") })
    }

    @Test fun `포지션이 record 스키마를 가른다`() {                                        // 함정 10
        assertIs<PlayerRecord.Batting>(player("player_batter.json").record)    // 양의지 = 포수
        assertIs<PlayerRecord.Pitching>(player("player_pitcher.json").record)  // 곽빈 = 투수
    }

    @Test fun `month 13은 월이 아니라 시즌 합계이고 월 합과 다르다`() {                     // 함정 10
        val r = player("player_batter.json").record as PlayerRecord.Batting
        assertNull(r.months.last().month)                              // 합계는 항상 끝
        assertTrue(r.months.dropLast(1).all { it.month in 3..11 })      // 나머지는 실제 월
        assertNotNull(r.months.last().games)
        assertNotEquals(r.months.dropLast(1).sumOf { it.games ?: 0 }, r.months.last().games)   // 합계 행 ≠ 월 합
    }

    @Test fun `이닝 표기 두 가지를 각각 해석한다`() {                                       // 함정 11
        assertEquals("29⅔", inningsFromMixed("29 2/3"))
        assertEquals("8", inningsFromMixed("8"))
        assertEquals("⅔", inningsFromIp("0.2"))                        // 0.2이닝이 아니다
        assertEquals("7", inningsFromIp("7.0"))
        assertEquals("1⅓", inningsFromIp("1.1"))
    }

    @Test fun `최근 경기의 ERA는 누적이고 기록이 통째로 빈 행이 섞인다`() {                  // 함정 12
        val r = player("player_pitcher.json").record as PlayerRecord.Pitching
        assertEquals(5, r.recent.size)
        // 가장 최근 경기의 "누적 ERA" = 시즌 합계 ERA → 그 경기 성적이 아님이 증명된다
        assertEquals(r.months.last().era, r.recent.first().cumulativeEra)
        val blank = r.recent.last()                                    // 8/22 롯데 — 날짜·상대만 옴
        assertNotNull(blank.date); assertEquals("롯데", blank.opponent)
        assertNull(blank.innings); assertNull(blank.strikeOuts); assertNull(blank.pitches)
    }

    @Test fun `금액은 만원 단위 문자열이다`() {
        assertEquals("3억원", "30000만원".toWon())
        assertEquals("42억원", "420000만원".toWon())
        assertEquals("3억 500만원", "30500만원".toWon())
        assertEquals("3000만원", "3000만원".toWon())
    }
}
```

```bash
./gradlew :app:testDebugUnitTest
```

<div class="checkpoint"><span class="t"></span> 테스트가 초록불이면 완료. 특히 <strong>연장 경기에서 10·11회 득점이 라인스코어에 나타나는지</strong>, <strong>취소 경기의 부분 점수가 사라지는지</strong>, <strong>투수/타자 record가 섞이지 않는지</strong>가 이 앱에서 가장 자주 깨지는 부분이니 반드시 통과시키세요. <code>load("…")</code>의 파일 이름은 Step 1에서 저장한 이름과 정확히 같아야 합니다 — 라이브 캡처(<code>schedule_day_live.json</code>)만 선택이라, 없으면 그 테스트 하나만 건너뜁니다.</div>

<div class="pager">
<a href="#/labs/step-2">← Step 2</a>
<a href="#/labs/step-4">Step 4 · Room·프리페치 →</a>
</div>
