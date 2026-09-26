# Daily AI Product Radar

This repository runs a daily TrendRadar-based digest for AI product manager job preparation.

## What Changed

- Removed the old `wewe-rss` and Railway dependency from the scheduled workflow.
- Runs TrendRadar once per day near Beijing 08:00 through GitHub Actions. The cron is set to Beijing 07:53 to avoid GitHub's top-of-hour schedule queue.
- Sends email to `1441469055@qq.com`.
- Uses keyword grouping as the stable primary filter, then uses DeepSeek for RSS translation and daily analysis.
- Organizes sources around three signal lines:
  - AI development: official AI feeds, Chinese AI media, Product Hunt, and AI Builders
  - product and business judgment: Zhihu, InfoQ 中文, TechCrunch AI, Lenny's Newsletter, Latent Space
  - finance and macro: Wallstreetcn, CLS
- Filters out SaaS, strong hardware technology details, and low-signal entertainment noise.

## Source Shape

TrendRadar directly reads hotlist platforms and RSS feeds. Builders data is generated from `zarazhangrui/follow-builders` JSON snapshots into a local JSON Feed during the GitHub Actions run, then passed to TrendRadar as an RSS-compatible source.

### Hotlist platforms (`config.yaml` → `platforms.sources`)

| id | name | why |
|---|---|---|
| `zhihu` | 知乎 | 互联网 / 产品讨论 |
| `github-trending-today` | GitHub Trending | 开源与 AI 工具风向 |
| `wallstreetcn-hot` | 华尔街见闻 | 金融宏观 |
| `cls-hot` | 财联社热门 | 投资快讯 |
| `cls-depth` | 财联社深度 | 深度报道 |
| `fastbull-news` | 法布财经解读 | 财经分析方法论 |

`fastbull-news` is the useful one for understanding rather than just knowing: its items are explainers such as "股票回购如何影响每股收益：增厚不等于创造价值", "债券到期收益率不等于实际年化回报", "DV01怎么算？把债券久期换成每个基点的盈亏". Note its links live on `fastbull.com`, not `.cn` — `expected_domain` must match or TrendRadar silently discards the whole platform.

Removed: `36kr-renqi` and `36kr` (the upstream NewsNow API answers `Invalid source id` for both), plus `sspai` and `jin10` (cut for volume; Jin10 overlapped with Wallstreetcn and CLS).

### RSS feeds (`config.yaml` → `rss.feeds`)

OpenAI official site: OpenAI News, OpenAI Research, OpenAI Alignment.

Anthropic official site: Anthropic News, Anthropic Research.

Other AI and product: Google AI Blog, Product Hunt, AI Builders.

Chinese: 量子位 (`qbitai.com/feed`), 人人都是产品经理 (`woshipm.com/feed`), InfoQ 中文 (`infoq.cn/feed`).

English first-hand: TechCrunch AI, Lenny's Newsletter, Latent Space, Hacker News.

Chinese finance RSS was tried and abandoned — 第一财经, 财新, 经济观察, 21财经, 证券时报, 中国证券报, 界面, 东方财富 and 智通财经 all return 403/404/500 or an empty feed. Policy and macro coverage therefore comes from the hotlist platforms above, which are the ones actually carrying interpretation rather than raw wire copy.

Removed for volume: `rss.huxiu.com` (returns an empty RSS channel with zero items), Anthropic Red Team, 极客公园, 钛媒体, Interconnects, Hugging Face Blog. All are one-line additions if you want them back.

### Official site sections

Neither OpenAI nor Anthropic publishes an official RSS feed for its research sections — `openai.com/research/rss.xml`, `www.anthropic.com/rss.xml`, `www.anthropic.com/research/rss.xml` and `www.anthropic.com/news/rss.xml` all return 404. Only `openai.com/news/rss.xml` is a real feed (`Content-Type: text/xml`, channel title `OpenAI News`).

