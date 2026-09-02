# DiamondScore 구현 계획

> 기준일: 2026-08-02 · 통합·재개편: 2026-08-23 (단일 계획 문서)
> 전제: **개인/포트폴리오 용도**, **백엔드 서버 없음(앱에서 직접 호출)**
> 데이터 소스: **SofaScore API (`api.sofascore.com/api/v1`)**, KBO `uniqueTournament.id = 11204`
> 스택: Kotlin 2.4 · AGP 9.4 · Compose · Navigation 3 · Retrofit 3 · Coil 3 · KSP2 (전체 표 §5.4, 2026-09-02 실측)
> 엔드포인트 분석 원자료(전체 목록·난독화 매핑·추출 스크립트)는 공개 저장소에서 제외한 별도 로컬 자료다.

> **이 문서가 프로젝트의 유일한 계획 문서다.** 제품 요구사항(무엇을)과 구현 계획(어떻게)을 한곳에
> 담는다. 이전에는 실행 계획(REALTIME)·구현 계획(IMPLEMENTATION)·제품 기획서(PRD) 3개로 나뉘어
> 혼선이 있었다 — 2026-08-23 개인용 트랙(실제 구현)을 본문으로 통합하고 구조를 재개편했다.
>
> **문서 지도**: §1 제품(무엇을) → §2 데이터 현실 → §3~§7 설계(어떻게) → §8 단계 → §9~§12 검증·운영 →
> §12~§13 부록. 공개 배포 확장(BFF·단계배포)은 §13 부록 B.

---

# I. 제품 (무엇을 만드는가)

## 1. 제품 개요

### 1.1 정의와 사용자

**한 줄 정의**: KBO 경기 일정·실시간 스코어·경기 상세·팀 정보·리그 순위를 빠르게 탐색하는 한국어
Android 앱. 핵심 경험은 *"오늘 경기 상황을 3초 안에 파악하고, 한 번의 탭으로 경기·팀 상세로 이동"*.

**사용자 유형**: ① 라이트 팬(오늘 시작 시각·현재 점수만) ② 구단 팬(즐겨찾기 팀 일정·결과 반복)
③ 기록 팬(순위·상세 기록 — 상당수는 P1).

**탐색 구조**: 최상위 4개 목적지 — `경기` · `순위` · `팀` · `즐겨찾기`. 선수는 팀/경기 문맥에서 진입.

### 1.2 범위와 우선순위

우선순위는 **데이터 커버리지(§2.3)가 결정한다.** SofaScore가 KBO에 주지 않는 것은 억지로 만들지 않는다.

| 우선순위 | 항목 |
|---|---|
| **P0 (SofaScore로 완결)** | 날짜별 경기 목록(예정/진행/종료/취소·연기), 라이브 카드(총점+상태+마지막 갱신), 경기 상세(이닝별 라인스코어), 2026 정규시즌 순위, 팀 상세(정보·구장·감독·최근/예정 경기), 팀 즐겨찾기, 오프라인 캐시, 다크·접근성·태블릿/폴더블 |
| **P1 (보조 소스 필요, 아래)** | 문자중계, 라인업, 투수/타자 경기 기록, 선수 상세·검색, 경기 알림, 위젯, 공유 카드, 영어 UI |
| **제외** | 베팅·예측·결제, 계정·채팅, 영상·오디오 중계, 자동 기사 생성, 허가 없는 데이터 수집/이미지 핫링크 |

**범위 제외의 근거 (§2.3)**: 볼카운트·주자·투수/타자·라인업·박스스코어·선수 기록·문자중계는
SofaScore가 KBO에 제공하지 않는다. **UI에 자리도 만들지 않는다** — 추정값으로 채우는 것은 표시
원칙(§1.3 "추정값을 생성하지 않는다")에 정면으로 위배된다.

**P1 보조 소스**: 위 제외 항목이 반드시 필요하면 별도 소스를 `KboEnrichmentSource`로 추가한다.
조사 결과 국내 소스(`api-gw.sports.naver.com`)가 볼카운트·주자·투수/타자·라인업·박스스코어·문자중계·
한국어 선수명을 제공한다. **단 P1이며 MVP는 SofaScore 단독으로 완결한다.** 두 소스 결합 시 경기 ID
매칭(팀 + 시작 시각 기준)이라는 난이도가 추가된다.

**개인용 트랙 유의**: 개인/포트폴리오 용도이므로 스토어 공개 배포 게이트(라이선스·production 차단)는
적용하지 않는다. **공개 배포로 전환하면 §13 부록 B가 선행 조건이 된다.** 개인 사용도 SofaScore
이용약관의 개인용 한정·자동요청 제한을 존중하고, 로고·선수 이미지는 재배포하지 않는다.

### 1.3 화면 명세

**경기 탭**: 상단에 오늘/이전·다음 날짜/날짜 선택기(날짜 조회 설계는 §3.2). 본문은 진행 중 → 예정 →
종료 순 또는 시작 시각 순. 카드는 팀·로고·점수·상태·경기장·시작 시각, 진행 중은 라이브 강조와 마지막
갱신 시각. 빈 날짜는 빈 상태 + 가장 가까운 경기일로 이동하는 액션.

**경기 상세**:
- **스코어보드**: 팀, 총점, 경기 상태, 시작 시각·경기장. **원정팀 먼저 표시**(§3.4-4).
- **라인스코어**: 1~9회 및 연장 이닝을 동적으로(§4.3), `R/H/E`는 공급될 때만 노출.
- **현재 상황(볼·스트라이크·아웃, 주자)**: *데이터가 완전하고 계약상 제공될 때만.* KBO는 현재
  미제공(§2.3)이므로 **P1**, 그 전에는 자리도 만들지 않는다.
- **탭**: 요약 / 문자중계(P1) / 라인업·기록(P1). 숨겨진 탭이 딥링크·back stack을 깨지 않게 한다.

**순위**: 시즌 선택, 순위·경기수·**승-패-무**(무는 파생 §3.4-1)·승률·게임차·득실차·진출권 배지.
공급되지 않는 컬럼은 `-`가 아니라 컬럼 자체를 숨긴다. 동률은 앱에서 재계산하지 않고 공급자 순서를 따른다.

**팀**: 10개 구단 목록 + 즐겨찾기. 팀 상세는 기본 정보·구장·감독·최근 5경기·다음 5경기. 로고 허가가
없으면 문자 모노그램 + 팀 컬러 대체 자산.

**선수(P1)**: 이름·등번호·포지션·투타·소속. 타자/투수 스키마 분리. **KBO 선수 데이터 미제공(§2.3)이라
MVP 범위 밖.**

**즐겨찾기·설정**: 즐겨찾는 팀 목록, 테마(시스템/라이트/다크), 데이터 출처(SofaScore)·개인정보·
오픈소스 라이선스 표기. 알림은 P1.

**표시 원칙 (모든 화면 공통)**:
- **UI에서 추정값을 생성하지 않는다.** 서버가 준 값만 표시하고, 라이브 상태 문자열은 원문 그대로 쓴다(§4.2).
- `null`/미제공/미집계를 `0`과 구분한다.
- 색만으로 라이브/종료/승패를 전달하지 않고 텍스트·아이콘을 함께 쓴다(§1.5).

### 1.4 사용자 여정 (검증 대상)

1. 실행 → 오늘 경기에서 진행 중 확인 → 경기 상세.
2. 경기 상세 → 이닝별 점수·상태 확인 → 팀 상세로 이동.
3. 순위 → 팀 선택 → 팀 상세의 최근/예정 경기.
4. 오프라인 실행 → 마지막 데이터 + "마지막 갱신" → 연결 복구 후 자동 동기화.

### 1.5 디자인·접근성

**컨셉: 브로드캐스트 × 에디토리얼** — 라이브는 중계 그래픽처럼 강렬하게(초대형 스코어·팀컬러 글로우),
목록·표·정보는 라인·여백으로 절제. **다크 기본 + 라이트 변형.** Codelabs Step 2가 이 토큰을 구현한다.

| 역할 | 다크 | 라이트 |
|---|---|---|
| background | `#07080B` | `#FBFAF7` |
| surface(라이브 카드) | `#0C0E14` | `#FFFFFF` |
| onSurface(본문) | `#EDEFF3` | `#161513` |
| onSurfaceVariant(muted) | `#8B90A0` | `#6B6862` |
| outline / outlineVariant | `#191C24` / `#15171E` | `#E4E0D8` / `#ECE8E0` |
| primary(라이브·강조) | `#FF2D4B` | `#D21F3C` |
| gold(진출권·즐겨찾기) | `#E7B24A` | `#B98900` |
| win / loss | `#39D98A` / `#C83250` | `#1E9E5E` / `#C83250` |

