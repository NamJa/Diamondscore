# Step 4 · Room + Repository + 시즌 프리페치

<div class="chips"><span class="chip time">2시간</span><span class="chip diff">보통</span><span class="chip goal">시즌 전체를 로컬 DB에 저장해 오프라인에서도 날짜별로 본다</span></div>

wisetoto에는 날짜 조회(`Schedule_Day`)가 있지만, 그래도 시즌 전체를 Room에 넣어 둡니다 — 오프라인·즉시 응답·즐겨찾기 팀 일정 때문입니다. 프리페치 단위는 **월**(`Schedule_Month` 9회, 약 300KB)이고, 오늘 화면은 `Schedule_Day` 1회로 최신화합니다.

## 1. 엔티티

`data/local/entity/Entities.kt`:

```kotlin
package com.diamondscore.data.local.entity

import androidx.room.*

@Entity(tableName = "games", indices = [Index("leagueDate"), Index("homeTeamId"), Index("awayTeamId")])
data class GameEntity(
    @PrimaryKey val gameId: Long,    // schedule_info_seq
    val startsAtEpoch: Long,
    val leagueDate: String,          // ISO yyyy-MM-dd (Asia/Seoul)
    val status: String,
    val statusLabel: String,
    val homeTeamId: Long, val homeName: String, val homeCode: String,
    val awayTeamId: Long, val awayName: String, val awayCode: String,
    val homeRuns: Int?, val awayRuns: Int?,
    val winner: String?,
    val wentExtra: Boolean,
    val finalInning: Int?,           // 최종/현재 회차 — Step 5·7이 "연장 11회"로 읽는다
    val homeStarter: String?, val awayStarter: String?,
)

@Entity(tableName = "innings", primaryKeys = ["gameId", "inning"], indices = [Index("gameId")])
data class InningRunEntity(
    val gameId: Long, val inning: Int, val home: Int?, val away: Int?,
)

@Entity(tableName = "standings", primaryKeys = ["season", "teamId"])
data class StandingEntity(
    val season: Int, val teamId: Long, val position: Int,
    val games: Int, val wins: Int, val losses: Int, val draws: Int,
    val winPct: Double, val gamesBehind: Double, val streak: String?,
)

@Entity(tableName = "favorites", primaryKeys = ["type", "targetId"])
data class FavoriteEntity(val type: String, val targetId: Long, val createdAt: Long)
```

## 2. DAO

`data/local/dao/GameDao.kt`:

```kotlin
@Dao
interface GameDao {
    @Query("SELECT * FROM games WHERE leagueDate = :date ORDER BY startsAtEpoch")
    fun observeByDate(date: String): kotlinx.coroutines.flow.Flow<List<GameEntity>>

    @Query("SELECT * FROM games WHERE homeTeamId = :teamId OR awayTeamId = :teamId ORDER BY startsAtEpoch")
    fun observeByTeam(teamId: Long): kotlinx.coroutines.flow.Flow<List<GameEntity>>   // Step 8 팀 상세

    @Query("SELECT * FROM games WHERE gameId = :id")
    fun observeGame(id: Long): kotlinx.coroutines.flow.Flow<GameEntity?>

    @Query("SELECT * FROM innings WHERE gameId = :id ORDER BY inning")
    fun observeInnings(id: Long): kotlinx.coroutines.flow.Flow<List<InningRunEntity>>

    @Query("SELECT * FROM games WHERE gameId = :id")
    suspend fun find(id: Long): GameEntity?          // 쓰기 스킵용 (함정 7: 델타 필드가 없다)

    @Query("SELECT leagueDate FROM games WHERE leagueDate > :date ORDER BY leagueDate LIMIT 1")
    suspend fun nearestAfter(date: String): String?  // Step 6 날짜 바의 "가장 가까운 경기일로"

    @Upsert suspend fun upsertGames(games: List<GameEntity>)
    @Upsert suspend fun upsertInnings(rows: List<InningRunEntity>)
    @Query("DELETE FROM innings WHERE gameId = :id") suspend fun clearInnings(id: Long)

    @Transaction
    suspend fun saveGame(game: GameEntity, innings: List<InningRunEntity>?) {
        upsertGames(listOf(game))
        if (innings != null) {                        // 목록 갱신(null)은 이닝을 건드리지 않는다
            clearInnings(game.gameId)                 // 취소·이닝 축소 시 옛 행이 남지 않게 먼저 비운다 (아래 콜아웃)
            upsertInnings(innings)                    // 총점·이닝을 한 트랜잭션으로
        }
    }
}
```

