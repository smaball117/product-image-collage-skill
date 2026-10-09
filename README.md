# Product Image Collage Skill

**输入一条商品图片文件夹路径 → 自动匹配品类 → 生成 InDesign CSV → 选中对应 ID 模板 → 用户手动导出 → OCR 重命名 → 去文字。**

这是可扩展的商品图片生产 Skill，适用于本地 Codex 等有本地文件权限的 Agent。

## 目录与职责

```text
product-image-collage-skill/
├── SKILL.md                         # Agent 总指令
├── scripts/
│   ├── batch_runner.py              # 生产调度、CSV、状态与续跑
│   ├── scan_product_images.py       # 商品图片编号解析
│   ├── ocr_rename_images.py         # OCR 识字与安全命名
│   └── batch_add_white_mask.py      # 固定白色遮罩去字
├── categories/
│   ├── underwear/rule.md            # 内裤 8 列 CSV
│   ├── underwear-set/rule.md        # 内衣套 8 列 CSV
│   └── template/rule-template.md
├── assets/indesign/
│   ├── 内裤数据合并模板-最终版.indd   # 二进制资源（需同步）
│   └── 内衣套数据合并模板.indd       # 二进制资源（需同步）
├── tests/                           # 自动化回归测试
└── requirements.txt
```

三个 Python 脚本已经集成在仓库内，不需要再输入工具路径。二进制 ID 模板如果尚未存在于仓库，请看 [模板资源安装说明](assets/indesign/README.md)。**不应把只有说明文件的目录误认为模板已上传完毕。**

## 只输入图片路径

给本地 Agent 的提示词：

```text
调用 product-image-collage Skill。
图片路径：F:\2026年秋冬\新品商品
帮我做拼图。
```

在 Skill 本地目录执行：

```powershell
python scripts/batch_runner.py check --images "F:\2026年秋冬\新品商品"
python scripts/batch_runner.py prepare --images "F:\2026年秋冬\新品商品"
```

程序依据素材命名判断品类；遇到内裤 `-5.jpg` 和内衣套 `-1.jpg` 同时存在的情况，会要求指定 `--category 内裤` / `--category 内衣套`，不会冒险猜测。默认只交付 `日期_品类/图片汇总.csv` 一份表格，UTF-16 LE（含 BOM）。

## 正式 CSV 列名与图片抓取

内衣套：

```csv
货号,颜色,@上衣png,@下衣png,@领口,@袖口,@肩线,@裤腰
```

按顺序读取 `-1.png`、`-2.png`、`-1.jpg`、`-2.jpg`、`-3.jpg`、`-4.jpg`。

内裤：

```csv
货号,颜色,@正面png,@背面png,@印花,@裤口,@裤边,@裤腰
```

按顺序读取 `-1.png`、`-2.png`、`-5.jpg`、`-2.jpg`、`-3.jpg`、`-4.jpg`。

## 五步

1. **Agent 生成一份 CSV**。缺失和冲突内部记录，冲突导致 `图片汇总_待确认.csv`。
2. **人工 InDesign**：用相应品类 .indd 模板导入 CSV，调整布局并导出。
3. **Agent OCR**：用户给导出图路径，自动识别文字和按文字命名副本。
4. **Agent 白遮罩**：覆盖固定文字区，输出去字图。
5. **Agent 交付**：`最终图片/`，其余工作状态放在隐藏 `.skill/`。

手动 ID 导出后续跑：

```powershell
python scripts/batch_runner.py resume --batch "日期品类批次的完整路径" --exported "ID导出图片文件夹"
```

## 安装依赖

建议为 Pillow、PaddleOCR 2.x、PaddlePaddle 使用独立 Python 环境（参见 `requirements.txt`）。**当前回归测试只模拟 OCR；真实 OCR 模型与本机 Adobe InDesign 的模板兼容性必须本地验证。** GitHub 及云端聊天无法替代 Windows 上的 InDesign GUI。
