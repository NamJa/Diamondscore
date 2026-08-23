# DiamondScore

KBO 실시간 경기, 선수, 팀, 순위 정보를 제공하는 Jetpack Compose Android 앱 프로젝트입니다.

제품 요구사항과 구현 계획을 하나의 문서로 통합해 두었습니다.

- [구현 계획](./docs/IMPLEMENTATION_PLAN_KO.md) — **단일 구현 계획** (개인 용도 · 백엔드 없음 · SofaScore 직접 호출). Step 1~8, 부록에 APK 추가 발견·공개배포 확장 정리
- **Step-by-Step 사이트** (`docs/index.html` ~ `step-8.html`) — 계획을 GitHub Pages용 HTML/CSS로 렌더링. 아래 [배포](#github-pages-배포) 참고

## 기술 스택 (2026-08-23 기준)

Kotlin 2.4 · Jetpack Compose (Material 3) · 클린 아키텍처(멀티모듈, `:domain`은 순수 Kotlin).

- **빌드**: AGP 9.2.x, Gradle 9.4.1, JDK 17 toolchain, version catalog (동적 버전 금지)
- **어노테이션 처리**: KSP2 (kapt 미사용) — Room · Hilt
- **Compose 컴파일러**: `org.jetbrains.kotlin.plugin.compose` (Kotlin 동봉, 별도 버전 pin 없음)
- **네트워크**: Retrofit 3 + OkHttp + kotlinx.serialization
- **이미지**: Coil 3 (`coil-compose` + `coil-network-okhttp`, OkHttp 인스턴스 공유)
- **로컬**: Room (읽기 SSOT) + DataStore · **DI**: Hilt · **탐색**: Navigation 3
- **SDK**: `compileSdk`/`targetSdk` 36, `minSdk` 26 · **릴리스**: R8 full mode

정확한 버전 숫자는 [구현 계획 §4.4](./docs/IMPLEMENTATION_PLAN_KO.md)의 표를 따르며, 최초 sync에서 확정합니다.

## 데이터 소스

SofaScore API (`api.sofascore.com/api/v1`), KBO `uniqueTournament.id = 11204`, 2026 `seasonId = 88022`.

2026-08-02 실측 기준으로 일정·이닝별 득점·경기 상태·순위·팀/구장/감독 정보를 제공합니다. 단 **KBO는 `hasEventPlayerStatistics: false`이며 `incidents`/`lineups`/`statistics` 엔드포인트가 모두 404**이므로, 볼카운트·주자·투수/타자·라인업·박스스코어·선수 기록은 제공되지 않습니다. MVP 범위는 이 커버리지에 맞춰 확정했습니다 — 근거는 구현 계획 §2.3 참고.

## GitHub Pages 배포

Step-by-Step 사이트는 `docs/` 폴더에 정적 HTML/CSS로 들어 있습니다.

1. GitHub 저장소 → **Settings → Pages**
2. **Source**: `Deploy from a branch`, **Branch**: `main` / 폴더 `/docs` 선택 → Save
3. 몇 분 뒤 `https://<사용자>.github.io/<저장소>/` 에서 개요 페이지가 열립니다

- 파일 구성: `docs/index.html`(개요) + `docs/step-1.html` ~ `step-8.html` + `docs/assets/site.css`
- 콘텐츠 수정은 `docs/build_site.py`의 데이터를 고친 뒤 `python3 docs/build_site.py`로 재생성합니다 (HTML을 직접 편집하지 않음)
- `.nojekyll`로 Jekyll 처리를 끕니다 (순수 정적 사이트)
