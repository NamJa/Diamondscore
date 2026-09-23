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
    compileSdk = 37                     // 카탈로그 라이브러리가 37을 요구한다(아래 callout). targetSdk는 36

    defaultConfig {
        applicationId = "com.diamondscore"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    buildFeatures { compose = true }

    compileOptions {                    // Step 0이 예고한 "Java 17 기준" 설정은 여기 한 곳뿐입니다
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildTypes {
        release {
            isMinifyEnabled = true          // R8 full mode
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfig = signingConfigs.getByName("debug")   // 개인용 — 서명이 없으면 릴리스 APK를 설치조차 못 한다(Step 9 §7)
        }
    }
}
```

<div class="callout warn"><span class="t"><code>compileSdk</code>는 37, <code>targetSdk</code>는 36</span>
§3 카탈로그의 라이브러리 29개(Compose BOM 2026.08의 1.12.0, core-ktx 1.19.0, lifecycle 2.11.0, Coil 3.6.1, OkHttp 5.5.0, adaptive 1.3.0, hilt-lifecycle-viewmodel-compose 1.4.0 등)가 AAR 메타데이터로 <strong>compileSdk 37 이상</strong>을 요구합니다. 36으로 두면 <code>:app:checkDebugAarMetadata</code>에서 빌드가 멈춥니다(2026-09-23 실측). <code>compileSdk</code>는 어떤 API로 컴파일할지일 뿐이라 올려도 동작이 바뀌지 않고, 실행 동작을 정하는 <code>targetSdk</code>는 Play 요건대로 36에 둡니다. Step 0에서 SDK Platform 37을 설치한 이유입니다.
<br><code>signingConfig</code> 줄은 개인용 편의입니다 — 없으면 <code>assembleRelease</code>가 <code>app-release-unsigned.apk</code>를 만들고 <code>adb install</code>이 <code>INSTALL_PARSE_FAILED_NO_CERTIFICATES</code>로 거절해 Step 9 §7의 "릴리스를 실제로 실행"을 할 수 없습니다. 스토어에 올릴 때는 업로드 키로 바꿉니다.
</div>

<div class="callout warn"><span class="t">AGP 9는 Kotlin이 내장이다</span>
AGP 9.0부터 <strong>built-in Kotlin</strong>이 기본이라 <code>org.jetbrains.kotlin.android</code> 플러그인을 적용하지 <strong>않습니다</strong>(새 DSL과 비호환). 그래서 <code>android { kotlinOptions { } }</code>도 없습니다 — 컴파일러 옵션은 최상위 <code>kotlin { compilerOptions { } }</code>에 씁니다. 별도 옵션이 없으면 jvmTarget은 위 <code>compileOptions.targetCompatibility</code>를 따라가므로 아무것도 더 쓸 필요가 없습니다.
</div>

## 3. version catalog (`gradle/libs.versions.toml`)

버전을 한곳에 고정합니다. **동적 버전(`+`)은 쓰지 않습니다.**

```toml
[versions]
agp = "9.4.0"
kotlin = "2.4.10"
ksp = "2.3.11"                # KSP2는 2.3.0부터 Kotlin 접두사 없는 독립 버전제
composeBom = "2026.08.00"
hilt = "2.60.1"               # KSP 2.3.x 위에서 도는 첫 Hilt
androidxHilt = "1.4.0"
room = "2.8.4"
retrofit = "3.0.0"
okhttp = "5.5.0"
serialization = "1.11.0"
coroutines = "1.11.0"
coil = "3.6.1"
nav3 = "1.1.7"
nav3Adaptive = "1.3.0"
lifecycle = "2.11.0"
work = "2.11.2"
coreKtx = "1.19.0"
activityCompose = "1.13.0"
datastore = "1.2.1"
turbine = "1.2.1"
espresso = "3.7.0"
junit = "4.13.2"

[libraries]
androidx-core-ktx = { module = "androidx.core:core-ktx", version.ref = "coreKtx" }
activity-compose = { module = "androidx.activity:activity-compose", version.ref = "activityCompose" }
lifecycle-runtime-compose = { module = "androidx.lifecycle:lifecycle-runtime-compose", version.ref = "lifecycle" }
lifecycle-viewmodel-compose = { module = "androidx.lifecycle:lifecycle-viewmodel-compose", version.ref = "lifecycle" }

# Compose — 버전은 BOM이 관리 (version 생략)
compose-bom = { module = "androidx.compose:compose-bom", version.ref = "composeBom" }
compose-ui = { module = "androidx.compose.ui:ui" }
compose-material3 = { module = "androidx.compose.material3:material3" }
compose-icons-extended = { module = "androidx.compose.material:material-icons-extended" }
compose-ui-text-google-fonts = { module = "androidx.compose.ui:ui-text-google-fonts" }
compose-tooling = { module = "androidx.compose.ui:ui-tooling" }
compose-tooling-preview = { module = "androidx.compose.ui:ui-tooling-preview" }
compose-ui-test-junit4 = { module = "androidx.compose.ui:ui-test-junit4" }
compose-ui-test-manifest = { module = "androidx.compose.ui:ui-test-manifest" }
espresso-core = { module = "androidx.test.espresso:espresso-core", version.ref = "espresso" }   # 명시하지 않으면 ui-test-junit4가 끌어오는 3.5.0이 쓰여 API 34+에서 깨진다(§4)

# Navigation 3 (Nav2의 NavHost·NavController는 쓰지 않습니다 — Step 9)
nav3-runtime = { module = "androidx.navigation3:navigation3-runtime", version.ref = "nav3" }
nav3-ui = { module = "androidx.navigation3:navigation3-ui", version.ref = "nav3" }
nav3-viewmodel = { module = "androidx.lifecycle:lifecycle-viewmodel-navigation3", version.ref = "lifecycle" }
nav3-adaptive = { module = "androidx.compose.material3.adaptive:adaptive-navigation3", version.ref = "nav3Adaptive" }

hilt-android = { module = "com.google.dagger:hilt-android", version.ref = "hilt" }
hilt-compiler = { module = "com.google.dagger:hilt-compiler", version.ref = "hilt" }
hilt-viewmodel-compose = { module = "androidx.hilt:hilt-lifecycle-viewmodel-compose", version.ref = "androidxHilt" }
hilt-work = { module = "androidx.hilt:hilt-work", version.ref = "androidxHilt" }
hilt-work-compiler = { module = "androidx.hilt:hilt-compiler", version.ref = "androidxHilt" }
hilt-android-testing = { module = "com.google.dagger:hilt-android-testing", version.ref = "hilt" }

room-runtime = { module = "androidx.room:room-runtime", version.ref = "room" }
room-ktx = { module = "androidx.room:room-ktx", version.ref = "room" }
room-compiler = { module = "androidx.room:room-compiler", version.ref = "room" }
room-testing = { module = "androidx.room:room-testing", version.ref = "room" }   # MigrationTestHelper용 — DB가 version 1이라 이 튜토리얼 코드에는 안 나옵니다(지우지 말 것: 계획서 §5.4가 Step 2를 전체 catalog로 둡니다)

retrofit = { module = "com.squareup.retrofit2:retrofit", version.ref = "retrofit" }
retrofit-serialization = { module = "com.squareup.retrofit2:converter-kotlinx-serialization", version.ref = "retrofit" }
okhttp = { module = "com.squareup.okhttp3:okhttp", version.ref = "okhttp" }
okhttp-logging = { module = "com.squareup.okhttp3:logging-interceptor", version.ref = "okhttp" }
okhttp-mockwebserver = { module = "com.squareup.okhttp3:mockwebserver", version.ref = "okhttp" }
serialization-json = { module = "org.jetbrains.kotlinx:kotlinx-serialization-json", version.ref = "serialization" }

coil-compose = { module = "io.coil-kt.coil3:coil-compose", version.ref = "coil" }
coil-network-okhttp = { module = "io.coil-kt.coil3:coil-network-okhttp", version.ref = "coil" }
datastore-preferences = { module = "androidx.datastore:datastore-preferences", version.ref = "datastore" }
work-runtime = { module = "androidx.work:work-runtime-ktx", version.ref = "work" }

junit = { module = "junit:junit", version.ref = "junit" }
coroutines-test = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-test", version.ref = "coroutines" }
turbine = { module = "app.cash.turbine:turbine", version.ref = "turbine" }   # Flow 단언용 — Step 4의 Fake DAO가 flowOf라 실제로 쓰는 테스트는 없습니다(카탈로그에는 남겨 둡니다)
kotlin-test = { module = "org.jetbrains.kotlin:kotlin-test", version.ref = "kotlin" }  # assertFailsWith·assertIs (Step 3)

[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
kotlin-compose = { id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }
kotlin-serialization = { id = "org.jetbrains.kotlin.plugin.serialization", version.ref = "kotlin" }
ksp = { id = "com.google.devtools.ksp", version.ref = "ksp" }
hilt = { id = "com.google.dagger.hilt.android", version.ref = "hilt" }
```

<div class="callout warn"><span class="t">이 세 줄은 그냥 최신이 아니라 서로 묶여 있다</span>
<ul>
<li><strong>KSP는 <code>2.3.11</code></strong>: KSP2가 2.3.0부터 <code>&lt;Kotlin&gt;-&lt;KSP&gt;</code> 접두사를 버리고 독립 버전제로 바뀌었습니다. 구 스킴은 <code>2.2.21-2.0.5</code>에서 끝났으니 <code>2.4.x-2.0.0</code> 같은 버전을 찾지 마세요 — 없습니다.</li>
<li><strong>Hilt는 <code>2.60.1</code> 이상</strong>: Hilt 2.59.x까지는 구 스킴 KSP(<code>2.2.20-2.0.3</code>)로 빌드돼 있어 KSP 2.3.x와 함께 못 씁니다.</li>
<li><strong>Gradle은 <code>9.7.1</code></strong>: AGP 9.4.0의 최소 Gradle이 9.6.0입니다.</li>
</ul>
버전 조합이 어긋나면 sync 단계에서 바로 깨지므로, 이 셋은 함께 올리거나 함께 두세요. Compose 쪽 조합은 BOM이 관리하니 개별 pin을 넣지 마세요.
</div>

## 4. 플러그인·의존성 연결 (`app/build.gradle.kts`)

```kotlin
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)          // Compose 컴파일러 (Kotlin 동봉)
    alias(libs.plugins.kotlin.serialization)    // DTO + Nav3 NavKey 직렬화
    alias(libs.plugins.ksp)
    alias(libs.plugins.hilt)
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.activity.compose)
    implementation(libs.lifecycle.runtime.compose)
    implementation(libs.lifecycle.viewmodel.compose)

    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.material3)
    implementation(libs.compose.icons.extended)
    implementation(libs.compose.tooling.preview)
    debugImplementation(libs.compose.tooling)

    implementation(libs.nav3.runtime)
    implementation(libs.nav3.ui)
    implementation(libs.nav3.viewmodel)
    implementation(libs.nav3.adaptive)

    implementation(libs.hilt.android)
    ksp(libs.hilt.compiler)                 // ← kapt 아님
    implementation(libs.hilt.viewmodel.compose)
    implementation(libs.hilt.work)
    ksp(libs.hilt.work.compiler)

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
    implementation(libs.datastore.preferences)
    implementation(libs.work.runtime)

    testImplementation(libs.junit)
    testImplementation(libs.kotlin.test)    // assertFailsWith·assertIs (Step 3 매퍼 테스트)
    testImplementation(libs.coroutines.test)
    testImplementation(libs.turbine)
    testImplementation(libs.okhttp.mockwebserver)
    testImplementation(libs.room.testing)

    androidTestImplementation(platform(libs.compose.bom))
    androidTestImplementation(libs.compose.ui.test.junit4)
    // ui-test-junit4는 espresso-core 3.5.0·runner 1.5.0을 끌어오는데, 3.5.0은 API 34+ 기기에서
    // NoSuchMethodException(InputManager.getInstance)으로 모든 Compose UI 테스트를 깨뜨린다(Step 9 §5). 템플릿이 넣던 3.7.0을 명시한다
    androidTestImplementation(libs.espresso.core)
    // Hilt 계측 테스트를 실제로 작성할 때는 kspAndroidTest(libs.hilt.compiler)와
    // HiltTestApplication을 띄우는 커스텀 러너가 더 필요합니다(이 튜토리얼 범위 밖).
    androidTestImplementation(libs.hilt.android.testing)
    debugImplementation(libs.compose.ui.test.manifest)
}

