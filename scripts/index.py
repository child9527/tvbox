#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
from datetime import datetime, timezone, timedelta
import requests
import os
import json

OUTPUT = "index.html"

# Gitee API：获取 json 目录下所有文件
GITEE_API_URL = "https://gitee.com/api/v5/repos/child9527/mybox/contents/json"
TEMP_FILE = "temp.json"


def fetch_gitee_json_files():
    """从 Gitee API 获取所有 *.json 文件名和下载链接"""
    print("正在从 Gitee API 获取 JSON 文件列表...")

    # 从环境变量读取 Token
    token = os.getenv("GITEE_TOKEN_FOR_INDEX")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Authorization": f"token {token}",
        "Accept": "application/json",
        "Referer": "https://gitee.com/"
    }

    resp = requests.get(GITEE_API_URL, headers=headers)
    resp.raise_for_status()

    with open(TEMP_FILE, "w", encoding="utf-8") as f:
        f.write(resp.text)

    with open(TEMP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    json_files = []
    for item in data:
        if item["name"].endswith(".json"):
            json_files.append({
                "name": item["name"],
                "download_url": item["download_url"]
            })

    # 按文件名长度排序（去掉 .json）
    json_files = sorted(json_files, key=lambda x: len(x["name"].replace(".json", "")))

    print(f"发现 {len(json_files)} 个 JSON 文件：", [f["name"] for f in json_files])
    return json_files


def fetch_local_lives_files():
    """直接读取本地 lives 目录下的 *.txt 文件，生成 Raw 下载链接并加镜像前缀"""
    print("正在扫描本地 lives 目录下的 TXT 文件...")
    lives_dir = "lives"
    
    if not os.path.exists(lives_dir):
        print("⚠️ 本地未找到 lives 目录")
        return []

    lives_files = []
    # 遍历本地 lives 文件夹
    for fname in os.listdir(lives_dir):
        if fname.endswith(".txt"):
            # 拼接标准的 Raw 下载链接，并附加镜像前缀
            raw_url = f"https://github.com/child9527/tvbox/raw/refs/heads/main/lives/{fname}"
            proxy_url = f"https://gh-proxy.com/{raw_url}"
            
            lives_files.append({
                "name": fname,
                "download_url": proxy_url
            })

    # 按文件名长度排序（去掉 .txt）
    lives_files = sorted(lives_files, key=lambda x: len(x["name"].replace(".txt", "")))
    print(f"发现 {len(lives_files)} 个本地 TXT 直播文件：", [f["name"] for f in lives_files])
    return lives_files


def generate_html():
    bj_tz = timezone(timedelta(hours=8))
    now = datetime.now(bj_tz).strftime("%Y-%m-%d %H:%M:%S")
    json_files = fetch_gitee_json_files()
    lives_files = fetch_local_lives_files()

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>TVBox 自动订阅中心 · Child9527</title>
<style>
body {{
    margin: 0;
    font-family: Arial, sans-serif;
    background: #1e1e1e;
    color: #e0e0e0;
}}

/* 顶部导航栏 */
.navbar {{
    width: 100%;
    background: #2b2b2b;
    border-bottom: 2px solid #4aa3ff;
    padding: 12px 20px;
    display: flex;
    gap: 20px;
    align-items: center;
    box-shadow: 0 0 12px rgba(74,163,255,0.3);
}}

.navbar a {{
    color: #e0e0e0;
    text-decoration: none;
    font-size: 16px;
    padding: 6px 10px;
    border-radius: 6px;
    transition: 0.2s;
}}

.navbar a:hover {{
    background: #4aa3ff;
    color: #000;
}}

/* 内容区块 */
.section {{
    max-width: 1000px;
    margin: 40px auto;
    padding: 0 20px;
}}

.section-title {{
    color: #ffffff;
    font-size: 1.6rem;
    margin-bottom: 20px;
}}

.sub-title {{
    color: #4aa3ff;
    font-size: 1.2rem;
    margin: 25px 0 15px 0;
    border-left: 4px solid #4aa3ff;
    padding-left: 10px;
}}

/* 卡片网格 */
.compact-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 12px;
}}

.data-card {{
    background: #2b2b2b;
    border: 1px solid #4aa3ff;
    box-shadow: 0 0 12px rgba(74,163,255,0.4);
    border-radius: 10px;
    padding: 12px 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}

.data-label {{
    color: #e0e0e0;
    font-size: 0.95rem;
    font-weight: 500;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}

.copy-pill {{
    font-size: 0.8rem;
    color: #bbb;
    cursor: pointer;
    background: #2b2b2b;
    padding: 4px 10px;
    border-radius: 12px;
    border: 1px solid #4aa3ff;
    transition: 0.2s;
}}

.copy-pill:hover {{
    background: #4aa3ff;
    color: #000;
}}

.copy-pill.copied {{
    background: rgba(46, 204, 113, 0.15);
    color: #2ecc71;
    border-color: #2ecc71;
}}

/* 底部 */
.footer {{
    text-align: center;
    padding: 20px;
    color: #888888;
    margin-top: 40px;
}}
</style>
</head>

<body>

<!-- 导航栏 -->
<div class="navbar">
    <a href="https://child9527.github.io/">首页</a>
    <a href="https://child9527.github.io/software/">Software 软件中心</a>
    <a href="https://child9527.github.io/about/">关于本站</a>    
</div>

<!-- 内容区块 -->
<div class="section">
    <h2 class="section-title">TVBox 自动订阅中心</h2>

    <!-- 1. 点播接口（JSON） -->
    <div class="sub-title">🎬 点播接口 (JSON)</div>
    <div class="compact-grid">
"""

    # 自动生成 Gitee JSON 文件列表
    for item in json_files:
        name = item["name"].replace(".json", "")
        url = item["download_url"]
        html += f"""
        <div class="data-card">
            <span class="data-label">{name}</span>
            <span class="copy-pill" data-value="{url}" onclick="copy(this)">复制链接</span>
        </div>
"""

    html += f"""
    </div>

    <!-- 2. 直播接口（TXT） -->
    <div class="sub-title">📺 直播接口 (TXT)</div>
    <div class="compact-grid">
"""

    # 自动生成本地 TXT 文件列表
    for item in lives_files:
        name = item["name"].replace(".txt", "")
        url = item["download_url"]
        html += f"""
        <div class="data-card">
            <span class="data-label">{name}</span>
            <span class="copy-pill" data-value="{url}" onclick="copy(this)">复制链接</span>
        </div>
"""

    html += f"""
    </div>

    <div class="footer">
        自动生成时间：{now}
    </div>
</div>

<script>
function copy(el) {{
    const value = el.getAttribute("data-value");
    navigator.clipboard.writeText(value).then(() => {{
        el.classList.add("copied");
        el.innerText = "已复制";
        setTimeout(() => {{
            el.classList.remove("copied");
            el.innerText = "复制链接";
        }}, 1500);
    }});
}}
</script>

</body>
</html>
"""

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"index.html 已生成 → {OUTPUT}")


if __name__ == "__main__":
    generate_html()
