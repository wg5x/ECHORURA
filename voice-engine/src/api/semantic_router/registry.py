from __future__ import annotations

from ..configs.capability_config import default_capability_configs
from .models import Capability


def default_capabilities() -> list[Capability]:
    return [
        Capability(
            id=config.id,
            mode=config.mode,
            intent=config.intent,
            keywords=config.keywords,
            confidence=config.confidence,
            scenario_id=config.scenario_id,
            scenario_intent=config.scenario_intent,
            requires_confirmation=config.requires_confirmation,
            arguments=config.arguments,
        )
        for config in default_capability_configs()
    ]
