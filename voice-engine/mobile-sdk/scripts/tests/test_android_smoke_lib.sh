#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
source "$repo_root/scripts/android-smoke-lib.sh"

assert_contains() {
  local dump="$1"
  local text="$2"

  if ! window_dump_contains_text "$dump" "$text"; then
    echo "Expected dump to contain: $text" >&2
    exit 1
  fi
}

assert_missing() {
  local dump="$1"
  local text="$2"

  if window_dump_contains_text "$dump" "$text"; then
    echo "Expected dump to miss: $text" >&2
    exit 1
  fi
}

home_dump='<node text="AI Engine" resource-id=""><node text="选择场景开始对话" resource-id="" /></node>'
scene_dump='<node text="陪伴语音体验台" resource-id=""><node text="结束通话" resource-id="" /></node>'
blank_dump='<node text="" resource-id="com.android.launcher3:id/workspace" />'
anr_dump='<node text="System UI isn&apos;t responding" resource-id="android:id/alertTitle" bounds="[138,901][942,975]" /><node text="Wait" resource-id="android:id/aerr_wait" bounds="[72,1148][1008,1280]" />'

assert_contains "$home_dump" "选择场景开始对话"
assert_contains "$scene_dump" "陪伴语音体验台"
assert_contains "$scene_dump" "结束通话"
assert_missing "$blank_dump" "选择场景开始对话"

wait_center="$(window_dump_center_for_text "$anr_dump" "Wait")"
if [[ "$wait_center" != "540 1214" ]]; then
  echo "Expected Wait center '540 1214', got: $wait_center" >&2
  exit 1
fi

fake_adb="$repo_root/tmp/fake-adb-pidof.sh"
mkdir -p "$(dirname "$fake_adb")"
cat >"$fake_adb" <<'FAKE_ADB'
#!/usr/bin/env bash
if [[ "$*" == *"pidof com.aiengine.ai"* ]]; then
  echo 12345
fi
FAKE_ADB
chmod +x "$fake_adb"

pid="$(wait_for_process "$fake_adb" emulator-test com.aiengine.ai 1)"
if [[ "$pid" != "12345" ]]; then
  echo "Expected fake pid 12345, got: $pid" >&2
  exit 1
fi