// Room 스키마 export 위치 — ksp 플러그인을 위에서 적용한 뒤라야 이 블록이 해석됩니다
// (Step 4에서 exportSchema = true를 씁니다).
ksp { arg("room.schemaLocation", "$projectDir/schemas") }
```

루트 `build.gradle.kts`:

```kotlin
buildscript {
    dependencies {
        // AGP 9.4는 KGP 2.2.10을 동봉한다. Kotlin 2.4를 쓰려면 여기서 올려야 한다.
        classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:2.4.10")
    }
}

plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.kotlin.serialization) apply false
    alias(libs.plugins.ksp) apply false
    alias(libs.plugins.hilt) apply false
}
```

Gradle wrapper도 맞춰 올립니다 — **AGP 9.4는 Gradle 9.6.0 이상을 요구**합니다. 빌드 스크립트가 새 카탈로그와 맞아진 **지금** 실행하세요 — §3 직후에 돌리면 `app/build.gradle.kts`가 아직 옛 alias를 참조해 configuration 단계에서 깨집니다.

```bash
./gradlew wrapper --gradle-version 9.7.1
```

<div class="callout tip"><span class="t">material-icons-extended는 동결된 아티팩트</span>
BOM이 <code>1.7.8</code>로 고정해 주며 그 이후 업데이트가 없습니다(deprecated). 이 앱은 아이콘 14종만 쓰므로 그대로 쓰되, 아이콘을 많이 넣게 되면 필요한 <code>ImageVector</code>만 직접 정의하는 쪽이 APK에 낫습니다.
</div>

## 5. Hilt Application 클래스

`app/src/main/java/com/diamondscore/App.kt`:

```kotlin
package com.diamondscore

