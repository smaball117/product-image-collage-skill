#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在用户原 InDesign 模板固定文字区域加白色遮罩。

沿用用户脚本参数 (0,1457,983,119)；不同 ID 模板应先验证坐标。
批次调度只使用 process_image(image_path, output_dir)。
"""
import argparse
from pathlib import Path

MASK_COLOR = (255, 255, 255)
MASK_WIDTH = 983
MASK_HEIGHT = 119
MASK_X = 0
MASK_Y = 1457
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def process_image(image_path, output_dir):
    from PIL import Image, ImageDraw
    src, dst = Path(image_path), Path(output_dir)
    try:
        with Image.open(src) as image:
            if image.width < MASK_X + MASK_WIDTH or image.height < MASK_Y + MASK_HEIGHT:
                print(f"跳过：{src.name}，图片过小 {image.size}")
                return False
            img = image.convert("RGBA") if image.mode not in ("RGB", "RGBA") else image.copy()
            draw = ImageDraw.Draw(img)
            draw.rectangle(
                (MASK_X, MASK_Y, MASK_X + MASK_WIDTH - 1, MASK_Y + MASK_HEIGHT - 1),
                fill=MASK_COLOR,
            )
            dst.mkdir(parents=True, exist_ok=True)
            output = dst / (src.stem + ".png")
            if output.exists():
                print(f"跳过：输出已存在，拒绝覆盖 {output}")
                return False
            img.save(output, format="PNG", optimize=False)
            print(f"已去字：{output.name}")
            return True
    except Exception as exc:
        print(f"处理失败：{src.name}，{exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="批量对白底 ID 拼图做文字区域遮罩")
    parser.add_argument("--input", required=True, help="已重命名的拼图目录")
    parser.add_argument("--output", required=True, help="成品输出目录")
    args = parser.parse_args()
    source = Path(args.input).resolve()
    target = Path(args.output).resolve()
    if not source.is_dir() or source == target:
        parser.error("输入文件夹必须存在，输出必须是另一个文件夹")
    images = sorted((p for p in source.iterdir()
                     if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS),
                    key=lambda p: p.name.casefold())
    if not images:
        parser.error("没有可处理的 JPG/PNG 图片")
    ok = sum(process_image(p, target) for p in images)
    print(f"完成：{ok}/{len(images)} 张；输出 {target}")
    return 0 if ok == len(images) else 2


if __name__ == "__main__":
    raise SystemExit(main())
