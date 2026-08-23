# Step 2 · 프로젝트 부트스트랩 & 디자인 시스템

<div class="chips"><span class="chip time">60분</span><span class="chip diff">쉬움</span><span class="chip goal">프로젝트·의존성 + 목업의 다크 테마·구단 컬러를 코드로 옮긴다</span></div>

실제 프로젝트를 만들고 Kotlin 2.4 / Compose / Retrofit 3 / Room / Hilt / Coil 3를 version catalog로 고정한 뒤, **확정된 목업의 디자인 토큰**(다크 팔레트·타이포·구단 컬러)을 Material 3 테마로 심습니다. 이후 모든 화면이 이 토큰을 씁니다.

## 1. 새 프로젝트 생성

Android Studio → **New Project → Empty Activity (Compose)**.

| 항목 | 값 |
|---|---|
| Name | `DiamondScore` |
| Package name | `com.diamondscore` |
| Minimum SDK | **API 26** |
| Build configuration language | **Kotlin DSL** |

Finish 후 상단에서 **Sync**가 끝날 때까지 기다립니다.

## 2. 컴파일 SDK와 옵션 (`app/build.gradle.kts`)

`android { }` 블록을 아래처럼 맞춥니다.

```kotlin
android {
    namespace = "com.diamondscore"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.diamondscore"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    buildFeatures { compose = true }
    kotlin { jvmToolchain(17) }

    buildTypes {
        release {
            isMinifyEnabled = true          // R8 full mode
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
}
```

## 3. version catalog (`gradle/libs.versions.toml`)

버전을 한곳에 고정합니다. **동적 버전(`+`)은 쓰지 않습니다.**

```toml
[versions]
kotlin = "2.4.0"
agp = "9.2.0"
ksp = "2.4.0-2.0.0"
composeBom = "2026.06.00"
hilt = "2.57"
androidxHilt = "1.4.0"
room = "2.8.4"
retrofit = "3.0.0"
okhttp = "5.0.0"
serialization = "1.9.0"
coil = "3.3.0"
nav3 = "1.0.1"
lifecycle = "2.10.0"
work = "2.11.2"

[libraries]
androidx-core-ktx = { module = "androidx.core:core-ktx", version = "1.17.0" }
androidx-lifecycle-runtime-compose = { module = "androidx.lifecycle:lifecycle-runtime-compose", version.ref = "lifecycle" }
androidx-lifecycle-viewmodel-compose = { module = "androidx.lifecycle:lifecycle-viewmodel-compose", version.ref = "lifecycle" }
compose-bom = { module = "androidx.compose:compose-bom", version.ref = "composeBom" }
compose-ui = { module = "androidx.compose.ui:ui" }
compose-material3 = { module = "androidx.compose.material3:material3" }
compose-tooling = { module = "androidx.compose.ui:ui-tooling" }
activity-compose = { module = "androidx.activity:activity-compose", version = "1.11.0" }
hilt-android = { module = "com.google.dagger:hilt-android", version.ref = "hilt" }
hilt-compiler = { module = "com.google.dagger:hilt-compiler", version.ref = "hilt" }
hilt-navigation-compose = { module = "androidx.hilt:hilt-navigation-compose", version.ref = "androidxHilt" }
room-runtime = { module = "androidx.room:room-runtime", version.ref = "room" }
room-ktx = { module = "androidx.room:room-ktx", version.ref = "room" }
room-compiler = { module = "androidx.room:room-compiler", version.ref = "room" }
retrofit = { module = "com.squareup.retrofit2:retrofit", version.ref = "retrofit" }
retrofit-serialization = { module = "com.squareup.retrofit2:converter-kotlinx-serialization", version.ref = "retrofit" }
okhttp = { module = "com.squareup.okhttp3:okhttp", version.ref = "okhttp" }
okhttp-logging = { module = "com.squareup.okhttp3:logging-interceptor", version.ref = "okhttp" }
serialization-json = { module = "org.jetbrains.kotlinx:kotlinx-serialization-json", version.ref = "serialization" }
coil-compose = { module = "io.coil-kt.coil3:coil-compose", version.ref = "coil" }
coil-network-okhttp = { module = "io.coil-kt.coil3:coil-network-okhttp", version.ref = "coil" }
work-runtime = { module = "androidx.work:work-runtime-ktx", version.ref = "work" }

[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
kotlin-android = { id = "org.jetbrains.kotlin.android", version.ref = "kotlin" }
kotlin-compose = { id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }
kotlin-serialization = { id = "org.jetbrains.kotlin.plugin.serialization", version.ref = "kotlin" }
ksp = { id = "com.google.devtools.ksp", version.ref = "ksp" }
hilt = { id = "com.google.dagger.hilt.android", version.ref = "hilt" }
```

