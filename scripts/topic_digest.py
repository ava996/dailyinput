"""Route all delivery channels into the same small, title-based topic digest."""

from __future__ import annotations

import re
from collections import defaultdict
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TOPIC_LIMITS = {
    "AI 模型与 Agent": 4,
    "AI 工具与效率": 3,
    "产品思考": 4,
    "内容平台": 2,
    "电商与本地生活": 2,
    "宏观政策与传导": 3,
    "金融与投资": 2,
    "求职与职业机会": 2,
}


def _pattern(expression: str) -> re.Pattern[str]:
    # ASCII boundaries let English names match directly beside Chinese text.
    return re.compile(expression, re.IGNORECASE | re.ASCII)


_MACRO = _pattern(
    r"美联储|央行|人民银行|降息|加息|降准|利率|汇率|人民币|美元指数|关税|贸易战|"
    r"通胀|通缩|财政|货币政策|社融|国债收益率|宏观经济|经济增长|经济数据|经济复苏|"
    r"国常会|中央经济工作会议|专项债|地方债|赤字|外贸|进出口|就业数据|非农|"
    r"\b(?:CPI|PPI|GDP|PMI|LPR|MLF|M1|M2)\b|\b(?:inflation|deflation|tariffs?|"
    r"federal reserve|interest rates?|rate cuts?|monetary policy|fiscal policy|"
    r"economic growth|macroeconomics?)\b"
)
_FINANCE = _pattern(
    r"银行|券商|保险|消费金融|财富管理|数字人民币|金融科技|金融监管|证监会|风控|反欺诈|"
    r"A股|港股|美股|股市|债市|股票|股价|股指|基金|黄金|白银|估值|并购|财报|营收|利润|"
    r"回购|资管|理财|北向资金|南向资金|上市公司|牛市|熊市|证券|债券|投资回报|"
    r"\b(?:fintech|IPO|earnings|revenue|stocks?|bonds?|equities|dividends?|"
    r"valuation|stock market|investment|banking|financial results)\b"
)
_CAREER = _pattern(
    r"校招|社招|招聘|岗位|面试|简历|实习|秋招|春招|裁员|组织调整|薪酬|求职|职业发展|"
    r"转行|晋升|\b(?:hiring|recruitment|job openings?|job search|job interviews?|"
    r"career|careers|resume|internships?|layoffs?|headcount|salar(?:y|ies))\b"
)
_ECOMMERCE = _pattern(
    r"电商|淘宝|天猫|京东|拼多多|美团|饿了么|即时零售|本地生活|外卖|到店|团购|"
    r"直播带货|跨境电商|亚马逊|\b(?:PDD|Temu|Shein|e-commerce|ecommerce|"
    r"online shopping|food delivery|Amazon)\b"
)
_CONTENT = _pattern(
    r"小红书|抖音|B站|快手|视频号|微信公众号|微博|内容平台|创作者生态|社区治理|"
    r"内容商业化|\b(?:TikTok|bilibili|YouTube|creator economy|content moderation)\b"
)
_PRODUCT = _pattern(
    r"产品设计|产品思维|产品体验|需求分析|需求验证|用户需求|产品发现|功能设计|用户体验|"
    r"用户增长|用户激活|用户留存|用户转化|留存率|转化率|用户研究|用户访谈|用户画像|"
    r"可用性测试|可用性研究|增长实验|定价实验|推荐算法|搜索体验|交互设计|原型设计|"
    r"竞品分析|产品策略|产品战略|产品路线图|产品市场匹配|获客成本|复购率|"
    r"\b(?:product discovery|product design|product strategy|product thinking|"
    r"product management|product analytics|product-market fit|user research|"
    r"user interviews?|user experience|customer discovery|customer interviews?|"
    r"usability|retention|activation|onboarding|conversion rates?|growth experiments?|"
    r"pricing experiments?|jobs[- ]to[- ]be[- ]done|PMF|JTBD)\b|"
    r"\bA\s*[/ -]\s*B\s*(?:test(?:ing|s)?|实验|测试)"
)
_AI_TOOLS = _pattern(
    r"AI\s*(?:工具|效率|办公|编程|笔记|搜索|工作流|自动化)|知识管理|效率工具|"
    r"提示词|上下文工程|\b(?:Claude Code|Codex|Cursor|Copilot|Notion|Obsidian|Figma|"
    r"AI tools?|AI workflows?|AI productivity|AI coding|coding assistants?|"
    r"prompt engineering|context engineering|knowledge management)\b"
)
_AI_MODELS = _pattern(
    r"人工智能|大模型|语言模型|世界模型|智能体|多模态|推理模型|模型评测|工具调用|"
    r"视频生成|语音模型|月之暗面|智谱|通义|豆包|元宝|\b(?:AI|AIGC|LLMs?|"
    r"Agent(?:s|ic)?|OpenAI|ChatGPT|GPT[- ]?\d\w*|Claude|Anthropic|Gemini|DeepSeek|"
    r"Qwen|Kimi|MiniMax|GLM|Sora|Manus|Coze|Dify|RAG|MCP|"
    r"artificial intelligence|language models?|foundation models?)\b"
)
_AI_NAMES = _pattern(
    r"(?<![a-z])(?:OpenAI|ChatGPT|Claude|Anthropic|Gemini|DeepSeek|Qwen|Kimi|MiniMax|GLM|Sora|RAG|MCP)(?![a-z])"
)
_NOISE = _pattern(r"明星|八卦|塌房|比分|赛果|光刻机|芯片制程|显卡评测|跑分对比|折叠屏|火箭发射|卫星发射|限时优惠|优惠券|抽奖|带货链接")
_OFFICIAL_AI = {"openai", "openai-research", "openai-alignment", "anthropic", "anthropic-research", "google-ai"}
_PRODUCT_SOURCES = {"woshipm", "lennys-newsletter"}
_SOURCE_NAMES = {
    "华尔街见闻文章": "wallstreetcn-news", "华尔街见闻": "wallstreetcn-news",
    "财联社热门": "cls-hot", "财联社深度": "cls-depth", "财联社电报": "cls-telegraph",
    "OpenAI News": "openai", "OpenAI Research": "openai-research", "OpenAI Alignment": "openai-alignment",
    "Anthropic News": "anthropic", "Anthropic Research": "anthropic-research", "Google AI Blog": "google-ai",
    "人人都是产品经理": "woshipm", "Lenny's Newsletter": "lennys-newsletter",
    "AI Builders": "builders", "Latent Space": "latent-space", "Product Hunt": "product-hunt",
}


