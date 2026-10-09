#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OCR 文本识别与安全命名，适用于 InDesign 导出图片。

原用户脚本逻辑保留：PaddleOCR 中文模式 + 将识别文字合并作文件名。
不再使用硬编码路径，不对原始素材原地重命名。
batch_runner.py 使用 init_ocr/extract_text_from_image/clean_to_filename。
"""
import argparse
import re
import shutil
from pathlib import Path

OCR_LANG = "ch"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def init_ocr():
    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise RuntimeError(
            "未安装 PaddleOCR；请在兼容的 Python 环境安装 paddlepaddle 和 paddleocr"
        ) from exc
    # 此配置对 PaddleOCR 2.x 适用。若使用 3.x，先在本机验证 API。
    return PaddleOCR(use_angle_cls=True, lang=OCR_LANG, show_log=False, use_gpu=False)


def extract_text_from_image(ocr, image_path):
    try:
        result = ocr.ocr(str(image_path), cls=True)
        texts = []
        for line in result or []:
            if line:
                for item in line:
                    text = str(item[1][0]).strip()
                    if text:
                        texts.append(text)
        return "".join(texts)
    except Exception as exc:
        print(f"[OCR错误] {Path(image_path).name}: {exc}")
        return ""


def clean_to_filename(text):
    if not text:
        return None
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", str(text))
    name = name.strip(" .\t\n\r")[:100].rstrip(" .")
    forbidden = {"CON", "PRN", "AUX", "NUL"}
    forbidden.update(f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(1, 10))
    if not name or name.upper().split(".")[0] in forbidden:
        return None
    return name


def main():
    parser = argparse.ArgumentParser(description="OCR 重命名图片副本")
    parser.add_argument("--input", required=True, help="InDesign 导出图片文件夹")
    parser.add_argument("--output", required=True, help="重命名副本输出文件夹")
    args = parser.parse_args()
    source = Path(args.input).resolve()
    target = Path(args.output).resolve()
    if not source.is_dir() or source == target:
        parser.error("输入目录必须存在，输出目录不能与输入目录相同")
    paths = sorted((p for p in source.iterdir()
                    if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS),
                   key=lambda p: p.name.casefold())
    if not paths:
        parser.error("没有待识别图片")
    target.mkdir(parents=True, exist_ok=True)
    engine = init_ocr()
    ok = failed = 0
    for img in paths:
        new_name = clean_to_filename(extract_text_from_image(engine, str(img)))
        if not new_name or (target / (new_name + img.suffix.lower())).exists():
            failed += 1
            print(f"跳过：{img.name}（未识别或重名）")
            continue
        shutil.copy2(img, target / (new_name + img.suffix.lower()))
        ok += 1
    print(f"已重命名 {ok} 张，失败/跳过 {failed} 张：{target}")
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
