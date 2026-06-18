import unittest

from .voice_profile_config import (
    DEFAULT_O2_SPEAKER,
    DEFAULT_SC2_SPEAKER,
    O2_SPEAKERS,
    SC2_SPEAKERS,
    default_realtime_config,
    default_voice_profile_configs,
)


class VoiceProfileConfigTest(unittest.TestCase):
    def test_default_profiles_include_current_frontend_profiles(self) -> None:
        profiles = default_voice_profile_configs()
        profile_ids = {profile.id for profile in profiles}

        self.assertIn("echorura-default", profile_ids)
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
        self.assertEqual(config["botName"], "ECHORURA")
        self.assertTrue(config["enableWebSearch"])
        self.assertTrue(config["enableMusic"])


if __name__ == "__main__":
    unittest.main()
