import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.api.runtime.config_service import (
    VOICE_SCENE_IDS,
    create_runtime_session_config,
    create_scene_runtime_session_config,
    create_scene,
    get_user,
    list_scenes,
    list_users,
    save_scene_config,
)


class RuntimeConfigServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        runtime_dir = Path(self.temp_dir.name)
        self.patchers = [
            patch("apps.api.runtime.config_service.RUNTIME_CONFIG_DIR", runtime_dir),
            patch("apps.api.runtime.config_service.SCENE_STORE_PATH", runtime_dir / "scenes.json"),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.temp_dir.cleanup()

    def test_default_podcast_users_bind_to_podcast_scenes(self):
        users = {user["id"]: user for user in list_users()}

        self.assertEqual(users["podcast_creator_user"]["assignedSceneIds"], ["podcast_creator_duo"])
        self.assertEqual(users["podcast_analysis_user"]["assignedSceneIds"], ["podcast_analysis_duo"])

    def test_default_podcast_scenes_have_host_pairs(self):
        scenes = {scene["id"]: scene for scene in list_scenes()}

        self.assertEqual(scenes["podcast_creator_duo"]["sceneKind"], "podcast")
        self.assertEqual(scenes["podcast_creator_duo"]["config"]["podcastHostA"], "mizi")
        self.assertEqual(scenes["podcast_creator_duo"]["config"]["podcastHostB"], "dayi")
        self.assertEqual(scenes["podcast_analysis_duo"]["config"]["podcastHostA"], "liufei")
        self.assertEqual(scenes["podcast_analysis_duo"]["config"]["podcastHostB"], "xiaolei")
        self.assertIn("podcast_generation", scenes["podcast_creator_duo"]["requiredCapabilities"])

    def test_default_dialogue_scene_kind(self):
        scenes = {scene["id"]: scene for scene in list_scenes()}

        self.assertEqual(scenes["evening_reflection"]["sceneKind"], "dialogue")
        self.assertIn("realtime_voice", scenes["evening_reflection"]["requiredCapabilities"])

    def test_hs6_interview_disables_user_query_exit_and_allows_barge_in(self):
        scenes = {scene["id"]: scene for scene in list_scenes()}
        session = asyncio.run(
            create_runtime_session_config("hs6_interview_user", "hs6_user_interview", memory_enabled=False)
        )

        self.assertFalse(scenes["hs6_user_interview"]["config"]["enableUserQueryExit"])
        self.assertFalse(session["config"]["enableUserQueryExit"])
        self.assertTrue(scenes["hs6_user_interview"]["config"]["enableBargeIn"])
        self.assertTrue(session["config"]["enableBargeIn"])

    def test_scene_session_can_start_without_runtime_user(self):
        session = asyncio.run(
            create_scene_runtime_session_config("hs6_user_interview", memory_enabled=False)
        )

        self.assertEqual(session["scene"]["id"], "hs6_user_interview")
        self.assertNotIn("user", session)
        self.assertNotIn("当前账号", session["config"]["systemRole"])
        self.assertIn("红旗 HS6-PHEV 用户深度访谈", session["config"]["systemRole"])

    def test_scene_session_ignores_business_entry_params(self):
        session = asyncio.run(
            create_scene_runtime_session_config(
                "hs6_user_interview",
                memory_enabled=False,
            )
        )

        self.assertNotIn("entryParams", session)
        self.assertNotIn("# 页面进入参数", session["config"]["systemRole"])

    def test_podcast_user_only_sees_its_bound_scene(self):
        user = get_user("podcast_creator_user")
        scenes = list_scenes(user["id"])

        self.assertEqual([scene["id"] for scene in scenes], ["podcast_creator_duo"])

    def test_voice_experience_user_sees_voice_scenes(self):
        user = get_user("voice_experience_user")
        scenes = list_scenes(user["id"])

        self.assertEqual(user["assignedSceneIds"], VOICE_SCENE_IDS)
        self.assertEqual([scene["id"] for scene in scenes], VOICE_SCENE_IDS)
        self.assertEqual(len(scenes), 20)

    def test_admin_can_save_user_specific_scene_config(self):
        saved_scene = save_scene_config(
            "podcast_creator_duo",
            "admin_operator",
            {
                "podcastHostA": "liufei",
                "podcastHostB": "xiaolei",
                "podcastStyle": "给创作者用户的专属配置",
            },
            "podcast_creator_user",
        )

        creator_scene = list_scenes("podcast_creator_user")[0]
        global_scene = {scene["id"]: scene for scene in list_scenes()}["podcast_creator_duo"]
        session = asyncio.run(create_runtime_session_config("podcast_creator_user", "podcast_creator_duo"))

        self.assertEqual(saved_scene["config"]["podcastHostA"], "liufei")
        self.assertEqual(creator_scene["config"]["podcastHostB"], "xiaolei")
        self.assertEqual(session["config"]["podcastStyle"], "给创作者用户的专属配置")
        self.assertEqual(global_scene["config"]["podcastHostA"], "mizi")

    def test_user_specific_scene_config_requires_assignment(self):
        with self.assertRaisesRegex(PermissionError, "目标用户没有被分配这个场景"):
            save_scene_config(
                "podcast_analysis_duo",
                "admin_operator",
                {"podcastHostA": "mizi", "podcastHostB": "dayi"},
                "podcast_creator_user",
            )

    def test_create_podcast_scene_sets_podcast_defaults(self):
        result = create_scene(
            "admin_operator",
            {
                "id": "custom_podcast",
                "sceneKind": "podcast",
                "title": "自定义播客",
                "config": {
                    "podcastHostA": "liufei",
                    "podcastHostB": "xiaolei",
                    "podcastStyle": "访谈分析",
                },
            },
        )

        scene = result["scene"]
        self.assertEqual(scene["sceneKind"], "podcast")
        self.assertEqual(scene["modelProfileId"], "doubao-seed-podcast")
        self.assertEqual(scene["requiredCapabilities"], ["podcast_generation", "podcast_voice_pair"])
        self.assertEqual(scene["config"]["podcastHostA"], "liufei")


if __name__ == "__main__":
    unittest.main()
