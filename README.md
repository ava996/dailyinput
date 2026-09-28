# Daily Input · 主题日报

服务于 AI 产品经理学习、求职与行业判断。GitHub Actions 每天北京时间 07:53 排队运行，实际开始时间可能延后。API、RSS 和 Builders 统一按主题筛选、去重、翻译和分析，再发送邮件。

## 主题与阅读量

| 主题 | 每日上限 | 入选依据 |
|---|---:|---|
| AI 模型与 Agent | 4 | 模型能力、Agent、多模态、API、评测与官方研究 |
| AI 工具与效率 | 3 | AI 编程、办公、知识管理、提示词与可复用工作流 |
| 产品思考 | 4 | 用户研究、需求验证、体验设计、实验、激活与留存 |
| 内容平台 | 2 | 内容平台动作、创作者生态、推荐与社区治理 |
| 电商与本地生活 | 2 | 电商、即时零售、外卖、团购与平台变化 |
| 宏观政策与传导 | 3 | 货币财政政策、利率汇率、通胀和经济传导 |
| 金融与投资 | 2 | 金融监管、银行、市场、财报与估值 |
| 求职与职业机会 | 2 | 明确的招聘、岗位、面试、实习与职业发展 |

最多 22 条；没有合格内容的主题不凑数。每个主题同一来源最多 2 条，轮流从不同来源选取。AI 官方源、产品方法论来源优先。限额在所有渠道合并后执行。

“增长、转化、会员、订阅、定价、App、产品经理”不再单独触发产品分类。“产品经理如何设计可用性测试”属于产品思考；“AI 产品经理秋招岗位”才属于求职。华尔街见闻和财联社只参与宏观、金融主题，不占产品和 AI 的名额；这意味着它们的纯 AI 发布稿会被略过，由 AI 专门来源提供覆盖。

## 来源

来源在 `config/config.yaml` 中维护。传输方式仅用于抓取，不决定邮件栏目。

- AI：OpenAI News/Research/Alignment、Anthropic News/Research、Google AI、量子位、TechCrunch AI、Latent Space。
- 产品与实践：人人都是产品经理、Lenny’s Newsletter、Product Hunt、AI Builders；知乎、GitHub Trending、InfoQ 中文、Hacker News 提供补充候选，必须通过主题规则。
- 宏观金融：华尔街见闻文章、财联社深度。移除财联社热门和电报，减少重复快讯与市场噪声。

OpenAI/Anthropic 的部分分栏来自第三方 `0xSMW/rss-feeds` 镜像，原文章链接仍指向发布网站。Builders 来自 `zarazhangrui/follow-builders`，在 Actions 中转换为本地 JSON Feed。

保留来源各自的时间窗：一般 2–5 天，周更 10 天，研究分栏 14 天。Builders 仅接受有效且近期的发布时间，缺失、无效或明显未来日期不再当作新内容；作者简介不参与内容。

## 筛选与展示实现

1. TrendRadar 抓取并执行 RSS 新鲜度过滤。
2. `config/frequency_words.txt` 只做无上限的候选收集；不要在此添加 `@N`，避免在合并前截掉内容。
3. `scripts/topic_digest.py` 用同一套中英文标题规则为每篇确定一个主题，按 URL（忽略追踪参数）或规范化标题去重，然后执行主题配额。只匹配标题，不能保证识别含义相同但标题和链接都不同的报道。
4. 同一份入选列表进入 AI 分析和翻译，再生成邮件 HTML。来源和原文链接保留在文章下方；没有 RSS 订阅更新或 RSS 深度洞察专栏。

`filter.method: keyword` 是上游的兼容入口；实际主题规则在 Python 模块中。`ai_interests.txt` 只记录编辑偏好，不是线上分类开关。`display.regions.rss: true` 必须保留以获取候选；`region_order` 不包含 rss，且合并后已清空独立 RSS 列表。英文标题通过统一列表的 hotlist 翻译路径翻译。

上游固定为 TrendRadar `792bcc3928b1617bba09df34989fd5675c159b86`。`scripts/apply_topic_patch.py` 在 AI 分析之前接入合并步骤，并保留 source_id。补丁检查代码位置并支持重复应用；升级上游需重新通过集成测试，不能直接改回浮动 master。

## Actions 与预览

- `schedule`：正常发送每日邮件。
- `push`（配置、脚本、测试或工作流变化）：测试并生成真实预览，不发送邮件。
- `workflow_dispatch`：默认只生成预览；需要发送时显式勾选 `send_email`。
- 运行产物 `dailyinput-preview-<run_id>` 保存 `current.html` 和 `topic-selection.json` 7 天。审计文件含真实入选数、每篇主题、来源、URL 及候选列表。

必需 Secrets：`DEEPSEEK_API_KEY` 或 `AI_API_KEY`。邮件发送另需 `QQ_AUTH_CODE` 或 `EMAIL_PASSWORD`，发送与接收地址保持现有配置。

## 验证

```sh
python -m unittest discover -s tests -v
python scripts/apply_topic_patch.py /path/to/TrendRadar
TRENDRADAR_ROOT=/path/to/TrendRadar /path/to/TrendRadar/.venv/bin/python -m unittest discover -s tests -v
```

第一条只跑独立规则测试；集成测试需要已经安装依赖并应用补丁的固定版本 TrendRadar。Actions 会执行完整测试，覆盖真实上游候选结构、分类、配额、去重、RSS-only、API-only 和最终 HTML。

`.github/workflows/keepalive.yml` 沿用现有半月提交机制；可配置 `KEEPALIVE_PAT`。不改变既有 keepalive 工作流。