- 폰트: **Bebas Neue**(스코어·헤더·큰 숫자) + **Archivo + Noto Sans KR**(본문·UI), 표의 작은 숫자는 등폭(tabular).
- 리그 레드 `#AE0D1D`는 브랜드 기준색, UI 액센트는 대비를 위해 `#FF2D4B`(다크)/`#D21F3C`(라이트).
- 라이브 = 레드 그라디언트 보더 히어로 카드, 예정·종료·순위 = 카드 없이 헤어라인 라인 로우.
- **팀 컬러는 강조에만** 쓰고(§3.4-5의 자체 컬러 자산) 텍스트 대비 WCAG AA 유지.
- 최소 터치 48dp, 동적 글꼴 200%에서 정보 손실 없이 스크롤(특히 라인스코어).
- 점수 변경 애니메이션 300ms 이내, 시스템 "애니메이션 줄이기" 존중.
- 로고·아이콘에 `contentDescription`, 장식 이미지는 null. 로딩 skeleton은 TalkBack에 안 읽히게.
- Compose semantics를 접근성과 UI 테스트의 공통 계약으로 관리.

### 1.6 성공 지표(SLO)와 수용 기준

| 구분 | MVP 목표 |
|---|---:|
| Crash-free users | 99.5% 이상 |
| 콜드 스타트 p75 | 2.5초 이하 (중급 실기기) |
| 캐시 있을 때 첫 콘텐츠 p75 | 1초 이하 |
| 라이브 화면 신선도 p95 | 마지막 갱신 후 30초 이내 |
| API 성공률 | 99.0% 이상 (앱 → SofaScore 직접) |
| 접근성 자동 검사 | 차단 이슈 0건 |
| 핵심 흐름 UI 테스트 | 100% 통과 |

신선도 SLO는 라이브 스키마 관측(`DS-002`, §8) 이후 실제 갱신 지연에 맞춰 조정한다.

**MVP 수용 기준**:
- 오늘 및 선택 날짜의 모든 KBO 경기를 볼 수 있다.
- 라이브 점수·이닝이 화면이 보이는 동안 자동 갱신된다.
- 경기 → 팀, 순위 → 팀 이동과 back 문맥 복원이 된다.
- 네트워크 단절 시 마지막 성공 데이터와 갱신 시각이 보인다.
- 데이터 결측·일부 필드 부재에도 크래시하지 않는다.
- §2.3 범위 밖 항목(볼카운트·선수 기록 등)의 UI 자리를 만들지 않는다.

---

# II. 데이터 (무엇을 알고 있는가)

## 2. 데이터 현실 — SofaScore KBO 실측

2026-08-02에 SofaScore API를 직접 호출해 확인한 사실이다. **추정이 아니라 실제 응답 기준**이며,
확인하지 못한 항목은 명시적으로 미검증으로 표기했다.

### 2.1 접근 가능성

SofaScore API는 **정상 접근되며 실제 KBO 데이터를 반환한다.**

| 확인 항목 | 결과 |
|---|---|
| `GET /unique-tournament/11204/seasons` | ✅ 200, 2014~2026 시즌 13개 |
| `GET /unique-tournament/11204/season/88022/standings/total` | ✅ 200, 10개 구단 순위 |
| `GET /unique-tournament/11204/season/88022/events/next/0` | ✅ 200, 16경기 |
| `GET /event/15290567` | ✅ 200, 구장·감독·이닝별 점수 |

> **주의**: 2026-08-23 APK 분석 환경에서는 같은 엔드포인트가 `403`이었다(웹페이지조차 403).
> 2026-09-03 재검증 결과 원인은 IP가 아니라 **HTTP 클라이언트의 TLS/HTTP2 핑거프린트**다 — 같은 IP에서
> curl·Python·Node·JDK `HttpClient`는 403, **OkHttp와 Chrome은 200**(§13 A-3). 앱 스택(OkHttp)은 영향 없음.
> 터미널 확인은 curl 대신 `labs/tools/sofa-fetch.sh`(OkHttp)를 쓴다. 실기기 확인은 `DS-001`(§8).

### 2.2 확정된 식별자

| 항목 | 값 |
|---|---|
| KBO uniqueTournament id | `11204` |
| Baseball sport id | `64` |
| South Korea category id | `1385` |
| tournament id | `108842` |
| **2026 시즌 seasonId** | **`88022`** |
| 리그 색상 | primary `#ae0d1d`, secondary `#44a0cb` |

시즌 ID는 매년 바뀐다(2025=71354, 2024=58206, 2023=48596, 2022=46676). **하드코딩하지 말고**
`/seasons`의 첫 항목을 현재 시즌으로 사용한다.

**10개 구단 팀 ID** (`/standings/total`에서 확보)

| teamId | name | nameCode | 한국어 표기(앱 자체 매핑) |
|---:|---|---|---|
| 188409 | Kt Wiz | WIZ | KT 위즈 |
| 188245 | Samsung Lions | LIO | 삼성 라이온즈 |
| 188257 | LG Twins | TWI | LG 트윈스 |
| 188248 | Doosan Bears | BEA | 두산 베어스 |
| 188247 | Kia Tigers | TIG | KIA 타이거즈 |
| 188243 | Hanwha Eagles | EAG | 한화 이글스 |
| 188253 | NC Dinos | DIN | NC 다이노스 |
| 188246 | Lotte Giants | GIA | 롯데 자이언츠 |
| 188244 | SSG Landers | SSG | SSG 랜더스 |
| 188258 | Kiwoom Heroes | KIH | 키움 히어로즈 |

**한국어 팀명은 API에 없다.** `fieldTranslations.nameTranslation`은 아랍어·힌디어·벵골어·러시아어만
제공하고 `ko` 키가 없다. 10개 구단뿐이므로 위 매핑을 앱 리소스로 하드코딩한다. 팀 ID는 시즌이 바뀌어도 안정적이다.

### 2.3 커버리지 — "득점 전용(runs-only)"

야구 전용 하위 리소스를 전수 확인한 결과다. **이것이 제품 범위(§1.2)를 결정한다.**

| 엔드포인트 | 결과 |
|---|---|
| `/event/{id}/incidents` | ❌ **404** |
| `/event/{id}/lineups` | ❌ **404** |
| `/event/{id}/statistics` | ❌ **404** |
| `/sport/baseball/scheduled-events/{date}` | ❌ **404** (2026-07-28 / 08-02 / 08-04 전부) |
| `uniqueTournament.hasEventPlayerStatistics` | ❌ **`false`** |

| 제공됨 ✅ | 제공되지 않음 ❌ |
|---|---|
| 경기 일정·결과 | 볼-스트라이크-아웃 카운트 |
| 총점 (`current`) | 주자 상황 (1·2·3루) |
| **이닝별 득점** (연장 포함) | 현재 투수 / 타자 |
| 경기 상태 (`status`) | 타순·라인업 |
| 승패 (`winnerCode`) | 박스스코어 (안타·실책·볼넷) |
| 변경 감지 (`changes`) | 선수 기록 |
| 순위 (승·패·승률·게임차) | 문자중계 / 플레이 이벤트 |
| 팀 정보·감독·구장·수용인원 | 한국어 팀명·선수명 |

### 2.4 라이브 스키마 — 미검증 (게임 데이 스파이크 필수)

`GET /sport/baseball/events/live`는 **200을 반환하되 `{"events":[]}` 였다.** 확인 시점에 라이브
경기가 없었기 때문이다(2026-08-03 월요일 = KBO 휴식일, 다음 경기 08-04 18:30 KST).

따라서 다음은 **확인하지 못했다.**

- 라이브 경기의 `status.code` / `status.description` 실제 값 (진행 이닝 표현 방식)
- 진행 중 `homeScore.innings`의 미진행 이닝 표현 (키 부재 / `run: 0` / `null`)
- `time` 객체가 진행 중에 갖는 필드
- 라이브 갱신 주기와 지연

관측된 `status` 값은 3개뿐이다.

```
{ "code": 0,   "description": "Not started", "type": "notstarted" }
{ "code": 100, "description": "Ended",       "type": "finished"   }
{ "code": 110, "description": "AET",         "type": "finished"   }   // 연장 종료
```

