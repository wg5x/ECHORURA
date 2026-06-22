#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

token="${FIR_API_TOKEN:-${API_TOKEN:-}}"
if [[ -z "$token" ]]; then
  echo "Missing FIR_API_TOKEN or API_TOKEN." >&2
  echo "Create an API token in betaqr/fir.im, then run:" >&2
  echo "  FIR_API_TOKEN=xxx ./scripts/publish-android-betaqr.sh" >&2
  exit 1
fi

apk_path="${1:-}"
if [[ -z "$apk_path" ]]; then
  if [[ -x apps/android/gradlew ]]; then
    (cd apps/android && ./gradlew assembleDebug)
  elif command -v gradle >/dev/null 2>&1; then
    (cd apps/android && gradle assembleDebug)
  else
    echo "Cannot build APK: Gradle is not available." >&2
    echo "Open apps/android in Android Studio once, or install Gradle/Android SDK, then retry." >&2
    echo "You can also pass an existing APK path:" >&2
    echo "  FIR_API_TOKEN=xxx ./scripts/publish-android-betaqr.sh path/to/app.apk" >&2
    exit 1
  fi

  apk_path="apps/android/app/build/outputs/apk/debug/app-debug.apk"
fi

if [[ ! -f "$apk_path" ]]; then
  echo "APK not found: $apk_path" >&2
  exit 1
fi

changelog="${BETAQR_CHANGELOG:-Android debug build}"

sdk_root="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Library/Android/sdk}}"
aapt="${AAPT:-}"
if [[ -z "$aapt" ]]; then
  aapt="$(find "$sdk_root/build-tools" -type f -name aapt 2>/dev/null | sort | tail -n 1 || true)"
fi

if [[ -z "$aapt" || ! -x "$aapt" ]]; then
  echo "Cannot inspect APK: aapt is not available." >&2
  echo "Set ANDROID_HOME or AAPT, then retry." >&2
  exit 1
fi

BETAQR_API_TOKEN="$token" \
BETAQR_APK_PATH="$apk_path" \
BETAQR_AAPT="$aapt" \
BETAQR_CHANGELOG="$changelog" \
python3 - <<'PY'
import json
import os
import re
import subprocess
import sys

api_token = os.environ["BETAQR_API_TOKEN"]
apk_path = os.environ["BETAQR_APK_PATH"]
aapt = os.environ["BETAQR_AAPT"]
changelog = os.environ["BETAQR_CHANGELOG"]

badging = subprocess.check_output([aapt, "dump", "badging", apk_path], text=True)
first_line = badging.splitlines()[0]
package = re.search(r"name='([^']+)'", first_line).group(1)
version_code = re.search(r"versionCode='([^']+)'", first_line).group(1)
version_name = re.search(r"versionName='([^']+)'", first_line).group(1)
label_match = re.search(r"application-label:'([^']+)'", badging)
name = os.environ.get("BETAQR_APP_NAME") or (label_match.group(1) if label_match else package)

create_payload = json.dumps({
    "type": "android",
    "bundle_id": package,
    "api_token": api_token,
}).encode()
create = subprocess.run([
    "curl", "-sS", "-X", "POST", "https://api.bq04.com/apps",
    "-H", "Content-Type: application/json",
    "--data-binary", "@-",
], input=create_payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if create.returncode != 0:
    sys.stderr.write(create.stderr.decode())
    raise SystemExit(create.returncode)

data = json.loads(create.stdout.decode())
if "cert" not in data:
    print(json.dumps(data, ensure_ascii=False, indent=2), file=sys.stderr)
    raise SystemExit("Create upload response has no cert field")

binary = data["cert"]["binary"]
short = data.get("short") or data.get("short_url") or data.get("app", {}).get("short") or ""

upload = subprocess.run([
    "curl", "-sS", "-X", "POST", binary["upload_url"],
    "-F", f"key={binary['key']}",
    "-F", f"token={binary['token']}",
    "-F", f"file=@{apk_path}",
    "-F", f"x:name={name}",
    "-F", f"x:version={version_name}",
    "-F", f"x:build={version_code}",
    "-F", "x:release_type=Adhoc",
    "-F", f"x:changelog={changelog}",
], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if upload.returncode != 0:
    sys.stderr.write(upload.stderr.decode())
    raise SystemExit(upload.returncode)

print(f"Uploaded {name} {version_name} ({version_code})")
if short:
    print(f"Install page: https://www.betaqr.com.cn/{short}")
    print(f"Mirror page: https://fir.im/{short}")
else:
    print(upload.stdout.decode())
PY
