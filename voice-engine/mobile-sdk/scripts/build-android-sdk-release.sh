#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../apps/android"

./gradlew \
  :sdk:testDebugUnitTest \
  :sdk:assembleRelease \
  :sdk:publishReleasePublicationToLocalSdkRepository \
  :samples:host-app:assembleDebug
