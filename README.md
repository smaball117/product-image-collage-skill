# Product Image Collage Skill

按用户原来的五步操作执行，不改变流程，也不提前输出后续步骤的文件。

**输入：** 图片路径 + 本地 Python 工具和 InDesign 模板目录（或指定模板文件）+ 品类（内裤 / 内衣套 / 后续品类）。

**输出：** Agent 生成 CSV 后，自动调用用户指定模板、导入并合并数据，保存可编辑的 `待人工调图.indd`；用户手工调整图片并导出后，Agent 再进行 OCR 重命名和白遮罩去字。

## 当前拼图需要抓取的图片

**内衣套：**

```csv
货号,颜色,@上衣png,@下衣png,@领口,@袖口,@肩线,@裤腰
```

对应：`PNG -1、-2`；`JPG -1、-2、-3、-4`。

**内裤：**

```csv
货号,颜色,@正面png,@背面png,@印花,@裤口,@裤边,@裤腰
```

对应：`PNG -1、-2`；`JPG -5、-2、-3、-4`。

每种品类的 CSV **只能有 8 列**，2 列文字和 6 列图片，顺序固定。额外产品图可以留在素材目录，但不会增加 CSV 字段。

## 第一步：制作表格

~~~powershell
python scripts/batch_runner.py check --images "F:\商品图片路径" --tools "F:\Python工具路径" --category "内裤"
python scripts/batch_runner.py prepare --images "F:\商品图片路径" --tools "F:\Python工具路径" --category "内裤"
~~~

在输出日期品类目录里：

~~~text
2026-10-08_内裤/
└── 图片汇总.csv
~~~

CSV 图片字段用 `@` 表头，内容为文件绝对路径，采用 UTF-16 LE（含 BOM），可直接尝试在 InDesign 数据合并导入。实际程序按英文 category ID 命名批次，例如 `2026-10-08_underwear`。

如果有重复/无编号无法确定的图片，则先输出 `图片汇总_待确认.csv`，让设计师确认图片归属，不直接进入 ID 操作。

为支持异常排查和断点续跑，程序保留一个隐藏目录 `.skill/`。它不属于需要你交付和管理的文件，请在日常操作中忽略它。

## 第二步：Agent 导入 InDesign，用户调图和导出

Agent 在用户指定模板的副本中选择 `图片汇总.csv`，检查字段绑定并合并全部记录，保存 `待人工调图.indd`。不能只选择数据源或显示预览就声称完成。具体流程以 `SKILL.md` 为准；`prepare` 本身只生成表格，Agent 必须继续完成 ID 操作。

用户打开已填入数据的 ID 文档，手工调整图片大小、位置并导出。

**此时 Agent 等待你操作，不会自己 OCR。**

## 第三步、第四步：OCR 重命名 + 白遮罩

用户完成 ID 导出后：

~~~powershell
python scripts/batch_runner.py resume --batch "日期品类批次目录" --exported "ID导出图片路径"
~~~

自动复制 ID 导出图，通过用户本地 `ocr_rename_images.py` 识别和重命名，再通过 `batch_add_white_mask.py` 去字，最终得到：

~~~text
2026-10-08_underwear/
├── 图片汇总.csv
└── 最终图片/
    └── 按识别文字命名的图片.png
~~~

如需追踪错误，可以展开隐藏的 `.skill/` 内部目录查看日志、OCR 中间结果；日常不用打开。

## 必须了解

- 三个 Python 原脚本仍放在你自己的工具文件夹，本仓库只调用它们的函数。
- GitHub 无法读你电脑 F 盘，需要在本地 Codex / 其他有文件系统权限的 Agent 运行。
- 模板涉及布局和遮罩坐标的调整必须人工验证。
- 两个测试品类：`categories/underwear/rule.md`、`categories/underwear-set/rule.md`。
- 原始图片不会被改名或覆写。
