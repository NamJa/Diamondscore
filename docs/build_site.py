#!/usr/bin/env python3
"""DiamondScore 구현 계획 정적 사이트 생성기.

콘텐츠를 아래 STEPS 데이터로 두고, 공유 템플릿/CSS로 Step별 HTML을 찍어낸다.
GitHub Pages(/docs 폴더) 배포용. 재생성: `python3 docs/build_site.py`
"""
import html
import pathlib

OUT = pathlib.Path(__file__).parent          # docs/
ASSETS = OUT / "assets"

# ─────────────────────────────────────────────────────────────────────────────
# 콘텐츠 (여기만 고치면 사이트 전체가 갱신된다)
# ─────────────────────────────────────────────────────────────────────────────

META = {
    "title": "DiamondScore 구현 계획",
    "subtitle": "KBO 실시간 Android 앱 · SofaScore API · Step-by-Step",
    "stack": "Kotlin 2.4 · Compose · Retrofit 3 · Coil 3 · KSP2",
    "plan_md": "IMPLEMENTATION_PLAN_KO.md",
}

# Step 0 = 개요/랜딩
ROADMAP = [
    (1, "접근성·스키마 스파이크", "0.5일", "실기기 403 여부와 라이브 스키마를 코드 전에 확인"),
    (2, "프로젝트 부트스트랩", "0.5일", "Compose·Hilt·Retrofit 3·Room·Coil 3 뼈대와 CI"),
    (3, "네트워크·매핑 계층", "1.5일", "DTO·매퍼·함정 7개 테스트로 고정"),
    (4, "Room + Repository + 프리페치", "2일", "시즌 전체를 로컬 SSOT로, 오프라인 날짜 탐색"),
    (5, "경기 목록", "1.5일", "날짜 네비게이션 + 라이브 폴링 1요청"),
    (6, "경기 상세", "1.5일", "동적 라인스코어(연장) + 종료 확정"),
    (7, "순위·팀·즐겨찾기", "1.5일", "승-패-무 파생, 팀 상세, 즐겨찾기"),
    (8, "마감", "1.5일", "접근성·적응형·성능·R8 릴리스"),
]

CONTEXT_CARDS = [
    ("데이터 제약 — 득점 전용", "danger",
     "SofaScore의 KBO 데이터는 일정·이닝별 득점·순위·팀/구장/감독만 제공한다. "
     "볼카운트·주자·투수/타자·라인업·박스스코어·선수 기록·문자중계는 <strong>404</strong>다. "
     "이 커버리지가 P0/P1 범위를 결정한다."),
    ("단일 요청 라이브", "ok",
     "<code>GET /sport/baseball/events/live</code> 한 번이 진행 중인 KBO 전 경기를 반환한다. "
     "경기별 개별 폴링이 필요 없어 트래픽·배터리·차단 위험이 모두 낮다."),
    ("최우선 리스크 — 403", "warn",
     "분석 환경에서 API가 403이었다(출처 IP 기반 추정). 실기기 접근은 미검증. "
     "<strong>Step 1(DS-001)</strong>이 코드 작성 전 관문이다 — 실패 시 보조 소스로 재설계."),
]

START_NOW = [
    ("DS-001", "실기기에서 SofaScore API 호출 성공 확인. 계획 전체의 전제. 가장 먼저."),
    ("DS-002", "게임 데이 18:30 KST 경기에서 라이브 응답 3시간 기록. 스크립트를 미리 준비."),
    ("DS-010", "Compose 프로젝트 생성. DS-002 대기 중 병행."),
]

