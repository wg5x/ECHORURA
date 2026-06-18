import unittest

from .gateway import _clean_display_text, _make_voice_turn_text_event, _merge_asr_text


class AsrTextMergeTest(unittest.TestCase):
    def test_replaces_partial_with_punctuated_final_text(self) -> None:
        first = "哎你刚才说出门记得防晒这件事不是有点废话吗我问的你今天多少度"
        second = "哎，你刚才说出门记得防晒这件事不是有点废话吗？我问的你今天多少度？"

        self.assertEqual(_merge_asr_text(first, second), second)

    def test_keeps_single_line_when_final_text_repeats(self) -> None:
        text = "今天上海多少度？"

        self.assertEqual(_merge_asr_text(text, text), text)

    def test_replaces_short_partial_with_longer_revision(self) -> None:
        first = "今天上海多少度"
        second = "今天上海多少度，适合出门吗？"

        self.assertEqual(_merge_asr_text(first, second), second)

    def test_keeps_previous_text_when_asr_rolls_back_to_shorter_fragment(self) -> None:
        first = "今天上海多少度，适合出门吗？"
        second = "上海多少度"

        self.assertEqual(_merge_asr_text(first, second), first)

    def test_merges_real_tail_content_by_overlap(self) -> None:
        first = "麻烦帮我播放周杰伦的歌"
        second = "周杰伦的歌曲晴天"

        self.assertEqual(_merge_asr_text(first, second), "麻烦帮我播放周杰伦的歌曲晴天")


class DisplayTextCleanTest(unittest.TestCase):
    def test_removes_spaces_between_chinese_characters(self) -> None:
        text = "我 在 用心 的 来 爱着 你 ， 为何 不见 你 对 我 用 真情"

        self.assertEqual(_clean_display_text(text), "我在用心的来爱着你，为何不见你对我用真情")

    def test_keeps_spaces_between_latin_words(self) -> None:
        text = "Play the song Hello World"

        self.assertEqual(_clean_display_text(text), "Play the song Hello World")


class VoiceTurnTextEventTest(unittest.TestCase):
    def test_builds_standard_voice_turn_text_event(self) -> None:
        event = _make_voice_turn_text_event(
            session_id="session-1",
            turn_id="turn-1",
            role="user",
            text="帮我做一首歌",
            output_id="user-output-1",
        )

        self.assertEqual(event["type"], "voice_turn_text")
        self.assertEqual(event["session_id"], "session-1")
        self.assertEqual(event["turn_id"], "turn-1")
        self.assertEqual(event["role"], "user")
        self.assertEqual(event["text"], "帮我做一首歌")
        self.assertEqual(event["source"], "doubao_s2s")
        self.assertEqual(event["output_id"], "user-output-1")
        self.assertRegex(event["at"], r"^\d{2}:\d{2}:\d{2}$")


if __name__ == "__main__":
    unittest.main()
