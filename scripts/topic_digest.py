"""Route all delivery channels into the same small, title-based topic digest."""

from __future__ import annotations

import re
from collections import defaultdict
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


# One shared ceiling for the whole digest. Per-topic counts are derived from how
# much usable material each topic actually has that day, not from a fixed table.
TOTAL_LIMIT = 22

# Display order. Only topics that clear their own classification rule appear.
TOPIC_ORDER = (
    "AI 模型与工具",
    "产品思考",
    "内容平台",
    "电商与本地生活",
    "宏观政策与传导",
    "金融与投资",
)

# A topic with any usable material keeps at least one slot, so a quiet day never
# blanks a whole section while another topic overflows.
MIN_PER_TOPIC = 1

# No single source may take more than this share of a topic, keeping a prolific
# feed from crowding out every other source in it.
MAX_PER_SOURCE = 2

# Weight one source can contribute at most, in items. Damping by item count
# stops a feed that dumps 50 entries from buying the whole digest.
SOURCE_DAMPING = 3


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
    r"竞品分析|产品策略|产品战略|产品路线图|产品市场匹配|产品复盘|需求洞察|产品增长|产品定价|信息架构|获客成本|复购率|"
    r"\b(?:product discovery|product design|product strategy|product thinking|"
    r"product management|product analytics|product advice|product leadership|product teams?|product-market fit|user research|"
    r"user interviews?|user experience|customer discovery|customer interviews?|"
    r"usability|retention|activation|onboarding|conversion rates?|growth experiments?|"
    r"pricing experiments?|finding (?:your )?first users|jobs[- ]to[- ]be[- ]done|PMF|JTBD|UX|design systems?)\b|"
    r"\bA\s*[/ -]\s*B\s*(?:test(?:ing|s)?|实验|测试)"
)
# Models, agents and the tooling built on them share one topic. Splitting them
# before let one broad "AI" regex fill a bucket of four while the other sat nearly
# empty, which is what starved most RSS entries.
_AI = _pattern(
    r"人工智能|大模型|语言模型|世界模型|智能体|多模态|推理模型|模型评测|工具调用|"
    r"视频生成|语音模型|月之暗面|智谱|通义|豆包|元宝|"
    r"AI\s*(?:[+＋]|工具|产品|应用|效率|办公|编程|笔记|搜索|工作流|自动化)|"
    r"知识管理|效率工具|提示词|上下文工程|"
    r"\b(?:AI|AIGC|LLMs?|Agent(?:s|ic)?|OpenAI|ChatGPT|GPT[- ]?\d\w*|Claude|Anthropic|"
    r"Gemini|DeepSeek|Qwen|Kimi|MiniMax|GLM|Sora|Manus|Coze|Dify|RAG|MCP|"
    r"Claude Code|Codex|Cursor|Copilot|Replit|Windsurf|Warp|Notion|Obsidian|"
    r"artificial intelligence|language models?|foundation models?|"
    r"AI tools?|AI workflows?|AI productivity|AI coding|coding assistants?|"
    r"prompt engineering|context engineering|knowledge management)\b"
)
_AI_NAMES = _pattern(
    r"(?<![a-z])(?:OpenAI|ChatGPT|Claude|Anthropic|Gemini|DeepSeek|Qwen|Kimi|MiniMax|GLM|Sora|RAG|MCP)(?![a-z])"
)
_NOISE = _pattern(r"明星|八卦|塌房|比分|赛果|光刻机|芯片制程|显卡评测|跑分对比|折叠屏|火箭发射|卫星发射|限时优惠|优惠券|抽奖|带货链接")
# Career content no longer has its own section, so it is excluded outright
# instead of being left to spill into the AI and product sections.
_CAREER = _pattern(
    r"校招|社招|招聘|岗位|面试|简历|秋招|春招|求职|职业发展|转行|晋升|"
    r"裁员|组织调整|人力资源|离职|入职|薪酬|薪资|offer|内推|"
    r"\b(?:hiring|recruitment|job openings?|job search|job interviews?|job market|open roles?|"
    r"career|careers|resume|internships?|layoffs?|headcount|salar(?:y|ies))\b"
)
_OFFICIAL_AI = {"openai", "openai-research", "openai-alignment", "anthropic", "anthropic-research", "google-ai"}
_PRODUCT_SOURCES = {"woshipm", "lennys-newsletter"}
_PRODUCT_CONTEXT = _pattern(r"\b(?:discovery|product chief|product advice|evals?|AI failures in your product)\b")
_OFFICIAL_NOISE = _pattern(r"周年|\b(?:anniversary|celebrating|two years of|our team|our office)\b")
_BUILDER_SIGNAL = _pattern(r"发布|工具|工作流|实践|开发|搭建|自动化|评测|提示词|\b(?:launch|releases?|workflows?|how to|built|build|ships?|coding|prompts?|tools?|evals?)\b")
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
        if not (_BUILDER_SIGNAL.search(title) or _PRODUCT.search(title)):
            return None
    if not title or _NOISE.search(title):
        return None
    if source_id in _OFFICIAL_AI and _OFFICIAL_NOISE.search(title):
        return None

    # Financial wires cannot consume the limited product and AI reading slots.
    if source_id.startswith(("wallstreetcn-", "cls-")):
        if _MACRO.search(title):
            return "宏观政策与传导"
        if _FINANCE.search(title):
            return "金融与投资"
        return None

    # Product newsletters combine several topics in one headline; an explicit
    # methodology item wins over an incidental career mention.
    if source_id in _PRODUCT_SOURCES:
        if _PRODUCT.search(title) or _PRODUCT_CONTEXT.search(title):
            return "产品思考"

    if _CAREER.search(title):
        return None

    for topic, pattern in (
        ("宏观政策与传导", _MACRO),
        ("金融与投资", _FINANCE),
        ("电商与本地生活", _ECOMMERCE),
        ("内容平台", _CONTENT),
        ("产品思考", _PRODUCT),
        ("AI 模型与工具", _AI),
    ):
        if pattern.search(title):
            return topic
    if _AI_NAMES.search(title):
        return "AI 模型与工具"
    # Official model/research announcements often omit the company or AI in their title.
    if source_id in _OFFICIAL_AI and _pattern(r"introducing|launch|model|reasoning|research|alignment|safety|发布|模型|研究|推理").search(title):
        return "AI 模型与工具"
    return None


