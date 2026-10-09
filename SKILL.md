---
name: product-image-collage
description: 只输入商品图片路径，自动选择品类并生成 InDesign 数据合并 CSV，提示对应内置模板；用户手动 ID 导出后自动 OCR 命名和遮罩去字。
---

# Product Image Collage Skill

## 用户输入
例如：“调用 product-image-collage Skill，图片路径：F:\\2026年秋冬\\新品商品，帮我做拼图。”

除图片路径之外无需重复提供工具路径或品类；只有图片编号不能可靠区分时才询问品类。运行环境必须能够访问本机文件和命令行（例如本地 Codex）。

## 内置资源
- `scripts/scan_product_images.py`：编号识别函数
- `scripts/ocr_rename_images.py`：PaddleOCR 中文识别、生成文件名
- `scripts/batch_add_white_mask.py`：白遮罩去字
- `scripts/batch_runner.py`：统一调度
- `categories/underwear/rule.md`：内裤规则
- `categories/underwear-set/rule.md`：内衣套规则
- `assets/indesign/内裤数据合并模板-最终版.indd`：内裤 ID 模板
- `assets/indesign/内衣套数据合并模板.indd`：内衣套 ID 模板

三个脚本与规则均包含在 Skill 中，不再要求用户提供工具路径。二进制 ID 模板须在本地上述位置存在；若 GitHub 尚未同步，参照 `assets/indesign/README.md` 安装。

## 严格遵照用户的五步生产流程

### 1. Agent 生成 CSV 表格
在本 Skill 根目录执行：

```powershell
python scripts/batch_runner.py check --images "用户图片路径"
python scripts/batch_runner.py prepare --images "用户图片路径"
```

自动检测品类：`-5.jpg` 是内裤特征，`-1.jpg` 是内衣套特征。两种同时出现或缺少可靠标志时停止并询问 `--category 内裤` 或 `--category 内衣套`，绝不猜测。

**内衣套固定 8 列**：
```csv
货号,颜色,@上衣png,@下衣png,@领口,@袖口,@肩线,@裤腰
```
对应抓取 `-1.png`、`-2.png`、`-1.jpg`、`-2.jpg`、`-3.jpg`、`-4.jpg`。

**内裤固定 8 列**：
```csv
货号,颜色,@正面png,@背面png,@印花,@裤口,@裤边,@裤腰
```
对应抓取 `-1.png`、`-2.png`、`-5.jpg`、`-2.jpg`、`-3.jpg`、`-4.jpg`。

图片单元格为完整本地绝对路径，CSV 为 UTF-16 LE（含 BOM）。
用户在新建的日期品类批次内只需找到 `图片汇总.csv`；如出现重复字段冲突先输出 `图片汇总_待确认.csv`，不让用户误导入 ID。

### 2. 人工 InDesign
告诉用户 CSV 完整路径和匹配的内置 `.indd` 模板完整路径，手动操作：打开 ID 模板 → 窗口 → 实用程序 → 数据合并 → 选择 CSV → 检查位置 → 导出图片。等用户提供导出图片目录。不得声称自动完成 ID。

### 3-4. Agent OCR 重命名 + 白遮罩去字
```powershell
python scripts/batch_runner.py resume --batch "第1步的批次目录" --exported "ID导出图片目录"
```
只操作副本，通过内置 OCR 脚本识别文字并重命名，再用遮罩脚本白色覆盖。遮罩参数 `x=0,y=1457,w=983,h=119` 适用于用户原模板，换模板需先确认。

### 5. 最终交付
只报告 `日期品类批次/最终图片/` 完整路径，以及处理成功/失败张数。内部日志、导出副本、重命名副本置于隐藏的 `.skill/`，不在普通回复中列一堆文件。

## 硬规则
1. 不修改任何原始图片。
2. 无法可靠判断品类或字段时先询问，不盲猜。
3. CSV 字段精确匹配品类模板，绝不增减或调整顺序。
4. 同名批次追加序号，禁止覆盖。
5. 必须等人工 ID 导出后才续跑 OCR。
6. 不能在未进行真实本地 InDesign/OCR 测试时声称全链路已通过。