**대응 원칙**: `status.type`을 1차 기준으로 쓰고 `status.code`는 보조로만 쓴다. `type`은
`notstarted / inprogress / finished / canceled / postponed / suspended`로 안정적이고, `code`는
스포츠별 확장 값이 많다. 미지의 `code`가 와도 `type`으로 안전하게 분류된다.

## 3. 데이터 소스 계약

Base URL: `https://api.sofascore.com/api/v1`

### 3.1 사용 엔드포인트 (전부 실측 200)

| # | 용도 | 엔드포인트 | 응답 규모 |
|---|---|---|---|
| 1 | 시즌 목록 | `GET /unique-tournament/11204/seasons` | 13 시즌 |
| 2 | 순위 | `GET /unique-tournament/11204/season/{seasonId}/standings/total` | 10 rows |
| 3 | 지난 경기 | `GET /unique-tournament/11204/season/{seasonId}/events/last/{page}` | ~16/page |
| 4 | 예정 경기 | `GET /unique-tournament/11204/season/{seasonId}/events/next/{page}` | ~16/page |
| 5 | 라운드별 경기 | `GET /unique-tournament/11204/season/{seasonId}/events/round/{n}` | 16 (4~5일 범위) |
| 6 | 경기 상세 | `GET /event/{eventId}` | 구장·감독·이닝 |
| 7 | **라이브 경기** | `GET /sport/baseball/events/live` | 전 종목 야구 → 11204 필터 |
| 8 | 팀 예정 경기 | `GET /team/{teamId}/events/next/{page}` | 20 |
| 9 | 팀 지난 경기 | `GET /team/{teamId}/events/last/{page}` | — |
| 10 | 팀 로고 | `GET /team/{teamId}/image` | 이미지 |
| 11 | 리그 로고 | `GET /unique-tournament/11204/image` | 이미지 |

### 3.2 날짜 기반 조회가 없다 → 시즌 전체 프리페치 설계

`/sport/baseball/scheduled-events/{date}`가 404이므로 **"8월 2일 경기"를 직접 조회할 수 없다.**
화면 명세(§1.3 경기 탭)의 날짜 네비게이션을 유지하려면 설계를 바꿔야 한다.

**해법: 시즌 전체를 Room에 프리페치하고, 날짜 조회는 로컬 쿼리로 처리한다.**

```
1회 초기 동기화:  /events/next/{0,1,2,...}  +  /events/last/{0,1,2,...}   → 빈 페이지까지 반복
                  ↓
            Room GameEntity (leagueDate 인덱스)
                  ↓
날짜 네비게이션:  SELECT * FROM games WHERE leagueDate = ?   ← 네트워크 0회
```

이게 오히려 더 나은 아키텍처다.

- KBO 정규시즌은 10팀 × 144경기 ÷ 2 = **720경기.** 경기당 ~500B → 전체 400KB 미만으로 Room에 여유롭게 들어간다
- 날짜 이동이 즉시 응답한다 (네트워크 왕복 없음)
- 오프라인에서 전 시즌 일정을 볼 수 있다
- `/events/next/*`만 주기적으로 재조회하면 우천 순연으로 인한 일정 변경이 반영된다

페이지네이션에 `hasNextPage` 필드가 없으므로 **빈 배열이 올 때까지 page를 증가**시킨다. 안전장치로
최대 페이지 수를 60으로 제한한다.

> APK 정적 분석에서 다른 날짜 조회 경로 후보를 발견했다(§13 A-1). 검증되면 프리페치는 유지하되
> 증분 갱신에 활용한다.

**날짜 경계**: `startTimestamp`는 epoch 초(UTC)다. `leagueDate`는 반드시 `Asia/Seoul`로 변환해
저장한다. 기기 타임존을 쓰면 해외에서 날짜가 밀린다.

### 3.3 응답 스키마 (실측)

**Event 객체** — 목록·상세 공통

```json
{
  "id": 15290563,
  "slug": "doosan-bears-ssg-landers",
  "customId": "ToAbsWoAb",
  "startTimestamp": 1785231000,
  "status":  { "code": 110, "description": "AET", "type": "finished" },
  "winnerCode": 2,
  "roundInfo": { "round": 1 },
  "time":    { "currentPeriodStartTimestamp": 1785241951 },
  "changes": { "changes": ["homeScore.overtime", "homeScore.innings"],
               "changeTimestamp": 1785242358 },
  "feedLocked": false,
  "homeTeam": { "id": 188244, "name": "SSG Landers",  "nameCode": "SSG" },
  "awayTeam": { "id": 188248, "name": "Doosan Bears", "nameCode": "BEA" },
  "homeScore": {
    "current": 1, "display": 1,
    "period1": 1, "period2": 0, "…": 0, "period9": 0,
    "normaltime": 1,
    "overtime": 0,
    "innings": { "inning1": {"run": 1}, "…": {}, "inning10": {"run": 0} }
  }
}
```

`/event/{id}` 는 위에 추가로 제공한다.

```
season { id, name: "KBO League 2026", year: "2026" }
venue  { name: "Daejeon Hanwha Life Ballpark", slug, hidden: true,
         city { name: "Daejeon" }, country { alpha2: "KR" },
         stadium { name, capacity } }
homeTeam.manager { name: "Kim Kyung-moon" }
homeTeam.venue.stadium { name, capacity }
uniqueTournament { primaryColorHex, secondaryColorHex, hasRounds: true,
                   hasEventPlayerStatistics: false,
                   displayInverseHomeAwayTeams: true }
periods { inning1 … inning9, extra1 }
```

**Standings row 객체**

```json
{
  "id": 2066536,
  "position": 1,
  "team": { "id": 188409, "name": "Kt Wiz", "nameCode": "WIZ", "slug": "kt-wiz",
            "teamColors": { "primary": "#374df5", "secondary": "#374df5", "text": "#ffffff" } },
  "matches": 97, "wins": 59, "losses": 36,
  "scoresFor": 544, "scoresAgainst": 461,
  "percentage": 0.621,
  "gamesBehind": 0,
  "scoreDiffFormatted": "+83",
  "promotion": { "id": 2, "text": "Finals" }
}
```
+ 최상위 `updatedAtTimestamp`.

### 3.4 반드시 처리해야 하는 함정 (실측 중 발견)

이 7개는 그냥 매핑하면 확실히 버그가 된다.

1. **무승부 필드가 없다.** KBO는 무승부가 있는데 standings row에 `draws`가 없다. KT: `matches 97, wins 59, losses 36` → 59+36=95 ≠ 97. **무승부 = `matches - wins - losses`로 파생**해야 한다. §1.3(순위)이 요구한 "승-패-무" 컬럼은 이 계산 없이는 못 만든다.

2. **연장전이 두 곳에 이중 표현된다.** `period1..period9`는 9회에서 멈추고, 10회 이후는 `overtime` 필드와 `innings.inning10`에만 나타난다. **라인스코어는 `period*`가 아니라 `innings` 맵을 파싱**해야 한다. `period*`만 읽으면 연장 경기의 결승점이 사라진다(SSG 1 : 2 두산 경기에서 실제로 10회 득점이 `period*`에 없음).

3. **`innings` 맵의 키가 동적이다.** `inning1`…`inning9`, 연장 시 `inning10`, `inning11`… 고정 필드로 선언할 수 없다. `Map<String, InningRun>`으로 받아 `"""inning(\d+)"""` 정규식으로 번호를 뽑고 정렬한다.

4. **`displayInverseHomeAwayTeams: true`.** SofaScore는 KBO를 **원정팀 먼저** 표시한다. `homeTeam`/`awayTeam` 데이터는 정확하지만, KBO 관행(원정 @ 홈)에 맞추려면 이 플래그를 UI 표시 순서에 반영해야 한다. 무시하면 국내 팬이 보는 순서와 반대가 된다.

5. **`teamColors`가 전부 동일하다.** 10개 구단 모두 `primary: "#374df5"`(같은 파란색)로 온다. 팀 식별에 쓸 수 없다. **구단 컬러는 앱 리소스로 자체 정의**한다(§1.5의 팀 컬러 강조).

6. **`status.code`를 신뢰하지 말고 `status.type`을 쓴다.** 관측된 code는 0/100/110 3개뿐이고 라이브 code는 미검증이다(§2.4). `type` 기준으로 분기하고 미지의 값은 `UNKNOWN`으로 떨어뜨린다.

