---
name: product-image-collage
description: 根据用户指定的商品图片路径、外部 Python 工具路径和品类规则，生成 InDesign 数据合并 CSV 及日期品类批次包，人工导出后安全执行 OCR 重命名和白色遮罩。
---

# Product Image Collage Skill

## 用户命令

“调用 product-image-collage skill。图片路径：…；工具路径：…；品类：内裤/内衣套；帮我做拼图。”

从当前用户消息读取 **图片路径、工具路径、品类**；若此前已明确某项，可沿用。不要从文件名猜品类，也不要要求用户每次输入日期（默认本地当前日期）。输出路径默认在输入目录的父目录下 `product-collage-output`，可由用户另行指定。

## 权限与输入检查

- **仅本地有文件系统与命令行能力的 Agent** 可以处理 Windows 盘符；若不可访问，明确说明，不虚报执行。
- 工作前读取 `categories/{品类ID}/rule.md` 中 `~~~json` 规则块；对应内裤为 `underwear`，内衣套为 `underwear-set`。其语义不能交叉使用。
- 只调用本仓库 `scripts/batch_runner.py` 作为适配层。三个原始 Python 文件由用户提供路径，保持在本地目录，不复制进仓库。
- 执行前阅读 `workflow/tool-execution.md` 与 `workflow/batch-package.md`，先用 `check` 检查；不要运行原工具的 `main()`（含硬编码路径/原地重命名/输入暂停等风险）。

## 工作流

### 1. 前置检查

~~~powershell
python scripts/batch_runner.py check --images "图片路径" --tools "工具路径" --category "品类"
~~~

### 2. 建批次并生成 CSV

~~~powershell
python scripts/batch_runner.py prepare --images "图片路径" --tools "工具路径" --category "品类"
~~~

获取命令打印的真实批次目录。确认 `batch.json`、`report/report.md` 和 `csv/data_merge_utf16.csv` 均存在且内容合理。

如果 `stage=needs_mapping`，不能让用户直接导入 ID；需要从 `report/overrides-needed.json` 找到候选文件，向用户确认无编号背面图等字段，制作 `--overrides` 文件重新运行 prepare。**不得猜配**。缺少必选素材必须在回复中指出。

### 3. 等待人工 InDesign

明确指导用户：ID → 窗口 → 实用程序 → 数据合并 → 选择 UTF-16 LE CSV → 人工确认排版 → 导出图片。此期间应停止，不要自动执行 OCR（此时尚无 ID 导出图）。

### 4. 续跑

用户明确提供 ID 导出目录后：

~~~powershell
python scripts/batch_runner.py resume --batch "实际批次目录" --exported "ID导出图片目录"
~~~

先复制导出图，再调用外部 OCR 识别函数对**副本**重命名，最后调用外部遮罩函数输出 `cleaned/`。失败时保留源、汇报文件数量和警告，不假装完整成功。

## 不可违背的规则

1. 原始图片不可原地改名、移动、覆盖、填色或重采样。
2. UTF-16 LE CSV 要带 BOM、图片表头必须以 `@` 开头；其余字段为 `货号` 和 `颜色`。
3. 任何歧义文件映射需人工确认，不允许“选择第一张”。
4. 同名批次不覆盖，生成新编号。
5. 不同品类只依据其自身 `rule.md`。
6. 不能把 prepare 的成功误报为最终拼图完成；人工 ID 是必需节点。
7. 遮罩参数继承用户外部脚本，若换模板必须先确认遮罩参数。

## 批次内容

`YYYY-MM-DD_{category}/source,csv,indesign,exported,renamed,cleaned,report,batch.json`。

详细调用约定在 `workflow/tool-execution.md`，新增品类参照 `categories/template/rule-template.md`。
