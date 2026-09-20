<!-- docsify 홈 -->

# DiamondScore Codelabs 🥎

> KBO 실시간 Android 앱을 **처음부터 끝까지 따라 만드는** 단계별 튜토리얼.
> 명령어·코드·확인 방법을 그대로 적어 두었으니, 순서대로 복사·실행하면 동작하는 앱이 됩니다.

**만드는 것**: 오늘 경기 목록 · 라이브 스코어 · 이닝별 라인스코어 · 리그 순위 · 팀 상세 · **팀 선수단·연혁** · **선수 상세(타자/투수)** · 즐겨찾기.
**스택**: Kotlin 2.4 · AGP 9.4 · Jetpack Compose · **Navigation 3** · Retrofit 3 · Coil 3 · Room · Hilt · KSP2.
**데이터**: wisetoto API(`bsrest.wisetoto.com`, 프로야구 LIVE 앱 백엔드 · 개인 용도, 백엔드 없음).
**디자인**: **브로드캐스트 × 에디토리얼** 하이브리드(다크 기본 + 라이트) · Bebas Neue + Archivo/Noto Sans KR · 10개 구단 컬러. 라이브는 초대형 스코어로 강렬하게, 목록·표는 라인·여백으로 절제. 각 화면은 확정된 목업을 그대로 구현합니다 — Step 5에서 공통 컴포넌트를 먼저 만들고, Step 6~8에서 조립합니다.

<div id="lab-progress"></div>

## 이 튜토리얼을 따라가는 법

1. **위에서부터 순서대로** 진행하세요. 각 Step은 이전 Step의 결과물 위에 쌓입니다.
2. 각 Step 안의 `## 1`, `## 2` … 는 **작은 단계**입니다. 코드 블록은 그대로 복사해 넣으세요.
3. 각 Step 끝(일부 Step은 중간에도) 나오는 **✅ 체크포인트**로 제대로 됐는지 확인한 뒤 다음으로 넘어갑니다.
4. 페이지 맨 아래 **"이 단계 완료로 표시"** 버튼을 누르면 위 진행률에 반영됩니다(브라우저에 저장).

<div class="callout danger">
<span class="t">먼저 알아둘 데이터 특성</span>
wisetoto API는 <strong>날짜별 일정·이닝별 득점·R/H/E·순위·구단 정보·선수단·선수 기록</strong>에 더해 볼카운트·주자·라인업·문자중계까지 줍니다.
이 튜토리얼은 그중 <strong>득점 + 팀·선수 정보</strong>까지 완성합니다. 볼카운트·문자중계·라인업은 경기일에만 검증할 수 있어 다음 단계로 미룹니다(계획서 §1.2).
응답은 HTTP 200에 오류 코드가 실려 오고, 수치가 문자열이며, 경로가 대소문자를 구분하고, <strong>같은 라우트가 선수 포지션에 따라 다른 스키마를 줍니다.</strong> Step 1·3에서 이 <strong>함정 12개</strong>를 테스트로 고정합니다.
</div>

## 코드랩 목록

<div class="lab-cards">
<a href="#/labs/step-0"><span class="n">Step 0</span><span class="h">개발 환경 준비</span><span class="d">⏱ 30분 · Android Studio·JDK·SDK·기기</span></a>
<a href="#/labs/step-1"><span class="n">Step 1</span><span class="h">API 스파이크</span><span class="d">⏱ 30분 · 접근 확인·응답 저장</span></a>
<a href="#/labs/step-2"><span class="n">Step 2</span><span class="h">부트스트랩 & 디자인 시스템</span><span class="d">⏱ 60분 · 의존성·다크 테마·구단 컬러</span></a>
<a href="#/labs/step-3"><span class="n">Step 3</span><span class="h">네트워크·매핑</span><span class="d">⏱ 110분 · DTO·Retrofit·매퍼·함정 12개 테스트</span></a>
<a href="#/labs/step-4"><span class="n">Step 4</span><span class="h">Room·프리페치</span><span class="d">⏱ 2시간 · DB·Repository·Worker</span></a>
<a href="#/labs/step-5"><span class="n">Step 5</span><span class="h">공통 컴포넌트</span><span class="d">⏱ 2시간 · 카드·라인스코어·상태 화면 + Preview</span></a>
<a href="#/labs/step-6"><span class="n">Step 6</span><span class="h">경기 목록</span><span class="d">⏱ 90분 · 날짜 네비·라이브 폴링</span></a>
<a href="#/labs/step-7"><span class="n">Step 7</span><span class="h">경기 상세</span><span class="d">⏱ 80분 · 스코어보드·라인스코어</span></a>
<a href="#/labs/step-8"><span class="n">Step 8</span><span class="h">순위·팀·선수·즐겨찾기</span><span class="d">⏱ 2시간 30분 · 순위표·팀 상세·선수단·선수 상세</span></a>
<a href="#/labs/step-9"><span class="n">Step 9</span><span class="h">마감·릴리스</span><span class="d">⏱ 90분 · 탭 연결·설정·적응형·성능·R8</span></a>
</div>

<div class="callout tip">
<span class="t">전체 그림이 궁금하면</span>
설계 배경·데이터 계약·리스크는 <a href="#/IMPLEMENTATION_PLAN_KO">전체 계획서</a>에 있습니다.
이 Codelabs는 그 계획을 "손으로 따라 하는 순서"로 풀어 쓴 것입니다.
</div>

---
<sub>개인/포트폴리오 용도. wisetoto 이용약관(사전 승낙 없는 복제·유통·상업적 이용 금지)을 존중해 개인 사용에 한정하고, 폴링은 공식 앱보다 느리게 유지하며, 로고·선수 이미지는 재배포하지 않습니다.</sub>