def canonical_url(url: str) -> str:
    """Discard tracking parameters while preserving article-identifying parameters."""
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid", "spm"}]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower().removeprefix("www."),
                       parts.path.rstrip("/"), urlencode(sorted(query)), ""))


def allocate_topic_budgets(supply: dict[str, tuple[int, int]],
                           total_limit: int = TOTAL_LIMIT) -> dict[str, int]:
    """Share one ceiling across topics according to what each topic actually has.

    ``supply`` maps topic -> (usable items, distinct sources). Weighting by
    ``min(items, SOURCE_DAMPING * sources)`` stops one high-volume feed from
    buying the whole digest, and the largest-remainder step keeps thin topics
    alive. Returns only the topics that earned at least one slot.
    """
    topics = [topic for topic in TOPIC_ORDER if supply.get(topic, (0, 0))[0] > 0]
    if not topics:
        return {}

    cap = min(total_limit, sum(supply[topic][0] for topic in topics))
    budget = dict.fromkeys(topics, 0)
    if MIN_PER_TOPIC * len(topics) <= cap:
        for topic in topics:
            budget[topic] = MIN_PER_TOPIC

    demand = {topic: min(supply[topic][0], SOURCE_DAMPING * supply[topic][1]) for topic in topics}

    for _ in range(len(topics) + 1):
        remaining = cap - sum(budget.values())
        if remaining <= 0:
            break
        pool = [topic for topic in topics
                if supply[topic][0] > budget[topic] and demand[topic] > 0]
        if not pool:
            break
        weight = sum(demand[topic] for topic in pool)
        share = {topic: remaining * demand[topic] / weight for topic in pool}
        add = {topic: min(int(share[topic]), supply[topic][0] - budget[topic]) for topic in pool}
        left = remaining - sum(add.values())
        # Hand out the rounding leftovers by largest fractional part first.
        for topic in sorted(pool, key=lambda t: share[t] - int(share[t]), reverse=True):
            if left <= 0:
                break
            room = supply[topic][0] - budget[topic] - add[topic]
            if room > 0:
                give = min(left, room)
                add[topic] += give
                left -= give
        if not any(add.values()):
            break
        for topic, count in add.items():
            budget[topic] += count

    return {topic: count for topic, count in budget.items() if count > 0}


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

    supply = {}
    for topic in TOPIC_ORDER:
        by_source = buckets.get(topic) or {}
        supply[topic] = (sum(len(items) for items in by_source.values()), len(by_source))
    budget = allocate_topic_budgets(supply)

    stats = []
    for topic in TOPIC_ORDER:
        limit = budget.get(topic, 0)
        by_source = buckets.get(topic) or {}
        if limit <= 0 or not by_source:
            continue
        # Every source takes one turn before any source is used a second time, so
        # the section reads across sources instead of doubling up on one.
        rounds = max(MAX_PER_SOURCE, -(-limit // len(by_source)))
        selected = []
        for round_index in range(rounds):
            for items in by_source.values():
                if len(selected) >= limit:
                    break
                if len(items) > round_index:
                    item = items[round_index]
                    if item["channel"] == "rss":
                        item["ranks"] = []  # Feed recency is not a hotlist ranking.
                    selected.append(item)
        if selected:
            stats.append({"word": topic, "count": len(selected), "position": len(stats),
                          "titles": selected, "percentage": 0})
    return stats
