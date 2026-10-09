#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""商品素材扫描器：从文件名解析末尾编号，不绑定单一品类。

品类与 CSV 列次序统一由 categories/<id>/rule.md 控制。
batch_runner.py 调用 match_image_number()，不会修改原图。
"""
import argparse
import os
import re
from pathlib import Path

EXTENSIONS = {".png", ".jpg", ".jpeg"}


def match_image_number(filename):
    """返回 (末尾数字, 模式)；有歧义时只让调度器采用 hyphen 类型。

    示例：xxx-1.png -> ("1", "hyphen")
    """
    stem, ext = os.path.splitext(filename)
    if ext.lower() not in EXTENSIONS:
        return None, None
    for pattern, kind in (
        (r"-(\d+)$", "hyphen"),
        (r"_(\d+)$", "underscore"),
        (r"\s+(\d+)$", "space"),
    ):
        m = re.search(pattern, stem)
        if m:
            return m.group(1), kind
    if len(stem) >= 2 and not stem.isdigit():
        m = re.search(r"(\d+)$", stem)
        if m:
            return m.group(1), "nosep"
    return None, None


def list_images(directory):
    p = Path(directory)
    if not p.is_dir():
        raise NotADirectoryError(str(p))
    return sorted((f for f in p.iterdir()
                   if f.is_file() and f.suffix.lower() in EXTENSIONS),
                  key=lambda f: f.name.casefold())


def main():
    parser = argparse.ArgumentParser(description="检查商品图片文件名编号（不修改图片）")
    parser.add_argument("image_folder", help="要检查的图片文件夹")
    args = parser.parse_args()
    for file in list_images(args.image_folder):
        number, pattern = match_image_number(file.name)
        print(f"{file.name}\t{number or '无编号'}\t{pattern or '-'}")


if __name__ == "__main__":
    main()
