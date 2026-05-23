import os, time, smtplib, requests, xml.etree.ElementTree as ET
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta
from openai import OpenAI

# ── 配置 ────────────────────────────────────────────
WEWE_BASE  = "https://wewe-rss-next-production.up.railway.app"
AUTH_CODE  = "wewerss2026"
QQ_EMAIL   = "1441469055@qq.com"
QQ_AUTH    = os.environ["QQ_AUTH_CODE"]
CST        = timezone(timedelta(hours=8))
MODEL      = "deepseek-v4-flash"

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com"
)

CATEGORIES = {
    "📦 产品": [
        ("MP_WXS_2399106260", "人人都是产品经理"),
        ("MP_WXS_3297653038", "野生运营社区"),
        ("MP_WXS_3581718360", "运营研究社"),
        ("MP_WXS_3866119643", "增长黑盒Growthbox"),
    ],
    "📡 行业动态": [
        ("MP_WXS_3264997043", "36氪"),
        ("MP_WXS_1432156401", "虎嗅APP"),
        ("MP_WXS_3572959446", "晚点LatePost"),
        ("MP_WXS_2390738373", "乱翻书"),
        ("MP_WXS_3902208921", "电商派Pro"),
    ],
    "🤖 AI": [
        ("MP_WXS_2399148061", "腾讯研究院"),
        ("MP_WXS_3268521424", "PyTorch研习社"),
        ("MP_WXS_1304308441", "极客公园"),
        ("MP_WXS_3271041950", "新智元"),
        ("MP_WXS_3236757533", "量子位"),
        ("MP_WXS_3621654047", "特工宇宙"),
    ],
    "📖 其他": [
        ("MP_WXS_3550405832", "一天一篇经济学人"),
    ],
}

# ── Step 1：获取公众号列表 ───────────────────────────
def get_sync_times():
    r = requests.get(f"{WEWE_BASE}/feeds?x-auth-code={AUTH_CODE}", timeout=30)
    r.raise_for_status()
    return {f["id"]: f["syncTime"] for f in r.json()}

# ── Step 2：拉取 RSS ────────────────────────────────
def fetch_rss(feed_id, force_update):
    url = f"{WEWE_BASE}/feeds/{feed_id}.rss?x-auth-code={AUTH_CODE}"
    if force_update:
        url += "&update=true"
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  跳过 {feed_id}：{e}")
        return None

def parse_rss(xml_text, account_name, cutoff):
    if not xml_text:
        return []
    try:
        root = ET.fromstring(xml_text)
        channel = root.find("channel")
        if channel is None:
            return []
        articles, seen = [], set()
        for item in channel.findall("item"):
            title   = (item.findtext("title") or "").strip()
            link    = item.findtext("link") or ""
            pub_str = item.findtext("pubDate") or ""
            desc    = item.findtext("description") or ""
            if not title or title in seen:
                continue
            seen.add(title)
            try:
                pub = parsedate_to_datetime(pub_str)
                if pub.tzinfo is None:
                    pub = pub.replace(tzinfo=timezone.utc)
                if pub < cutoff:
                    continue
            except Exception:
                continue
            articles.append({"title": title, "link": link,
                              "pub": pub, "desc": desc, "account": account_name})
        articles.sort(key=lambda x: x["pub"], reverse=True)
        return articles[:2]
    except ET.ParseError:
        return []

# ── Step 3：生成摘要 ────────────────────────────────
def summarize_article(title, desc):
    if not desc or len(desc.strip()) < 50:
        return ""
    prompt = f"""对以下文章生成中文摘要。

标题：{title}
内容：{desc[:2000]}

格式：
核心观点：[1-2句结论，不写"本文""作者"]
要点：
- [具体数字/数据/反常识判断]
- [工具/产品/方法论直接点名]

资讯类≤80字，深度分析类≤150字。"""
    try:
        r = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300, temperature=0.3
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        print(f"  摘要失败：{e}")
        return ""

# ── Step 4：AI Builders ─────────────────────────────
def fetch_builders():
    base = "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main"
    try:
        builders = requests.get(f"{base}/feed-x.json", timeout=30).json().get("x", [])
    except Exception:
        builders = []
    try:
        podcasts = requests.get(f"{base}/feed-podcasts.json", timeout=30).json().get("podcasts", [])
    except Exception:
        podcasts = []
    return builders, podcasts

def summarize_builder(b):
    tweets = b.get("tweets", [])
    if not tweets:
        return None
    texts = "\n".join(f"- {t['text']}" for t in tweets[:3])
    prompt = f"""{b['name']}（{b.get('bio', '')[:100]}）的最新推文：

{texts}

用2-3句中文描述最有价值的判断或动作，跳过平淡内容。若内容平淡返回空字符串。"""
    try:
        r = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150, temperature=0.3
        )
        s = r.choices[0].message.content.strip()
        return {"name": b["name"], "bio": b.get("bio", ""),
                "summary": s, "url": tweets[0]["url"]} if len(s) > 10 else None
    except Exception:
        return None

def summarize_podcast(p):
    transcript = p.get("transcript", "")
    if not transcript:
        return ""
    try:
        r = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content":
                f"对以下播客生成中文摘要，150字以内，突出核心论点和关键数据。\n\n{transcript[:3000]}"}],
            max_tokens=250, temperature=0.3
        )
        return r.choices[0].message.content.strip()
    except Exception:
        return ""

