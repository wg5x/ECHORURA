import unittest

from .capability_config import default_capability_configs


class CapabilityConfigTest(unittest.TestCase):
    def test_default_configs_include_current_router_capabilities(self) -> None:
        configs = default_capability_configs()
        capability_ids = {config.id for config in configs}

        self.assertIn("music_creation.create_song", capability_ids)
        self.assertIn("music_creation.revise_song", capability_ids)
        self.assertIn("music_creation.publish_work", capability_ids)
        self.assertIn("native.open_page", capability_ids)
        self.assertIn("chat.general", capability_ids)

    def test_default_config_ids_are_unique(self) -> None:
        configs = default_capability_configs()
        capability_ids = [config.id for config in configs]

        self.assertEqual(len(capability_ids), len(set(capability_ids)))

    def test_publish_config_requires_confirmation(self) -> None:
        configs = {config.id: config for config in default_capability_configs()}

        self.assertTrue(configs["music_creation.publish_work"].requires_confirmation)


if __name__ == "__main__":
    unittest.main()
