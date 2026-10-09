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


## InDesign 自动合并被模态对话框阻塞（故障修复）

报错包含「modal dialog or alert is active」「模态对话框或警告启用」时：

1. 新版 `scripts/indesign_merge.jsx` 会在打开模板前暂时设置 `app.scriptPreferences.userInteractionLevel = UserInteractionLevels.NEVER_INTERACT`；在数据源选择与正式合并前重新设定，并且在 `finally` 中恢复原来的交互设置。
2. 在 InDesign 模板中检查残留的丢失链接；如有 `LinkStatus.LINK_MISSING`，在合并前明确报出部分素材名称，而不是继续生成缺图拼版。
3. `scripts/indesign_merge.py` 会在启动 InDesign 前校验 CSV 所有必填图像路径实际存在且不为空，避免把空字段交给数据合并。
4. 如果弹窗在 JSX 开始执行 **之前就已经出现**，脚本无法关闭现存窗口。请先切到 InDesign 处理该弹窗（例如缺字体、启动提示、损坏链接或数据源导入选项），再在新批次中重新执行。
5. 若仍然报错，请保存 `.skill/report.md` 中的阶段标记 `step=...`、原始错误码和行号。根据 `open_template` / `select_csv_data_source` / `merge_all_records` 定位到具体故障环节，不要猜测原因或反复盲试。

**禁止**强制终止正在使用的 InDesign、不允许自动点击关闭未知的确认框；脚本完成后设计师的 InDesign 应恢复原来的交互级别。


## 其他 AI 版本 JSX 对比与合并原则（2026-10-09）

用户提供的另一份 `indesign_merge.jsx` 也通过 `UserInteractionLevels.NEVER_INTERACT` 抑制运行时弹窗、通过 `finally` 恢复交互。但该版本直接设置 `INTERACT_WITH_ALL`，**没有恢复原来可能不同的交互设置**，而且没有模板残留链接检查和阶段化的报错信息。

因此本仓库**保留现有增强版本**，不直接覆盖。后续任何变更必须维持：
- `savedInteractionLevel = app.scriptPreferences.userInteractionLevel` 先读取原始值；
- `finally` 中还原 `savedInteractionLevel`，不得硬编码恢复为 `INTERACT_WITH_ALL`；
- `open_template`、`select_csv_data_source`、`merge_all_records` 的错误阶段记录；
- `LinkStatus.LINK_MISSING` 检测和 Python 的 CSV 图片路径存在性校验；
- 对于 **JSX 开始执行之前** 的模态框，返回可操作报错，要求先关闭现有对话框，不能擅自杀进程或强制点击未知提示。

相关回归测试：`tests/test_indesign_merge.py`。GitHub Actions 验证的是代码与模拟 COM 失败，不表示在 Windows 上已完成真实 InDesign 合并测试。
