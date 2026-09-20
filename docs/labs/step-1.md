# Step 1 · API 스파이크 (접근성·스키마 확인)

<div class="chips"><span class="chip time">30분</span><span class="chip diff">쉬움</span><span class="chip goal">wisetoto API가 응답하는지 확인하고 실제 응답을 저장한다</span></div>

**코드를 쓰기 전에** wisetoto API(`bsrest.wisetoto.com`, 프로야구 LIVE 앱의 백엔드)가 내 환경에서 응답하는지, 응답이 계획서와 같은 모양인지 확인합니다. 여기서 막히면 이후 작업이 의미 없으므로 가장 먼저 합니다.

<div class="callout warn"><span class="t">HTTP 200이어도 실패일 수 있다 — <code>code</code>를 보라</span>
이 API는 오류도 HTTP <code>200</code>으로 주고, 본문의 <code>"code"</code>가 <code>"00"</code>일 때만 정상입니다. <code>"01"</code>(잘못된 접근)이 나오면 대부분 <strong>필수 쿼리 <code>os</code>·<code>version</code>·<code>lang</code> 중 하나가 빠졌거나</strong>(값은 아무거나 되지만 세 개 다 있어야 합니다), <strong>경로 대소문자</strong>(<code>Schedule_Day</code>는 되고 <code>schedule_day</code>는 404)나 <strong>날짜 형식</strong>(<code>20260913</code>은 되고 <code>2026-09-13</code>은 01)이 틀린 것입니다. curl로 그대로 됩니다 — TLS 핑거프린트 차단 같은 것은 없습니다(단 Python 기본 UA만 401).
</div>

## 1. 터미널에서 접근 확인

셸 함수 하나로 공통 쿼리를 붙입니다. 이후 명령은 전부 이 함수를 씁니다. **경로에 `?`를 직접 붙이지 말고 두 번째 인자로 넘기세요** — 경로 뒤에 `?`를 또 쓰면 `os`가 쿼리 키로 인식되지 않아 전부 `code "01"`이 됩니다.

```bash
# $1 = 경로, $2 = 추가 쿼리(선택)
wt() { curl -sS "https://bsrest.wisetoto.com$1?os=a&version=4.1.3&lang=kr${2:+&$2}"; }

wt /live/Schedule_Day/$(date +%Y%m%d) | head -c 300 ; echo
wt /rank/League_Rank "year=2026"      | head -c 120 ; echo   # 추가 쿼리는 이렇게
```

<div class="checkpoint"><span class="t"></span> <code>{"result":"success","code":"00","message":"정상 출력","data":{"Vot_posible":"","Schedule_Day":[...]}}</code> 형태가 나오면 접근 성공. 오늘이 휴식일(월요일)이면 <code>Schedule_Day</code>가 빈 배열이어도 정상입니다 — 날짜를 어제로 바꿔 다시 확인하세요. <code>code:"01"</code>이면 위 callout의 세 가지를 점검합니다.</div>

## 2. 실기기에서도 되는지 확인

앱은 결국 휴대전화에서 돕니다. 이 API는 클라이언트를 가리지 않으므로(curl·OkHttp·브라우저 전부 200) 실기기에서 실패할 이유는 사실상 네트워크뿐입니다. **실기기 확정은 Step 3에서 만든 앱의 첫 호출**로 합니다(계획서 `DS-001`). 판정 기준은 HTTP 상태가 아니라 응답 봉투의 `code:"00"`입니다.

## 3. 핵심 엔드포인트 응답 저장

이후 Step에서 **테스트 fixture**로 쓸 실제 응답을 파일로 저장합니다. 날짜는 2026 시즌에서 성격이 다른 날을 골랐습니다 — 종료일, 우천 취소일, 연장 11회 경기. 예정 경기만은 고정 날짜가 아니라 **오늘** 목록에서 받습니다(바로 아래 이유). 팀·선수는 **두산 베어스(316)** 기준입니다(목업과 같은 팀).

