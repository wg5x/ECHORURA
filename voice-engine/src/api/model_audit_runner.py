from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Protocol

from .config import load_local_env
from .memory_eval_runner import default_eval_cases_path as default_memory_cases_path
from .memory_eval_runner import load_eval_cases as load_memory_eval_cases
from .semantic_router.eval_runner import default_eval_cases_path as default_router_cases_path
from .semantic_router.eval_runner import load_eval_cases as load_router_eval_cases
from .semantic_router.policy_guard import enforce_route_policy


DEFAULT_MODEL_AUDIT_BASE_URL = "https://apihub.agnes-ai.com/v1"
DEFAULT_MODEL_AUDIT_MODEL = "agnes-2.0-flash"


class JsonModelClient(Protocol):
    def complete_json(self, prompt: str) -> dict:
        ...


class OpenAICompatibleJsonClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        max_attempts: int = 3,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.max_attempts = max(1, max_attempts)
        self.retry_delay_seconds = retry_delay_seconds

    @classmethod
    def from_env(cls) -> "OpenAICompatibleJsonClient":
        load_local_env()
        base_url = os.environ.get("MODEL_AUDIT_BASE_URL", DEFAULT_MODEL_AUDIT_BASE_URL).strip()
        api_key = os.environ.get("MODEL_AUDIT_API_KEY", "").strip()
        model = os.environ.get("MODEL_AUDIT_MODEL", DEFAULT_MODEL_AUDIT_MODEL).strip()
        if not api_key:
            raise RuntimeError("MODEL_AUDIT_API_KEY is required.")
        return cls(base_url=base_url, api_key=api_key, model=model)

    def complete_json(self, prompt: str) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Return only one valid JSON object. Do not include markdown or prose.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        for attempt in range(self.max_attempts):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    body = json.loads(response.read().decode("utf-8"))
                break
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                if attempt + 1 >= self.max_attempts or not _is_retryable_request_error(error):
                    raise
                if self.retry_delay_seconds > 0:
                    time.sleep(self.retry_delay_seconds * (attempt + 1))
        content = body["choices"][0]["message"]["content"]
        return _parse_json_object_from_text(content)


def generate_router_model_decisions(
    cases,
    client: JsonModelClient,
    out_path: Path,
    limit: int | None = None,
    workers: int = 1,
) -> Path:
    selected_cases = cases[:limit] if limit else cases
    records = _run_cases(selected_cases, lambda case: _router_record(case, client), workers)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    return out_path


def generate_memory_model_memories(
    cases,
    client: JsonModelClient,
    out_path: Path,
    limit: int | None = None,
    workers: int = 1,
) -> Path:
    selected_cases = cases[:limit] if limit else cases
    records = _run_cases(selected_cases, lambda case: _memory_record(case, client), workers)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    return out_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate offline model labels for rule audit eval cases.")
    parser.add_argument("--kind", choices=("router", "memory", "both"), default="both")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args(argv)

    client = OpenAICompatibleJsonClient.from_env()
    outputs: dict[str, str] = {}
    if args.kind in {"router", "both"}:
        outputs["router_model_decisions"] = str(
            generate_router_model_decisions(
                load_router_eval_cases(default_router_cases_path()),
                client,
                args.out_dir / "router_model_decisions.jsonl",
                limit=args.limit,
                workers=args.workers,
            )
        )
    if args.kind in {"memory", "both"}:
        outputs["memory_model_memories"] = str(
            generate_memory_model_memories(
                load_memory_eval_cases(default_memory_cases_path()),
                client,
                args.out_dir / "memory_model_memories.jsonl",
                limit=args.limit,
                workers=args.workers,
            )
        )
    print(json.dumps(outputs, ensure_ascii=False, indent=2))


