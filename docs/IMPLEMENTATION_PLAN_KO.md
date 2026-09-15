# DiamondScore 구현 계획

> 기준일: 2026-08-02 · 통합·재개편: 2026-08-23 · **데이터 소스 교체(SofaScore → wisetoto): 2026-09-15**
> 전제: **개인/포트폴리오 용도**, **백엔드 서버 없음(앱에서 직접 호출)**
> 데이터 소스: **wisetoto API (`bsrest.wisetoto.com`, 프로야구 LIVE 앱 백엔드)**, KBO `league_info_seq = 39`
> 스택: Kotlin 2.4 · AGP 9.4 · Compose · Navigation 3 · Retrofit 3 · Coil 3 · KSP2 (전체 표 §5.4, 2026-09-02 실측)
> 엔드포인트 분석 원자료(APK 추출물·전체 Retrofit 인터페이스·실측 로그)는 공개 저장소에서 제외한 별도 로컬 자료다.

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

우선순위는 **데이터 커버리지(§2.3)가 결정한다.** wisetoto가 주지 않는 것은 억지로 만들지 않고, 주더라도 MVP는 득점 중심으로 끝낸다.

| 우선순위 | 항목 |
|---|---|
| **P0 (wisetoto로 완결)** | 날짜별 경기 목록(예정/진행/종료/취소), 라이브 카드(총점+이닝 라벨+마지막 갱신), 경기 상세(이닝별 라인스코어·R/H/E·선발/승패 투수), 2026 정규시즌 순위, 팀 상세(구장·감독·최근/예정 경기), 팀 즐겨찾기, 오프라인 캐시, 다크·접근성·태블릿/폴더블 |
| **P1 (데이터는 있음, 화면만 미구현)** | 현재 상황(볼카운트·주자·현재 투수/타자), 문자중계(투구 단위), 라인업·박스스코어, 선수 상세·개인 순위, 날씨, 경기 알림, 위젯, 공유 카드, 영어 UI |
| **제외** | 베팅·예측·결제, 계정·채팅, 영상·오디오 중계, 자동 기사 생성, 허가 없는 데이터 수집/이미지 핫링크 |

**P1을 MVP에서 뺀 근거**: 데이터는 전부 같은 API에 있고 진행 중 `detail`(볼카운트·주자·현재 투수/타자)이 실제로
채워지는 것도 확인했다(§2.4). 뺀 이유는 **일정과 검증 범위**다 — 라이브 화면은 경기일에만 검증할 수 있어 득점 화면을
먼저 닫는다. 자리는 미리 만들지 않는다 — 추정값으로 채우는 것은 표시 원칙(§1.3)에 위배된다.

**보조 소스는 없다.** 한 API가 목록·상세·순위·팀·선수를 다 주므로 두 소스의 경기 ID를 매칭할 일이 없다.
SofaScore는 2026-09-14 실측에서 연장 라인스코어 오류가 확인돼(§12 부록 A) 교차 검증용으로도 쓰지 않는다.

**개인용 트랙 유의**: 개인/포트폴리오 용도이므로 스토어 공개 배포 게이트(라이선스·production 차단)는
적용하지 않는다. **공개 배포로 전환하면 §13 부록 B가 선행 조건이 된다.** wisetoto 이용약관은 "서비스에서 얻은
정보의 사전 승낙 없는 복제·유통·상업적 이용"을 금지하므로 개인 사용에 한정하고, 폴링은 공식 앱 수준(목록 4초)을
넘지 않으며, 로고·선수 이미지는 재배포하지 않는다.

### 1.3 화면 명세

**경기 탭**: 상단에 오늘/이전·다음 날짜/날짜 선택기(날짜 조회 설계는 §3.2). 본문은 진행 중 → 예정 →
종료 순 또는 시작 시각 순. 카드는 팀·로고·점수·상태·경기장·시작 시각, 진행 중은 라이브 강조와 마지막
갱신 시각. 빈 날짜는 빈 상태 + 가장 가까운 경기일로 이동하는 액션.

**경기 상세**:
- **스코어보드**: 팀, 총점, 경기 상태, 시작 시각·경기장. **원정팀 먼저 표시**(KBO 관행).
- **라인스코어**: 1~9회 및 연장 이닝을 동적으로(§4.2), `R/H/E`는 공급될 때만 노출.
- **현재 상황(볼·스트라이크·아웃, 주자)**: 목록 행과 상세의 `detail`에 진행 중 채워진다(§2.4 실측). **P1** —
  득점 화면을 먼저 완성하고 다음 경기일에 라이브 검증과 함께 붙인다. 그 전에는 자리도 만들지 않는다.
- **탭**: 요약 / 문자중계(P1) / 라인업·기록(P1). 숨겨진 탭이 딥링크·back stack을 깨지 않게 한다.

**순위**: 시즌(연도) 선택, 순위·경기수·**승-패-무**(`draw_count` 직접)·승률·게임차·연속. 득실차·진출권 배지는 공급되지 않으므로 컬럼을 두지 않고, 5위 뒤 진출선은 UI 고정 규칙으로 그린다.
공급되지 않는 컬럼은 `-`가 아니라 컬럼 자체를 숨긴다. 동률은 앱에서 재계산하지 않고 공급자 순서를 따른다.

**팀**: 10개 구단 목록 + 즐겨찾기. 팀 상세는 기본 정보·구장·감독·최근 5경기·다음 5경기. 로고 허가가
없으면 문자 모노그램 + 팀 컬러 대체 자산.

**선수(P1)**: 이름·등번호·포지션·투타·소속·월별 기록(`/extra/Player_Info`). 타자/투수 스키마 분리. 데이터는
있으나 MVP 범위 밖.

**즐겨찾기·설정**: 즐겨찾는 팀 목록, 테마(시스템/라이트/다크), 데이터 출처(wisetoto)·개인정보·
오픈소스 라이선스 표기. 알림은 P1.

**표시 원칙 (모든 화면 공통)**:
- **UI에서 추정값을 생성하지 않는다.** 서버가 준 값만 표시한다. 이닝 라벨은 `inning` 코드 파싱으로만 만들고, 파싱에 실패하면 "진행 중"으로 둔다(§4.1).
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
- **팀 컬러는 강조에만** 쓰고(§2.2의 앱 리소스 컬러) 텍스트 대비 WCAG AA 유지.
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
| API 성공률 | 99.0% 이상 (앱 → wisetoto 직접, 봉투 `code 00` 기준) |
| 접근성 자동 검사 | 차단 이슈 0건 |
| 핵심 흐름 UI 테스트 | 100% 통과 |

신선도 SLO는 라이브 스키마 관측(`DS-002`, §8) 이후 실제 갱신 지연에 맞춰 조정한다.

**MVP 수용 기준**:
- 오늘 및 선택 날짜의 모든 KBO 경기를 볼 수 있다.
- 라이브 점수·이닝이 화면이 보이는 동안 자동 갱신된다.
- 경기 → 팀, 순위 → 팀 이동과 back 문맥 복원이 된다.
- 네트워크 단절 시 마지막 성공 데이터와 갱신 시각이 보인다.
- 데이터 결측·일부 필드 부재에도 크래시하지 않는다.
- P1 항목(볼카운트·라인업·선수 기록 등)의 UI 자리를 만들지 않는다.

