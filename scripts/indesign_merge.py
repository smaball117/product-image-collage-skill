#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run Adobe InDesign ExtendScript through Windows PowerShell COM.

Input: validated UTF-16 CSV + original template. Output: editable merged INDD.
This is NOT an image export: the designer reviews/edits/exports in InDesign.
"""
import argparse
import csv
import json
import platform
import subprocess
import tempfile
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
JSX_SOURCE = SCRIPT_ROOT / "indesign_merge.jsx"
RUNNER_PS = r"""param([Parameter(Mandatory=$true)][string]$Jsx)
$ErrorActionPreference = 'Stop'
$code = Get-Content -LiteralPath $Jsx -Raw -Encoding UTF8
$app = New-Object -ComObject InDesign.Application
$result = $app.DoScript($code, 1246973031)
Write-Output 'INDESIGN_DOSCRIPT_FINISHED'
"""


def read_csv_header(csv_path):
    source = Path(csv_path).resolve()
    with source.open(encoding="utf-16", newline="") as file:
        reader = csv.reader(file)
        header = next(reader)
    if len(header) != 8 or header[:2] != ["货号", "颜色"] or not all(
        col.startswith("@") for col in header[2:]
    ):
        raise ValueError("CSV must contain exactly two text fields and six @ image fields")
    if len(set(header)) != len(header):
        raise ValueError("CSV field names are not unique")
    return header


def validate_image_paths(csv_path):
    """Fail before launching InDesign if any merged image path is empty/missing."""
    path = Path(csv_path)
    errors = []
    records = 0
    with path.open(encoding="utf-16", newline="") as stream:
        reader = csv.DictReader(stream)
        image_fields = [field for field in (reader.fieldnames or [])
                        if field.startswith("@")]
        for row_number, row in enumerate(reader, start=2):
            records += 1
            for field in image_fields:
                value = (row.get(field) or "").strip()
                if not value:
                    errors.append(f"第 {row_number} 行 {field} 为空")
                elif not Path(value).is_file():
                    errors.append(f"第 {row_number} 行 {field} 图片不存在：{value}")
                if len(errors) >= 8:
                    break
            if len(errors) >= 8:
                break
    if not records:
        raise ValueError("数据合并 CSV 没有任何商品记录")
    if errors:
        raise ValueError("数据源图片检查失败，尚未启动 InDesign：\n" + "\n".join(errors))


def generate_jsx(template, csv_path, output, result_file):
    """Safe string injection: JSON encodes Windows paths as JS literal escapes."""
    source = JSX_SOURCE.read_text(encoding="utf-8")
    if source.count("__JOB_JSON__") != 1:
        raise RuntimeError("InDesign ExtendScript source is missing job marker")
    job = {
        "template": str(Path(template).resolve()),
        "csv": str(Path(csv_path).resolve()),
        "output": str(Path(output).resolve()),
        "result": str(Path(result_file).resolve()),
        "headers": read_csv_header(csv_path),
    }
    return source.replace("__JOB_JSON__", json.dumps(job, ensure_ascii=True))


def merge(template, csv_path, output, dry_run=False, timeout=240):
    template = Path(template).resolve()
    csv_path = Path(csv_path).resolve()
    output = Path(output).resolve()
    if not template.is_file():
        raise FileNotFoundError(f"InDesign 模板不存在：{template}")
    if not csv_path.is_file():
        raise FileNotFoundError(f"数据表不存在：{csv_path}")
    if output.exists():
        raise FileExistsError(f"禁止覆盖已合并的 INDD：{output}")
    if not output.parent.is_dir():
        raise FileNotFoundError(f"输出目录不存在：{output.parent}")
    read_csv_header(csv_path)
    validate_image_paths(csv_path)
    with tempfile.TemporaryDirectory(prefix="indesign-merge-") as temp:
        work = Path(temp)
        result_file = work / "result.txt"
        jsx = work / "run.jsx"
        jsx.write_text(generate_jsx(template, csv_path, output, result_file),
                       encoding="utf-8-sig")
        if dry_run:
            return {"dry_run": True, "script": jsx.read_text(encoding="utf-8-sig"),
                    "output": str(output)}
        if platform.system() != "Windows":
            raise RuntimeError("自动导入 InDesign 需要 Windows 10/11 和桌面版 Adobe InDesign")
        powershell = work / "launch.ps1"
        powershell.write_text(RUNNER_PS, encoding="utf-8-sig")
        try:
            result = subprocess.run([
                "powershell.exe", "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass", "-File", str(powershell),
                "-Jsx", str(jsx)
            ], capture_output=True, text=True, errors="replace",
               timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("等待 InDesign 超时；请检查是否出现启动或数据合并对话框") from exc
        if not result_file.exists():
            details = (result.stderr + "\n" + result.stdout)[-2400:]
            modal_hint = (
                "InDesign 可能已有未关闭的模态对话框。请到 InDesign 窗口手动"
                "关闭当前警告/对话框后重新执行；脚本运行前已存在的窗口不能靠"
                " JSX 内的 NEVER_INTERACT 设置关闭。"
            ) if ("modal" in details.lower() or "模态" in details or
                  "dialog" in details.lower()) else (
                "请检查桌面 InDesign 是否已启动、是否弹出启动/登录对话框。"
            )
            raise RuntimeError(
                "没有收到 InDesign 脚本执行结果。" + modal_hint +
                f" exit={result.returncode}, 原始错误：{details}"
            )
        lines = result_file.read_text(encoding="utf-8-sig").splitlines()
        if not lines or lines[0] != "OK":
            raise RuntimeError("InDesign 数据合并失败：" + "\n".join(lines[1:])[:1600])
        if result.returncode != 0 or not output.is_file():
            raise RuntimeError("InDesign 返回成功标志，但未正常保存完整文档")
        return {"dry_run": False, "output": str(output), "status": "OK"}


def main():
    p = argparse.ArgumentParser(description="自动打开 ID 模板、导入 CSV 并生成合并后的可编辑 INDD")
    p.add_argument("--template", required=True)
    p.add_argument("--csv", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--dry-run", action="store_true", help="只生成脚本，测试路径与语法")
    args = p.parse_args()
    result = merge(args.template, args.csv, args.output, dry_run=args.dry_run)
    if args.dry_run:
        print("已生成 InDesign JSX 调用预览，未打开 InDesign")
    else:
        print("InDesign 自动导入和合并成功：" + result["output"])


if __name__ == "__main__":
    main()
