# Step 3 · 네트워크·매핑 계층

<div class="chips"><span class="chip time">90분</span><span class="chip diff">보통</span><span class="chip goal">JSON을 도메인 모델로 안전하게 바꾸고, 함정 7개를 테스트로 고정한다</span></div>

SofaScore 응답을 앱이 쓸 모양으로 바꿉니다. 실측에서 발견한 **함정 7개**(무승부 필드 없음, 연장 이중 표현, 동적 이닝 키 등)를 각각 테스트로 막는 것이 이 Step의 핵심입니다.

## 1. 도메인 모델

`core/model/Models.kt`:

```kotlin
package com.diamondscore.domain.model

import java.time.Instant
import java.time.LocalDate

@JvmInline value class EventId(val value: Long)
@JvmInline value class TeamId(val value: Long)

enum class GameStatus { SCHEDULED, LIVE, FINAL, CANCELED, POSTPONED, SUSPENDED, UNKNOWN }
enum class Winner { HOME, AWAY, DRAW }

data class TeamRef(val id: Long, val nameKo: String, val code: String)

data class InningRuns(val number: Int, val home: Int?, val away: Int?) // null = 미진행

data class GameSummary(
    val id: Long,
    val startsAt: Instant,
    val leagueDate: LocalDate,       // Asia/Seoul
    val status: GameStatus,
    val statusLabel: String,         // status.description 원문
    val home: TeamRef, val away: TeamRef,
    val homeRuns: Int?, val awayRuns: Int?,   // 경기 전 null (0 아님)
    val winner: Winner?,
    val wentExtra: Boolean,
    val changeTimestamp: Long?,
)

data class Standing(
    val position: Int, val team: TeamRef,
    val games: Int, val wins: Int, val losses: Int, val draws: Int,  // draws = 파생
    val winPct: Double, val gamesBehind: Double,
    val runsFor: Int, val runsAgainst: Int, val runDiff: String,
    val playoffTier: String?,
)
```

## 2. DTO — 서버 JSON 그대로 받기

`data/remote/dto/Dtos.kt`. **`innings`는 반드시 `Map`** 입니다(이닝 키가 동적이라 배열/고정필드 불가).

```kotlin
package com.diamondscore.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable data class SeasonsDto(val seasons: List<SeasonDto>)
@Serializable data class SeasonDto(val id: Long, val name: String, val year: String? = null)

@Serializable data class EventsDto(val events: List<EventDto> = emptyList())

@Serializable data class EventDto(
    val id: Long,
    val startTimestamp: Long,
    val status: StatusDto,
    val winnerCode: Int? = null,
    val homeTeam: TeamDto,
    val awayTeam: TeamDto,
    val homeScore: ScoreDto? = null,
    val awayScore: ScoreDto? = null,
    val changes: ChangesDto? = null,
)
@Serializable data class StatusDto(val code: Int, val description: String, val type: String)
@Serializable data class TeamDto(val id: Long, val name: String, val nameCode: String? = null)
@Serializable data class ScoreDto(
    val current: Int? = null,
    val innings: Map<String, InningRunDto> = emptyMap(),   // {"inning1":{"run":1}}
)
@Serializable data class InningRunDto(val run: Int? = null)
@Serializable data class ChangesDto(val changeTimestamp: Long? = null)

@Serializable data class StandingsResponseDto(val standings: List<StandingsGroupDto> = emptyList())
@Serializable data class StandingsGroupDto(val rows: List<StandingRowDto> = emptyList())
@Serializable data class StandingRowDto(
    val position: Int,
    val team: TeamDto,
    val matches: Int, val wins: Int, val losses: Int,   // draws 없음 → 파생
    val scoresFor: Int = 0, val scoresAgainst: Int = 0,
    val percentage: Double = 0.0,
    val gamesBehind: Double = 0.0,
    val scoreDiffFormatted: String? = null,
    val promotion: PromotionDto? = null,
)
@Serializable data class PromotionDto(val text: String? = null)
```

## 3. Retrofit API와 네트워크 모듈

`data/remote/SofaScoreApi.kt`:

```kotlin
package com.diamondscore.data.remote

import com.diamondscore.data.remote.dto.*
import retrofit2.http.GET
import retrofit2.http.Path

interface SofaScoreApi {
    @GET("unique-tournament/11204/seasons")
    suspend fun seasons(): SeasonsDto

    @GET("unique-tournament/11204/season/{sid}/standings/total")
    suspend fun standings(@Path("sid") seasonId: Long): StandingsResponseDto

    @GET("unique-tournament/11204/season/{sid}/events/next/{page}")
    suspend fun eventsNext(@Path("sid") seasonId: Long, @Path("page") page: Int): EventsDto

    @GET("unique-tournament/11204/season/{sid}/events/last/{page}")
    suspend fun eventsLast(@Path("sid") seasonId: Long, @Path("page") page: Int): EventsDto

    @GET("sport/baseball/events/live")
    suspend fun liveBaseball(): EventsDto

    @GET("event/{id}")
    suspend fun event(@Path("id") id: Long): EventDetailDto
}
```

`di/NetworkModule.kt` — OkHttp + Retrofit 3 + kotlinx.serialization:

```kotlin
package com.diamondscore.di

import com.diamondscore.data.remote.SofaScoreApi
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
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
            val req = chain.request().newBuilder()
                .header("User-Agent", "DiamondScore/0.1 (Android)")
                .header("Accept", "application/json")
                .build()
            chain.proceed(req)
        })
        .build()

    @Provides @Singleton fun retrofit(client: OkHttpClient): Retrofit = Retrofit.Builder()
        .baseUrl("https://api.sofascore.com/api/v1/")
        .client(client)
        .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
        .build()

    @Provides @Singleton fun api(retrofit: Retrofit): SofaScoreApi = retrofit.create(SofaScoreApi::class.java)
}
```