import android.app.Application
import dagger.hilt.android.HiltAndroidApp

// 이름은 DiamondScoreApplication이다 — Step 9의 @Composable fun DiamondScoreApp()과 같은 패키지라
// 클래스를 DiamondScoreApp으로 두면 생성자와 함수가 같은 시그니처로 충돌한다("Conflicting overloads").
@HiltAndroidApp
class DiamondScoreApplication : Application()
```

`AndroidManifest.xml`의 `<application>`에 등록하고 인터넷 권한을 추가합니다.

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

<application
    android:name=".DiamondScoreApplication"
    ... >
```

## 6. 브로드캐스트 팔레트 (다크 + 라이트)

디자인은 **브로드캐스트 × 에디토리얼** — 근블랙 다크가 기본, 페이퍼 라이트가 변형입니다. 목업의
정확한 색을 Compose 테마로 옮깁니다. 기본색(배경·서피스·본문·라인·액센트)은 M3 `ColorScheme`에
매핑해 M3 컴포넌트가 그대로 동작하게 하고, 의미색(라이브·골드·승/패)은 `DsColors`에 둡니다.

`app/src/main/java/com/diamondscore/core/designsystem/Color.kt`:

```kotlin
package com.diamondscore.core.designsystem

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.ReadOnlyComposable
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

/** M3 역할로 안 잡히는 의미색. 다크/라이트 두 세트. `live`는 `primary`와 같은 값이라 여기 두지 않는다. */
data class DsExtras(
    val gold: Color, val win: Color, val loss: Color,
    val staleBg: Color, val staleLine: Color, val faint: Color,
    // 목업이 본문 아래로 두 단계를 더 쓰고(팀명·보조 라벨 / 캡션·미세 수치),
    // 스코어보드 승팀 약칭(Step 7 §2)처럼 액센트를 한 톤 낮춰 쓰는 자리가 있다.
    // 목업에서 loss와 accentSoft는 같은 색이다(다크 #FF6B7F, 라이트 #C83250) — 역할이 달라 따로 둔다.
    val textSecondary: Color, val textTertiary: Color, val accentSoft: Color,
)
val DarkExtras  = DsExtras(Color(0xFFE7B24A), Color(0xFF39D98A), Color(0xFFFF6B7F),
                           Color(0xFF241C0B), Color(0xFF4A3D1E), Color(0xFF4A4E5C),
                           Color(0xFFC7CBD6), Color(0xFF6B7080), Color(0xFFFF6B7F))
val LightExtras = DsExtras(Color(0xFFB98900), Color(0xFF1E9E5E), Color(0xFFC83250),
                           Color(0xFFFBF3DC), Color(0xFFE8DCBE), Color(0xFFB4AFA4),
                           Color(0xFF3A3833), Color(0xFF8A867D), Color(0xFFC83250))

val LocalDsExtras = androidx.compose.runtime.staticCompositionLocalOf { DarkExtras }

/** 의미색을 테마 인지형으로 읽는 접근자 — 컴포저블 안에서 `DsColors.live` 처럼 씁니다. */
object DsColors {
    val live: Color      @Composable @ReadOnlyComposable get() = MaterialTheme.colorScheme.primary
    val gold: Color      @Composable @ReadOnlyComposable get() = LocalDsExtras.current.gold
    val win: Color       @Composable @ReadOnlyComposable get() = LocalDsExtras.current.win
    val loss: Color      @Composable @ReadOnlyComposable get() = LocalDsExtras.current.loss
    val staleBg: Color   @Composable @ReadOnlyComposable get() = LocalDsExtras.current.staleBg
    val staleLine: Color @Composable @ReadOnlyComposable get() = LocalDsExtras.current.staleLine
    val muted2: Color    @Composable @ReadOnlyComposable get() = LocalDsExtras.current.faint
    val textSecondary: Color @Composable @ReadOnlyComposable get() = LocalDsExtras.current.textSecondary
    val textTertiary: Color  @Composable @ReadOnlyComposable get() = LocalDsExtras.current.textTertiary
    val accentSoft: Color    @Composable @ReadOnlyComposable get() = LocalDsExtras.current.accentSoft
}
```
> `DsColors`는 `@Composable` 프로퍼티 getter라 컴포저블 안에서만 읽힙니다(모든 UI 코드가 그렇습니다).

