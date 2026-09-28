import unittest
from datetime import datetime, timedelta, timezone

from scripts.builders_jsonfeed import add_x_items, is_recent, parse_datetime


class BuildersTests(unittest.TestCase):
    def test_missing_invalid_old_and_future_dates_are_excluded(self):
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=3)
        for value in (None, "", "invalid", 42, (now - timedelta(days=4)).isoformat(),
                      (now + timedelta(days=2)).isoformat()):
            with self.subTest(value=value):
                self.assertFalse(is_recent(value, cutoff))
        self.assertTrue(is_recent(now.isoformat(), cutoff))
        self.assertTrue(is_recent(now.replace(tzinfo=None).isoformat(), cutoff))
        self.assertIsNotNone(parse_datetime("2026-09-28T00:00:00Z").tzinfo)

    def test_author_bio_is_not_article_content(self):
        now = datetime.now(timezone.utc)
        items = []
        add_x_items({"x": [{"name": "Builder", "bio": "AI product manager", "tweets": [
            {"createdAt": now.isoformat(), "text": "周末跑步愉快", "url": "https://example.com/post"}
        ]}]}, items, now - timedelta(days=3))
        self.assertEqual(len(items), 1)
        self.assertNotIn("AI product manager", items[0]["content_text"])
        self.assertEqual(items[0]["url"], "https://example.com/post")
