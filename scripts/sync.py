#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, json, time, subprocess, requests, hashlib
from concurrent.futures import ThreadPoolExecutor
import commentjson

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8"
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

def decrypt(text, original_url="", best_mirror="https://v4.gh-proxy.org/"):
    tmp_in = "tmp_in.txt"
    tmp_out = "tmp_out.json"
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tvbox_script = os.path.join(script_dir, "tvbox.py")
    
    decrypted_content = ""
    local_success = False
    
    try:
        with open(tmp_in, "w", encoding="utf-8") as f:
            f.write(text)
        subprocess.run(["python", tvbox_script, tmp_in, tmp_out], check=True)
        if os.path.exists(tmp_out):
            res = open(tmp_out, "r", encoding="utf-8").read()
            if res.strip():
                try:
                    cleaned_test = clean_comments(res)
                    commentjson.loads(cleaned_test) if 'commentjson' in globals() else json.loads(cleaned_test)
                    decrypted_content = res
                    local_success = True
                    print("  ✓ 本地 tvbox.py 解密并验证 JSON 成功")
                except Exception:
                    print("  ⚠️ 本地 tvbox.py 解密完成，但输出的不是标准的 JSON 格式，尝试网页端解密...")
    except Exception as e:
        print(f"  ⚠️ 本地 tvbox.py 解密报错: {e}，尝试网页端解密...")
    finally:
        for f in [tmp_in, tmp_out]:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass

    if local_success:
        return decrypted_content

    if original_url:
        parse_target_url = original_url
        if "raw.githubusercontent.com" in parse_target_url or "github.com" in parse_target_url:
            if not parse_target_url.startswith("http"):
                parse_target_url = "https://" + parse_target_url
            if not parse_target_url.startswith(best_mirror):
                parse_target_url = best_mirror + parse_target_url

        print(f"  🔄 正在尝试网页端解析兜底 (带镜像): {parse_target_url}")
        try:
            from bs4 import BeautifulSoup
            target_url = "https://my9.ltd/tvin/"
            payload = {
                "action": "parse_url",
                "url": parse_target_url
            }
            response = requests.post(target_url, data=payload, headers=HEADERS, timeout=20)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                json_text = None
                
                raw_div = soup.find(class_="json-raw")
                if raw_div:
                    json_text = raw_div.get_text()
                else:
                    for pre in soup.find_all(['pre', 'code']):
                        t_str = pre.get_text()
                        if t_str.strip().startswith('{') and t_str.strip().endswith('}'):
                            json_text = t_str
                            break
                
                if json_text:
                    cleaned_test = clean_comments(json_text)
                    commentjson.loads(cleaned_test) if 'commentjson' in globals() else json.loads(cleaned_test)
                    print("  ✓ 网页端解析并验证 JSON 成功")
                    return json_text
        except Exception as backend_err:
            print(f"  ❌ 网页端解析失败: {backend_err}")

    return ""

# ============================================================
# 工具：判断 URL / 本地文件状态
# ============================================================
def default_url(name):
    return f"{REPO_RAW_PREFIX}{name}.json"

def is_self_hosted_url(url, name):
    if not url or not name:
        return False
    u = url.strip()
    candidates = [
        f"https://raw.githubusercontent.com/child9527/tvbox/main/json/{name}.json",
        f"https://raw.githubusercontent.com/child9527/tvbox/refs/heads/main/json/{name}.json",
        f"https://github.com/child9527/tvbox/raw/main/json/{name}.json",
        f"https://github.com/child9527/tvbox/raw/refs/heads/main/json/{name}.json",
    ]
    return u in candidates

def is_effectively_empty_json(filepath):
    if not os.path.isfile(filepath):
        return True
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read().strip()
        return text == "" or text in ("{}", "[]", "null")
    except Exception:
        return False

def load_task_json():
    try:
        with open(TASK_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            print("❌ task.json 根节点必须是数组")
            raise SystemExit(1)
        return data
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"❌ task.json 解析失败: {e}")
        print("❌ 为避免覆盖 url，本次直接退出")
        raise SystemExit(1)

def scan_local_json():
    os.makedirs(JSON_DIR, exist_ok=True)
    result = {}
    for fname in os.listdir(JSON_DIR):
        if not fname.lower().endswith(".json"):
            continue
        base = os.path.splitext(fname)[0]
        if not base:
            continue
        result[base.lower()] = base
    return result

def detect_trigger():
    event = os.getenv("GITHUB_EVENT_NAME", "")
    if event == "schedule":
        return "schedule"
    if event == "workflow_run":
        return "task"
    if event == "push":
        return "json"
    if event == "workflow_dispatch":
        return "manual"
    return "manual"

