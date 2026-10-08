# 外部 Python 工具调用协议

## 边界

- 用户给出 **商品图片目录**、**本地 Python 工具目录**、**品类**。仓库保存 Skill 调度及适配脚本，不复制用户原有三个工具。
- Agent 只能在**具有本机文件读写和命令行执行权限**的环境运行（如本地 Codex）。GitHub 网页及云端聊天无法直接读取用户 F 盘。
- Agent 不应直接对原始素材运行会原地重命名的脚本。
- InDesign 数据合并、位置调整、导出仍由用户完成；Skill 只制作可供数据合并的 CSV，并在用户完成导出后处理输出图片。

## 原工具能力与已知局限

| 脚本 | 可重用函数 | 不可直接拿来做的事 |
|---|---|---|
| `scan_product_images.py` | `match_image_number(filename)` | `main()` 固定内衣套六栏，不能正确扫描内裤；末尾有交互回车 |
| `ocr_rename_images.py` | `init_ocr()`, `extract_text_from_image()`, `clean_to_filename()` | `main()` 读取硬编码 `IMAGE_DIR` 且原地重命名 |
| `batch_add_white_mask.py` | `process_image(image_path, output_dir)` | `main()` 读取硬编码 `INPUT_DIR` |

因此 **只通过适配层导入上表函数**，不执行其 `main()`，三个原始脚本不必修改。

## 阶段 A：准备与检查

在本地仓库根目录运行（Windows PowerShell 示例）：

~~~powershell
python scripts/batch_runner.py check --tools "F:\AI_Tools\product_scripts" --category "内裤" --images "F:\2027春夏\商品图片"
~~~

检查路径、品类、脚本签名，不做任何源图片更改。

## 阶段 B：制作待合并批次包

~~~powershell
python scripts/batch_runner.py prepare --images "F:\2027春夏\商品图片" --tools "F:\AI_Tools\product_scripts" --category "内裤"
~~~

生成 `YYYY-MM-DD_underwear/` 及：
- `csv/data_merge_utf16.csv`（UTF-16 LE + BOM，图像表头 `@` 开头）
- `csv/data_merge_utf8.csv`（用于排查）
- `batch.json`（阶段状态与可恢复信息）
- `report/report.md`（数量、缺项、重复及警告）
- `report/overrides-needed.json`（若有无法识别的无编号图片）

如有无法确定的槽位，**不宣布 CSV 已就绪**，用户应先提供覆盖映射并重新 `prepare --overrides xxx.json`。

## 阶段 C：人工 InDesign

1. 打开匹配品类的 InDesign 模板。
2. 窗口 → 实用程序 → 数据合并 → 选择 `csv/data_merge_utf16.csv`。
3. 人工调整页面并导出为图片。
4. 导出的图片保留在指定目录，告诉 Agent 目录位置。

注意：产品品类规则并不等于真实 ID 版式，缺失模板不应宣称自动拼图已完成。

## 阶段 D：续跑 OCR 和白色遮罩

~~~powershell
python scripts/batch_runner.py resume --batch "F:\批次输出\2026-10-08_underwear" --exported "F:\ID导出图片"
~~~

- 将原始 ID 导出图**复制**进批次 `exported/`。
- 通过外部 `ocr_rename_images.py` 的函数逐张识别，重命名**副本**到 `renamed/`。
- 通过外部 `batch_add_white_mask.py` 的函数生成 `cleaned/`。
- 冲突和 OCR 失败不覆盖旧文件，记录警告并保留源导出图。
- OCR 和遮罩须使用用户本机已安装的 PaddleOCR / PaddlePaddle / Pillow。首次 OCR 可能下载模型。
- 遮罩尺寸位置为原始外部脚本所设的固定值：宽 983、高 119、X=0、Y=1457；仅适用于该 ID 模板，使用不同版式时先确认遮罩坐标。

## 禁止事项

- 禁止静默修改或移动用户源图片。
- 禁止内衣套的无编号背面 PNG 自动猜配。
- 禁止在不同品类之间共享 `-1.png`、`-2.png` 的语义。
- 禁止覆盖已存在批次，使用新批次名或恢复现有批次。
- 不得把准备阶段成功误报为“已完成拼图”。


## 无编号图片的人工确认示例

若 `prepare` 打印 `needs_mapping`，查看当前批次 `report/overrides-needed.json`。这个文件中每个字段的值是**候选文件名数组**，不是最终选择。确认图片后另建一个 JSON 文件，将对应字段改成唯一的文件名字符串：

~~~json
{
  "T20276D01/01_浅水蓝": {
    "上衣背面": "0N2A6666.png",
    "裤子背面": "0N2A6668.png"
  }
}
~~~

**示例文件名仅供说明，须根据实际图片内容由用户确认。** 然后运行：

~~~powershell
python scripts/batch_runner.py prepare --images "图片路径" --tools "工具路径" --category "内衣套" --overrides "F:\override.json"
~~~

系统会创建一个**新批次**而不是覆盖旧批次；查看新批次 `batch.json` 是否已进入 `waiting_indesign`。

## 何时可以声称测试通过

- GitHub Actions 中模拟外部脚本的单元测试通过，只说明批次逻辑、CSV 与安全流程在隔离环境中运行正确。
- 真实投入生产之前，必须在用户本机再检查一次真实工具的版本与依赖，用一套测试商品确认 ID CSV 是否正常合并，用一张 ID 导出图确认 OCR 文本与遮罩坐标正确。
