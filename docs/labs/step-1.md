# Step 1 · API 스파이크 (접근성·스키마 확인)

<div class="chips"><span class="chip time">30분</span><span class="chip diff">쉬움</span><span class="chip goal">wisetoto API가 응답하는지 확인하고 실제 응답을 저장한다</span></div>

**코드를 쓰기 전에** wisetoto API(`bsrest.wisetoto.com`, 프로야구 LIVE 앱의 백엔드)가 내 환경에서 응답하는지, 응답이 계획서와 같은 모양인지 확인합니다. 여기서 막히면 이후 작업이 의미 없으므로 가장 먼저 합니다.

<div class="callout warn"><span class="t">HTTP 200이어도 실패일 수 있다 — <code>code</code>를 보라</span>
이 API는 오류도 HTTP <code>200</code>으로 주고, 본문의 <code>"code"</code>가 <code>"00"</code>일 때만 정상입니다. <code>"01"</code>(잘못된 접근)이 나오면 대부분 <strong>필수 쿼리 <code>os</code>·<code>version</code>·<code>lang</code> 중 하나가 빠졌거나</strong>(값은 아무거나 되지만 세 개 다 있어야 합니다), <strong>경로 대소문자</strong>(<code>Schedule_Day</code>는 되고 <code>schedule_day</code>는 404)나 <strong>날짜 형식</strong>(<code>20260913</code>은 되고 <code>2026-09-13</code>은 01)이 틀린 것입니다. curl로 그대로 됩니다 — TLS 핑거프린트 차단 같은 것은 없습니다(단 Python 기본 UA만 401).
</div>

## 1. 터미널에서 접근 확인

셸 함수 하나로 공통 쿼리를 붙입니다. 이후 명령은 전부 이 함수를 씁니다.

```bash
wt() { curl -sS "https://bsrest.wisetoto.com$1?os=a&version=4.1.3&lang=kr"; }

wt /live/Schedule_Day/$(date +%Y%m%d) | head -c 300 ; echo
```

<div class="checkpoint"><span class="t"></span> <code>{"result":"success","code":"00","message":"정상 출력","data":{"Vot_posible":"","Schedule_Day":[...]}}</code> 형태가 나오면 접근 성공. 오늘이 휴식일(월요일)이면 <code>Schedule_Day</code>가 빈 배열이어도 정상입니다 — 날짜를 어제로 바꿔 다시 확인하세요. <code>code:"01"</code>이면 위 callout의 세 가지를 점검합니다.</div>

## 2. 실기기에서도 되는지 확인

앱은 결국 휴대전화에서 돕니다. 이 API는 클라이언트를 가리지 않으므로(curl·OkHttp·브라우저 전부 200) 실기기에서 실패할 이유는 사실상 네트워크뿐입니다. **실기기 확정은 Step 3에서 만든 앱의 첫 호출**로 합니다(계획서 `DS-001`). 판정 기준은 HTTP 상태가 아니라 응답 봉투의 `code:"00"`입니다.

## 3. 핵심 엔드포인트 응답 저장

이후 Step에서 **테스트 fixture**로 쓸 실제 응답을 파일로 저장합니다. 날짜는 2026 시즌에서 성격이 다른 날을 골랐습니다 — 종료일, 우천 취소일, 예정일, 연장 11회 경기.

```bash
mkdir -p fixtures
wt() { curl -sS "https://bsrest.wisetoto.com$1?os=a&version=4.1.3&lang=kr"; }

wt /live/Schedule_Day/20260913   > fixtures/schedule_day_finished.json    # 4경기 전부 종료(e)
wt /live/Schedule_Day/20260409   > fixtures/schedule_day_canceled.json    # 5경기 우천 취소(c)
wt /live/Schedule_Day/20260915   > fixtures/schedule_day_scheduled.json   # 예정(a) — 지났으면 미래 날짜로 바꿀 것
wt /live/Schedule_Month/202609   > fixtures/schedule_month.json           # 9월 108경기
wt /live/Schedule_Month/202603   > fixtures/schedule_month_march.json     # 3월 — WBC·시범경기가 섞인 달 (필터 테스트용)
wt /live/schedule/490683         > fixtures/game_extra.json               # 09-10 NC 2:1 KIA, 연장 11회
wt /live/schedule/490691         > fixtures/game_final.json               # 09-13 한화 2:9 KIA, 9회말 미실시
wt "/rank/League_Rank?year=2026" > fixtures/league_rank.json             # 순위 10행
wt "/extra/Team_Info?team_info_seq=316" > fixtures/team_info.json         # 두산 구단 정보
# 경기일 18:30 이후에 한 번 더:
# wt /live/Schedule_Day/$(date +%Y%m%d) > fixtures/schedule_day_live.json  # 진행 중(i) — 없으면 아래 callout의 캡처 값을 참고

ls -la fixtures
```