```bash
mkdir -p fixtures
wt() { curl -sS "https://bsrest.wisetoto.com$1?os=a&version=4.1.3&lang=kr${2:+&$2}"; }

# ── 경기 ──
wt /live/Schedule_Day/20260913 > fixtures/schedule_day_finished.json   # 4경기 전부 종료(e)
wt /live/Schedule_Day/20260409 > fixtures/schedule_day_canceled.json   # 5경기 우천 취소(c)
wt /live/Schedule_Day/$(date +%Y%m%d) > fixtures/schedule_day_scheduled.json  # 예정(a) — 오늘, 첫 경기 시작 전에
wt /live/Schedule_Month/202609 > fixtures/schedule_month.json          # 9월 — 구장명 표기 흔들림 확인용
wt /live/Schedule_Month/202603 > fixtures/schedule_month_march.json    # 3월 — WBC·시범경기가 섞인 달
wt /live/schedule/490683       > fixtures/game_extra.json              # 09-10 NC 2:1 KIA, 연장 11회
wt /live/schedule/490691       > fixtures/game_final.json              # 09-13 한화 2:9 KIA, 9회말 미실시

# ── 순위 ──
wt /rank/League_Rank "year=2026" > fixtures/league_rank.json           # 순위 10행

# ── 팀 선수단 — 한 번에 안 옵니다. player_position으로 두 번 부릅니다 ──
wt /extra/Team_Info "team_info_seq=316&player_position=0" > fixtures/team_info_pitchers.json  # 두산 투수 43명
wt /extra/Team_Info "team_info_seq=316&player_position=1" > fixtures/team_info_batters.json   # 두산 타자 47명

# ── 선수 상세 — 타자와 투수는 record 스키마가 다릅니다 ──
wt /extra/Player_Info/938464 > fixtures/player_batter.json    # 양의지(포수 25번) — 타자 스키마
wt /extra/Player_Info/923961 > fixtures/player_pitcher.json   # 곽빈(투수 47번)  — 투수 스키마 + null 행 포함

# 경기 진행 중에 한 번 더:
# wt /live/Schedule_Day/$(date +%Y%m%d) > fixtures/schedule_day_live.json  # 진행 중(i)

ls -la fixtures
```

<div class="callout warn"><span class="t">예정 fixture는 <strong>오늘</strong>, 첫 경기 시작 전에 받는다</span>
고정 날짜를 적어 두면 그 날이 지나는 순간 <code>state</code>가 <code>e</code>로 바뀌어 파일 이름과 내용이 어긋납니다. 그렇다고 미래 날짜도 안 됩니다 — 이틀 뒤 목록은 <code>state:"a"</code>이지만 <code>home_pitcher</code>·<code>away_pitcher</code>가 전부 <code>null</code>입니다(실측). <strong>선발투수는 경기 당일 목록에만 채워집니다.</strong> Step 3의 <code>예정 경기는 선발투수가 있고 점수는 null</code> 테스트가 둘 다 보므로 오늘 첫 경기 시작 전(평일 18:30, 주말 14:00)에 받으세요. 부득이 미래 날짜로 받았다면 선발이 <code>null</code>이므로 Step 3에서 <code>assertNotNull(g.homeStarter)</code> 단언을 지워야 합니다. 월요일 휴식일과 시즌(3~11월) 밖에는 <code>Schedule_Day</code>가 빈 배열이라 다른 날에 받아야 합니다.
</div>

<div class="callout danger"><span class="t">선수단은 두 번 불러야 다 온다</span>
<code>Team_Info</code>를 <code>team_info_seq</code>만으로 부르면 <strong>투수만</strong> 돌아옵니다(두산 43명). <code>player_position=1</code>을 붙여야 타자 47명이 옵니다 — <code>0</code>이 투수, <code>0이 아닌 값</code>은 전부 타자입니다. 그래서 선수단 화면은 요청이 <strong>2회</strong>입니다. 그리고 목록에는 <code>seq</code>·<code>name</code>·<code>c_number</code>·<code>img</code> 넷뿐입니다 — <strong>포수·내야수·외야수 구분은 목록에 없고 선수 상세에만 있습니다</strong>. 포지션별로 묶으려면 90명을 각각 조회해야 하므로, 이 앱은 투수/타자 2단으로만 나눕니다.
</div>

