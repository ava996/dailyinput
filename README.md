# Daily AI Product Radar

This repository runs a daily TrendRadar-based digest for AI product manager job preparation.

## What Changed

- Removed the old `wewe-rss` and Railway dependency from the scheduled workflow.
- Runs TrendRadar once per day at Beijing 08:00 through GitHub Actions.
- Sends email to `1441469055@qq.com`.
- Uses keyword grouping as the stable primary filter, then uses DeepSeek for RSS translation and daily analysis.
- Organizes sources around three signal lines:
  - AI development: official AI feeds, Product Hunt, and AI Builders
  - product and business judgment: Zhihu, 36Kr, Huxiu, product/platform/business topics
  - finance and macro: Wallstreetcn and CLS
- Filters out SaaS, strong hardware technology details, and low-signal entertainment noise.

## Source Shape

TrendRadar directly reads hotlist platforms and RSS feeds. Builders data is generated from `zarazhangrui/follow-builders` JSON snapshots into a local JSON Feed during the GitHub Actions run, then passed to TrendRadar as an RSS-compatible source.

## Required GitHub Secrets

Existing secrets are supported:

- `DEEPSEEK_API_KEY`
- `QQ_AUTH_CODE`

Optional newer names are also supported:

- `AI_API_KEY`
- `EMAIL_PASSWORD`

Email sender and receiver are both configured as `1441469055@qq.com`.

## Filtering Strategy

Keep `filter.method` set to `keyword` for production runs. TrendRadar's `ai` filter is an AI-only gate: if classification returns zero matches, it replaces the keyword result with an empty report and skips email delivery. Keyword filtering keeps the digest stable while DeepSeek still adds analysis and translation after the candidate set is selected.
