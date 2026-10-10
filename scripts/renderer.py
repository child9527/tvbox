#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from jinja2 import Environment, FileSystemLoader, select_autoescape


# 模板目录（相对于项目根目录）
TEMPLATE_DIR = "templates"


def render(template_name, **context):
    """
    渲染指定模板。

    参数：
        template_name: 模板文件路径（相对 templates/ 目录），如 "base.html.j2"
        **context:     传给模板的变量

    返回：
        渲染后的 HTML 字符串
    """
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,      # 块标签后的第一个换行符自动去掉
        lstrip_blocks=True,    # 块标签前的空白自动去掉
    )
    template = env.get_template(template_name)
    return template.render(**context)