# ── Step 6：组装 HTML ───────────────────────────────
def build_html(cat_articles, builder_items, podcast_items, date_str):
    H = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{{font-family:-apple-system,sans-serif;max-width:680px;margin:0 auto;padding:20px;color:#333;line-height:1.6}}
h2{{border-left:4px solid #0066cc;padding-left:12px;color:#444}}
h3 a{{color:#0066cc;text-decoration:none}}
.meta{{color:#888;font-size:12px}}
hr{{border:none;border-top:1px solid #eee;margin:14px 0}}
</style></head><body>
<h1>📰 每日摘要 · {date_str}</h1>\n"""

    for cat, articles in cat_articles.items():
        if not articles:
            continue
        H += f"<h2>{cat}</h2>\n"
        for a in articles:
            pub_str = a["pub"].astimezone(CST).strftime("%m-%d %H:%M")
            H += f'<h3><a href="{a["link"]}">{a["title"]}</a></h3>\n'
            H += f'<p class="meta">{a["account"]} · {pub_str}</p>\n'
            if a.get("summary"):
                H += f'<p>{a["summary"]}</p>\n'
            H += f'<p><a href="{a["link"]}">阅读原文 →</a></p><hr>\n'

    if builder_items or podcast_items:
        H += "<h2>🔭 AI Builders</h2>\n"
        for b in builder_items:
            H += f'<h3>{b["name"]} · {b["bio"][:60]}</h3>\n'
            H += f'<p>{b["summary"]}</p>\n'
            H += f'<p><a href="{b["url"]}">查看原推 →</a></p><hr>\n'
        for name, title, url, summary in podcast_items:
            H += f'<h3><a href="{url}">{name}：{title}</a></h3>\n'
            if summary:
                H += f'<p>{summary}</p>\n'
            H += "<hr>\n"

    H += "</body></html>"
    return H

# ── 发邮件 ──────────────────────────────────────────
def send_email(html, date_str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📰 {date_str} 每日摘要"
    msg["From"] = QQ_EMAIL
    msg["To"] = QQ_EMAIL
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.qq.com", 465) as s:
        s.login(QQ_EMAIL, QQ_AUTH)
        s.sendmail(QQ_EMAIL, QQ_EMAIL, msg.as_string())

# ── 主流程 ──────────────────────────────────────────
def main():
    now      = datetime.now(timezone.utc)
    cutoff   = now - timedelta(hours=30)
    date_str = (now + timedelta(hours=8) - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"运行日期：{date_str}，截止时间：{cutoff}")

    # 获取 syncTime
    try:
        sync_times = get_sync_times()
    except Exception as e:
        print(f"获取 feeds 列表失败：{e}")
        sync_times = {}

    # 分4批拉取 RSS
    all_accounts = [(fid, name, cat)
                    for cat, accounts in CATEGORIES.items()
                    for fid, name in accounts]
    cat_articles = {cat: [] for cat in CATEGORIES}

    # Pass 1：对需要更新的账号触发同步（异步，不解析结果）
    stale_ids = []
    for fid, name, cat in all_accounts:
        hours_stale = (now.timestamp() - sync_times.get(fid, 0)) / 3600
        if hours_stale > 3:
            stale_ids.append((fid, name))
    if stale_ids:
        print(f"触发同步：{len(stale_ids)} 个账号（每批4个，批次间隔5秒）...")
        for i in range(0, len(stale_ids), 4):
            batch = stale_ids[i:i+4]
            for fid, name in batch:
                print(f"  同步 {name}")
                fetch_rss(fid, force_update=True)
            if i + 4 < len(stale_ids):
                time.sleep(5)
        print("同步触发完毕，等待 30 秒让后台完成...")
        time.sleep(30)

    # Pass 2：读取最新缓存（不带 update=true）
    for i in range(0, len(all_accounts), 4):
        for fid, name, cat in all_accounts[i:i+4]:
            print(f"  读取 {name}")
            xml = fetch_rss(fid, force_update=False)
            articles = parse_rss(xml, name, cutoff)
            for a in articles:
                a["summary"] = summarize_article(a["title"], a["desc"])
            cat_articles[cat].extend(articles)

    # AI Builders
    print("拉取 AI Builders...")
    builders, podcasts = fetch_builders()
    builder_items = [r for b in builders if (r := summarize_builder(b))]
    podcast_items = []
    for p in podcasts[:1]:
        podcast_items.append((
            p.get("name", ""), p.get("title", ""),
            p.get("url", ""), summarize_podcast(p)
        ))

    # 检查是否有内容
    total = sum(len(a) for a in cat_articles.values())
    if total == 0 and not builder_items and not podcast_items:
        print("近30小时无新文章且 AI Builders 无更新，跳过发送")
        return

    # 发送
    html = build_html(cat_articles, builder_items, podcast_items, date_str)
    send_email(html, date_str)
    print("✅ 邮件发送成功")
    for cat, arts in cat_articles.items():
        print(f"  {cat}：{len(arts)} 篇")
    print(f"  🔭 AI Builders：{len(builder_items)} 位，{len(podcast_items)} 集播客")

if __name__ == "__main__":
    main()
