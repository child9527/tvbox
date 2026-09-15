#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, json, time, subprocess, requests, hashlib
from concurrent.futures import ThreadPoolExecutor
import commentjson

HEADERS = {"User-Agent": "Mozilla/5.0"}
RAW_PREFIX = "https://raw.githubusercontent.com/"
TASK_FILE = os.path.join("task", "task.json")
MIRROR_FILE = os.path.join("scripts", "mirror.txt")

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
    test_url = mirror + RAW_PREFIX + "alantang1977/X/main/X.json"
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
        return "https://gh-proxy.com/"
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
# 辅助处理逻辑
# ============================================================
def replace_relative_paths(content, best_mirror):
    """
    1. 清理别人硬编码的第三方加速前缀（支持多层循环剥离，如 https://web.ksx.qzz.io/https://raw.github...）
    2. 将 ./ 相对路径替换为 最快镜像 + GitHub Raw 路径
    3. 将所有裸露的 raw.githubusercontent.com 替换为你 mirror.txt 里测出的最快镜像
    """
    # 步骤 A: 剥离嵌套的前置第三方代理前缀（打破域名斜杠限制，支持完整剥离）
    nested_pattern = r'https?://[^"\'\s]+/+(https?://(?:raw\.githubusercontent\.com|github\.com)/[^\s"\'<>]+)'
    while re.search(nested_pattern, content):
        content = re.sub(nested_pattern, r'\1', content)

    # 步骤 B: 将 ./ 相对路径替换为当前仓库的 raw 路径 + 最快镜像
    rel_pattern = r'(\"|\')\.\/([^\"\']+)\1'
    def replace_rel(match):
        quote = match.group(1)
        rel_path = match.group(2)
        raw_github_url = f"https://raw.githubusercontent.com/child9527/tvbox/main/{rel_path}"
        full_url = f"{best_mirror}{raw_github_url}"
        return f"{quote}{full_url}{quote}"
    content = re.sub(rel_pattern, replace_rel, content)

    # 步骤 C: 统一将所有直连 raw.githubusercontent.com 替换为你测出的 best_mirror
    raw_pattern = r'https://raw\.githubusercontent\.com/'
    content = re.sub(raw_pattern, best_mirror + "https://raw.githubusercontent.com/", content)

    # 步骤 D: 修正可能因反复替换导致的镜像双重拼接
    double_mirror_pattern = re.escape(best_mirror) + r'+'
    content = re.sub(double_mirror_pattern, best_mirror, content)

    return content

def extract_raw(url):
    if not isinstance(url, str):
        return False, url, ""
    
    # 清理 URL 中可能嵌套的前置第三方代理
    url = re.sub(r'^https?://[^"\'\s]+/+(https?://)', r'\1', url)

    pat = r'(https?://)?(raw\.githubusercontent\.com|github\.com)/[^\s"\'<>]+'
    m = re.search(pat, url)
    if not m:
        return False, url, ""
    raw = m.group(0)
    if not raw.startswith("http"):
        raw = "https://" + raw
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

def decrypt(text):
    tmp_in = "tmp_in.txt"
    tmp_out = "tmp_out.json"
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tvbox_script = os.path.join(script_dir, "tvbox.py")
    
    try:
        with open(tmp_in, "w", encoding="utf-8") as f:
            f.write(text)
        subprocess.run(["python", tvbox_script, tmp_in, tmp_out], check=True)
        res = open(tmp_out, "r", encoding="utf-8").read()
        return res
    finally:
        for f in [tmp_in, tmp_out]:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass

# ============================================================
# 2. 获取 & 补全任务清单
# ============================================================
def load_tasks():
    tasks = []
    if os.path.exists(TASK_FILE):
        try:
            with open(TASK_FILE, "r", encoding="utf-8") as f:
                tasks = json.load(f)
        except:
            tasks = []

    if not os.path.exists("json"):
        os.makedirs("json", exist_ok=True)

    for fn in os.listdir("json"):
        if fn.lower().endswith(".json"):
            base_name = os.path.splitext(fn)[0]
            found = next((t for t in tasks if t.get("name", "").strip().lower() in [base_name.lower(), fn.lower()]), None)
            raw_url = f"https://raw.githubusercontent.com/child9527/tvbox/main/json/{fn}"

            if found:
                found["name"] = base_name
                if not found.get("url"):
                    found["url"] = raw_url
            else:
                tasks.append({
                    "name": base_name,
                    "url": raw_url,
                    "md5": None,
                    "last_modified": None,
                    "status": "local",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
    return tasks

# ============================================================
# 3. 主逻辑
# ============================================================
def main():
    best_mirror = pick_best_mirror()
    print(f"当前最快镜像为：{best_mirror}")

    tasks = load_tasks()

    for t in tasks:
        raw_name = t.get("name", "")
        name = os.path.splitext(raw_name)[0]
        t["name"] = name

        filename = f"{name}.json"
        filepath = os.path.join("json", filename)

        url = t.get("url")
        t["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

        if not url:
            t["status"] = "missing_url"
            continue

        # 1. 拉取远程原始文本
        is_gh, raw, _ = extract_raw(url)
        try:
            r = requests.get(raw if is_gh else url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                t["status"] = f"http{r.status_code}"
                continue
            raw_content = r.content.decode("utf-8", errors="ignore").strip()
            t["status"] = "ok"
        except Exception:
            t["status"] = "error"
            continue

        # 2. 计算【远程源文本 MD5】
        remote_md5 = hashlib.md5(raw_content.encode("utf-8")).hexdigest()

        # 3. 对比远程 MD5
        if remote_md5 == t.get("md5") and os.path.exists(filepath):
            continue

        # 4. 执行解密、清理与镜像剥离/重组
        t["md5"] = remote_md5
        t["last_modified"] = time.strftime("%Y-%m-%d %H:%M:%S")

        content = raw_content
        if is_encrypted(content):
            content = decrypt(content)

        cleaned = clean_comments(content)
        
        obj = None
        try:
            obj = commentjson.loads(cleaned)
        except:
            try:
                obj = json.loads(cleaned)
            except:
                t["status"] = "invalid_json"
                continue

        final_str = json.dumps(obj, ensure_ascii=False, indent=2)
        final_str = replace_relative_paths(final_str, best_mirror)

        # 5. 保存文件
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_str)

    os.makedirs(os.path.dirname(TASK_FILE), exist_ok=True)
    with open(TASK_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