`data/local/dao/StandingDao.kt` · `FavoriteDao.kt`:

```kotlin
@Dao
interface StandingDao {
    @Query("SELECT * FROM standings WHERE season = :year ORDER BY position")
    fun observe(year: Int): Flow<List<StandingEntity>>

    @Transaction
    suspend fun replace(year: Int, rows: List<StandingEntity>) { clear(year); upsert(rows) }
    @Query("DELETE FROM standings WHERE season = :year") suspend fun clear(year: Int)
    @Upsert suspend fun upsert(rows: List<StandingEntity>)
}

@Dao
interface FavoriteDao {
    @Query("SELECT * FROM favorites WHERE type = :type") fun observe(type: String): Flow<List<FavoriteEntity>>
    @Query("SELECT EXISTS(SELECT 1 FROM favorites WHERE type = :type AND targetId = :id)")
    suspend fun exists(type: String, id: Long): Boolean
    @Insert suspend fun insert(f: FavoriteEntity)
    @Query("DELETE FROM favorites WHERE type = :type AND targetId = :id") suspend fun delete(type: String, id: Long)
}
```

## 3. Database

`data/local/DiamondScoreDatabase.kt`:

```kotlin
@Database(
    entities = [GameEntity::class, InningRunEntity::class, StandingEntity::class, FavoriteEntity::class],
    version = 1, exportSchema = true,
)
abstract class DiamondScoreDatabase : RoomDatabase() {
    abstract fun gameDao(): GameDao
    abstract fun standingDao(): StandingDao
    abstract fun favoriteDao(): FavoriteDao
}
```

`data/local/di/DatabaseModule.kt`:

```kotlin
package com.diamondscore.data.local.di

import android.content.Context
import androidx.room.Room
import com.diamondscore.data.local.DiamondScoreDatabase
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module @InstallIn(SingletonComponent::class)
object DatabaseModule {
    @Provides @Singleton fun db(@ApplicationContext ctx: Context) =
        Room.databaseBuilder(ctx, DiamondScoreDatabase::class.java, "diamondscore.db").build()
    @Provides fun gameDao(db: DiamondScoreDatabase) = db.gameDao()
    @Provides fun standingDao(db: DiamondScoreDatabase) = db.standingDao()
    @Provides fun favoriteDao(db: DiamondScoreDatabase) = db.favoriteDao()
}
```

<div class="callout tip"><span class="t">schema export</span>
<code>exportSchema = true</code>면 <code>app/build.gradle.kts</code>에 스키마 위치가 필요합니다: <code>ksp { arg("room.schemaLocation", "$projectDir/schemas") }</code>
</div>

## 4. Repository — 프리페치와 관찰

`data/repository/GamesRepository.kt`:

```kotlin
@Singleton
class GamesRepository @Inject constructor(
    private val api: WisetotoApi,
    private val dao: GameDao,
) {
    fun observeByDate(date: LocalDate): Flow<List<GameSummary>> =
        dao.observeByDate(date.toString()).map { it.map(GameEntity::toSummary) }

    fun observeByTeam(teamId: Long): Flow<List<GameSummary>> =
        dao.observeByTeam(teamId).map { it.map(GameEntity::toSummary) }

    /** Step 6 날짜 바의 "가장 가까운 경기일로" — 프리페치된 Room 행만 보므로 네트워크가 없다. */
    suspend fun nearestGameDay(after: LocalDate): LocalDate? = dao.nearestAfter(after.toString())?.let(LocalDate::parse)

    /** 시즌 = 연도. wisetoto엔 시즌 ID가 없고 순위·프리페치 모두 year로 조회한다. 이 앱에서 `WisetotoApi`를 아는 곳은 data 레이어뿐이다. */
    fun currentSeasonYear(): Int = LocalDate.now(SEOUL).year

    /** 정규시즌 시작일 — Schedule_Day 응답의 league_rank.start (조회 날짜와 무관하게 현재 시즌). refreshDay가 채워 둔다. */
    private var seasonStart: LocalDate? = null
    private suspend fun seasonStart(): LocalDate? = seasonStart ?: runCatching {
        api.scheduleDay(LocalDate.now(SEOUL).format(apiDay)).body().season?.start?.let(LocalDate::parse)
    }.getOrNull()?.also { seasonStart = it }

    /** 시즌 전체를 월 단위로 받아 Room에 upsert. 3~11월 9회. WBC·시범경기·올스타전은 여기서 걸러진다(함정 8). */
    suspend fun prefetchSeason(year: Int) {
        // 시작일을 모르면 3월 시범경기(3/12~3/24)가 그대로 들어오고 지울 방법이 없다 → 아무것도 쓰지 말고 워커가 재시도하게 둔다
        val start = seasonStart() ?: error("league_rank.start를 받지 못했다 — 프리페치를 건너뛴다")
        for (month in 3..11) {
            // Schedule_Month엔 game_timestamp가 없어 game_date 문자열을 파싱한다(함정 7).
            // 한 행이 깨져도 그 달 전체가 날아가지 않게 행 단위로 막는다.
            api.scheduleMonth("%04d%02d".format(year, month)).body().games
                .mapNotNull { row -> runCatching { row.takeIf { it.isKboRegular(start) }?.toSummary() }.getOrNull() }
                .forEach { saveSummary(it) }
        }
    }

    /** 하루치 최신화 — 오늘 화면 진입 시 1회, 라이브 중엔 20초마다(Step 6). */
    suspend fun refreshDay(date: LocalDate) {
        val day = api.scheduleDay(date.format(apiDay)).body()
        // 같은 응답에 league_rank가 실려 오므로 시즌 시작일을 따로 조회하지 않는다 — 폴링 1회 = 요청 1개
        val start = day.season?.start?.let(LocalDate::parse)?.also { seasonStart = it } ?: seasonStart
        day.games.filter { it.isKboRegular(start) }.forEach { saveSummary(it.toSummary()) }
    }

    private suspend fun saveSummary(s: GameSummary, innings: List<InningRuns>? = null) {
        val old = dao.find(s.id)
        // 선발은 Schedule_Day에만 있다 — Schedule_Month와 상세 응답은 null이므로 덮어쓰지 말고 기존 값을 보존한다
        val entity = s.toEntity().let {
            it.copy(homeStarter = it.homeStarter ?: old?.homeStarter, awayStarter = it.awayStarter ?: old?.awayStarter)
        }
        // 함정 7: 변경 감지 필드가 없다 → 기존 행과 같으면 DB 쓰기 스킵 (불필요한 Flow 재방출 방지)
        if (innings == null && old == entity) return
        dao.saveGame(entity, innings?.map { InningRunEntity(s.id, it.number, it.home, it.away) })
    }

    // ── 경기 상세 (Step 7에서 사용) ──
    private val detailMeta = MutableStateFlow<Map<Long, DetailMeta>>(emptyMap())   // 구장·R/H/E·투수 요약

    fun observeGameDetail(id: Long): Flow<GameDetail?> =
        combine(dao.observeGame(id), dao.observeInnings(id), detailMeta) { g, inn, meta ->
            g?.let {
                val m = meta[id]
                GameDetail(
                    summary = it.toSummary(),
                    innings = inn.map { r -> InningRuns(r.inning, r.home, r.away) },
                    venueName = m?.venueName,
                    homeHits = m?.homeHits, awayHits = m?.awayHits,
                    homeErrors = m?.homeErrors, awayErrors = m?.awayErrors,
                    winPitcher = m?.winPitcher, losePitcher = m?.losePitcher, savePitcher = m?.savePitcher,
                )
            }
        }

    suspend fun refreshGame(id: Long) {
        val dto = api.game(id).body().detail ?: return
        val d = dto.toDetail()
        saveSummary(d.summary, d.innings)                // 점수·이닝 갱신 (Room, 한 트랜잭션)
        detailMeta.update { it + (id to DetailMeta(       // 라인스코어 외 상세는 메모리 캐시
            d.venueName, d.homeHits, d.awayHits, d.homeErrors, d.awayErrors,
            d.winPitcher, d.losePitcher, d.savePitcher)) }
    }
}

data class DetailMeta(
    val venueName: String?, val homeHits: Int?, val awayHits: Int?, val homeErrors: Int?, val awayErrors: Int?,
    val winPitcher: String?, val losePitcher: String?, val savePitcher: String?,
)
```