7. **`venue.hidden: true`.** 구장 정보에 숨김 플래그가 있다. 표시 정책을 정해야 한다(이 계획에서는 `stadium.name`이 있으면 표시).

추가 주의: `winnerCode`는 `1`=홈, `2`=원정, `3`=무승부로 추정되나 **무승부 표본을 확보하지 못했다** → `DS-002`에서 확정. 확정 전에는 `status.type == "finished"`가 아니면 무조건 `null`로 매핑한다.

---

# III. 설계 (어떻게 만드는가)

## 4. 도메인 모델과 매핑

```kotlin
@JvmInline value class EventId(val value: Long)
@JvmInline value class TeamId(val value: Long)
@JvmInline value class SeasonId(val value: Long)

enum class GameStatus { SCHEDULED, LIVE, FINAL, CANCELED, POSTPONED, SUSPENDED, UNKNOWN }
enum class Winner { HOME, AWAY, DRAW }

data class GameSummary(
    val id: EventId,
    val startsAt: Instant,          // startTimestamp(초) → Instant
    val leagueDate: LocalDate,      // Asia/Seoul 기준, 인덱스 키
    val status: GameStatus,
    val statusLabel: String,        // status.description 원문 (추정 없이 그대로 표시)
    val home: TeamRef, val away: TeamRef,
    val homeRuns: Int?, val awayRuns: Int?,   // 경기 전에는 null (0이 아님)
    val winner: Winner?,            // FINAL일 때만 non-null
    val wentExtra: Boolean,         // status.code == 110 || innings에 10회+ 존재
    val changeTimestamp: Instant?,  // changes.changeTimestamp — 델타 감지용
)

data class LineScore(val innings: List<InningRuns>, val homeTotal: Int, val awayTotal: Int)
data class InningRuns(val number: Int, val home: Int?, val away: Int?)  // null = 미진행

data class GameDetail(
    val summary: GameSummary,
    val lineScore: LineScore,
    val venue: Venue?,              // stadium.name, city, capacity
    val homeManager: String?, val awayManager: String?,
    val seasonName: String,
    val round: Int?,
)

data class Standing(
    val position: Int, val team: TeamRef,
    val games: Int, val wins: Int, val losses: Int,
    val draws: Int,                 // 파생: games - wins - losses  (§3.4-1)
    val winPct: Double, val gamesBehind: Double,
    val runsFor: Int, val runsAgainst: Int, val runDiff: String,
    val playoffTier: String?,       // promotion.text
)
```

### 4.1 상태 매핑

```kotlin
fun mapStatus(s: StatusDto): GameStatus = when (s.type) {
    "notstarted" -> GameStatus.SCHEDULED
    "inprogress" -> GameStatus.LIVE
    "finished"   -> GameStatus.FINAL       // code 100(Ended), 110(AET) 모두
    "canceled"   -> GameStatus.CANCELED
    "postponed"  -> GameStatus.POSTPONED
    "suspended"  -> GameStatus.SUSPENDED
    else -> GameStatus.UNKNOWN.also { logUnknownStatus(s.type, s.code) }
}
```

`statusLabel`에는 `status.description`을 **원문 그대로** 담는다. 라이브 표현이 미검증이므로(§2.4)
앱이 "5회말" 같은 문자열을 만들어내지 않고 서버가 준 값을 표시한다. 파싱 성공 시에만 아이콘·강조를 추가한다.

### 4.2 라인스코어 매핑 (연장 처리)

```kotlin
fun parseInnings(home: Map<String, InningRunDto>, away: Map<String, InningRunDto>): List<InningRuns> {
    val re = Regex("""inning(\d+)""")
    val numbers = (home.keys + away.keys).mapNotNull { re.matchEntire(it)?.groupValues?.get(1)?.toIntOrNull() }
    return numbers.distinct().sorted().map { n ->
        InningRuns(n, home["inning$n"]?.run, away["inning$n"]?.run)
    }
}
```

`period*` 필드는 **읽지 않는다**(§3.4-2). 최소 9이닝은 항상 열을 확보하고, 그 이상은 데이터에 있는 만큼만 표시한다.

### 4.3 결측·정정 규칙

- `null`/미제공/미집계를 `0`과 구분한다(§1.3 표시 원칙).
- 점수·기록 정정은 `changes.changeTimestamp` 기준 최신이 승리한다(§6 쓰기 규칙).
- 공급자가 필드를 제거하거나 타입을 바꿔도 앱이 죽지 않게 관대한 파서(§5.3 `ignoreUnknownKeys`) +
  명시적 매퍼로 격리한다.

## 5. 아키텍처와 기술 스택

```
Compose UI  ──events──▶  ViewModel  ──────────────▶  Repository
    ▲                                                    │
    └──── StateFlow<UiState> ◀── Room(SSOT) ◀────────────┘
                                                          ▼
                                                 KboDataSource
                                                 └ SofaScoreDataSource (Retrofit)
                                                 └ FakeDataSource (fixture, 테스트)
```

**UseCase 계층은 두지 않는다.** 이 앱의 화면-데이터 관계는 1:1이고, 재사용되는 도메인 로직은
`parseInnings`·`draws` 파생처럼 순수 함수라 매퍼에 있다. ViewModel과 Repository 사이에 클래스를 한 겹
더 넣으면 위임만 하는 파일이 화면 수만큼 생긴다. 로직이 두 화면에서 실제로 겹칠 때 그때 만든다.

Android 공식 가이드의 계층·단방향 흐름·SSOT 원칙을 따른다. UI는 `ViewModel`의 불변 `UiState`를
`collectAsStateWithLifecycle()`로 구독하고 이벤트를 위로 올린다. 개인용 트랙은 BFF 계층이 없으므로
**DTO→도메인 변환 책임을 앱이 진다.** BFF 계약·서버 보안은 공개 배포 시에만 필요하다(§13 부록 B).

### 5.1 패키지 구조 (1인 개발)

14개 모듈은 1인 개발에서 빌드 오버헤드만 만든다. 단일 `:app` + 패키지 경계로 시작한다.

```
com.diamondscore
├─ DiamondScoreApp.kt   ← Nav3 back stack + entryProvider (여기만 전체 화면을 안다)
├─ core/
│   ├─ common/          time, KboTeams(순수 표), Result — Compose·Android 없음
│   ├─ navigation/      DsNavKeys(NavKey) — 순수 Kotlin + kotlinx.serialization
│   ├─ designsystem/    Color, Type, Theme, TeamColors — 도메인을 모른다
│   └─ ui/              GameCard, LineScoreTable, StandingRow, States, DsHelpers — 도메인은 알고 화면은 모른다
├─ data/
│   ├─ remote/          SofaScoreApi, dto/, mapper/, di/NetworkModule
│   ├─ local/           entity/, dao/, mapper/, di/DatabaseModule, DiamondScoreDatabase
│   ├─ repository/      Games, Standings, Teams, Favorites, SettingsStore
│   └─ sync/            PrefetchWorker
├─ domain/model/        GameSummary, GameDetail, Standing, TeamDetail, TeamRef …
└─ feature/             games/, gamedetail/, standings/, teams/, favorites/, settings/
```

규칙 2개만 지킨다:

1. **`feature`·`core/ui`·`core/designsystem`은 `data`를 참조하지 않는다.** ViewModel이 주입받는 것은
   Repository뿐이다 — `SofaScoreApi`·DAO·`Entity`는 이름조차 나오지 않는다.
2. **DTO와 Room `Entity`는 `data` 밖으로 나가지 않는다.** 경계를 넘는 타입은 `domain/model`뿐이다.

파생 규칙 두 개가 여기서 나온다 — `core/designsystem`은 `domain`을 모르고(그래서 도메인을 아는
컴포넌트는 `core/ui`에 있다), `data`는 Compose를 모른다(그래서 한글 팀명 표는 `core/common`에,
팀 컬러는 `core/designsystem`에 나뉘어 있다). 화면끼리는 서로를 모르고, 이동은 `(Long) -> Unit`
콜백으로 위에 올려 `DiamondScoreApp.kt`가 `NavKey`로 바꾼다.

이 넷을 지키면 이후 모듈 분리(§5.5)는 기계적 작업이다.

### 5.2 직렬화와 OkHttp

네트워크는 **Retrofit 3 + OkHttp + kotlinx.serialization**(버전표 §5.4).