def fetch_and_write(task, best_mirror):
    name = task.get("name", "")
    filename = f"{name}.json"
    filepath = os.path.join(JSON_DIR, filename)
    url = task.get("url")
    now_time = time.strftime("%Y-%m-%d %H:%M:%S")
    task["timestamp"] = now_time

    if not url:
        task["status"] = "missing_url"
        return False

    is_gh, raw, _ = extract_raw(url)
    target_url = raw if is_gh else url
    print(f"📥 正在拉取 [{name}]，目标地址: {target_url}")

    raw_content = ""
    fetch_success = False

    # 优先策略：模拟 TVBox 客户端下载方式 (okhttp/3.12.0)
    try:
        r = requests.get(target_url, headers={"User-Agent": "okhttp/3.12.0"}, timeout=10)
        if r.status_code == 200:
            raw_content = r.content.decode("utf-8", errors="ignore").strip()
            fetch_success = True
            print("  ✓ 通过 TVBox 客户端下载方式成功获取原文")
        else:
            print(f"⚠️ TVBox 客户端下载状态码: {r.status_code}，切换为常规方式兜底...")
    except Exception as e:
        print(f"⚠️ TVBox 客户端下载异常: {e}，切换为常规方式兜底...")

    # 兜底策略 1：切换为常规浏览器下载方式 (HEADERS)
    if not fetch_success:
        try:
            r2 = requests.get(target_url, headers=HEADERS, timeout=10)
            if r2.status_code == 200:
                raw_content = r2.content.decode("utf-8", errors="ignore").strip()
                fetch_success = True
                print("  ✓ 通过常规方式兜底成功获取原文")
            else:
                print(f"⚠️ 常规方式下载状态码: {r2.status_code}，尝试使用镜像通道...")
        except Exception as e2:
            print(f"⚠️ 常规方式下载异常: {e2}，尝试使用镜像通道...")

    # 兜底策略 2：换用镜像/代理通道兜底重试
    if not fetch_success:
        proxy_url = target_url
        if not proxy_url.startswith("http"):
            proxy_url = "https://" + proxy_url
        if not proxy_url.startswith(best_mirror):
            print(f"  🔄 尝试通过镜像通道兜底重试: {best_mirror}{proxy_url}")
            try:
                r3 = requests.get(best_mirror + proxy_url, headers={"User-Agent": "okhttp/3.12.0"}, timeout=15)
                if r3.status_code == 200:
                    raw_content = r3.content.decode("utf-8", errors="ignore").strip()
                    fetch_success = True
                    print(f"  ✓ 通过镜像通道成功获取 [{name}] 原文")
            except Exception as mirror_err:
                print(f"  ❌ 镜像通道兜底也失败: {mirror_err}")

    if not fetch_success:
        task["status"] = "fetch_failed"
        return False

    task["status"] = "ok"

    if raw_content.startswith("\ufeff"):
        raw_content = raw_content[1:]

    content = raw_content
    try:
        cleaned_test = clean_comments(content)
        commentjson.loads(cleaned_test)
    except Exception:
        print(f"  🔒 检测到 [{name}] 内容非标准JSON，尝试解密...")
        content = decrypt(content, original_url=target_url, best_mirror=best_mirror)
        if not content:
            print(f"❌ [{name}] 本地与网页端双重解密均失败或结果非标准JSON，跳过该任务")
            task["status"] = "decrypt_failed"
            return False

    cleaned = clean_comments(content)

    try:
        obj = commentjson.loads(cleaned)
    except Exception:
        try:
            obj = json.loads(cleaned)
        except Exception:
            print(f"❌ [{name}] JSON 解析失败！抓取到的响应前 300 字符为:\n{cleaned[:300]}")
            task["status"] = "invalid_json"
            return False

    final_str = json.dumps(obj, ensure_ascii=False, indent=2)
    final_str = replace_dot_slash(task["url"], best_mirror, final_str)
    final_str = replace_relative_paths(final_str, best_mirror)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(final_str)

    remote_md5 = hashlib.md5(raw_content.encode("utf-8")).hexdigest()
    md5_changed = (remote_md5 != task.get("md5"))
    task["md5_changed"] = md5_changed
    if md5_changed:
        task["md5"] = remote_md5
        task["last_modified"] = now_time

    return True

