# Daily Input · 主题日报

服务于 AI 产品经理学习、求职与行业判断。GitHub Actions 每天北京时间 07:53 排队运行，实际开始时间可能延后。API、RSS 和 Builders 统一按主题筛选、去重、翻译和分析，再发送邮件。

## 主题与阅读量

| 主题 | 入选依据 |
|---|---|
| AI 模型与工具 | 模型能力、Agent、多模态、API、评测与官方研究；AI 编程、办公、知识管理、提示词与可复用工作流 |
| 产品思考 | 用户研究、需求验证、体验设计、实验、激活与留存 |
| 内容平台 | 内容平台动作、创作者生态、推荐与社区治理 |
| 电商与本地生活 | 电商、即时零售、外卖、团购与平台变化 |
| 宏观政策与传导 | 货币财政政策、利率汇率、通胀和经济传导 |
| 金融与投资 | 金融监管、银行、市场、财报与估值 |

**主题每日条数不固定，由当天候选量决定，全篇最多 22 条。** 没有合格内容的主题不出现，也不凑数。分配方式见下。

## 主题分配规则

配额不写死在配置里，由 `scripts/topic_digest.py` 的 `allocate_topic_budgets` 每天现算：

1. 统计每个主题当天有多少可用条数、覆盖多少个不同来源。
2. 权重取 `min(条数, 3 × 来源数)`——用条数衡量当天的信息量，同时防止某个高频源（一次返回 50 条的那种）独占整份日报。
3. 有内容的主题先各保底 1 条，剩余名额按权重用最大余数法分配，总数不超过 22。
4. 主题内按来源轮流选取，同一来源在同一主题最多 2 条（来源少于名额时才允许更多），保证一栏里能看到多个来源而不是同一个源刷屏。

效果是：某天 AI 内容特别多，AI 栏就厚；某天产品方法论文章扎堆，产品栏就厚。全篇永远不超 22 条。

“增长、转化、会员、订阅、定价、App、产品经理”不单独触发产品分类。“产品经理如何设计可用性测试”属于产品思考。**求职与职业机会已移除**：含招聘、岗位、面试、简历、实习、裁员、hiring、layoffs 等信号的标题直接丢弃，不会再被改派到 AI 或产品栏。华尔街见闻和财联社只参与宏观、金融主题，不占产品和 AI 的名额；它们的纯 AI 发布稿会被略过，由 AI 专门来源提供覆盖。

## 来源

来源在 `config/config.yaml` 中维护。传输方式仅用于抓取，不决定邮件栏目。

- AI：OpenAI News/Research/Alignment、Anthropic News/Research、Google AI、量子位、TechCrunch AI、Latent Space。
- 产品与实践：人人都是产品经理、Lenny’s Newsletter、Product Hunt、AI Builders；知乎、GitHub Trending、InfoQ 中文、Hacker News 提供补充候选，必须通过主题规则。
- 宏观金融：华尔街见闻文章、财联社深度。移除财联社热门和电报，减少重复快讯与市场噪声。
- 中文媒体（替代已停用的公众号）：36氪、极客公园、新智元、虎嗅、增长黑盒。

### 关于那批公众号

2026-05-25 之前，日报用自建 **wewe-rss** 把 16 个公众号转成 RSS（脚本 `digest.py`）。换成 TrendRadar 时那段脚本被整体删除，公众号列表从未进入 `config.yaml`；原 wewe-rss 的 Railway 实例现已删除（`Application not found`），旧 feed id 全部作废。

大部分公众号至今没有可用的官网 RSS，只有 5 个找到了替代并已配回：**36氪、极客公园、新智元、虎嗅、增长黑盒**（其中虎嗅官网 RSS 已 403，走 RSSHub 公共镜像）。另有 2 个（人人都是产品经理、量子位）本来就有官网 RSS，早就在跑。

仍未覆盖：晚点LatePost、腾讯研究院、机器之心、运营研究社、电商派Pro、乱翻书、野生运营社区、PyTorch研习社、特工宇宙、一天一篇经济学人 —— 这些只有公众号，没有可用的官网或第三方 RSS。要覆盖它们，只能重新自建公众号转 RSS 服务（如 `cooderl/wewe-rss`）。

OpenAI/Anthropic 的部分分栏来自第三方 `0xSMW/rss-feeds` 镜像，原文章链接仍指向发布网站。Builders 来自 `zarazhangrui/follow-builders`，在 Actions 中转换为本地 JSON Feed。

来源时间窗按各源的**实际更新频率**单独设定，不能一刀切：快讯类 2–5 天，周更 10 天，研究分栏 14–21 天，对齐研究 45 天，双月刊 60 天。窗口定得太短会让低频源**整栏永久为空**——这不是抓取失败，`Anthropic News` 和 `OpenAI Alignment` 就曾分别因为 5 天 / 14 天窗口而一条都留不下来。Builders 仅接受有效且近期的发布时间，缺失、无效或明显未来日期不当作新内容；作者简介不参与内容。

## 筛选与展示实现

1. TrendRadar 抓取并执行 RSS 新鲜度过滤。
2. `config/frequency_words.txt` 只做无上限的候选收集；不要在此添加 `@N`，避免在合并前截掉内容。
3. `scripts/topic_digest.py` 用同一套中英文标题规则为每篇确定一个主题，按 URL（忽略追踪参数）或规范化标题去重，再按当天供应分配主题名额（见上一节）。只匹配标题，不能保证识别含义相同但标题和链接都不同的报道。
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
