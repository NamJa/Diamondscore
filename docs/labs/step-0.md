# Step 0 · 개발 환경 준비

<div class="chips"><span class="chip time">30분</span><span class="chip diff">쉬움</span><span class="chip goal">빈 앱을 실기기/에뮬레이터에 띄운다</span></div>

코드를 쓰기 전에 도구부터 갖춥니다. 이 Step이 끝나면 **Android Studio에서 빈 앱을 실행**하고, **터미널에서 `adb`로 기기를 인식**할 수 있습니다.

## 1. Android Studio 설치

1. [developer.android.com/studio](https://developer.android.com/studio) 에서 최신 Android Studio를 내려받아 설치합니다.
2. 첫 실행 시 **SDK 설정 마법사**가 뜹니다. 그대로 진행하되, 다음이 포함됐는지 확인합니다.
   - **Android SDK Platform 36** (Android 16)
   - **Android SDK Build-Tools**
   - **Android Emulator** + **Android SDK Platform-Tools**

설치가 끝나면 SDK 위치를 확인해 둡니다(보통 macOS `~/Library/Android/sdk`).

<div class="callout tip"><span class="t">JDK</span>
Android Studio에는 JDK가 내장(JBR 17+)돼 있어 따로 설치하지 않아도 됩니다. 이 프로젝트는 <strong>JDK 17 toolchain</strong>을 씁니다.
</div>

## 2. 터미널에서 adb 잡기

`adb`(Android Debug Bridge)를 PATH에 추가하면 터미널에서 기기를 다룰 수 있습니다.

```bash
# macOS / zsh — ~/.zshrc 에 추가
echo 'export PATH="$PATH:$HOME/Library/Android/sdk/platform-tools"' >> ~/.zshrc
source ~/.zshrc

# 확인
adb version
```

<div class="checkpoint"><span class="t"></span> <code>adb version</code>이 <code>Android Debug Bridge version ...</code>을 출력하면 성공.</div>

## 3. 실행할 기기 준비 (둘 중 하나)

**A. 에뮬레이터** — Android Studio → **Device Manager** → `Create Device` → Pixel 계열 선택 → 시스템 이미지 **API 36** 다운로드 → Finish → ▶로 부팅.

**B. 실기기** — USB 연결 후 기기에서 개발자 옵션·USB 디버깅을 켭니다(설정 → 휴대전화 정보 → 빌드번호 7번 탭 → 개발자 옵션 → USB 디버깅).

```bash
adb devices          # 연결 확인
```

<div class="checkpoint"><span class="t"></span> <code>adb devices</code> 목록에 기기가 <code>device</code> 상태로 보이면 성공. <code>unauthorized</code>면 기기 화면의 디버깅 허용 팝업을 수락하세요.</div>

## 4. 빈 프로젝트로 실행 리허설

1. Android Studio → **New Project** → **Empty Activity (Compose)** 선택.
2. 이름은 아무거나(예: `Sandbox`), 나머지 기본값으로 Finish.
3. 상단 초록 ▶(Run) 클릭 → 위에서 준비한 기기 선택.

<div class="checkpoint"><span class="t"></span> 기기에 "Hello Android!" 화면이 뜨면 환경 준비 완료. 이 Sandbox 프로젝트는 리허설용이므로 지워도 됩니다 — 실제 프로젝트는 <a href="#/labs/step-2">Step 2</a>에서 새로 만듭니다.</div>

<div class="callout ok"><span class="t">정리</span>
Android Studio·SDK 36·adb·실행 기기가 준비됐습니다. 이제 코드를 쓸 수 있는 상태입니다.
</div>

<div class="pager">
<a href="#/">← 소개</a>
<a href="#/labs/step-1">Step 1 · API 스파이크 →</a>
</div>
