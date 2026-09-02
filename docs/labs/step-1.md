# Step 1 · API 스파이크 (접근성·스키마 확인)

<div class="chips"><span class="chip time">30분</span><span class="chip diff">쉬움</span><span class="chip goal">SofaScore가 응답하는지 확인하고 실제 응답을 저장한다</span></div>

**코드를 쓰기 전에** SofaScore가 내 환경에서 응답하는지, 응답이 계획서와 같은 모양인지 확인합니다. 여기서 막히면(예: 403) 이후 작업이 의미 없으므로 가장 먼저 합니다.

<div class="callout warn"><span class="t">curl은 403이 나옵니다 — 정상입니다</span>
SofaScore 엣지는 <strong>HTTP 클라이언트의 TLS 핑거프린트</strong>로 차단합니다. 같은 네트워크에서 curl·Python·Node·JDK <code>HttpClient</code>는 <code>403</code>, <strong>OkHttp와 Chrome은 <code>200</code></strong>입니다(<a href="#/IMPLEMENTATION_PLAN_KO">계획서</a> §13 A-3). 앱은 OkHttp를 쓰므로 영향이 없고, 터미널 확인도 OkHttp로 합니다. curl로 403을 보고 "막혔다"고 판단하지 마세요.
</div>

## 1. 터미널에서 접근 확인

KBO(`uniqueTournament.id = 11204`)의 시즌 목록을 받아 봅니다. 저장소의 `docs/labs/tools/sofa-fetch.sh`는
OkHttp 4 jar 3개를 Maven Central에서 한 번 내려받아(`~/.cache/diamondscore-tools/`) 단일 파일 Java로 호출하는
스크립트입니다. JDK 17 이상만 있으면 됩니다.

```bash
SOFA=docs/labs/tools/sofa-fetch.sh
$SOFA "https://api.sofascore.com/api/v1/unique-tournament/11204/seasons" | head -c 300 ; echo
```

<div class="checkpoint"><span class="t"></span> <code>{"seasons":[{"name":"KBO League 2026",...}]}</code> 형태가 나오면 접근 성공. 비교용으로 같은 URL을 <code>curl -s -o /dev/null -w "%{http_code}\n"</code>로 쳐 보면 <code>403</code>이 나옵니다 — 이게 위 callout의 핑거프린트 차단입니다. <strong>OkHttp에서도</strong> <code>403</code>이면 다른 네트워크(모바일 핫스팟 등)로 바꿔 다시 시도하고, 그래도 안 되면 <a href="#/IMPLEMENTATION_PLAN_KO">계획서</a> §1.2의 보조 소스로 방향을 바꿉니다.</div>

## 2. 실기기에서도 되는지 확인

앱은 결국 휴대전화에서 돕니다. 위 스크립트는 데스크톱 JVM의 OkHttp이고, Android의 OkHttp는 TLS 구현(Conscrypt)이
달라 핑거프린트도 다릅니다. SofaScore 공식 앱이 같은 스택이라 될 가능성이 높지만, **실기기 확정은 Step 3에서
만든 앱의 첫 호출**로 합니다(계획서 `DS-001`). `adb shell curl`은 쓰지 마세요 — 기기에 curl이 없고, 있어도 위와
같은 이유로 403이 나와 판단을 흐립니다. 지금은 "내 네트워크에서 OkHttp로 된다"까지만 확인하면 충분합니다.

## 3. 핵심 엔드포인트 4개 응답 저장

이후 Step에서 **테스트 fixture**로 쓸 실제 응답을 파일로 저장합니다.

```bash
mkdir -p fixtures
BASE="https://api.sofascore.com/api/v1"
SOFA=docs/labs/tools/sofa-fetch.sh

$SOFA "$BASE/unique-tournament/11204/seasons" > fixtures/seasons.json
$SOFA "$BASE/unique-tournament/11204/season/88022/standings/total" > fixtures/standings.json
$SOFA "$BASE/unique-tournament/11204/season/88022/events/next/0" > fixtures/events_next.json
$SOFA "$BASE/unique-tournament/11204/season/88022/events/last/0" > fixtures/events_last.json

ls -la fixtures
```

<div class="callout tip"><span class="t">seasonId는 매년 바뀐다</span>
2026 시즌은 <code>88022</code>입니다. <code>fixtures/seasons.json</code>을 열어 첫 항목의 <code>id</code>가 88022인지 확인하세요. 앱에서는 이 값을 하드코딩하지 않고 <code>/seasons</code> 첫 항목을 씁니다.
</div>

## 4. 응답 구조 눈으로 확인

한 경기의 점수 구조를 봅니다. `jq`가 있으면:

```bash
jq '.events[0] | {id, startTimestamp, status, homeTeam:.homeTeam.name, awayTeam:.awayTeam.name, homeScore}' fixtures/events_last.json
```

다음을 직접 확인하세요(이후 매퍼가 이걸 처리합니다).

- `status.type` 이 `notstarted` / `finished` 중 하나인가
- `homeScore.innings` 가 `{"inning1":{"run":1}, ...}` 형태의 **맵**인가 (배열 아님)
- standings row에 `draws`가 **없고** `matches / wins / losses`만 있는가

<div class="callout danger"><span class="t">라이브는 경기 날에만 확인 가능</span>
<code>/sport/baseball/events/live</code>는 경기가 없을 때 <code>{"events":[]}</code>를 반환합니다. 라이브 응답의 정확한 모양(진행 이닝 표현 등)은 <strong>실제 경기일 저녁</strong>에 아래로 한 번 더 확인하세요.
<br><br>
<code>watch -n 30 'docs/labs/tools/sofa-fetch.sh "https://api.sofascore.com/api/v1/sport/baseball/events/live" | jq ".events | length"'</code>
</div>

<div class="checkpoint"><span class="t"></span> <code>fixtures/</code>에 4개 JSON이 저장됐고, 위 3가지 구조를 눈으로 확인했으면 완료. 이 파일들은 Step 3에서 <code>app/src/test/resources/fixtures/</code>로 옮깁니다.</div>

<div class="pager">
<a href="#/labs/step-0">← Step 0</a>
<a href="#/labs/step-2">Step 2 · 부트스트랩 →</a>
</div>
