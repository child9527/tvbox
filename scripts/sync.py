#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, json, time, subprocess, requests, hashlib
from concurrent.futures import ThreadPoolExecutor
import commentjson

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8"
}
# 部分源站（如 kstore）会拒绝浏览器 UA，需用 TVBox/okhttp 客户端身份
TVBOX_HEADERS = {
    "User-Agent": "okhttp/3.12.0",
    "Accept": "*/*",
}
TASK_FILE = os.path.join("task", "task.json")
MIRROR_FILE = os.path.join("scripts", "mirror.txt")
JSON_DIR = "json"
REPO_RAW_PREFIX = "https://raw.githubusercontent.com/child9527/tvbox/main/json/"

# ============================================================
# 1. 镜像测速
# ============================================================
def load_mirrors():
    if not os.path.exists(MIRROR_FILE):
        return []
    mirrors = []
    with open(MIRROR_FILE, "r", encoding="utf-8") as f:
        for line in f:
            m = line.strip()
            if m and not m.startswith("#"):
                if not m.endswith("/"):
                    m += "/"
                mirrors.append(m)
    return mirrors

def test_mirror(mirror):
    test_url = mirror + "https://github.com/child9527/tvbox/raw/refs/heads/main/Readme.md"
    try:
        start = time.time()
        r = requests.get(test_url, headers=HEADERS, timeout=4)
        text = r.content.decode("utf-8", errors="ignore").lstrip()
        if r.status_code == 200 and (text.startswith("{") or text.startswith("[") or text.startswith("//")):
            return mirror, time.time() - start
    except:
        pass
    return mirror, None

def pick_best_mirror():
    mirrors = load_mirrors()
    if not mirrors:
        return "https://v4.gh-proxy.org/"
    results = {}
    with ThreadPoolExecutor(max_workers=len(mirrors)) as ex:
        futures = [ex.submit(test_mirror, m) for m in mirrors]
        for f in futures:
            m, d = f.result()
            if d is not None:
                results[m] = d
    if not results:
        return mirrors[0]
    return sorted(results, key=results.get)[0]

# ============================================================
# 2. 路径处理逻辑（强制替换镜像版）
# ============================================================
def parse_github_raw(url):
    m = re.match(
        r'https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.*)',
        url
    )
    if not m:
        return None
    owner, repo, branch, path = m.groups()
    base_dir = os.path.dirname(path)
    return owner, repo, branch, base_dir

def replace_dot_slash(task_url, best_mirror, text):
    info = parse_github_raw(task_url)

    if info:
        owner, repo, branch, base_dir = info
        dir_part = f"{base_dir}/" if base_dir else ""
        prefix = f'{best_mirror}https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{dir_part}'
    else:
        prefix = task_url.rsplit('/', 1)[0] + "/"

    prefix = re.sub(r'(?<!:)/{2,}', '/', prefix)

    out = []
    i = 0
    n = len(text)

    while i < n:
        if text[i] == '"' and i+2 < n and text[i+1] == '.' and text[i+2] == '/':
            out.append('"')
            start = i + 3
            j = start

            while j < n and text[j] not in [';', '"']:
                j += 1

            url_part = text[start:j]
            end_char = text[j]

            url_part = url_part.lstrip('/')

            new_url = prefix + url_part
            out.append(new_url)
            out.append(end_char)

            i = j + 1
        else:
            out.append(text[i])
            i += 1

    return "".join(out)

def replace_relative_paths(content, best_mirror):
    pattern = r'(?:https?://[^"\'\s]+/)*(https://raw\.githubusercontent\.com/)'
    content = re.sub(pattern, r'%s\1' % best_mirror, content)
    return content

# ============================================================
# JSON 清理与解密
# ============================================================
def extract_raw(url):
    if not isinstance(url, str):
        return False, url, ""
    
    pat = r'^https?://(raw\.githubusercontent\.com|github\.com)/[^\s"\'<>]+'
    m = re.match(pat, url)
    if not m:
        return False, url, ""
    
    raw = m.group(0)
    raw = re.sub(
        r'https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.*)',
        r'https://raw.githubusercontent.com/\1/\2/\3/\4',
        raw
    )
    raw = raw.replace("/refs/heads/", "/")
    return True, raw, ""

def clean_comments(text):
    text = text.replace("\r", "")
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("//") or s.startswith("#"):
            continue
        lines.append(line)
    t = "\n".join(lines)
    t = re.sub(r",\s*([\}\]])", r"\1", t)
    return t

def is_encrypted(text):
    text = text.strip()
    if all(c in "0123456789abcdefABCDEF" for c in text):
        return ("2423" in text and "2324" in text)
    return False
