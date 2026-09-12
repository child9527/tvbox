#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import requests
from bs4 import BeautifulSoup

OUTPUT = "index.html"

# Gitee 仓库原始文件链接前缀
GITEE_RAW_PREFIX = "https://gitee.com/child9527/mybox/raw/master/json"

# Gitee 仓库文件列表页面
GITEE_FILE_LIST_URL = "https://gitee.com/child9527/mybox/tree/master/json"


def fetch_gitee_json_files():
    """从 Gitee 仓库抓取所有 *.json 文件名"""
    print("正在从 Gitee 获取 JSON 文件列表...")

    resp = requests.get(GITEE_FILE_LIST_URL)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    json_files = []

    # Gitee 文件列表的 class 名为 "file-name"
    for tag in soup.find_all("a", class_="file-name"):
        filename = tag.text.strip()
        if filename.endswith(".json"):
            json_files.append(filename)

    # 按文件名长度排序（去掉 .json）
    json_files = sorted(json_files, key=lambda x: len(x.replace(".json", "")))

    print(f"发现 {len(json_files)} 个 JSON 文件：", json_files)
    return json_files


def generate_html():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    json_files = fetch_gitee_json_files()

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TVBox 自动订阅中心 - child9527</title>
    <style>
        :root {{
            --bg-color: #1a1a1a;
            --card-bg: #2d2d2d;
            --text-color: #e0e0e0;
            --accent-color: #ff4757;
            --success-color: #2ecc71;
            --border-radius: 8px;
        }}

        body {{
            font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            margin: 0;
            padding: 20px;
        }}

        .container {{ max-width: 900px; margin: 0 auto; }}
        
        h2 {{ 
            color: var(--accent-color); 
            border-bottom: 2px solid var(--accent-color);
            padding-bottom: 8px;
            margin-top: 30px;
            font-size: 1.5rem;
        }}

        .section {{
            background: var(--card-bg);
            padding: 20px;
            border-radius: var(--border-radius);
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            margin-bottom: 20px;
        }}

        .compact-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 10px;
        }}

        .data-card {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: #363636;
            border-radius: 6px;
            border: 1px solid #404040;
            transition: background 0.2s, border-color 0.2s;
        }}

        .data-card:hover {{
            background: #404040;
            border-color: #555;
        }}

        .data-label {{ 
            color: #ddd; 
            font-size: 0.9rem;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            margin-right: 12px;
        }}

        .copy-pill {{ 
            font-size: 0.8rem;
            color: #bbb; 
            cursor: pointer;
            background: #2b2b2b;
            padding: 4px 10px;
            border-radius: 12px;
            border: 1px solid #484848;
            transition: all 0.2s ease;
            user-select: none;
            flex-shrink: 0;
        }}

        .copy-pill:hover {{ 
            background: #4a4a4a; 
            color: #fff;
            border-color: #666;
        }}

        .copy-pill.copied {{
            background: rgba(46, 204, 113, 0.15);
            color: var(--success-color);
            border-color: var(--success-color);
        }}
    </style>
</head>
<body>

<div class="container">
    <h2>TVBox 自动订阅中心</h2>
    <div class="section">
        <div class="compact-grid">
"""

    # 自动生成 Gitee JSON 文件列表
    for f in json_files:
        name = f.replace(".json", "")  # 去掉 .json
        url = f"{GITEE_RAW_PREFIX}{f}"
        html += f"""
            <div class="data-card">
                <span class="data-label">{name}</span>
                <span class="copy-pill" data-value="{url}" onclick="copy(this)">点击复制</span>
            </div>
"""

    html += f"""
        </div>
    </div>

    <div style="color:#888; font-size:0.8rem; margin-top:20px;">
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
            el.innerText = "点击复制";
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
