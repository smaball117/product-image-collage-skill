# Product Image Collage Skill

## Overview

商品图片自动拼图生产 Skill。

本 Skill 采用「批次生产（Batch Production）」模式。

目标：用户提供商品图片路径和本地工具路径，Skill 根据品类规则调用对应工具，生成标准化商品图片生产批次包。

---

# User Input

用户调用格式：

```
调用 product-image-collage skill

图片路径：xxx

工具路径：xxx

品类：内裤 / 内衣套 / 其他

执行商品拼图
```

---

# Core Workflow

## Step 1：创建生产批次

根据日期和品类创建批次名称：

```
YYYY-MM-DD_品类
```

例如：

```
2026-10-08_underwear
```

所有输出文件进入该批次目录。

---

## Step 2：加载品类规则

根据品类读取：

```
categories/{category}/rule.md
```

规则负责：

- 图片命名识别
- 图片类型映射
- 拼图顺序
- 异常处理

不同品类禁止共享编号逻辑。

---

## Step 3：调用本地工具

工具由用户提供路径。

工具包括：

### scan_product_images.py

用途：

- 扫描商品图片目录
- 识别货号和颜色
- 生成图片映射数据

---

### ocr_rename_images.py

用途：

- OCR识别图片文字
- 根据识别结果重命名图片

---

### batch_add_white_mask.py

用途：

- 清理图片中文字区域
- 输出处理后的商品图片

---

## Step 4：人工设计节点

以下流程保留人工：

- InDesign 数据合并
- 页面位置调整
- 最终导出确认

Skill 不自动模拟设计软件操作。

---

# Output Batch Structure

标准输出：

```
output/

└── YYYY-MM-DD_品类/

    ├── csv/
    │
    ├── indesign/
    │
    ├── exported/
    │
    ├── renamed/
    │
    ├── cleaned/
    │
    └── report.md
```

---

# Hard Rules

1. 原始图片目录禁止修改。
2. 所有处理结果必须进入批次目录。
3. 图片编号必须根据品类 rule.md 判断。
4. 工具路径由用户提供，不固定写入 Skill。
5. 每个批次必须生成处理记录。

---

# Future Extension

新增品类只需要增加：

```
categories/{new-category}/rule.md
```

无需修改核心工作流。