STEPS = [
    {
        "num": 1,
        "title": "실기기 접근성 + 라이브 스키마 스파이크",
        "duration": "0.5일",
        "priority": "최우선",
        "goal": "미검증 항목(§2.4)을 코드 작성 전에 닫는다. 여기서 막히면 이후가 전부 무의미하다.",
        "prereq": "없음 — 프로젝트 부트스트랩보다 먼저 한다.",
        "substeps": [
            {"id": "DS-001", "title": "실기기/에뮬레이터 접근성 확인",
             "tasks": ["OkHttp로 <code>/unique-tournament/11204/seasons</code> 호출",
                       "모바일 네트워크 + Wi-Fi 양쪽에서 상태 코드 확인",
                       "403이면 즉시 중단하고 보조 소스(naver)로 재설계 판단"],
             "ref": "§2.1 · §10 리스크"},
            {"id": "DS-002", "title": "게임 데이 라이브 관측 (3시간)",
             "tasks": ["<code>/sport/baseball/events/live</code>를 30초 간격 기록",
                       "확정: 라이브 <code>status.code/description</code>, 진행 중 <code>innings</code> 맵 형태, "
                       "<code>time</code> 필드, 갱신 지연, <code>winnerCode</code> 무승부 값, <code>feedLocked</code> 전환",
                       "특히 라이브 응답에 <code>innings</code>가 포함되는지 확인 (§7.1 폴링 설계가 여기 달림)"],
             "ref": "§2.4 · §7.1"},
            {"id": "DS-003", "title": "응답 헤더 조사",
             "tasks": ["<code>ETag</code> / <code>Cache-Control</code> / <code>Last-Modified</code> 지원 여부",
                       "지원되면 조건부 요청으로 라이브 폴링 트래픽 절감"],
             "ref": "§5.2"},
            {"id": "DS-004", "title": "프리페치 페이지네이션 확인",
             "tasks": ["<code>/events/next/{page}</code> page 0→N 종료 조건",
                       "총 경기 수가 720에 수렴하는지"],
             "ref": "§3.2"},
            {"id": "DS-005", "title": "fixture 저장",
             "tasks": ["<code>app/src/test/resources/fixtures/</code>에 예정/라이브/종료/연장/취소 각 1건 이상"],
             "ref": "§9 테스트"},
        ],
        "done": ["§3.4 함정 7개 + DS-002 신규 발견 항목이 전부 fixture로 고정됨",
                 "산출물: <code>docs/data/SOFASCORE_KBO_FIELDS.md</code> 필드 사전 + fixture 세트"],
    },
    {
        "num": 2,
        "title": "프로젝트 부트스트랩",
        "duration": "0.5일",
        "priority": None,
        "goal": "Kotlin 2.4 · Compose · Hilt · Retrofit 3 · Room · Coil 3 뼈대와 CI를 세운다.",
        "prereq": "DS-001 접근 확인(병행 가능).",
        "substeps": [
            {"id": "DS-010", "title": "프로젝트·version catalog",
             "tasks": ["Compose 프로젝트, version catalog (동적 버전 금지)",
                       "<code>compileSdk 36</code> / <code>minSdk 26</code>, Kotlin 2.4.x, JDK 17 toolchain",
                       "Compose 컴파일러는 <code>plugin.compose</code>만 적용(별도 버전 pin 없음)"],
             "ref": "§5.4 버전표"},
            {"id": "DS-011", "title": "의존성 (전부 KSP2)",
             "tasks": ["Hilt(KSP2), Retrofit 3/OkHttp/kotlinx.serialization, Room(KSP2), Coil 3",
                       "kapt 미사용. Coil 3는 앱 OkHttp 인스턴스 공유"],
             "ref": "§5.3"},
            {"id": "DS-012", "title": "테마·리소스",
             "tasks": ["Material 3 테마",
                       "<strong>10개 구단 자체 컬러 토큰</strong> (API teamColors가 전부 동일 §3.4-5)",
                       "한국어 팀명 리소스 (API에 <code>ko</code> 없음 §2.2)"],
             "ref": "§2.2 · §3.4-5"},
            {"id": "DS-013", "title": "CI",
             "tasks": ["<code>assembleDebug</code> + unit test + lint"],
             "ref": None},
        ],
        "done": ["API 26/36 에뮬레이터에서 빈 앱 실행, 라이트/다크 preview 렌더",
                 "clean checkout 기준 CI build/lint/test 통과"],
    },
    {
        "num": 3,
        "title": "네트워크·매핑 계층",
        "duration": "1.5일",
        "priority": None,
        "goal": "DTO·매퍼를 만들고 실측 함정 7개를 각각 독립 테스트로 고정한다.",
        "prereq": "Step 2 뼈대, Step 1의 fixture.",
        "substeps": [
            {"id": "DS-020", "title": "DTO 정의",
             "tasks": ["필요 필드만. <code>innings</code>는 <code>Map&lt;String, InningRunDto&gt;</code> (키가 동적 §3.4-3)"],
             "ref": "§3.3"},
            {"id": "DS-021", "title": "API·인터셉터",
             "tasks": ["<code>SofaScoreApi</code> + 헤더/최소간격 인터셉터",
                       "<code>KboDataSource</code> 인터페이스(테스트용 Fake 대비)"],
             "ref": "§5.2"},
            {"id": "DS-022", "title": "매퍼",
             "tasks": ["상태 매핑 (<code>status.type</code> 기준 §4.1)",
                       "라인스코어 (<code>innings</code> 파싱, <code>period*</code> 무시 §4.2)",
                       "무승부 파생 (<code>matches - wins - losses</code> §3.4-1)"],
             "ref": "§4.1 · §4.2 · §3.4"},
            {"id": "DS-023", "title": "매퍼 단위 테스트 — 함정 7개",
             "tasks": ["§3.4 함정 7개를 각각 독립 케이스로",
                       "특히 연장 경기에서 10회 득점이 라인스코어에 나타나는지"],
             "ref": "§3.4"},
            {"id": "DS-024", "title": "MockWebServer",
             "tasks": ["타임아웃 / 500 / 깨진 JSON / 빈 배열 / 미지의 <code>status.type</code>"],
             "ref": "§9"},
        ],
        "done": ["fixture만으로 매퍼 branch coverage 90%+",
                 "<strong>함정 7개 테스트 없이 다음 단계로 넘어가지 않는다</strong>"],
    },
    {
        "num": 4,
        "title": "Room + Repository + 시즌 프리페치",
        "duration": "2일",
        "priority": None,
        "goal": "시즌 전체를 로컬 SSOT로 프리페치해, 날짜 조회를 네트워크 없이 로컬 쿼리로 처리한다.",
        "prereq": "Step 3 매퍼.",
        "substeps": [
            {"id": "DS-030", "title": "Entity/DAO/Database",
             "tasks": ["§6 엔티티 표대로. schema export 켜기",
                       "점수는 <code>InningRunEntity</code>로 정규화(스칼라 아님)"],
             "ref": "§6"},
            {"id": "DS-031", "title": "시즌 프리페치 워커",
             "tasks": ["<code>next</code>/<code>last</code> 페이지 순회, 빈 배열까지, 최대 60페이지",
                       "<code>leagueDate</code>는 Asia/Seoul로 변환 저장 (§3.2)"],
             "ref": "§3.2"},
            {"id": "DS-032", "title": "GamesRepository",
             "tasks": ["<code>observeByDate(LocalDate)</code>는 Room에서 읽기",
                       "<code>refresh*</code>는 네트워크 → 트랜잭션 upsert"],
             "ref": "§6"},
            {"id": "DS-033", "title": "쓰기 최적화",
             "tasks": ["<code>changeTimestamp</code> 동일 시 DB 쓰기 스킵",
                       "single-flight, <code>DataFreshness</code> 상태"],
             "ref": "§6"},
            {"id": "DS-034", "title": "통합 테스트",
             "tasks": ["캐시 히트, 오프라인, 프리페치 중단·재개, 롤백"],
             "ref": "§9"},
        ],
        "done": ["비행기 모드에서 시즌 전체 일정을 날짜 이동으로 탐색할 수 있다"],
    },
    {
        "num": 5,
        "title": "경기 목록",
        "duration": "1.5일",
        "priority": None,
        "goal": "날짜별 경기 목록과 라이브 자동 갱신(단일 요청)을 완성한다.",
        "prereq": "Step 4 Repository.",
        "substeps": [
            {"id": "DS-040", "title": "ViewModel·UiState",
             "tasks": ["<code>GamesUiState</code>(날짜, 섹션, freshness, error)"],
             "ref": "§1.3"},
            {"id": "DS-041", "title": "날짜 네비게이션",
             "tasks": ["이전/다음/오늘, <code>SavedStateHandle</code>로 선택 날짜 보존"],
             "ref": "§1.3"},
            {"id": "DS-042", "title": "경기 카드",
             "tasks": ["4종 상태(예정/진행/종료/취소·연기)",
                       "<strong>원정팀 먼저 표시</strong> (§3.4-4)"],
             "ref": "§3.4-4"},
            {"id": "DS-043", "title": "라이브 폴링",
             "tasks": ["<code>LivePoller</code> + <code>/events/live</code>, STARTED에서만, jitter·backoff"],
             "ref": "§7.1 · §7.2"},
            {"id": "DS-044", "title": "상태 UI",
             "tasks": ["loading / empty / error / stale"],
             "ref": "§1.3"},
        ],
        "done": ["경기일 30분 켜두면 점수가 자동 갱신되고, 홈→복귀 시 폴링이 정확히 멈췄다 재개된다"],
    },
    {
        "num": 6,
        "title": "경기 상세",
        "duration": "1.5일",
        "priority": None,
        "goal": "동적 라인스코어(연장 포함)와 종료 확정을 구현한다. 범위 밖 UI는 만들지 않는다.",
        "prereq": "Step 5.",
        "substeps": [
            {"id": "DS-050", "title": "스코어 헤더",
             "tasks": ["상태 라벨은 <code>status.description</code> 원문 표시(추정 금지)"],
             "ref": "§4.1"},
            {"id": "DS-051", "title": "라인스코어 테이블",
             "tasks": ["동적 이닝, 연장 가로 스크롤, 미진행 이닝 구분"],
             "ref": "§4.2"},
            {"id": "DS-052", "title": "정보 섹션",
             "tasks": ["구장·감독·시즌·라운드"],
             "ref": "§3.3"},
            {"id": "DS-053", "title": "상세 폴링·종료 확정",
             "tasks": ["<code>FINAL</code> 전환 직후 1회 확정 조회 (§7.3)"],
             "ref": "§7.3"},
            {"id": "DS-054", "title": "범위 밖 확인",
             "tasks": ["볼카운트·주자·라인업 영역을 <strong>만들지 않음</strong>을 코드 리뷰에서 확인"],
             "ref": "§1.2"},
        ],
        "done": ["9이닝 / 연장 / 취소 / 미진행 fixture 골든 시나리오 통과"],
    },
    {
        "num": 7,
        "title": "순위·팀·즐겨찾기",
        "duration": "1.5일",
        "priority": None,
        "goal": "순위표, 팀 상세, 팀 즐겨찾기를 완성한다.",
        "prereq": "Step 4 Repository, Step 5 카드.",
        "substeps": [
            {"id": "DS-060", "title": "순위 화면",
             "tasks": ["승-패-<strong>무</strong>(파생), 승률, 게임차, 득실차",
                       "<code>promotion.text</code> 진출권 배지, 공급 안 되는 컬럼은 숨김"],
             "ref": "§1.3 · §3.4-1"},
            {"id": "DS-061", "title": "팀 상세",
             "tasks": ["구장·수용인원·감독, 최근/예정 경기(<code>/team/{id}/events/*</code>)"],
             "ref": "§3.1"},
            {"id": "DS-062", "title": "팀 즐겨찾기",
             "tasks": ["로컬 저장, 목록 상단 고정"],
             "ref": "§6"},
        ],
        "done": ["순위→팀→최근 경기 여정과 back 문맥 복원이 된다"],
    },
    {
        "num": 8,
        "title": "마감 — 접근성·적응형·성능·릴리스",
        "duration": "1.5일",
        "priority": None,
        "goal": "접근성·적응형 레이아웃·성능을 마무리하고 R8 릴리스 빌드를 검증한다.",
        "prereq": "Step 5~7 화면.",
        "substeps": [
            {"id": "DS-070", "title": "설정",
             "tasks": ["테마, 폴링 간격, <strong>데이터 출처 표기(SofaScore)</strong>"],
             "ref": "§1.3"},
            {"id": "DS-071", "title": "접근성",
             "tasks": ["TalkBack 순서, 48dp, 200% 글꼴에서 라인스코어 스크롤"],
             "ref": "§1.5"},
            {"id": "DS-072", "title": "적응형 레이아웃",
             "tasks": ["compact/medium/expanded 목록-상세"],
             "ref": "§5.5"},
            {"id": "DS-073", "title": "성능",
             "tasks": ["Baseline Profile, 30분 라이브 배터리·메모리 측정"],
             "ref": "§9"},
            {"id": "DS-074", "title": "릴리스",
             "tasks": ["R8 full mode 릴리스 빌드 검증(직렬화 DTO 생존 확인)"],
             "ref": "§5.3"},
        ],
        "done": ["§1.6 SLO·수용 기준 통과, P0 회귀 0건",
                 "총 예상 10~11일(1인), 캘린더 2~3주(게임 데이 검증 포함)"],
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# 템플릿
# ─────────────────────────────────────────────────────────────────────────────

def nav(active):
    items = ['<a href="index.html"%s>개요</a>' % (' class="active"' if active == 0 else "")]
    for n in range(1, 9):
        cls = ' class="active"' if active == n else ""
        items.append(f'<a href="step-{n}.html"{cls}>Step {n}</a>')
    return '<nav class="steps">' + "".join(items) + "</nav>"


def page(title, active, body):
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · DiamondScore</title>
<link rel="stylesheet" href="assets/site.css">
</head>
<body>
<header class="top">
  <a class="brand" href="index.html">◆ DiamondScore</a>
  <span class="stack">{html.escape(META['stack'])}</span>
</header>
{nav(active)}
<main>
{body}
</main>
<footer>
  <p>단일 계획 문서: <a href="{META['plan_md']}">{META['plan_md']}</a> · 이 사이트는 <code>docs/build_site.py</code>로 생성됨</p>
</footer>
</body>
</html>
"""


def render_index():
    cards = "".join(
        f'<article class="ctx {kind}"><h3>{t}</h3><p>{body}</p></article>'
        for t, kind, body in CONTEXT_CARDS
    )
    road = "".join(
        f'<a class="road" href="step-{n}.html"><span class="rn">Step {n}</span>'
        f'<span class="rt">{html.escape(t)}</span>'
        f'<span class="rd">{html.escape(d)}</span>'
        f'<span class="rg">{html.escape(g)}</span></a>'
        for n, t, d, g in ROADMAP
    )
    start = "".join(
        f"<li><code>{i}</code> {html.escape(x)}</li>" for i, x in START_NOW
    )
    body = f"""
<section class="hero">
  <span class="step0">Step 0 · 개요</span>
  <h1>{html.escape(META['title'])}</h1>
  <p class="sub">{html.escape(META['subtitle'])}</p>
</section>

<section>
  <h2>먼저 알아야 할 것</h2>
  <div class="ctx-grid">{cards}</div>
</section>

<section>
  <h2>구현 로드맵 (Step 1 → 8)</h2>
  <p class="lead">각 단계는 “구현 → 자동 테스트 → 실기기 확인”으로 끝낸다. 카드를 눌러 상세로 이동.</p>
  <div class="road-grid">{road}</div>
</section>

<section class="startnow">
  <h2>지금 시작할 3가지</h2>
  <ol>{start}</ol>
</section>
"""
    return page("개요", 0, body)


def render_step(s):
    n = s["num"]
    prio = f'<span class="badge prio">{s["priority"]}</span>' if s.get("priority") else ""
    subs = ""
    for i, sub in enumerate(s["substeps"], 1):
        ref = f'<span class="ref">{sub["ref"]}</span>' if sub.get("ref") else ""
        tasks = "".join(f"<li>{t}</li>" for t in sub["tasks"])
        subs += f"""
    <li class="sub">
      <div class="sub-head"><span class="dsid">{sub['id']}</span>
        <span class="sub-title">{sub['title']}</span>{ref}</div>
      <ul class="tasks">{tasks}</ul>
    </li>"""
    done = "".join(f"<li>{d}</li>" for d in s["done"])
    prev_link = ('<a href="index.html">← 개요</a>' if n == 1
                 else f'<a href="step-{n-1}.html">← Step {n-1}</a>')
    next_link = (f'<a href="step-{n+1}.html">Step {n+1} →</a>' if n < 8 else "")
    body = f"""
<section class="hero step">
  <span class="step0">Step {n} / 8 · {s['duration']}</span>
  <h1>{html.escape(s['title'])} {prio}</h1>
</section>

<div class="meta-box">
  <p><strong>목표</strong> {s['goal']}</p>
  <p><strong>선행 조건</strong> {s['prereq']}</p>
</div>

<section>
  <h2>세부 단계</h2>
  <ol class="substeps">{subs}
  </ol>
</section>

<section class="done">
  <h2>완료 조건</h2>
  <ul class="check">{done}</ul>
</section>

<nav class="pager">{prev_link}{next_link}</nav>
"""
    return page(f"Step {n} — {s['title']}", n, body)


CSS = """
:root{
  --bg:#f7f8fa; --surface:#ffffff; --ink:#1a1d24; --muted:#5b6472; --line:#e4e7ec;
  --brand:#ae0d1d; --accent:#44a0cb; --code-bg:#f0f2f5;
  --ok:#0f7a4d; --ok-bg:#e7f6ee; --warn:#a8710a; --warn-bg:#fbf1dd; --danger:#b0202f; --danger-bg:#fbe9eb;
}
@media (prefers-color-scheme:dark){
  :root{
    --bg:#0f1216; --surface:#171b21; --ink:#e6e9ef; --muted:#9aa4b2; --line:#2a303a;
    --brand:#f2647a; --accent:#6fc0e6; --code-bg:#1f242c;
    --ok:#5fd39a; --ok-bg:#12291f; --warn:#e0b25f; --warn-bg:#2a2313; --danger:#f2647a; --danger-bg:#2a1518;
  }
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;
  line-height:1.65;font-size:16px}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
code{background:var(--code-bg);padding:.1em .4em;border-radius:4px;font-size:.88em;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace}

.top{display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;
  padding:.9rem 1.2rem;background:var(--surface);border-bottom:1px solid var(--line)}
.brand{font-weight:700;color:var(--brand);font-size:1.05rem}
.brand:hover{text-decoration:none}
.stack{color:var(--muted);font-size:.82rem}

nav.steps{position:sticky;top:0;z-index:10;display:flex;gap:.2rem;flex-wrap:wrap;
  padding:.5rem 1rem;background:var(--surface);border-bottom:1px solid var(--line)}
nav.steps a{padding:.3rem .7rem;border-radius:6px;color:var(--muted);font-size:.9rem;font-weight:500}
nav.steps a:hover{background:var(--code-bg);text-decoration:none}
nav.steps a.active{background:var(--brand);color:#fff}

main{max-width:860px;margin:0 auto;padding:1.5rem 1.2rem 3rem}
section{margin:2.2rem 0}
h1{font-size:1.8rem;line-height:1.25;margin:.2rem 0}
h2{font-size:1.25rem;margin:0 0 .8rem;padding-bottom:.35rem;border-bottom:2px solid var(--line)}
h3{font-size:1rem;margin:0 0 .4rem}
.lead,.sub{color:var(--muted)}

.hero{padding:1.6rem 0 .4rem}
.step0{display:inline-block;font-size:.8rem;font-weight:700;letter-spacing:.03em;
  color:var(--brand);background:var(--danger-bg);padding:.2rem .6rem;border-radius:999px}
.hero .sub{font-size:1.05rem;margin-top:.4rem}

.badge{font-size:.7rem;vertical-align:middle;padding:.15rem .5rem;border-radius:999px}
.badge.prio{background:var(--warn-bg);color:var(--warn);border:1px solid var(--warn)}

.ctx-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:1rem}
.ctx{background:var(--surface);border:1px solid var(--line);border-left:4px solid var(--line);
  border-radius:10px;padding:1rem}
.ctx p{margin:.3rem 0 0;color:var(--muted);font-size:.92rem}
.ctx.danger{border-left-color:var(--danger)}
.ctx.warn{border-left-color:var(--warn)}
.ctx.ok{border-left-color:var(--ok)}

.road-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:.9rem}
.road{display:flex;flex-direction:column;gap:.25rem;background:var(--surface);
  border:1px solid var(--line);border-radius:10px;padding:1rem;transition:transform .1s,border-color .1s}
.road:hover{text-decoration:none;transform:translateY(-2px);border-color:var(--accent)}
.rn{font-weight:700;color:var(--brand);font-size:.85rem}
.rt{font-weight:600;color:var(--ink)}
.rd{font-size:.78rem;color:var(--muted)}
.rg{font-size:.85rem;color:var(--muted);margin-top:.2rem}

.startnow ol{padding-left:0;list-style:none;counter-reset:s}
.startnow li{counter-increment:s;background:var(--surface);border:1px solid var(--line);
  border-radius:8px;padding:.7rem 1rem .7rem 2.6rem;margin:.5rem 0;position:relative}
.startnow li::before{content:counter(s);position:absolute;left:.8rem;top:.65rem;
  width:1.4rem;height:1.4rem;background:var(--brand);color:#fff;border-radius:50%;
  display:grid;place-items:center;font-size:.8rem;font-weight:700}

.meta-box{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:.4rem 1.1rem}
.meta-box p{margin:.6rem 0}
.meta-box strong{display:inline-block;min-width:5.5rem;color:var(--brand)}

ol.substeps{list-style:none;padding:0;counter-reset:d}
li.sub{background:var(--surface);border:1px solid var(--line);border-radius:10px;
  padding:1rem 1.1rem;margin:.8rem 0}
.sub-head{display:flex;align-items:baseline;gap:.6rem;flex-wrap:wrap}
.dsid{font-family:ui-monospace,monospace;font-size:.78rem;font-weight:700;color:#fff;
  background:var(--accent);padding:.15rem .5rem;border-radius:5px}
.sub-title{font-weight:600;font-size:1.02rem}
.ref{margin-left:auto;font-size:.78rem;color:var(--muted)}
ul.tasks{margin:.6rem 0 0;padding-left:1.2rem}
ul.tasks li{margin:.3rem 0}

.done{background:var(--ok-bg);border:1px solid var(--ok);border-radius:10px;padding:.6rem 1.2rem}
.done h2{border-color:color-mix(in srgb,var(--ok) 40%,transparent)}
ul.check{list-style:none;padding-left:1.6rem}
ul.check li{position:relative;margin:.4rem 0}
ul.check li::before{content:"✓";position:absolute;left:-1.6rem;color:var(--ok);font-weight:700}

nav.pager{display:flex;justify-content:space-between;gap:1rem;margin-top:2.5rem;
  padding-top:1.2rem;border-top:1px solid var(--line)}
nav.pager a{font-weight:600}

footer{max-width:860px;margin:0 auto;padding:1.5rem 1.2rem;color:var(--muted);font-size:.85rem;
  border-top:1px solid var(--line)}
footer p{margin:0}
"""


def main():
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "site.css").write_text(CSS, encoding="utf-8")
    (OUT / "index.html").write_text(render_index(), encoding="utf-8")
    for s in STEPS:
        (OUT / f"step-{s['num']}.html").write_text(render_step(s), encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"generated: index.html + step-1..8.html + assets/site.css ({len(STEPS)} steps)")


if __name__ == "__main__":
    main()