---

# II. 데이터 (무엇을 알고 있는가)

## 2. 데이터 현실 — wisetoto KBO 실측

2026-09-14~15에 wisetoto API(`bsrest.wisetoto.com`, Google Play "프로야구 LIVE" 앱의 백엔드)를 직접 호출해
확인한 사실이다. **추정이 아니라 실제 응답 기준**이며, 확인하지 못한 항목은 명시적으로 미검증으로 표기했다.
엔드포인트 목록은 실기기에서 추출한 앱(v4.1.3)의 Retrofit 인터페이스에서 확보했고, 전부 실측 응답으로 검증했다.

### 2.1 접근 가능성

wisetoto API는 **정상 접근되며 실제 KBO 데이터를 반환한다.**

| 확인 항목 | 결과 |
|---|---|
| `GET /live/Schedule_Day/20260913` | ✅ `code 00`, 4경기(종료) |
| `GET /live/Schedule_Month/202609` | ✅ 108경기 |
| `GET /live/schedule/490683` | ✅ 라인스코어 15칸·R/H/E/B·종료 요약 |
| `GET /rank/League_Rank?year=2026` | ✅ 10개 구단 순위 |
| `GET /extra/Team_Info?team_info_seq=316` | ✅ 구단 정보·감독·선수 명단 |

| 접근 조건 | 실측 |
|---|---|
| 필수 쿼리 | `os`·`version`·`lang` **세 키 모두 필수** — 하나라도 없거나 빈 값이면 모든 경로가 `code:"01" 잘못된 접근`(HTTP는 200). 값은 검사하지 않는다(`os=i`, `version=x`, `lang=en` 전부 정상) |
| 클라이언트 | curl·OkHttp·브라우저 전부 200. **`User-Agent`가 `Python-urllib/*`이면 401** |
| 경로 | **대소문자 구분** (`Schedule_Day` ○, `schedule_day` ×404). 날짜 인자는 `yyyyMMdd`/`yyyyMM`만 |
| 인증 | 없음. 회원 기능(`user_key`)은 이 앱이 쓰지 않는다 |
| 지연·제한 | 35~140 ms. 40 병렬 × 약 8만 요청에도 차단·429 없음 |
| 응답 헤더 | `Content-Type: text/html`(본문은 JSON), gzip, ETag/Cache-Control 없음 |
| 서버 캐시 | 응답의 `cache_second`: 목록·상세 2초, 순위·팀·날씨 3600초 |

> 앱 부트스트랩 `GET /extra/notice`가 최신 앱 버전과 강제 업데이트 신호(`update.next_action`)를 내려준다.
> 데이터 경로는 구버전 `version`에도 응답하지만, 앱 시작 시 이 값을 읽어 서비스 측 차단 신호로 삼는다(`DS-003`).

### 2.2 확정된 식별자

| 항목 | 값 |
|---|---|
| Base URL | `https://bsrest.wisetoto.com` |
| KBO 정규시즌 `league_info_seq` | `39` (시범경기 `186`) |
| 시즌 | `year=2026` — 시즌 ID가 따로 없다. 순위는 연도로 조회 |
| 경기 ID | `schedule_info_seq` — **전 종목 공용 전역 증가 번호** |
| 팀 로고 | `https://storage.wisetoto.com/data/sports_db/team_{teamSeq}.png` (`_s.png` 소형) |

**`schedule_info_seq`는 날짜·팀으로 계산할 수 없다.** 와이즈토토가 리그 일정을 DB에 입력한 순서로 붙기 때문에
2026 KBO는 462828~463500(개막~9/6), 468584~468638(시범경기), 490672~490821(9/8 이후 재편성) 세 블록에
흩어져 있고, 우천 취소 경기의 대체 경기는 새 번호를 받는다. **경기 ID는 항상 목록 경로에서 받아온다.**

**10개 구단 팀 ID** (`team_info_seq`, `/extra/Team_Select`에서 확보)

| teamSeq | 약칭(API `short_name`) | 정식 명칭 | 홈 |
|---:|---|---|---|
| 2674 | KT | KT 위즈 | 수원 |
| 318 | 삼성 | 삼성 라이온즈 | 대구 |
| 322 | LG | LG 트윈스 | 잠실 |
| 316 | 두산 | 두산 베어스 | 잠실 |
| 320 | KIA | KIA 타이거즈 | 광주 |
| 319 | 한화 | 한화 이글스 | 대전 |
| 2107 | NC | NC 다이노스 | 창원 |
| 317 | 롯데 | 롯데 자이언츠 | 사직 |
| 315 | SSG | SSG 랜더스 | 인천 |
| 321 | 키움 | 키움 히어로즈 | 고척 |

한국어 약칭은 API가 준다. 정식 명칭·홈 도시·구단 컬러는 앱 리소스로 둔다(§3.4-6 구장명 표기가 비정규라서).
팀 ID는 시즌이 바뀌어도 안정적이다(2015년 경기도 같은 ID).

### 2.3 커버리지

SofaScore 시절의 "득점 전용(runs-only)" 제약이 사라졌다. **제공 범위가 제품 범위(§1.2)를 결정**하는 원칙은
그대로이며, MVP는 여전히 득점 중심으로 완결하고 나머지는 P1로 미룬다.

| 제공됨 ✅ (MVP 사용) | 제공됨 ✅ (P1 — 데이터는 있으나 MVP 화면 없음) | 제공되지 않음 ❌ |
|---|---|---|
| 날짜별·월별 경기 일정 (KBO 외 경기 포함 → 앱에서 필터, §3.4-8) | 볼-스트라이크-아웃, 주자 (`detail`) | 구장 수용 인원 |
| 총점, 이닝별 득점(15칸, 연장 포함) | 현재 투수/타자, 다음 타자 | 변경 감지 타임스탬프 |
| R/H/E/B | 라인업·박스스코어(`/extra/lineup`) | 시즌 목록(연도로 대체) |
| 경기 상태·이닝 코드 | 문자중계 투구 단위(`/extra/Live_comment`, 약 90일 보존) | 진출권 배지 |
| 선발·승리·패전·세이브 투수 | 선수 프로필·기록(`/extra/Player_Info`) | |
| 순위(승·패·무·승률·게임차·연속) | 개인 순위 타자 8부문·투수 6부문(`/rank/Sector_Rank`) | |
| 구단 정보·감독·한국어 팀명·로고 | 날씨(`/extra/Weather_Info`), 중계 링크 | |

### 2.4 라이브 스키마 — 2026-09-15 18:31 KST 실측 (경기 시작 직후)

780경기의 `state` 분포는 `a`(예정) 82 · `e`(종료) 630 · `c`(취소/노게임) 68이었고, 09-15 18:30 경기 4건을 1분 간격으로
캡처해 **진행 중 값 `i`를 확인**했다. 시작 1분 뒤(18:31) 관측:

| 항목 | 관측 |
|---|---|
| `state` | **`i`** (4경기 동시에 `a` → `i`) |
| `Schedule_Day` 행 | `home_score:"0"`·`away_score:"0"` 문자열, `inning:"bs1_1"`, `attack_team_info_seq` = 공격 팀, `detail`에 `current_batter_name`·`current_pitcher_name`·`first/second/third_base`·`balls`·`strikes`·`outs` |
| 상세 `game_result` | 진행 중엔 **이닝 라벨 문자열** `"1회초"` (종료 후 `w`/`l`/`d`) |
| 상세 `boxscore` | 공격 중인 하프이닝 칸이 `0`, 나머지 `null`. `RHEB` `[0,0,0,0]` |
| 상세 `detail` | 볼카운트·아웃·주자(이름 또는 `"0"`)·현재 투수/타자(사진·등번호·기록)·다음 타자 3명 |
| `end_summary` | `null` (종료 후 채워짐) |
| `livecomment` | 마지막 투구 1건(`"2구 볼 (144km/h, 직구)"`), `cache_second: 2` |
| `other_game_state` | 같은 날 다른 경기 3건이 `state:"i"`·점수로 같이 옴 |

**아직 미관측**: 종료 전환 시 `end_summary`가 채워지는 시점, 갱신 지연(서버 캐시 2초 대비). 경기 종료까지 캡처가 이어진다(`DS-002`).

**대응 원칙**: `a`/`e`/`c`/`i`는 확정 매핑, 그 외 값은 `UNKNOWN`으로 두고 로그를 남긴다(§4.1). 이닝 라벨은 `inning`
코드 `bs{N}_{1|2}` 파싱으로 만든다(진행 중엔 `game_result`에도 같은 라벨이 오지만 종료 후 의미가 바뀌므로 쓰지 않는다).

## 3. 데이터 소스 계약

Base URL: `https://bsrest.wisetoto.com/` · 공통 쿼리 `os=a&version=4.1.3&lang=kr`(인터셉터가 붙인다)

### 3.1 사용 엔드포인트 (전부 실측 200 · `code 00`)

| # | 용도 | 엔드포인트 | 응답 규모 |
|---|---|---|---|
| 1 | **날짜별 경기 목록 + 라이브 갱신** | `GET /live/Schedule_Day/{yyyyMMdd}` | 5 KB, 하루 최대 5경기 (+ 3월엔 WBC 등 비KBO 경기) |
| 2 | 월별 일정(프리페치) | `GET /live/Schedule_Month/{yyyyMM}` (`&team_info_seq=&home_away=h\|a` 선택) | 34 KB, ~110~130행 (비KBO 포함) |
| 3 | 경기 상세(라인스코어·R/H/E·투수 요약·진행 상황) | `GET /live/schedule/{seq}` | 5~8 KB |
| 4 | 순위 | `GET /rank/League_Rank?year={YYYY}` | 3 KB, 10 rows |
| 5 | 팀 정보(정식 명칭·홈구장·감독·선수 명단) | `GET /extra/Team_Info?team_info_seq={id}` | 8 KB |
| 6 | 팀 목록 | `GET /extra/Team_Select` | 1 KB (앱은 로컬 표를 쓰므로 검증용) |
| 7 | 앱 부트스트랩(버전·차단 신호) | `GET /extra/notice` | 1 KB |
| 8 | 팀 로고 | `storage.wisetoto.com/data/sports_db/team_{id}.png` | 이미지 |
| P1 | 라인업·박스스코어 | `GET /extra/lineup/{seq}` | 7 KB |
| P1 | 문자중계 | `GET /extra/Live_comment/{seq}` | 30~60 KB |
| P1 | 선수·개인 순위·날씨 | `GET /extra/Player_Info/{seq}` · `/rank/Sector_Rank?year=` · `/extra/Weather_Info/{yyyyMMdd}` | — |

전부 `GET`이며 인증이 없다. 회원·커뮤니티·이벤트 경로(80여 개)는 이 앱과 무관하다.

### 3.2 날짜 조회 + 월 단위 프리페치

`Schedule_Day/{날짜}`가 있으므로 "8월 2일 경기"를 직접 조회할 수 있다. 그래도 **시즌 전체를 Room에 넣어 두는
설계는 유지**한다 — 오프라인·즉시 응답·즐겨찾기 팀 일정 때문이다. 다만 프리페치 단위가 월이라 훨씬 싸다.

```
초기 동기화:      Schedule_Month/{202603 … 202611}  9회 (약 300 KB)
                  ↓
            Room GameEntity (leagueDate 인덱스)
                  ↓
날짜 네비게이션:  SELECT * FROM games WHERE leagueDate = ?   ← 네트워크 0회
오늘 화면 진입:   Schedule_Day/{오늘} 1회 → upsert            ← 점수·상태 최신화 (라이브면 20초마다)
```

- **목록은 KBO 전용이 아니다.** 3월엔 WBC(한국·체코·호주…, 도쿄), 3/12~3/24 시범경기(`league_info_seq 186`), 7월엔 올스타전(드림·나눔)이 같은 목록에 섞여 온다(2026년 3~11월 890행 중 108행). 행에는 리그 필드가 없으므로 **양 팀이 모두 KBO 10구단이고 날짜가 `Schedule_Day`의 `league_rank.start`(2026-03-27) 이후**인 행만 저장한다 → 782행(종료 630·취소 70·예정 82). 포스트시즌은 같은 규칙을 통과한다
- 잔여 경기 재편성은 새 seq로 들어오지만 날짜 조회에 즉시 반영된다. 하루 1회 현재 월과 다음 월만 다시 받으면 된다
- 과거 시즌은 같은 경로로 조회된다(2015년까지 확인). 시즌 전환은 `year`만 바꾼다
- `Schedule_Month` 행에는 `game_timestamp`가 없고 `game_date` 문자열만 있다 → `yyyy-MM-dd HH:mm:ss`를 **`Asia/Seoul`로 파싱**한다

**날짜 경계**: `game_timestamp`는 epoch 초다. `leagueDate`는 반드시 `Asia/Seoul`로 변환해 저장한다. 기기
타임존을 쓰면 해외에서 날짜가 밀린다.

### 3.3 응답 스키마 (실측)

**공통 봉투**

```json
{ "result": "success", "code": "00", "message": "정상 출력", "data": { … } }
```
`code`가 `"00"`이 아니면 실패다(`"01"` 잘못된 접근). `data`에는 `resource`·`cache_set`·`cache_second`·
`execution_time` 같은 상수 노이즈가 늘 섞여 온다.

**Schedule_Day / Schedule_Month 항목**

```json
{
  "seq": "490691",
  "game_date": "2026-09-13 17:00:00",     // 표시용 문자열 (Month에는 이것만 있음)
  "game_timestamp": 1789286400,           // Day에만
  "state": "e",                            // a 예정 · e 종료 · c 취소
  "inning": "bs9_1",                       // 9회초 (홈 승 → 9회말 미실시)
  "stadium_name": "기아챔피언스필드",
  "home_team_info_seq": "320", "home_team_name": "KIA", "home_pitcher": "시라카와",
  "away_team_info_seq": "319", "away_team_name": "한화", "away_pitcher": "화이트",
  "home_score": "9", "away_score": "2",     // 문자열! 취소·예정은 null
  "weather": "w01", "double_header_no": null,
  "detail": { "win_pitcher": {…}, "lose_pitcher": {…} }     // 예정 경기는 선발 비교 기록
}
```
+ `Schedule_Day` 최상위에 `league_rank { season, start, end }`(현재 시즌 메타), `banner`, `Vot_posible`.

