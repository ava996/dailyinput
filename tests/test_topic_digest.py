"""Regression cases for article meaning and shared API/RSS topic budgets."""

import unittest

from scripts.topic_digest import TOPIC_LIMITS, build_topic_stats, classify_article


class ClassifyArticleTests(unittest.TestCase):
    def test_representative_topics(self):
        cases = [
            ("OpenAI 发布新一代 Agent 工具调用 API", "openai", "AI 模型与 Agent"),
            ("Gemini adds multimodal reasoning", "google-ai", "AI 模型与 Agent"),
            ("用 Claude Code 搭建自动化知识库", "builders", "AI 工具与效率"),
            ("Five AI productivity tools for research", "product-hunt", "AI 工具与效率"),
            ("产品经理如何设计可用性测试", "woshipm", "产品思考"),
            ("从用户访谈到需求验证", "woshipm", "产品思考"),
            ("Product discovery: improving activation and retention", "lennys-newsletter", "产品思考"),
            ("A/B testing your onboarding flow", "product-talk", "产品思考"),
            ("A B tests for pricing experiments", "product-talk", "产品思考"),
            ("小红书推出创作者订阅功能", "zhihu", "内容平台"),
            ("TikTok adjusts content moderation", "hacker-news", "内容平台"),
            ("美团调整会员与团购机制", "zhihu", "电商与本地生活"),
            ("Temu expands cross-border ecommerce", "hacker-news", "电商与本地生活"),
            ("中国经济增长预期上修", "wallstreetcn-news", "宏观政策与传导"),
            ("Federal Reserve holds interest rates", "cls-depth", "宏观政策与传导"),
            ("腾讯季度利润增长 20%", "wallstreetcn-news", "金融与投资"),
            ("银行财富管理产品发行增长", "cls-hot", "金融与投资"),
            ("AI 产品经理秋招岗位能力要求", "woshipm", "求职与职业机会"),
            ("银行科技岗招聘与面试准备", "zhihu", "求职与职业机会"),
            ("Product manager job interview preparation", "lennys-newsletter", "求职与职业机会"),
            ("金融科技监管政策更新", "zhihu", "金融与投资"),
        ]
        for title, source, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(classify_article(title, source), expected)

    def test_weak_words_and_author_names_do_not_classify(self):
        for title in (
            "产品经理的一天", "增长带来更多可能", "一个新 App", "科技成果转化大会",
            "社区会员本周活动", "经济模型的数学推导", "历史记忆与城市", "GitHub 项目合集",
            "Apple announces an update", "OA 办公系统维护", "", "周末跑步愉快",
        ):
            with self.subTest(title=title):
                self.assertIsNone(classify_article(title, "builders"))

    def test_financial_sources_cannot_fill_product_ai_or_career_topics(self):
        for source in ("wallstreetcn-news", "wallstreetcn-hot", "cls-hot", "cls-depth", "cls-telegraph"):
            for title in (
                "OpenAI 发布新模型", "产品经理如何做用户研究", "AI 产品经理招聘启事",
                "留存率提升的 A/B 测试", "美团推出新团购功能",
            ):
                with self.subTest(source=source, title=title):
                    self.assertIsNone(classify_article(title, source))

    def test_macro_and_earnings_take_precedence_over_generic_ai_or_growth(self):
        self.assertEqual(classify_article("AI 产业营收增长 50%", "zhihu"), "金融与投资")
        self.assertEqual(classify_article("AI 热潮能否改变经济增长", "wallstreetcn-news"), "宏观政策与传导")
        self.assertEqual(classify_article("AI 产品如何做用户研究", "woshipm"), "产品思考")

    def test_topic_order_and_total_budget(self):
        self.assertEqual(list(TOPIC_LIMITS.values()), [4, 3, 4, 2, 2, 3, 2, 2])
        self.assertEqual(sum(TOPIC_LIMITS.values()), 22)

    def test_source_and_cjk_boundaries(self):
        self.assertEqual(classify_article("OpenAI发布全新模型", "openai"), "AI 模型与 Agent")
        self.assertEqual(classify_article("Codex新增代码审查功能", "builders"), "AI 工具与效率")
        self.assertEqual(classify_article("AI应用的多模态新进展", "qbitai"), "AI 模型与 Agent")
        self.assertEqual(classify_article("Introducing our latest reasoning system", "openai"), "AI 模型与 Agent")
        self.assertIsNone(classify_article("[X] OpenAI: 周末跑步愉快", "builders"))


def article(title, source="zhihu", url=None):
    return {"title": title, "source_id": source, "source_name": source,
            "url": url or f"https://example.com/{source}/{title}", "ranks": [1]}


class MergeTests(unittest.TestCase):
    def test_cross_channel_duplicates_and_tracking(self):
        api = [{"titles": [article("OpenAI 发布 Agent", url="https://example.com/story?utm_source=api")]}]
        rss = [{"titles": [article("OpenAI launches agent", "openai", "https://example.com/story"),
                            article("OpenAI launches agent", "builders", "https://another.com/story")]}]
        stats = build_topic_stats(api, rss)
        self.assertEqual(sum(s["count"] for s in stats), 1)
        self.assertEqual(stats[0]["titles"][0]["source_id"], "openai")

    def test_shared_cap_and_source_diversity(self):
        api = [{"titles": [article(f"AI 新模型{i}", "zhihu") for i in range(10)]}]
        rss = [{"titles": [article(f"OpenAI reasoning release {i}", "openai") for i in range(10)]}]
        stats = build_topic_stats(api, rss)
        self.assertEqual(stats[0]["count"], 4)
        self.assertEqual([x["source_id"] for x in stats[0]["titles"]], ["openai", "zhihu", "openai", "zhihu"])

    def test_finance_cannot_leak_via_display_name_only(self):
        item = article("利润增长推动股票定价", "wallstreetcn-news")
        item.pop("source_id")
        item["source_name"] = "华尔街见闻文章"
        stats = build_topic_stats([{"titles": [item]}], None)
        self.assertEqual([s["word"] for s in stats], ["金融与投资"])

    def test_api_only_rss_only_empty_and_no_input_mutation(self):
        item = article("用户研究与需求验证", "woshipm")
        for api, rss in (([{"titles": [item]}], None), (None, [{"titles": [item]}])):
            self.assertEqual(build_topic_stats(api, rss)[0]["word"], "产品思考")
        self.assertNotIn("topic", item)
        self.assertEqual(build_topic_stats(None, None), [])

    def test_unsafe_url_and_noise_are_dropped(self):
        items = [article("OpenAI 发布", url="javascript:alert(1)"),
                 article("AI 明星八卦"), article("AI 更新", url="https://[bad")]
        self.assertEqual(build_topic_stats([{"titles": items}], None), [])


if __name__ == "__main__":
    unittest.main()
