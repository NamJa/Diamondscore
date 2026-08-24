# Step 2 · 프로젝트 부트스트랩 & 디자인 시스템

<div class="chips"><span class="chip time">60분</span><span class="chip diff">쉬움</span><span class="chip goal">프로젝트·의존성 + 목업의 다크 테마·구단 컬러를 코드로 옮긴다</span></div>

실제 프로젝트를 만들고 Kotlin 2.4 / Compose / Retrofit 3 / Room / Hilt / Coil 3를 version catalog로 고정한 뒤, **확정된 목업의 디자인 토큰**(브로드캐스트 팔레트·Bebas 타이포·구단 컬러)을 Compose 테마(Material 3 `ColorScheme` 컨테이너 위)로 심습니다. 이후 모든 화면이 이 토큰을 씁니다.

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

## 6. 브로드캐스트 팔레트 (다크 + 라이트)

디자인은 **브로드캐스트 × 에디토리얼** — 근블랙 다크가 기본, 페이퍼 라이트가 변형입니다. 목업의
정확한 색을 Compose 테마로 옮깁니다. 기본색(배경·서피스·본문·라인·액센트)은 M3 `ColorScheme`에
매핑해 M3 컴포넌트가 그대로 동작하게 하고, 의미색(라이브·골드·승/패)은 `DsColors`에 둡니다.

`app/src/main/java/com/diamondscore/core/designsystem/Color.kt`:

```kotlin
package com.diamondscore.core.designsystem

import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.ui.graphics.Color

// 다크(기본) — 근블랙 + 브로드캐스트 레드
val DsDarkColors = darkColorScheme(
    primary          = Color(0xFFFF2D4B),   // 라이브·강조
    onPrimary        = Color(0xFFFFFFFF),
    background       = Color(0xFF07080B),
    onBackground     = Color(0xFFEDEFF3),
    surface          = Color(0xFF0C0E14),   // 라이브 히어로 카드
    onSurface        = Color(0xFFEDEFF3),
    surfaceVariant   = Color(0xFF12141C),
    onSurfaceVariant = Color(0xFF8B90A0),   // muted 텍스트
    outline          = Color(0xFF191C24),   // 라인·구분선
    outlineVariant   = Color(0xFF15171E),   // 헤어라인
)

// 라이트 변형 — 페이퍼 + 딥 레드
val DsLightColors = lightColorScheme(
    primary          = Color(0xFFD21F3C),
    onPrimary        = Color(0xFFFFFFFF),
    background       = Color(0xFFFBFAF7),
    onBackground     = Color(0xFF161513),
    surface          = Color(0xFFFFFFFF),
    onSurface        = Color(0xFF161513),
    surfaceVariant   = Color(0xFFEFEDE6),
    onSurfaceVariant = Color(0xFF6B6862),
    outline          = Color(0xFFE4E0D8),
    outlineVariant   = Color(0xFFECE8E0),
)

/** M3 역할로 안 잡히는 의미색. 다크/라이트 두 세트. */
data class DsExtras(
    val liveDot: Color, val gold: Color, val win: Color, val loss: Color,
    val staleBg: Color, val staleLine: Color, val faint: Color,
)
val DarkExtras  = DsExtras(Color(0xFFFF2D4B), Color(0xFFE7B24A), Color(0xFF39D98A), Color(0xFFC83250),
                           Color(0xFF241C0B), Color(0xFF4A3D1E), Color(0xFF4A4E5C))
val LightExtras = DsExtras(Color(0xFFD21F3C), Color(0xFFB98900), Color(0xFF1E9E5E), Color(0xFFC83250),
                           Color(0xFFFBF3DC), Color(0xFFE8DCBE), Color(0xFFB4AFA4))

val LocalDsExtras = androidx.compose.runtime.staticCompositionLocalOf { DarkExtras }

/** 의미색을 테마 인지형으로 읽는 접근자 — 컴포저블 안에서 `DsColors.live` 처럼 씁니다. */
object DsColors {
    val live: Color      @Composable @ReadOnlyComposable get() = MaterialTheme.colorScheme.primary
    val liveDot: Color   @Composable @ReadOnlyComposable get() = LocalDsExtras.current.liveDot
    val gold: Color      @Composable @ReadOnlyComposable get() = LocalDsExtras.current.gold
    val win: Color       @Composable @ReadOnlyComposable get() = LocalDsExtras.current.win
    val loss: Color      @Composable @ReadOnlyComposable get() = LocalDsExtras.current.loss
    val staleBg: Color   @Composable @ReadOnlyComposable get() = LocalDsExtras.current.staleBg
    val staleLine: Color @Composable @ReadOnlyComposable get() = LocalDsExtras.current.staleLine
    val muted2: Color    @Composable @ReadOnlyComposable get() = LocalDsExtras.current.faint
}
```
> `DsColors`는 `@Composable` 프로퍼티 getter라 컴포저블 안에서만 읽힙니다(모든 UI 코드가 그렇습니다).
> 추가 import: `androidx.compose.material3.MaterialTheme`, `androidx.compose.runtime.{Composable, ReadOnlyComposable}`.

<div class="callout tip"><span class="t">색을 읽는 법</span>
배경·서피스·본문·라인·액센트는 <code>MaterialTheme.colorScheme.{background,surface,onSurface,onSurfaceVariant,outline,primary}</code>로, 라이브 닷·골드·승/패는 <code>LocalDsExtras.current.{liveDot,gold,win,loss}</code>로 읽습니다. 이렇게 하면 다크↔라이트 전환 시 색이 자동으로 바뀝니다.
</div>