**경기 상세 `/live/schedule/{seq}` → `data.detail_info`**

```json
{
  "schedule_info_seq": "490683", "game_timestamp": 1789032600, "game_date": "09/10(목) 18:30",
  "state": "e", "inning": "bs11_2", "game_result": "l",          // game_result는 홈 기준 w/l/d
  "stadium_name": "기아챔피언스필드", "home_area": "광주", "weather": "w01",
  "home_team_info_seq": "320", "home_team_name": "KIA", "home_score": 1,     // 상세는 숫자
  "away_team_info_seq": "2107", "away_team_name": "NC", "away_score": 2,
  "rank": { "home_rank": "4위", "home_rank_detail": "68승56패2무", "away_rank": "6위", "away_rank_detail": "…" },
  "boxscore": {
    "home_score": [0,0,0,0,0,0,0,0,1,0,0,null,null,null,null],   // 항상 15칸, null = 미진행
    "home_RHEB": [1, 6, 0, 3],                                    // R H E B(볼넷)
    "away_score": [0,0,0,0,1,0,0,0,0,0,1,null,null,null,null],
    "away_RHEB": [2, 5, 0, 2]
  },
  "detail": { "first_base": "0", "second_base": "박건우", "third_base": "0",
              "balls": 2, "strikes": 1, "outs": 3,
              "current_pitcher_name": "…", "current_batter_name": "…", "next_up_batter": "…" },   // 진행 상황
  "end_summary": { "pitcher_batter_record": { "win_pitcher": "김주원 (…)", "lose_pitcher": "…", "save_pitcher": null,
                                              "homerun_hit": "…", "referee": "…" },
                   "home_stats": { "h": 6, "hr": 0, "e": 0, … }, "away_stats": {…} },
  "other_game_state": [ { "schedule_info_seq": "490684", "state": "e", "inning": "bs9_2", "home_score": "1", … } ]
}
```
+ `data.livecomment`: 마지막 문자중계 1건(없으면 `null`).

**순위 `/rank/League_Rank?year=2026` → `data.rank[]`**

```json
{ "rank": "1", "simple_name": "KT", "team_inf_seq": "2674",
  "team_logo": "http://storage.wisetoto.com/data/sports_db/team_2674.png",
  "player_count": "124",           // 이름과 달리 경기 수
  "win_count": "75", "lose_count": "46", "draw_count": "3",
  "win_rate": "0.620", "win_distinction": "0.0",   // 게임차
  "straight": "6승" }
```

### 3.4 반드시 처리해야 하는 함정 (실측 중 발견)

이 8개는 그냥 매핑하면 확실히 버그가 된다.

1. **경로가 대소문자를 구분하고 날짜 형식이 하나뿐이다.** `Schedule_Day`/`Schedule_Month`/`League_Rank`/`Team_Info`는
   대문자 그대로, 날짜는 `yyyyMMdd`·`yyyyMM`. 틀리면 404 또는 `code 01`. 공통 쿼리 `os`·`version`·`lang` 중 하나라도 없어도 `01`.
   **HTTP 200이 성공을 뜻하지 않는다** — 봉투의 `code`로 판정한다.

2. **숫자가 문자열로 온다.** 목록의 `home_score:"9"`, 순위의 `win_count:"75"`·`win_rate:"0.620"`·`win_distinction:"0.0"`.
   상세의 `home_score: 1`만 숫자. DTO는 서버 타입 그대로 받고 매퍼에서 `toIntOrNull()`로 바꾼다. 빈 문자열·`null`은 `null`.

3. **`state:"c"`인데 점수가 남아 있다.** 노게임(강우 콜드 전)은 `bs3_2`, `0:2` 같은 부분 점수와 라인스코어를 남긴다.
   `c`면 점수·라인스코어를 **버린다**(총점 `null`, 이닝 빈 배열).

4. **`game_result`는 진행 중과 종료 후 의미가 다르다.** 진행 중엔 `"1회초"` 같은 이닝 라벨, 종료 후엔 홈 기준 `w`/`l`/`d`. 승패는 `game_result`가 아니라 **총점 비교**로, 이닝 라벨은 `inning` 코드로 만든다. 진행 중 `state`는 `i`(§2.4).

5. **라인스코어는 15칸 고정 배열이고 미진행이 `null`이다.** `0`은 0점, `null`은 안 한 이닝. 9회말 미실시(홈 승)도
   `null`. "진행된 이닝 수"는 `null`이 아닌 마지막 칸 또는 `inning` 코드로 구한다. 15칸을 그대로 그리면 안 된다.

6. **구장명 표기가 비정규다.** 잠실만 `서울잠실야구장`/`서울 잠실야구장`, 사직 3종 등 23가지. 카드의 구장 표시는
   `stadium_name`이 아니라 **앱 팀 표의 홈 도시**로 한다. 상세 화면에서만 원문을 그대로 보여준다.

7. **`game_date`는 표시 문자열이고 변경 감지 필드가 없다.** 상세의 `game_date`는 `"09/10(목) 18:30"`(연도 없음).
   시각은 `game_timestamp`(초)만 쓴다. SofaScore의 `changeTimestamp` 같은 델타 필드가 없으므로 **DB 쓰기 스킵은
   기존 행과의 동등 비교**로 한다(§6).

8. **목록에 KBO가 아닌 경기가 섞여 있다.** WBC·시범경기·올스타전이 `Schedule_Day`/`Schedule_Month`에 같이 온다(§3.2). 행에
   리그 필드가 없으니 **양 팀 `team_info_seq`가 KBO 10구단이고 날짜가 `league_rank.start` 이후**인 행만 받는다. 이 필터가
   없으면 3월 목록에 "한국 : 체코"가 뜨고 순위 계산·팀 일정이 시범경기로 오염된다.

추가 주의: `Schedule_Day`의 `league_rank`는 조회 날짜와 무관하게 **현재 시즌** 메타만 준다(그래서 시즌 시작일 소스로 쓴다). `player_count`는 선수
수가 아니라 경기 수다. `team_inf_seq`·`team_ifno_seq`(Team_Select) 오타는 서버 필드명 그대로 `@SerialName`으로 받는다.

---

# III. 설계 (어떻게 만드는가)

## 4. 도메인 모델과 매핑

