#!/usr/bin/env bash

window_dump_contains_text() {
  local dump="$1"
  local text="$2"

  [[ "$dump" == *"$text"* ]]
}

window_dump_center_for_text() {
  local dump="$1"
  local text="$2"
  local node=""
  local bounds=""

  node="$(printf '%s\n' "$dump" | tr '<' '\n' | grep -F "text=\"$text\"" | head -1 || true)"
  if [[ -z "$node" ]]; then
    return 1
  fi

  bounds="$(printf '%s\n' "$node" | sed -n 's/.*bounds="\[\([0-9][0-9]*\),\([0-9][0-9]*\)\]\[\([0-9][0-9]*\),\([0-9][0-9]*\)\]".*/\1 \2 \3 \4/p')"
  if [[ -z "$bounds" ]]; then
    return 1
  fi

  read -r left top right bottom <<<"$bounds"
  echo "$(((left + right) / 2)) $(((top + bottom) / 2))"
}

adb_shell() {
  local adb_bin="$1"
  local serial="$2"
  local timeout_seconds="${ADB_SHELL_TIMEOUT_SECONDS:-5}"
  shift 2

  command_with_timeout "$timeout_seconds" "$adb_bin" -s "$serial" shell "$@"
}

adb_shell_with_timeout() {
  local adb_bin="$1"
  local serial="$2"
  local timeout_seconds="$3"
  shift 3

  command_with_timeout "$timeout_seconds" "$adb_bin" -s "$serial" shell "$@"
}

command_with_timeout() {
  local timeout_seconds="$1"
  shift

  "$@" &
  local command_pid=$!
  local elapsed=0

  while kill -0 "$command_pid" >/dev/null 2>&1; do
    if (( elapsed >= timeout_seconds )); then
      kill "$command_pid" >/dev/null 2>&1 || true
      wait "$command_pid" 2>/dev/null || true
      return 124
    fi

    sleep 1
    elapsed=$((elapsed + 1))
  done

  wait "$command_pid"
}

dump_window_xml() {
  local adb_bin="$1"
  local serial="$2"

  adb_shell "$adb_bin" "$serial" uiautomator dump /sdcard/window.xml >/dev/null 2>&1
  adb_shell "$adb_bin" "$serial" cat /sdcard/window.xml 2>/dev/null | tr -d '\r'
}

wait_for_window_text() {
  local adb_bin="$1"
  local serial="$2"
  local timeout_seconds="$3"
  local label="$4"
  shift 4

  local end_time=$((SECONDS + timeout_seconds))
  local dump=""

  while (( SECONDS < end_time )); do
    dump="$(dump_window_xml "$adb_bin" "$serial" || true)"
    if window_dump_contains_text "$dump" "isn't responding"; then
      center="$(window_dump_center_for_text "$dump" "Wait" || true)"
      if [[ -n "$center" ]]; then
        read -r x y <<<"$center"
        adb_shell "$adb_bin" "$serial" input tap "$x" "$y" || true
        sleep 3
        continue
      fi
    fi

    for text in "$@"; do
      if window_dump_contains_text "$dump" "$text"; then
        return 0
      fi
    done
    sleep 1
  done

  echo "Timed out waiting for $label. Expected one of: $*" >&2
  if [[ -n "$dump" ]]; then
    echo "$dump" >&2
  fi
  return 1
}

wait_for_webview() {
  local adb_bin="$1"
  local serial="$2"
  local timeout_seconds="$3"
  local end_time=$((SECONDS + timeout_seconds))
  local dump=""

  while (( SECONDS < end_time )); do
    dump="$(dump_window_xml "$adb_bin" "$serial" || true)"
    if window_dump_contains_text "$dump" "isn't responding"; then
      center="$(window_dump_center_for_text "$dump" "Wait" || true)"
      if [[ -n "$center" ]]; then
        read -r x y <<<"$center"
        adb_shell "$adb_bin" "$serial" input tap "$x" "$y" || true
      fi
      sleep 3
      continue
    fi

    if window_dump_contains_text "$dump" "android.webkit.WebView"; then
      return 0
    fi
    sleep 1
  done

  echo "Timed out waiting for foreground WebView." >&2
  if [[ -n "$dump" ]]; then
    echo "$dump" >&2
  fi
  return 1
}

wait_for_nonblank_screenshot() {
  local adb_bin="$1"
  local serial="$2"
  local output_path="$3"
  local timeout_seconds="$4"
  local min_non_white_ratio="${5:-0.02}"
  local checker_path="$6"
  local end_time=$((SECONDS + timeout_seconds))

  while (( SECONDS < end_time )); do
    "$adb_bin" -s "$serial" exec-out screencap -p >"$output_path"
    if node "$checker_path" "$output_path" "$min_non_white_ratio"; then
      return 0
    fi
    sleep 2
  done

  echo "Timed out waiting for nonblank screenshot: $output_path" >&2
  return 1
}

wait_for_process() {
  local adb_bin="$1"
  local serial="$2"
  local package_name="$3"
  local timeout_seconds="$4"

  local end_time=$((SECONDS + timeout_seconds))
  local pid=""

  while (( SECONDS < end_time )); do
    pid="$(adb_shell "$adb_bin" "$serial" pidof "$package_name" 2>/dev/null | tr -d '\r' || true)"
    if [[ -n "$pid" ]]; then
      echo "$pid"
      return 0
    fi
    sleep 1
  done

  echo "Timed out waiting for process: $package_name" >&2
  return 1
}

dismiss_system_wait_dialog() {
  local adb_bin="$1"
  local serial="$2"
  local dump=""
  local center=""

  dump="$(dump_window_xml "$adb_bin" "$serial" || true)"
  if ! window_dump_contains_text "$dump" "isn't responding"; then
    return 0
  fi

  center="$(window_dump_center_for_text "$dump" "Wait" || true)"
  if [[ -z "$center" ]]; then
    return 1
  fi

  read -r x y <<<"$center"
  adb_shell "$adb_bin" "$serial" input tap "$x" "$y"
}
