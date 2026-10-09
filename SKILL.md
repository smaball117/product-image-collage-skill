---
name: product-image-collage
description: 用户只提供商品图片路径，Skill 自动生成 CSV、调用本地 Adobe InDesign 模板完成数据导入和全部记录合并，再由设计师人工调整导出；用户提供导出图片包路径后，自动 OCR 重命名并白遮罩去字。
---

# 商品图片拼图 Skill（自动填入 InDesign）

## 两次用户输入

第一次：
~~~text
调用 product-image-collage Skill
图片路径：F:/2026秋冬/商品图片
帮我做拼图
~~~

第二次（人工调整并导出完成以后）：
~~~text
ID 已经导出，图片包路径：F:/2026秋冬/导出拼图
继续处理上一批
~~~

用户无需每次输入 Python 工具路径、模板路径。运行环境必须是可以访问用户本地文件和桌面 Adobe InDesign 的 Windows Agent（如本地 Codex）。

## 第一阶段：Agent 必须自动执行，不让用户手动导入 CSV

执行：
~~~powershell
python scripts/batch_runner.py check --images "用户图片路径"
python scripts/batch_runner.py prepare --images "用户图片路径" --merge
~~~

自动操作次序：
1. 扫描货号/颜色/图片文件夹，按 categories/对应品类/rule.md 识别文件。
2. 生成单一 UTF-16 LE（带 BOM）图片汇总.csv，图像列以 @ 开头，8 列及顺序严格对应 ID 模板。
3. 自动选择 assets/indesign/ 里的正确 .indd 原模板。
4. 使用 scripts/indesign_merge.py 通过 Windows PowerShell COM 执行 scripts/indesign_merge.jsx。
5. JSX 必须真正执行 selectDataSource(CSV) 和 mergeRecords() 全部记录，并另存为新的可编辑 拼图_待人工调整.indd，在 InDesign 里留给设计师查看。

固定 CSV：
内衣套：货号,颜色,@上衣png,@下衣png,@领口,@袖口,@肩线,@裤腰
内裤：货号,颜色,@正面png,@背面png,@印花,@裤口,@裤边,@裤腰

图片抓取：
内衣套：PNG -1/-2，JPG -1/-2/-3/-4。
内裤：PNG -1/-2，JPG -5/-2/-3/-4。

成功后只报告两个主文件：
~~~text
YYYY-MM-DD_品类/
├── 图片汇总.csv
└── 拼图_待人工调整.indd
~~~

只创建 CSV 不算完成第一阶段，不得告知用户自己选数据源或合并。缺少模板、缺少必选图、品类有歧义或 COM 错误时必须停止并说明，不能报告已导入。

## 第二阶段：唯一人工节点

设计师打开自动生成并已经完成合并的 INDD，检查和调整版式、图片位置，然后人工导出 JPG/PNG 图片包。**不再手动执行数据源选择或数据合并。**

## 第三阶段：Agent 自动 OCR + 去字

用户提供 ID 导出图片路径，Agent 使用第一次输出的 batch 路径调用：
~~~powershell
python scripts/batch_runner.py resume --batch "对应日期品类批次目录" --exported "用户导出图片包路径"
~~~

使用内置脚本：
- scripts/ocr_rename_images.py：识别图片文字并重命名 ID 导出图的副本。
- scripts/batch_add_white_mask.py：使用原模板适配的固定遮罩 (0,1457,983,119) 覆盖文字。

只交付 最终图片/ 目录和处理数量。内部状态与副本都放在隐藏的 .skill/。

## 严格安全规则

- 保留商品原图和两份模板原文件，严禁覆盖；数据合并必须生成新 INDD。
- 同日同品类重复运行生成新批次名称。
- 仅自动 InDesign 合并成功后才交给用户人工调整导出。
- 不得在用户未导出图片之前调用 OCR/遮罩。
- 本地 Windows + InDesign COM 尚未真实验证前，只能报告脚本/CI 检查结果，不得声称整条生产线已经打通。
- 真实 .indd 二进制模板必须安装在 assets/indesign/；如不存在参照 assets/indesign/README.md。
