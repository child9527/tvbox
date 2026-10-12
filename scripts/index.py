#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
from urllib.parse import quote
from datetime import datetime, timezone, timedelta
from jinja2 import Environment, FileSystemLoader, select_autoescape


# ============================================================
# 模板渲染
# ============================================================

# 模板目录（相对于项目根目录）
TEMPLATE_DIR = "templates"


def render(template_name, **context):
    """
    渲染指定模板。

    参数：
        template_name: 模板文件路径（相对 templates/ 目录），如 "base.html.j2"
        **context:     传给模板的变量

    返回：
        渲染后的 HTML 字符串
    """
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,      # 块标签后的第一个换行符自动去掉
        lstrip_blocks=True,    # 块标签前的空白自动去掉
    )
    template = env.get_template(template_name)
    return template.render(**context)


# ============================================================
# 板块构造
# ============================================================

def section_software_list(title, items):
    """
    软件卡片列表板块（带筛选按钮）。

    参数：
        title: 板块标题
        items: 软件列表，每项结构：
            {
                "name":        展示名,
                "version":     版本号,
                "url":         原始下载链接,
                "file_size":   文件大小（字节）,
                "file_size_text": 格式化后的大小（如 "12.3 MB"）,
                "icon":        图标 URL（可为空）,
                "type":        分类（如 "Win64"、"Android"）,
                "description": 简介,
                "mirrors":     [(镜像名, 镜像链接), ...],
            }

    返回：
        {
            "title":      标题,
            "type":       "software_list",
            "items":      items,
            "types":      去重后的分类列表（按出现顺序）,
            "first_type": 第一个分类（用于默认显示）,
        }
    """
    types = list(dict.fromkeys([it["type"] for it in items if it.get("type")]))
    return {
        "title": title,
        "type": "software_list",
        "items": items,
        "types": types,
        "first_type": types[0] if types else None,
    }


def section_copy_cards(title, items):
    """
    复制型卡片（网格）板块。

    参数：
        title: 板块标题
        items: 卡片列表，每项结构：
            {
                "name":        展示名,
                "url_literal": 已经过 json.dumps 的 JS 字符串字面量,
            }

    返回：
        {
            "title": 标题,
            "type":  "copy_cards",
            "items": items,
        }
    """
    return {
        "title": title,
        "type": "copy_cards",
        "items": items,
    }


def section_copy_cards_wide(title, items):
    """
    复制型卡片（单行大卡片）板块，支持多张。

    items 里每项结构：
        {
            "name":            展示名,
            "js_var":          JS 变量名（英文，全局唯一，如 "EXTENSION_JS_TEXT"）,
            "content_literal": 已经过 json.dumps 的 JS 字符串字面量,
        }

    示例：
        section_copy_cards_wide("📋 规则及配置", [
            {
                "name": "Clash Verge Rev全局扩展覆写脚本",
                "js_var": "EXTENSION_JS_TEXT",
                "content_literal": json.dumps(js_text, ensure_ascii=False),
            },
            {
                "name": "Clash 配置模板",
                "js_var": "CLASH_CONFIG_TEXT",
                "content_literal": json.dumps(config_text, ensure_ascii=False),
            },
        ])
    """
    return {
        "title": title,
        "type": "copy_cards_wide",
        "items": items,
    }


# ============================================================
# 配置
# ============================================================

# Gitee API：获取 json 目录下所有文件
GITEE_API_URL = "https://gitee.com/api/v5/repos/child9527/mybox/contents/json"

# 本地 lives 目录
LIVES_DIR = "lives"

# GitHub raw 前缀（用于拼接 lives 文件的 raw 链接）
GITHUB_RAW_PREFIX = "https://github.com/child9527/tvbox/raw/refs/heads/main/lives/"

# 镜像前缀
GH_PROXY = "https://gh-proxy.com/"

# 输出文件
OUTPUT = "index.html"


# ============================================================
# 数据获取
# ============================================================

def fetch_gitee_json_files():
    """
    从 Gitee API 获取 json 目录下所有 *.json 文件。
    返回 [{name, url_literal}]，name 已去掉 .json 后缀。
    """
    print("正在从 Gitee API 获取 JSON 文件列表...")

    token = os.getenv("GITEE_TOKEN_FOR_INDEX")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Authorization": f"token {token}",
        "Accept": "application/json",
        "Referer": "https://gitee.com/",
    }

    resp = requests.get(GITEE_API_URL, headers=headers)
    resp.raise_for_status()

    data = resp.json()

    items = []
    for item in data:
        if not item["name"].endswith(".json"):
            continue

        display_name = item["name"][:-len(".json")]   # 去掉 .json 后缀
        download_url = item["download_url"]

        items.append({
            "name": display_name,
            "url_literal": json.dumps(download_url, ensure_ascii=False),
        })

    # 按名字长度排序
    items.sort(key=lambda x: len(x["name"]))

    print(f"发现 {len(items)} 个 JSON 文件")
    return items


def fetch_local_lives_files():
    """
    扫描本地 lives 目录下所有 *.txt 文件。
    返回 [{name, url_literal}]，name 已去掉 .txt 后缀。
    """
    print("正在扫描本地 lives 目录下的 TXT 文件...")

    if not os.path.exists(LIVES_DIR):
        print(f"⚠️ 本地未找到目录: {LIVES_DIR}")
        return []

    items = []
    for fname in os.listdir(LIVES_DIR):
        if not fname.endswith(".txt"):
            continue

        # 拼接标准 raw 链接，并附加镜像前缀
        raw_url = f"{GITHUB_RAW_PREFIX}{quote(fname)}"
        proxy_url = f"{GH_PROXY}{raw_url}"

        display_name = fname[:-len(".txt")]   # 去掉 .txt 后缀

        items.append({
            "name": display_name,
            "url_literal": json.dumps(proxy_url, ensure_ascii=False),
        })

    # 按名字长度排序
    items.sort(key=lambda x: len(x["name"]))

    print(f"发现 {len(items)} 个本地 TXT 直播文件")
    return items


# ============================================================
# 组装 sections
# ============================================================

def build_sections():
    """
    组装所有板块。

    以后新增板块，只改这里：
        sections.append(section_xxx("板块标题", 数据))
    """
    sections = []

    # 板块 1：点播接口（Gitee json 文件）
    json_items = fetch_gitee_json_files()
    sections.append(section_copy_cards("🎬 点播接口", json_items))

    # 板块 2：直播接口（本地 lives txt 文件）
    lives_items = fetch_local_lives_files()
    sections.append(section_copy_cards("📺 直播接口", lives_items))

    return sections


# ============================================================
# 主入口
# ============================================================

def main():
    bj_tz = timezone(timedelta(hours=8))
    now = datetime.now(bj_tz).strftime("%Y-%m-%d %H:%M:%S")

    sections = build_sections()

    html = render(
        "base.html.j2",
        sections=sections,
        now=now,
        page_title="TVBox订阅",
    )

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"index.html 生成成功！共 {len(sections)} 个板块。")


if __name__ == "__main__":
    main()
