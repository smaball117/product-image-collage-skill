# Product Image Collage Skill

这是一个**本地运行、品类规则驱动、按日期打包**的商品图片生产 Skill。三个现有 Python 工具继续保留在用户电脑原始目录，仓库只包含规则、调度说明和一个轻量适配器。

## 一句话调用

~~~text
调用 product-image-collage skill
图片路径：F:\2027春夏\商品图片
工具路径：F:\AI_Tools\product_scripts
品类：内裤
帮我做拼图
~~~

Agent 必须有本机文件读写及命令行权限（例如本地 Codex）。GitHub 网站或远程聊天中的 Agent 无法自动读取用户 F 盘。

## 命令（Windows PowerShell）

在本仓库根目录执行：

~~~powershell
python scripts/batch_runner.py check --images "F:\2027春夏\商品图片" --tools "F:\AI_Tools\product_scripts" --category "内裤"
python scripts/batch_runner.py prepare --images "F:\2027春夏\商品图片" --tools "F:\AI_Tools\product_scripts" --category "内裤"
~~~

默认在图片路径的上一级创建 `product-collage-output/YYYY-MM-DD_underwear/`，生成 CSV、报告、批次状态。已有同名批次会新建 `-02` 等后缀，不覆盖旧结果。

打开 ID 手动数据合并：选 `csv/data_merge_utf16.csv`，确认页面位置后导出图片。然后运行：

~~~powershell
python scripts/batch_runner.py resume --batch "F:\2027春夏\product-collage-output\2026-10-08_underwear" --exported "F:\ID导出图片"
~~~

文件保存到该批次下的 `exported/`、`renamed/`、`cleaned/`。

## 技术约束

- 扫描器原脚本仅支持内衣套固定字段；适配器复用其文件名解析函数，然后从对应品类 `rule.md` 读取映射，不直接运行原脚本的 `main()`。
- OCR 原脚本直接原地修改文件；适配器调用其识别函数并将重命名结果写入**副本目录**。
- 遮罩使用原脚本的 `process_image()`，固定坐标仅适用于相同 ID 版式；不同模板须确认坐标。
- 需要 Python、Pillow；OCR 需本机原工具使用的 PaddleOCR/PaddlePaddle 环境。
- 内衣套“无编号背面 PNG”不包含上/下衣信息，需要手工确认映射，绝不按文件名猜测。
- **InDesign 操作是人工步骤**。此 Skill 不等于自动生成 ID 版式或自动点击 ID。

更详细的说明见 `workflow/tool-execution.md`。
