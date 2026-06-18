from __future__ import annotations

from .models import Capability


def default_capabilities() -> list[Capability]:
    return [
        Capability(
            id="music_creation.publish_work",
            mode="scenario",
            intent="publish_work",
            scenario_id="music_creation",
            scenario_intent="publish_work",
            keywords=("保存并发布", "发布作品", "发出去", "发布到作品页"),
            confidence=0.9,
            requires_confirmation=True,
        ),
        Capability(
            id="music_creation.revise_song",
            mode="scenario",
            intent="revise_song",
            scenario_id="music_creation",
            scenario_intent="revise_song",
            keywords=("副歌", "改成", "调整", "慢一点", "快一点", "重新唱", "修改"),
            confidence=0.84,
        ),
        Capability(
            id="native.open_page",
            mode="native_action",
            intent="open_page",
            keywords=("打开作品页", "去作品页", "查看作品", "打开创作页", "打开模板页"),
            confidence=0.85,
            arguments={"target": "work_detail"},
        ),
        Capability(
            id="music_creation.create_song",
            mode="scenario",
            intent="create_song",
            scenario_id="music_creation",
            scenario_intent="create_song",
            keywords=("做一首", "生成一首", "写一首", "创作一首", "来一首", "做歌", "写歌"),
            confidence=0.88,
        ),
        Capability(
            id="chat.general",
            mode="chat",
            intent="general",
            keywords=(),
            confidence=0.45,
        ),
    ]
