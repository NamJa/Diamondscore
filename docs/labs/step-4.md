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

    @Upsert suspend fun upsertGames(games: List<GameEntity>)
    @Upsert suspend fun upsertInnings(rows: List<InningRunEntity>)

    @Transaction
    suspend fun saveGame(game: GameEntity, innings: List<InningRunEntity>?) {
        upsertGames(listOf(game))
        if (innings != null) upsertInnings(innings)   // 총점·이닝을 한 트랜잭션으로. 목록 갱신(null)은 이닝을 건드리지 않는다
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
    private val api: WisetotoApi,
    private val dao: GameDao,
) {
    fun observeByDate(date: LocalDate): Flow<List<GameSummary>> =
        dao.observeByDate(date.toString()).map { it.map(GameEntity::toSummary) }

    fun observeByTeam(teamId: Long): Flow<List<GameSummary>> =
        dao.observeByTeam(teamId).map { it.map(GameEntity::toSummary) }

    /** 시즌 = 연도. wisetoto엔 시즌 ID가 없고 순위·프리페치 모두 year로 조회한다. 이 앱에서 `WisetotoApi`를 아는 곳은 data 레이어뿐이다. */
    fun currentSeasonYear(): Int = LocalDate.now(SEOUL).year

    /** 정규시즌 시작일 — Schedule_Day 응답의 league_rank.start (조회 날짜와 무관하게 현재 시즌). 실패 시 null → 팀 필터만 적용. */
    private var seasonStart: LocalDate? = null
    private suspend fun seasonStart(): LocalDate? = seasonStart ?: runCatching {
        api.scheduleDay(LocalDate.now(SEOUL).format(apiDay)).body().season?.start?.let(LocalDate::parse)
    }.getOrNull()?.also { seasonStart = it }

    /** 시즌 전체를 월 단위로 받아 Room에 upsert. 3~11월 9회. WBC·시범경기·올스타전은 여기서 걸러진다(함정 8). */
    suspend fun prefetchSeason(year: Int) {
        val start = seasonStart()
        for (month in 3..11) {
            api.scheduleMonth("%04d%02d".format(year, month)).body().games
                .filter { it.isKboRegular(start) }
                .forEach { saveSummary(it.toSummary()) }
        }
    }

    /** 하루치 최신화 — 오늘 화면 진입 시 1회, 라이브 중엔 20초마다(Step 6). */
    suspend fun refreshDay(date: LocalDate) {
        val start = seasonStart()
        api.scheduleDay(date.format(apiDay)).body().games
            .filter { it.isKboRegular(start) }
            .forEach { saveSummary(it.toSummary()) }
    }

    private suspend fun saveSummary(s: GameSummary, innings: List<InningRuns>? = null) {
        val entity = s.toEntity()
        // 함정 7: 변경 감지 필드가 없다 → 기존 행과 같으면 DB 쓰기 스킵 (불필요한 Flow 재방출 방지)
        if (innings == null && dao.find(s.id) == entity) return
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
노게임은 <code>state:"c"</code>로 바뀌면서 매퍼가 이닝을 빈 배열로 만듭니다(Step 3 함정 3). <code>saveGame</code>은 upsert라 이전에 저장된 부분 이닝 행이 남을 수 있으니, <code>innings</code>가 비어 있고 상태가 <code>CANCELED</code>면 <code>DELETE FROM innings WHERE gameId = :id</code>를 한 번 태우세요(<code>GameDao</code>에 <code>clearInnings</code> 추가). 화면은 <code>CANCELED</code>면 라인스코어를 그리지 않으므로 표시에는 영향이 없지만 DB를 깨끗이 두는 편이 낫습니다.
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
    wentExtra = wentExtra,
    venueShort = KBO_TEAMS[homeTeamId]?.home,
    homeStarter = homeStarter, awayStarter = awayStarter,
)

fun GameSummary.toEntity() = GameEntity(
    gameId = id, startsAtEpoch = startsAt.epochSecond, leagueDate = leagueDate.toString(),
    status = status.name, statusLabel = statusLabel,
    homeTeamId = home.id, homeName = home.nameKo, homeCode = home.code,
    awayTeamId = away.id, awayName = away.nameKo, awayCode = away.code,
    homeRuns = homeRuns, awayRuns = awayRuns, winner = winner?.name,
    wentExtra = wentExtra, homeStarter = homeStarter, awayStarter = awayStarter,
)
```

(`saveSummary`의 `s.toEntity()`가 이 함수입니다. `data class` 동등 비교가 곧 쓰기 스킵 조건이므로 **엔티티에 갱신 시각 같은 필드를 넣지 마세요** — 넣는 순간 매번 달라져 스킵이 안 됩니다. `StandingEntity.toDomain()`·`Standing.toEntity(year)`는 Step 8에서 순위와 함께 만듭니다.)

## 5. 시즌 프리페치 워커

`data/sync/PrefetchWorker.kt` — 앱 시작 시 1회, 이후 하루 1회.

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

`App.kt`의 `onCreate`에서 unique work로 등록합니다(네트워크 제약 + 지수 backoff). 잔여 경기 재편성(9월 이후 새 seq)은 하루 1회 재실행으로 자연히 들어옵니다 — 이미 있는 행은 동등 비교로 스킵되므로 비용이 거의 없습니다.

## 6. 통합 테스트

`app/src/test/.../RepositoryTest.kt` — MockWebServer로 9개 월을 순회하는지, 3월 fixture의 WBC·시범경기 행이 Room에 들어가지 않는지, 같은 응답을 두 번 받으면 DB 쓰기가 한 번뿐인지, 오프라인에서 Room이 읽히는지 검증합니다. `code:"01"` 봉투를 주면 `WisetotoException`으로 실패하고 Room이 비어 있지 않은지도 함께 봅니다.

```bash
./gradlew :app:testDebugUnitTest
```

<div class="checkpoint"><span class="t"></span> 앱을 한 번 실행해 프리페치가 돌게 한 뒤 <strong>비행기 모드</strong>로 바꿔도, <code>observeByDate</code>로 과거/미래 날짜의 경기가 조회되면 성공. (아직 화면은 없으니 로그나 DB Inspector로 확인)</div>

<div class="pager">
<a href="#/labs/step-3">← Step 3</a>
<a href="#/labs/step-5">Step 5 · 공통 컴포넌트 →</a>
</div>
