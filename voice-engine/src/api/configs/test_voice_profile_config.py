import unittest
from typing import Any

from .voice_profile_config import (
    DEFAULT_O2_SPEAKER,
    DEFAULT_SC2_SPEAKER,
    O2_SPEAKERS,
    SC2_SPEAKERS,
    default_realtime_config,
    default_voice_profile_configs,
)


FORBIDDEN_BRAND = "echo" + "rura"


def _string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [entry for item in value.values() for entry in _string_values(item)]
    if isinstance(value, (list, tuple)):
        return [entry for item in value for entry in _string_values(item)]
    return []


class VoiceProfileConfigTest(unittest.TestCase):
    def test_default_profiles_include_current_frontend_profiles(self) -> None:
        profiles = default_voice_profile_configs()
        profile_ids = {profile.id for profile in profiles}

        self.assertIn("default", profile_ids)
        self.assertIn("short-latency", profile_ids)
        self.assertIn("music-test", profile_ids)

    def test_default_profile_ids_are_unique(self) -> None:
        profiles = default_voice_profile_configs()
        profile_ids = [profile.id for profile in profiles]

        self.assertEqual(len(profile_ids), len(set(profile_ids)))

    def test_default_speakers_are_in_allowlists(self) -> None:
        self.assertIn(DEFAULT_O2_SPEAKER, O2_SPEAKERS)
        self.assertIn(DEFAULT_SC2_SPEAKER, SC2_SPEAKERS)

    def test_default_realtime_config_uses_default_voice_profile(self) -> None:
        config = default_realtime_config()

        self.assertEqual(config["mode"], "o2")
        self.assertEqual(config["speaker"], DEFAULT_O2_SPEAKER)
        self.assertEqual(config["botName"], "语音助手")
        self.assertTrue(config["enableWebSearch"])
        self.assertTrue(config["enableMusic"])

    def test_default_voice_profiles_do_not_use_project_brand_name(self) -> None:
        values = _string_values(default_realtime_config())
        for profile in default_voice_profile_configs():
            values.extend(_string_values(profile.id))
            values.extend(_string_values(profile.name))
            values.extend(_string_values(profile.description))
            values.extend(_string_values(profile.config))

        self.assertTrue(all(FORBIDDEN_BRAND not in value.lower() for value in values))


if __name__ == "__main__":
    unittest.main()
