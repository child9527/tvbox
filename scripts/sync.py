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
    nested_pattern = r'https?://[^"\'\s]+/+(https?://(?:raw\.githubusercontent\.com|github\.com)/[^\s"\'<>]+)'
    while re.search(nested_pattern, content):
        content = re.sub(nested_pattern, r'\1', content)

    rel_pattern = r'(\"|\')\.\/([^\"\']+)\1'
    def replace_rel(match):
        quote = match.group(1)
        rel_path = match.group(2)
        raw_github_url = f"https://raw.githubusercontent.com/child9527/tvbox/main/{rel_path}"
        full_url = f"{best_mirror}{raw_github_url}"
        return f"{quote}{full_url}{quote}"
    content = re.sub(rel_pattern, replace_rel, content)

    raw_pattern = r'https://raw\.githubusercontent\.com/'
    content = re.sub(raw_pattern, best_mirror + "https://raw.githubusercontent.com/", content)

    double_mirror_pattern = re.escape(best_mirror) + r'+'
    content = re.sub(double_mirror_pattern, best_mirror, content)

    return content

# ============================================================
# 新增逻辑：严格替换 JSON 中的 "./"
# ============================================================
def replace_dot_slash(task_url, best_mirror, text):
    if '"./' not in text:
        return text

    m = re.match(
        r'https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.*)',
        task_url
    )

    if m:
        owner, repo, branch, path = m.groups()
        base_dir = os.path.dirname(path)

        prefix = (
            f'{best_mirror}https://raw.githubusercontent.com/'
            f'{owner}/{repo}/{branch}/{base_dir}/'
        )

        return text.replace('"./', f'"{prefix}')

    base_url = task_url.rsplit('/', 1)[0] + "/"
    return text.replace('"./', f'"{base_url}')

def extract_raw(url):
    if not isinstance(url, str):
        return False, url, ""
    
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
# 2. 获取 & 严格同步任务清单
# ============================================================
def load_tasks():
    old_tasks = []
    if os.path.exists(TASK_FILE):
        try:
            with open(TASK_FILE, "r", encoding="utf-8") as f:
                old_tasks = json.load(f)
        except:
            old_tasks = []

    os.makedirs("json", exist_ok=True)
    local_files = [f for f in os.listdir("json") if f.lower().endswith(".json")]
    local_names_set = {os.path.splitext(f)[0].lower(): f for f in local_files}

    old_tasks_map = {}
    for t in old_tasks:
        name = os.path.splitext(t.get("name", ""))[0].strip()
        if name:
            t["name"] = name
            old_tasks_map[name.lower()] = t

    synced_tasks = []

    for lower_name, filename in local_names_set.items():
        base_name = os.path.splitext(filename)[0]
        raw_url = f"https://raw.githubusercontent.com/child9527/tvbox/main/json/{filename}"

        if lower_name in old_tasks_map:
            task = old_tasks_map[lower_name]
            task["name"] = base_name
            if not task.get("url"):
                task["url"] = raw_url
            synced_tasks.append(task)
        else:
            synced_tasks.append({
                "name": base_name,
                "url": raw_url,
                "md5": None,
                "last_modified": None,
                "status": "local",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })

    return synced_tasks

# ============================================================
# 3. 主逻辑
# ============================================================
def main():
    best_mirror = pick_best_mirror()
    print(f"当前最快镜像为：{best_mirror}")

    tasks = load_tasks()

    for t in tasks:
        name = t.get("name", "")
        filename = f"{name}.json"
        filepath = os.path.join("json", filename)

        url = t.get("url")
        now_time = time.strftime("%Y-%m-%d %H:%M:%S")
        t["timestamp"] = now_time

        if not url:
            t["status"] = "missing_url"
            continue

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

        remote_md5 = hashlib.md5(raw_content.encode("utf-8")).hexdigest()

        if remote_md5 == t.get("md5") and os.path.exists(filepath):
            continue

        t["md5"] = remote_md5
        t["last_modified"] = now_time

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
        final_str = replace_dot_slash(t["url"], best_mirror, final_str)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_str)

    os.makedirs(os.path.dirname(TASK_FILE), exist_ok=True)
    with open(TASK_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