The research feeds come from [0xSMW/rss-feeds](https://github.com/0xSMW/rss-feeds), which scrapes each site section and republishes it as RSS on a schedule:

| Section | URL | Cadence |
|---|---|---|
| Anthropic Research | `feeds/feed_anthropic_research.xml` | ~1 per 6 days |
| OpenAI Research | `feeds/feed_openai_research.xml` | ~1 per 6 days |

These publish irregularly, so they use `max_age_days: 14` instead of the 2-day global window. Weekly sources (Lenny's, Latent Space) use `max_age_days: 10`.

## How The Digest Length Is Controlled

This is the part that is easy to get wrong, so it is worth writing down.

**`@N` in `frequency_words.txt` is the maximum number of items shown per group, not a weight.** TrendRadar's parser (`trendradar/core/frequency.py`) documents it as `@数字：该词组最多显示的条数`. `report.max_news_per_keyword` is only the global fallback used when a group has no `@N`.

**The first matching group wins.** `count_rss_frequency` breaks out of the group loop as soon as one group matches. A broad group placed first therefore swallows everything and the groups after it never fill. That is why the order below goes specific → generic, with the catch-all AI group last.

**The hotlist and RSS caps are applied independently.** `count_frequency` and `count_rss_frequency` each enforce `@N` on their own side, so a group can occupy up to `2 × @N` slots in the finished email. Size the caps at roughly half the per-group total you actually want.

Current caps, chosen so the whole digest lands at 15–20 items:

| Group | `@N` |
|---|---|
| 求职与职业机会 | 3 |
| 金融银行与宏观投资 | 4 |
| 电商与本地生活 | 2 |
| 内容平台 | 2 |
| 产品思考 | 2 |
| AI 工具与效率 | 2 |
| AI 模型与 Agent (catch-all, last) | 4 |

**Do not size the digest from the Actions log.** The log line `[推送] 准备发送：热榜 N 条 + RSS M 条` mixes two different counters: the hotlist number is `sum(len(stat["titles"]))`, which is already capped, while the RSS number is `sum(stat["count"])`, which is the raw pre-cap match count. The RSS figure is therefore inflated several-fold — a run reporting "RSS 38 条" renders about 10 entries.

To check the real volume without sending an email every time, replicate the matching locally: filter each feed by its `max_age_days`, apply `[GLOBAL_FILTER]`, assign each title to its first matching group, then apply the `@N` caps. Cross-check the hotlist figure against the log, which is accurate on that side.

Measured with that method on 2026-09-27: **18 items** (8 hotlist + 10 RSS).

## Required GitHub Secrets

- `DEEPSEEK_API_KEY` (or `AI_API_KEY`)
- `QQ_AUTH_CODE` (or `EMAIL_PASSWORD`)
- `KEEPALIVE_PAT` (optional but recommended — see below)

Email sender and receiver are both configured as `1441469055@qq.com`.

## Filtering Strategy

Keep `filter.method` set to `keyword` for production runs. TrendRadar's `ai` filter is an AI-only gate: if classification returns zero matches, it replaces the keyword result with an empty report and skips email delivery. Keyword filtering keeps the digest stable while DeepSeek still adds analysis and translation after the candidate set is selected.

## Why The Daily Digest Stopped (2026-08-15)

Symptom: 91 consecutive successful runs, then nothing for 43 days. No failed run in between — the workflow simply stopped being scheduled.

Cause: GitHub automatically disables every `schedule`-triggered workflow once a repository has had **no activity for 60 days**. This repository's last push was `dcb6a43` on 2026-06-15. Sixty days later, on 2026-08-14, the counter expired; the last run (#91) went out on 08-15 and nothing fired afterwards. The workflow state now reads `disabled_inactivity`.

### How to re-enable

1. Actions tab → **Daily AI Product Radar** → **Enable workflow**.
2. Or with the API: `PUT /repos/ava996/dailyinput/actions/workflows/282154964/enable`.
3. Trigger one run manually with **Run workflow** to confirm the email still lands.

### How it stays enabled now

`.github/workflows/keepalive.yml` writes a timestamp into `.github/keepalive.txt` and commits it on the 1st and 15th of every month. That keeps the repository's activity window from ever reaching 60 days.

The keepalive workflow is self-sustaining: as long as it keeps committing every half month, the 60-day window never closes. It is still a scheduled workflow, so if it ever lapses along with everything else, re-enable both together.

Recommended: create a fine-grained PAT scoped to this repository only, with **Contents: Read and write**, and store it as the `KEEPALIVE_PAT` secret. Commits pushed with a PAT are unambiguously counted as repository activity; whether the default `GITHUB_TOKEN` counts is not documented.
