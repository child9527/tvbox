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
# 镜像测速与路径处理
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

def replace_relative_paths(content, best_mirror):
    """将 json 文件中的 ./ 相对路径替换为最快镜像 + GitHub Raw 路径"""
    pattern = r'(\"|\')\.\/([^\"\']+)\1'
    def replace_fn(match):
        quote = match.group(1)
        rel_path = match.group(2)
        raw_github_url = f"https://raw.githubusercontent.com/child9527/tvbox/main/{rel_path}"
        full_url = f"{best_mirror}{raw_github_url}"
        return f"{quote}{full_url}{quote}"
    return re.sub(pattern, replace_fn, content)

# ============================================================
# URL 转换
# ============================================================
def extract_raw(url):
    if not isinstance(url, str):
        return False, url, ""
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

# ============================================================
# 注释清理
# ============================================================
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

# ============================================================
# 加密检测与解密
# ============================================================
def is_encrypted(text):
    text = text.strip()
    if all(c in "0123456789abcdefABCDEF" for c in text):
        return ("2423" in text and "2324" in text)
    return False

def decrypt(text):
    tmp_in = "tmp_in.txt"
    tmp_out = "tmp_out.json"
    
    # 动态获取 scripts/tvbox.py 的精准绝对路径
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
# 读取任务（task/task.json + json目录补充）
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
            filepath = os.path.join("json", fn)
            try:
                with open(filepath, "rb") as f:
                    md5_val = hashlib.md5(f.read()).hexdigest()
            except:
                md5_val = None

            found = next((t for t in tasks if t.get("name", "").strip().lower() == fn.strip().lower()), None)
            raw_url = f"https://raw.githubusercontent.com/child9527/tvbox/main/json/{fn}"

            if found:
                if "child9527/tvbox" in found.get("url", "") or not found.get("url"):
                    found["url"] = raw_url
                found["md5"] = md5_val
            else:
                tasks.append({
                    "name": fn,
                    "url": raw_url,
                    "md5": md5_val,
                    "last_modified": None,
                    "status": "local",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
    return tasks

# ============================================================
# 主逻辑
# ============================================================
def main():
    best_mirror = pick_best_mirror()
    tasks = load_tasks()

    for t in tasks:
        name = t.get("name")
        url = t.get("url")
        filepath = os.path.join("json", name)

        t["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

        if not url:
            t["status"] = "missing_url"
            continue

        is_gh, raw, _ = extract_raw(url)
        try:
            r = requests.get(raw if is_gh else url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                t["status"] = f"http{r.status_code}"
                continue
            content = r.content.decode("utf-8", errors="ignore").strip()
            t["status"] = "ok"
        except Exception:
            t["status"] = "error"
            continue

        md5_val = hashlib.md5(content.encode("utf-8")).hexdigest()
        
        # 解密
        if is_encrypted(content):
            content = decrypt(content)

        cleaned = clean_comments(content)
        
        # JSON 校验与解析
        obj = None
        try:
            obj = commentjson.loads(cleaned)
        except:
            try:
                obj = json.loads(cleaned)
            except:
                t["status"] = "invalid_json"
                continue

        # 格式化并替换内部 ./ 镜像相对路径
        final_str = json.dumps(obj, ensure_ascii=False, indent=2)
        final_str = replace_relative_paths(final_str, best_mirror)

        # 计算写盘前最终内容 MD5
        new_md5 = hashlib.md5(final_str.encode("utf-8")).hexdigest()

        if new_md5 != t.get("md5") or not os.path.exists(filepath):
            t["md5"] = new_md5
            t["last_modified"] = time.strftime("%Y-%m-%d %H:%M:%S")

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(final_str)

    # 统一保存更新后的 task.json
    os.makedirs(os.path.dirname(TASK_FILE), exist_ok=True)
    with open(TASK_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