def classify_article(title: str, source_id: str) -> str | None:
    """Choose one topic from title evidence; source metadata never adds keywords."""
    title = " ".join((title or "").split())
    source_id = (source_id or "").casefold()
    if source_id == "builders":
        title = re.sub(r"^\[(?:X|Blog|Podcast)\]\s*[^:]+:\s*", "", title)
    if not title or _NOISE.search(title):
        return None

    # Financial wires cannot consume the limited product and AI reading slots.
    if source_id.startswith(("wallstreetcn-", "cls-")):
        if _MACRO.search(title):
            return "宏观政策与传导"
        if _FINANCE.search(title):
            return "金融与投资"
        return None

    for topic, pattern in (
        ("求职与职业机会", _CAREER),
        ("宏观政策与传导", _MACRO),
        ("金融与投资", _FINANCE),
        ("电商与本地生活", _ECOMMERCE),
        ("内容平台", _CONTENT),
        ("产品思考", _PRODUCT),
        ("AI 工具与效率", _AI_TOOLS),
        ("AI 模型与 Agent", _AI_MODELS),
    ):
        if pattern.search(title):
            return topic
    if _AI_NAMES.search(title):
        return "AI 模型与 Agent"
    # Official model/research announcements often omit the company or AI in their title.
    if source_id in _OFFICIAL_AI and _pattern(r"introducing|launch|model|reasoning|research|alignment|safety|发布|模型|研究|推理").search(title):
        return "AI 模型与 Agent"
    return None


def canonical_url(url: str) -> str:
    """Discard tracking parameters while preserving article-identifying parameters."""
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid", "spm"}]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower().removeprefix("www."),
                       parts.path.rstrip("/"), urlencode(sorted(query)), ""))


def build_topic_stats(hotlist_stats: list[dict] | None, rss_stats: list[dict] | None) -> list[dict]:
    """Classify before capping, deduplicate across channels, then share topic budgets."""
    candidates = []
    for channel, groups in (("api", hotlist_stats), ("rss", rss_stats)):
        for group in groups or []:
            for original in group.get("titles", []):
                item = dict(original)
                title = item.get("title", "").strip()
                source = item.get("source_id") or _SOURCE_NAMES.get(item.get("source_name"), item.get("source_name", ""))
                topic = classify_article(title, source)
                url = item.get("url", "")
                try:
                    parts = urlsplit(url)
                except ValueError:
                    continue
                if not topic or parts.scheme not in {"http", "https"} or not parts.netloc:
                    continue
                item.update(source_id=source, channel=channel, topic=topic, title=title)
                item.setdefault("time_display", "")
                item.setdefault("count", 1)
                item.setdefault("ranks", [])
                item.setdefault("rank_threshold", 5)
                priority = 0 if source in _OFFICIAL_AI or (topic == "产品思考" and source in _PRODUCT_SOURCES) else 1
                candidates.append((priority, min(item["ranks"] or [999]), item))

    candidates.sort(key=lambda entry: (entry[0], entry[1]))
    buckets = defaultdict(lambda: defaultdict(list))
    seen_urls, seen_titles = set(), set()
    for _, _, item in candidates:
        url_key = canonical_url(item["url"])
        title_key = re.sub(r"[\W_]+", "", item["title"].casefold())
        if url_key in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(url_key)
        seen_titles.add(title_key)
        buckets[item["topic"]][item["source_id"]].append(item)

    stats = []
    for position, (topic, limit) in enumerate(TOPIC_LIMITS.items()):
        sources = buckets[topic]
        selected = []
        # Give each source one turn before using its second slot.
        for round_index in range(2):
            for items in sources.values():
                if len(items) > round_index and len(selected) < limit:
                    selected.append(items[round_index])
        if selected:
            stats.append({"word": topic, "count": len(selected), "position": position,
                          "titles": selected, "percentage": 0})
    return stats