```kotlin
Json {
    ignoreUnknownKeys = true   // 필수
    coerceInputValues = true
    explicitNulls = false
}
```

`ignoreUnknownKeys = true`는 선택이 아니다. `/event/{id}` 응답은 `fieldTranslations`, `userCount` 등
앱에 불필요한 필드가 수십 개고 수시로 늘어난다.

```kotlin
OkHttpClient.Builder()
    .addInterceptor(SofaScoreHeaderInterceptor())   // UA, Accept, Accept-Language
    .addInterceptor(MinIntervalInterceptor())       // 호스트당 최소 요청 간격
    .cache(Cache(cacheDir.resolve("http"), 20L * 1024 * 1024))
    .callTimeout(10.seconds)
    .connectTimeout(5.seconds)
    .build()
```

Coil 3는 이 OkHttp 인스턴스를 공유한다(`coil-network-okhttp`). 응답 헤더의 `ETag` / `Cache-Control`
지원 여부는 `DS-003`에서 확인하고, 지원되면 조건부 요청으로 라이브 폴링 트래픽을 크게 줄인다.

### 5.3 도구 체인 (Kotlin 2.4 · AGP 9)

- **AGP 9는 Kotlin이 내장이다.** `org.jetbrains.kotlin.android`를 적용하지 않는다(새 DSL과 비호환).
  `android { kotlinOptions { } }`도 없어졌으니 컴파일러 옵션은 최상위 `kotlin { compilerOptions { } }`.
  AGP 9.4는 KGP 2.2.10을 동봉하므로 Kotlin 2.4를 쓰려면 루트 `buildscript`에서
  `classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:2.4.10")`으로 올린다.
- Compose 컴파일러는 Kotlin과 함께 배포 → `org.jetbrains.kotlin.plugin.compose`만 적용, 별도 버전 pin 없음.
- 어노테이션 처리는 전부 **KSP2**(Room·Hilt). kapt는 넣지 않는다. **KSP는 2.3.0부터 `<Kotlin>-<KSP>`
  접두사를 버린 독립 버전제**다(구 스킴은 `2.2.21-2.0.5`가 마지막). 그래서 `2.4.x-2.0.0` 같은 버전은
  존재하지 않는다 — `2.3.11`을 쓴다. Hilt는 KSP 2.3.x로 빌드된 **2.60 이상**이어야 짝이 맞는다.
- 시간 타입은 `java.time`(minSdk 26이라 desugaring 불필요).
- 릴리스는 **R8 full mode** + resource shrinking. 직렬화 DTO가 난독화로 사라지지 않는지 릴리스 빌드에서 검증.

### 5.4 스택 버전표

2026-09-02 기준 stable을 실측(Google Maven / Maven Central / services.gradle.org)해 확정했다.

| 항목 | 확정 버전 | 비고 |
|---|---|---|
| Build | **AGP 9.4.0, Gradle 9.7.1**, JDK 17 | AGP 9.4는 Gradle 9.6.0 이상 필수 |
| SDK | `compileSdk`/`targetSdk` 36, `minSdk` 26 | Play 신규 앱 요건(2026-08-31 발효)이 API 36. AGP 9.4는 37까지 지원하나 36으로 고정 |
| Language | **Kotlin 2.4.10** | AGP built-in Kotlin(2.2.10)을 루트 `buildscript`에서 승격 |
| UI | Compose BOM **2026.08.00** + Material 3 | ui 1.12.0 / material3 1.4.0을 BOM이 관리 |
| Compose 컴파일러 | `org.jetbrains.kotlin.plugin.compose` | Kotlin 동봉, 별도 버전 pin 없음 |
| Navigation | **Navigation 3 `1.1.7`** | `navigation3-runtime` + `navigation3-ui`. Nav2(`navigation-compose`)는 쓰지 않는다 |
| Nav3 보조 | `lifecycle-viewmodel-navigation3` 2.11.0, `adaptive-navigation3` **1.3.0** | 각각 ViewModel 스코핑, 목록-상세 2-pane |
| DI | **Hilt 2.60.1**(KSP2), `androidx.hilt` 1.4.0 | `hilt-lifecycle-viewmodel-compose`(Nav3용) + `hilt-work` |
| Annotation 처리 | **KSP 2.3.11**, kapt 미사용 | §5.3의 독립 버전제 주의 |
| Local | Room **2.8.4**(KSP2), DataStore Preferences 1.2.1 | |
| Background | WorkManager **2.11.2** | |
| Network | Retrofit **3.0.0** + OkHttp **5.5.0** + kotlinx.serialization **1.11.0** | 컨버터는 공식 `com.squareup.retrofit2:converter-kotlinx-serialization`(패키지 `retrofit2.converter.kotlinx.serialization`) |
| Images | Coil **3.6.1** (`coil-compose` + `coil-network-okhttp`) | OkHttp 인스턴스 공유 |
| Lifecycle | **2.11.0** | `lifecycle-runtime-compose`(`collectAsStateWithLifecycle`) |
| 기타 AndroidX | core-ktx **1.19.0**, activity-compose **1.13.0** | |
| Quality | JUnit 4.13.2, kotlinx-coroutines-test 1.11.0, Turbine 1.2.1, MockWebServer 5.5.0, Compose UI Test(BOM), room-testing, hilt-android-testing | |

동적 버전을 금지하고 version catalog에 고정한다(Codelabs Step 2가 전체 catalog). 서로 묶인 세 줄은
**Gradle ≥ 9.6 / KSP 2.3.x / Hilt ≥ 2.60**이며, 하나만 어긋나도 sync 단계에서 깨진다.

