# Daily AI Product Radar

This repository runs a daily TrendRadar-based digest for AI product manager job preparation.

## What Changed

- Removed the old `wewe-rss` and Railway dependency from the scheduled workflow.
- Runs TrendRadar once per day at Beijing 08:07 through GitHub Actions.
- Sends email to `1441469055@qq.com`.
- Uses DeepSeek for AI filtering, RSS translation, and daily analysis.
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