<div class="callout tip"><span class="t">색을 읽는 법</span>
배경·서피스·본문·라인·액센트는 <code>MaterialTheme.colorScheme.{background,surface,onSurface,onSurfaceVariant,outline,primary}</code>로, 골드·승/패는 <code>LocalDsExtras.current.{gold,win,loss}</code>로 읽습니다. 이렇게 하면 다크↔라이트 전환 시 색이 자동으로 바뀝니다.
<br>본문 아래 두 단계는 <code>DsColors.textSecondary</code>(팀명·보조 라벨)와 <code>DsColors.textTertiary</code>(캡션·미세 수치), 한 톤 낮춘 액센트는 <code>DsColors.accentSoft</code>(Step 7 스코어보드의 승팀 약칭)입니다 — 화면 코드에 <code>Color(0xFF…)</code>를 직접 적지 않으려면 이 셋이 필요합니다.
<br><strong><code>win</code>·<code>loss</code>는 Step 5 <code>StandingRow</code>의 연속 컬럼이 씁니다</strong>(연승이면 <code>win</code>, 연패면 <code>loss</code>) — <strong>지우지 마세요.</strong> 목업 팀 상세의 승/패 글자 자리는 Step 8이 공용 <code>GameCard</code>(승팀을 굵게)로 대신합니다.
</div>

