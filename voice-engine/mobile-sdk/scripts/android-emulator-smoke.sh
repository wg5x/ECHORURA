#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

repo_root="$(pwd)"
source "$repo_root/scripts/android-smoke-lib.sh"

android_dir="$repo_root/apps/android"
png_checker="$repo_root/scripts/check-png-nonblank.mjs"
png_diff_checker="$repo_root/scripts/check-png-different.mjs"
artifact_dir="$repo_root/tmp/android-smoke"
mkdir -p "$artifact_dir"

jbr_home_default="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
if [[ -z "${JAVA_HOME:-}" && -d "$jbr_home_default" ]]; then
  export JAVA_HOME="$jbr_home_default"
fi

export ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-$HOME/Library/Android/sdk}}"
adb_bin="$ANDROID_SDK_ROOT/platform-tools/adb"
emulator_bin="$ANDROID_SDK_ROOT/emulator/emulator"
avdmanager_bin="$ANDROID_SDK_ROOT/cmdline-tools/latest/bin/avdmanager"

if [[ ! -x "$adb_bin" || ! -x "$emulator_bin" || ! -x "$avdmanager_bin" ]]; then
  echo "Android SDK tools are missing. Check ANDROID_SDK_ROOT=$ANDROID_SDK_ROOT" >&2
  exit 1
fi

avd_name="${AVD_NAME:-codex_ai_engine_api29_clean}"
avd_package="${AVD_PACKAGE:-system-images;android-29;google_apis;x86_64}"
avd_device="${AVD_DEVICE:-pixel_3a}"
emulator_port="${EMULATOR_PORT:-5560}"
emulator_serial="emulator-${emulator_port}"
apk_path="$android_dir/app/build/outputs/apk/debug/app-debug.apk"
screenshot_home="$artifact_dir/android-home.png"
screenshot_scene="$artifact_dir/android-scene.png"
emulator_log="$artifact_dir/emulator.log"
rm -f "$screenshot_home" "$screenshot_scene"

cleanup() {
  if [[ "${KEEP_EMULATOR_RUNNING:-0}" == "1" ]]; then
    return
  fi

  if "$adb_bin" -s "$emulator_serial" get-state >/dev/null 2>&1; then
    "$adb_bin" -s "$emulator_serial" emu kill >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "==> Building SDK and demo APK"
(
  cd "$android_dir"
  ./gradlew :sdk:testDebugUnitTest :sdk:assembleDebug :app:assembleDebug >/dev/null
)

if [[ ! -f "$apk_path" ]]; then
  echo "APK not found after build: $apk_path" >&2
  exit 1
fi

if [[ ! -d "$HOME/.android/avd/${avd_name}.avd" ]]; then
  echo "==> Creating AVD $avd_name"
  printf 'no\n' | "$avdmanager_bin" create avd -n "$avd_name" -k "$avd_package" -d "$avd_device" --force >/dev/null
fi

echo "==> Starting emulator $avd_name on port $emulator_port"
"$emulator_bin" \
  -avd "$avd_name" \
  -port "$emulator_port" \
  -no-snapshot-load \
  -no-snapshot-save \
  -no-audio \
  -gpu swiftshader_indirect \
  >"$emulator_log" 2>&1 &

echo "==> Waiting for adb device"
"$adb_bin" -s "$emulator_serial" wait-for-device

boot_ok=""
for _ in $(seq 1 120); do
  state="$("$adb_bin" -s "$emulator_serial" get-state 2>/dev/null || true)"
  if [[ "$state" != "device" ]]; then
    sleep 1
    continue
  fi

  boot_value="$(adb_shell "$adb_bin" "$emulator_serial" getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
  bootanim_value="$(adb_shell "$adb_bin" "$emulator_serial" getprop init.svc.bootanim 2>/dev/null | tr -d '\r' || true)"
  if [[ "$boot_value" == "1" && "$bootanim_value" == "stopped" ]]; then
    boot_ok="1"
    break
  fi
  sleep 1
done

if [[ "$boot_ok" != "1" ]]; then
  echo "Emulator failed to reach boot_completed=1" >&2
  echo "See emulator log: $emulator_log" >&2
  exit 1
fi

# Cold-booted AVDs often report boot completed before WebView/network is ready.
sleep 15
dismiss_system_wait_dialog "$adb_bin" "$emulator_serial" || true

echo "==> Installing APK"
"$adb_bin" -s "$emulator_serial" install -r "$apk_path" >/dev/null

echo "==> Clearing app data for deterministic launch"
adb_shell_with_timeout "$adb_bin" "$emulator_serial" 30 pm clear com.aiengine.ai >/dev/null

echo "==> Launching app"
adb_shell_with_timeout "$adb_bin" "$emulator_serial" 30 monkey -p com.aiengine.ai -c android.intent.category.LAUNCHER 1 >/dev/null
dismiss_system_wait_dialog "$adb_bin" "$emulator_serial" || true

pid="$(wait_for_process "$adb_bin" "$emulator_serial" com.aiengine.ai 20)"

echo "==> Waiting for WebView"
wait_for_webview "$adb_bin" "$emulator_serial" 45

echo "==> Capturing home screenshot"
wait_for_nonblank_screenshot "$adb_bin" "$emulator_serial" "$screenshot_home" 45 0.02 "$png_checker"

echo "==> Opening first scene list"
adb_shell_with_timeout "$adb_bin" "$emulator_serial" 30 input tap 530 1450

echo "==> Capturing scene screenshot"
wait_for_nonblank_screenshot "$adb_bin" "$emulator_serial" "$screenshot_scene" 30 0.02 "$png_checker"
node "$png_diff_checker" "$screenshot_home" "$screenshot_scene" 0.01

echo "Smoke test complete."
echo "PID: $pid"
echo "APK: $apk_path"
echo "SDK AAR: $android_dir/sdk/build/outputs/aar/sdk-debug.aar"
echo "Home screenshot: $screenshot_home"
echo "Scene screenshot: $screenshot_scene"
echo "Emulator log: $emulator_log"