```kotlin
enum class GameStatus { SCHEDULED, LIVE, FINAL, CANCELED, POSTPONED, SUSPENDED, UNKNOWN }
enum class Winner { HOME, AWAY, DRAW }

data class TeamRef(val id: Long, val nameKo: String, val code: String)   // id = team_info_seq

data class GameSummary(
    val id: Long,                   // schedule_info_seq
    val startsAt: Instant,          // game_timestamp(초) → Instant
    val leagueDate: LocalDate,      // Asia/Seoul 기준, 인덱스 키
    val status: GameStatus,
    val statusLabel: String,        // "경기 전" / "7회말"(inning 코드 파싱) / "경기 종료" / "취소"
    val home: TeamRef, val away: TeamRef,
    val homeRuns: Int?, val awayRuns: Int?,   // 경기 전·취소는 null (0이 아님)
    val winner: Winner?,            // FINAL일 때만 non-null, 동점 종료 = DRAW
    val wentExtra: Boolean,         // inning 코드 번호 > 9
    val venueShort: String? = null, // 홈 도시 — 앱 리소스
    val homeStarter: String? = null, val awayStarter: String? = null,   // 선발 (Schedule_Day)
)

data class InningRuns(val number: Int, val home: Int?, val away: Int?)  // null = 미진행

data class GameDetail(
    val summary: GameSummary,
    val innings: List<InningRuns>,          // 진행된 이닝까지만 (최소 열 수는 UI가 보장)
    val venueName: String?,                 // stadium_name 원문
    val homeHits: Int?, val awayHits: Int?, val homeErrors: Int?, val awayErrors: Int?,   // RHEB[1], [2]
    val winPitcher: String?, val losePitcher: String?, val savePitcher: String?,
)

data class Standing(
    val position: Int, val team: TeamRef,
    val games: Int, val wins: Int, val losses: Int, val draws: Int,   // draw_count 직접 제공
    val winPct: Double, val gamesBehind: Double,
    val streak: String?,                    // straight ("6승")
)
```

`POSTPONED`·`SUSPENDED`는 wisetoto가 구분하지 않아 현재 매핑되지 않는다(우천 취소도 `c`). 표본이 잡힐 때까지 enum만 남긴다.

### 4.1 상태 매핑

```kotlin
fun mapStatus(state: String?): GameStatus = when (state) {
    "a"  -> GameStatus.SCHEDULED
    "i"  -> GameStatus.LIVE            // 2026-09-15 실측 (§2.4)
    "e"  -> GameStatus.FINAL
    "c"  -> GameStatus.CANCELED
    else -> GameStatus.UNKNOWN.also { logUnknownState(state) }
}

private val INNING_CODE = Regex("""bs(\d+)_([12])""")
fun inningLabel(code: String?): String? =
    INNING_CODE.matchEntire(code.orEmpty())?.destructured?.let { (n, half) -> "${n}회${if (half == "1") "초" else "말"}" }
```

`statusLabel`은 진행 중이면 `inningLabel`, 그 외는 상태별 고정 문자열이다. 서버가 설명 문자열을 주지 않으므로
라벨은 앱이 만들되 **이닝 코드 파싱에 실패하면 "진행 중"**으로만 표시하고 이닝을 지어내지 않는다.

### 4.2 라인스코어 매핑 (15칸 → 진행 이닝)

```kotlin
fun parseInnings(home: List<Int?>, away: List<Int?>): List<InningRuns> {
    val played = maxOf(home.indexOfLast { it != null }, away.indexOfLast { it != null }) + 1
    return (1..played).map { n -> InningRuns(n, home.getOrNull(n - 1), away.getOrNull(n - 1)) }
}
```

`boxscore.home_score`/`away_score` 15칸 중 진행된 이닝까지만 남긴다. 9회말 미실시는 `home = null`로 유지된다
(§3.4-5). 최소 9이닝 열은 UI가 확보하고, 그 이상은 데이터에 있는 만큼만 표시한다. `state:"c"`면 빈 배열(§3.4-3).

### 4.3 결측·정정 규칙

- `null`/미제공/미집계를 `0`과 구분한다(§1.3 표시 원칙).
- 점수·기록 정정은 최신 응답이 승리한다. 델타 필드가 없으므로 Repository가 기존 행과 비교해 같으면 쓰지 않는다(§6).
- 공급자가 필드를 제거하거나 타입을 바꿔도 앱이 죽지 않게 관대한 파서(§5.2 `ignoreUnknownKeys`) +
  명시적 매퍼로 격리한다. 문자열 숫자는 `toIntOrNull()`.

## 5. 아키텍처와 기술 스택

```
Compose UI  ──events──▶  ViewModel  ──────────────▶  Repository
    ▲                                                    │
    └──── StateFlow<UiState> ◀── Room(SSOT) ◀────────────┘
                                                          ▼
                                                 WisetotoApi (Retrofit)
                                                 └ 테스트: MockWebServer + fixture
```

**UseCase 계층은 두지 않는다.** 이 앱의 화면-데이터 관계는 1:1이고, 재사용되는 도메인 로직은
`parseInnings`·`inningLabel`처럼 순수 함수라 매퍼에 있다. ViewModel과 Repository 사이에 클래스를 한 겹
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
│   ├─ remote/          WisetotoApi, dto/, mapper/, di/NetworkModule
│   ├─ local/           entity/, dao/, mapper/, di/DatabaseModule, DiamondScoreDatabase
│   ├─ repository/      Games, Standings, Teams, Favorites, SettingsStore
│   └─ sync/            PrefetchWorker
├─ domain/model/        GameSummary, GameDetail, Standing, TeamDetail, TeamRef …
└─ feature/             games/, gamedetail/, standings/, teams/, favorites/, settings/
```

규칙 2개만 지킨다:

1. **`feature`·`core/ui`·`core/designsystem`은 `data`를 참조하지 않는다.** ViewModel이 주입받는 것은
   Repository뿐이다 — `WisetotoApi`·DAO·`Entity`는 이름조차 나오지 않는다.
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

`ignoreUnknownKeys = true`는 선택이 아니다. 모든 응답에 `resource`·`cache_set`·`execution_time` 같은 노이즈가
섞이고, 상세 응답은 `rank`·`detail`·`end_summary`·`other_game_state`·`livecomment` 등 MVP가 안 쓰는 객체가 대부분이다.
`explicitNulls = false`도 필요하다 — 미진행 이닝·미제공 값이 `null`로 온다.

```kotlin
OkHttpClient.Builder()
    .addInterceptor(WisetotoQueryInterceptor())     // os=a&version=4.1.3&lang=kr (없으면 code 01) + UA
    .addInterceptor(MinIntervalInterceptor())       // 호스트당 최소 요청 간격
    .cache(Cache(cacheDir.resolve("http"), 20L * 1024 * 1024))
    .callTimeout(10.seconds)
    .connectTimeout(5.seconds)
    .build()