## 7. 타이포그래피 — Bebas Neue + Archivo + Noto Sans KR

스코어·헤더는 **Bebas Neue**(콘덴스드 디스플레이), 본문·UI는 **Archivo + Noto Sans KR**, 숫자는
**등폭(tabular)**. 세 폰트는 Google Fonts에서 받습니다.

`app/build.gradle.kts` 의존성에 추가:

```kotlin
implementation(libs.compose.ui.text.google.fonts)
```

`core/designsystem/Type.kt`:

```kotlin
package com.diamondscore.core.designsystem

import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.*
import androidx.compose.ui.text.googlefonts.GoogleFont
import androidx.compose.ui.text.googlefonts.Font
import androidx.compose.ui.unit.em

private val provider = GoogleFont.Provider(
    "com.google.android.gms.fonts",
    "com.google.android.gms",
    // 인증서 배열은 ui-text-google-fonts AAR이 들고 있습니다. AGP 9의 non-transitive R 탓에
    // 앱 R(com.diamondscore.R)에는 들어오지 않으므로 라이브러리 R을 정규화해 씁니다.
    androidx.compose.ui.text.googlefonts.R.array.com_google_android_gms_fonts_certs,
)
val Bebas   = FontFamily(Font(GoogleFont("Bebas Neue"), provider, FontWeight.Normal))
val Archivo = FontFamily(
    Font(GoogleFont("Archivo"), provider, FontWeight.Normal),
    Font(GoogleFont("Archivo"), provider, FontWeight.Medium),
    Font(GoogleFont("Archivo"), provider, FontWeight.Bold),
)

/** 본문·UI (한글은 시스템 Noto Sans KR로 자동 폴백). 뒤 단계가 실제로 쓰는 스타일만 덮습니다. */
val DsTypography = Typography().let { t ->
    t.copy(
        titleMedium = t.titleMedium.copy(fontFamily = Archivo, fontWeight = FontWeight.Bold),
        bodyLarge   = t.bodyLarge.copy(fontFamily = Archivo),
        bodyMedium  = t.bodyMedium.copy(fontFamily = Archivo),
        // labelLarge는 화면 코드가 직접 부르지 않지만 M3 Button·TextButton의 기본 스타일이라 남깁니다.
        labelLarge  = t.labelLarge.copy(fontFamily = Archivo, fontWeight = FontWeight.Medium),
        labelMedium = t.labelMedium.copy(fontFamily = Archivo),
        labelSmall  = t.labelSmall.copy(fontFamily = Archivo),
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
Google Fonts 다운로드가 부담되면 <code>Bebas Neue</code>·<code>Archivo</code> <code>.ttf</code>를 <code>res/font/</code>에 넣고 <code>FontFamily(Font(R.font.bebas_neue))</code>로 바꾸면 됩니다(이 경로에서는 앱 리소스라 <code>import com.diamondscore.R</code>가 필요합니다). 한글은 시스템 Noto Sans KR가 폴백합니다. <code>Display</code>는 콘덴스드라 <strong>초대형 스코어·섹션 헤더 전용</strong>, 본문엔 쓰지 않습니다.
<br>lint는 위 인증서 배열에 <code>PrivateResource</code> 경고를 냅니다 — 라이브러리 비공개 리소스라 지금은 동작하지만(2026-09-23 Compose 1.12.0 실측) 버전을 올릴 때 사라질 수 있습니다. 그때는 이 오프라인 대안으로 바꿉니다.
</div>

## 8. 구단 컬러 + 한국어 팀명

API는 한글 약칭(`KIA`, `두산`)만 주고 정식 명칭·구단 컬러는 주지 않으며, 구장명 표기가 경기마다 다릅니다(계획서 §3.4-6).
목업의 구단 컬러·정식 명칭·홈 도시를 **앱에 직접** 넣습니다. 팀 ID는 wisetoto의 `team_info_seq`입니다.

이 표를 **두 파일로 나눕니다.** 팀명·약칭은 매퍼(data 레이어)가 쓰고, 컬러는 UI만 씁니다. 한 파일에
두면 `Color` 때문에 data 레이어가 Compose에 의존하게 됩니다 — 나중에 모듈을 쪼갤 때 그 의존이
`:data → :core:designsystem`이라는 못 쓰는 방향으로 굳습니다.

`core/common/KboTeams.kt` — **Compose 없는 순수 Kotlin**:

```kotlin
package com.diamondscore.core.common

data class KboTeam(val id: Long, val nameKo: String, val short: String, val home: String, val colorArgb: Long)

