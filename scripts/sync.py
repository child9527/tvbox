#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, json, time, subprocess, requests
from concurrent.futures import ThreadPoolExecutor
import commentjson

HEADERS = {"User-Agent": "Mozilla/5.0"}
RAW_PREFIX = "https://raw.githubusercontent.com/"

# ============================================================
# 读取镜像列表（自动补 /）
# ============================================================
def load_mirrors():
    mirrors = []
    path = os.path.join("scripts", "mirror.txt")
    if not os.path.exists(path):
        return mirrors

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = line.strip()
            if not m:
                continue
            if not m.endswith("/"):
                m += "/"
            mirrors.append(m)
    return mirrors


# ============================================================
# 镜像测速
# ============================================================
def test_mirror(mirror):
    test_url = mirror + RAW_PREFIX + "alantang1977/X/main/X.json"
    try:
        start = time.time()
        r = requests.get(test_url, headers=HEADERS, timeout=4)
        text = r.content.decode("utf-8", errors="ignore").lstrip()
        if r.status_code == 200 and (text.startswith("{") or text.startswith("[") or text.startswith("//")):
            delay = time.time() - start
            return mirror, delay
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
    print(f"🚀 最优镜像: {best}")
    return best


# ============================================================
# GitHub RAW 提取
# ============================================================
def extract_raw(url):
    if not isinstance(url, str):
        return False, url, ""

    extra = ""
    clean = url
    if ";" in url:
        clean, extra = url.split(";", 1)
        extra = ";" + extra

    pat = r'(https?://)?(raw\.githubusercontent\.com|github\.com)/[^\s"\'<>]+'
    m = re.search(pat, clean)
    if not m:
        return False, url, extra

    raw = m.group(0)
    if not raw.startswith("http"):
        raw = "https://" + raw

    raw = re.sub(
        r'https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.*)',
        r'https://raw.githubusercontent.com/\1/\2/\3/\4',
        raw
    )
    raw = raw.replace("/refs/heads/", "/")
    return True, raw, extra


# ============================================================
# base_url 修复
# ============================================================
def get_base_url(url):
    if not isinstance(url, str) or not url.strip():
        return ""
    is_gh, raw, _ = extract_raw(url)
    target = raw if is_gh else url
    if not isinstance(target, str) or not target.strip():
        return ""
    if "/" in target:
        return target.rsplit("/", 1)[0] + "/"
    return target


# ============================================================
# URL 替换
# ============================================================
def process_url(url, base_url, mirror):
    if not isinstance(url, str):
        return url

    # ./ 相对路径
    if "./" in url:
        extra = ""
        clean = url
        if ";" in url:
            clean, extra = url.split(";", 1)
            extra = ";" + extra

        if clean.startswith("./"):
            clean = base_url + clean[2:]
        else:
            clean = re.sub(r'\./', base_url, clean)

        url = clean + extra

    # GitHub RAW
    is_gh, raw, extra = extract_raw(url)
    if is_gh:
        return f"{mirror}{raw}{extra}"

    return url


def traverse(data, base_url, mirror):
    if isinstance(data, dict):
        return {k: traverse(v, base_url, mirror) for k, v in data.items()}
    elif isinstance(data, list):
        return [traverse(v, base_url, mirror) for v in data]
    elif isinstance(data, str):
        return process_url(data, base_url, mirror)
    return data


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
# 加密检测
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
# 主逻辑
# ============================================================
def main():
    mirror = pick_best_mirror()

    # 读取任务
    tasks = []
    if os.path.exists("task/json.txt"):
        for line in open("task/json.txt", "r", encoding="utf-8"):
            m = re.search(r"https?://[^\s]+", line)
            if m:
                url = m.group(0)
                name = url.split("?")[0].rstrip("/").split("/")[-1]
                if not name.endswith(".json"):
                    name += ".json"
                tasks.append({"name": "json/" + name, "url": url})

    # 本地文件也处理
    for fn in os.listdir("json"):
        if fn.endswith(".json"):
            name = "json/" + fn
            if not any(t["name"] == name for t in tasks):
                tasks.append({"name": name, "url": None})

    print(f"📦 总任务: {len(tasks)}")

    success = []

    for t in tasks:
        name = t["name"]
        url = t["url"]

        # 本地文件
        if url is None:
            print(f"📄 本地文件: {name}")
            if not os.path.exists(name):
                print(f"❌ 本地不存在: {name}")
                continue
            content = open(name, "r", encoding="utf-8", errors="ignore").read()
            base = ""
        else:
            print(f"📥 拉取: {url}")
            is_gh, raw, _ = extract_raw(url)
            content = None

            if is_gh:
                for m in load_mirrors():
                    try:
                        r = requests.get(m + raw, headers=HEADERS, timeout=8)
                        if r.status_code == 200:
                            txt = r.content.decode("utf-8", errors="ignore").strip()
                            if txt:
                                content = txt
                                print(f"--> 成功: {m}")
                                break
                    except:
                        pass
            else:
                try:
                    r = requests.get(url, headers=HEADERS, timeout=10)
                    if r.status_code == 200:
                        content = r.content.decode("utf-8", errors="ignore").strip()
                        print("--> 成功")
                except:
                    pass

            if not content:
                print(f"❌ 拉取失败: {name}")
                continue

            base = get_base_url(url)

        # 解密
        if is_encrypted(content):
            print(f"🔓 自动解密: {name}")
            content = decrypt(content)

        # 注释清理
        cleaned = clean_comments(content)

        # JSON 校验
        try:
            obj = commentjson.loads(cleaned)
        except:
            try:
                obj = json.loads(cleaned)
            except:
                print(f"❌ 非标准 JSON: {name}")
                continue

        # URL 替换
        obj2 = traverse(obj, base, mirror)

        # 保存
        final = json.dumps(obj2, ensure_ascii=False, indent=2)
        open(name, "w", encoding="utf-8").write(final)
        print(f"✅ 保存: {name}")
        success.append(name)

    print("--------------------------------------------------")
    print(f"📊 完成: {len(success)} 个文件")
    print("--------------------------------------------------")


if __name__ == "__main__":
    main()