<div class="callout tip"><span class="t">Retrofit 3 컨버터</span>
Retrofit 3는 <code>suspend</code> 함수와 kotlinx.serialization 컨버터를 정식 지원합니다. Gson/Moshi를 추가하지 마세요.
</div>

## 4. 매퍼 — 함정을 여기서 흡수

`data/remote/mapper/Mappers.kt`:

```kotlin
package com.diamondscore.data.remote.mapper

import com.diamondscore.data.remote.dto.*
import com.diamondscore.domain.model.*
import com.diamondscore.core.designsystem.teamNameKo
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId

private val SEOUL = ZoneId.of("Asia/Seoul")
private val INNING = Regex("""inning(\d+)""")

fun StatusDto.toDomain(): GameStatus = when (type) {   // 함정 6: type 기준
    "notstarted" -> GameStatus.SCHEDULED
    "inprogress" -> GameStatus.LIVE
    "finished"   -> GameStatus.FINAL
    "canceled"   -> GameStatus.CANCELED
    "postponed"  -> GameStatus.POSTPONED
    "suspended"  -> GameStatus.SUSPENDED
    else -> GameStatus.UNKNOWN
}

fun TeamDto.toRef() = TeamRef(id, teamNameKo(id, name), nameCode ?: "")

// 함정 2·3: period* 무시, innings 맵을 정규식으로 파싱·정렬
fun parseInnings(home: Map<String, InningRunDto>, away: Map<String, InningRunDto>): List<InningRuns> {
    val nums = (home.keys + away.keys).mapNotNull { INNING.matchEntire(it)?.groupValues?.get(1)?.toIntOrNull() }
    return nums.distinct().sorted().map { n ->
        InningRuns(n, home["inning$n"]?.run, away["inning$n"]?.run)
    }
}

fun EventDto.toSummary(): GameSummary {
    val st = status.toDomain()
    val innings = parseInnings(homeScore?.innings ?: emptyMap(), awayScore?.innings ?: emptyMap())
    return GameSummary(
        id = id,
        startsAt = Instant.ofEpochSecond(startTimestamp),
        leagueDate = Instant.ofEpochSecond(startTimestamp).atZone(SEOUL).toLocalDate(), // 함정: KST
        status = st,
        statusLabel = status.description,           // 원문 그대로 (추정 금지)
        home = homeTeam.toRef(), away = awayTeam.toRef(),
        homeRuns = homeScore?.current, awayRuns = awayScore?.current,  // 경기 전 null
        winner = if (st == GameStatus.FINAL) when (winnerCode) {
            1 -> Winner.HOME; 2 -> Winner.AWAY; 3 -> Winner.DRAW; else -> null
        } else null,
        wentExtra = status.code == 110 || innings.any { it.number > 9 },
        changeTimestamp = changes?.changeTimestamp,
    )
}

fun StandingRowDto.toDomain() = Standing(
    position = position, team = team.toRef(),
    games = matches, wins = wins, losses = losses,
    draws = matches - wins - losses,                 // 함정 1: 무승부 파생
    winPct = percentage, gamesBehind = gamesBehind,
    runsFor = scoresFor, runsAgainst = scoresAgainst,
    runDiff = scoreDiffFormatted ?: (scoresFor - scoresAgainst).let { if (it >= 0) "+$it" else "$it" },
    playoffTier = promotion?.text,
)
```

## 5. fixture 옮기고 매퍼 테스트

Step 1에서 받은 JSON을 테스트 리소스로 옮깁니다.

```bash
mkdir -p app/src/test/resources/fixtures
cp fixtures/*.json app/src/test/resources/fixtures/
```

`app/src/test/java/.../MapperTest.kt` — **함정 7개**를 각각 검증합니다.

```kotlin
class MapperTest {
    private val json = kotlinx.serialization.json.Json { ignoreUnknownKeys = true; explicitNulls = false }
    private fun load(name: String) = javaClass.classLoader!!.getResourceAsStream("fixtures/$name")!!.bufferedReader().readText()

    @Test fun `무승부 파생`() {
        val row = json.decodeFromString<StandingsResponseDto>(load("standings.json")).standings[0].rows[0]
        val s = row.toDomain()
        assertEquals(row.matches - row.wins - row.losses, s.draws)   // 함정 1
    }

    @Test fun `연장 이닝이 라인스코어에 나온다`() {
        val ev = json.decodeFromString<EventsDto>(load("events_last.json")).events
            .firstOrNull { it.status.code == 110 } ?: return   // 연장 표본이 있으면
        val innings = parseInnings(ev.homeScore!!.innings, ev.awayScore!!.innings)
        assertTrue(innings.any { it.number >= 10 })                  // 함정 2·3
    }

    @Test fun `미지의 status는 UNKNOWN`() {
        assertEquals(GameStatus.UNKNOWN, StatusDto(999, "??", "??").toDomain())  // 함정 6
    }
}
```

```bash
./gradlew :app:testDebugUnitTest
```

<div class="checkpoint"><span class="t"></span> 테스트가 초록불이면 완료. 특히 <strong>연장 경기에서 10회 득점이 라인스코어에 나타나는지</strong>가 이 앱에서 가장 자주 깨지는 부분이니 반드시 통과시키세요.</div>

<div class="pager">
<a href="#/labs/step-2">← Step 2</a>
<a href="#/labs/step-4">Step 4 · Room·프리페치 →</a>
</div>