val KBO_TEAMS: Map<Long, KboTeam> = listOf(       // id = wisetoto team_info_seq
    KboTeam(2674, "KT 위즈",     "KT",  "수원", 0xFF8A8D91), // 검정은 안 보여 회색 대체
    KboTeam(318,  "삼성 라이온즈", "삼성", "대구", 0xFF074CA1),
    KboTeam(322,  "LG 트윈스",    "LG",  "잠실", 0xFFC30452),
    KboTeam(316,  "두산 베어스",  "두산", "잠실", 0xFF232A63),
    KboTeam(320,  "KIA 타이거즈", "KIA", "광주", 0xFFEA0029),
    KboTeam(319,  "한화 이글스",  "한화", "대전", 0xFFFC4E00),
    KboTeam(2107, "NC 다이노스",  "NC",  "창원", 0xFF315288),
    KboTeam(317,  "롯데 자이언츠", "롯데", "사직", 0xFF24406E),
    KboTeam(315,  "SSG 랜더스",   "SSG", "인천", 0xFFCE0E2D),
    KboTeam(321,  "키움 히어로즈", "키움", "고척", 0xFF570514),
).associateBy { it.id }

fun teamNameKo(id: Long, fallback: String): String = KBO_TEAMS[id]?.nameKo ?: fallback
fun teamShort(id: Long): String = KBO_TEAMS[id]?.short ?: "?"
```

`core/designsystem/TeamColors.kt` — Compose는 여기만:

```kotlin
package com.diamondscore.core.designsystem

import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.graphics.toArgb
import com.diamondscore.core.common.KBO_TEAMS

/** 구단 원색 — 엠블럼·컬러 바처럼 **면**으로 쓸 때만. */
fun teamColor(id: Long): Color = Color(KBO_TEAMS[id]?.colorArgb ?: 0xFF8A8D91)

/**
 * 구단 색을 현재 배경 위에서 읽히게 조정한 틴트 — 팀명 라벨·등번호처럼 **글자**로 쓸 때.
 * 원색을 그대로 글자에 쓰면 두산(`#232A63`)·롯데(`#24406E`)처럼 어두운 팀은 다크 배경에서 사라지고,
 * KIA(`#EA0029`)처럼 밝은 팀은 라이트 배경에서 대비가 모자랍니다. 색상(hue)은 유지한 채 채도·명도만 옮깁니다.
 */
@Composable @ReadOnlyComposable
fun teamTint(id: Long): Color {
    val dark = MaterialTheme.colorScheme.background.luminance() < 0.5f
    val hsv = FloatArray(3).also { android.graphics.Color.colorToHSV(teamColor(id).toArgb(), it) }
    hsv[1] = hsv[1].coerceAtMost(if (dark) 0.55f else 0.95f)   // 채도
    hsv[2] = if (dark) maxOf(hsv[2], 0.85f) else minOf(hsv[2], 0.55f)   // 명도
    return Color(android.graphics.Color.HSVToColor(hsv))
}
```

<div class="callout tip"><span class="t">팀 색과 앱 액센트는 다른 역할이다</span>
확정 목업이 두 계열을 <strong>섞지 않습니다</strong>.
<ul>
<li><strong>팀 색</strong>(<code>teamColor</code>/<code>teamTint</code>) — "이건 이 팀 것"을 가리킬 때: 엠블럼, 헤더 글로우, 팀명 라벨, 등번호, 순위표의 팀 닷.</li>
<li><strong>앱 액센트</strong>(<code>MaterialTheme.colorScheme.primary</code>) — 앱의 기능일 때: 라이브 배지, 탭바 선택, 세그먼트, 링크·이동, 대표 기록 수치.</li>
</ul>
KIA 레드가 앱 액센트와 우연히 같은 계열이라 이 구분이 안 보였는데, 두산처럼 네이비 팀을 열어 보면 바로 드러납니다 — 팀 헤더는 네이비, 탭바와 "선수단 ›"은 여전히 레드입니다.
</div>

<div class="callout tip"><span class="t">경계 규칙</span>
이 앱이 지키는 규칙은 두 개뿐입니다 — <strong><code>feature</code>·<code>core/ui</code>·<code>core/designsystem</code>은 <code>data</code>의 내부(<code>WisetotoApi</code>·DAO·DTO·Entity)를 참조하지 않는다 — 넘어오는 것은 Repository와 <code>domain/model</code>뿐</strong>, <strong>DTO·Room Entity는 <code>data</code> 레이어를 벗어나지 않는다.</strong> 위 분리는 그 둘에서 파생되는 규칙(<strong><code>data</code>는 Compose를 모른다</strong>)을 위한 것입니다.
</div>

## 9. 내비게이션 키 (Navigation 3)

Navigation 3는 문자열 route가 아니라 **타입 있는 키 객체**로 이동합니다. 화면 인자(`gameId`·`teamId`)가
키의 프로퍼티가 되므로 `NavType`·`navArgument`·파싱이 전부 사라집니다.

키는 화면들이 서로를 직접 참조하지 않도록 한곳에 모읍니다. `core/navigation/DsNavKeys.kt` —
**Compose를 모르는 파일**입니다(`navigation3-runtime`의 `NavKey` 인터페이스만 씁니다):

```kotlin
package com.diamondscore.core.navigation