<div class="callout warn"><span class="t">버전 숫자는 sync에서 확정</span>
위 숫자는 계획 기준값입니다. Android Studio가 호환성 경고를 내면 최신 stable로 맞추세요 — 조합은 Compose BOM이 관리합니다. 중요한 원칙은 <strong>kapt를 쓰지 않고 KSP2</strong>, <strong>Compose 컴파일러는 <code>kotlin-compose</code> 플러그인</strong>이라는 점입니다.
</div>

## 4. 플러그인·의존성 연결 (`app/build.gradle.kts`)

```kotlin
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.ksp)
    alias(libs.plugins.hilt)
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.material3)
    implementation(libs.activity.compose)
    debugImplementation(libs.compose.tooling)

    implementation(libs.hilt.android)
    ksp(libs.hilt.compiler)                 // ← kapt 아님
    implementation(libs.hilt.navigation.compose)

    implementation(libs.room.runtime)
    implementation(libs.room.ktx)
    ksp(libs.room.compiler)                 // ← kapt 아님

    implementation(libs.retrofit)
    implementation(libs.retrofit.serialization)
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging)
    implementation(libs.serialization.json)

    implementation(libs.coil.compose)
    implementation(libs.coil.network.okhttp)
    implementation(libs.work.runtime)

    testImplementation("junit:junit:4.13.2")
    testImplementation("com.squareup.okhttp3:mockwebserver:5.0.0")
}
```

루트 `build.gradle.kts`에도 플러그인을 `apply false`로 등록합니다.

```kotlin
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.kotlin.serialization) apply false
    alias(libs.plugins.ksp) apply false
    alias(libs.plugins.hilt) apply false
}
```

## 5. Hilt Application 클래스

`app/src/main/java/com/diamondscore/App.kt`:

```kotlin
package com.diamondscore

import android.app.Application
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class DiamondScoreApp : Application()
```

`AndroidManifest.xml`의 `<application>`에 등록하고 인터넷 권한을 추가합니다.

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

<application
    android:name=".DiamondScoreApp"
    ... >
```

## 6. 다크 팔레트 — 목업의 토큰을 M3 ColorScheme으로

목업은 다크 우선입니다. 그 정확한 색값을 Material 3 `darkColorScheme`으로 옮기고, M3에 없는
의미색(라이브 레드·골드·승/패)은 별도 객체로 둡니다.

`app/src/main/java/com/diamondscore/core/designsystem/Color.kt`:

```kotlin
package com.diamondscore.core.designsystem

import androidx.compose.material3.darkColorScheme
import androidx.compose.ui.graphics.Color

val DsDarkColors = darkColorScheme(
    primary          = Color(0xFFFF5563),   // 라이브·강조 레드
    onPrimary        = Color(0xFF2A0A0E),
    background       = Color(0xFF0E1116),
    onBackground     = Color(0xFFE8ECF1),
    surface          = Color(0xFF161B22),   // 카드
    onSurface        = Color(0xFFE8ECF1),
    surfaceVariant   = Color(0xFF1E242E),
    onSurfaceVariant = Color(0xFF98A2B2),   // muted 텍스트
    outline          = Color(0xFF2A313C),   // 카드 테두리·구분선
)

/** M3 역할로 안 잡히는 의미색 (목업 기준). */
object DsColors {
    val live       = Color(0xFFFF5563)
    val liveDot    = Color(0xFFFF3A4C)
    val gold       = Color(0xFFE6B450)   // 진출권·즐겨찾기
    val win        = Color(0xFF3FB980)
    val loss       = Color(0xFFFF6B78)
    val staleBg    = Color(0xFF221D12)
    val staleLine  = Color(0xFF4A3D1E)
    val muted2     = Color(0xFF6B727E)   // 보조 캡션
}
```

<div class="callout tip"><span class="t">라이트 테마</span>
MVP는 다크 우선입니다. 라이트도 지원하려면 같은 역할로 <code>lightColorScheme</code>을 하나 더 만들고 §설정에서 전환합니다(Step 9). 지금은 다크만 만들어 진도를 냅니다.
</div>

## 7. 타이포그래피 — 점수는 등폭 숫자

목업은 본문에 한글 산세리프, **점수·기록에는 등폭(tabular) 숫자**를 씁니다. 숫자가 자리에서
흔들리지 않아야 라인스코어·순위표가 깔끔합니다.

`app/src/main/java/com/diamondscore/core/designsystem/Type.kt`:

```kotlin
package com.diamondscore.core.designsystem

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