<div class="callout warn"><span class="t">취소 경기 재조회 시 옛 이닝이 남지 않게</span>
노게임은 <code>state:"c"</code>로 바뀌면서 매퍼가 이닝을 빈 배열로 만듭니다(Step 3 함정 3). 그런데 <code>upsert</code>만 하면 3회까지 저장해 둔 부분 이닝 행이 그대로 남습니다 — Step 7의 상세 화면은 상태와 상관없이 라인스코어를 그리므로 “취소” 라벨 아래 1·2·3회 점수가 유령처럼 남습니다. 그래서 위 <code>saveGame</code>은 이닝을 받을 때마다 <code>clearInnings</code>로 먼저 비우고 다시 넣습니다(이닝이 줄어드는 정정도 같이 막힙니다). 목록 갱신은 <code>innings = null</code>이라 이 경로를 타지 않습니다.
</div>

### 엔티티 ↔ 도메인 매퍼

`data/local/mapper/EntityMappers.kt` — Repository가 Room 행을 도메인으로, 도메인을 행으로 바꿉니다.
`teamNameKo`·`teamShort`·`KBO_TEAMS`는 Step 2에서 `core/common`에 둔 순수 Kotlin입니다(`core/designsystem`이 아닙니다 —
data 레이어는 Compose를 모릅니다).

```kotlin
fun GameEntity.toSummary() = GameSummary(
    id = gameId,
    startsAt = Instant.ofEpochSecond(startsAtEpoch),
    leagueDate = LocalDate.parse(leagueDate),
    status = GameStatus.valueOf(status),
    statusLabel = statusLabel,
    home = TeamRef(homeTeamId, teamNameKo(homeTeamId, homeName), homeCode),
    away = TeamRef(awayTeamId, teamNameKo(awayTeamId, awayName), awayCode),
    homeRuns = homeRuns, awayRuns = awayRuns,
    winner = winner?.let(Winner::valueOf),
    wentExtra = wentExtra, finalInning = finalInning,
    venueShort = KBO_TEAMS[homeTeamId]?.home,
    homeStarter = homeStarter, awayStarter = awayStarter,
)

fun GameSummary.toEntity() = GameEntity(
    gameId = id, startsAtEpoch = startsAt.epochSecond, leagueDate = leagueDate.toString(),
    status = status.name, statusLabel = statusLabel,
    homeTeamId = home.id, homeName = home.nameKo, homeCode = home.code,
    awayTeamId = away.id, awayName = away.nameKo, awayCode = away.code,
    homeRuns = homeRuns, awayRuns = awayRuns, winner = winner?.name,
    wentExtra = wentExtra, finalInning = finalInning,
    homeStarter = homeStarter, awayStarter = awayStarter,
)
```

(`saveSummary`의 `s.toEntity()`가 이 함수입니다. `data class` 동등 비교가 곧 쓰기 스킵 조건이므로 **엔티티에 갱신 시각 같은 필드를 넣지 마세요** — 넣는 순간 매번 달라져 스킵이 안 됩니다. `StandingEntity.toDomain()`·`Standing.toEntity(year)`는 Step 8에서 순위와 함께 만듭니다.)

## 5. 시즌 프리페치 워커

`data/sync/PrefetchWorker.kt` — 설치 후 첫 실행에 1회, 이후 하루 1회.

```kotlin
@HiltWorker
class PrefetchWorker @AssistedInject constructor(
    @Assisted ctx: Context, @Assisted params: WorkerParameters,
    private val repo: GamesRepository,
) : CoroutineWorker(ctx, params) {
    override suspend fun doWork(): Result = try {
        repo.prefetchSeason(repo.currentSeasonYear())
        Result.success()
    } catch (e: Exception) { Result.retry() }
}
```

`@HiltWorker`는 앱이 `HiltWorkerFactory`를 넘겨줘야 만들어집니다 — 기본 팩토리는 `(Context, WorkerParameters)` 2인자 생성자만 찾으므로, 이 배선이 없으면 빌드는 되는데 실행 시 logcat에 `Could not instantiate com.diamondscore.data.sync.PrefetchWorker`만 남고 작업이 FAILED로 끝납니다. **Step 2 §5에서 만든 `App.kt`를 이렇게 바꿉니다** — 워커 팩토리 제공과 등록을 한 파일에서 끝냅니다(완전한 코드).

