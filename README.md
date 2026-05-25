# Daily AI Product Radar

This repository runs a daily TrendRadar-based digest for AI product manager job preparation.

## What Changed

- Removed the old `wewe-rss` and Railway dependency from the scheduled workflow.
- Runs TrendRadar once per day at Beijing 08:07 through GitHub Actions.
- Sends email to `1441469055@qq.com`.
- Uses AI filtering for:
  - AI models, agents, product practices
  - product thinking
  - content platforms
  - ecommerce and local life
  - China finance, banking, macro, and investment news
- Filters out SaaS, strong hardware technology details, and low-signal entertainment noise.

## Required GitHub Secrets

Existing secrets are supported:

- `DEEPSEEK_API_KEY`
- `QQ_AUTH_CODE`

Optional newer names are also supported:

- `AI_API_KEY`
- `EMAIL_PASSWORD`

Email sender and receiver are both configured as `1441469055@qq.com`.
