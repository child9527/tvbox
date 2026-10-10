#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
from urllib.parse import quote
from datetime import datetime, timezone, timedelta

from renderer import render
from sections import section_copy_cards


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
