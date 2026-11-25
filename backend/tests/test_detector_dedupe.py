"""Deterministic tests for the proposed anomaly deduplication helper."""

from __future__ import annotations

import hashlib
import sys
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.detector_dedupe import (
    DeduplicationContext,
    canonical_dedupe_payload,
    dedupe_sha256,
)

UTC = timezone.utc
START = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
END = START + timedelta(seconds=10)


def context(**overrides) -> DeduplicationContext:
    values = {
        "subject_id": "subject-1",
        "demo_run_id": "run-1",
        "generation": 1,
        "detector_version": "sahyog-hr-threshold-v1",
        "window_start": START,
        "window_end": END,
    }
    values.update(overrides)
    return DeduplicationContext(**values)


class CanonicalPayloadTests(unittest.TestCase):
    def test_canonical_json_is_exact_compact_and_sorted(self) -> None:
        self.assertEqual(
            canonical_dedupe_payload(context()),
            (
                '{"demo_run_id":"run-1","detector_version":'
                '"sahyog-hr-threshold-v1","generation":1,'
                '"subject_id":"subject-1",'
                '"window_end":"2026-01-01T00:00:10.000000Z",'
                '"window_start":"2026-01-01T00:00:00.000000Z"}'
            ),
        )

    def test_fixed_microsecond_precision(self) -> None:
        payload = canonical_dedupe_payload(
            context(
                window_start=START.replace(microsecond=1),
                window_end=START.replace(microsecond=123456),
            )
        )
        self.assertIn('"window_start":"2026-01-01T00:00:00.000001Z"', payload)
        self.assertIn('"window_end":"2026-01-01T00:00:00.123456Z"', payload)

    def test_equivalent_offset_timestamps_normalize_to_same_payload(self) -> None:
        utc_context = context()
        offset = timezone(timedelta(hours=5, minutes=30))
        offset_context = context(
            window_start=datetime(2026, 1, 1, 5, 30, tzinfo=offset),
            window_end=datetime(2026, 1, 1, 5, 30, 10, tzinfo=offset),
        )
        self.assertEqual(
            canonical_dedupe_payload(utc_context),
            canonical_dedupe_payload(offset_context),
        )
        self.assertEqual(dedupe_sha256(utc_context), dedupe_sha256(offset_context))

    def test_non_ascii_text_is_utf8_encoded(self) -> None:
        value = context(subject_id="subject-é")
        self.assertIn("subject-é", canonical_dedupe_payload(value))
        expected = hashlib.sha256(
            canonical_dedupe_payload(value).encode("utf-8")
        ).hexdigest()
        self.assertEqual(dedupe_sha256(value), expected)


class DigestTests(unittest.TestCase):
    def test_hash_is_raw_lowercase_sha256(self) -> None:
        digest = dedupe_sha256(context())
        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, digest.lower())
        self.assertTrue(all(character in "0123456789abcdef" for character in digest))
        self.assertFalse(digest.startswith("anomaly:"))
        self.assertNotIn(":", digest)

    def test_same_logical_anomaly_has_same_hash(self) -> None:
        self.assertEqual(dedupe_sha256(context()), dedupe_sha256(context()))

    def test_each_context_field_changes_hash(self) -> None:
        base = dedupe_sha256(context())
        changes = {
            "subject_id": "subject-2",
            "demo_run_id": "run-2",
            "generation": 2,
            "detector_version": "sahyog-hr-threshold-v2",
            "window_start": START + timedelta(microseconds=1),
            "window_end": END + timedelta(microseconds=1),
        }
        for name, value in changes.items():
            with self.subTest(field=name):
                self.assertNotEqual(base, dedupe_sha256(context(**{name: value})))


class ValidationTests(unittest.TestCase):
    def test_empty_identifiers_are_rejected(self) -> None:
        for field in ("subject_id", "demo_run_id", "detector_version"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    context(**{field: "   "})

    def test_non_string_identifier_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            context(subject_id=123)

    def test_generation_must_be_a_positive_integer(self) -> None:
        for invalid in (0, -1, True, 1.5, "1"):
            with self.subTest(invalid=invalid):
                with self.assertRaises((TypeError, ValueError)):
                    context(generation=invalid)

    def test_timestamps_must_be_aware(self) -> None:
        with self.assertRaises(ValueError):
            context(window_start=datetime(2026, 1, 1))
        with self.assertRaises(ValueError):
            context(window_end=datetime(2026, 1, 1, 0, 0, 10))

    def test_window_end_cannot_precede_start(self) -> None:
        with self.assertRaises(ValueError):
            context(window_end=START - timedelta(seconds=1))

    def test_non_datetime_window_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            context(window_start="2026-01-01T00:00:00Z")

    def test_replacing_valid_field_still_validates(self) -> None:
        changed = replace(context(), generation=3)
        self.assertNotEqual(changed, context())


if __name__ == "__main__":
    unittest.main()
