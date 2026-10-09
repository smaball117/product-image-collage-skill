---
name: product-image-collage
description: 从商品图片生成 InDesign 数据合并 CSV；在用户完成 InDesign 调图和导出后，调用本地工具去字并重命名最终图片。
---

# Product Image Collage Skill

## 输入

从用户消息取得以下内容：

- 图片路径
- 外部 Python 工具路径
- 品类：`内裤` 或 `内衣套`

未提供的必要信息才询问。品类规则只从 `categories/{category}/rule.md` 读取，不能跨品类解释文件名编号。

## 两段式工作流

### 第一段：生成数据合并表格

依次运行：

~~~powershell
python scripts/batch_runner.py check --images "图片路径" --tools "工具路径" --category "品类"
python scripts/batch_runner.py prepare --images "图片路径" --tools "工具路径" --category "品类"
~~~

`prepare` 使用外部 `scan_product_images.py` 的解析函数和品类规则生成 UTF-16 LE（含 BOM）的 `图片汇总.csv`。每个“货号 + 颜色”是一行；图片表头以 `@` 开头，单元格填写图片绝对路径。

若出现重复候选图或无法判断的图片，生成 `图片汇总_待确认.csv`，说明待确认字段并等待用户确认。不得猜配，也不得让用户把待确认表导入 InDesign。

生成正式 `图片汇总.csv` 后，**立即停止**。交付 CSV 路径、记录数和缺图数量，并提示用户自行完成以下操作：

1. 在 InDesign 的“窗口 → 实用程序 → 数据合并”中选择 `图片汇总.csv`。
2. 人工调整图片大小、位置和版式。
3. 人工导出拼图图片。

在这一段，Agent 不得打开、创建或修改 InDesign 模板，不得自动导入 CSV，不得调整图片，也不得导出拼图。

### 第二段：处理 InDesign 导出图片

仅当用户明确提供 InDesign 导出图片目录后，运行：

~~~powershell
python scripts/batch_runner.py resume --batch "实际批次目录" --exported "ID导出图片目录"
~~~

`resume` 必须：

1. 复制用户提供的 ID 导出图到批次内部目录。
2. 调用外部 `ocr_rename_images.py` 的函数，识别文字并在副本上生成重命名图片。
3. 调用外部 `batch_add_white_mask.py` 的函数，在重命名副本上去除文字并输出到 `最终图片/`。

三个外部脚本各自的 `main()` 都不能运行：`scan_product_images.py` 仅在第一段供表格识别使用；OCR 和去字脚本仅在第二段通过适配层调用。

## 表格字段

字段和顺序必须以当前品类的 `rule.md` 为准。当前规则如下：

| 品类 | CSV 表头 |
| --- | --- |
| 内衣套 | `货号,颜色,@上衣png,@下衣png,@领口,@袖口,@肩线,@裤腰` |
| 内裤 | `货号,颜色,@正面png,@背面png,@印花,@裤口,@裤边,@裤腰` |

同一字段有多张候选图时等待人工确认。未被当前模板字段使用的素材只记录在日志中，不新增 CSV 列。

## 安全与交付

- 不移动、改名、覆盖、裁切或缩放原始商品图。
- 同名批次追加编号，不能覆盖旧批次。
- 只在用户给出导出图片目录后进入第二段。
- 第一段完成时简短回复 CSV 路径、行数、缺失和待确认数量。
- 第二段完成时简短回复最终图片路径、成功数量和异常数量。