<div class="callout tip"><span class="t">시즌은 <code>year</code>, 경기는 <code>seq</code></span>
SofaScore식 "시즌 ID"는 없습니다. 순위는 <code>year=2026</code>처럼 연도로 조회하고, 경기는 전 종목 공용 전역 ID <code>schedule_info_seq</code>로 조회합니다. seq는 날짜·팀으로 계산할 수 없으므로 <strong>항상 <code>Schedule_Day</code>/<code>Schedule_Month</code> 목록에서 받아옵니다</strong>. 2026 KBO는 462828~463500, 468584~468638(시범경기), 490672~(9월 8일 이후 재편성) 세 블록에 흩어져 있습니다.
</div>

## 4. 응답 구조 눈으로 확인

`jq`가 있으면:

```bash
jq '.data.Schedule_Day[0] | {seq, game_timestamp, state, inning, home_team_name, home_score, away_team_name, away_score, home_pitcher}' fixtures/schedule_day_finished.json
jq '.data.detail_info | {state, inning, home_score, away_score, boxscore}' fixtures/game_extra.json
jq '.data.rank[0]' fixtures/league_rank.json

# 팀 — 구단 정보 + 선수단
jq '.data.team_info.team_detail | {name, en_simple_name, stadium_name, director, team_history}' fixtures/team_info_pitchers.json
jq '.data.team_info.player_list | length, .[0]' fixtures/team_info_pitchers.json

# 선수 — 타자와 투수의 record 키를 나란히 본다
jq '.data.player_info | {pos: .player_detail.c_position, month: .record.month[-1], last: .record.previous5[0]}' fixtures/player_batter.json
jq '.data.player_info | {pos: .player_detail.c_position, month: .record.month[-1], last: .record.previous5[-1]}' fixtures/player_pitcher.json
```

다음을 직접 확인하세요(이후 매퍼가 이걸 처리합니다).

**경기·순위**

- `home_score`가 목록에서는 **문자열** `"9"`, 상세에서는 숫자 `9`인가
- 취소 경기(`state:"c"`)의 점수가 `null`인가 — 노게임은 부분 점수가 남아 있을 수 있음
- `boxscore.home_score`가 **항상 15칸**이고 미진행 이닝이 `null`(0이 아님)인가, 연장 경기는 10·11번째 칸에 값이 있는가
- `inning`이 `bs9_1`(9회초) 형식인가 — 홈팀이 이기면 9회말이 없어 `bs9_1`로 끝남
- 순위 행에 `draw_count`가 **직접** 있는가, `player_count`가 실제로는 경기 수인가
- 3월 목록(`schedule_month_march.json`)에 `한국 : 체코`(WBC)와 3/12~3/24 시범경기가 **KBO 정규 경기와 같은 배열에** 섞여 있는가 — 행에 리그 구분 필드가 없다
- 9월 목록에 같은 구장이 `서울 잠실야구장`과 `서울잠실야구장` **두 표기로** 들어 있는가 — 한 달 안에서도 흔들립니다
  (`jq -r '.data.Schedule_Month[].stadium_name' fixtures/schedule_month.json | sort -u`)
- 월별 목록 행에 `game_timestamp`도, `home_pitcher`도 **없는가** — 시각은 문자열 파싱, 선발은 당일 목록에서만

**팀·선수**

- `team_history`의 구분자가 파이프(`|`)가 아니라 **소문자 `l`** 인가 — `"1982년 l \"OB 베어스\" 창단"`
- 투수 파일과 타자 파일의 `player_list` 길이가 다른가(두산 43 / 47), 두 파일 모두 키가 `seq`·`name`·`c_number`·`img` **넷뿐**인가
- `c_number`가 문자열이라 정렬하면 `1, 10, 101, 104, 11 …`로 섞이는가
  (`jq -r '.data.team_info.player_list[].c_number' fixtures/team_info_pitchers.json | sort | head`)
