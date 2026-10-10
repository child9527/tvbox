#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
各板块的数据构造函数。

每个函数返回一个 dict，结构如下：
{
    "title": 板块标题,
    "type":  板块类型（决定模板用哪个组件渲染）,
    "items": 该板块的数据列表,
    ...（其他该类型专用字段）
}

新增板块类型时，在这里加一个函数即可。
"""


def section_software_list(title, items):
    """
    软件卡片列表板块（带筛选按钮）。

    参数：
        title: 板块标题
        items: 软件列表，每项结构：
            {
                "name":        展示名,
                "version":     版本号,
                "url":         原始下载链接,
                "file_size":   文件大小（字节）,
                "file_size_text": 格式化后的大小（如 "12.3 MB"）,
                "icon":        图标 URL（可为空）,
                "type":        分类（如 "Win64"、"Android"）,
                "description": 简介,
                "mirrors":     [(镜像名, 镜像链接), ...],
            }

    返回：
        {
            "title":      标题,
            "type":       "software_list",
            "items":      items,
            "types":      去重后的分类列表（按出现顺序）,
            "first_type": 第一个分类（用于默认显示）,
        }
    """
    types = list(dict.fromkeys([it["type"] for it in items if it.get("type")]))
    return {
        "title": title,
        "type": "software_list",
        "items": items,
        "types": types,
        "first_type": types[0] if types else None,
    }


def section_copy_cards(title, items):
    """
    复制型卡片（网格）板块。

    参数：
        title: 板块标题
        items: 卡片列表，每项结构：
            {
                "name":        展示名,
                "url_literal": 已经过 json.dumps 的 JS 字符串字面量,
            }

    返回：
        {
            "title": 标题,
            "type":  "copy_cards",
            "items": items,
        }
    """
    return {
        "title": title,
        "type": "copy_cards",
        "items": items,
    }


def section_copy_cards_wide(title, items):
    """
    复制型卡片（单行大卡片）板块，支持多张。

    items 里每项结构：
        {
            "name":            展示名,
            "js_var":          JS 变量名（英文，全局唯一，如 "EXTENSION_JS_TEXT"）,
            "content_literal": 已经过 json.dumps 的 JS 字符串字面量,
        }

    示例：
        section_copy_cards_wide("📋 规则及配置", [
            {
                "name": "Clash Verge Rev全局扩展覆写脚本",
                "js_var": "EXTENSION_JS_TEXT",
                "content_literal": json.dumps(js_text, ensure_ascii=False),
            },
            {
                "name": "Clash 配置模板",
                "js_var": "CLASH_CONFIG_TEXT",
                "content_literal": json.dumps(config_text, ensure_ascii=False),
            },
        ])
    """
    return {
        "title": title,
        "type": "copy_cards_wide",
        "items": items,
    }