```

Coil 3는 이 OkHttp 인스턴스를 공유한다(`coil-network-okhttp`). 응답에 `ETag`/`Cache-Control`이 없으므로(§2.1)
조건부 요청은 불가능하다. 대신 목록 응답이 5 KB 안팎이라 20초 폴링 부담이 작고, 서버 캐시(`cache_second: 2`)가
원본 부하를 막는다. 응답 `Content-Type`은 `text/html`이지만 kotlinx 컨버터는 헤더를 보지 않는다.

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
| `GameEntity` | `gameId` (= `schedule_info_seq`) | `leagueDate`, `homeTeamId`, `awayTeamId` | 시즌 전체 ~720행 + 선발투수 |
| `InningRunEntity` | `(gameId, inning)` | `gameId` | home/away nullable, 상세 조회 시에만 채워짐 |
| `StandingEntity` | `(season, teamId)` | — | `season`은 연도(Int), `draws` 직접 저장, `streak` |
| `FavoriteEntity` | `(type, targetId)` | — | |
| `SyncMetaEntity` | `resourceKey` | — | `lastSuccessAt`, `lastError` |

팀 정보(`TeamEntity`)는 두지 않는다 — 10개 구단 표는 `core/common`의 상수이고, 구장·감독은 팀 상세에서 `Team_Info`를 그때 받는다(서버 캐시 1시간). 시즌 테이블도 없다(연도가 곧 시즌).

**쓰기 규칙**

- 경기 상세 갱신은 `GameEntity` + `InningRunEntity`를 **한 트랜잭션**으로 upsert. 총점과 이닝이 불일치하는 중간 상태가 UI에 보이면 안 된다.
- 델타 필드가 없으므로(§3.4-7) **새 행이 기존 행과 `data class` 동등이면 DB 쓰기를 건너뛴다.** 불필요한 `Flow` 재방출과 recomposition을 막는 가장 효과적인 최적화다. 이 비교가 성립하려면 엔티티에 갱신 시각 같은 필드를 넣지 않는다.
- 목록(`Schedule_Day/Month`) 갱신은 `GameEntity`만 만지고 `InningRunEntity`는 건드리지 않는다(목록엔 이닝이 없다). 취소로 바뀐 경기는 이닝 행을 지운다.
- 프리페치는 upsert이므로 기존 행의 즐겨찾기·로컬 상태를 지우지 않는다.

테마·설정은 DataStore.

> **엔티티 정정**: `PlayerEntity`·`PlayEntity`(선수·문자중계)는 데이터가 있어도 **P1 화면을 만들 때** 만든다.
> 문자중계는 약 90일만 서버에 남으므로 보관하려면 그때 앱이 저장해야 한다. 점수는 스칼라가 아니라
> `InningRunEntity`로 정규화한다(연장 동적 이닝, §3.4-5).

## 7. 실시간 갱신 엔진

이 앱에서 버그와 배터리 문제가 가장 많이 나오는 지점이라 별도 컴포넌트로 설계한다.

### 7.1 라이브 폴링은 요청 1개로 끝난다

`GET /live/Schedule_Day/{오늘}` 한 번이면 **그날 KBO 전 경기**(최대 5)의 상태·이닝·점수를 받는다. 목록 화면 전체가
단일 요청으로 갱신되므로 경기별 개별 폴링이 필요 없다. 응답은 5 KB 안팎이다.

| 화면 / 상태 | 간격 | 요청 |
|---|---:|---|
| 경기 목록, 라이브 있음 | 20초 | `Schedule_Day/{오늘}` × 1 (공식 앱은 4초) |
| 경기 목록, 라이브 없음 | 폴링 없음 | 진입 시 1회 + 당겨서 새로고침 |
| 경기 상세, `LIVE` | 15초 | `live/schedule/{seq}` × 1 (라인스코어·R/H/E 필요, 서버 캐시 2초) |
| 경기 상세, `SCHEDULED` | 폴링 없음 | 진입 시 1회 |
| 경기 상세, `FINAL` | 중단 | 전환 직후 1회 확정 조회 |
| 순위 | TTL 10분 | `League_Rank?year=` 진입 시 조건부 (서버 캐시 1시간) |
| 시즌 일정 프리페치 | 하루 1회 | `Schedule_Month/{현재·다음 달}` (재편성 반영) |

전부 **화면이 `STARTED` 라이프사이클일 때만** 동작한다. WorkManager는 최소 주기 제한이 있어 실시간
폴링에 쓰지 않고, 캐시 동기화와 일정 프리페치에만 쓴다.

> 목록 응답에는 이닝별 득점이 없고(총점·이닝 코드만) 상세에만 `boxscore`가 있으므로 상세 폴링은 필수다.
> 상세 응답의 `other_game_state`에 같은 날 다른 경기의 점수·이닝이 함께 오므로, 상세 화면을 보는 동안은
> 목록 폴링을 멈추고 이 값으로 목록을 갱신할 수 있다 → `DS-002`에서 확인.

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
- **적응형 간격**: 응답이 이전과 같으면(DB 쓰기 스킵) 간격 1.5배(최대 40초), 변화 감지 시 기본값 복귀
- **jitter**: ±10% 난수
- **backoff**: 실패 시 2배 증가(최대 2분), 성공 시 즉시 복구
- **네트워크 콜백**: 끊기면 즉시 중단, 복구 시 즉시 1회 조회

### 7.3 종료 처리

`LIVE → FINAL`(`state: e`) 전환을 감지하면 폴링 중단 **전에** `live/schedule/{seq}`를 1회 더 호출한다. 마지막
이닝 득점이 반영되기 전에 상태만 먼저 바뀔 수 있다. `end_summary`(승·패·세이브 투수)가 채워지는 시점이
최종 확정 신호일 가능성이 있어 `DS-002`에서 관찰한다.

---

# IV. 실행 (언제·어떤 순서로)

## 8. 단계별 구현 계획

각 단계는 "구현 → 자동 테스트 → 실기기 확인"으로 끝낸다. 1인 기준 소요를 병기한다.

### Step 1 — 실기기 접근성 + 라이브 스키마 스파이크 (0.5일, **최우선**)

§2.4의 미검증 항목을 닫는다. **여기서 막히면 이후 전부 무의미하므로 코드 작성 전에 한다.**

- [ ] `DS-001` **실기기/에뮬레이터에서 앱의 OkHttp로 `live/Schedule_Day/{오늘}`이 봉투 `code:"00"`으로 오는지 확인.** 모바일 네트워크와 Wi-Fi 양쪽. HTTP 200은 판정 기준이 아니다(§3.4-1). `01`이면 공통 쿼리 인터셉터부터 본다
- [x] `DS-002a` **라이브 시작 관측 (2026-09-15 18:31)** — 진행 중 `state = i`, 목록 행에 볼카운트·주자·현재 투수/타자 포함, `boxscore` 현재 하프이닝 `0`, `game_result`가 이닝 라벨(§2.4·§3.4-4)
- [ ] `DS-002b` **라이브 종료 관측** — `i → e` 전환 시 `end_summary` 채워지는 시점, 마지막 이닝 득점과 상태 전환 순서, 목록 대비 상세 갱신 지연
- [ ] `DS-003` `/extra/notice` 부트스트랩 응답의 `update.next_action`·`server.next_action` 처리 — 강제 업데이트/차단 신호를 앱 시작 시 확인
- [ ] `DS-004` 프리페치 확인 — `Schedule_Month` 3~11월 890행 중 KBO 필터(§3.4-8) 통과 782행이 시즌 경기 수(정규 720 + 취소 70)에 맞는지, WBC·시범경기·올스타전이 걸러지는지
- [ ] `DS-005` fixture 저장 → `app/src/test/resources/fixtures/` (예정/라이브/종료/연장 11회/취소·노게임 각 1건 이상)

**산출물**: fixture 세트(Step 1) + `DS-002` 관측 기록.
**완료 조건**: §3.4의 함정 8개 + `DS-002` 신규 발견 항목이 전부 fixture로 고정됨.

### Step 2 — 프로젝트 부트스트랩 (0.5일)

- [ ] `DS-010` Compose 프로젝트, version catalog(§5.4), `compileSdk 36` / `minSdk 26`, AGP built-in Kotlin(§5.3)
- [ ] `DS-011` Hilt(KSP2), Retrofit 3/OkHttp/kotlinx.serialization, Room(KSP2), Coil 3, **Navigation 3**
- [ ] `DS-012` Material 3 테마 + **10개 구단 자체 컬러 토큰**(§2.2) + 한국어 팀명 리소스(§2.2) — 팀명은 `core/common`, 컬러는 `core/designsystem`으로 분리(§5.1)
- [ ] `DS-013` `core/navigation`에 `NavKey` 7개 정의(`@Serializable`)
- [ ] `DS-014` CI: `assembleDebug` + unit test + lint

### Step 3 — 네트워크·매핑 계층 (1.5일)

- [ ] `DS-020` DTO 정의 — 공통 `Envelope<T>`, 문자열 수치는 `String`으로, `boxscore`는 `List<Int?>`
- [ ] `DS-021` `WisetotoApi` + 공통 쿼리/UA 인터셉터 + 최소간격 인터셉터, `Envelope.body()`로 `code` 검사
- [ ] `DS-022` 매퍼 — 상태(§4.1), 이닝 라벨, 라인스코어(§4.2), 취소 점수 제거(§3.4-3), 문자열 수치(§3.4-2)
- [ ] `DS-023` **매퍼 단위 테스트 — §3.4 함정 8개를 각각 독립 테스트 케이스로.** 특히 연장 11회 득점이 라인스코어에 나타나는지, 취소 경기 점수가 `null`인지, 3월 목록에서 WBC·시범경기가 걸러지는지
- [ ] `DS-024` MockWebServer — 타임아웃 / 500 / 깨진 JSON / 빈 배열 / `code:"01"` 봉투 / 미지의 `state`

**완료 조건**: fixture만으로 매퍼 branch coverage 90%+. **함정 8개 테스트 없이 다음 단계로 넘어가지 않는다.**

### Step 4 — Room + Repository + 시즌 프리페치 (2일)

- [ ] `DS-030` Entity/DAO/Database, schema export
- [ ] `DS-031` **시즌 프리페치 워커**(§3.2) — `Schedule_Month` 3~11월, 하루 1회 현재·다음 달 재조회
- [ ] `DS-032` `GamesRepository` — `observeByDate(LocalDate)`는 Room, `refreshDay`/`refreshGame`은 네트워크→트랜잭션 upsert
- [ ] `DS-033` 행 동등 비교 기반 쓰기 스킵(§6), single-flight, `DataFreshness`
- [ ] `DS-034` 통합 테스트: 캐시 히트, 오프라인, 프리페치 중단·재개, 롤백

**완료 조건**: 비행기 모드에서 시즌 전체 일정을 날짜 이동으로 탐색할 수 있다.

### Step 5 — 경기 목록 (1.5일)

- [ ] `DS-040` `GamesViewModel` + `GamesUiState`(날짜, 섹션, freshness, error)
- [ ] `DS-041` 날짜 네비게이션 + `SavedStateHandle` 보존(읽기만 하지 말고 쓸 것), "오늘" 버튼
- [ ] `DS-042` 경기 카드 4종 상태, **원정팀 먼저 표시**(KBO 관행)
- [ ] `DS-043` `LivePoller` + `Schedule_Day/{오늘}` 연동(§7.1)
- [ ] `DS-044` loading / empty / error / stale UI

**완료 조건**: 경기일에 30분 켜두고 점수가 자동 갱신되며, 홈 → 복귀 시 폴링이 정확히 멈췄다 재개된다.

### Step 6 — 경기 상세 (1.5일)

- [ ] `DS-050` 스코어 헤더 + 상태 라벨(원문 표시)
- [ ] `DS-051` **라인스코어 테이블** — 동적 이닝, 연장 가로 스크롤, 미진행 이닝 구분
- [ ] `DS-052` 구장·안타·실책·승/패/세이브 투수 정보 섹션 (공급되는 것만)
- [ ] `DS-053` 상세 폴링 + `FINAL` 확정 조회(§7.3)
- [ ] `DS-054` 볼카운트·주자·라인업 영역을 **만들지 않음**을 코드 리뷰에서 확인(§1.2, `DS-002` 이후 P1)

**완료 조건**: 9이닝 / 연장 / 취소 / 미진행 fixture 골든 시나리오 통과.

### Step 7 — 순위·팀·즐겨찾기 (1.5일)

- [ ] `DS-060` 순위 화면 — 승-패-무, 승률, 게임차, 연속(`straight`); 5위 뒤 진출선은 UI 고정
- [ ] `DS-061` 팀 상세 — 구장·감독(`Team_Info`), 최근/예정 경기는 Room(`observeByTeam`)
- [ ] `DS-062` 팀 즐겨찾기 → 목록 상단 고정

### Step 8 — 마감 (1.5일)

- [ ] `DS-070` 설정: 테마, 폴링 간격, **데이터 출처 표기(wisetoto · 프로야구 LIVE)**
- [ ] `DS-071` Nav3 연결 — 탭별 back stack 4개, `entryProvider`, decorator 2개(saveable + viewModelStore)
- [ ] `DS-072` 접근성 — TalkBack 순서, 48dp, 200% 글꼴에서 라인스코어 스크롤
- [ ] `DS-073` 적응형 레이아웃 — `ListDetailSceneStrategy`로 compact/medium/expanded 목록-상세
- [ ] `DS-074` Baseline Profile, 30분 라이브 배터리·메모리 측정
- [ ] `DS-075` R8 릴리스 빌드 검증

**총 예상: 10~11일** (1인). 단 `DS-002`와 Step 5·6 검증이 실제 경기일에 묶이므로 캘린더 기준 2~3주.

### 착수 순서 — 지금 시작할 3가지

1. **`DS-001`** — 실기기에서 wisetoto API 호출이 `code 00`으로 오는지 확인. 이 계획 전체의 전제다. **가장 먼저, 코드 작성 전에.**
2. **`DS-002b`** — 경기 종료 전환 관측. 시작 시점 스키마는 09-15에 확보했고(§2.4) 종료 시 `end_summary` 타이밍만 남았다.
3. **`DS-010`** — Compose 프로젝트 생성. `DS-002`를 기다리는 동안 병행.

---

# V. 검증·운영

## 9. 테스트 전략

| 층 | 대상 | 도구 |
|---|---|---|
| 단위 | 매퍼(§3.4 함정 8종), 상태 매핑, 이닝 코드·15칸 라인스코어 파싱, 문자열 수치, KBO 필터, `LivePoller` 간격 | JUnit, coroutines-test, Turbine |
| 통합 | 월 프리페치 순회, Repository 캐시/오프라인/트랜잭션/쓰기 스킵, `code 01` 봉투 처리, Room 마이그레이션 | MockWebServer, Room testing |
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
| **앱 버전 게이팅·인증 도입** | 중 | 치명 | `/extra/notice`의 `next_action`을 시작 시 확인(`DS-003`). `code 01`이 연속되면 retry 없이 circuit open + 기능 flag off(§13 B). 우회하지 않는다 |
| **진행 중 `state` 값이 폴백과 다름** | 중 | 큼 | 점수 유무 폴백(§4.1)으로 LIVE 판정, 이닝 라벨은 코드 파싱 실패 시 "진행 중". `DS-002`로 사전 확인 |
| 목록에 이닝별 득점 없음 | 확정 | 중 | 상세 폴링 유지(§7.1), `other_game_state`로 보완 검토 |
| 라이브 갱신 지연 | 중 | 중 | 응답 동등 비교 기반 신선도 표시, "마지막 갱신" 명시 |
| 스키마 변경·필드명 오타 정정 | 중 | 중 | `ignoreUnknownKeys`, 전 필드 nullable, `@SerialName` 한곳, 필드 단위 폐기 |
| 과도한 폴링으로 차단 | 낮 | 큼 | 라이브 요청 1개로 통합(§7.1), 공식 앱(4초)보다 느린 20초, jitter, 화면 꺼짐 시 중단 |
| 문자중계 서버 보존 약 90일 | 확정 | 낮 | P1에서 앱이 저장 |
| 포스트시즌 스키마 차이 | 중 | 중 | MVP는 정규시즌. 10월 이전에 포스트시즌 표본 확보 |
| 더블헤더 | 낮 | 낮 | 같은 `leagueDate`에 같은 팀 2경기 → `game_timestamp`·`double_header_no`로 정렬·구분 |
| 이용약관(상업적 이용 금지) | 확정 | 큼(공개 배포 시) | 개인 사용 한정. 공개 배포는 서면 승낙 후(§13 B) |

## 11. Definition of Done

한 기능은 아래를 모두 만족할 때만 완료다.

- 요구사항과 수용 기준(§1.6)을 충족한다.
- §5.1의 경계 규칙 4개를 침범하지 않는다. 리뷰에서 실제로 보는 것:
  - ViewModel 생성자에 `WisetotoApi`·DAO·`*Entity`가 없다.
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

## 12. 부록 A — 데이터 소스 교체 이력 (SofaScore → wisetoto, 2026-09-14~15)

이 계획은 2026-08-02~09-03까지 SofaScore(`api.sofascore.com/api/v1`, KBO `uniqueTournament 11204`)를 전제로
작성됐다. 2026-09-14 wisetoto API를 실측 검증하고 09-15 실기기에서 추출한 앱 APK로 전체 엔드포인트를 확보한
뒤 **데이터 소스를 wisetoto로 교체**했다. 상세 검증 보고서는 공개 저장소에서 제외한 별도 로컬 자료다.

**교체 근거**

| 항목 | SofaScore | wisetoto |
|---|---|---|
| 접근 | TLS 핑거프린트 차단 — curl·JDK 403, OkHttp만 200 | 클라이언트 무관 200 (`os`·`version`·`lang` 세 키 필수) |
| 커버리지 | 득점 전용. 라인업·박스스코어·문자중계 404 | 이닝별 득점 + R/H/E/B + 볼카운트·주자 + 라인업 + 문자중계 + 선수 |
| 연장 라인스코어 | **오류** — 11이닝 경기를 10이닝으로 압축(09-10 NC 2:1 KIA, 보도로 확인) | 정확 (15칸 배열) |
| 미실시 이닝 | `inning9.run = -1` (최근 30경기 중 14건) | `null` |
| 무승부 | 필드 없음, `matches - wins - losses`로 파생 | `draw_count` 직접 |
| 한국어 팀명 | 없음 | 약칭 제공 |
| 날짜 조회 | 없음(시즌 페이지 순회) | `Schedule_Day/{yyyyMMdd}` |

SofaScore 시절 확정한 사실 중 남길 것: 무승부 `winnerCode = 3`(`DS-002` 구 항목 해소), 라이브 스키마는 두 소스
모두 미관측이었다는 점. 이전 `DS-120`·`DS-121`·`DS-125`(SofaScore APK 경로 검증)는 폐기한다.

**wisetoto 접근 메모**: 경로 대소문자 구분, 필수 쿼리, Python 기본 UA 401, 앱 부트스트랩 `/extra/notice`의
강제 업데이트 신호. 전부 §2.1·§3.4에 반영됐다.

## 13. 부록 B — 공개 배포로 확장할 때 (현재 범위 밖)

개인용 트랙에는 해당 없다. 앱을 스토어에 공개하려면 **앱이 wisetoto를 직접 호출하는 구조를 버리고**
아래가 필요하다. 통합 전 BFF 계획의 요지만 남긴다.

1. **데이터 사용 권리 (선행 게이트)**: 서면 사용 허가 없이 공개 배포하지 않는다. wisetoto 이용약관은
   "서비스에서 얻은 정보의 사전 승낙 없는 복제·유통·상업적 이용"을 금지한다. 호출이 된다는 것과 호출할 권리는
   별개다. 캐시 기간·재배포·출처 표기·계약 종료 시 삭제를 계약서에서 확인.
2. **BFF 도입**: 앱은 공급자 중립 계약(OpenAPI)만 보고, `bsrest.wisetoto.com`·`team_info_seq` 같은 문자열은
   서버 코드에만 둔다. base URL은 서버 주도로 바뀌므로 호스트를 상수로 박지 않는다.
3. **집계·회복탄력성**: 라이브는 서버가 한 번 조회해 fan-out, request coalescing·circuit breaker·
   backoff. `code 01`·401은 retry storm 없이 circuit open + 경보 + 기능 flag off.
4. **관측성·보안·개인정보**: data age SLO 경보, APK secret scan, cleartext 차단(선수 사진 URL이 `http://`로
   오므로 `https`로 승격), 계정 없는 MVP의 수집 이벤트·보존기간 문서화.
5. **단계 배포**: 내부 → 폐쇄 → 5% → 25/50/100%, 경기일 간격 확대, 임계치 초과 시 flag off/롤백.

전체 세부 계획이 필요하면 별도 문서로 복원한다. 지금은 개인용 트랙이 유일한 실행 대상이다.

---

## 참고

- [프로야구 LIVE — Google Play (com.tionnet.android.baseball)](https://play.google.com/store/apps/details?id=com.tionnet.android.baseball) — API의 원 소비자 앱. 공식 문서화된 공개 API가 없으므로 스키마 변경 통지를 기대할 수 없다
- [와이즈토토 이용약관](https://www.wisetoto.com/customer/agreement.htm) — 상업적 이용·재배포 제한의 근거
- [Android 앱 아키텍처 권장사항](https://developer.android.com/topic/architecture/recommendations)
- [Android 오프라인 우선 가이드](https://developer.android.com/topic/architecture/data-layer/offline-first)
- [Compose 접근성 semantics](https://developer.android.com/develop/ui/compose/accessibility/semantics)
