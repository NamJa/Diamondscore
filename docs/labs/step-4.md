# Step 4 · Room + Repository + 시즌 프리페치

<div class="chips"><span class="chip time">2시간</span><span class="chip diff">보통</span><span class="chip goal">시즌 전체를 로컬 DB에 저장해 오프라인에서도 날짜별로 본다</span></div>

SofaScore에는 "8월 2일 경기" 같은 **날짜 조회가 없습니다**(404). 대신 시즌 전체를 한 번 받아 Room에 넣고, 날짜 이동은 로컬 쿼리로 처리합니다(720경기 ≈ 400KB).

## 1. 엔티티

`data/local/entity/Entities.kt`:

```kotlin
package com.diamondscore.data.local.entity

import androidx.room.*

@Entity(tableName = "games", indices = [Index("leagueDate"), Index("homeTeamId"), Index("awayTeamId")])
data class GameEntity(
    @PrimaryKey val eventId: Long,
    val startsAtEpoch: Long,
    val leagueDate: String,          // ISO yyyy-MM-dd (Asia/Seoul)
    val status: String,
    val statusLabel: String,
    val homeTeamId: Long, val homeName: String, val homeCode: String,
    val awayTeamId: Long, val awayName: String, val awayCode: String,
    val homeRuns: Int?, val awayRuns: Int?,
    val winner: String?,
    val wentExtra: Boolean,
    val changeTimestamp: Long?,
)

@Entity(tableName = "innings", primaryKeys = ["eventId", "inning"], indices = [Index("eventId")])
data class InningRunEntity(
    val eventId: Long, val inning: Int, val home: Int?, val away: Int?,
)

@Entity(tableName = "standings", primaryKeys = ["seasonId", "teamId"])
data class StandingEntity(
    val seasonId: Long, val teamId: Long, val position: Int,
    val games: Int, val wins: Int, val losses: Int, val draws: Int,
    val winPct: Double, val gamesBehind: Double,
    val runsFor: Int, val runsAgainst: Int, val runDiff: String, val playoffTier: String?,
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

    @Query("SELECT * FROM games WHERE eventId = :id")
    fun observeGame(id: Long): kotlinx.coroutines.flow.Flow<GameEntity?>

    @Query("SELECT changeTimestamp FROM games WHERE eventId = :id")
    suspend fun changeTs(id: Long): Long?

    @Upsert suspend fun upsertGames(games: List<GameEntity>)
    @Upsert suspend fun upsertInnings(rows: List<InningRunEntity>)

    @Transaction
    suspend fun saveGame(game: GameEntity, innings: List<InningRunEntity>) {
        upsertGames(listOf(game)); upsertInnings(innings)      // 총점·이닝을 한 트랜잭션으로
    }
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

`di/DatabaseModule.kt`:

```kotlin
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
class GamesRepository @Inject constructor(
    private val api: SofaScoreApi,
    private val dao: GameDao,
) {
    fun observeByDate(date: LocalDate): Flow<List<GameSummary>> =
        dao.observeByDate(date.toString()).map { it.map(GameEntity::toSummary) }

    /** 시즌 전체를 next/last 페이지로 순회해 Room에 upsert. 빈 배열까지, 최대 60페이지. */
    suspend fun prefetchSeason(seasonId: Long) {
        suspend fun crawl(fetch: suspend (Int) -> EventsDto) {
            var page = 0
            while (page < 60) {
                val events = fetch(page).events
                if (events.isEmpty()) break
                events.forEach { saveEvent(it) }
                page++
            }
        }
        crawl { api.eventsLast(seasonId, it) }
        crawl { api.eventsNext(seasonId, it) }
    }

    private suspend fun saveEvent(dto: EventDto) {
        // 함정: changeTimestamp가 같으면 DB 쓰기 스킵 (불필요한 Flow 재방출 방지)
        if (dto.changes?.changeTimestamp != null && dao.changeTs(dto.id) == dto.changes.changeTimestamp) return
        val s = dto.toSummary()
        val innings = parseInnings(dto.homeScore?.innings ?: emptyMap(), dto.awayScore?.innings ?: emptyMap())
        dao.saveGame(s.toEntity(), innings.map { InningRunEntity(dto.id, it.number, it.home, it.away) })
    }

    suspend fun refreshLive() = api.liveBaseball().events
        .filter { /* uniqueTournament.id == 11204 필터 (상세 DTO에 필드 추가해 사용) */ true }
        .forEach { saveEvent(it) }
}
```

(엔티티 ↔ 도메인 변환 `toEntity()`/`toSummary()`는 Step 3 매퍼 옆에 추가합니다.)

## 5. 시즌 프리페치 워커

`data/sync/PrefetchWorker.kt` — 앱 시작 시 1회, 이후 하루 1회.

```kotlin
@HiltWorker
class PrefetchWorker @AssistedInject constructor(
    @Assisted ctx: Context, @Assisted params: WorkerParameters,
    private val api: SofaScoreApi, private val repo: GamesRepository,
) : CoroutineWorker(ctx, params) {
    override suspend fun doWork(): Result = try {
        val seasonId = api.seasons().seasons.first().id     // 하드코딩 금지: 첫 항목
        repo.prefetchSeason(seasonId)
        Result.success()
    } catch (e: Exception) { Result.retry() }
}
```

`App.kt`의 `onCreate`에서 unique work로 등록합니다(네트워크 제약 + 지수 backoff).

## 6. 통합 테스트

`app/src/test/.../RepositoryTest.kt` — MockWebServer로 빈 배열까지 순회하는지, 오프라인에서 Room이 읽히는지 검증합니다.

```bash
./gradlew :app:testDebugUnitTest
```

<div class="checkpoint"><span class="t"></span> 앱을 한 번 실행해 프리페치가 돌게 한 뒤 <strong>비행기 모드</strong>로 바꿔도, <code>observeByDate</code>로 과거/미래 날짜의 경기가 조회되면 성공. (아직 화면은 없으니 로그나 DB Inspector로 확인)</div>

<div class="pager">
<a href="#/labs/step-3">← Step 3</a>
<a href="#/labs/step-5">Step 5 · 공통 컴포넌트 →</a>
</div>
