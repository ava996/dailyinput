#!/usr/bin/env python3
"""Apply the small, checked adapter to the pinned TrendRadar checkout."""

from __future__ import annotations

import argparse
from pathlib import Path


PIPELINE = '''        # dailyinput: merge channels before analysis, translation and rendering.
        from trendradar.dailyinput_topics import build_topic_stats
        import json

        candidates = [dict(item) for group in (stats or []) + (rss_items or [])
                      for item in group.get("titles", [])]
        stats = build_topic_stats(stats, rss_items)
        rss_items, rss_new_items = None, None
        total_titles = len(candidates)
        id_to_name = dict(id_to_name or {})
        for group in stats:
            for item in group["titles"]:
                id_to_name[item["source_id"]] = item["source_name"]
        selected_count = sum(group["count"] for group in stats)
        audit_path = Path("output/topic-selection.json")
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.write_text(json.dumps({
            "candidate_count": total_titles, "selected_count": selected_count,
            "topics": stats, "candidates": candidates,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[主题日报] {total_titles} 条候选 -> {selected_count} 条精选，{len(stats)} 个主题")

'''

HEADER = '''    # dailyinput: unified source and article counts.
    source_total = platform_total + rss_source_total
    source_success = platform_success + rss_source_success
    html += f"""
                    <div class="info-item">
                        <span class="info-label">精选 / 候选</span>
                        <span class="info-value">{hot_news_count} / {hotlist_total}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">可用来源</span>
                        <span class="info-value">{source_success} / {source_total}</span>
                    </div>"""

'''


def replace_once(text: str, before: str, after: str, label: str) -> str:
    if after in text:
        return text
    if text.count(before) != 1:
        raise ValueError(f"Upstream compatibility check failed: {label}")
    return text.replace(before, after, 1)


def apply_patch(root: Path) -> None:
    main_path = root / "trendradar/__main__.py"
    analyzer_path = root / "trendradar/core/analyzer.py"
    html_path = root / "trendradar/report/html.py"
    main = main_path.read_text(encoding="utf-8")
    main = replace_once(main, "        self._hotlist_total_count = total_titles\n",
                        PIPELINE + "        self._hotlist_total_count = total_titles\n", "pipeline")

    analyzer = analyzer_path.read_text(encoding="utf-8")
    analyzer = replace_once(analyzer, '                        "source_name": source_name,\n',
                            '                        "source_name": source_name,\n                        "source_id": source_id,\n', "API source identity")
    anchor = '                    "source_name": item.get("feed_name", item.get("feed_id", "RSS")),\n'
    analyzer = replace_once(analyzer, anchor, anchor + '                    "source_id": item.get("feed_id", ""),\n                    "published_at": published_at,\n', "RSS source identity")

    html = html_path.read_text(encoding="utf-8")
    if HEADER not in html:
        start = html.index("    # 3. 热榜命中\n")
        end = html.index("    # 8. AI 分析\n", start)
        html = html[:start] + HEADER + html[end:]
    html = html.replace('<div class="header-title">热点新闻分析</div>', '<div class="header-title">Daily Input · 主题日报</div>')
    html = html.replace('mode_display = "当前榜单"', 'mode_display = "主题日报"')

    # Validate every edit before writing anything to the upstream checkout.
    for path, content in ((main_path, main), (analyzer_path, analyzer), (html_path, html)):
        compile(content, str(path), "exec")
    for path, content in ((main_path, main), (analyzer_path, analyzer), (html_path, html)):
        path.write_text(content, encoding="utf-8")
    module = Path(__file__).with_name("topic_digest.py").read_text(encoding="utf-8")
    (root / "trendradar/dailyinput_topics.py").write_text(module, encoding="utf-8")
    print("[dailyinput] Unified topic adapter applied")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trendradar_root", type=Path)
    apply_patch(parser.parse_args().trendradar_root)
