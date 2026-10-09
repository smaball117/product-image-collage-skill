---
name: product-image-collage
description: 按商品品类识别本地图片，第一步只输出 InDesign 所需 UTF-16 LE CSV 表格，等待人工 InDesign 导出后再执行 OCR 重命名与遮罩去字。
---

# Product Image Collage Skill

## 用户输入

“调用商品拼图 Skill，图片路径：xxx，工具路径：xxx，品类：内裤/内衣套，帮我做拼图。”

从输入提取三个值：`图片路径`、`工具路径`、`品类`。未指定时只问缺失的必要值。品类仅从 `categories/{category}/rule.md` 判断，不跨品类混用编号。

## 当前两种品类的固定 CSV 表头

> 以下字段与 InDesign 模板绑定，不是整个商品图片库的所有命名类型。每种品类仅抓取 2 张 PNG + 4 张 JPG，合计 8 列。

### 内衣套（underwear-set）

```csv
货号,颜色,@上衣png,@下衣png,@领口,@袖口,@肩线,@裤腰
```

依次抓取：`-1.png`、`-2.png`、`-1.jpg`、`-2.jpg`、`-3.jpg`、`-4.jpg`。

### 内裤（underwear）

```csv
货号,颜色,@正面png,@背面png,@印花,@裤口,@裤边,@裤腰
```

依次抓取：`-1.png`、`-2.png`、`-5.jpg`、`-2.jpg`、`-3.jpg`、`-4.jpg`。

**必须按用户要求保持字段名大小写、字段顺序与总列数完全一致。** 同一文件夹里其他无关素材仅记日志，不得增加 CSV 列，也不应该因为这些未选素材阻止生成 CSV；同一所需字段的图片冲突仍需人工确认。

## 五步操作，按顺序执行

### Step 1｜自动制作 CSV 表格（此时只交付表格）

先运行：

~~~powershell
python scripts/batch_runner.py check --images "图片路径" --tools "工具路径" --category "品类"
python scripts/batch_runner.py prepare --images "图片路径" --tools "工具路径" --category "品类"
~~~

`prepare` 会用外部 `scan_product_images.py` 的解析函数和品类规则识别图片。每个“货号 + 颜色”为 CSV 一行，字段为 `货号`、`颜色`、以及以 `@` 开头的图片列。所有图片单元格填写文件的绝对路径。编码是 **UTF-16 LE（含 BOM）**。

**第 1 步用户在输出目录中只能看到一个主文件**：

~~~text
product-collage-output/
└── YYYY-MM-DD_品类/
    └── 图片汇总.csv
~~~

本地程序额外在隐藏的 `.skill/` 保存恢复信息和异常日志，Agent 不要主动把其内部文件列成用户要操作的结果。

如果出现无法确认的无编号图/重复图，只生成 `图片汇总_待确认.csv`，不生成可以误导用户导入 ID 的正式表格。Agent 简明说明哪张图片需要核对，等确认后重做。

**执行完成后停止，简短向用户汇报“CSV 生成成功 + 文件位置 + 记录数量 + 是否有缺图”，提示下一步人工 ID。不要自动执行第 3、4 步。**

### Step 2｜用户手动完成 InDesign

用户自己操作：InDesign → 窗口 → 实用程序 → 数据合并 → 选择 `图片汇总.csv` → 手动排版 → 导出拼图图片。

此阶段 Agent 必须等待用户提供 ID 导出图片的路径。

### Step 3｜Agent 调用 OCR 重命名

用户完成导出后调用：

~~~powershell
python scripts/batch_runner.py resume --batch "实际 YYYY-MM-DD_品类目录" --exported "ID图片导出目录"
~~~

通过外部 `ocr_rename_images.py` 的 OCR 函数识别、重命名**复制的 ID 图片**。不改变原始图片文件名。

### Step 4｜Agent 调用白遮罩去字

同一条 `resume` 命令会接着调用外部 `batch_add_white_mask.py` 的 `process_image()` 完成去字。坐标沿用原脚本的固定位置，若更换 ID 模板需先验证。

### Step 5｜输出最终图片

用户只需要打开：

~~~text
YYYY-MM-DD_品类/
├── 图片汇总.csv
└── 最终图片/
    ├── 某颜色.png
    └── …
~~~

其他工作记录都在隐藏的 `.skill/` 目录内；不要主动给用户展示冗长内部目录、batch.json、日志等，除非有错误需要排查。

## 简明答复格式

第 1 步只回复：

> 第 1 步完成：已生成 XX 行 CSV 表格。
> 表格位置：完整路径
> 检查结果：缺失 X 项／待确认 X 项。
> 下一步：请在 InDesign 里导入 CSV 并导出图片。

第 3、4 步完成后只回复：

> 已完成 OCR 重命名与去文字。
> 最终图片：完整路径
> 成功 X 张，异常 X 张。

## 必须遵守

1. 不访问不到的本机盘符，不假称已执行。
2. 不修改、不覆写原始图片；重复批次加 `-02`。
3. CSV 图片列以 @ 开头，编码 UTF-16 LE + BOM。
4. 映射歧义等待人工确认，不猜配。
5. 外部三个 Python 工具由用户提供目录，本 Skill 只导入函数，不运行其带硬编码路径的 `main()`。
6. 用户人工 ID 操作保留，Agent 不模拟点击。
7. 默认第 1 步只交付 **一张 CSV**，之后才产出 **最终图片**。
