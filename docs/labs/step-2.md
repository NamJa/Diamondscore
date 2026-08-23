# Step 2 · 프로젝트 부트스트랩

<div class="chips"><span class="chip time">40분</span><span class="chip diff">쉬움</span><span class="chip goal">DiamondScore 프로젝트에 의존성·테마·팀 리소스를 세운다</span></div>

실제 프로젝트를 만들고 Kotlin 2.4 / Compose / Retrofit 3 / Room / Hilt / Coil 3를 version catalog로 고정합니다.

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

## 6. 10개 구단 리소스 (한국어 이름 + 팀 컬러)

API는 한국어 팀명을 주지 않고, `teamColors`가 전 구단 동일합니다. 그래서 **앱에 직접** 넣습니다.

`app/src/main/java/com/diamondscore/core/designsystem/KboTeams.kt`:

```kotlin
package com.diamondscore.core.designsystem

import androidx.compose.ui.graphics.Color

data class KboTeam(val id: Long, val nameKo: String, val color: Color)

val KBO_TEAMS: Map<Long, KboTeam> = listOf(
    KboTeam(188409, "KT 위즈",     Color(0xFF000000)),
    KboTeam(188245, "삼성 라이온즈", Color(0xFF074CA1)),
    KboTeam(188257, "LG 트윈스",    Color(0xFFC30452)),
    KboTeam(188248, "두산 베어스",  Color(0xFF131230)),
    KboTeam(188247, "KIA 타이거즈", Color(0xFFEA0029)),
    KboTeam(188243, "한화 이글스",  Color(0xFFFC4E00)),
    KboTeam(188253, "NC 다이노스",  Color(0xFF315288)),
    KboTeam(188246, "롯데 자이언츠", Color(0xFF041E42)),
    KboTeam(188244, "SSG 랜더스",   Color(0xFFCE0E2D)),
    KboTeam(188258, "키움 히어로즈", Color(0xFF570514)),
).associateBy { it.id }

fun teamNameKo(id: Long, fallback: String): String = KBO_TEAMS[id]?.nameKo ?: fallback
```

<div class="callout tip"><span class="t">팀 컬러는 예시</span>
위 색은 구단 상징색 예시입니다. 원하는 값으로 조정하세요. 핵심은 API의 <code>teamColors</code>(전부 동일)를 쓰지 않고 자체 정의한다는 점입니다.
</div>

## 7. 빌드 확인

```bash
./gradlew :app:assembleDebug
```

<div class="checkpoint"><span class="t"></span> <code>BUILD SUCCESSFUL</code>이 뜨고, ▶로 실행했을 때 빈 화면이 기기에 뜨면 부트스트랩 완료.</div>

<div class="pager">
<a href="#/labs/step-1">← Step 1</a>
<a href="#/labs/step-3">Step 3 · 네트워크·매핑 →</a>
</div>