def _router_prompt(case) -> str:
    return (
        "Label this voice command for semantic routing.\n"
        "Choose exactly one route from this closed catalog and return only JSON with mode and intent. "
        "Do not invent labels. Do not add entities or explanations.\n"
        "Closed catalog:\n"
        '- {"mode":"chat","intent":"general"} for ordinary chat, weather, questions, or unsupported requests.\n'
        '- {"mode":"native_action","intent":"phone.dial"} for phone calls.\n'
        '- {"mode":"native_action","intent":"sms.compose"} for SMS/messages.\n'
        '- {"mode":"native_action","intent":"calendar.create_event"} for creating calendar events/reminders. '
        "Do not use scenario for Android phone actions.\n"
        '- {"mode":"native_action","intent":"app.open"} for opening apps.\n'
        '- {"mode":"native_action","intent":"app.search"} for app search requests.\n'
        '- {"mode":"native_action","intent":"app.open_deep_link"} for deep app actions such as WeChat message.\n'
        '- {"mode":"native_action","intent":"browser.open_url"} for URLs.\n'
        '- {"mode":"native_action","intent":"gallery.pick_image"} for selecting images or opening gallery/album. '
        "Do not use app.open for gallery or album.\n"
        '- {"mode":"native_action","intent":"media.play_from_search"} for playing/searching audio or video.\n'
        '- {"mode":"native_action","intent":"settings.open_wifi"} for Wi-Fi settings.\n'
        '- {"mode":"native_action","intent":"camera.capture_photo"} for photos.\n'
        '- {"mode":"native_action","intent":"camera.capture_video"} for videos.\n'
        '- {"mode":"native_action","intent":"open_page"} for opening local product pages such as work, creation, or templates.\n'
        '- {"mode":"server_action","intent":"memory.preference.update"} only for explicit remember/update preference requests.\n'
        '- {"mode":"scenario","intent":"create_song","scenario_id":"music_creation","scenario_intent":"create_song"} for music creation.\n'
        '- {"mode":"scenario","intent":"revise_song","scenario_id":"music_creation","scenario_intent":"revise_song"} for music revision.\n'
        '- {"mode":"scenario","intent":"publish_work","scenario_id":"music_creation","scenario_intent":"publish_work"} for publishing work.\n'
        "Profile boundaries:\n"
        "default profile supports only chat.general, native_action open_page, and music_creation scenarios. "
        "Phone/system intents outside this profile must use chat/general.\n"
        "phone-assistant profile supports only chat.general, native_action phone/calendar/app/browser/gallery/media/settings/camera/open_page, "
        "and server_action memory.preference.update. Music creation scenarios outside this profile must use chat/general.\n"
        "Disambiguation examples:\n"
        "发短信, 发信息, 发消息, 短信通知, 发信息告诉他... => sms.compose, not chat/general.\n"
        "淘宝搜索, 京东搜索, 打开京东搜索 => app.search, not app.open_deep_link.\n"
        "打开淘宝 => app.open, not app.search.\n"
        "发微信给...说... => app.open_deep_link, not chat/general.\n"
        "看电影, 看视频, 播放音乐, 听歌 => media.play_from_search, not chat/general.\n"
        "For default profile music creation, 帮我做一首下班路上听的中文 LoFi => create_song.\n"
        "For default profile music publishing, 发出去 => publish_work.\n"
        f"agent_profile_id: {case.agent_profile_id}\n"
        f"text: {case.text}"
    )


def _memory_prompt(case) -> str:
    return (
        "Extract durable long-term user memories from this transcript.\n"
        "Return only JSON: {\"memories\":[{\"type\":\"preference\",\"content\":\"...\",\"confidence\":0.0}]}.\n"
        "Only extract memory when the user explicitly asks to remember, update a preference, or avoid something later. "
        "Explicit triggers include 记住, 请你记住, 以后你要记得, 我的偏好是, 不要再, 别再, 以后不要, 以后别. "
        "Implicit likes or dislikes such as 我喜欢女声 or 我不喜欢男声 are ordinary chat; return {\"memories\":[]} for them.\n"
        "Examples:\n"
        "- 记住我喜欢女声 => {\"memories\":[{\"type\":\"preference\",\"content\":\"我喜欢女声\"}]}\n"
        "- 我喜欢女声 => {\"memories\":[]}\n"
        "content must be copied verbatim from the user's Chinese phrase whenever possible. "
        "Do not translate, explain, add parentheses, or rewrite into third person. "
        "Keep polarity: 喜欢, 不喜欢, 讨厌, 不要, 别再. "
        "If there is no durable memory, return {\"memories\":[]}.\n"
        f"agent_profile_id: {case.agent_profile_id}\n"
        f"transcript: {json.dumps(case.transcript, ensure_ascii=False)}"
    )


def _router_record(case, client: JsonModelClient) -> dict:
    raw_decision = client.complete_json(_router_prompt(case))
    decision = enforce_route_policy(
        _with_route_metadata(raw_decision, case),
        text=case.text,
        agent_profile_id=case.agent_profile_id,
    )
    return {
        "case_id": case.id,
        "raw_decision": {
            key: raw_decision[key]
            for key in ("mode", "intent", "scenario_id", "scenario_intent")
            if key in raw_decision
        },
        "decision": {
            key: decision[key]
            for key in ("mode", "intent", "scenario_id", "scenario_intent")
            if key in decision
        },
    }


def _memory_record(case, client: JsonModelClient) -> dict:
    response = client.complete_json(_memory_prompt(case))
    memories = response.get("memories") if isinstance(response.get("memories"), list) else []
    return {
        "case_id": case.id,
        "memories": [memory for memory in memories if isinstance(memory, dict)],
    }


def _with_route_metadata(decision: dict, case) -> dict:
    return {
        "type": "route_decision",
        "session_id": "model-audit",
        "turn_id": case.id,
        "agent_profile_id": case.agent_profile_id,
        "confidence": 0.0,
        "need_clarification": False,
        "requires_confirmation": False,
        "arguments": {},
        **decision,
    }


def _run_cases(cases, run_case, workers: int) -> list[dict]:
    if workers <= 1:
        return [run_case(case) for case in cases]
    results: list[dict | None] = [None] * len(cases)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_index = {executor.submit(run_case, case): index for index, case in enumerate(cases)}
        for future in concurrent.futures.as_completed(future_to_index):
            results[future_to_index[future]] = future.result()
    return [result for result in results if result is not None]


def _is_retryable_request_error(error: BaseException) -> bool:
    if isinstance(error, urllib.error.HTTPError):
        return error.code in {408, 409, 425, 429, 500, 502, 503, 504}
    return isinstance(error, (urllib.error.URLError, TimeoutError, OSError))


def _parse_json_object_from_text(text: str) -> dict:
    text = str(text or "").strip()
    if not text:
        raise ValueError("Model response content is empty.")
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("Model response must contain one JSON object.")


if __name__ == "__main__":
    main()
