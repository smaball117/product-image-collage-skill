#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local batch adapter. Original user-provided .py tools stay in their own directory."""
import argparse
import csv
import ctypes
import filecmp
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATEGORIES = ROOT / "categories"
REQUIRED_TOOLS = {
    "scan": "scan_product_images.py",
    "ocr": "ocr_rename_images.py",
    "mask": "batch_add_white_mask.py",
}
SUPPORTED = {".png", ".jpg", ".jpeg"}
TEMPLATES = {
    "underwear": (
        "内裤数据合并模板-最终版.indd",
        "6b57a0e097b2b31665a301ad817b1701f9a51a68a98a5335f514222613e93aab"
    ),
    "underwear-set": (
        "内衣套数据合并模板.indd",
        "be1c4ba81fbcb50bbcf1047495b8508843dfc258fb3acf00720a14e79c9bd57c"
    ),
}


def verify_indesign_template(rule):
    spec = TEMPLATES.get(rule["category"])
    if not spec:
        return None, "此品类还没有 ID 模板配置"
    path = ROOT / "assets" / "indesign" / spec[0]
    if not path.is_file():
        return None, f"ID 模板尚未安装：{path}"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != spec[1]:
        return None, f"ID 模板校验值不一致，请确认是否使用原版文件：{path}"
    return path.resolve(), None


