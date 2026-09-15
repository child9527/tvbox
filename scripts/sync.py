#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, json, time, subprocess, requests, hashlib
from concurrent.futures import ThreadPoolExecutor
import commentjson

HEADERS = {"User-Agent": "Mozilla/5.0"}
RAW_PREFIX = "https://raw.githubusercontent.com/"

# ============================================================
# 镜像测速
# ============================================================
def load_mirrors():
    path = os.path.join("scripts", "mirror.txt")
    if not os.path.exists(path):
        return []
    mirrors = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = line.strip()
            if m:
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
    best = sorted(results, key=results.get)[0]
    print(f"🚀 选择最快镜像: {best}")
    return best

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
    with open(tmp_in, "w", encoding="utf-8") as f:
        f.write(text)
    subprocess.run(["python", "scripts/tvbox.py", tmp_in, tmp_out], check=True)
    return open(tmp_out, "r", encoding="utf-8").read()

# ============================================================
# 读取任务（task.json + json目录补充）
# ============================================================
def load_tasks():
    tasks = []
    if os.path.exists("task.json"):
        with open("task.json", "r", encoding="utf-8") as f:
            tasks = json.load(f)

    # 打印当前 json 目录文件列表
    print("📂 当前 json 目录文件:")
    for fn in os.listdir("json"):
        print(" -", fn)

    existing_names = {t["name"].strip().lower() for t in tasks}
    for fn in os.listdir("json"):
        if fn.endswith(".json") and fn.strip().lower() not in existing_names:
            filepath = os.path.join("json", fn)
            if os.path.exists(filepath):
                with open(filepath, "rb") as f:
                    md5_val = hashlib.md5(f.read()).hexdigest()
            else:
                md5_val = None
            tasks.append({
                "name": fn,
                "url": f"https://raw.githubusercontent.com/child9527/tvbox/main/json/{fn}",
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
    mirror = pick_best_mirror()
    tasks = load_tasks()
    print(f"📦 总任务数: {len(tasks)}")

    for t in tasks:
        name = t["name"]
        url = t.get("url")
        filepath = os.path.join("json", name)

        print(f"🔍 检查任务: {name}")
        t["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

        if not url:
            print(f"❌ 没有远程地址: {name}")
            t["status"] = "missing_url"
            continue

        is_gh, raw, _ = extract_raw(url)
        try:
            r = requests.get(raw if is_gh else url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                print(f"❌ 拉取失败: HTTP {r.status_code}")
                t["status"] = f"http{r.status_code}"
                continue
            content = r.content.decode("utf-8", errors="ignore").strip()
            print("✅ 拉取成功")
            t["status"] = "ok"
        except Exception as e:
            print(f"❌ 拉取异常: {e}")
            t["status"] = "error"
            continue

        md5_val = hashlib.md5(content.encode("utf-8")).hexdigest()
        if md5_val != t.get("md5"):
            print(f"📌 文件有变化: {name}")
            t["md5"] = md5_val
            t["last_modified"] = time.strftime("%Y-%m-%d %H:%M:%S")

            if is_encrypted(content):
                print(f"🔓 自动解密: {name}")
                content = decrypt(content)

            cleaned = clean_comments(content)
            try:
                obj = commentjson.loads(cleaned)
            except:
                try:
                    obj = json.loads(cleaned)
                except:
                    print(f"❌ 非标准 JSON: {name}")
                    t["status"] = "invalid_json"
                    continue

            final = json.dumps(obj, ensure_ascii=False, indent=2)
            open(filepath, "w", encoding="utf-8").write(final)
            print(f"✅ 已保存更新: {name}")
        else:
            print(f"🎉 文件未变化: {name}")

    with open("task.json", "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

    print("--------------------------------------------------")
    print("📊 全部任务检查完成")
    print("--------------------------------------------------")

if __name__ == "__main__":
    main()
