#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import datetime

OUTPUT = "index.html"

def list_json_files():
    files = []
    root = "json"
    if os.path.exists(root):
        for f in os.listdir(root):
            if f.endswith(".json"):
                files.append(f)
    return sorted(files)

def generate_html():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    json_files = list_json_files()

    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>TVBox 自动订阅中心</title>
<style>
body {{
    font-family: Arial, sans-serif;
    background: #f7f7f7;
    padding: 20px;
}}
.container {{
    max-width: 800px;
    margin: auto;
    background: white;
    padding: 20px;
    border-radius: 10px;
}}
h1 {{
    text-align: center;
}}
.file-list {{
    margin-top: 20px;
}}
.file-item {{
    padding: 10px;
    border-bottom: 1px solid #ddd;
}}
a {{
    color: #0078ff;
    text-decoration: none;
}}
a:hover {{
    text-decoration: underline;
}}
.footer {{
    margin-top: 30px;
    text-align: center;
    color: #888;
}}
</style>
</head>
<body>
<div class="container">
<h1>TVBox 自动订阅中心</h1>
<p>自动生成时间：{now}</p>

<h2>订阅文件列表</h2>
<div class="file-list">
"""

    for f in json_files:
        html += f'<div class="file-item"><a href="json/{f}" target="_blank">{f}</a></div>\n'

    html += """
</div>

<div class="footer">
TVBox 自动化系统 · GitHub Pages 自动发布
</div>

</div>
</body>
</html>
"""

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"index.html 已生成 → {OUTPUT}")

if __name__ == "__main__":
    generate_html()