import androidx.navigation3.runtime.NavKey
import kotlinx.serialization.Serializable

// 탭 루트 4개
@Serializable data object GamesKey : NavKey
@Serializable data object StandingsKey : NavKey
@Serializable data object TeamsKey : NavKey
@Serializable data object FavoritesKey : NavKey

// 인자를 받는 화면
@Serializable data class GameDetailKey(val gameId: Long) : NavKey
@Serializable data class TeamDetailKey(val teamId: Long) : NavKey
@Serializable data class TeamRosterKey(val teamId: Long) : NavKey      // 팀 정보 — 선수단·연혁 (Step 8)
// Player_Info 응답에는 소속 팀이 없다 → 팀 색·팀명을 위해 키가 teamId를 함께 싣는다 (Step 8-4)
@Serializable data class PlayerDetailKey(val playerId: Long, val teamId: Long) : NavKey

@Serializable data object SettingsKey : NavKey
```

<div class="callout tip"><span class="t">키가 9개인 이유</span>
탭 루트 4 + 인자 화면 4(경기 상세·팀 상세·선수단·선수 상세) + 설정 1입니다. <code>TeamRosterKey</code>와 <code>TeamDetailKey</code>를 <strong>따로</strong> 두는 이유는 태블릿 때문입니다(Step 9) — 팀 상세는 detail pane, 선수단은 그 안에서 다시 목록이라 <code>ListDetailSceneStrategy</code>가 둘을 구분해야 합니다. 같은 <code>teamId</code>를 실어도 키 타입이 다르면 back stack에서 별개 항목입니다.
</div>

<div class="callout tip"><span class="t"><code>@Serializable</code>이 필수인 이유</span>
<code>rememberNavBackStack</code>은 back stack을 직렬화해 <strong>프로세스 재생성까지</strong> 살립니다. 그래서 모든 키에 <code>@Serializable</code>이 필요하고, §4에서 <code>kotlin-serialization</code> 플러그인을 넣은 이유가 DTO만이 아닙니다. 인자 없는 화면은 <code>data object</code>로 두면 인스턴스가 하나라 비교가 공짜입니다.
</div>

## 10. 테마 Composable — 다크 기본 + 라이트

`core/designsystem/Theme.kt`:

```kotlin
package com.diamondscore.core.designsystem

import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider

@Composable
fun DiamondScoreTheme(dark: Boolean = true, content: @Composable () -> Unit) {
    val scheme = if (dark) DsDarkColors else DsLightColors
    CompositionLocalProvider(
        LocalDsExtras provides if (dark) DarkExtras else LightExtras,
        // M3 MaterialTheme은 기본 글자색을 주지 않는다(Surface·Scaffold만 준다). 없으면 색을 안 적은 Text·Icon이 검정이 된다
        LocalContentColor provides scheme.onBackground,
    ) {
        MaterialTheme(
            colorScheme = scheme,
            typography = DsTypography,
            content = content,
        )
    }
}
```

<div class="callout warn"><span class="t"><code>LocalContentColor</code> 줄을 빼면 다크에서 글자가 사라진다</span>
M3의 <code>MaterialTheme</code>은 색 스킴만 깔고 기본 글자색(<code>LocalContentColor</code>)은 건드리지 않습니다 — 그 값은 <code>Surface</code>·<code>Scaffold</code>가 줍니다. Step 5 Preview와 Step 6~8의 화면은 <code>Column.background(…)</code>만 쓰고 <code>Scaffold</code>는 Step 9에서야 들어오므로, 이 줄이 없으면 색을 적지 않은 <code>Text</code>·<code>Icon</code>이 기본값 <strong>검정</strong>으로 그려져 근블랙 배경에서 안 보입니다(화면 제목·날짜 바·팀명·순위 수치·뒤로 버튼 — 2026-09-23 실측). 라이트에선 검정이 우연히 읽혀서 놓치기 쉽습니다.
</div>

템플릿이 만든 `com.diamondscore.ui.theme` 패키지(`Color.kt`·`Theme.kt`·`Type.kt`)는 **통째로 삭제**합니다 —
같은 이름의 `DiamondScoreTheme`이 들어 있어 위 함수와 충돌합니다. `MainActivity`의 import를
`com.diamondscore.core.designsystem.DiamondScoreTheme`로 바꾸고, `setContent { }`를
`DiamondScoreTheme { … }`로 감쌉니다. `dark`는 Step 9 설정에서 DataStore 값으로 제어합니다(기본 다크).

## 11. 빌드 확인

```bash
./gradlew :app:assembleDebug
```

<div class="checkpoint"><span class="t"></span> <code>BUILD SUCCESSFUL</code>이 뜨고, ▶로 실행 시 배경이 <code>#07080B</code> 근블랙으로 칠해지면 디자인 시스템까지 완료. (컴포넌트는 Step 5에서 만듭니다) 템플릿 <code>MainActivity</code>의 <code>enableEdgeToEdge()</code>는 시스템 다크 모드를 따르므로, 시스템이 라이트면 이 시점엔 상태바 아이콘이 어둡게 그려져 잘 안 보입니다 — 앱 테마에 맞추는 코드는 Step 9 §1에서 넣습니다.</div>

<!-- appendix:compose-api -->
## 별첨 · Compose API 사용 목적

이 Step은 화면이 아니라 **디자인 시스템**(색·타이포·테마)과 내비게이션 키를 만듭니다. 여기서 정한 값을 Step 5~9의 모든 컴포저블이 읽습니다.

**테마·CompositionLocal**

| API | 이 Step에서의 사용 목적 |
|---|---|
| `MaterialTheme(colorScheme, typography, content)` | `DiamondScoreTheme` 안에서 앱 전체에 색 스킴(`DsDarkColors`/`DsLightColors`)과 `DsTypography`를 깐다. 이후 화면은 `MaterialTheme.colorScheme.*`·`MaterialTheme.typography.*`로 읽는다 |
| `darkColorScheme()` / `lightColorScheme()` | 목업의 다크(근블랙 `#07080B`)·라이트(페이퍼 `#FBFAF7`) 팔레트를 M3 역할(`background`·`surface`·`primary`…)에 매핑한다 |
| `staticCompositionLocalOf { … }` | M3 스킴에 없는 색(골드·승/패·오프라인 배너)을 담는 `LocalDsExtras`를 만든다. 테마 전환 때만 바뀌므로 읽는 쪽을 추적하지 않는 `static` 버전을 쓴다 |
| `CompositionLocalProvider(… provides …)` | `DiamondScoreTheme`에서 `LocalDsExtras`와 `LocalContentColor`에 다크/라이트 값을 공급한다 |
| `LocalContentColor` | 기본 글자·아이콘 색. M3 `MaterialTheme`은 이 값을 주지 않으므로(`Surface`·`Scaffold`만 준다) `onBackground`를 직접 공급해, 색을 적지 않은 `Text`·`Icon`이 다크에서 검정으로 사라지지 않게 한다 |
| `@Composable` | `DiamondScoreTheme`, `teamTint()`, `DsColors`의 getter를 컴포지션 안에서만 부를 수 있게 표시한다(`CompositionLocal.current`를 읽으려면 필요) |
| `@ReadOnlyComposable` | `DsColors.live`·`teamTint()`처럼 값을 **읽기만** 하는 컴포저블 getter에 붙여, 그룹 생성 비용 없이 호출되게 한다 |

**색·타이포**

| API | 이 Step에서의 사용 목적 |
|---|---|
| `Color(0xFF…)` | 팔레트 상수와 구단 컬러(`teamColor`)를 정의한다. 구단 컬러는 `core/designsystem`에만 두어 `data`가 Compose에 의존하지 않게 한다 |
| `Color.luminance()` | `teamTint()`가 현재 배경이 어두운지(`< 0.5f`) 판별해 팀 색을 밝히거나 누를 방향을 정한다 |
| `Color.toArgb()` | 팀 색을 `android.graphics.Color.colorToHSV`에 넘기려 ARGB `Int`로 바꾼다 |
| `Typography().copy(…)` | M3 기본 타입 스케일에서 뒤 Step이 실제로 쓰는 스타일(`titleMedium`·`bodyLarge`·`labelSmall`…)만 Archivo로 덮는다 |
| `TextStyle` | 스코어·섹션 헤더용 `Display`(Bebas)와 표 숫자용 `ScoreNumber`(등폭 `tnum`)를 정의한다 |
| `GoogleFont.Provider` / `GoogleFont` / `Font` / `FontFamily` | Bebas Neue·Archivo를 APK에 넣지 않고 Google Play 서비스에서 내려받아 `FontFamily`로 묶는다 |
| `FontWeight` | 같은 패밀리에서 Normal·Medium·Bold 굵기를 등록·선택한다 |
| `em` | `letterSpacing = 0.02.em`처럼 글자 크기에 비례하는 자간을 준다 |

**내비게이션**

| API | 이 Step에서의 사용 목적 |
|---|---|
| `NavKey` (Navigation 3 runtime) | 화면 목적지(`GamesKey`, `GameDetailKey(gameId)` …)를 `@Serializable` 타입으로 선언한다. Compose UI를 모르는 인터페이스라 `core/navigation`에 둘 수 있고, Step 9의 `rememberNavBackStack`이 이 직렬화로 back stack을 보존한다 |

<div class="pager">
<a href="#/labs/step-1">← Step 1</a>
<a href="#/labs/step-3">Step 3 · 네트워크·매핑 →</a>
</div>