def hide_internal_directory(path):
    """On Windows a leading dot does not hide a folder in Explorer."""
    if os.name == "nt":
        api = ctypes.windll.kernel32
        attributes = api.GetFileAttributesW(str(path))
        if attributes == 0xFFFFFFFF:
            raise OSError(f"无法读取内部目录属性：{path}")
        if not api.SetFileAttributesW(str(path), attributes | 0x2):
            raise OSError(f"无法设置内部目录为隐藏：{path}")


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if not spec or not spec.loader:
        raise RuntimeError(f"无法加载工具：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_categories():
    rules = []
    for path in sorted(CATEGORIES.glob("*/rule.md")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"~~~json\s*(\{.*?\})\s*~~~", text, re.S)
        if not match:
            raise ValueError(f"品类规则缺少 ~~~json 块：{path}")
        rule = json.loads(match.group(1))
        if rule.get("category") != path.parent.name:
            raise ValueError(f"品类 ID 不匹配：{path}")
        slots = rule.get("slots")
        if not isinstance(slots, list) or not slots:
            raise ValueError(f"未定义 slots：{path}")
        labels = [item["label"] for item in slots]
        if len(set(labels)) != len(labels):
            raise ValueError(f"图片字段重名：{path}")
        rules.append(rule)
    return rules


def resolve_category(category):
    key = category.strip().lower()
    matches = [r for r in load_categories()
               if key in {r["category"].lower(), r["name"].lower(),
                          *(alias.lower() for alias in r.get("aliases", []))}]
    if len(matches) != 1:
        raise ValueError(f"品类不可识别或不唯一：{category}")
    return matches[0]


def tool_paths(directory=None):
    # Skill 内自带三个工具；--tools 仅用于老版本/调试兼容。
    directory = Path(directory).expanduser().resolve() if directory else ROOT / "scripts"
    if not directory.is_dir():
        raise FileNotFoundError(f"工具目录不存在：{directory}")
    result = {k: directory / v for k, v in REQUIRED_TOOLS.items()}
    missing = [str(p) for p in result.values() if not p.is_file()]
    if missing:
        raise FileNotFoundError("缺少外部 Python 脚本：" + "；".join(missing))
    return result


def images_direct(path):
    return sorted((p for p in path.iterdir()
                   if p.is_file() and p.suffix.lower() in SUPPORTED),
                  key=lambda p: p.name.lower())


def discover_product_dirs(root):
    """Accept a product/SKU folder or a parent of several SKU folders."""
    if not root.is_dir():
        raise FileNotFoundError(f"图片目录不存在：{root}")
    folders = sorted((p for p in root.iterdir() if p.is_dir()),
                     key=lambda p: p.name.lower())
    if any(images_direct(p) for p in folders):
        # root is a single SKU directory, children are colors
        if any(any(images_direct(c) for c in p.iterdir() if c.is_dir()) for p in folders):
            raise ValueError("存在混合的文件夹层级，无法确认货号与颜色目录")
        return [root]
    products = [p for p in folders if p.is_dir()
                and any(images_direct(c) for c in p.iterdir() if c.is_dir())]
    if products:
        return products
    raise ValueError("未发现 货号/颜色/*.png|*.jpg 格式的商品目录")


def check_size(path, expected):
    try:
        from PIL import Image
        with Image.open(path) as img:
            return tuple(img.size) == tuple(expected), img.size
    except ImportError:
        return None, "未安装 Pillow，跳过尺寸检查"
    except Exception as exc:
        return False, f"打开失败：{exc}"


def classify_by_suffix(path, scan_module, slot_by_suffix):
    """Reuse the original scanner's filename parser but require a literal hyphen."""
    number, pattern = scan_module.match_image_number(path.name)
    if pattern != "hyphen":
        return None
    extension = ".jpg" if path.suffix.lower() in {".jpg", ".jpeg"} else ".png"
    return slot_by_suffix.get(f"-{number}{extension}")


def detect_category(images_root, scan_module):
    """从品类特有的 JPG 编号检测商品类型；有冲突时拒绝猜测。"""
    seen = {"-1.jpg": 0, "-5.jpg": 0}
    underwear_png_extra = 0
    product_dirs = discover_product_dirs(images_root)
    for product in product_dirs:
        for color in product.iterdir():
            if not color.is_dir():
                continue
            for p in images_direct(color):
                n, pattern = scan_module.match_image_number(p.name)
                if pattern != "hyphen" or not n:
                    continue
                ext = ".jpg" if p.suffix.lower() in {".jpg", ".jpeg"} else ".png"
                key = f"-{n}{ext}"
                if key in seen:
                    seen[key] += 1
                if key in {"-3.png", "-4.png", "-5.png"}:
                    underwear_png_extra += 1

    is_underwear = seen["-5.jpg"] > 0
    is_set = seen["-1.jpg"] > 0
    if is_underwear and not is_set:
        return resolve_category("underwear")
    if is_set and not is_underwear:
        return resolve_category("underwear-set")
    if is_underwear and is_set and underwear_png_extra:
        # The extra underwear PNGs are useful signals, but simultaneous signature
        # markers may indicate mixed products. Never silently guess a category.
        raise ValueError("检测到内裤与内衣套混合标志（-5.jpg、-1.jpg），请指定 --category")
    raise ValueError(
        "仅凭当前图片无法唯一判断品类。请指定 --category 内裤 或 --category 内衣套；"
        "以后可在规则中添加更明确的品类标志"
    )


def read_overrides(path):
    if not path:
        return {}
    content = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(content, dict):
        raise ValueError("overrides 必须是 JSON 对象")
    return content


def scan_rows(root, rule, scan_module, overrides):
    slots = rule["slots"]
    by_suffix = {s["suffix"].lower(): s for s in slots if s.get("suffix")}
    rows, warnings, unresolved, missing = [], [], {}, []
    for product in discover_product_dirs(root):
        for color in sorted((p for p in product.iterdir() if p.is_dir()),
                            key=lambda p: p.name.lower()):
            files = images_direct(color)
            if not files:
                continue
            row_key = f"{product.name}/{color.name}"
            row = {"货号": product.name, "颜色": color.name}
            picked = {}
            candidates = {}
            used = set()
            for path in files:
                slot = classify_by_suffix(path, scan_module, by_suffix)
                if slot:
                    candidates.setdefault(slot["label"], []).append(path)
            for slot in slots:
                label = slot["label"]
                hits = candidates.get(label, [])
                if len(hits) == 1:
                    picked[label] = hits[0]
                    used.add(hits[0])
                elif len(hits) > 1:
                    warnings.append(f"{row_key}: {label} 有 {len(hits)} 张候选图，未自动选择")
                    unresolved.setdefault(row_key, {})[label] = [x.name for x in hits]

            unnamed = [p for p in files if p not in used
                       and classify_by_suffix(p, scan_module, by_suffix) is None
                       and not re.search(r"-\d+$", p.stem)]
            remaining_null = [s for s in slots if not s.get("suffix")]
            for extension in {".png", ".jpg"}:
                null_slots = [s for s in remaining_null
                              if s.get("extension") == extension]
                pool = [p for p in unnamed if
                        (".jpg" if p.suffix.lower() == ".jpeg"
                         else p.suffix.lower()) == extension]
                # One optional slot and one unnumbered candidate are unambiguous.
                if len(null_slots) == 1 and len(pool) == 1:
                    picked[null_slots[0]["label"]] = pool[0]
                    used.add(pool[0])
                elif pool and null_slots:
                    unresolved.setdefault(row_key, {}).update(
                        {s["label"]: [p.name for p in pool] for s in null_slots})
                    warnings.append(f"{row_key}: 无编号 {extension} 图片无法唯一匹配")

            for label, filename in overrides.get(row_key, {}).items():
                slot = next((s for s in slots if s["label"] == label), None)
                if slot is None:
                    raise ValueError(f"{row_key}: 未定义字段 {label}")
                requested = color / filename
                if (not requested.is_file() or requested.parent.resolve() != color.resolve()
                    or requested.suffix.lower() not in SUPPORTED):
                    raise ValueError(f"{row_key}: 指定文件不存在或格式不支持：{filename}")
                canonical = ".jpg" if requested.suffix.lower() == ".jpeg" else requested.suffix.lower()
                expected_ext = (slot.get("suffix") or slot.get("extension")).lower()
                if not expected_ext.endswith(canonical):
                    raise ValueError(f"{row_key}: {label} 文件格式不匹配：{filename}")
                if slot.get("suffix") and not requested.name.lower().endswith(slot["suffix"].lower()):
                    raise ValueError(f"{row_key}: {label} 图片尾缀不符合规则：{filename}")
                picked[label] = requested
                used.add(requested)
                if row_key in unresolved:
                    unresolved[row_key].pop(label, None)

            if len(set(picked.values())) < len(picked):
                raise ValueError(f"{row_key}: 同一张图片被分配到多个字段")
            if row_key in unresolved and not unresolved[row_key]:
                del unresolved[row_key]
            for slot in slots:
                label = slot["label"]
                path = picked.get(label)
                row[f"@{label}"] = str(path.resolve()) if path else ""
                if not path and slot.get("required"):
                    missing.append(f"{row_key}: 缺少 {label}")
                if path:
                    ok, found = check_size(path, slot["size"])
                    if ok is False:
                        warnings.append(f"{row_key}: {label} 尺寸 {found}，应为 {slot['size']}")
                    elif ok is None:
                        warnings.append(f"{row_key}: {label} 未检查尺寸：{found}")
            extra = [p.name for p in files if p not in used]
            if extra:
                warnings.append(f"{row_key}: 未纳入字段的文件：" + "，".join(extra))
            rows.append(row)
    return rows, warnings, unresolved, missing


def dump_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def csv_write(path, rows, fields, encoding):
    with path.open("w", encoding=encoding, newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)


def render_report(batch_dir, state):
    report = [
        "# 商品图片处理报告", "",
        f"- 批次：{batch_dir.name}",
        f"- 品类：{state['category']}",
        f"- 源路径：{state['images']}",
        f"- 阶段：{state['stage']}",
        f"- 数据记录：{state['records']}", "",
        "## 缺失（必选字段）", "",
        *(f"- {m}" for m in state.get("missing", [])),
        "", "## 待人工映射", "",
        *(f"- {k}: {', '.join(v)}" for row in state.get("unresolved", {}).values()
          for k, v in row.items()),
        "", "## 警告及处理日志", "",
        *(f"- {w}" for w in state.get("warnings", [])),
    ]
    (batch_dir / ".skill" / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def prepare(args):
    images = Path(args.images).expanduser().resolve()
    tools = tool_paths(args.tools)
    overrides = read_overrides(args.overrides)
    scan_module = load_module(tools["scan"], "local_scan_image_names")
    rule = (resolve_category(args.category) if args.category not in (None, "auto")
            else detect_category(images, scan_module))
    for fn in ("match_image_number",):
        if not callable(getattr(scan_module, fn, None)):
            raise ValueError(f"扫描工具缺少函数 {fn}")
    rows, warnings, unresolved, missing = scan_rows(images, rule, scan_module, overrides)
    if not rows:
        raise ValueError("没有找到可生成 CSV 的颜色数据")

    day = args.date or date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise ValueError("日期格式应为 YYYY-MM-DD")
    output_root = (Path(args.output_root).expanduser().resolve() if args.output_root
                   else images.parent / "product-collage-output")
    output_root.mkdir(parents=True, exist_ok=True)
    stem = f"{day}_{rule['category']}"
    batch_dir = output_root / stem
    idx = 2
    while batch_dir.exists():
        batch_dir = output_root / f"{stem}-{idx:02d}"
        idx += 1
    batch_dir.mkdir(parents=True, exist_ok=False)
    meta = batch_dir / ".skill"
    meta.mkdir()
    hide_internal_directory(meta)
    fields = ["货号", "颜色"] + [f"@{slot['label']}" for slot in rule["slots"]]
    csv_name = "图片汇总_待确认.csv" if unresolved else "图片汇总.csv"
    csv_path = batch_dir / csv_name
    csv_write(csv_path, rows, fields, "utf-16")
    if unresolved:
        dump_json(meta / "overrides-needed.json", unresolved)
    template_path, template_warning = verify_indesign_template(rule)
    if template_warning:
        warnings.append(template_warning)
    state = {
        "schema_version": 1, "date": day, "category": rule["category"],
        "images": str(images), "tools": str(tools["scan"].parent),
        "template": str(template_path) if template_path else "",
        "records": len(rows), "stage": "needs_mapping" if unresolved else "waiting_indesign",
        "warnings": warnings, "unresolved": unresolved, "missing": missing,
        "resume_processed": 0,
    }
    # The complete workflow requires actually merging the CSV into a new editable
    # InDesign document. Never claim handoff before DoScript succeeds.
    if args.merge and not unresolved:
        if missing:
            state["stage"] = "needs_images"
            state["warnings"].append("缺少必选图片，已停止自动 InDesign 合并")
        elif not template_path:
            state["stage"] = "needs_template"
            state["warnings"].append("缺少或未通过校验的 ID 模板，无法自动导入")
        else:
            try:
                from indesign_merge import merge as merge_indesign
                merged = batch_dir / "拼图_待人工调整.indd"
                merge_indesign(template_path, csv_path, merged)
                state["merged_document"] = str(merged)
                state["stage"] = "waiting_manual_export"
            except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
                state["stage"] = "indesign_merge_failed"
                state["warnings"].append(f"InDesign 自动合并失败：{exc}")
    dump_json(meta / "batch.json", state)
    render_report(batch_dir, state)
    print(f"识别品类：{rule['name']}")
    print(f"第1步：生成图片汇总表：{csv_path}")
    if args.merge:
        if state["stage"] == "waiting_manual_export":
            print(f"InDesign 自动导入并合并完成：{state['merged_document']}")
            print("现在请在 InDesign 中人工检查、调整并导出图片。")
        else:
            print(f"尚未完成 InDesign 自动合并，当前阶段：{state['stage']}")
    elif template_path:
        print(f"模板已定位（本次仅生成表格）：{template_path}")
    elif template_warning:
        print(f"注意：{template_warning}")
    print(f"共 {len(rows)} 行，UTF-16 LE（带 BOM），图片字段以 @ 开头。")
    print(f"缺少必选图片：{len(missing)}；需人工确定映射：{sum(map(len, unresolved.values()))}")
    if unresolved:
        print(f"请先核对图片并填写映射：{meta / 'overrides-needed.json'}")
        print("当前表格仅供核对，暂勿导入 InDesign。")
    elif not args.merge:
        print("仅 CSV 阶段完成。要自动导入 ID，请添加 --merge。")
    return 0 if state["stage"] not in {
        "needs_images", "needs_template", "indesign_merge_failed"
    } else 1


def check(args):
    tools = tool_paths(args.tools)
    for key, path in tools.items():
        module = load_module(path, "check_" + key)
        required = {
            "scan": ["match_image_number"],
            "ocr": ["init_ocr", "extract_text_from_image", "clean_to_filename"],
            "mask": ["process_image"],
        }[key]
        for fn in required:
            if not callable(getattr(module, fn, None)):
                raise ValueError(f"{path.name} 缺少函数 {fn}")
    if args.category in (None, "auto"):
        if not args.images:
            raise ValueError("自动识别品类必须提供 --images")
        rule = detect_category(Path(args.images).expanduser().resolve(),
                               load_module(tools["scan"], "auto_category_scanner"))
    else:
        rule = resolve_category(args.category)
    print("品类规则有效：" + rule["category"])
    template_path, warning = verify_indesign_template(rule)
    if template_path:
        print("InDesign 模板文件校验通过：" + str(template_path))
    elif warning:
        print("模板提示：" + warning)
    print("Python 脚本接口检查通过（尚未验证 PaddleOCR 运行环境）")
    if args.images:
        dirs = discover_product_dirs(Path(args.images).expanduser().resolve())
        print(f"发现货号目录：{len(dirs)} 个")
    return 0


def resume(args):
    batch_dir = Path(args.batch).expanduser().resolve()
    manifest = batch_dir / ".skill" / "batch.json"
    if not manifest.is_file():
        raise FileNotFoundError(f"找不到批次文件：{manifest}")
    state = json.loads(manifest.read_text(encoding="utf-8-sig"))
    if state["stage"] not in ("waiting_manual_export", "completed_with_warnings"):
        raise ValueError(
            f"当前阶段为 {state['stage']}，还未生成可人工调整的 ID 合并文档；"
            "必须先完成 InDesign 自动合并和人工导出"
        )
    if state["stage"] == "completed":
        raise ValueError("批次已经完成，禁止覆盖；如要重新处理请新建批次")
    tools = tool_paths(args.tools or state["tools"])
    source = Path(args.exported).expanduser().resolve() if args.exported else batch_dir / ".skill" / "exported"
    if not source.is_dir():
        raise FileNotFoundError(f"ID 导出图片目录不存在：{source}")
    exported = batch_dir / ".skill" / "exported"
    exported.mkdir(parents=True, exist_ok=True)
    (batch_dir / ".skill" / "renamed").mkdir(parents=True, exist_ok=True)
    (batch_dir / "最终图片").mkdir(parents=True, exist_ok=True)
    # Initialize the external OCR engine before touching the batch exports.
    ocr = load_module(tools["ocr"], "local_ocr_functions")
    mask = load_module(tools["mask"], "local_mask_functions")
    engine = ocr.init_ocr()
    if source != exported:
        for path in images_direct(source):
            dest = exported / path.name
            if dest.exists():
                if not filecmp.cmp(path, dest, shallow=False):
                    raise FileExistsError(f"ID 导出图与批次已有文件同名但内容不同：{dest}")
                continue  # safe to resume an interrupted job
            shutil.copy2(path, dest)
    pics = images_direct(exported)
    if not pics:
        raise ValueError("未找到 ID 导出图片，等待人工导出")
    warnings = state.setdefault("warnings", [])
    successes = 0
    for path in pics:
        text = ocr.extract_text_from_image(engine, str(path))
        stem = ocr.clean_to_filename(text) if text else None
        if stem:
            stem = stem[:100].rstrip(" .")
        forbidden = {"CON", "PRN", "AUX", "NUL"}
        forbidden.update({f"{prefix}{i}" for prefix in ("COM", "LPT") for i in range(1, 10)})
        if (not stem or stem.upper().split(".")[0] in forbidden
            or any(ord(ch) < 32 or ch in '<>:"/\\|?*' for ch in stem)):
            warnings.append(f"OCR 未能生成合法名称：{path.name}")
            continue
        renamed = batch_dir / ".skill" / "renamed" / (stem + path.suffix.lower())
        cleaned = batch_dir / "最终图片" / (stem + ".png")
        if cleaned.exists() and renamed.exists():
            # Previous attempt finished this image; keep both results.
            successes += 1
            continue
        if renamed.exists() or cleaned.exists():
            warnings.append(f"OCR 部分结果已存在，需人工检查：{path.name} => {stem}")
            continue
        shutil.copy2(path, renamed)
        if mask.process_image(renamed, batch_dir / "最终图片"):
            successes += 1
        else:
            warnings.append(f"遮罩失败，已保留重命名副本：{renamed.name}")
    state["resume_processed"] = successes
    state["stage"] = "completed" if successes == len(pics) else "completed_with_warnings"
    dump_json(manifest, state)
    render_report(batch_dir, state)
    print(f"第4步：完成 {successes}/{len(pics)} 张；最终图片：{batch_dir / '最终图片'}")
    if warnings:
        print(f"问题详情：{batch_dir / '.skill' / 'report.md'}")
    return 0 if successes == len(pics) else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description="商品批次拼图辅助处理工具")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("check", help="预检查，不更改文件")
    p.add_argument("--tools", help="可选；默认使用 Skill/scripts 内置工具")
    p.add_argument("--category", default="auto", help="可选；默认根据图片尾缀识别品类")
    p.add_argument("--images", required=True)
    p.set_defaults(func=check)
    p = sub.add_parser("prepare", help="第1步：生成单个 ID 数据合并 CSV 表格")
    p.add_argument("--images", required=True)
    p.add_argument("--tools", help="可选；默认使用 Skill/scripts 内置工具")
    p.add_argument("--category", default="auto", help="可选；默认根据图片尾缀识别品类")
    p.add_argument("--output-root")
    p.add_argument("--date", help="YYYY-MM-DD，默认本机当前日期")
    p.add_argument("--overrides", help="手工映射 JSON 文件")
    p.add_argument("--merge", action="store_true",
                   help="生成 CSV 后自动调用桌面 InDesign 模板进行全部记录合并")
    p.set_defaults(func=prepare)
    p = sub.add_parser("resume", help="第3、4步：人工 ID 导出后的 OCR + 去文字")
    p.add_argument("--batch", required=True)
    p.add_argument("--exported", help="ID 导出文件夹；可直接放在 batch/exported")
    p.add_argument("--tools", help="工具路径变更时指定")
    p.set_defaults(func=resume)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError, FileExistsError, ImportError, RuntimeError, OSError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
