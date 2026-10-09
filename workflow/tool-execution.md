# 自动工具执行协议

只给商品图片路径，不需要三个 Python 路径和 ID 模板路径。Skill 所有脚本位于 scripts/，模板位于 assets/indesign/。

## 第一阶段：自动生成 CSV 并导入 InDesign

~~~powershell
python scripts/batch_runner.py check --images "商品图片路径"
python scripts/batch_runner.py prepare --images "商品图片路径" --merge
~~~

--merge 触发：
- 扫描图片、按照 categories/品类/rule.md 匹配 8 列，生成 UTF-16 LE 图片汇总.csv。
- 校验必选图片和本地 .indd 模板（使用 SHA-256 防止拿错版本）。
- 运行 scripts/indesign_merge.py → Windows PowerShell COM → scripts/indesign_merge.jsx。
- JSX 自动打开原模板副本的合并会话，调用 selectDataSource() 和 mergeRecords()。
- InDesign 另存 拼图_待人工调整.indd，原始模板不覆盖。用户拿到的是**已填入数据的可编辑文档**。

不应让用户再手动导入 CSV；如果 InDesign 报错，打印错误和阶段状态，等排除故障后重做。

## 唯一人工阶段

在已自动合并的文档里检查版式、调整布局、人工导出 JPG/PNG。不自动替用户做主观排版或最终导出。

## 第二阶段：OCR + 遮罩

~~~powershell
python scripts/batch_runner.py resume --batch "批次路径" --exported "ID导出图片包路径"
~~~

从导出图片包复制副本，用 OCR 命名，再使用 (0,1457,983,119) 白遮罩去字。只返回最终图片目录。

## 运行要求

- 必须 Windows 本机有桌面 Adobe InDesign 和 PowerShell，COM ProgID 为 InDesign.Application。
- 不需要额外 InDesign MCP；这个 Skill 自带 ExtendScript 和 COM 调用桥。
- GitHub CI 只可做无 GUI 测试。若首次启用 InDesign 或弹出模态框，可能需要在本机先启动并完成授权。
- Pillow 用于遮罩；PaddleOCR 与 PaddlePaddle 用于后处理。版本要求见 requirements.txt。
- 不得在未执行成功 InDesign 合并时调用 OCR。
