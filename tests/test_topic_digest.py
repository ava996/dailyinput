"""Regression cases for article meaning and shared API/RSS topic budgets."""

import unittest

from scripts.topic_digest import (
    TOPIC_ORDER,
    TOTAL_LIMIT,
    allocate_topic_budgets,
    build_topic_stats,
    classify_article,
)


class ClassifyArticleTests(unittest.TestCase):
    def test_representative_topics(self):
        cases = [
            ("OpenAI 发布新一代 Agent 工具调用 API", "openai", "AI 模型与工具"),
            ("Gemini adds multimodal reasoning", "google-ai", "AI 模型与工具"),
            ("用 Claude Code 搭建自动化知识库", "builders", "AI 模型与工具"),
            ("Five AI productivity tools for research", "product-hunt", "AI 模型与工具"),
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
            ("金融科技监管政策更新", "zhihu", "金融与投资"),
        ]
        for title, source, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(classify_article(title, source), expected)

    def test_models_and_tooling_share_one_topic(self):
        for title, source in (
            ("OpenAI 发布新一代模型", "openai"),
            ("Codex 新增代码审查功能", "openai"),
            ("用 Cursor 重构遗留代码库", "hacker-news"),
            ("提示词工程的五个常见误区", "woshipm"),
            ("AI+经营分析：从0到1搭建经营分析体系", "woshipm"),
        ):
            with self.subTest(title=title):
                self.assertEqual(classify_article(title, source), "AI 模型与工具")

    def test_career_content_is_dropped_not_rerouted(self):
        for title, source in (
            ("AI 产品经理秋招岗位能力要求", "woshipm"),
            ("银行科技岗招聘与面试准备", "zhihu"),
            ("Product manager job interview preparation", "lennys-newsletter"),
            ("OpenAI is hiring aggressively for its safety team", "openai"),
            ("大厂裁员与组织调整观察", "wallstreetcn-news"),
        ):
            with self.subTest(title=title):
                self.assertIsNone(classify_article(title, source))
        self.assertNotIn("求职与职业机会", TOPIC_ORDER)

    def test_weak_words_and_author_names_do_not_classify(self):
        for title in (
            "产品经理的一天", "增长带来更多可能", "一个新 App", "科技成果转化大会",
            "社区会员本周活动", "经济模型的数学推导", "历史记忆与城市", "GitHub 项目合集",
            "Apple announces an update", "OA 办公系统维护", "", "周末跑步愉快",
        ):
            with self.subTest(title=title):
                self.assertIsNone(classify_article(title, "builders"))

    def test_financial_sources_cannot_fill_product_or_ai_topics(self):
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

    def test_real_preview_product_misses_and_official_noise(self):
        for title in (
            "90 minutes of unfiltered product advice from Snap and Discord’s product chief",
            "Community Wisdom: AI doomerism, speeding up discovery in a big org, and more",
            "Finding your first users before the product exists, and early years of your career",
            "Advanced evals: How to find hidden AI failures in your product",
        ):
            self.assertEqual(classify_article(title, "lennys-newsletter"), "产品思考")
        self.assertIsNone(classify_article("Two years of OpenAI Academy", "openai"))

    def test_source_and_cjk_boundaries(self):
        self.assertEqual(classify_article("OpenAI发布全新模型", "openai"), "AI 模型与工具")
        self.assertEqual(classify_article("Codex新增代码审查功能", "openai"), "AI 模型与工具")
        self.assertEqual(classify_article("AI应用的多模态新进展", "qbitai"), "AI 模型与工具")
        self.assertEqual(classify_article("Introducing our latest reasoning system", "openai"), "AI 模型与工具")
        self.assertIsNone(classify_article("[X] OpenAI: 周末跑步愉快", "builders"))
        self.assertIsNone(classify_article("[X] Someone: Cool to see Replit being popular at a celebrity household!", "builders"))


class AllocationTests(unittest.TestCase):
    def test_topics_are_merged_and_career_is_gone(self):
        self.assertEqual(TOPIC_ORDER, (
            "AI 模型与工具", "产品思考", "内容平台",
            "电商与本地生活", "宏观政策与传导", "金融与投资",
        ))
        self.assertEqual(TOTAL_LIMIT, 22)

    def test_allocation_is_supply_driven_and_capped(self):
        supply = {
            "AI 模型与工具": (50, 18),
            "产品思考": (5, 3),
            "金融与投资": (19, 8),
            "宏观政策与传导": (4, 2),
            "电商与本地生活": (1, 1),
        }
        budget = allocate_topic_budgets(supply)
        self.assertEqual(sum(budget.values()), TOTAL_LIMIT)
        self.assertTrue(all(count >= 1 for count in budget.values()))
        self.assertEqual(max(budget, key=budget.get), "AI 模型与工具")
        # Damping means one huge topic can never take the whole digest.
        self.assertLessEqual(budget["AI 模型与工具"], TOTAL_LIMIT - 4)

    def test_allocation_follows_the_day_not_a_fixed_table(self):
        product_heavy = {"产品思考": (40, 10), "AI 模型与工具": (3, 1)}
        ai_heavy = {"产品思考": (3, 1), "AI 模型与工具": (40, 10)}
        self.assertGreater(allocate_topic_budgets(product_heavy)["产品思考"],
                           allocate_topic_budgets(ai_heavy)["产品思考"])
        self.assertGreater(allocate_topic_budgets(ai_heavy)["AI 模型与工具"],
                           allocate_topic_budgets(product_heavy)["AI 模型与工具"])

    def test_allocation_never_exceeds_low_supply(self):
        budget = allocate_topic_budgets({"AI 模型与工具": (2, 1), "产品思考": (3, 1)})
        self.assertEqual(sum(budget.values()), 5)
        self.assertLessEqual(budget["AI 模型与工具"], 2)
        self.assertLessEqual(budget["产品思考"], 3)

    def test_allocation_handles_no_supply(self):
        self.assertEqual(allocate_topic_budgets({}), {})


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

    def test_single_topic_uses_the_shared_ceiling(self):
        api = [{"titles": [article(f"AI 新模型{i}", "zhihu") for i in range(10)]}]
        rss = [{"titles": [article(f"OpenAI reasoning release {i}", "openai") for i in range(10)]}]
        stats = build_topic_stats(api, rss)
        self.assertEqual([s["word"] for s in stats], ["AI 模型与工具"])
        self.assertEqual(len(stats[0]["titles"]), 20)
        # Each source takes a turn before any source is used twice.
        self.assertEqual([x["source_id"] for x in stats[0]["titles"][:2]], ["openai", "zhihu"])

    def test_total_never_exceeds_the_ceiling(self):
        api = [{"titles": [article(f"AI 模型{i}", "zhihu") for i in range(40)]}]
        rss = [{"titles": [article(f"AI 工具发布 {i}", "qbitai") for i in range(40)]
                            + [article(f"用户研究方法 {i}", "woshipm") for i in range(30)]
                            + [article(f"美团团购调整 {i}", "hacker-news") for i in range(30)]}]
        stats = build_topic_stats(api, rss)
        self.assertEqual(sum(s["count"] for s in stats), TOTAL_LIMIT)
        self.assertEqual([s["word"] for s in stats][0], "AI 模型与工具")

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