val DsTypography = Typography()   // M3 기본(시스템 한글 폰트) 사용

/** 점수·이닝·승률 등 숫자 전용 — 등폭으로 자리 고정. */
val ScoreNumber = TextStyle(
    fontFamily = FontFamily.Monospace,
    fontWeight = FontWeight.SemiBold,
)
```

<div class="callout tip"><span class="t">디자인 폰트를 그대로 쓰려면</span>
목업은 <code>IBM Plex Sans KR / Mono</code>로 렌더했습니다. 앱에서 동일하게 하려면 폰트 파일을 <code>res/font/</code>에 넣고 <code>FontFamily(Font(R.font.…))</code>로 교체하세요. 튜토리얼은 진도를 위해 시스템 한글 폰트 + <code>Monospace</code>로 갑니다.
</div>

## 8. 구단 컬러 + 한국어 팀명

API는 한국어 팀명을 주지 않고 `teamColors`가 전 구단 동일합니다. 목업의 구단 컬러와 한글명을
**앱에 직접** 넣습니다.

`app/src/main/java/com/diamondscore/core/designsystem/KboTeams.kt`:

```kotlin
package com.diamondscore.core.designsystem

import androidx.compose.ui.graphics.Color

data class KboTeam(val id: Long, val nameKo: String, val short: String, val color: Color)

val KBO_TEAMS: Map<Long, KboTeam> = listOf(
    KboTeam(188409, "KT 위즈",     "KT",  Color(0xFF6B7280)), // 검정은 다크 배경에서 안 보여 회색 대체
    KboTeam(188245, "삼성 라이온즈", "삼성", Color(0xFF074CA1)),
    KboTeam(188257, "LG 트윈스",    "LG",  Color(0xFFC30452)),
    KboTeam(188248, "두산 베어스",  "두산", Color(0xFF232A63)),
    KboTeam(188247, "KIA 타이거즈", "KIA", Color(0xFFEA0029)),
    KboTeam(188243, "한화 이글스",  "한화", Color(0xFFFC4E00)),
    KboTeam(188253, "NC 다이노스",  "NC",  Color(0xFF315288)),
    KboTeam(188246, "롯데 자이언츠", "롯데", Color(0xFF24406E)),
    KboTeam(188244, "SSG 랜더스",   "SSG", Color(0xFFCE0E2D)),
    KboTeam(188258, "키움 히어로즈", "키움", Color(0xFF570514)),
).associateBy { it.id }

fun teamNameKo(id: Long, fallback: String): String = KBO_TEAMS[id]?.nameKo ?: fallback
fun teamShort(id: Long): String = KBO_TEAMS[id]?.short ?: "?"
fun teamColor(id: Long): Color = KBO_TEAMS[id]?.color ?: Color(0xFF6B7280)
```

## 9. 테마 Composable

`app/src/main/java/com/diamondscore/core/designsystem/Theme.kt`:

```kotlin
package com.diamondscore.core.designsystem

import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable

@Composable
fun DiamondScoreTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DsDarkColors,
        typography = DsTypography,
        content = content,
    )
}
```

`MainActivity`의 `setContent { }`를 `DiamondScoreTheme { … }`로 감쌉니다.

## 10. 빌드 확인

```bash
./gradlew :app:assembleDebug
```

<div class="checkpoint"><span class="t"></span> <code>BUILD SUCCESSFUL</code>이 뜨고, ▶로 실행 시 배경이 <code>#0E1116</code> 다크로 칠해지면 디자인 시스템까지 완료. (컴포넌트는 Step 5에서 만듭니다)</div>

<div class="pager">
<a href="#/labs/step-1">← Step 1</a>
<a href="#/labs/step-3">Step 3 · 네트워크·매핑 →</a>
</div>
