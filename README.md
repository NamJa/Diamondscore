# DiamondScore

KBO 실시간 경기, 선수, 팀, 순위 정보를 제공하는 Jetpack Compose Android 앱 프로젝트입니다.

제품 요구사항과 구현 계획을 하나의 문서로 통합해 두었습니다.

- **Codelabs 튜토리얼** (`docs/`) — 앱을 처음부터 따라 만드는 단계별 문서(Step 0~9). docsify 기반 GitHub Pages 사이트. 아래 [배포](#github-pages-배포) 참고
- [구현 계획](./docs/IMPLEMENTATION_PLAN_KO.md) — 단일 계획서(설계 배경·데이터 계약·리스크). Codelabs가 참조하는 원본

## 기술 스택 (2026-09-02 실측 기준)

Kotlin 2.4.10 · Jetpack Compose (Material 3) · 클린 아키텍처(단일 `:app` + 패키지 경계, 승격 시 `:domain`은 순수 Kotlin).

- **빌드**: AGP 9.4.0, Gradle 9.7.1, JDK 17. AGP 9는 **Kotlin 내장** — `kotlin.android` 플러그인을 적용하지 않습니다
- **어노테이션 처리**: KSP2 **2.3.11** (kapt 미사용) — Room · Hilt. KSP는 2.3.0부터 Kotlin 접두사 없는 독립 버전제
- **Compose**: BOM `2026.08.00`, 컴파일러는 `org.jetbrains.kotlin.plugin.compose` (Kotlin 동봉, 별도 pin 없음)
- **탐색**: **Navigation 3 `1.1.7`** — `NavDisplay` + 타입 있는 `NavKey`. Nav2(`navigation-compose`)는 쓰지 않습니다
- **네트워크**: Retrofit 3.0.0 + OkHttp 5.5.0 + kotlinx.serialization 1.11.0
- **이미지**: Coil 3.6.1 (`coil-compose` + `coil-network-okhttp`, OkHttp 인스턴스 공유)
- **로컬**: Room 2.8.4 (읽기 SSOT) + DataStore · **DI**: Hilt 2.60.1
- **SDK**: `compileSdk`/`targetSdk` 36, `minSdk` 26 · **릴리스**: R8 full mode

전체 버전표와 서로 묶인 조합(Gradle ≥ 9.6 / KSP 2.3.x / Hilt ≥ 2.60)은 [구현 계획 §5.4](./docs/IMPLEMENTATION_PLAN_KO.md)에 있습니다.

## 아키텍처 경계

규칙 4개로 유지합니다 (상세 [§5.1](./docs/IMPLEMENTATION_PLAN_KO.md)):

1. `feature`·`core/ui`·`core/designsystem`은 `data`를 참조하지 않는다 (ViewModel은 Repository만 주입받는다)
2. DTO와 Room `Entity`는 `data` 밖으로 나가지 않는다 — 경계를 넘는 타입은 `domain/model`뿐
3. `core/designsystem`은 도메인을 모른다 (도메인을 아는 공용 컴포넌트는 `core/ui`)
4. `data`는 Compose를 모른다 (그래서 한글 팀명은 `core/common`, 팀 컬러는 `core/designsystem`)

화면끼리는 서로를 모릅니다 — 이동은 `(Long) -> Unit` 콜백으로 올려 `DiamondScoreApp.kt`가 `NavKey`로 바꿉니다.

## 데이터 소스

SofaScore API (`api.sofascore.com/api/v1`), KBO `uniqueTournament.id = 11204`, 2026 `seasonId = 88022`.

2026-08-02 실측 기준으로 일정·이닝별 득점·경기 상태·순위·팀/구장/감독 정보를 제공합니다. 단 **KBO는 `hasEventPlayerStatistics: false`이며 `incidents`/`lineups`/`statistics` 엔드포인트가 모두 404**이므로, 볼카운트·주자·투수/타자·라인업·박스스코어·선수 기록은 제공되지 않습니다. MVP 범위는 이 커버리지에 맞춰 확정했습니다 — 근거는 구현 계획 §2.3 참고.

## GitHub Pages 배포

Codelabs 튜토리얼은 `docs/` 폴더에 [docsify](https://docsify.js.org) SPA로 들어 있습니다.

1. GitHub 저장소 → **Settings → Pages**
2. **Source**: `Deploy from a branch`, **Branch**: `main` / 폴더 `/docs` 선택 → Save
3. 몇 분 뒤 `https://namja.github.io/Diamondscore/` 에서 소개 페이지가 열립니다

- 파일 구성: `docs/index.html`(docsify 부트스트랩) · `docs/README.md`(홈) · `docs/_sidebar.md`(네비) · `docs/labs/step-0~9.md`(코드랩) · `docs/assets/codelab.css`
- 콘텐츠 수정은 해당 `labs/step-N.md`를 직접 편집하면 됩니다(빌드 단계 없음 — docsify가 런타임 렌더)
- `.nojekyll`로 Jekyll을 끕니다 (docsify는 `_sidebar.md` 등 언더스코어 파일을 씀)
- docsify·Prism은 jsDelivr CDN에서 로드하므로 인터넷 연결이 필요합니다

로컬 미리보기: `python3 -m http.server -d docs 8000` → `http://localhost:8000`
