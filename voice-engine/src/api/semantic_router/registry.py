from __future__ import annotations

from ..configs.agent_profile_config import default_agent_profile_configs
from ..configs.capability_config import CapabilityConfig, default_capability_configs
from .models import Capability


def default_capabilities(agent_profile_id: str = "default") -> list[Capability]:
    configs = _capability_configs_for_agent(agent_profile_id)
    return [_to_capability(config) for config in configs]


def _capability_configs_for_agent(agent_profile_id: str) -> list[CapabilityConfig]:
    configs = default_capability_configs()
    agent_profiles = {profile.id: profile for profile in default_agent_profile_configs()}
    profile = agent_profiles.get(agent_profile_id) or agent_profiles["default"]
    enabled_ids = set(profile.enabled_capability_ids)

    return [config for config in configs if config.id in enabled_ids]


def _to_capability(config: CapabilityConfig) -> Capability:
    return Capability(
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
