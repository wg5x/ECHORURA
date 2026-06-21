import unittest

from .agent_profile_config import default_agent_profile_configs
from .capability_config import default_capability_configs
from .voice_profile_config import default_voice_profile_configs


FORBIDDEN_BRAND = "echo" + "rura"


class AgentProfileConfigTest(unittest.TestCase):
    def test_default_profiles_are_default_and_phone_assistant_only(self) -> None:
        profiles = default_agent_profile_configs()
        profile_ids = {profile.id for profile in profiles}

        self.assertEqual(profile_ids, {"default", "phone-assistant"})

    def test_profile_ids_do_not_use_project_brand_name(self) -> None:
        profile_ids = [profile.id for profile in default_agent_profile_configs()]

        self.assertTrue(all(FORBIDDEN_BRAND not in profile_id.lower() for profile_id in profile_ids))

    def test_profile_ids_are_unique(self) -> None:
        profiles = default_agent_profile_configs()
        profile_ids = [profile.id for profile in profiles]

        self.assertEqual(len(profile_ids), len(set(profile_ids)))

    def test_profiles_reference_existing_voice_profiles(self) -> None:
        voice_profile_ids = {profile.id for profile in default_voice_profile_configs()}

        for profile in default_agent_profile_configs():
            self.assertIn(profile.voice_profile_id, voice_profile_ids)

    def test_profiles_reference_existing_capabilities(self) -> None:
        capability_ids = {capability.id for capability in default_capability_configs()}

        for profile in default_agent_profile_configs():
            self.assertTrue(set(profile.enabled_capability_ids).issubset(capability_ids))

    def test_phone_assistant_starts_with_native_open_page_and_chat(self) -> None:
        profiles = {profile.id: profile for profile in default_agent_profile_configs()}

        self.assertEqual(profiles["phone-assistant"].voice_profile_id, "short-latency")
        self.assertEqual(
            profiles["phone-assistant"].enabled_capability_ids,
            (
                "native.open_page",
                "native.calendar.create_event",
                "native.phone.dial",
                "native.sms.compose",
                "native.app.open",
                "native.app.search",
                "native.app.open_deep_link",
                "native.browser.open_url",
                "native.gallery.pick_image",
                "native.media.play_from_search",
                "native.settings.open_wifi",
                "native.camera.capture_photo",
                "native.camera.capture_video",
                "server.memory.preference_update",
                "chat.general",
            ),
        )


if __name__ == "__main__":
    unittest.main()
