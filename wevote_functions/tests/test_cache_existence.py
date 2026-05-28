# wevote_functions/tests/test_cache_existence.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import unittest
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.utils import timezone

from config.base import get_environment_variable
from wevote_functions.functions import positive_value_exists, generate_random_string
SERVER_IS_SOURCE_OF_TRUTH = positive_value_exists(get_environment_variable("SERVER_IS_SOURCE_OF_TRUTH",
                                                                           no_exception=True))

@dataclass
class NestedMetrics:
    support_count: int
    oppose_count: int
    tags: list

@dataclass
class ComplexTestCachePayload:
  # Example shape similar to an API payload: ids, flags, numbers, nested data, datetimes.
    we_vote_id: str
    display_name: str
    is_active: bool
    score: float
    ratio: Decimal
    metadata: dict
    metrics: NestedMetrics
    updated_at: datetime  # noqa: F821 — use below
    child_ids: list
    optional_note: str | None = None
    extra: dict = field(default_factory=dict)


# Fix forward reference for older Python if needed (3.9+ can use from __future__ import annotations)
 # noqa: E402


@unittest.skipIf(
    SERVER_IS_SOURCE_OF_TRUTH == True,
    "Database cache tests only run when SERVER_IS_SOURCE_OF_TRUTH is false",
)
class TestDatabaseCacheComplexObject(TestCase):
    """
    Integration test for django.core.cache.backends.db.DatabaseCache.

    Requires wevote_functions.0001_create_cache_table (creates wevote_server_cache).
  """

    def setUp(self):
        self.CACHE_KEY = generate_random_string(10)
        cache.clear()

    def tearDown(self):
        cache.delete(self.CACHE_KEY)

    def _build_payload(self) -> ComplexTestCachePayload:
        return ComplexTestCachePayload(
            we_vote_id="wv01candidate123",
            display_name="Jane Q. Candidate",
            is_active=True,
            score=87.5,
            ratio=Decimal("0.625"),
            metadata={
                "state_code": "CA",
                "election_year": 2026,
                "sources": ["ballotpedia", "vote_usa"],
            },
            metrics=NestedMetrics(
                support_count=1200,
                oppose_count=340,
                tags=["climate", "education"],
            ),
            updated_at=timezone.now(),
            child_ids=["wv01pos1", "wv01pos2"],
            optional_note=None,
            extra={"nested": {"flag": True, "count": 3}},
        )

    def test_set_get_complex_object_round_trip(self):
        payload = self._build_payload()

        cache.set(self.CACHE_KEY, payload, timeout=300)
        retrieved = cache.get(self.CACHE_KEY)

        self.assertIsNotNone(retrieved)
        self.assertIsInstance(retrieved, ComplexTestCachePayload)

        self.assertIsNot(retrieved, payload, "Cache should return a deserialized copy, not the same object")
        self.assertEqual(retrieved.we_vote_id, payload.we_vote_id)
        self.assertEqual(retrieved.display_name, payload.display_name)
        self.assertEqual(retrieved.is_active, payload.is_active)
        self.assertEqual(retrieved.score, payload.score)
        self.assertEqual(retrieved.ratio, payload.ratio)
        self.assertEqual(retrieved.metadata, payload.metadata)
        self.assertEqual(retrieved.metrics.support_count, payload.metrics.support_count)
        self.assertEqual(retrieved.metrics.oppose_count, payload.metrics.oppose_count)
        self.assertEqual(retrieved.metrics.tags, payload.metrics.tags)
        self.assertEqual(retrieved.updated_at, payload.updated_at)
        self.assertEqual(retrieved.child_ids, payload.child_ids)
        self.assertEqual(retrieved.optional_note, payload.optional_note)
        self.assertEqual(retrieved.extra, payload.extra)
        # Whole-object equality (pickle round-trip)
        self.assertEqual(retrieved, payload)


    def test_row_persisted_in_cache(self):
        payload = self._build_payload()
        cache.set(self.CACHE_KEY, payload, timeout=300)

        self.assertTrue(cache.has_key(self.CACHE_KEY))
        self.assertGreater(cache.get(self.CACHE_KEY).updated_at, timezone.now() - timedelta(seconds=5))

    def test_cache_miss_returns_none(self):
        self.assertIsNone(cache.get("wevote_functions:test:does_not_exist"))