근거: [Compose BOM](https://developer.android.com/develop/ui/compose/bom) · [Compose 컴파일러](https://developer.android.com/develop/ui/compose/compiler) · [KSP](https://github.com/google/ksp/releases) · [Navigation 3](https://developer.android.com/guide/navigation/navigation-3) · [Room](https://developer.android.com/jetpack/androidx/releases/room) · [AGP 9.4](https://developer.android.com/build/releases/gradle-plugin) · [built-in Kotlin](https://developer.android.com/build/migrate-to-built-in-kotlin) · [Kotlin별 AGP 요건](https://developer.android.com/build/kotlin-support) · [Retrofit](https://square.github.io/retrofit/) · [Coil](https://coil-kt.github.io/coil/) · [Play target API](https://developer.android.com/google/play/requirements/target-sdk)

### 5.5 목표 모듈 구조와 적응형 UI

§5.1은 1인 개발용 단일 `:app` 패키지 경계다. 병렬 개발이 시작되면 아래로 승격하되, §5.1의 네 규칙을
그대로 모듈 경계로 굳힌다. **패키지 이름이 곧 모듈 이름이라 승격은 기계적이다.**

```
:app                       ← Nav3 back stack + entryProvider. 유일하게 모든 feature를 안다
:domain                    ← 순수 Kotlin. 모델만. 아무것에도 의존하지 않는다
:core:common               ← 순수 Kotlin. 시간·KBO 팀표·Result
:core:navigation           ← NavKey 정의. nav3-runtime + serialization만, Compose 없음
:core:designsystem         ← Compose. 토큰·테마·팀 컬러. :domain을 모른다
:core:ui                   ← Compose + :domain. 도메인을 아는 공용 컴포넌트
:core:network :core:database :core:testing
:data:sports               ← remote + local + repository + sync. DTO·Entity가 여기서 끝난다
:feature:games :feature:game-detail :feature:standings :feature:teams :feature:favorites :feature:settings
```

허용되는 의존 방향은 이것뿐이다:

```
:app → :feature:* → (:core:ui → :domain), :core:designsystem, :core:navigation, :data:sports(인터페이스 아님, 구현 주입)
:data:sports → :domain, :core:common, :core:network, :core:database
:core:designsystem → (Compose만)          # :domain 금지
:core:common, :domain → (순수 Kotlin)      # Android·Compose 금지
:core:navigation → nav3-runtime, serialization  # Compose 금지
```

- `:domain`은 Android SDK·Compose·Retrofit·Room에 의존하지 않는 순수 Kotlin 모듈(클린 아키텍처의 안정 핵).
- `:feature:*`는 서로를 참조하지 않는다. 화면 간 이동은 `(Long) -> Unit` 콜백으로 `:app`이 받아
  `NavKey`로 바꾼다.
- 모델은 `:domain`에만 둔다(`:core:model`을 따로 만들지 않는다 — 모델 소유 모듈이 둘이면 승격이 막힌다).

적응형 UI — Nav3에서는 back stack 하나에 `SceneStrategy`만 얹는다:
- compact: 단일 pane + bottom navigation
- medium: 단일/이중 pane + navigation rail
- expanded: 경기/팀 목록과 상세를 나란히 표시
- `adaptive-navigation3`의 `ListDetailSceneStrategy`가 `listPane()`/`detailPane()` 메타데이터를 보고
  창 크기에 따라 pane을 나눈다. 목적지 정의는 한 벌이고 predictive back도 `NavDisplay`가 처리한다.

근거: [적응형 목록-상세](https://developer.android.com/develop/adaptive-apps/guides/list-detail) · [Nav3 어댑티브](https://developer.android.com/guide/navigation/navigation-3/adaptive)

## 6. 로컬 저장소

Room을 읽기 SSOT로 쓴다. ViewModel은 항상 DAO의 `Flow`만 구독한다.

| Entity | PK | 인덱스 | 비고 |
|---|---|---|---|
| `GameEntity` | `eventId` | `leagueDate`, `homeTeamId`, `awayTeamId` | 시즌 전체 720행 |
| `InningRunEntity` | `(eventId, inning)` | `eventId` | home/away nullable |
| `StandingEntity` | `(seasonId, teamId)` | — | `draws` 파생값 저장 |
| `TeamEntity` | `teamId` | — | nameKo, 자체 팀 컬러, 구장, 감독 |
| `SeasonEntity` | `seasonId` | — | `isCurrent` |
| `FavoriteEntity` | `(type, targetId)` | — | |
| `SyncMetaEntity` | `resourceKey` | — | `lastSuccessAt`, `etag`, `lastError` |

**쓰기 규칙**

- 경기 상세 갱신은 `GameEntity` + `InningRunEntity`를 **한 트랜잭션**으로 upsert. 총점과 이닝이 불일치하는 중간 상태가 UI에 보이면 안 된다.
- `changes.changeTimestamp`가 저장값과 같으면 **DB 쓰기를 건너뛴다.** 불필요한 `Flow` 재방출과 recomposition을 막는 가장 효과적인 최적화다.
- 프리페치는 upsert이므로 기존 행의 즐겨찾기·로컬 상태를 지우지 않는다.

테마·설정은 DataStore.

> **엔티티 정정**: `PlayerEntity`·`PlayEntity`(선수·문자중계)는 §2.3 실측으로 KBO에 데이터가 없으므로
> **P1 보조 소스(§1.2) 도입 시에만** 만든다. 점수는 스칼라가 아니라 `InningRunEntity`로 정규화한다
> (연장 동적 이닝 때문, §3.4).

## 7. 실시간 갱신 엔진

이 앱에서 버그와 배터리 문제가 가장 많이 나오는 지점이라 별도 컴포넌트로 설계한다.

### 7.1 라이브 폴링은 요청 1개로 끝난다

`GET /sport/baseball/events/live` 한 번이면 **진행 중인 KBO 전 경기**를 받는다.
`uniqueTournament.id == 11204`로 필터링하면 목록 화면 전체가 단일 요청으로 갱신된다. 경기별 개별 폴링이 필요 없다.

| 화면 / 상태 | 간격 | 요청 |
|---|---:|---|
| 경기 목록, 라이브 있음 | 20초 | `/sport/baseball/events/live` × 1 |
| 경기 목록, 라이브 없음 | 폴링 없음 | 진입 시 1회 + 당겨서 새로고침 |
| 경기 상세, `LIVE` | 15초 | `/event/{id}` × 1 (라인스코어 필요) |
| 경기 상세, `SCHEDULED` | 폴링 없음 | 진입 시 1회 |
| 경기 상세, `FINAL` | 중단 | 전환 직후 1회 확정 조회 |
| 순위 | TTL 10분 | 진입 시 조건부 |
| 시즌 일정 프리페치 | 하루 1회 | `/events/next/*` (순연 반영) |

전부 **화면이 `STARTED` 라이프사이클일 때만** 동작한다. WorkManager는 최소 주기 제한이 있어 실시간
폴링에 쓰지 않고, 캐시 동기화와 일정 프리페치에만 쓴다.

> ⚠️ 경기 상세 `LIVE` 폴링(`/event/{id}` 15초)은 라이브 응답에 `innings`가 포함되는지에 달렸다.
> `events/live`에 이닝별 득점이 있으면 상세 폴링을 없애고 목록 스트림을 재사용할 수 있다 → `DS-002`에서 확인.

### 7.2 구현

```kotlin
class LivePoller<T>(
    private val scope: CoroutineScope,
    private val intervalFor: (T?) -> Duration?,   // null 반환 → 폴링 중단
    private val fetch: suspend () -> T,
)
```

- **lifecycle 연동**: `repeatOnLifecycle(STARTED)` — 화면 이탈 즉시 취소
- **single-flight**: 자동 폴링과 당겨서 새로고침이 겹치면 `Mutex`로 병합
- **적응형 간격**: `changeTimestamp`가 그대로면 간격 1.5배(최대 40초), 변화 감지 시 기본값 복귀
- **jitter**: ±10% 난수
- **backoff**: 실패 시 2배 증가(최대 2분), 성공 시 즉시 복구
- **네트워크 콜백**: 끊기면 즉시 중단, 복구 시 즉시 1회 조회

### 7.3 종료 처리

`inprogress → finished` 전환을 감지하면 폴링 중단 **전에** `/event/{id}`를 1회 더 호출한다. 마지막
이닝 득점이 반영되기 전에 상태만 먼저 바뀔 수 있다. `feedLocked` 필드가 최종 확정 신호일 가능성이
있어 `DS-002`에서 관찰한다.

---

# IV. 실행 (언제·어떤 순서로)

## 8. 단계별 구현 계획

각 단계는 "구현 → 자동 테스트 → 실기기 확인"으로 끝낸다. 1인 기준 소요를 병기한다.

### Step 1 — 실기기 접근성 + 라이브 스키마 스파이크 (0.5일, **최우선**)

§2.4의 미검증 항목을 닫는다. **여기서 막히면 이후 전부 무의미하므로 코드 작성 전에 한다.**

- [ ] `DS-001` **실기기/에뮬레이터에서 OkHttp로 `/unique-tournament/11204/seasons` 호출 성공 확인.** 모바일 네트워크와 Wi-Fi 양쪽. curl의 403은 정상(§13 A-3)이므로 판정은 OkHttp 결과로만 한다. OkHttp에서도 403이면 즉시 중단하고 §1.2 보조 소스로 재설계
- [ ] `DS-002` **게임 데이(08-04 18:30 KST 이후) 라이브 관측** — `/sport/baseball/events/live`를 30초 간격으로 3시간 기록. 확정할 것: 라이브 `status.code`/`description` 값, 진행 중 `innings` 맵 형태(§7.1 전제), `time` 객체 필드, 갱신 지연, `winnerCode` 무승부 값, `feedLocked` 전환
- [ ] `DS-003` 응답 헤더 조사 — `ETag` / `Cache-Control` / `Last-Modified` 지원 여부
- [ ] `DS-004` 프리페치 페이지네이션 확인 — `/events/next/{page}` page 0→N 끝 조건, 총 경기 수가 720에 수렴하는지
- [ ] `DS-005` fixture 저장 → `app/src/test/resources/fixtures/` (예정/라이브/종료/연장/취소 각 1건 이상)

**산출물**: `docs/data/SOFASCORE_KBO_FIELDS.md` 필드 사전 + fixture 세트.
**완료 조건**: §3.4의 함정 7개 + `DS-002` 신규 발견 항목이 전부 fixture로 고정됨.

### Step 2 — 프로젝트 부트스트랩 (0.5일)

- [ ] `DS-010` Compose 프로젝트, version catalog(§5.4), `compileSdk 36` / `minSdk 26`, AGP built-in Kotlin(§5.3)
- [ ] `DS-011` Hilt(KSP2), Retrofit 3/OkHttp/kotlinx.serialization, Room(KSP2), Coil 3, **Navigation 3**
- [ ] `DS-012` Material 3 테마 + **10개 구단 자체 컬러 토큰**(§3.4-5) + 한국어 팀명 리소스(§2.2) — 팀명은 `core/common`, 컬러는 `core/designsystem`으로 분리(§5.1)
- [ ] `DS-013` `core/navigation`에 `NavKey` 7개 정의(`@Serializable`)
- [ ] `DS-014` CI: `assembleDebug` + unit test + lint

### Step 3 — 네트워크·매핑 계층 (1.5일)

- [ ] `DS-020` DTO 정의 — 필요 필드만, `innings`는 `Map<String, InningRunDto>`
- [ ] `DS-021` `SofaScoreApi` + 헤더/최소간격 인터셉터, `KboDataSource` 인터페이스
- [ ] `DS-022` 매퍼 — 상태(§4.1), 라인스코어(§4.2), 무승부 파생(§3.4-1)
- [ ] `DS-023` **매퍼 단위 테스트 — §3.4 함정 7개를 각각 독립 테스트 케이스로.** 특히 연장전 경기에서 10회 득점이 라인스코어에 나타나는지
- [ ] `DS-024` MockWebServer — 타임아웃 / 500 / 깨진 JSON / 빈 배열 / 미지의 `status.type`

**완료 조건**: fixture만으로 매퍼 branch coverage 90%+. **함정 7개 테스트 없이 다음 단계로 넘어가지 않는다.**

### Step 4 — Room + Repository + 시즌 프리페치 (2일)

- [ ] `DS-030` Entity/DAO/Database, schema export
- [ ] `DS-031` **시즌 프리페치 워커**(§3.2) — `next`/`last` 페이지 순회, 빈 배열까지, 최대 60페이지
- [ ] `DS-032` `GamesRepository` — `observeByDate(LocalDate)`는 Room, `refresh*`는 네트워크→트랜잭션 upsert
- [ ] `DS-033` `changeTimestamp` 기반 쓰기 스킵, single-flight, `DataFreshness`
- [ ] `DS-034` 통합 테스트: 캐시 히트, 오프라인, 프리페치 중단·재개, 롤백

**완료 조건**: 비행기 모드에서 시즌 전체 일정을 날짜 이동으로 탐색할 수 있다.

### Step 5 — 경기 목록 (1.5일)

- [ ] `DS-040` `GamesViewModel` + `GamesUiState`(날짜, 섹션, freshness, error)
- [ ] `DS-041` 날짜 네비게이션 + `SavedStateHandle` 보존(읽기만 하지 말고 쓸 것), "오늘" 버튼
- [ ] `DS-042` 경기 카드 4종 상태, **원정팀 먼저 표시**(§3.4-4)
- [ ] `DS-043` `LivePoller` + `/events/live` 연동(§7.1)
- [ ] `DS-044` loading / empty / error / stale UI

**완료 조건**: 경기일에 30분 켜두고 점수가 자동 갱신되며, 홈 → 복귀 시 폴링이 정확히 멈췄다 재개된다.

### Step 6 — 경기 상세 (1.5일)

- [ ] `DS-050` 스코어 헤더 + 상태 라벨(원문 표시)
- [ ] `DS-051` **라인스코어 테이블** — 동적 이닝, 연장 가로 스크롤, 미진행 이닝 구분
- [ ] `DS-052` 구장·감독·시즌·라운드 정보 섹션
- [ ] `DS-053` 상세 폴링 + `FINAL` 확정 조회(§7.3)
- [ ] `DS-054` 볼카운트·주자·라인업 영역을 **만들지 않음**을 코드 리뷰에서 확인(§1.2)

**완료 조건**: 9이닝 / 연장 / 취소 / 미진행 fixture 골든 시나리오 통과.

### Step 7 — 순위·팀·즐겨찾기 (1.5일)

- [ ] `DS-060` 순위 화면 — 승-패-**무**(파생), 승률, 게임차, 득실차, `promotion.text` 진출권 배지
- [ ] `DS-061` 팀 상세 — 구장·수용인원·감독, 최근/예정 경기(`/team/{id}/events/*`)
- [ ] `DS-062` 팀 즐겨찾기 → 목록 상단 고정

### Step 8 — 마감 (1.5일)

- [ ] `DS-070` 설정: 테마, 폴링 간격, **데이터 출처 표기(SofaScore)**
- [ ] `DS-071` Nav3 연결 — 탭별 back stack 4개, `entryProvider`, decorator 2개(saveable + viewModelStore)
- [ ] `DS-072` 접근성 — TalkBack 순서, 48dp, 200% 글꼴에서 라인스코어 스크롤
- [ ] `DS-073` 적응형 레이아웃 — `ListDetailSceneStrategy`로 compact/medium/expanded 목록-상세
- [ ] `DS-074` Baseline Profile, 30분 라이브 배터리·메모리 측정
- [ ] `DS-075` R8 릴리스 빌드 검증

**총 예상: 10~11일** (1인). 단 `DS-002`와 Step 5·6 검증이 실제 경기일에 묶이므로 캘린더 기준 2~3주.

### 착수 순서 — 지금 시작할 3가지

1. **`DS-001`** — 실기기에서 SofaScore API 호출 성공 확인. 이 계획 전체의 전제다. **가장 먼저, 코드 작성 전에.**
2. **`DS-002`** — 게임 데이 18:30 KST 경기에서 라이브 응답 3시간 기록. **다음 경기일까지 기다려야 하므로 지금 스크립트를 준비**한다(월요일은 휴식일).
3. **`DS-010`** — Compose 프로젝트 생성. `DS-002`를 기다리는 동안 병행.

---

# V. 검증·운영

## 9. 테스트 전략

| 층 | 대상 | 도구 |
|---|---|---|
| 단위 | 매퍼(§3.4 함정 7종), 상태 매핑, 이닝 맵 파싱, 무승부 파생, `LivePoller` 간격 | JUnit, coroutines-test, Turbine |
| 통합 | 프리페치 페이지 순회, Repository 캐시/오프라인/트랜잭션, Room 마이그레이션 | MockWebServer, Room testing |
| UI | 화면별 loading/content/empty/error, 라인스코어 연장 렌더링, 원정-홈 표시 순서 | Compose UI Test |
| 시각 | compact/medium/expanded × light/dark × 글꼴 1.0/2.0 | screenshot test |
| 경계 | 위 4개 규칙을 import 기준으로 검사 | 승격 후에는 모듈 의존 그래프가 대신 강제한다 |
| 수동 | 경기일 라이브 검증 | 실기기 |

**경기일 수동 체크리스트** (자동화 불가, 최소 1회)

- 이닝 교체 시 라인스코어가 깨지지 않고 열이 늘어나는가
- 득점 순간 목록과 상세가 20초 이내에 일치하는가
- 연장 진입 시 10회 열이 추가되고 득점이 반영되는가
- 경기 종료 시 폴링이 멈추고 최종 점수가 확정되는가
- 경기 A 상세 → back → 경기 B 상세에서 A의 점수가 남지 않는가 (Nav3 ViewModel 스코핑)
- 탭을 옮겼다 돌아왔을 때 그 탭의 back stack과 스크롤 위치가 남아 있는가
- 백그라운드 10분 후 복귀 시 즉시 갱신되는가
- 30분 라이브 시청 배터리 소모 5% 이내인가

## 10. 리스크

| 리스크 | 확률 | 영향 | 대응 |
|---|---|---|---|
| **실기기(OkHttp)에서 403** | 낮 | 치명 | `DS-001`을 최우선 실행. curl 403은 핑거프린트 차단이라 무시(§13 A-3). OkHttp 실패 시 §1.2 보조 소스로 즉시 재설계 |
| **엣지 핑거프린트 정책 변경으로 OkHttp도 차단** | 낮 | 치명 | 우회하지 않는다. 403은 retry 없이 circuit open + 기능 flag off(§13 B). 보조 소스 준비 |
| **라이브 스키마가 예상과 다름** | 중 | 큼 | `status.type` 기준 분기(§4.1), `description` 원문 표시로 추정 회피. `DS-002`로 사전 확인 |
| KBO 라이브 커버리지 지연 | 중 | 중 | `changeTimestamp` 기준 신선도 표시, "마지막 갱신" 명시 |
| 스키마 변경 | 중 | 중 | `ignoreUnknownKeys`, 전 필드 nullable, 필드 단위 폐기 |
| 과도한 폴링으로 차단 | 낮 | 큼 | 라이브 요청 1개로 통합(§7.1), 최소간격 인터셉터, jitter, 화면 꺼짐 시 중단 |
| 포스트시즌 스키마 차이 | 중 | 중 | MVP는 정규시즌. 10월 이전에 포스트시즌 표본 확보 |
| 더블헤더 | 낮 | 낮 | 같은 `leagueDate`에 같은 팀 2경기 → `startTimestamp`로 정렬·구분 |
| 한국어 선수명 부재 | 확정 | 중 | MVP에 선수 화면 없음(§1.2). P1에서 보조 소스 필요 |

## 11. Definition of Done

한 기능은 아래를 모두 만족할 때만 완료다.

- 요구사항과 수용 기준(§1.6)을 충족한다.
- §5.1의 경계 규칙 4개를 침범하지 않는다. 리뷰에서 실제로 보는 것:
  - ViewModel 생성자에 `SofaScoreApi`·DAO·`*Entity`가 없다.
  - `Dto`·`Entity` 타입 이름이 `data/` 밖 파일에 등장하지 않는다.
  - `core/designsystem`에 `domain.model` import가 없고, `data/`에 `androidx.compose` import가 없다.
  - `feature/x`가 `feature/y`를 import하지 않는다.
- 정상·결측·오류·오프라인 테스트가 있다. §3.4 함정에 걸리는 로직은 독립 테스트로 고정한다.
- compact와 expanded, light/dark, 200% font에서 검증했다.
- TalkBack label, focus order, 48dp touch target을 확인했다.
- 로그/분석에 원문 응답·개인정보가 없다.
- lifecycle 종료 시 polling/coroutine이 취소되고 성능 회귀가 없다.
- 관련 문서(이 계획, 데이터 필드 사전, 엔드포인트 문서)를 갱신했다.

---

# VI. 부록

## 12. 부록 A — APK 정적 분석 추가 발견 (2026-08-23)

SofaScore Android APK를 디컴파일해 얻은, **§2가 작성된 2026-08-02 이후**의 추가 사실이다.
전체 엔드포인트 목록·난독화 매핑·재추출 절차는 공개 저장소에서 제외한 별도 로컬 분석 자료에 있다.

**이 항목들은 경로만 확인됐고 응답은 미검증이다. 설계 확정 근거로 쓰지 않는다.**

### A-1. 날짜 조회 경로가 존재한다 — §3.2 재검토 (`DS-120`)

§3.2는 `/sport/baseball/scheduled-events/{date}`가 404인 것을 근거로 "날짜 조회 불가 → 시즌 전체
프리페치"를 택했다. 그런데 APK에는 **테스트했던 경로 형태 자체가 없고**, 다음이 있다.

```
unique-tournament/{uid}/scheduled-events/{date}     category/{cid}/scheduled-events/{date}
sport/{sport}/{date}/events/{page}                  calendar/season/{sid}/{tz}/days-with-events
```

`uid=11204` / `cid=1385` 버전이 동작하면 프리페치가 불필요할 수 있다. **판단 보류** — 프리페치는
날짜 조회가 되더라도 오프라인·즉시응답 이점이 있어 유지하되, 증분 갱신에 날짜 조회를 쓴다.
`days-with-events`는 날짜 네비게이터의 "경기 있는 날" 표시에 바로 쓸 수 있다.

### A-2. 야구 전용 리소스의 KBO 지원 여부 (`DS-121`)

APK에 야구 전용으로 존재하나 KBO 응답 미확인. `hasEventPlayerStatistics: false`로 보아 404 가능성이
높지만 확정 전엔 §1.2(범위 제외)를 되살리지 않는다.

| 대상 | 프리체크 | 확인 |
|---|---|---|
| `event/{id}/innings` | `HEAD` 있음 | HEAD 1회 (단 `event/{id}`에 이미 `innings` 있음 → 중복 가능) |
| `event/{id}/at-bats` · `atbat/{atBatId}/pitches` · `top-performers` · `umpires` | 없음 | GET, 종료 경기 1건에 최대 4회 |

**하나라도 200이면 §1.2를 재검토한다.** `at-bats`가 살아 있으면 볼카운트·주자가 되살아난다.

### A-3. 접근 차단의 성격 (`DS-125` — 2026-09-03 규명 완료)

| 시점 | 환경 | 결과 |
|---|---|---|
| 2026-08-02 | §2.1 검증 네트워크 | ✅ 200, 인증 없음 |
| 2026-08-23 | APK 분석 환경 (curl) | ❌ 403 (웹페이지도 403) |
| 2026-09-03 | 같은 IP, 클라이언트만 교체 | 아래 표 |

| 클라이언트 (동일 IP·동일 URL) | 결과 |
|---|---|
| curl 8.7, Python `urllib`, Node `fetch`, JDK 21 `java.net.http.HttpClient` — Chrome 헤더 세트를 전부 복제해도 | ❌ 403 |
| Chrome headless, 빈 프로파일(쿠키 없음) | ✅ 200 |
| **OkHttp 4.12 (JVM)** — UA 없음 / 브라우저 UA / SofaScore 앱 UA 전부 | ✅ 200 |

**확정: 엣지(Fastly, `server: Varnish`, `retry-after: 0`)의 TLS/HTTP2 클라이언트 핑거프린트 기반 차단.**
IP·헤더·쿠키·UA는 무관하다. 허용 목록에 브라우저와 OkHttp(SofaScore 공식 앱의 스택)가 들어 있는
것으로 보이며, 이 프로젝트의 앱도 OkHttp라 영향이 없다. 2026-08-23의 "IP 기반" 추정은 폐기한다.

APK 재분석으로 확인한 공식 앱의 요청 구성: OkHttp + Retrofit만 사용. Cronet은 광고 SDK 전용.
GET에는 인증·서명·인증서 피닝 없음(앱이 붙이는 UA 서명도 서버가 검증하지 않음 — 위 표).

운영 규칙: 핑거프린트 차단은 **우회하지 않는다**(curl 위장 등 금지). 터미널 확인이 필요하면
`labs/tools/sofa-fetch.sh`(OkHttp 그대로)를 쓴다. 정책이 바뀌어 OkHttp도 403이 되면 §10 리스크
행대로 circuit open + 보조 소스.

## 13. 부록 B — 공개 배포로 확장할 때 (현재 범위 밖)

개인용 트랙에는 해당 없다. 앱을 스토어에 공개하려면 **앱이 SofaScore를 직접 호출하는 구조를 버리고**
아래가 필요하다. 통합 전 BFF 계획의 요지만 남긴다.

1. **데이터 사용 권리 (선행 게이트)**: 서면 사용 허가 없이 공개 배포하지 않는다. `403`을 아는 것과
   호출할 권리는 별개다(§12 A-3). 캐시 기간·재배포·출처 표기·계약 종료 시 삭제를 계약서에서 확인.
2. **BFF 도입**: 앱은 공급자 중립 계약(OpenAPI)만 보고, `api.sofascore.com`·`11204` 같은 문자열은
   서버 코드에만 둔다. base URL은 서버 주도로 바뀌므로(`InfoWorker`) 호스트를 상수로 박지 않는다.
3. **집계·회복탄력성**: 라이브는 서버가 한 번 조회해 fan-out, request coalescing·circuit breaker·
   backoff. `403`은 retry storm 없이 circuit open + 경보 + 기능 flag off.
4. **관측성·보안·개인정보**: data age SLO 경보, APK secret scan, cleartext 차단, 계정 없는 MVP의
   수집 이벤트·보존기간 문서화.
5. **단계 배포**: 내부 → 폐쇄 → 5% → 25/50/100%, 경기일 간격 확대, 임계치 초과 시 flag off/롤백.

전체 세부 계획이 필요하면 별도 문서로 복원한다. 지금은 개인용 트랙이 유일한 실행 대상이다.

---

## 참고

- [SofaScore KBO 2026 (uniqueTournament 11204)](https://www.sofascore.com/baseball/tournament/south-korea/kbo/11204)
- [SofaScore — Sports data API availability (FAQ)](https://sofascore.helpscoutdocs.com/article/129-sports-data-api-availability?lng=en) — 공식 문서화된 공개 API가 없으므로 스키마 변경 통지를 기대할 수 없다는 점의 근거
- [apdmatos/sofascore-api — 커뮤니티 엔드포인트 문서](https://github.com/apdmatos/sofascore-api/blob/main/sofascore-api.md)
- [Android 앱 아키텍처 권장사항](https://developer.android.com/topic/architecture/recommendations)
- [Android 오프라인 우선 가이드](https://developer.android.com/topic/architecture/data-layer/offline-first)
- [Compose 접근성 semantics](https://developer.android.com/develop/ui/compose/accessibility/semantics)