# ============================================================
# 主逻辑
# ============================================================
def main():
    trigger = detect_trigger()
    print(f"🔔 触发来源: {trigger}")

    best_mirror = pick_best_mirror()
    print(f"当前最快镜像为：{best_mirror}")

    old_tasks = load_task_json()
    old_tasks_map = {}
    for t in old_tasks:
        name = os.path.splitext(str(t.get("name", "")))[0].strip()
        if not name:
            continue
        t["name"] = name
        old_tasks_map[name.lower()] = t

    local_map = scan_local_json()
    task_keys = set(old_tasks_map.keys())
    local_keys = set(local_map.keys())

    new_tasks = []
    deleted_files = []
    content_changed = False
    registry_only = False

    if trigger == "json":
        for lower, base_name in sorted(local_map.items(), key=lambda x: x[1]):
            if lower in old_tasks_map:
                task = dict(old_tasks_map[lower])
                task["name"] = base_name
                task["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                new_tasks.append(task)
            else:
                print(f"📝 本地新增 [{base_name}]，仅注册到 task.json（不下载）")
                new_tasks.append({
                    "name": base_name,
                    "url": default_url(base_name),
                    "md5": None,
                    "last_modified": None,
                    "status": "local",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                })
                registry_only = True

        for lower, task in old_tasks_map.items():
            if lower not in local_keys:
                fname = f"{task['name']}.json"
                print(f"🗑️ 本地已删除 [{task['name']}]，从 task 移除并标记双端删除")
                deleted_files.append(fname)
                content_changed = True

    elif trigger == "task":
        for lower, task in old_tasks_map.items():
            task = dict(task)
            name = task["name"]
            filepath = os.path.join(JSON_DIR, f"{name}.json")

            if lower not in local_keys:
                print(f"➕ task 新增 [{name}]，开始拉取...")
                ok = fetch_and_write(task, best_mirror)
                new_tasks.append(task)
                if ok:
                    content_changed = True
            else:
                url = task.get("url") or ""
                if is_self_hosted_url(url, name) or task.get("status") == "local":
                    if is_effectively_empty_json(filepath):
                        print(f"⏭️ [{name}] 为本地占位，跳过下载")
                        task["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        new_tasks.append(task)
                        continue
                prev = old_tasks_map.get(lower, {})
                need_fetch = (
                    not task.get("md5")
                    or (url and url != prev.get("url"))
                )
                if need_fetch:
                    print(f"🔄 [{name}] 需要更新，开始拉取...")
                    ok = fetch_and_write(task, best_mirror)
                    if ok and task.get("md5_changed"):
                        content_changed = True
                else:
                    task["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    task["md5_changed"] = False
                new_tasks.append(task)

        for lower, base_name in local_map.items():
            if lower not in task_keys:
                filepath = os.path.join(JSON_DIR, f"{base_name}.json")
                print(f"🗑️ task 已移除 [{base_name}]，删除本地文件并标记双端删除")
                try:
                    os.remove(filepath)
                except OSError:
                    pass
                deleted_files.append(f"{base_name}.json")
                content_changed = True

    else:
        for lower, task in old_tasks_map.items():
            task = dict(task)
            name = task["name"]
            url = task.get("url") or ""
            filepath = os.path.join(JSON_DIR, f"{name}.json")

            if is_self_hosted_url(url, name) or task.get("status") == "local":
                if is_effectively_empty_json(filepath):
                    print(f"⏭️ [{name}] 本地占位，定时任务跳过下载")
                    task["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    new_tasks.append(task)
                    continue

            ok = fetch_and_write(task, best_mirror)
            new_tasks.append(task)
            if ok and task.get("md5_changed"):
                content_changed = True

        for lower, base_name in local_map.items():
            if lower not in task_keys:
                print(f"📝 本地存在但 task 无记录 [{base_name}]，补注册")
                new_tasks.append({
                    "name": base_name,
                    "url": default_url(base_name),
                    "md5": None,
                    "last_modified": None,
                    "status": "local",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                })
                registry_only = True

    os.makedirs(os.path.dirname(TASK_FILE), exist_ok=True)
    with open(TASK_FILE, "w", encoding="utf-8") as f:
        json.dump(new_tasks, f, ensure_ascii=False, indent=2)

    if deleted_files:
        print(f"🗑️ 待双端删除: {', '.join(deleted_files)}")

    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        need_deploy = "true" if (content_changed or deleted_files) else "false"
        should_index = "true" if (content_changed or deleted_files) else "false"
        with open(github_output, "a", encoding="utf-8") as gh_out:
            gh_out.write(f"deleted_files={' '.join(deleted_files)}\n")
            gh_out.write(f"need_deploy={need_deploy}\n")
            gh_out.write(f"should_index={should_index}\n")
            gh_out.write(f"registry_only={'true' if registry_only and not content_changed and not deleted_files else 'false'}\n")

    print(f"✅ 完成。tasks={len(new_tasks)}, deleted={len(deleted_files)}, "
          f"content_changed={content_changed}, registry_only={registry_only}")

if __name__ == "__main__":
    main()
