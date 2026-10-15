#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os rem, re, json, time, subprocess, requests, hashlib
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