```kotlin
package com.diamondscore

import android.app.Application
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.BackoffPolicy
import androidx.work.Configuration
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.diamondscore.data.sync.PrefetchWorker
import dagger.hilt.android.HiltAndroidApp
import java.util.concurrent.TimeUnit
import javax.inject.Inject

// 이름은 DiamondScoreApplication이다 — Step 9의 @Composable fun DiamondScoreApp()과 충돌하지 않게(Step 2 §5).
@HiltAndroidApp
class DiamondScoreApplication : Application(), Configuration.Provider {

    @Inject lateinit var workerFactory: HiltWorkerFactory

    // WorkManager가 @HiltWorker를 만들 수 있는 유일한 통로. 이 프로퍼티가 없으면 워커는 생성 단계에서 실패한다.
    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder().setWorkerFactory(workerFactory).build()

    override fun onCreate() {
        super.onCreate()
        val request = PeriodicWorkRequestBuilder<PrefetchWorker>(1, TimeUnit.DAYS)
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 10, TimeUnit.MINUTES)   // Result.retry()가 타는 간격
            .build()
        // KEEP: 이미 예약돼 있으면 주기를 초기화하지 않는다. 첫 실행 1회 + 하루 1회가 이 한 줄로 끝난다.
        WorkManager.getInstance(this)
            .enqueueUniquePeriodicWork("prefetch-season", ExistingPeriodicWorkPolicy.KEEP, request)
    }
}
```

WorkManager는 기본적으로 `androidx.startup`으로 자기 자신을 초기화하므로, 그 초기화기를 꺼야 위 `Configuration`이 쓰입니다. `AndroidManifest.xml`의 `<manifest>`에 `xmlns:tools`를 선언하고 `<application>` 안에 이 블록을 넣습니다.

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">

    <application android:name=".DiamondScoreApplication" ... >

        <!-- WorkManager 기본 초기화 제거 — Configuration.Provider가 대신 설정을 넘긴다 -->
        <provider
            android:name="androidx.startup.InitializationProvider"
            android:authorities="${applicationId}.androidx-startup"
            android:exported="false"
            tools:node="merge">
            <meta-data
                android:name="androidx.work.WorkManagerInitializer"
                android:value="androidx.startup"
                tools:node="remove" />
        </provider>
    </application>
</manifest>
```

<div class="callout warn"><span class="t">이 셋은 세트다</span>
<code>Configuration.Provider</code> 구현 · 매니페스트의 <code>tools:node="remove"</code> · <code>enqueueUniquePeriodicWork</code> 호출 — 하나라도 빠지면 워커는 <strong>크래시 없이 그냥 안 돕니다</strong>. 확인은 logcat의 <code>WM-</code> 태그와 <code>adb shell dumpsys jobscheduler | grep diamondscore</code>로 합니다.
</div>

잔여 경기 재편성(9월 이후 새 seq)은 하루 1회 재실행으로 자연히 들어옵니다 — 이미 있는 행은 동등 비교로 스킵되므로 비용이 거의 없습니다.

## 6. 통합 테스트

`app/src/test/java/.../RepositoryTest.kt` — 네트워크만 MockWebServer로 바꿔 끼우고 Step 1의 fixture를 그대로 돌려줍니다. **DAO는 인메모리 가짜를 씁니다** — JVM 테스트에는 SQLite가 없어 Room을 띄우려면 Robolectric이 필요하고, 여기서 보려는 것은 Room이 아니라 Repository의 필터·쓰기 스킵·병합 규칙이기 때문입니다(Room 자체는 아래 체크포인트에서 실기기로 확인합니다).

```kotlin
package com.diamondscore.data.repository

import com.diamondscore.data.local.dao.GameDao
import com.diamondscore.data.local.entity.GameEntity
import com.diamondscore.data.local.entity.InningRunEntity
import com.diamondscore.data.remote.WisetotoApi
import com.diamondscore.data.remote.WisetotoException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.time.LocalDate
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/** Room 없이 도는 DAO. `saveGame`은 인터페이스의 기본 구현이라 그대로 실행된다(= 이닝 비우기도 같이 검증된다). */
class FakeGameDao : GameDao {
    val rows = linkedMapOf<Long, GameEntity>()
    val innings = linkedMapOf<Long, List<InningRunEntity>>()
    var gameWrites = 0
    override suspend fun find(id: Long) = rows[id]
    override suspend fun nearestAfter(date: String) = rows.values.map { it.leagueDate }.filter { it > date }.minOrNull()
    override suspend fun upsertGames(games: List<GameEntity>) { gameWrites++; games.forEach { rows[it.gameId] = it } }
    override suspend fun upsertInnings(rows: List<InningRunEntity>) =
        rows.groupBy { it.gameId }.forEach { (id, r) -> innings[id] = innings[id].orEmpty() + r }
    override suspend fun clearInnings(id: Long) { innings -= id }
    override fun observeByDate(date: String): Flow<List<GameEntity>> = flowOf(rows.values.filter { it.leagueDate == date })
    override fun observeByTeam(teamId: Long): Flow<List<GameEntity>> =
        flowOf(rows.values.filter { it.homeTeamId == teamId || it.awayTeamId == teamId })
    override fun observeGame(id: Long): Flow<GameEntity?> = flowOf(rows[id])
    override fun observeInnings(id: Long): Flow<List<InningRunEntity>> = flowOf(innings[id].orEmpty())
}