- **등번호가 겹치는가** — 두산 투수 48번이 벤자민·김영현 둘입니다. 등번호는 키가 될 수 없습니다
  (`jq -r '.data.team_info.player_list[].c_number' fixtures/team_info_pitchers.json | sort | uniq -d`)
- 타자(`player_batter.json`)의 `record.month[]`는 `avg`·`ab`·`h`·`hr`·`rbi`, 투수(`player_pitcher.json`)는 `era`·`win`·`lose`·`inning`·`so` — **키가 아예 다른가**
- 두 파일 모두 `record.month`의 마지막 원소가 `"month": "13"` 인가 — 13월이 아니라 **시즌 합계**입니다
- 투수의 월별 `inning`은 `"29 2/3"`(대분수 문자열)인데 `previous5`의 `ip`는 `"0.2"`·`"7.0"`인가 — **`0.2`는 0.2이닝이 아니라 ⅔이닝**입니다
- `previous5`의 `era`/`avg`가 과거로 갈수록 값이 바뀌는가 — 그 경기 성적이 아니라 **그 시점 누적값**입니다
- `player_pitcher.json`의 `previous5` 마지막 행(8/22 롯데)이 `game_date`·`matchteamname`만 있고 **나머지 전부 `null`** 인가
- `img_s`·`player_photo`가 `http://`로 오는가 — 그대로 쓰면 Android 기본 설정에서 차단됩니다(`https`로 바꿔 실음)

<div class="callout danger"><span class="t">라이브는 경기 날에만 확인 가능</span>
진행 중 경기의 <code>state</code>는 <code>i</code>입니다(2026-09-15 18:31 실측). 시작 직후 목록 행은 점수 <code>"0"</code>, <code>inning: "bs1_1"</code>, <code>detail</code>에 볼카운트·주자·현재 투수/타자가 채워지고, 상세의 <code>game_result</code>는 종료 전까지 <code>"1회초"</code> 같은 라벨입니다. <strong>경기가 진행 중일 때</strong> 아래로 직접 한 번 더 보고 <code>fixtures/schedule_day_live.json</code>으로 저장하세요 — Step 3의 라이브 매핑 테스트가 이 파일을 쓰는데, 이닝 라벨이 <code>"N회초"</code>·<code>"N회말"</code> 형태인지만 정규식으로 보므로 <strong>몇 회에 캡처했는지는 상관없습니다</strong>. 진행 중(<code>state:"i"</code>) 행이 하나라도 들어 있기만 하면 됩니다. 경기 시간이 아니라면 이 파일 없이 진행하고 경기일에 다시 저장·재실행하세요.
<br><br>
<code>watch -n 30 'wt /live/Schedule_Day/$(date +%Y%m%d) | jq ".data.Schedule_Day[] | {state, inning, home_score, away_score}"'</code>
</div>

<div class="checkpoint"><span class="t"></span> <code>fixtures/</code>에 <strong>12개 JSON</strong>(+ 경기일에 <code>schedule_day_live.json</code>)이 저장됐고, 위 목록을 눈으로 확인했으면 완료. 파일 이름은 Step 3의 <code>MapperTest</code>가 <code>load("…")</code>로 그대로 부르므로 바꾸지 마세요(<code>schedule_month.json</code>만 예외 — 위 구장명 <code>jq</code> 확인용입니다). 라이브 파일은 경기 시간에만 받을 수 있는 13번째 파일이라, 없으면 Step 3에서 라이브 매핑 테스트 하나만 경기일로 미루면 됩니다. 이 파일들은 Step 3에서 <code>app/src/test/resources/fixtures/</code>로 옮깁니다.</div>

<div class="pager">
<a href="#/labs/step-0">← Step 0</a>
<a href="#/labs/step-2">Step 2 · 부트스트랩 →</a>
</div>