## 7. 타이포그래피 — Bebas Neue + Archivo + Noto Sans KR

스코어·헤더는 **Bebas Neue**(콘덴스드 디스플레이), 본문·UI는 **Archivo + Noto Sans KR**, 숫자는
**등폭(tabular)**. 세 폰트는 Google Fonts에서 받습니다.

`app/build.gradle.kts` 의존성에 추가:

```kotlin
implementation("androidx.compose.ui:ui-text-google-fonts")
```

`core/designsystem/Type.kt`:

```kotlin
package com.diamondscore.core.designsystem

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.*
import androidx.compose.ui.text.googlefonts.GoogleFont
import androidx.compose.ui.text.googlefonts.Font
import androidx.compose.ui.unit.sp
import com.diamondscore.R

private val provider = GoogleFont.Provider(
    "com.google.android.gms.fonts",
    "com.google.android.gms",
    R.array.com_google_android_gms_fonts_certs,
)
private fun gf(name: String, w: FontWeight) = FontFamily(Font(GoogleFont(name), provider, w))

val Bebas   = FontFamily(Font(GoogleFont("Bebas Neue"), provider, FontWeight.Normal))
val Archivo = FontFamily(
    Font(GoogleFont("Archivo"), provider, FontWeight.Normal),
    Font(GoogleFont("Archivo"), provider, FontWeight.Medium),
    Font(GoogleFont("Archivo"), provider, FontWeight.Bold),
)

/** 본문·UI (한글은 시스템 Noto Sans KR로 자동 폴백). */
val DsTypography = Typography().let { t ->
    t.copy(
        titleLarge = t.titleLarge.copy(fontFamily = Archivo, fontWeight = FontWeight.Bold),
        bodyLarge  = t.bodyLarge.copy(fontFamily = Archivo),
        bodyMedium = t.bodyMedium.copy(fontFamily = Archivo),
        labelLarge = t.labelLarge.copy(fontFamily = Archivo, fontWeight = FontWeight.Medium),
        labelSmall = t.labelSmall.copy(fontFamily = Archivo),
    )
}

/** 스코어·큰 숫자·섹션 헤더 — Bebas. */
val Display = TextStyle(fontFamily = Bebas, letterSpacing = 0.02.em)
/** 표·순위의 작은 숫자 — Archivo 등폭. */
val ScoreNumber = TextStyle(
    fontFamily = Archivo, fontWeight = FontWeight.Medium,
    fontFeatureSettings = "tnum",   // tabular numbers
)
```

<div class="callout tip"><span class="t">오프라인 대안</span>
Google Fonts 다운로드가 부담되면 <code>Bebas Neue</code>·<code>Archivo</code> <code>.ttf</code>를 <code>res/font/</code>에 넣고 <code>FontFamily(Font(R.font.bebas_neue))</code>로 바꾸면 됩니다. 한글은 시스템 Noto Sans KR가 폴백합니다. <code>Display</code>는 콘덴스드라 <strong>초대형 스코어·섹션 헤더 전용</strong>, 본문엔 쓰지 않습니다.
</div>

## 8. 구단 컬러 + 한국어 팀명

API는 한국어 팀명을 주지 않고 `teamColors`가 전 구단 동일합니다. 목업의 구단 컬러와 한글명을
**앱에 직접** 넣습니다.

`core/designsystem/KboTeams.kt`:

```kotlin
package com.diamondscore.core.designsystem

import androidx.compose.ui.graphics.Color

data class KboTeam(val id: Long, val nameKo: String, val short: String, val color: Color)

val KBO_TEAMS: Map<Long, KboTeam> = listOf(
    KboTeam(188409, "KT 위즈",     "KT",  Color(0xFF8A8D91)), // 검정은 안 보여 회색 대체
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
fun teamColor(id: Long): Color = KBO_TEAMS[id]?.color ?: Color(0xFF8A8D91)
```

## 9. 테마 Composable — 다크 기본 + 라이트

`core/designsystem/Theme.kt`:

```kotlin
package com.diamondscore.core.designsystem

import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider

@Composable
fun DiamondScoreTheme(dark: Boolean = true, content: @Composable () -> Unit) {
    CompositionLocalProvider(LocalDsExtras provides if (dark) DarkExtras else LightExtras) {
        MaterialTheme(
            colorScheme = if (dark) DsDarkColors else DsLightColors,
            typography = DsTypography,
            content = content,
        )
    }
}
```

`MainActivity`의 `setContent { }`를 `DiamondScoreTheme { … }`로 감쌉니다. `dark`는 Step 9 설정에서
DataStore 값으로 제어합니다(기본 다크).

## 10. 빌드 확인

```bash
./gradlew :app:assembleDebug
```

<div class="checkpoint"><span class="t"></span> <code>BUILD SUCCESSFUL</code>이 뜨고, ▶로 실행 시 배경이 <code>#07080B</code> 근블랙으로 칠해지면 디자인 시스템까지 완료. (컴포넌트는 Step 5에서 만듭니다)</div>

<div class="pager">
<a href="#/labs/step-1">← Step 1</a>
<a href="#/labs/step-3">Step 3 · 네트워크·매핑 →</a>
</div>