<div class="callout tip"><span class="t">시즌은 <code>year</code>, 경기는 <code>seq</code></span>
SofaScore식 "시즌 ID"는 없습니다. 순위는 <code>year=2026</code>처럼 연도로 조회하고, 경기는 전 종목 공용 전역 ID <code>schedule_info_seq</code>로 조회합니다. seq는 날짜·팀으로 계산할 수 없으므로 <strong>항상 <code>Schedule_Day</code>/<code>Schedule_Month</code> 목록에서 받아옵니다</strong>. 2026 KBO는 462828~463500, 468584~468638(시범경기), 490672~(9월 8일 이후 재편성) 세 블록에 흩어져 있습니다.
</div>

## 4. 응답 구조 눈으로 확인

`jq`가 있으면:

```bash
jq '.data.Schedule_Day[0] | {seq, game_timestamp, state, inning, home_team_name, home_score, away_team_name, away_score, home_pitcher}' fixtures/schedule_day_finished.json
jq '.data.detail_info | {state, inning, home_score, away_score, boxscore}' fixtures/game_extra.json
jq '.data.rank[0]' fixtures/league_rank.json
```

다음을 직접 확인하세요(이후 매퍼가 이걸 처리합니다).

- `home_score`가 목록에서는 **문자열** `"9"`, 상세에서는 숫자 `9`인가
- 취소 경기(`state:"c"`)의 점수가 `null`인가 — 노게임은 부분 점수가 남아 있을 수 있음
- `boxscore.home_score`가 **항상 15칸**이고 미진행 이닝이 `null`(0이 아님)인가, 연장 경기는 10·11번째 칸에 값이 있는가
- `inning`이 `bs9_1`(9회초) 형식인가 — 홈팀이 이기면 9회말이 없어 `bs9_1`로 끝남
- 순위 행에 `draw_count`가 **직접** 있는가, `player_count`가 실제로는 경기 수인가
- 3월 목록(`schedule_month_march.json`)에 `한국 : 체코`(WBC)와 3/12~3/24 시범경기가 **KBO 정규 경기와 같은 배열에** 섞여 있는가 — 행에 리그 구분 필드가 없다

<div class="callout danger"><span class="t">라이브는 경기 날에만 확인 가능</span>
진행 중 경기의 <code>state</code>는 <code>i</code>입니다(2026-09-15 18:31 실측). 시작 직후 목록 행은 점수 <code>"0"</code>, <code>inning: "bs1_1"</code>, <code>detail</code>에 볼카운트·주자·현재 투수/타자가 채워지고, 상세의 <code>game_result</code>는 종료 전까지 <code>"1회초"</code> 같은 라벨입니다. <strong>경기일 18:30 이후</strong>에 아래로 직접 한 번 더 보고 <code>fixtures/schedule_day_live.json</code>으로 저장하세요(Step 3 테스트가 씁니다).
<br><br>
<code>watch -n 30 'wt /live/Schedule_Day/$(date +%Y%m%d) | jq ".data.Schedule_Day[] | {state, inning, home_score, away_score}"'</code>
</div>

<div class="checkpoint"><span class="t"></span> <code>fixtures/</code>에 9개 JSON(+ 경기일에 <code>schedule_day_live.json</code>)이 저장됐고, 위 6가지 구조를 눈으로 확인했으면 완료. 이 파일들은 Step 3에서 <code>app/src/test/resources/fixtures/</code>로 옮깁니다.</div>

<div class="pager">
<a href="#/labs/step-0">← Step 0</a>
<a href="#/labs/step-2">Step 2 · 부트스트랩 →</a>
</div>
