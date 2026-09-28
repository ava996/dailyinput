"""Exercise the pinned upstream pipeline without network, AI calls or email."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = os.environ.get("TRENDRADAR_ROOT")
if UPSTREAM:
    sys.path.insert(0, UPSTREAM)


@unittest.skipUnless(UPSTREAM, "Set TRENDRADAR_ROOT to test the patched upstream checkout")
class TrendRadarIntegrationTests(unittest.TestCase):
    def test_ingestion_is_uncapped_and_preserves_source_identity(self):
        from trendradar.core.analyzer import count_rss_frequency, count_word_frequency
        from trendradar.core.frequency import load_frequency_words
        groups, filters, global_filters = load_frequency_words(str(ROOT / "config/frequency_words.txt"))
        data = {"wallstreetcn-news": {f"公司{i}利润增长": {"ranks": [i + 1], "url": f"https://example.com/{i}"} for i in range(30)}}
        api, _ = count_word_frequency(data, groups, filters, {"wallstreetcn-news": "华尔街见闻文章"},
                                     mode="current", global_filters=global_filters, quiet=True)
        self.assertEqual(len(api[0]["titles"]), 30)
        self.assertEqual(api[0]["titles"][0]["source_id"], "wallstreetcn-news")
        rss, _ = count_rss_frequency([
            {"title": "用户研究与需求验证", "feed_id": "woshipm", "feed_name": "人人都是产品经理",
             "url": "https://example.com/product", "published_at": "2026-09-28T08:00:00+08:00"}
        ], groups, filters, global_filters=global_filters, quiet=True)
        self.assertEqual(rss[0]["titles"][0]["source_id"], "woshipm")

    def test_real_pipeline_merges_before_ai_and_html_including_rss_only(self):
        from trendradar.__main__ import NewsAnalyzer
        from trendradar.report.generator import prepare_report_data
        from trendradar.report.html import render_html_content

        api_item = {"title": "经济增长预期上修", "source_id": "wallstreetcn-news", "source_name": "华尔街见闻文章",
                    "url": "https://example.com/macro", "ranks": [1]}
        rss_item = {"title": "Product discovery through user interviews", "source_id": "woshipm",
                    "source_name": "人人都是产品经理", "url": "https://example.com/product", "ranks": [1]}
        for api, rss in (([api_item], [rss_item]), ([], [rss_item]), ([api_item], []), ([], [])):
            with self.subTest(api=bool(api), rss=bool(rss)), tempfile.TemporaryDirectory() as tmp:
                analyzer = NewsAnalyzer.__new__(NewsAnalyzer)
                captured = {}

                def ai(stats, rss_items, *args, **kwargs):
                    captured["ai_stats"] = stats
                    self.assertIsNone(rss_items)
                    return None

                def generate(stats, total, **kwargs):
                    self.assertIsNone(kwargs["rss_items"])
                    self.assertIsNone(kwargs["rss_new_items"])
                    report = prepare_report_data(stats)
                    report.update(kwargs["report_metadata"])
                    rendered = render_html_content(report, total, mode="current", region_order=["hotlist", "ai_analysis"])
                    captured["html"] = rendered.split("<script>")[0]
                    return "preview.html"

                analyzer.filter_method = "keyword"
                analyzer.report_mode = "current"
                analyzer.frequency_file = str(ROOT / "config/frequency_words.txt")
                analyzer._rss_total_count = len(rss)
                analyzer._rss_source_total = 1
                analyzer._rss_source_failed = 0
                analyzer.ctx = SimpleNamespace(
                    count_frequency=lambda *a, **k: ([{"titles": api}], len(api)),
                    display_mode="keyword", platform_ids=["wallstreetcn-news"],
                    config={"AI_ANALYSIS": {"ENABLED": True}, "AI_TRANSLATION": {"ENABLED": False},
                            "STORAGE": {"FORMATS": {"HTML": True}}, "DISPLAY": {}, "SHOW_VERSION_UPDATE": False},
                    generate_html=generate,
                )
                analyzer._run_ai_analysis = ai
                previous = Path.cwd()
                try:
                    os.chdir(tmp)
                    result = analyzer._run_analysis_pipeline({}, "current", {}, {}, [], [], {}, rss_items=[{"titles": rss}])
                finally:
                    os.chdir(previous)
                stats = result[0]
                self.assertEqual(sum(s["count"] for s in stats), len(api) + len(rss))
                if stats:
                    self.assertEqual(captured["ai_stats"], stats)
                for item in api + rss:
                    self.assertIn(item["title"], captured["html"])
                    self.assertIn(item["url"], captured["html"])
                self.assertNotIn('class="rss-section"', captured["html"])
                self.assertNotIn('>RSS 订阅更新<', captured["html"])
                self.assertNotIn('>RSS 命中<', captured["html"])
                self.assertIn("精选 / 候选", captured["html"])

    def test_production_config_supports_unified_translation_and_collection(self):
        import yaml
        cfg = yaml.safe_load((ROOT / "config/config.yaml").read_text())
        self.assertTrue(cfg["display"]["regions"]["rss"])
        self.assertNotIn("rss", cfg["display"]["region_order"])
        self.assertEqual(cfg["report"]["max_news_per_keyword"], 0)
        self.assertTrue(cfg["ai_translation"]["scope"]["hotlist"])
        self.assertFalse(cfg["ai_analysis"]["include_rss"])