class RepositoryTest {
    private val json = Json { ignoreUnknownKeys = true; coerceInputValues = true; explicitNulls = false }
    private val server = MockWebServer()
    private val dao = FakeGameDao()
    private val api = Retrofit.Builder()
        .baseUrl(server.url("/"))
        .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
        .build().create(WisetotoApi::class.java)
    private val repo = GamesRepository(api, dao)

    private fun fixture(name: String) =
        javaClass.classLoader!!.getResourceAsStream("fixtures/$name")!!.bufferedReader().readText()

    /** 경로 조각 → 응답 본문. 라우트 이름이 대소문자를 가리므로 조각도 그대로 쓴다(함정 1). */
    private fun serve(vararg bodyByPath: Pair<String, String>) {
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse =
                bodyByPath.firstOrNull { request.path.orEmpty().contains(it.first) }
                    ?.let { MockResponse().setBody(it.second) } ?: MockResponse().setResponseCode(404)
        }
    }

    @After fun tearDown() = server.shutdown()

    @Test fun `프리페치는 9개 월을 돌고 시범경기·WBC는 저장하지 않는다`() = runTest {
        serve("Schedule_Day/" to fixture("schedule_day_finished.json"),
              "Schedule_Month/" to fixture("schedule_month_march.json"))
        repo.prefetchSeason(2026)
        assertEquals(10, server.requestCount)                     // 시즌 시작일 1회 + 3~11월 9회
        assertTrue(dao.rows.isNotEmpty())
        val start = LocalDate.parse("2026-03-27")                 // league_rank.start
        assertTrue(dao.rows.values.none { LocalDate.parse(it.leagueDate).isBefore(start) })
    }

    @Test fun `같은 응답을 두 번 받으면 DB 쓰기는 한 번뿐이다`() = runTest {
        serve("Schedule_Day/" to fixture("schedule_day_finished.json"))
        repo.refreshDay(LocalDate.of(2026, 9, 13))
        val writes = dao.gameWrites
        repo.refreshDay(LocalDate.of(2026, 9, 13))
        assertEquals(writes, dao.gameWrites)                      // 함정 7: 델타 필드가 없으니 동등 비교로 스킵
    }

    @Test fun `상세 갱신은 목록이 채운 선발투수를 지우지 않는다`() = runTest {
        serve("Schedule_Day/" to fixture("schedule_day_finished.json"),
              "schedule/" to fixture("game_final.json"))          // 490691 — 같은 날 경기
        repo.refreshDay(LocalDate.of(2026, 9, 13))
        val starter = dao.rows[490691L]!!.homeStarter
        assertNotNull(starter)                                    // Schedule_Day가 채웠다
        repo.refreshGame(490691L)
        assertEquals(starter, dao.rows[490691L]!!.homeStarter)    // 상세 응답엔 선발이 없다 → 보존
    }

    @Test fun `code 01 봉투는 예외가 되고 기존 행은 살아 있다`() = runTest {
        serve("Schedule_Day/" to fixture("schedule_day_finished.json"))
        repo.refreshDay(LocalDate.of(2026, 9, 13))
        serve("Schedule_Day/" to """{"result":"fail","code":"01","message":"잘못된 접근"}""")
        assertFailsWith<WisetotoException> { repo.refreshDay(LocalDate.of(2026, 9, 13)) }
        assertTrue(dao.rows.isNotEmpty())                         // 실패가 캐시를 비우지 않는다
    }
}
```

```bash
./gradlew :app:testDebugUnitTest
```

<div class="checkpoint"><span class="t"></span> 앱을 한 번 실행해 프리페치가 돌게 한 뒤 <strong>비행기 모드</strong>로 바꿔도, <code>observeByDate</code>로 과거/미래 날짜의 경기가 조회되면 성공. (아직 화면은 없으니 로그나 DB Inspector로 확인)</div>

<div class="pager">
<a href="#/labs/step-3">← Step 3</a>
<a href="#/labs/step-5">Step 5 · 공통 컴포넌트 →</a>
</div>
