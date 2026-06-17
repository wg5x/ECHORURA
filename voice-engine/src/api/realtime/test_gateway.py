import unittest

from .gateway import _merge_asr_text


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


if __name__ == "__main__":
    unittest.main()
