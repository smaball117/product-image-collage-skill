# 外部三个 Python 工具：按实际五步执行

## 输入信息

- 图片路径：货号目录或包含多个货号的父目录
- 工具路径：`scan_product_images.py`、`ocr_rename_images.py`、`batch_add_white_mask.py` 三个脚本所在目录
- 品类：内裤 / 内衣套（或新增品类）

本 Skill 在本地执行，不能直接通过 GitHub 访问用户 Windows F 盘。

## Step 1：先扫描商品，生成 CSV

~~~powershell
python scripts/batch_runner.py check --images "图片路径" --tools "工具路径" --category "内裤"
python scripts/batch_runner.py prepare --images "图片路径" --tools "工具路径" --category "内裤"
~~~

用户在日期品类批次中只需找 `图片汇总.csv`。

- 每行表示一个货号下的一个颜色
- 货号、颜色为文字列；图片列必须带 `@` 
- 单元格为图片的绝对路径
- 文件直接以 UTF-16 LE（BOM）编码生成
- 无需记事本再手动转码
- 图片解析由 `scan_product_images.py` 的文件名解析函数完成，图片类型映射由品类 `rule.md` 完成

若某类多张图或无编号无法区分，输出 `图片汇总_待确认.csv`。此时不建议导入 ID，需要先确认映射。

在背面图确认后，制作 JSON 覆盖表：

~~~json
{
  "T20276D01/01_浅水蓝": {
    "上衣背面": "0N2A6666.png",
    "裤子背面": "0N2A6668.png"
  }
}
~~~

再运行：

~~~powershell
python scripts/batch_runner.py prepare --images "图片路径" --tools "工具路径" --category "内衣套" --overrides "人工映射.json"
~~~

## Step 2：Agent 自动填入 InDesign，用户调图导出

Agent 按 `../SKILL.md` 打开用户指定模板的副本，选择 CSV、核对真实字段绑定、合并全部记录，保存 `待人工调图.indd` 并检查文字与图片。随后用户手工调整图片大小和位置、导出图片；收到用户导出目录后才调用 OCR、遮罩。`prepare` 不含 InDesign 自动化，生成 CSV 后必须继续执行这些 ID 操作。

## Step 3：OCR 重命名

用户提供 ID 导出图片目录后，Agent 调用：

~~~powershell
python scripts/batch_runner.py resume --batch "实际日期品类批次目录" --exported "ID导出图片目录"
~~~

程序复用 `ocr_rename_images.py` 中的 `init_ocr()`、`extract_text_from_image()`、`clean_to_filename()`，仅对 ID 导出图的副本进行操作。

## Step 4：白遮罩去字

同一个 `resume` 在 OCR 后继续调用 `batch_add_white_mask.py` 的 `process_image()` 函数，输出 `最终图片/`。目前脚本的白遮罩坐标为 X=0，Y=1457，尺寸 983×119 px。不同 ID 模板需要提前核对。

## Step 5：最终交付

普通结果只显示 `日期品类/最终图片/` 文件夹和处理张数。

中间状态、日志、原始 ID 导出图副本、OCR 重命名副本均存于 `.skill/` 内部目录。Windows 下将设置该目录的隐藏属性。需要排错时再查看，不在日常报告中逐一罗列。

## 为什么不直接运行三个脚本的 main

- 原扫描脚本 `main()` 只支持内衣套的固定字段，缺少内裤完整映射。
- 原 OCR `main()` 使用硬编码路径并直接改名原文件。
- 原遮罩脚本 `main()` 使用硬编码路径。

因此本 Skill 用 `scripts/batch_runner.py` 分阶段调用各脚本**已有函数**，不修改原有三个工具文件。

本地首次使用必须验证已安装 Pillow、PaddleOCR、PaddlePaddle 等依赖，实际 InDesign 合并和固定遮罩位置需用真实图片确认。
