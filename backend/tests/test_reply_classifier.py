"""Tests for the conservative verification reply classifier."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.reply_classifier import (
    ReplyClassifier,
    ReplyResult,
    classify_reply,
)


class PositiveReplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.classifier = ReplyClassifier()

    def test_approved_positive_phrases(self) -> None:
        for reply in ("I'm okay", "I am okay", "I'm fine", "I'm safe"):
            with self.subTest(reply=reply):
                self.assertIs(self.classifier.classify(reply), ReplyResult.OK)

    def test_case_punctuation_and_apostrophe_variants(self) -> None:
        for reply in (
            "I'M OKAY!",
            "  i am FINE.  ",
            "I’m okay",
            "I‘m okay",
            "I\u02bcm okay",
            "I`m okay",
            "I am okay,\nthanks.",
            "I'm safe.",
            "I am OK",
            "I'm fine 👍",
        ):
            with self.subTest(reply=reply):
                self.assertIs(self.classifier.classify(reply), ReplyResult.OK)

    def test_positive_text_with_no_negative_marker(self) -> None:
        self.assertIs(
            self.classifier.classify("I'm fine, no help needed."),
            ReplyResult.OK,
        )
        self.assertIs(self.classifier.classify("No, I'm fine."), ReplyResult.OK)


class NegativeReplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.classifier = ReplyClassifier()

    def test_approved_negative_phrases(self) -> None:
        for reply in (
            "I'm not okay",
            "I'm not okay!",
            "I need help",
            "Help me",
            "No, I need help.",
        ):
            with self.subTest(reply=reply):
                self.assertIs(self.classifier.classify(reply), ReplyResult.NOT_OK)

    def test_not_okay_is_never_ok(self) -> None:
        for reply in (
            "I'm not okay",
            "I’m not okay",
            "I AM NOT OKAY",
            "I am not okay",
            "I am not ok",
        ):
            with self.subTest(reply=reply):
                self.assertIsNot(self.classifier.classify(reply), ReplyResult.OK)
                self.assertIs(self.classifier.classify(reply), ReplyResult.NOT_OK)

    def test_negative_markers_inside_other_text(self) -> None:
        for reply in (
            "I need HELP!",
            "Please help me now.",
            "I'm fine, but I need help.",
            "I'm okay but not safe.",
            "I am not safe",
            "I am not fine",
            "Maybe I'm okay but I need help.",
            "Okay, but I am not safe.",
            "I'm not okay and I'm fine.",
        ):
            with self.subTest(reply=reply):
                self.assertIs(self.classifier.classify(reply), ReplyResult.NOT_OK)

    def test_negative_phrases_win_conflicts(self) -> None:
        self.assertIs(
            self.classifier.classify("I'm okay, but I am not safe."),
            ReplyResult.NOT_OK,
        )


class UnrecognisedReplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.classifier = ReplyClassifier()

    def test_unrelated_or_incomplete_text_is_unrecognised(self) -> None:
        for reply in (
            "What time is it?",
            "I am not sure",
            "maybe",
            "help",
            "okayish",
            "I am helpful",
            "notokay",
        ):
            with self.subTest(reply=reply):
                self.assertIs(
                    self.classifier.classify(reply),
                    ReplyResult.UNRECOGNISED,
                )

    def test_empty_and_whitespace_only_are_unrecognised(self) -> None:
        for reply in ("", " ", "\n\t", "..."):
            with self.subTest(reply=repr(reply)):
                self.assertIs(
                    self.classifier.classify(reply),
                    ReplyResult.UNRECOGNISED,
                )

    def test_silence_is_not_a_verification_reply(self) -> None:
        self.assertIs(
            self.classifier.classify(""),
            ReplyResult.UNRECOGNISED,
        )

    def test_non_string_reply_raises(self) -> None:
        for invalid in (None, 1, [], object()):
            with self.subTest(invalid=invalid):
                with self.assertRaises(TypeError):
                    self.classifier.classify(invalid)  # type: ignore[arg-type]


class ResultContractTests(unittest.TestCase):
    def test_exact_result_values(self) -> None:
        self.assertEqual(ReplyResult.OK.value, "ok")
        self.assertEqual(ReplyResult.NOT_OK.value, "notOk")
        self.assertEqual(ReplyResult.UNRECOGNISED.value, "unrecognised")

    def test_convenience_wrapper_matches_classifier(self) -> None:
        self.assertIs(classify_reply("I'm okay."), ReplyResult.OK)
        self.assertIs(classify_reply("I'm not okay."), ReplyResult.NOT_OK)
        self.assertIs(classify_reply("unknown"), ReplyResult.UNRECOGNISED)


if __name__ == "__main__":
    unittest.main()
