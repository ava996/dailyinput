# Daily AI Product Radar

This repository runs a daily TrendRadar-based digest for AI product manager job preparation.

## What Changed

- Removed the old `wewe-rss` and Railway dependency from the scheduled workflow.
- Runs TrendRadar once per day near Beijing 08:00 through GitHub Actions. The cron is set to Beijing 07:53 to avoid GitHub's top-of-hour schedule queue.
- Sends email to `1441469055@qq.com`.
- Uses keyword grouping as the stable primary filter, then uses DeepSeek for RSS translation and daily analysis.
- Organizes sources around three signal lines:
  - AI development: official AI feeds, Chinese AI media, Product Hunt, and AI Builders
  - product and business judgment: Zhihu, SSPAI, GeekPark, TMTPost, InfoQ, TechCrunch AI, Lenny's Newsletter, Latent Space, Interconnects
  - finance and macro: Wallstreetcn, CLS, Jin10
- Filters out SaaS, strong hardware technology details, and low-signal entertainment noise.

## Source Shape

TrendRadar directly reads hotlist platforms and RSS feeds. Builders data is generated from `zarazhangrui/follow-builders` JSON snapshots into a local JSON Feed during the GitHub Actions run, then passed to TrendRadar as an RSS-compatible source.

### Hotlist platforms (`config.yaml` → `platforms.sources`)

| id | name | why |
|---|---|---|
| `zhihu` | 知乎 | 互联网 / 产品讨论 |
| `wallstreetcn-hot` | 华尔街见闻 | 金融宏观 |
| `cls-hot` | 财联社热门 | 投资快讯 |
| `github-trending-today` | GitHub Trending | 开源与 AI 工具风向 |
| `sspai` | 少数派 | 效率工具与产品体验 |
| `jin10` | 金十数据 | 宏观快讯 |

`36kr-renqi` and `36kr` were removed on 2026-09-27: the upstream NewsNow API now answers `Invalid source id` for both.

### RSS feeds (`config.yaml` → `rss.feeds`)

OpenAI official site: OpenAI News (`openai.com/news/rss.xml`), OpenAI Research, OpenAI Alignment.

Anthropic official site: Anthropic News, Anthropic Research, Anthropic Red Team.

Other AI and product: Google AI Blog, Hugging Face Blog, Product Hunt, AI Builders.

Chinese AI and product: 量子位 (`qbitai.com/feed`), 极客公园 (`geekpark.net/rss`), InfoQ 中文 (`infoq.cn/feed`), 钛媒体 (`tmtpost.com/rss`).

English first-hand: TechCrunch AI, Lenny's Newsletter, Latent Space, Interconnects, Hacker News.

`rss.huxiu.com` was removed on 2026-09-27: it returns an empty RSS channel with zero items.

### Official site sections

Neither OpenAI nor Anthropic publishes an official RSS feed for its research sections — `openai.com/research/rss.xml`, `www.anthropic.com/rss.xml`, `www.anthropic.com/research/rss.xml` and `www.anthropic.com/news/rss.xml` all return 404. Only `openai.com/news/rss.xml` is a real feed (`Content-Type: text/xml`, channel title `OpenAI News`).

The research feeds come from [0xSMW/rss-feeds](https://github.com/0xSMW/rss-feeds), which scrapes each site section and republishes it as RSS on a schedule:

| Section | URL | Cadence |
|---|---|---|
| Anthropic Research | `feeds/feed_anthropic_research.xml` | ~1 per 6 days |
| Anthropic Red Team | `feeds/feed_anthropic_red.xml` | ~1 per 2 weeks |
| OpenAI Research | `feeds/feed_openai_research.xml` | ~1 per 6 days |
| OpenAI Alignment | `feeds/feed_openai_alignment.xml` | ~1 per 2 weeks |

### Freshness windows

These sections publish irregularly, so they use `max_age_days: 14` instead of the 2-day global window. Weekly sources (Lenny's, Latent Space, Interconnects) use `max_age_days: 10`.

Trade-off to be aware of: `report.mode` is `current`, which re-pushes every matching item that is still inside its freshness window. A wide window therefore means the same research post can appear in several consecutive digests. Widen it if you want recall, narrow it if you want each item to appear only once.

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
